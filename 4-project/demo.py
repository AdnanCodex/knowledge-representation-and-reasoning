"""Terminal demo - no Streamlit needed.
Run:  python demo.py            (asks sample questions and prints proof traces)
      python demo.py "Can Zara take AI401?"
"""
import sys
from knowlogic.kb import load_sample_kb
from knowlogic.chatbot import Chatbot

QUESTIONS = [
    "Can Ali take AI301?",
    "Recommend courses for Hassan",
    "How can Hassan reach Deep Learning?",
    "Who teaches Machine Learning?",
    "Which students does Dr. Sara teach?",
    "Any problems in the knowledge base?",
]

if __name__ == "__main__":
    bot = Chatbot(load_sample_kb())
    for q in (sys.argv[1:] or QUESTIONS):
        r = bot.ask(q)
        print(f"\nQ: {q}\nA: {r.answer}")
        if r.explanation:
            print(r.explanation.render())
