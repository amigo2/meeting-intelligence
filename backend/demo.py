"""End-to-end demo: ingest a transcript, then retrieve for a question.

Needs the Postgres+pgvector container up (docker compose up -d db) and Bedrock access.
Run from backend/:  python demo.py
"""

from pathlib import Path

from app.generation.answerer import answer
from app.ingestion.pipeline import ingest
from app.retrieval.store import init_db

DATA = Path(__file__).resolve().parent / "data"


def main() -> None:
    init_db()

    transcript = (DATA / "sample_meeting.txt").read_text(encoding="utf-8")
    n = ingest("meeting-1", transcript)
    print(f"Ingested {n} chunks for meeting-1.\n")

    questions = (
        "When is the launch date?",
        "What is Ben responsible for?",
        "What was the marketing budget agreed?",  # not in transcript -> should refuse
    )
    for question in questions:
        result = answer("meeting-1", question)
        print(f"Q: {question}")
        print(f"A: {result['answer']}\n")


if __name__ == "__main__":
    main()
