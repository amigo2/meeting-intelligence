"""End-to-end demo: ingest a transcript, then retrieve for a question.

Needs the Postgres+pgvector container up (docker compose up -d db) and Bedrock access.
Run from backend/:  python demo.py
"""

from pathlib import Path

from app.ingestion.pipeline import ingest
from app.retrieval.retriever import retrieve
from app.retrieval.store import init_db

DATA = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    init_db()

    transcript = (DATA / "sample_meeting.txt").read_text(encoding="utf-8")
    n = ingest("meeting-1", transcript)
    print(f"Ingested {n} chunks for meeting-1.\n")

    for question in ("When is the launch date?", "What is Ben responsible for?"):
        print(f"Q: {question}")
        for hit in retrieve("meeting-1", question, k=3):
            preview = hit["text"].replace("\n", " ")[:90]
            print(f"  {hit['similarity']:.3f}  [{hit['start']}-{hit['end']}] "
                  f"{hit['speakers']}: {preview}...")
        print()


if __name__ == "__main__":
    main()
