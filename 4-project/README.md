# KnowLogic AI 🧠

A professional **Knowledge Representation & Reasoning (KRR)** project that combines:

- 💬 an **intelligent chatbot** that answers from facts + logical rules (no LLM guessing),
- 🕸️ an **interactive knowledge graph** (searchable, query-highlighted),
- ⚙️ a **Prolog-based reasoning engine** (SWI-Prolog file + an exact Python mirror),
- 🔍 **explainable reasoning** — every answer shows the facts, rules and inference steps behind it,
- 🦉 **ontology support** (Protégé / OWL export & import via RDFLib),
- ⚠️ **contradiction detection** and a full **knowledge-base manager**.

**Domain:** University — students, courses, prerequisites, instructors.

---

## Architecture (modular)

```
knowlogic-ai/
├── app.py                      # Streamlit UI (9 pages)
├── requirements.txt
├── knowlogic/
│   ├── kb.py                   # KnowledgeBase: facts + relations, CRUD, JSON, Prolog export
│   ├── engine.py               # ReasoningEngine (rules R1–R8) + Explanation traces
│   │                           # + PrologBridge (pyswip / swipl binary, auto-detected)
│   ├── chatbot.py              # Rule-based NLU: entity extraction → intent → engine query
│   ├── graph_builder.py        # NetworkX graph + PyVis interactive HTML, search, highlight
│   ├── ontology.py             # Turtle/OWL export + RDFLib parsing (Protégé-ready)
│   ├── contradictions.py       # KB integrity: 5 checks (see below)
│   └── prolog/university.pl    # Real SWI-Prolog KB + rules (mirrors the Python engine)
├── data/
│   ├── university.ttl          # Generated ontology (opens in Protégé)
│   └── sample_kb.json          # Sample knowledge base in JSON
└── tests/test_knowlogic.py     # 28 unit tests (engine, chatbot, graph, ontology, contradictions, progress, simulation)
```

**Integration:** the chatbot, graph, ontology and UI all derive from the *same* `KnowledgeBase`
object. Edit a fact in the KB Manager and the chatbot answers, graph and contradiction
checks update immediately. Chatbot answers return node IDs that the graph page highlights.

## The rules (same in Prolog and Python)

| Rule | Meaning |
|---|---|
| R1 `eligible(S,C)` | All prerequisites completed, course not already completed/enrolled |
| R2 `missing_prereqs` | Prerequisites of C that S has not completed |
| R3 `instructor_of` | enrolled(S,C) ∧ teaches(I,C) → I is S's instructor |
| R4 `student_of` | Inverse of R3 |
| R5 `all_prereqs` | Transitive closure of prerequisites (recursion) |
| R6 `recommended` | Courses a student is eligible for but hasn't taken |
| R7 `classmates` | Two students enrolled in the same course |
| R8 `course_path` | Missing courses to a target, in correct prerequisite order (topological) |
| R9 `degree_progress` | Completed credits / total catalogue credits, with remaining courses |
| R10 `transcript` | A student's completed + enrolled courses with titles and credits |
| Analytics | Instructor workload, course demand, top students — all derived from facts |
| What-if simulation | Hypothetical reasoning on a copy of the KB: progress delta + newly eligible courses |

## Sample data

12 students, 6 instructors, 15 courses, 14 prerequisite links, 113 facts — and the
sample KB is **fully consistent**: the Contradictions page reports zero issues.
The detector itself is verified by tests that inject a violation (enrolling a
student in a course whose prerequisites they have not completed) into a copy of
the KB, check that it is caught, and that removing it makes the KB clean again.

## Setup

```bash
# 1. (Recommended) create an environment — use your Anaconda 'ml' env if you have one
conda activate ml            # or:  python -m venv .venv && .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the tests (core logic, no UI needed)
python -m unittest discover -s tests -v

# 4. Launch the app
streamlit run app.py
```

### Optional: real SWI-Prolog

1. Install SWI-Prolog from https://www.swi-prolog.org/download/stable
2. `pip install pyswip` (and make sure `swipl` is on your PATH)
3. The sidebar shows the detected backend automatically. Try in the SWI-Prolog terminal:

```prolog
?- [university].              % from knowlogic/prolog/
?- eligible(ayesha, 'AI302'). % false — AI301 not completed yet
?- missing_prereqs(ali, 'AI301', M).   % M = ['CS201', 'MATH201']
?- recommended(zara, C).      % C = 'CS305' ; C = 'MATH201'
```

Without SWI-Prolog the app still works fully: the Python engine executes the *same*
rules and the sidebar honestly shows which backend is active.

## Example chatbot questions

- `Can Ali take AI301?` → No + missing prerequisites + proof trace
- `What are the prerequisites of AI401?` → direct + transitive
- `Recommend courses for Hassan`
- `How can Hassan reach Deep Learning?` → ordered study path
- `Who teaches Machine Learning?` / `Which students does Dr. Sara teach?`
- `Who are Zara's classmates?`
- `Any problems in the knowledge base?`

## Error handling

- Unknown student/course/instructor in a question → the bot asks for clarification and lists valid entities instead of crashing or hallucinating.
- Invalid KB additions (duplicate IDs, unknown references, self-prerequisite) raise clear errors shown in the UI.
- Missing optional packages (networkx / pyvis / rdflib / SWI-Prolog) degrade gracefully with an exact install instruction; core reasoning never depends on them.

## Author

Muhammad Adnan — BS Artificial Intelligence, Hazara University, Mansehra (CGPA 3.95, 1st in class)
GitHub: https://github.com/AdnanCodex · LinkedIn: https://linkedin.com/in/adnan-ai
