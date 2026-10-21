"""
Ontology support (Protégé / OWL) via RDFLib, with a manual Turtle
fallback so export works even without rdflib installed.

The ontology models the same university domain:
  Classes:   Person > Student, Instructor; Course; Department
  Properties: enrolledIn, hasCompleted, teaches, hasPrerequisite,
              belongsToDepartment
The generated .ttl / .owl (RDF/XML) files open directly in Protégé.
"""
from __future__ import annotations

from .kb import KnowledgeBase

NS = "http://knowlogic.ai/ontology/university#"


def kb_to_turtle(kb: KnowledgeBase) -> str:
    """Deterministic Turtle built by hand (no dependency needed)."""
    def q(name: str) -> str:
        return "uni:" + "".join(ch if ch.isalnum() else "_" for ch in name)

    L = [f"@prefix uni: <{NS}> .",
         "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
         "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .", "",
         "uni:Person a owl:Class .",
         "uni:Student a owl:Class ; rdfs:subClassOf uni:Person .",
         "uni:Instructor a owl:Class ; rdfs:subClassOf uni:Person .",
         "uni:Course a owl:Class .",
         "uni:Department a owl:Class .", "",
         "uni:enrolledIn a owl:ObjectProperty ; rdfs:domain uni:Student ; rdfs:range uni:Course .",
         "uni:hasCompleted a owl:ObjectProperty ; rdfs:domain uni:Student ; rdfs:range uni:Course .",
         "uni:teaches a owl:ObjectProperty ; rdfs:domain uni:Instructor ; rdfs:range uni:Course .",
         "uni:hasPrerequisite a owl:ObjectProperty ; rdfs:domain uni:Course ; rdfs:range uni:Course .",
         "uni:belongsToDepartment a owl:ObjectProperty ; rdfs:range uni:Department .", ""]
    depts = sorted({s.department for s in kb.students.values()} |
                   {c.department for c in kb.courses.values()})
    for d in depts:
        L.append(f'{q(d)} a uni:Department ; rdfs:label "{d}" .')
    for s in kb.students.values():
        L.append(f'uni:{s.id} a uni:Student ; rdfs:label "{s.name}" ; uni:belongsToDepartment {q(s.department)} .')
    for i in kb.instructors.values():
        L.append(f'uni:{i.id} a uni:Instructor ; rdfs:label "{i.name}" ; uni:belongsToDepartment {q(i.department)} .')
    for c in kb.courses.values():
        L.append(f'uni:{c.code} a uni:Course ; rdfs:label "{c.code} - {c.title}" ; uni:belongsToDepartment {q(c.department)} .')
    for sid, code in sorted(kb.enrolled): L.append(f"uni:{sid} uni:enrolledIn uni:{code} .")
    for sid, code in sorted(kb.completed): L.append(f"uni:{sid} uni:hasCompleted uni:{code} .")
    for iid, code in sorted(kb.teaches): L.append(f"uni:{iid} uni:teaches uni:{code} .")
    for code, pre in sorted(kb.prerequisites): L.append(f"uni:{code} uni:hasPrerequisite uni:{pre} .")
    return "\n".join(L) + "\n"


def parse_ontology(text: str, fmt: str = "turtle") -> dict:
    """Parse an uploaded .ttl/.owl file with RDFLib and summarise it."""
    try:
        from rdflib import Graph, RDF, RDFS, OWL
    except ImportError as e:
        raise RuntimeError("rdflib is not installed: pip install rdflib") from e
    g = Graph(); g.parse(data=text, format=fmt)
    classes = sorted({str(s) for s in g.subjects(RDF.type, OWL.Class)})
    props = sorted({str(s) for s in g.subjects(RDF.type, OWL.ObjectProperty)})
    individuals = sorted({str(s) for s in g.subjects(RDF.type, None)
                          if "#" in str(s) and str(s) not in classes})
    return {"triples": len(g), "classes": classes, "properties": props,
            "individuals_count": len(individuals), "individuals_sample": individuals[:30],
            "graph": g}


def export_owl_xml(kb: KnowledgeBase) -> str:
    """RDF/XML (Protégé-native .owl) via RDFLib when available."""
    try:
        from rdflib import Graph
    except ImportError:
        return kb_to_turtle(kb)  # Turtle is also valid OWL input for Protégé
    g = Graph(); g.parse(data=kb_to_turtle(kb), format="turtle")
    return g.serialize(format="xml")
