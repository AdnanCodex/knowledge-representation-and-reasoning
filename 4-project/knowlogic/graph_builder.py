"""
Knowledge graph: NetworkX graph built from the KB + PyVis interactive HTML.

Node types: student, instructor, course, department
Edge types: enrolled_in, completed, teaches, prerequisite_of, belongs_to

If networkx / pyvis are not installed, the adjacency data is still
available (search, neighbours, highlight) and the HTML export raises a
clear error telling the user what to install.
"""
from __future__ import annotations

from .kb import KnowledgeBase

COLORS = {"student": "#4C9AFF", "instructor": "#FFAB00", "course": "#36B37E",
          "department": "#8777D9", "highlight": "#FF5630"}


class KnowledgeGraph:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.edges: list[tuple[str, str, str]] = []  # (src, dst, relation)
        self.nodes: dict[str, dict] = {}             # id -> {label, type}
        self._build_data()

    def _add_node(self, nid: str, label: str, ntype: str):
        self.nodes.setdefault(nid, {"label": label, "type": ntype})

    def _build_data(self):
        kb = self.kb
        depts = set()
        for s in kb.students.values():
            self._add_node(s.id, s.name, "student"); depts.add(s.department)
            self.edges.append((s.id, s.department, "belongs_to"))
        for i in kb.instructors.values():
            self._add_node(i.id, i.name, "instructor"); depts.add(i.department)
            self.edges.append((i.id, i.department, "belongs_to"))
        for c in kb.courses.values():
            self._add_node(c.code, f"{c.code}\n{c.title}", "course"); depts.add(c.department)
            self.edges.append((c.code, c.department, "belongs_to"))
        for d in depts:
            self._add_node(d, d, "department")
        for sid, code in kb.enrolled: self.edges.append((sid, code, "enrolled_in"))
        for sid, code in kb.completed: self.edges.append((sid, code, "completed"))
        for iid, code in kb.teaches: self.edges.append((iid, code, "teaches"))
        for code, pre in kb.prerequisites: self.edges.append((pre, code, "prerequisite_of"))

    # ---------- plain-Python queries (no networkx needed) ----------
    def search(self, text: str) -> list[str]:
        t = text.lower()
        return [nid for nid, n in self.nodes.items()
                if t in nid.lower() or t in n["label"].lower()]

    def neighbours(self, nid: str) -> dict[str, list[str]]:
        out, inc = [], []
        for a, b, rel in self.edges:
            if a == nid: out.append(f"{rel} -> {b}")
            if b == nid: inc.append(f"{a} -{rel}->")
        return {"outgoing": out, "incoming": inc}

    def highlight_for_query(self, node_ids: list[str]) -> set[str]:
        """Nodes to highlight: the given ids plus their direct neighbours."""
        hl = {n for n in node_ids if n in self.nodes or n in self.kb.courses or n in self.kb.students}
        # ids may be course codes / student ids, which equal node ids in this graph
        hl = {n for n in node_ids}
        for a, b, _ in self.edges:
            if a in hl: hl.add(b)
            if b in hl: hl.add(a)
        return hl

    # ---------- NetworkX ----------
    def to_networkx(self):
        try:
            import networkx as nx
        except ImportError as e:
            raise RuntimeError("networkx is not installed: pip install networkx") from e
        g = nx.DiGraph()
        for nid, n in self.nodes.items():
            g.add_node(nid, label=n["label"], type=n["type"], color=COLORS[n["type"]])
        for a, b, rel in self.edges:
            g.add_edge(a, b, relation=rel, title=rel)
        return g

    # ---------- PyVis interactive HTML ----------
    def to_pyvis_html(self, highlight: set[str] | None = None, height: str = "620px") -> str:
        try:
            from pyvis.network import Network
        except ImportError as e:
            raise RuntimeError("pyvis is not installed: pip install pyvis") from e
        net = Network(height=height, width="100%", directed=True, bgcolor="#0f172a",
                      font_color="white", notebook=False)
        net.barnes_hut()
        for nid, n in self.nodes.items():
            color = COLORS["highlight"] if highlight and nid in highlight else COLORS[n["type"]]
            size = 28 if highlight and nid in highlight else 18
            net.add_node(nid, label=n["label"], color=color, size=size,
                         title=f"{n['type']}: {n['label']}")
        for a, b, rel in self.edges:
            hot = highlight and a in highlight and b in highlight
            net.add_edge(a, b, title=rel, label=rel if hot else "",
                         color="#FF5630" if hot else "#64748b", width=3 if hot else 1)
        return net.generate_html()
