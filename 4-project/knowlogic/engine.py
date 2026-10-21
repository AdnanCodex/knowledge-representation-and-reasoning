"""
Reasoning engine for KnowLogic AI.

Implements the same rules as `knowlogic/prolog/university.pl` using
backward chaining over the KnowledgeBase, and records a full proof
trace (facts used + rules fired + steps) for every answer - that trace
is what makes the system *explainable*, and it is what the chatbot and
the Reasoning Explorer display.

If SWI-Prolog is installed (binary `swipl` or the `pyswip` package),
`PrologBridge` can additionally run the queries against the real
Prolog file. The Python engine mirrors the Prolog rules exactly, so
answers are identical with or without SWI-Prolog present.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .kb import KnowledgeBase

RULES = {
    "R1_eligible": "eligible(S, C) :- forall prerequisite P of C: completed(S, P), not completed(S, C), not enrolled(S, C).",
    "R2_missing": "missing_prereqs(S, C) = { P | prerequisite(C, P), not completed(S, P) }.",
    "R3_instructor_of": "instructor_of(S, I) :- enrolled(S, C), teaches(I, C).",
    "R4_student_of": "student_of(I, S) :- teaches(I, C), enrolled(S, C).",
    "R5_all_prereqs": "all_prereqs(C, P) :- prerequisite(C, P).  all_prereqs(C, P) :- prerequisite(C, X), all_prereqs(X, P).  % transitive closure",
    "R6_recommend": "recommended(S, C) :- eligible(S, C).  % eligible and not yet taken",
    "R7_classmates": "classmates(S1, S2) :- enrolled(S1, C), enrolled(S2, C), S1 \\= S2.",
    "R8_can_graduate_check": "course_path(S, Target) = ordered list of missing courses in prerequisite order for Target.",
    "R9_progress": "degree_progress(S) = credits(completed courses of S) / credits(all catalogue courses) x 100, with the remaining courses listed.",
    "R10_transcript": "transcript(S) = completed + enrolled courses of S with titles and credits, derived directly from KB facts.",
}


@dataclass
class Explanation:
    """One answered query plus its proof trace."""
    query: str
    answer: object
    facts_used: list[str] = field(default_factory=list)
    rules_fired: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)

    def render(self) -> str:
        out = [f"Query: {self.query}", f"Answer: {self.answer}", "", "Reasoning steps:"]
        out += [f"  {n}. {s}" for n, s in enumerate(self.steps, 1)]
        if self.facts_used:
            out += ["", "Facts used:"] + [f"  - {f}" for f in self.facts_used]
        if self.rules_fired:
            out += ["", "Rules fired:"] + [f"  - {r}: {RULES.get(r, '')}" for r in self.rules_fired]
        return "\n".join(out)


class ReasoningEngine:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    # ---------- helpers ----------
    def _sname(self, sid: str) -> str:
        s = self.kb.students.get(sid); return s.name if s else sid

    def _iname(self, iid: str) -> str:
        i = self.kb.instructors.get(iid); return i.name if i else iid

    # ---------- R2: missing prerequisites ----------
    def missing_prereqs(self, sid: str, code: str) -> Explanation:
        kb = self.kb
        direct = kb.direct_prereqs(code)
        done = set(kb.completed_courses(sid))
        missing = [p for p in direct if p not in done]
        facts = [f"prerequisite('{code}', '{p}')" for p in direct]
        facts += [f"completed({sid}, '{p}')" for p in direct if p in done]
        facts += [f"NOT completed({sid}, '{p}')" for p in missing]
        steps = [f"Direct prerequisites of {code}: {direct or 'none'}",
                 f"Courses completed by {self._sname(sid)}: {sorted(done)}",
                 f"Missing = prerequisites - completed = {missing}"]
        return Explanation(f"missing_prereqs({sid}, {code})", missing, facts, ["R2_missing"], steps)

    # ---------- R1: eligibility ----------
    def eligible(self, sid: str, code: str) -> Explanation:
        kb = self.kb
        miss = self.missing_prereqs(sid, code)
        already_done = code in kb.completed_courses(sid)
        already_enr = code in kb.enrolled_courses(sid)
        ok = not miss.answer and not already_done and not already_enr
        steps = list(miss.steps)
        if already_done: steps.append(f"{code} is already completed -> not eligible (cannot retake it).")
        if already_enr: steps.append(f"Already enrolled in {code} -> not eligible.")
        steps.append(f"All prerequisites completed: {not miss.answer} -> eligible = {ok}")
        return Explanation(f"eligible({sid}, {code})", ok, miss.facts_used,
                           ["R1_eligible", "R2_missing"], steps)

    # ---------- R5: transitive prerequisites ----------
    def all_prereqs(self, code: str) -> Explanation:
        seen, order, steps = set(), [], []

        def visit(c: str, depth: int):
            for p in self.kb.direct_prereqs(c):
                steps.append(f"{'  ' * depth}prerequisite('{c}', '{p}')")
                if p not in seen:
                    seen.add(p); order.append(p); visit(p, depth + 1)
        visit(code, 0)
        steps.append(f"Transitive closure (all prerequisites of {code}): {sorted(seen)}")
        return Explanation(f"all_prereqs({code})", sorted(seen),
                           [f"prerequisite chain from {code}"], ["R5_all_prereqs"], steps)

    # ---------- R3 / R4 ----------
    def instructors_of_student(self, sid: str) -> Explanation:
        result, facts, steps = {}, [], []
        for code in self.kb.enrolled_courses(sid):
            for iid in self.kb.instructor_of_course(code):
                result.setdefault(iid, []).append(code)
                facts += [f"enrolled({sid}, '{code}')", f"teaches({iid}, '{code}')"]
                steps.append(f"{self._sname(sid)} is enrolled in {code}, taught by {self._iname(iid)} -> instructor.")
        ans = {self._iname(i): v for i, v in result.items()}
        return Explanation(f"instructor_of({sid}, ?I)", ans, sorted(set(facts)), ["R3_instructor_of"], steps or ["No enrolments found."])

    def students_of_instructor(self, iid: str) -> Explanation:
        result, facts, steps = {}, [], []
        for iid2, code in sorted(self.kb.teaches):
            if iid2 != iid: continue
            studs = self.kb.students_in_course(code)
            if studs:
                result[code] = [self._sname(s) for s in studs]
                facts += [f"teaches({iid}, '{code}')"] + [f"enrolled({s}, '{code}')" for s in studs]
                steps.append(f"{self._iname(iid)} teaches {code}; enrolled students: {result[code]}")
        return Explanation(f"student_of({iid}, ?S)", result, sorted(set(facts)), ["R4_student_of"], steps or ["No enrolled students in any course."])

    # ---------- R7: classmates ----------
    def classmates(self, sid: str) -> Explanation:
        mates, facts, steps = {}, [], []
        for code in self.kb.enrolled_courses(sid):
            others = [s for s in self.kb.students_in_course(code) if s != sid]
            if others:
                mates[code] = [self._sname(s) for s in others]
                facts += [f"enrolled({sid}, '{code}')"] + [f"enrolled({o}, '{code}')" for o in others]
                steps.append(f"Also enrolled in {code}: {mates[code]} -> classmates.")
        return Explanation(f"classmates({sid}, ?S)", mates, sorted(set(facts)), ["R7_classmates"], steps or ["No classmates (no shared enrolment)."])

    # ---------- R6: recommendations ----------
    def recommended_courses(self, sid: str) -> Explanation:
        recs, facts, steps = [], [], []
        for code in sorted(self.kb.courses):
            e = self.eligible(sid, code)
            if e.answer:
                recs.append(code)
                steps.append(f"{code}: all prerequisites complete and not yet taken -> recommended.")
                facts += e.facts_used
        steps.append(f"Total recommended: {recs}")
        return Explanation(f"recommended({sid}, ?C)", recs, sorted(set(facts)),
                           ["R6_recommend", "R1_eligible"], steps)

    # ---------- R8: study path to a target course ----------
    def course_path(self, sid: str, target: str) -> Explanation:
        """Topologically ordered list of courses still needed before target."""
        closure = self.all_prereqs(target).answer
        done = set(self.kb.completed_courses(sid))
        needed = [c for c in closure if c not in done]
        # topological order: a course appears after its own prerequisites
        ordered: list[str] = []
        temp: set[str] = set()

        def visit(c: str):
            if c in temp or c not in needed: return
            temp.add(c)
            for p in self.kb.direct_prereqs(c): visit(p)
            ordered.append(c)
        for c in sorted(needed): visit(c)
        steps = [f"Transitive prerequisites of {target}: {closure}",
                 f"Already completed: {sorted(done & set(closure))}",
                 f"Remaining courses (in correct order): {ordered}",
                 f"After these, {target} can be taken."]
        return Explanation(f"course_path({sid}, {target})", ordered,
                           closure, ["R8_can_graduate_check", "R5_all_prereqs", "R2_missing"], steps)

    # ---------- R9: degree progress ----------
    def total_credits(self) -> int:
        return sum(c.credits for c in self.kb.courses.values())

    def degree_progress(self, sid: str) -> Explanation:
        kb = self.kb
        done = kb.completed_courses(sid)
        done_cr = sum(kb.courses[c].credits for c in done)
        total = self.total_credits()
        remaining = [c for c in sorted(kb.courses)
                     if c not in done and c not in kb.enrolled_courses(sid)]
        pct = round(100 * done_cr / total, 1) if total else 0.0
        ans = {"completed_credits": done_cr, "total_credits": total,
               "percent": pct, "completed_courses": done, "remaining_courses": remaining}
        facts = [f"completed({sid}, '{c}') [{kb.courses[c].credits} cr]" for c in done]
        steps = [f"Credits from completed courses: {done_cr}",
                 f"Catalogue total credits: {total}",
                 f"Progress = {done_cr}/{total} = {pct}%",
                 f"Remaining (not completed/enrolled): {remaining}"]
        return Explanation(f"degree_progress({sid})", ans, facts, ["R9_progress", "R10_transcript"], steps)

    # ---------- R10: transcript ----------
    def transcript(self, sid: str) -> Explanation:
        kb = self.kb
        comp = [(c, kb.courses[c].title, kb.courses[c].credits) for c in kb.completed_courses(sid)]
        enr = [(c, kb.courses[c].title, kb.courses[c].credits) for c in kb.enrolled_courses(sid)]
        ans = {"completed": comp, "enrolled": enr}
        facts = [f"completed({sid}, '{c}')" for c, _, _ in comp] + \
                [f"enrolled({sid}, '{c}')" for c, _, _ in enr]
        steps = [f"Completed: {[c for c, _, _ in comp]} ({sum(x[2] for x in comp)} credits)",
                 f"Currently enrolled: {[c for c, _, _ in enr]}"]
        return Explanation(f"transcript({sid})", ans, facts, ["R10_transcript"], steps)

    # ---------- analytics (derived from facts, no guessing) ----------
    def course_demand(self) -> dict[str, int]:
        """Enrollments per course, most demanded first."""
        demand = {code: len(self.kb.students_in_course(code)) for code in self.kb.courses}
        return dict(sorted(demand.items(), key=lambda kv: (-kv[1], kv[0])))

    def top_students(self, n: int = 3) -> list[tuple[str, int, int]]:
        """(name, completed_credits, completed_courses) - best first."""
        rows = []
        for sid, s in self.kb.students.items():
            done = self.kb.completed_courses(sid)
            rows.append((s.name, sum(self.kb.courses[c].credits for c in done), len(done)))
        rows.sort(key=lambda r: (-r[1], -r[2], r[0]))
        return rows[:n]

    def instructor_workload(self) -> list[dict]:
        """Per-instructor load, derived from teaches + enrolled facts."""
        rows = []
        for iid, ins in sorted(self.kb.instructors.items()):
            courses = sorted(c for (i2, c) in self.kb.teaches if i2 == iid)
            students = {s for c in courses for s in self.kb.students_in_course(c)}
            rows.append({"id": iid, "instructor": ins.name, "courses": courses,
                         "course_count": len(courses), "students_taught": len(students),
                         "enrolments": sum(len(self.kb.students_in_course(c)) for c in courses)})
        rows.sort(key=lambda r: (-r["course_count"], -r["students_taught"], r["instructor"]))
        return rows

    def simulate_completion(self, sid: str, extra_completed: list[str]) -> dict:
        """What-if reasoning on a COPY of the KB (the real KB never changes).

        Pretends the student has completed `extra_completed`, then reports
        the progress change and which courses become newly eligible."""
        from .kb import KnowledgeBase  # local import to avoid a cycle
        before = self.degree_progress(sid).answer
        before_eligible = set(self.recommended_courses(sid).answer)
        kb2 = KnowledgeBase.from_dict(self.kb.to_dict())
        for c in extra_completed:
            if c in kb2.courses and c not in kb2.completed_courses(sid):
                kb2.completed.add((sid, c)); kb2.enrolled.discard((sid, c))
        e2 = ReasoningEngine(kb2)
        after = e2.degree_progress(sid).answer
        after_eligible = set(e2.recommended_courses(sid).answer)
        return {"before": before, "after": after,
                "newly_eligible": sorted(after_eligible - before_eligible),
                "simulated": [c for c in extra_completed if c in self.kb.courses]}

    def who_teaches(self, code: str) -> Explanation:
        iids = self.kb.instructor_of_course(code)
        facts = [f"teaches({i}, '{code}')" for i in iids]
        steps = [f"Searched KB for teaches(I, '{code}') -> {iids}"] if iids else ["No instructor assigned."]
        return Explanation(f"teaches(?I, {code})", [self._iname(i) for i in iids], facts, [], steps)


class PrologBridge:
    """Optional bridge to a real SWI-Prolog installation.

    Tries pyswip first, then the `swipl` binary. If neither exists,
    `available()` is False and the Python engine above is used - its
    rules are literal translations of university.pl, and the test
    suite cross-checks the .pl file syntax when swipl is present.
    """

    def __init__(self, prolog_file: str | Path | None = None):
        self.file = Path(prolog_file) if prolog_file else Path(__file__).parent / "prolog" / "university.pl"

    def available(self) -> tuple[bool, str]:
        try:
            import pyswip  # noqa: F401
            return True, "pyswip"
        except Exception:
            pass
        if shutil.which("swipl"):
            return True, "swipl binary"
        return False, "SWI-Prolog not found - Python mirror engine active (same rules). Install SWI-Prolog + pyswip to switch."

    def query(self, goal: str, timeout: int = 15) -> dict:
        ok, how = self.available()
        if not ok:
            return {"ok": False, "backend": how, "error": how}
        if how == "swipl binary":
            cmd = ["swipl", "-q", "-s", str(self.file), "-g", goal, "-t", "halt"]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                return {"ok": r.returncode == 0, "backend": how,
                        "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
            except Exception as e:  # timeout, OS error, ...
                return {"ok": False, "backend": how, "error": str(e)}
        try:
            from pyswip import Prolog
            p = Prolog(); p.consult(str(self.file))
            rows = list(p.query(goal))
            return {"ok": True, "backend": how, "results": rows}
        except Exception as e:
            return {"ok": False, "backend": how, "error": str(e)}
