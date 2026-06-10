"""Interactive QA over the indexed paper corpus.

Usage:
    PYTHONPATH=src uv run python script/ask.py
    PYTHONPATH=src uv run python script/ask.py "Who authored the paper 'X'?"
"""
from __future__ import annotations

import sys

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _ask(question: str) -> None:
    settings = load_settings()
    index = LocalEmbeddingIndex.load(settings)

    result = answer_question(question, settings=settings, index=index)

    print(f"\nQ: {result.question}")
    print(f"A: {result.answer}")
    print(f"\nSources retrieved ({len(result.retrieved_titles)}):")
    for i, title in enumerate(result.retrieved_titles, 1):
        print(f"  {i}. {title}")


def _interactive() -> None:
    settings = load_settings()
    print(f"[ask] Loaded index — {settings.embedding_model}")
    index = LocalEmbeddingIndex.load(settings)
    print("Type a question and press Enter. Empty line to quit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not question:
            print("Bye!")
            break

        result = answer_question(question, settings=settings, index=index)
        print(f"Bot: {result.answer}")
        print(f"     (from: {result.retrieved_titles[0] if result.retrieved_titles else 'N/A'})\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _ask(" ".join(sys.argv[1:]))
    else:
        _interactive()
