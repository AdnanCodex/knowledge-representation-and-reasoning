"""Contradiction / integrity detection over the KnowledgeBase."""
from __future__ import annotations
from .kb import KnowledgeBase


def _prereq_cycles(kb: KnowledgeBase) -> list[list[str]]:
    cycles, visited, stack = [], set(), []

    def dfs(c: str):
        visited.add(c); stack.append(c)
        for p in kb.direct_prereqs(c):
            if p in stack:
                cycles.append(stack[stack.index(p):] + [p])
            elif p not in visited:
                dfs(p)
        stack.pop()
    for code in kb.courses:
        if code not in visited:
            dfs(code)
    return cycles


def detect_contradictions(kb: KnowledgeBase, max_teaching_load: int = 4) -> list[dict]:
    """Return a list of issues: {type, severity, message, entities}."""
    issues: list[dict] = []

    # 1. Enrolled without completing prerequisites (the serious one)
    for sid, code in sorted(kb.enrolled):
        missing = [p for p in kb.direct_prereqs(code) if p not in kb.completed_courses(sid)]
        if missing:
            issues.append({
                "type": "enrolled_without_prereq", "severity": "error",
                "message": f"{kb.students[sid].name} is enrolled in {code} but has not completed its prerequisites: {missing}",
                "entities": [sid, code] + missing})

    # 2. Same course both completed AND enrolled
    for sid, code in sorted(kb.completed & kb.enrolled):
        issues.append({
            "type": "completed_and_enrolled", "severity": "error",
            "message": f"For {kb.students[sid].name}, {code} is marked both completed and enrolled - it can only be one.",
            "entities": [sid, code]})

    # 3. Prerequisite cycles (A needs B, B needs A -> nobody can ever take them)
    for cyc in _prereq_cycles(kb):
        issues.append({
            "type": "prereq_cycle", "severity": "error",
            "message": f"Prerequisite cycle detected: {' -> '.join(cyc)}",
            "entities": cyc})

    # 4. Course with students but no instructor
    for code in sorted(kb.courses):
        if kb.students_in_course(code) and not kb.instructor_of_course(code):
            issues.append({
                "type": "course_without_instructor", "severity": "warning",
                "message": f"{code} has enrolled students but no instructor assigned.",
                "entities": [code]})

    # 5. Instructor overload
    load: dict[str, list[str]] = {}
    for iid, code in kb.teaches:
        load.setdefault(iid, []).append(code)
    for iid, codes in sorted(load.items()):
        if len(codes) > max_teaching_load:
            issues.append({
                "type": "instructor_overload", "severity": "warning",
                "message": f"{kb.instructors[iid].name} is teaching {len(codes)} courses (limit {max_teaching_load}): {sorted(codes)}",
                "entities": [iid] + sorted(codes)})

    # 6. Duplicate fact sanity is handled by set storage; report KB health counts
    return issues
