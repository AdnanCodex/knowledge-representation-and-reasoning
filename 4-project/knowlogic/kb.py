"""
Knowledge Base for KnowLogic AI (university domain).

Stores facts as typed records and relations. Everything else in the
project (reasoning engine, Prolog file, graph, ontology) is *derived*
from this single source of truth, so the components can never disagree.

Fact types
----------
- Student(id, name, department, semester)
- Instructor(id, name, department)
- Course(code, title, department, credits)
Relations
---------
- completed(student_id, course_code)
- enrolled(student_id, course_code)
- teaches(instructor_id, course_code)
- prerequisite(course_code, prereq_code)   # course requires prereq first
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Student:
    id: str
    name: str
    department: str
    semester: int


@dataclass
class Instructor:
    id: str
    name: str
    department: str


@dataclass
class Course:
    code: str
    title: str
    department: str
    credits: int = 3


@dataclass
class KnowledgeBase:
    students: dict[str, Student] = field(default_factory=dict)
    instructors: dict[str, Instructor] = field(default_factory=dict)
    courses: dict[str, Course] = field(default_factory=dict)
    completed: set[tuple[str, str]] = field(default_factory=set)
    enrolled: set[tuple[str, str]] = field(default_factory=set)
    teaches: set[tuple[str, str]] = field(default_factory=set)
    prerequisites: set[tuple[str, str]] = field(default_factory=set)  # (course, prereq)

    # ---------- basic CRUD with validation ----------
    def add_student(self, s: Student) -> None:
        if s.id in self.students:
            raise ValueError(f"Student id already exists: {s.id}")
        self.students[s.id] = s

    def add_instructor(self, i: Instructor) -> None:
        if i.id in self.instructors:
            raise ValueError(f"Instructor id already exists: {i.id}")
        self.instructors[i.id] = i

    def add_course(self, c: Course) -> None:
        if c.code in self.courses:
            raise ValueError(f"Course code already exists: {c.code}")
        self.courses[c.code] = c

    def _check_student(self, sid: str) -> None:
        if sid not in self.students:
            raise KeyError(f"Unknown student: {sid}")

    def _check_course(self, code: str) -> None:
        if code not in self.courses:
            raise KeyError(f"Unknown course: {code}")

    def add_completed(self, sid: str, code: str) -> None:
        self._check_student(sid); self._check_course(code)
        self.completed.add((sid, code))

    def add_enrolled(self, sid: str, code: str) -> None:
        self._check_student(sid); self._check_course(code)
        self.enrolled.add((sid, code))

    def add_teaches(self, iid: str, code: str) -> None:
        if iid not in self.instructors:
            raise KeyError(f"Unknown instructor: {iid}")
        self._check_course(code)
        self.teaches.add((iid, code))

    def add_prerequisite(self, code: str, prereq: str) -> None:
        self._check_course(code); self._check_course(prereq)
        if code == prereq:
            raise ValueError("A course cannot be its own prerequisite")
        self.prerequisites.add((code, prereq))

    def remove_relation(self, kind: str, a: str, b: str) -> bool:
        store = {"completed": self.completed, "enrolled": self.enrolled,
                 "teaches": self.teaches, "prerequisite": self.prerequisites}[kind]
        if (a, b) in store:
            store.discard((a, b)); return True
        return False

    # ---------- lookups used by the engine / UI ----------
    def direct_prereqs(self, code: str) -> list[str]:
        return sorted(p for (c, p) in self.prerequisites if c == code)

    def completed_courses(self, sid: str) -> list[str]:
        return sorted(c for (s, c) in self.completed if s == sid)

    def enrolled_courses(self, sid: str) -> list[str]:
        return sorted(c for (s, c) in self.enrolled if s == sid)

    def instructor_of_course(self, code: str) -> list[str]:
        return sorted(i for (i, c) in self.teaches if c == code)

    def students_in_course(self, code: str) -> list[str]:
        return sorted(s for (s, c) in self.enrolled if c == code)

    def find_student(self, text: str) -> Student | None:
        """Match by id, full name, or first name (case-insensitive)."""
        t = text.strip().lower()
        for s in self.students.values():
            if t in (s.id.lower(), s.name.lower(), s.name.lower().split()[0]):
                return s
        for s in self.students.values():  # partial match as fallback
            if t and t in s.name.lower():
                return s
        return None

    def find_instructor(self, text: str) -> Instructor | None:
        t = text.strip().lower().replace("dr.", "").replace("dr", "").strip()
        for i in self.instructors.values():
            clean = i.name.lower().replace("dr.", "").strip()
            if t in (i.id.lower(), clean, clean.split()[-1] if clean else ""):
                return i
        for i in self.instructors.values():
            if t and t in i.name.lower():
                return i
        return None

    def find_course(self, text: str) -> Course | None:
        t = text.strip().upper().replace(" ", "")
        for c in self.courses.values():
            if t == c.code.upper().replace(" ", ""):
                return c
        tl = text.strip().lower()
        for c in self.courses.values():
            if tl == c.title.lower() or tl in c.title.lower():
                return c
        return None

    # ---------- serialisation ----------
    def stats(self) -> dict:
        return {
            "students": len(self.students), "instructors": len(self.instructors),
            "courses": len(self.courses), "completed_facts": len(self.completed),
            "enrollments": len(self.enrolled), "teaches_facts": len(self.teaches),
            "prerequisite_rules": len(self.prerequisites),
            "total_facts": (len(self.students) + len(self.instructors) + len(self.courses)
                            + len(self.completed) + len(self.enrolled)
                            + len(self.teaches) + len(self.prerequisites)),
        }

    def to_dict(self) -> dict:
        return {
            "students": [asdict(s) for s in self.students.values()],
            "instructors": [asdict(i) for i in self.instructors.values()],
            "courses": [asdict(c) for c in self.courses.values()],
            "completed": sorted(self.completed), "enrolled": sorted(self.enrolled),
            "teaches": sorted(self.teaches), "prerequisites": sorted(self.prerequisites),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KnowledgeBase":
        kb = cls()
        for s in d.get("students", []): kb.students[s["id"]] = Student(**s)
        for i in d.get("instructors", []): kb.instructors[i["id"]] = Instructor(**i)
        for c in d.get("courses", []): kb.courses[c["code"]] = Course(**c)
        kb.completed = {tuple(x) for x in d.get("completed", [])}
        kb.enrolled = {tuple(x) for x in d.get("enrolled", [])}
        kb.teaches = {tuple(x) for x in d.get("teaches", [])}
        kb.prerequisites = {tuple(x) for x in d.get("prerequisites", [])}
        return kb

    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "KnowledgeBase":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_prolog_facts(self) -> str:
        """Render the whole KB as SWI-Prolog facts (same syntax as data file)."""
        lines = ["% --- Facts generated from KnowLogic KnowledgeBase ---"]
        for s in self.students.values():
            lines.append(f"student({s.id}, '{s.name}', '{s.department}', {s.semester}).")
        for i in self.instructors.values():
            lines.append(f"instructor({i.id}, '{i.name}', '{i.department}').")
        for c in self.courses.values():
            lines.append(f"course('{c.code}', '{c.title}', '{c.department}', {c.credits}).")
        for sid, code in sorted(self.completed):
            lines.append(f"completed({sid}, '{code}').")
        for sid, code in sorted(self.enrolled):
            lines.append(f"enrolled({sid}, '{code}').")
        for iid, code in sorted(self.teaches):
            lines.append(f"teaches({iid}, '{code}').")
        for code, pre in sorted(self.prerequisites):
            lines.append(f"prerequisite('{code}', '{pre}').")
        return "\n".join(lines) + "\n"


def load_sample_kb() -> KnowledgeBase:
    """Sample university data: 12 students, 6 instructors, 15 courses,
    113 facts - and FULLY CONSISTENT (every enrolment satisfies its
    prerequisites; contradiction detection returns zero issues).
    Earlier the sample contained one intentional violation (Omar in
    AI301); that was removed on the user's request - the detector is
    now demonstrated by tests that inject a violation on a copy."""
    kb = KnowledgeBase()
    for i in [Instructor("dr_ahmed", "Dr. Ahmed Khan", "Computer Science"),
              Instructor("dr_sara", "Dr. Sara Malik", "Artificial Intelligence"),
              Instructor("dr_bilal", "Dr. Bilal Ahmed", "Mathematics"),
              Instructor("dr_fatima", "Dr. Fatima Noor", "Computer Science"),
              Instructor("dr_usman", "Dr. Usman Tariq", "Computer Science"),
              Instructor("dr_maryam", "Dr. Maryam Aslam", "Artificial Intelligence")]:
        kb.add_instructor(i)
    for c in [Course("CS101", "Introduction to Programming", "Computer Science", 3),
              Course("CS102", "Data Structures", "Computer Science", 3),
              Course("CS201", "Algorithms", "Computer Science", 3),
              Course("CS202", "Operating Systems", "Computer Science", 3),
              Course("CS305", "Database Systems", "Computer Science", 3),
              Course("CS310", "Computer Networks", "Computer Science", 3),
              Course("CS320", "Software Engineering", "Computer Science", 3),
              Course("MATH101", "Calculus I", "Mathematics", 3),
              Course("MATH201", "Statistics", "Mathematics", 3),
              Course("MATH301", "Linear Algebra", "Mathematics", 3),
              Course("AI301", "Machine Learning", "Artificial Intelligence", 3),
              Course("AI302", "Natural Language Processing", "Artificial Intelligence", 3),
              Course("AI303", "Computer Vision", "Artificial Intelligence", 3),
              Course("AI305", "Data Science", "Artificial Intelligence", 4),
              Course("AI401", "Deep Learning", "Artificial Intelligence", 4)]:
        kb.add_course(c)
    for code, pre in [("CS102", "CS101"), ("CS201", "CS102"), ("CS202", "CS102"),
                      ("CS305", "CS102"), ("CS310", "CS201"), ("CS320", "CS102"),
                      ("MATH201", "MATH101"), ("MATH301", "MATH101"),
                      ("AI301", "CS201"), ("AI301", "MATH201"),
                      ("AI302", "AI301"), ("AI303", "AI301"), ("AI305", "MATH201"),
                      ("AI401", "AI301")]:
        kb.add_prerequisite(code, pre)
    for iid, code in [("dr_ahmed", "CS101"), ("dr_ahmed", "CS102"),
                      ("dr_fatima", "CS201"), ("dr_fatima", "CS305"), ("dr_fatima", "CS320"),
                      ("dr_bilal", "MATH101"), ("dr_bilal", "MATH201"), ("dr_bilal", "MATH301"),
                      ("dr_sara", "AI301"), ("dr_sara", "AI302"), ("dr_sara", "AI401"),
                      ("dr_usman", "CS202"), ("dr_usman", "CS310"),
                      ("dr_maryam", "AI303"), ("dr_maryam", "AI305")]:
        kb.add_teaches(iid, code)
    for s in [Student("ali", "Ali Raza", "Computer Science", 5),
              Student("ayesha", "Ayesha Khan", "Artificial Intelligence", 7),
              Student("hassan", "Hassan Ali", "Computer Science", 3),
              Student("zara", "Zara Iqbal", "Computer Science", 5),
              Student("omar", "Omar Farooq", "Artificial Intelligence", 3),
              Student("danish", "Danish Mehmood", "Computer Science", 3),
              Student("kinza", "Kinza Tariq", "Artificial Intelligence", 5),
              Student("shayan", "Shayan Ahmed", "Computer Science", 7),
              Student("mahnoor", "Mahnoor Fatima", "Mathematics", 3),
              Student("usama", "Usama Khalid", "Computer Science", 1),
              Student("iqra", "Iqra Aziz", "Artificial Intelligence", 7),
              Student("hamza", "Hamza Sheikh", "Computer Science", 5)]:
        kb.add_student(s)
    for sid, code in [("ali", "CS101"), ("ali", "CS102"), ("ali", "MATH101"),
                      ("ayesha", "CS101"), ("ayesha", "CS102"), ("ayesha", "CS201"),
                      ("ayesha", "MATH101"), ("ayesha", "MATH201"),
                      ("hassan", "CS101"),
                      ("zara", "CS101"), ("zara", "CS102"), ("zara", "MATH101"),
                      ("omar", "CS101"),
                      ("danish", "CS101"),
                      ("kinza", "CS101"), ("kinza", "CS102"), ("kinza", "MATH101"),
                      ("kinza", "MATH201"),
                      ("shayan", "CS101"), ("shayan", "CS102"), ("shayan", "CS201"),
                      ("shayan", "MATH101"),
                      ("mahnoor", "MATH101"),
                      ("iqra", "CS101"), ("iqra", "CS102"), ("iqra", "CS201"),
                      ("iqra", "MATH101"), ("iqra", "MATH201"), ("iqra", "AI301"),
                      ("hamza", "CS101"), ("hamza", "CS102")]:
        kb.add_completed(sid, code)
    for sid, code in [("ali", "CS201"), ("zara", "CS201"),
                      ("ayesha", "AI301"), ("hassan", "CS102"),
                      ("omar", "CS102"), ("omar", "MATH101"),
                      ("danish", "CS102"), ("danish", "MATH101"),
                      ("kinza", "CS201"), ("kinza", "AI305"),
                      ("shayan", "CS305"), ("shayan", "CS310"),
                      ("mahnoor", "MATH201"), ("mahnoor", "CS101"),
                      ("usama", "CS101"), ("usama", "MATH101"),
                      ("iqra", "AI302"), ("iqra", "AI401"),
                      ("hamza", "CS201"), ("hamza", "CS320")]:
        kb.add_enrolled(sid, code)
    return kb
