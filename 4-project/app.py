"""
KnowLogic AI - Streamlit app (v2, redesigned).

Run locally:   streamlit run app.py
Live demo:     https://knowlogic-ai.streamlit.app/

Pages: Dashboard | Chatbot | Knowledge Graph | Reasoning Explorer |
       Knowledge Base | Ontology | Contradictions

Design: dark navy + gold theme (CSS + .streamlit/config.toml), native
Streamlit widgets wherever possible (theme-safe, mobile-friendly),
cached graph rendering, and friendly error handling on every page.
The KB lives in st.session_state, so edits instantly affect the
chatbot, reasoning engine, graph and contradiction checks.
"""
from __future__ import annotations

import json
import traceback
from pathlib import Path

import streamlit as st

from knowlogic.kb import KnowledgeBase, load_sample_kb, Student, Course
from knowlogic.engine import ReasoningEngine, PrologBridge, RULES
from knowlogic.chatbot import Chatbot
from knowlogic.graph_builder import KnowledgeGraph
from knowlogic.ontology import kb_to_turtle, parse_ontology, export_owl_xml
from knowlogic.contradictions import detect_contradictions

APP_DIR = Path(__file__).parent

st.set_page_config(page_title="KnowLogic AI — KRR Reasoning System",
                   page_icon="🧠", layout="wide",
                   initial_sidebar_state="expanded",
                   menu_items={"About": "KnowLogic AI: rule-based chatbot + Prolog reasoning "
                                        "engine + knowledge graph + OWL ontology."})

