"""Run:  python -m unittest discover -s tests -v   (no extra deps needed)"""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowlogic.kb import load_sample_kb
from knowlogic.engine import ReasoningEngine
from knowlogic.chatbot import Chatbot
from knowlogic.graph_builder import KnowledgeGraph
from knowlogic.ontology import kb_to_turtle
from knowlogic.contradictions import detect_contradictions


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.kb = load_sample_kb(); self.e = ReasoningEngine(self.kb)

    def test_missing_prereqs(self):
        self.assertEqual(self.e.missing_prereqs("ali", "AI301").answer, ["CS201", "MATH201"])
        self.assertEqual(self.e.missing_prereqs("ayesha", "AI301").answer, [])

    def test_eligibility(self):
        self.assertTrue(self.e.eligible("ayesha", "AI302").answer is False)  # AI301 not completed yet
        self.assertTrue(self.e.eligible("hassan", "CS102").answer is False)  # already enrolled
        self.assertTrue(self.e.eligible("hassan", "CS201").answer is False)  # CS102 missing
        self.assertTrue(self.e.eligible("zara", "CS305").answer)             # CS102 done
        self.assertFalse(self.e.eligible("ali", "AI301").answer)

    def test_transitive_prereqs(self):
        self.assertEqual(self.e.all_prereqs("AI401").answer,
                         ["AI301", "CS101", "CS102", "CS201", "MATH101", "MATH201"])

    def test_course_path_order(self):
        path = self.e.course_path("hassan", "AI401").answer
        # har course apne prereq ke BAAD aye
        pos = {c: i for i, c in enumerate(path)}
        for course, pre in self.kb.prerequisites:
            if course in pos and pre in pos:
                self.assertLess(pos[pre], pos[course])
        self.assertNotIn("CS101", path)  # hassan already completed it

    def test_instructor_student_inverse(self):
        ins = self.e.instructors_of_student("ayesha").answer
        self.assertIn("Dr. Sara Malik", ins)
        studs = self.e.students_of_instructor("dr_sara").answer
        self.assertIn("AI301", studs); self.assertIn("Ayesha Khan", studs["AI301"])

    def test_classmates(self):
        mates = self.e.classmates("ali").answer
        self.assertEqual(mates.get("CS201"), ["Hamza Sheikh", "Kinza Tariq", "Zara Iqbal"])

    def test_recommendations(self):
        recs = self.e.recommended_courses("zara").answer
        self.assertIn("CS305", recs); self.assertNotIn("CS201", recs)  # enrolled already

    def test_explanation_has_trace(self):
        ex = self.e.eligible("ali", "AI301")
        self.assertTrue(ex.steps and ex.facts_used and ex.rules_fired)


class TestPowerFeatures(unittest.TestCase):
    def setUp(self):
        self.kb = load_sample_kb(); self.e = ReasoningEngine(self.kb)

    def test_degree_progress(self):
        a = self.e.degree_progress("ayesha").answer
        self.assertEqual((a["completed_credits"], a["total_credits"]), (15, 47))
        self.assertEqual(a["percent"], 31.9)

    def test_transcript(self):
        t = self.e.transcript("iqra").answer
        self.assertIn("AI301", [c for c, _, _ in t["completed"]])
        self.assertEqual([c for c, _, _ in t["enrolled"]], ["AI302", "AI401"])

    def test_course_demand(self):
        d = self.e.course_demand()
        self.assertEqual(next(iter(d.items())), ("CS201", 4))

    def test_top_students(self):
        tops = self.e.top_students(3)
        self.assertEqual(tops[0][0], "Iqra Aziz"); self.assertEqual(tops[0][1], 18)
        self.assertEqual(tops[1][0], "Ayesha Khan")

    def test_instructor_workload(self):
        w = self.e.instructor_workload()
        self.assertEqual(w[0]["course_count"], 3)  # several instructors teach 3 courses
        sara = [r for r in w if r["id"] == "dr_sara"][0]
        self.assertEqual(sara["students_taught"], 2)  # unique: ayesha (AI301), iqra (AI302+AI401)
        self.assertEqual(sara["enrolments"], 3)

    def test_simulate_completion(self):
        sim = self.e.simulate_completion("ali", ["CS201"])
        self.assertEqual(sim["before"]["percent"], 19.1)
        self.assertEqual(sim["after"]["completed_credits"], 12)
        # ali still misses MATH201 for AI301, so it must NOT be newly eligible:
        self.assertNotIn("AI301", sim["newly_eligible"])
        self.assertIn("CS310", sim["newly_eligible"])  # needs only CS201
        # the real KB is untouched by simulation
        self.assertNotIn("CS201", self.kb.completed_courses("ali"))

    def test_chatbot_progress_and_demand(self):
        bot = Chatbot(self.kb)
        r = bot.ask("What is Iqra's degree progress?")
        self.assertEqual(r.intent, "progress"); self.assertIn("18/47", r.answer)
        r = bot.ask("Which course is most popular?")
        self.assertEqual(r.intent, "demand"); self.assertIn("CS201", r.answer)


