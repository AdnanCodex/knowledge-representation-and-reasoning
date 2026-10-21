"""
Rule-based chatbot for KnowLogic AI.

No LLM is used for reasoning. The bot:
  1. extracts entities (student / course / instructor) from the question
     by matching against the actual KnowledgeBase,
  2. classifies the intent with patterns,
  3. runs the matching reasoning-engine query,
  4. answers from the proof trace - so every answer is explainable.

Supported intents (English + simple Roman Urdu mix):
  - eligibility        "Can Ali take AI301?" / "Is Ayesha eligible for Deep Learning?"
  - missing prereqs    "What is missing for Hassan to take CS201?"
  - prerequisites      "What are the prerequisites of AI401?" (direct + all)
  - who teaches        "Who teaches Machine Learning?"
  - instructors of     "Who are Ali's teachers?"
  - students of        "Which students does Dr. Sara teach?"
  - recommendations    "Recommend courses for Ali"
  - course path        "How can Hassan reach Deep Learning?" / path/plan to X
  - classmates         "Who are Zara's classmates?"
  - completed/enrolled "Which courses has Ayesha completed / is Zara enrolled in?"
  - list / stats       "List all courses" / "How many students?"
  - contradictions     "Any problems in the knowledge base?"
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .kb import KnowledgeBase
from .engine import ReasoningEngine, Explanation
from .contradictions import detect_contradictions

COURSE_CODE_RE = re.compile(r"\b([A-Za-z]{2,4})\s?(\d{3})\b")


@dataclass
class ChatResult:
    answer: str
    explanation: Explanation | None = None
    intent: str = "unknown"
    entities: dict = field(default_factory=dict)
    highlight_nodes: list[str] = field(default_factory=list)  # for graph highlighting


class Chatbot:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.engine = ReasoningEngine(kb)

    # ---------- entity extraction ----------
    def extract(self, text: str) -> dict:
        kb, out = self.kb, {}
        m = COURSE_CODE_RE.search(text)
        if m:
            c = kb.find_course(m.group(1) + m.group(2))
            if c: out["course"] = c
        if "course" not in out:  # try course title words
            for c in sorted(kb.courses.values(), key=lambda x: -len(x.title)):
                if c.title.lower() in text.lower():
                    out["course"] = c; break
        # students before instructors (names overlap e.g. 'Ahmed')
        # \b matches before an apostrophe too, so "Zara's classmates" works.
        for s in kb.students.values():
            first = re.escape(s.name.split()[0].lower())
            if s.name.lower() in text.lower() or re.search(rf"\b{first}\b", text.lower()):
                out["student"] = s; break
        # Instructor match: full name, or a name-token that belongs to
        # exactly ONE instructor and to no student (avoids 'Khan'/'Ahmed'
        # collisions between Ayesha Khan, Dr. Ahmed Khan, Dr. Bilal Ahmed).
        student_tokens = {t.lower() for s in kb.students.values() for t in s.name.split()}
        token_owner: dict[str, str] = {}
        ambiguous: set[str] = set()
        for i in kb.instructors.values():
            for tok in i.name.replace("Dr.", "").strip().lower().split():
                if tok in token_owner and token_owner[tok] != i.id:
                    ambiguous.add(tok)
                token_owner.setdefault(tok, i.id)
        for i in kb.instructors.values():
            parts = i.name.replace("Dr.", "").strip().lower().split()
            hit = i.name.lower() in text.lower() or any(
                re.search(rf"\b{re.escape(tok)}\b", text.lower())
                for tok in parts
                if tok not in ambiguous and tok not in student_tokens and token_owner.get(tok) == i.id)
            if hit:
                out["instructor"] = i; break
        return out

    # ---------- main entry ----------
    def ask(self, text: str) -> ChatResult:
        if not text or not text.strip():
            return ChatResult("Please type a question - e.g. 'Can Ali take AI301?'", intent="empty")
        q = text.lower()
        ent = self.extract(text)
        stu, course, ins = ent.get("student"), ent.get("course"), ent.get("instructor")

        def need(*kinds: str) -> ChatResult | None:
            missing = [k for k in kinds if k not in ent]
            if not missing: return None
            pretty = {"student": "a student name", "course": "a course (code or title)", "instructor": "an instructor name"}
            return ChatResult(
                f"This question needs {', '.join(pretty[m] for m in missing)}. "
                f"Available students: {', '.join(s.name for s in self.kb.students.values())}. "
                f"Courses: {', '.join(self.kb.courses)}. "
                f"Instructors: {', '.join(i.name for i in self.kb.instructors.values())}.",
                intent="clarify", entities=ent)

        # contradictions
        if any(w in q for w in ("contradiction", "problem", "issue", "galti", "conflict", "wrong with")):
            issues = detect_contradictions(self.kb)
            if not issues:
                return ChatResult("The knowledge base is clean - no contradictions found.", intent="contradictions", entities=ent)
            lines = [f"{len(issues)} issue(s) found:"] + [f"- [{i['severity']}] {i['message']}" for i in issues]
            nodes = [e for i in issues for e in i["entities"]]
            return ChatResult("\n".join(lines), intent="contradictions", entities=ent, highlight_nodes=nodes)

        # recommendations
        if any(w in q for w in ("recommend", "suggest", "konsa course loon", "which courses should")):
            if r := need("student"): return r
            ex = self.engine.recommended_courses(stu.id)
            titles = [f"{c} ({self.kb.courses[c].title})" for c in ex.answer]
            return ChatResult(
                f"Recommended courses for {stu.name}: {', '.join(titles) if titles else 'none - complete the missing prerequisites first.'}",
                ex, "recommend", ent, [stu.id] + list(ex.answer))

        # course path / plan
        if any(w in q for w in ("path", "plan", "reach", "how can", "kaise loon", "route")) and course and stu:
            ex = self.engine.course_path(stu.id, course.code)
            seq = " -> ".join(ex.answer + [course.code]) if ex.answer else course.code
            return ChatResult(
                f"Study path for {stu.name} to {course.code}: {seq}. "
                f"(Must complete first: {', '.join(ex.answer) if ex.answer else 'nothing - can be taken directly'})",
                ex, "path", ent, [stu.id, course.code] + list(ex.answer))

        # missing prerequisites
        if any(w in q for w in ("missing", "need to take", "required before", "kami")) and stu and course:
            ex = self.engine.missing_prereqs(stu.id, course.code)
            return ChatResult(
                f"For {course.code}, {stu.name} still needs to complete: {', '.join(ex.answer) if ex.answer else 'nothing - all prerequisites are complete.'}",
                ex, "missing", ent, [stu.id, course.code] + list(ex.answer))

        # eligibility
        if any(w in q for w in ("can ", "eligible", "take", "enroll in", "le sakta", "le sakti")) and stu and course:
            ex = self.engine.eligible(stu.id, course.code)
            if ex.answer:
                msg = f"Yes, {stu.name} can take {course.code} ({course.title}) - all prerequisites are complete."
            else:
                miss = self.engine.missing_prereqs(stu.id, course.code).answer
                extra = f" Missing prerequisites: {', '.join(miss)}." if miss else " The course is already completed or enrolled."
                msg = f"No, {stu.name} is not yet eligible for {course.code}.{extra}"
            return ChatResult(msg, ex, "eligibility", ent, [stu.id, course.code])

        # prerequisites of a course
        if "prereq" in q and course:
            direct = self.kb.direct_prereqs(course.code)
            ex = self.engine.all_prereqs(course.code)
            return ChatResult(
                f"Direct prerequisites of {course.code} ({course.title}): {', '.join(direct) or 'none'}. "
                f"All (transitive) prerequisites: {', '.join(ex.answer) or 'none'}.",
                ex, "prerequisites", ent, [course.code] + list(ex.answer))

        # who teaches a course
        if any(w in q for w in ("who teaches", "teacher of", "instructor of", "kon parhata")) and course and "student" not in ent:
            ex = self.engine.who_teaches(course.code)
            return ChatResult(
                f"{course.code} ({course.title}) is taught by: {', '.join(ex.answer) if ex.answer else 'no instructor assigned'}",
                ex, "who_teaches", ent, [course.code])

        # instructors of a student
        if any(w in q for w in ("teacher", "instructor")) and stu:
            ex = self.engine.instructors_of_student(stu.id)
            detail = "; ".join(f"{k}: {', '.join(v)}" for k, v in ex.answer.items())
            return ChatResult(f"Instructors of {stu.name}: {detail if detail else 'none (no enrolments)'}",
                              ex, "instructors_of", ent, [stu.id])

        # students of an instructor
        if ins and any(w in q for w in ("student", "teach", "parhata", "parhati")):
            ex = self.engine.students_of_instructor(ins.id)
            detail = "; ".join(f"{k}: {', '.join(v)}" for k, v in ex.answer.items())
            courses = [c for (i2, c) in self.kb.teaches if i2 == ins.id]
            return ChatResult(
                f"{ins.name} teaches these courses: {', '.join(sorted(courses))}. "
                f"Enrolled students - {detail if detail else 'no students enrolled in any course yet'}",
                ex, "students_of", ent, [ins.id] + sorted(courses))

        # classmates
        if "classmate" in q and stu:
            if r := need("student"): return r
            ex = self.engine.classmates(stu.id)
            detail = "; ".join(f"{k}: {', '.join(v)}" for k, v in ex.answer.items())
            return ChatResult(f"Classmates of {stu.name}: {detail if detail else 'none'}",
                              ex, "classmates", ent, [stu.id])

        # degree progress
        if stu and any(w in q for w in ("progress", "degree", "credits", "kitna complete")):
            ex = self.engine.degree_progress(stu.id)
            a = ex.answer
            return ChatResult(
                f"Degree progress of {stu.name}: {a['completed_credits']}/{a['total_credits']} credits "
                f"({a['percent']}%) complete. Remaining courses: {', '.join(a['remaining_courses']) or 'none'}",
                ex, "progress", ent, [stu.id] + a["completed_courses"])

        # transcript
        if stu and "transcript" in q:
            ex = self.engine.transcript(stu.id)
            comp = ", ".join(f"{c} ({t}, {cr} cr)" for c, t, cr in ex.answer["completed"]) or "none"
            enr = ", ".join(f"{c} ({t})" for c, t, cr in ex.answer["enrolled"]) or "none"
            return ChatResult(f"Transcript of {stu.name}:\nCompleted: {comp}\nEnrolled: {enr}",
                              ex, "transcript", ent, [stu.id])

        # busiest instructor / workload
        if any(w in q for w in ("busiest", "workload", "most students does", "teaches the most")):
            w = self.engine.instructor_workload()
            top = w[0]
            txt = ", ".join(f"{r['instructor']} ({r['course_count']} courses, {r['students_taught']} students)"
                            for r in w[:3])
            return ChatResult(f"Instructor workload (top): {txt}. Busiest: {top['instructor']}.",
                              intent="workload", entities=ent)

        # most popular course / top student
        if any(w in q for w in ("popular", "most enrolled", "demand")):
            d = self.engine.course_demand()
            top = ", ".join(f"{c}: {n}" for c, n in list(d.items())[:5])
            return ChatResult(f"Most in-demand courses (enrolments): {top}",
                              intent="demand", entities=ent)
        if any(w in q for w in ("top student", "best student", "sab se zyada courses", "most courses")):
            tops = self.engine.top_students(3)
            txt = ", ".join(f"{name} ({cr} credits, {cnt} courses)" for name, cr, cnt in tops)
            return ChatResult(f"Top students by completed credits: {txt}", intent="top", entities=ent)

        # completed / enrolled listing
        if stu and ("complete" in q or "passed" in q):
            done = self.kb.completed_courses(stu.id)
            return ChatResult(f"{stu.name} has completed: {', '.join(done) if done else 'nothing yet'}",
                              intent="completed", entities=ent, highlight_nodes=[stu.id] + done)
        if stu and ("enroll" in q or "taking" in q or "studying" in q):
            enr = self.kb.enrolled_courses(stu.id)
            return ChatResult(f"{stu.name} is enrolled in: {', '.join(enr) if enr else 'nothing'}",
                              intent="enrolled", entities=ent, highlight_nodes=[stu.id] + enr)

        # lists / stats
        if any(w in q for w in ("list", "all courses", "show courses")):
            lines = [f"{c.code} - {c.title} ({c.department}, {c.credits} cr)" for c in self.kb.courses.values()]
            return ChatResult("Courses:\n" + "\n".join(lines), intent="list_courses", entities=ent)
        if any(w in q for w in ("how many", "stats", "total", "summary")):
            s = self.kb.stats()
            return ChatResult(f"KB summary: {s['students']} students, {s['instructors']} instructors, "
                              f"{s['courses']} courses, {s['total_facts']} total facts.", intent="stats", entities=ent)
        if "help" in q or q.strip() in ("hi", "hello", "salam"):
            return ChatResult(
                "I am the KnowLogic bot - I answer with logic, not guesses. You can ask:\n"
                "- Can Ali take AI301?\n- What are the prerequisites of AI401?\n"
                "- Recommend courses for Hassan\n- How can Hassan reach Deep Learning?\n"
                "- Who teaches Machine Learning?\n- Which students does Dr. Sara teach?\n"
                "- Who are Zara's classmates?\n- Any problems in the knowledge base?",
                intent="help", entities=ent)

        return ChatResult(
            "I could not understand that question. I only answer with logic from the knowledge base. "
            "Type 'help' to see example questions.",
            intent="unknown", entities=ent)