st.markdown("""
<style>
  .block-container { padding-top: 1rem; padding-bottom: 2rem; }
  [data-testid="stSidebar"] { background: linear-gradient(180deg, #0b1526 0%, #0f1e38 100%); }
  [data-testid="stSidebar"] * { color: #dbe4f3 !important; }
  [data-testid="stMetric"] { background:#101c31; border:1px solid #24365a; border-radius:14px;
                             padding:14px 16px; }
  [data-testid="stMetricValue"] { color:#f5c542 !important; }
  .kl-hero { background: linear-gradient(90deg,#0b1526,#14315e 60%,#0b1526);
             border:1px solid #2a4470; border-radius:16px; padding:20px 24px; margin-bottom:14px; }
  .kl-hero h1 { margin:0; font-size:1.9rem; color:#ffffff; }
  .kl-hero p { margin:4px 0 0 0; color:#aebedd; }
  .kl-hero .gold { color:#f5c542; }
  .stButton button, .stDownloadButton button { border-radius:10px; font-weight:600; }
  .stButton button:hover, .stDownloadButton button:hover { border-color:#f5c542; color:#f5c542; }
  [data-testid="stChatMessage"] { border-radius:14px; border:1px solid #24365a; }
  .kl-chip { display:inline-block; padding:2px 10px; border-radius:999px; font-size:.8rem;
             border:1px solid #2a4470; background:#101c31; color:#aebedd; margin-right:6px; }
  .kl-ok { color:#34d399; font-weight:700; } .kl-bad { color:#f87171; font-weight:700; }
  [data-testid="stProgress"] > div > div { background: linear-gradient(90deg,#b8860b,#f5c542); }
  [data-testid="stDataFrame"] { border:1px solid #24365a; border-radius:12px; }
  .kl-insight { background:#101c31; border-left:4px solid #f5c542; border-radius:10px;
                padding:12px 16px; color:#dbe4f3; height:100%; }
  .kl-insight b { color:#f5c542; font-size:1.15rem; display:block; }
  footer { visibility: hidden; }
</style>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ state
if "kb" not in st.session_state:
    st.session_state.kb = load_sample_kb()
if "kb_version" not in st.session_state:
    st.session_state.kb_version = 0
if "chat_msgs" not in st.session_state:
    st.session_state.chat_msgs = []          # [{role, text, expl}]
if "highlight" not in st.session_state:
    st.session_state.highlight = []

kb: KnowledgeBase = st.session_state.kb
engine = ReasoningEngine(kb)
bot = Chatbot(kb)


def touch() -> None:
    """Call after any KB change so cached views rebuild."""
    st.session_state.kb_version += 1


def kb_json() -> str:
    return json.dumps(kb.to_dict(), sort_keys=True)


def page_guard(fn):
    """Run a page; show a friendly error instead of a raw traceback page."""
    try:
        fn()
    except Exception:
        st.error("Something went wrong on this page. Try resetting the KB, "
                 "or see the technical details below.")
        with st.expander("Technical details"):
            st.code(traceback.format_exc())
        if st.button("↺ Reset sample data", key="guard-reset"):
            st.session_state.kb = load_sample_kb(); touch(); st.rerun()


def build_report() -> str:
    """A Markdown summary of the whole KB - stats, leaders, demand, health."""
    s = kb.stats(); issues = detect_contradictions(kb)
    lines = ["# KnowLogic AI — Knowledge Base Report", "",
             f"- Students: **{s['students']}** · Instructors: **{s['instructors']}** · "
             f"Courses: **{s['courses']}** · Total facts: **{s['total_facts']}**",
             f"- Consistency: **{'CONSISTENT (0 issues)' if not issues else f'{len(issues)} issue(s)'}**",
             "", "## Top students (by completed credits)"]
    lines += [f"{i}. {n} — {cr} credits, {c} courses" for i, (n, cr, c) in enumerate(engine.top_students(5), 1)]
    lines += ["", "## Most in-demand courses"]
    lines += [f"- {c} ({kb.courses[c].title}): {n} enrolments" for c, n in list(engine.course_demand().items())[:5]]
    lines += ["", "## Instructor workload"]
    lines += [f"- {r['instructor']}: {r['course_count']} courses, {r['students_taught']} students"
              for r in engine.instructor_workload()]
    return "\n".join(lines)


def fmt_answer(ans) -> str:
    """Human-readable rendering for engine answers."""
    if isinstance(ans, bool):
        return "✅ Yes" if ans else "❌ No"
    if isinstance(ans, (list, tuple, set)):
        return ", ".join(str(x) for x in ans) if ans else "— none —"
    if isinstance(ans, dict):
        if not ans:
            return "— none —"
        return "\n".join(f"- **{k}**: {', '.join(map(str, v)) if isinstance(v, (list, tuple, set)) else v}"
                         for k, v in ans.items())
    return str(ans)


# ------------------------------------------------------------------ sidebar
PAGES = ["📊 Dashboard", "💬 Chatbot", "🕸️ Knowledge Graph", "🔍 Reasoning Explorer",
         "🎓 Student Insights", "🔮 What-If Simulator", "🗄️ Knowledge Base", "🦉 Ontology",
         "⚠️ Contradictions"]

with st.sidebar:
    st.markdown("## 🧠 KnowLogic AI")
    st.caption("Knowledge Representation & Reasoning\nUniversity domain · FOL + Prolog + OWL")
    page = st.radio("Navigate", PAGES, key="nav_page", label_visibility="collapsed")
    st.divider()
    ok, backend = PrologBridge().available()
    if ok:
        st.success(f"Prolog backend: {backend}")
    else:
        st.info("Python mirror engine active (same rules as university.pl). "
                "Install SWI-Prolog + pyswip for the real Prolog bridge.")
    s = kb.stats()
    st.caption(f"KB: {s['students']} students · {s['instructors']} instructors · "
               f"{s['courses']} courses · {s['total_facts']} facts")
    if st.button("↺ Reset sample data", width="stretch"):
        st.session_state.kb = load_sample_kb(); st.session_state.chat_msgs = []
        st.session_state.highlight = []; touch(); st.rerun()
    st.caption("v4.1 · Streamlit + SWI-Prolog + NetworkX + RDFLib")


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="kl-hero"><h1>{title}</h1><p>{subtitle}</p></div>',
                unsafe_allow_html=True)


# ------------------------------------------------------------------ Dashboard
def page_dashboard() -> None:
    hero("🧠 KnowLogic <span class='gold'>AI</span>",
         "Rule-based chatbot · Prolog reasoning engine · Interactive knowledge graph · OWL ontology — "
         "every answer backed by a proof.")
    s = kb.stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Students", s["students"]); c2.metric("Instructors", s["instructors"])
    c3.metric("Courses", s["courses"]); c4.metric("Total facts", s["total_facts"])

    # --- global search across students, instructors and courses ---
    def _open_student(sid_: str) -> None:
        st.session_state["insight-student"] = sid_
        st.session_state.nav_page = "🎓 Student Insights"

    def _open_in_graph(node: str) -> None:
        st.session_state.highlight = [node]
        st.session_state.nav_page = "🕸️ Knowledge Graph"

    query = st.text_input("🔎 Search the knowledge base", key="dash-search",
                          placeholder="Type a student, instructor or course — e.g. Iqra, Sara, Machine Learning…")
    if query:
        hits = KnowledgeGraph(kb).search(query)[:8]
        if not hits:
            st.info("No matches found.")
        for h in hits:
            if h in kb.students:
                st.button(f"🎓 {kb.students[h].name} — Student · Sem {kb.students[h].semester}",
                          key=f"hit-{h}", on_click=_open_student, args=(h,))
            elif h in kb.instructors:
                r = [x for x in engine.instructor_workload() if x["id"] == h][0]
                st.button(f"👩‍🏫 {kb.instructors[h].name} — Instructor · {r['course_count']} courses · "
                          f"{r['students_taught']} students (view in graph)",
                          key=f"hit-{h}", on_click=_open_in_graph, args=(h,))
            elif h in kb.courses:
                st.button(f"📘 {h} — {kb.courses[h].title} · {len(kb.students_in_course(h))} enrolled (view in graph)",
                          key=f"hit-{h}", on_click=_open_in_graph, args=(h,))

    issues = detect_contradictions(kb)
    if issues:
        st.warning(f"⚠️ {len(issues)} contradiction(s) detected in the KB — "
                   "open the Contradictions page for details.")
    else:
        st.success("✅ Knowledge base is fully consistent — 0 contradictions.")

    # --- meaningful insights, all derived live from KB facts ---
    demand = engine.course_demand()
    top_course, top_n = next(iter(demand.items()))
    tops = engine.top_students(1)
    avg_pct = round(sum(engine.degree_progress(sid).answer["percent"]
                        for sid in kb.students) / max(len(kb.students), 1), 1)
    i1, i2, i3 = st.columns(3)
    i1.markdown(f'<div class="kl-insight">🔥 Most in-demand course<b>{top_course} — {kb.courses[top_course].title}</b>'
                f'{top_n} students enrolled right now</div>', unsafe_allow_html=True)
    i2.markdown(f'<div class="kl-insight">🏆 Top student<b>{tops[0][0]}</b>'
                f'{tops[0][1]} credits · {tops[0][2]} courses completed</div>', unsafe_allow_html=True)
    i3.markdown(f'<div class="kl-insight">🎓 Average degree progress<b>{avg_pct}%</b>'
                f'across all {len(kb.students)} students</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🎓 Degree progress by student")
        prog = sorted(((engine.degree_progress(sid).answer, kb.students[sid].name)
                       for sid in kb.students), key=lambda x: -x[0]["percent"])
        for a, name in prog:
            st.progress(a["percent"] / 100,
                        text=f"{name} — {a['percent']}% ({a['completed_credits']}/{a['total_credits']} cr)")
    with col_b:
        st.subheader("🏆 Leaderboard — most credits completed")
        st.dataframe([{"Student": n, "Credits": cr, "Courses done": c}
                      for n, cr, c in engine.top_students(5)],
                     width="stretch", hide_index=True)
        st.subheader("📈 Enrollments per course")
        st.bar_chart({code: len(kb.students_in_course(code)) for code in sorted(kb.courses)})

    st.subheader("⚙️ Reasoning rules (R1–R10)")
    with st.expander("View all rules (Prolog form)"):
        for rid, rule in RULES.items():
            st.code(f"{rid}: {rule}", language="prolog")

    st.subheader("💬 Try the chatbot")
    samples = ["Can Ali take AI301?", "Recommend courses for Hassan",
               "How can Hassan reach Deep Learning?", "Who teaches Machine Learning?",
               "What is Iqra's degree progress?", "Who are Zara's classmates?",
               "Any problems in the knowledge base?"]
    def _goto_chat(q: str) -> None:  # on_click callback: widget state may only be changed here
        st.session_state.pending_q = q
        st.session_state.nav_page = "💬 Chatbot"

    cols = st.columns(3)
    for i, q in enumerate(samples):
        cols[i % 3].button(q, key=f"sample-{i}", width="stretch",
                           on_click=_goto_chat, args=(q,))
    st.caption("Clicking a question runs it directly on the Chatbot page.")


# ------------------------------------------------------------------ Chatbot
def _ask_and_store(q: str) -> None:
    res = bot.ask(q)
    st.session_state.chat_msgs.append({"role": "user", "text": q, "expl": None})
    st.session_state.chat_msgs.append({
        "role": "assistant", "text": res.answer,
        "expl": res.explanation.render() if res.explanation else None})
    st.session_state.highlight = res.highlight_nodes


def page_chatbot() -> None:
    hero("💬 Chatbot", "Logic-based answers — no LLM guessing. Every answer is built from KB facts and rules.")
    if "pending_q" in st.session_state:
        _ask_and_store(st.session_state.pop("pending_q")); st.rerun()

    for m in st.session_state.chat_msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["text"])
            if m.get("expl"):
                with st.expander("🔍 Reasoning — facts, rules & steps"):
                    st.code(m["expl"])

    if not st.session_state.chat_msgs:
        st.info("Example: `Can Ayesha take AI401?` · `What are the prerequisites of AI301?` · "
                "`Recommend courses for Ali` · `Which students does Dr. Sara teach?`")

    q = st.chat_input("Type your question… e.g. Can Ali take AI301?")
    if q:
        _ask_and_store(q); st.rerun()
    if st.session_state.highlight:
        st.caption(f"🕸️ Graph highlight ready: {st.session_state.highlight} — see it on the Knowledge Graph page.")
    if st.session_state.chat_msgs and st.button("🗑️ Clear chat"):
        st.session_state.chat_msgs = []; st.rerun()


# ------------------------------------------------------------------ Graph
@st.cache_data(show_spinner=False)
def _graph_html(kb_json_str: str, highlight_key: str) -> str:
    kb2 = KnowledgeBase.from_dict(json.loads(kb_json_str))
    g = KnowledgeGraph(kb2)
    hl = g.highlight_for_query(highlight_key.split(",")) if highlight_key else None
    return g.to_pyvis_html(highlight=hl)


def _graph_dot(highlight: set[str]) -> str:
    g = KnowledgeGraph(kb)
    colors = {"student": "#4C9AFF", "instructor": "#FFAB00", "course": "#36B37E",
              "department": "#8777D9"}
    lines = ['digraph KG { rankdir=LR; bgcolor="#0b1526"; node [style=filled, fontcolor=white]; '
             'edge [color="#64748b"];']
    for nid, n in g.nodes.items():
        col = "#FF5630" if nid in highlight else colors[n["type"]]
        label = n["label"].replace('"', "'").replace("\n", "\\n")
        lines.append(f'"{nid}" [label="{label}", fillcolor="{col}"];')
    for a, b, rel in g.edges:
        hot = a in highlight and b in highlight
        lines.append(f'"{a}" -> "{b}" [label="{rel}", color="{"#FF5630" if hot else "#64748b"}", '
                     f'fontcolor="#aebedd"];')
    lines.append("}")
    return "\n".join(lines)


def page_graph() -> None:
    hero("🕸️ Knowledge Graph", "Searchable nodes · relationships · query-based highlighting.")
    g = KnowledgeGraph(kb)
    view = st.radio("View", ["Interactive (PyVis)", "Static (Graphviz)"], horizontal=True)
    use_hl = st.checkbox("Highlight last chatbot / reasoning query",
                         value=bool(st.session_state.highlight))
    hl = g.highlight_for_query(st.session_state.highlight) if use_hl else set()

    if view.startswith("Interactive"):
        try:
            html = _graph_html(kb_json(), ",".join(sorted(hl)) if use_hl else "")
            st.iframe(html, height=640)
            st.download_button("⬇️ Download interactive graph (HTML)", html,
                               "knowlogic_graph.html", mime="text/html")
        except RuntimeError as e:
            st.error(str(e))
    else:
        st.graphviz_chart(_graph_dot(hl), width="stretch")
        st.caption("Static view — no external scripts, always renders.")

    st.divider()
    query = st.text_input("🔎 Search nodes", placeholder="e.g. Ali, AI301, Sara, Mathematics")
    if query:
        hits = g.search(query)
        if not hits:
            st.warning("No matching nodes found.")
        for h in hits:
            with st.expander(f"{h} — {g.nodes[h]['type']}"):
                nb = g.neighbours(h)
                st.write("**Outgoing:**", nb["outgoing"] or "—")
                st.write("**Incoming:**", nb["incoming"] or "—")
    st.markdown("**Legend:** "
                '<span class="kl-chip">🔵 Student</span><span class="kl-chip">🟡 Instructor</span>'
                '<span class="kl-chip">🟢 Course</span><span class="kl-chip">🟣 Department</span>'
                '<span class="kl-chip">🔴 Highlighted</span>', unsafe_allow_html=True)


# ------------------------------------------------------------------ Reasoning
def page_reasoning() -> None:
    hero("🔍 Reasoning Explorer", "Run any query — and get the full proof trace behind the answer.")
    sid = st.selectbox("Student", [s.id for s in kb.students.values()],
                       format_func=lambda x: kb.students[x].name)
    code = st.selectbox("Course", sorted(kb.courses),
                        format_func=lambda x: f"{x} — {kb.courses[x].title}")
    mode = st.radio("Query", ["Eligibility", "Missing prerequisites", "Recommendations",
                              "Course path", "Instructors of student", "Classmates"],
                    horizontal=True)
    if st.button("▶ Run query", type="primary"):
        if mode == "Eligibility": ex = engine.eligible(sid, code)
        elif mode == "Missing prerequisites": ex = engine.missing_prereqs(sid, code)
        elif mode == "Recommendations": ex = engine.recommended_courses(sid)
        elif mode == "Course path": ex = engine.course_path(sid, code)
        elif mode == "Instructors of student": ex = engine.instructors_of_student(sid)
        else: ex = engine.classmates(sid)
        st.markdown(f"### Answer\n{fmt_answer(ex.answer)}")
        with st.expander("🧾 Proof trace — steps, facts, rules", expanded=True):
            st.code(ex.render())
        st.download_button("⬇️ Download proof trace (.txt)", ex.render(),
                           "proof_trace.txt", mime="text/plain")
        st.session_state.highlight = [sid, code]

    with st.expander("📜 university.pl — the real SWI-Prolog file"):
        pl_path = APP_DIR / "knowlogic" / "prolog" / "university.pl"
        if pl_path.exists():
            pl = pl_path.read_text(encoding="utf-8")
            st.code(pl, language="prolog")
            st.download_button("⬇️ Download university.pl", pl, "university.pl")
        else:
            st.warning("university.pl was not found.")


# ------------------------------------------------------------------ What-If
def page_whatif() -> None:
    hero("🔮 What-If Simulator",
         "Hypothetical reasoning: pretend a student completes some courses and see what changes — "
         "the real knowledge base is never modified.")
    sid = st.selectbox("Student", [s.id for s in kb.students.values()],
                       format_func=lambda x: kb.students[x].name, key="whatif-student")
    candidates = [c for c in sorted(kb.courses) if c not in kb.completed_courses(sid)]
    default = [c for c in kb.enrolled_courses(sid)]
    picks = st.multiselect("Pretend these courses are completed", candidates, default=default,
                           format_func=lambda c: f"{c} — {kb.courses[c].title}", key="whatif-courses")
    if st.button("▶️ Run simulation", type="primary", key="whatif-run"):
        st.session_state["whatif-result"] = engine.simulate_completion(sid, picks)
    res = st.session_state.get("whatif-result")
    if res:
        b, a = res["before"], res["after"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Progress before", f"{b['percent']}%")
        m2.metric("Progress after", f"{a['percent']}%", delta=f"{round(a['percent'] - b['percent'], 1)}%")
        m3.metric("Credits after", f"{a['completed_credits']}/{a['total_credits']}")
        st.progress(a["percent"] / 100)
        if res["newly_eligible"]:
            st.success("Newly eligible courses: " +
                       ", ".join(f"**{c}** ({kb.courses[c].title})" for c in res["newly_eligible"]))
        else:
            st.info("No new course becomes eligible with this combination — check the missing prerequisites.")
        st.caption("Simulation ran on an in-memory copy of the KB. Nothing was saved or changed.")


# ------------------------------------------------------------------ Student Insights
def page_insights() -> None:
    hero("🎓 Student Insights", "A complete logical profile of a student — progress, transcript, recommendations.")
    sid = st.selectbox("Student", [s.id for s in kb.students.values()],
                       format_func=lambda x: f"{kb.students[x].name} · Sem {kb.students[x].semester} · "
                                             f"{kb.students[x].department}", key="insight-student")
    a = engine.degree_progress(sid).answer
    t = engine.transcript(sid).answer
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Degree progress", f"{a['percent']}%")
    m2.metric("Credits completed", f"{a['completed_credits']}/{a['total_credits']}")
    m3.metric("Courses completed", len(t["completed"]))
    m4.metric("Currently enrolled", len(t["enrolled"]))
    st.progress(a["percent"] / 100)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("✅ Completed")
        st.dataframe([{"Code": c, "Course": ti, "Credits": cr} for c, ti, cr in t["completed"]],
                     width="stretch", hide_index=True)
        st.subheader("📚 Currently enrolled")
        st.dataframe([{"Code": c, "Course": ti, "Credits": cr} for c, ti, cr in t["enrolled"]],
                     width="stretch", hide_index=True)
    with c2:
        st.subheader("🎯 Recommended next courses")
        recs = engine.recommended_courses(sid).answer
        if recs:
            for r in recs:
                st.markdown(f"- **{r}** — {kb.courses[r].title} ({kb.courses[r].credits} cr)")
        else:
            st.info("No course is currently eligible — complete the enrolled or missing courses first.")
        st.subheader("🛤️ Remaining for degree")
        st.write(", ".join(a["remaining_courses"]) or "— none —")
        st.subheader("🗺️ Study plan to a target course")
        targets = [c for c in sorted(kb.courses) if c not in kb.completed_courses(sid)]
        target = st.selectbox("Target course", targets, key="insight-target",
                              format_func=lambda c: f"{c} — {kb.courses[c].title}")
        plan = engine.course_path(sid, target).answer
        if plan:
            total_cr = sum(kb.courses[c].credits for c in plan)
            for i, c in enumerate(plan, 1):
                st.markdown(f"{i}. **{c}** — {kb.courses[c].title} ({kb.courses[c].credits} cr)")
            st.caption(f"Plan length: {len(plan)} course(s) · {total_cr} credits until {target}.")
        else:
            st.success("Target already completed.")
        mates = engine.classmates(sid).answer
        st.subheader("👥 Classmates")
        st.write(fmt_answer(mates))
    with st.expander("🧾 Proof traces (progress + transcript)"):
        st.code(engine.degree_progress(sid).render())
        st.code(engine.transcript(sid).render())
    def _goto_graph() -> None:  # on_click callback — widget state may only be changed here
        st.session_state.highlight = [sid]
        st.session_state.nav_page = "🕸️ Knowledge Graph"

    st.button("🕸️ View this student in the graph", key="insight-graph", on_click=_goto_graph)


# ------------------------------------------------------------------ KB manager
def page_kb() -> None:
    hero("🗄️ Knowledge Base Manager", "Add or delete facts — the chatbot, graph and checks update immediately.")
    t1, t2, t3, t4 = st.tabs(["➕ Student", "➕ Course", "🔗 Relation", "📋 Facts / Backup"])
    with t1:
        with st.form("add_student"):
            sid = st.text_input("ID (e.g. bilal2)"); name = st.text_input("Full name")
            dept = st.selectbox("Department", ["Computer Science", "Artificial Intelligence", "Mathematics"])
            sem = st.number_input("Semester", 1, 8, 1)
            if st.form_submit_button("Add student"):
                try:
                    kb.add_student(Student(sid.strip(), name.strip(), dept, int(sem)))
                    touch(); st.success(f"Student {name} added."); st.rerun()
                except Exception as e: st.error(str(e))
    with t2:
        with st.form("add_course"):
            cc = st.text_input("Code (e.g. CS401)"); title = st.text_input("Title")
            dept = st.selectbox("Dept", ["Computer Science", "Artificial Intelligence", "Mathematics"])
            credits = st.number_input("Credits", 1, 6, 3)
            pre = st.multiselect("Prerequisites", sorted(kb.courses))
            if st.form_submit_button("Add course"):
                try:
                    kb.add_course(Course(cc.strip().upper(), title.strip(), dept, int(credits)))
                    for p in pre: kb.add_prerequisite(cc.strip().upper(), p)
                    touch(); st.success(f"Course {cc} added."); st.rerun()
                except Exception as e: st.error(str(e))
    with t3:
        kind = st.selectbox("Relation", ["completed", "enrolled", "teaches", "prerequisite"])
        a_options = sorted(kb.students) if kind in ("completed", "enrolled") else \
            sorted(kb.instructors) if kind == "teaches" else sorted(kb.courses)
        a = st.selectbox("From", a_options); b = st.selectbox("To (course)", sorted(kb.courses))
        if st.button("Add relation", type="primary"):
            try:
                {"completed": kb.add_completed, "enrolled": kb.add_enrolled,
                 "teaches": kb.add_teaches, "prerequisite": kb.add_prerequisite}[kind](a, b)
                touch(); st.success(f"{kind}({a}, {b}) added."); st.rerun()
            except Exception as e: st.error(str(e))
    with t4:
        s = kb.stats()
        st.caption(f"{s['total_facts']} facts · {s['completed_facts']} completed · "
                   f"{s['enrollments']} enrolled · {s['teaches_facts']} teaches · "
                   f"{s['prerequisite_rules']} prerequisites")
        for kind, store in [("completed", kb.completed), ("enrolled", kb.enrolled),
                            ("teaches", kb.teaches), ("prerequisite", kb.prerequisites)]:
            with st.expander(f"{kind} ({len(store)})"):
                for a, b in sorted(store):
                    c1, c2 = st.columns([5, 1])
                    c1.write(f"`{kind}({a}, {b})`")
                    if c2.button("Delete", key=f"del-{kind}-{a}-{b}"):
                        kb.remove_relation(kind, a, b); touch(); st.rerun()
        st.divider()
        st.download_button("⬇️ Download KB backup (JSON)",
                           json.dumps(kb.to_dict(), indent=2),
                           "knowlogic_kb.json", mime="application/json")
        st.download_button("📄 Download KB report (Markdown)", build_report(),
                           "knowlogic_report.md", mime="text/markdown")
        st.subheader("👩‍🏫 Instructor workload")
        st.dataframe([{"Instructor": r["instructor"], "Courses": r["course_count"],
                       "Students taught": r["students_taught"], "Enrolments": r["enrolments"],
                       "Course list": ", ".join(r["courses"])} for r in engine.instructor_workload()],
                     width="stretch", hide_index=True)
        up = st.file_uploader("Restore KB from JSON backup", type=["json"])
        if up and st.button("Restore uploaded KB"):
            try:
                data = json.loads(up.read().decode("utf-8"))
                st.session_state.kb = KnowledgeBase.from_dict(data)
                touch(); st.success("KB restored."); st.rerun()
            except Exception as e: st.error(f"Restore failed: {e}")


# ------------------------------------------------------------------ Ontology
def page_ontology() -> None:
    hero("🦉 Ontology (Protégé / OWL)", "The same KB in OWL form — opens directly in Protégé.")
    ttl = kb_to_turtle(kb)
    try:
        info = parse_ontology(ttl)
        m1, m2, m3 = st.columns(3)
        m1.metric("RDF triples", info["triples"]); m2.metric("Classes", len(info["classes"]))
        m3.metric("Properties", len(info["properties"]))
    except RuntimeError:
        st.caption("rdflib is not available — Turtle export still works.")
    st.text_area("university.ttl (preview)", ttl, height=320)
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Download university.ttl", ttl, "university.ttl", mime="text/turtle")
    try:
        c2.download_button("⬇️ Download university.owl (RDF/XML)", export_owl_xml(kb),
                           "university.owl", mime="application/rdf+xml")
    except Exception as e:
        c2.warning(str(e))
    st.caption("Protégé: File → Open → select the file. Classes: Student/Instructor ⊑ Person, Course, Department.")
    st.divider()
    up = st.file_uploader("Upload a .ttl / .owl file to inspect", type=["ttl", "owl", "xml", "rdf"])
    if up:
        raw = up.read().decode("utf-8", errors="ignore")
        summary, last_err = None, None
        for fmt in (["turtle"] if up.name.endswith(".ttl") else ["xml", "turtle"]):
            try: summary = parse_ontology(raw, fmt=fmt); break
            except Exception as e: last_err = e
        if summary:
            st.success(f"Parsed: {summary['triples']} triples · {len(summary['classes'])} classes · "
                       f"{len(summary['properties'])} properties · {summary['individuals_count']} individuals")
            st.write("**Classes:**", summary["classes"])
            st.write("**Properties:**", summary["properties"])
        else:
            st.error(f"Parse failed: {last_err}")


# ------------------------------------------------------------------ Contradictions
FIX_HINTS = {
    "enrolled_without_prereq": "Fix: delete this enrolment on the Knowledge Base page, or complete the prerequisites first.",
    "completed_and_enrolled": "Fix: delete one of the two relations on the Knowledge Base page.",
    "prereq_cycle": "Fix: remove the prerequisite relation that closes the cycle, on the Knowledge Base page.",
    "course_without_instructor": "Fix: add a teaches relation on the Knowledge Base page.",
    "instructor_overload": "Fix: reassign some courses to another instructor.",
}


def page_contradictions() -> None:
    hero("⚠️ Contradiction Detection", "Knowledge base consistency checks — every issue comes with its fix.")
    issues = detect_contradictions(kb)
    errors = sum(1 for i in issues if i["severity"] == "error")
    m1, m2 = st.columns(2)
    m1.metric("Total issues", len(issues)); m2.metric("Errors", errors)
    if not issues:
        st.success("✅ No contradictions — the knowledge base is consistent.")
    for i in issues:
        box = st.error if i["severity"] == "error" else st.warning
        box(f"**[{i['type']}]** {i['message']}\n\n💡 {FIX_HINTS.get(i['type'], '')}")
    st.caption("Checks: enrolled-without-prerequisite · completed+enrolled overlap · prerequisite cycles · "
               "course without instructor · instructor overload (>4 courses). "
               "The sample data is fully consistent — but as soon as a wrong relation is added, "
               "this page will catch it immediately (verified by tests that inject a violation).")


# ------------------------------------------------------------------ router
ROUTER = {"📊 Dashboard": page_dashboard, "💬 Chatbot": page_chatbot,
          "🕸️ Knowledge Graph": page_graph, "🔍 Reasoning Explorer": page_reasoning,
          "🎓 Student Insights": page_insights, "🔮 What-If Simulator": page_whatif,
          "🗄️ Knowledge Base": page_kb, "🦉 Ontology": page_ontology,
          "⚠️ Contradictions": page_contradictions}
page_guard(ROUTER[page])

st.divider()
st.caption("KnowLogic AI · Knowledge Representation & Reasoning · "
           "Muhammad Adnan — BS AI, Hazara University · "
           "[Live demo](https://knowlogic-ai.streamlit.app/)")