class TestChatbot(unittest.TestCase):
    def setUp(self): self.bot = Chatbot(load_sample_kb())

    def test_eligibility_question(self):
        r = self.bot.ask("Can Ali take AI301?")
        self.assertEqual(r.intent, "eligibility"); self.assertIn("No,", r.answer)

    def test_title_based_question(self):
        r = self.bot.ask("Who teaches Machine Learning?")
        self.assertEqual(r.intent, "who_teaches"); self.assertIn("Sara", r.answer)

    def test_path_question(self):
        r = self.bot.ask("How can Hassan reach Deep Learning?")
        self.assertEqual(r.intent, "path"); self.assertIn("CS102", r.answer)

    def test_recommend_question(self):
        r = self.bot.ask("Recommend courses for Zara")
        self.assertEqual(r.intent, "recommend"); self.assertIn("CS305", r.answer)

    def test_classmates_question_possessive(self):
        r = self.bot.ask("Who are Zara's classmates?")
        self.assertEqual(r.intent, "classmates"); self.assertIn("Ali Raza", r.answer)

    def test_unknown_question(self):
        r = self.bot.ask("What is the weather today?")
        self.assertEqual(r.intent, "unknown")

    def test_highlight_nodes_set(self):
        r = self.bot.ask("Can Ayesha take AI302?")
        self.assertIn("AI302", r.highlight_nodes)


class TestGraphOntologyContradictions(unittest.TestCase):
    def setUp(self): self.kb = load_sample_kb()

    def test_graph_search_and_neighbours(self):
        g = KnowledgeGraph(self.kb)
        self.assertIn("ali", g.search("ali"))
        nb = g.neighbours("ali")
        self.assertTrue(any("CS201" in x for x in nb["outgoing"]))

    def test_turtle_export(self):
        ttl = kb_to_turtle(self.kb)
        self.assertIn("uni:AI301 uni:hasPrerequisite uni:CS201", ttl)
        self.assertIn("owl:Class", ttl)

    def test_sample_kb_is_consistent(self):
        self.assertEqual(detect_contradictions(self.kb), [])

    def test_injected_violation_detected_and_fixable(self):
        self.kb.add_enrolled("omar", "AI301")  # omar lacks CS201 + MATH201
        types = [i["type"] for i in detect_contradictions(self.kb)]
        self.assertIn("enrolled_without_prereq", types)
        self.kb.remove_relation("enrolled", "omar", "AI301")
        self.assertEqual(detect_contradictions(self.kb), [])

    def test_expanded_dataset_counts(self):
        s = self.kb.stats()
        self.assertEqual((s["students"], s["instructors"], s["courses"], s["total_facts"]),
                         (12, 6, 15, 113))

    def test_kb_json_roundtrip(self):
        kb2 = type(self.kb).from_dict(self.kb.to_dict())
        self.assertEqual(kb2.stats(), self.kb.stats())


if __name__ == "__main__":
    unittest.main()
