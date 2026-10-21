<div align="center">

<img src="assets/banner.gif" alt="Knowledge Representation and Reasoning — First-Order Logic, Prolog, OWL Ontology, KnowLogic AI" width="100%"/>

# Knowledge Representation & Reasoning (KRR)

**First-Order Logic · Prolog · OWL Ontologies (Protégé) · Knowledge Graphs · Explainable AI**

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-KnowLogic_AI-brightgreen?style=for-the-badge)](https://knowlogic-ai.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)
![SWI-Prolog](https://img.shields.io/badge/SWI--Prolog-9.x-red?style=for-the-badge)
![Protégé](https://img.shields.io/badge/Protégé-OWL_2-8c1515?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

</div>

Hands-on **Knowledge Representation and Reasoning** in Python, Prolog and OWL — knowledge bases, logical inference, unification, resolution, description logic and ontology engineering — ending in **KnowLogic AI**, a complete reasoning project with a live demo.

---

## 🚀 Featured Project — KnowLogic AI

An intelligent university advisor that answers by **logic, not guesswork** — every answer comes with its proof (facts + rules + inference steps).

- 💬 Rule-based **chatbot** (no LLM reasoning) · ⚙️ **Prolog reasoning engine** (8 rules: eligibility, prerequisites, recommendations, study paths) · 🕸️ Interactive **knowledge graph** · 🦉 **OWL ontology** · ⚠️ Contradiction detection

**▶ Try it live: [knowlogic-ai.streamlit.app](https://knowlogic-ai.streamlit.app/)** · Source: [`4-project/`](https://github.com/AdnanCodex/knowledge-representation-and-reasoning/tree/main/4-project)

---

## 📚 Contents

| # | Part | Topics | Open |
|---|---|---|---|
| 1 | **First-Order Logic** | Knowledge bases, propositional logic, truth tables, CNF, entailment, unification (MGU), resolution refutation | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AdnanCodex/knowledge-representation-and-reasoning/blob/main/1-first-order-logic/first_order_logic.ipynb) |
| 2 | **Prolog** | Facts & rules, unification, SLD resolution, negation as failure, recursion | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AdnanCodex/knowledge-representation-and-reasoning/blob/main/2-prolog/prolog_logic_programming.ipynb) |
| 3 | **Protégé (OWL)** | OWL ontologies, description logic, HermiT reasoner, SPARQL, open vs closed world | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AdnanCodex/knowledge-representation-and-reasoning/blob/main/3-protege/protege_ontologies.ipynb) |
| 4 | **Project — KnowLogic AI** | Chatbot + Prolog engine + knowledge graph + OWL ontology, explainable reasoning | [📂 Folder](https://github.com/AdnanCodex/knowledge-representation-and-reasoning/tree/main/4-project) · [🚀 Live](https://knowlogic-ai.streamlit.app/) |

**Concepts at a glance:** `∀x (Human(x) → Mortal(x))` in FOL = `mortal(X) :- human(X).` in Prolog = `Human ⊑ Mortal` in OWL — the same knowledge, three representations, one inference idea.

---

## ⚡ Quick Start

```bash
git clone https://github.com/AdnanCodex/knowledge-representation-and-reasoning.git
cd knowledge-representation-and-reasoning

# Notebooks (Parts 1–3): open in Jupyter or via the Colab badges above
pip install sympy owlready2 rdflib jupyter

# Project (Part 4): KnowLogic AI
cd 4-project && pip install -r requirements.txt
python -m unittest discover -s tests -v   # 28 tests
streamlit run app.py                      # or use the live demo
```

<details>
<summary>🗂️ Repository structure</summary>

```
├── 1-first-order-logic/   FOL, propositional logic, resolution (2 notebooks)
├── 2-prolog/              Prolog programming (1 notebook + 3 .pl programs)
├── 3-protege/             OWL ontologies (notebook + 2 .owl files)
└── 4-project/             KnowLogic AI — Python package `knowlogic/`,
                           SWI-Prolog rules, Streamlit app, tests, ontology (.ttl)
```
</details>

---

## 🔑 Keywords

`knowledge-representation` · `knowledge-reasoning` · `first-order-logic` · `prolog` · `logic-programming` · `unification` · `resolution` · `owl-ontology` · `protege` · `description-logic` · `hermit-reasoner` · `sparql` · `expert-system` · `knowledge-graph` · `explainable-ai` · `rule-based-chatbot` · `streamlit`

## 👤 Author

**Muhammad Adnan** — BS Artificial Intelligence, Hazara University, Mansehra · CGPA 3.95/4.0 · 1st in class · COO @ Capinex · Data Science Intern & QA @ DigiSync

[![GitHub](https://img.shields.io/badge/GitHub-AdnanCodex-181717?logo=github&logoColor=white)](https://github.com/AdnanCodex) [![LinkedIn](https://img.shields.io/badge/LinkedIn-adnan--ai-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/adnan-ai) [![Email](https://img.shields.io/badge/Email-adnan906132%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:adnan906132@gmail.com)
