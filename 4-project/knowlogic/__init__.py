"""KnowLogic AI - KRR system: KB + Prolog-style reasoning + graph + ontology."""
from .kb import KnowledgeBase, load_sample_kb
from .engine import ReasoningEngine, Explanation
from .chatbot import Chatbot

__all__ = ["KnowledgeBase", "load_sample_kb", "ReasoningEngine", "Explanation", "Chatbot"]
__version__ = "1.0.0"
