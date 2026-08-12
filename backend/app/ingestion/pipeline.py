"""Ingestion pipeline: transcript text -> parsed -> chunked -> embedded -> stored.

One entry point that ties the ingestion steps together, so the API layer just
calls ingest() without knowing the internals.
"""

from app.core.bedrock import embed_texts
from app.ingestion.chunker import chunk_turns
from app.ingestion.parser import parse_transcript
from app.retrieval.store import delete_meeting, store_chunks


def ingest(meeting_id: str, transcript_text: str) -> int:
    """Ingest a transcript for a meeting; returns the number of chunks stored.

    Re-ingesting the same meeting_id replaces its chunks (idempotent).
    """
    turns = parse_transcript(transcript_text)
    chunks = chunk_turns(turns)
    embeddings = embed_texts([c.text for c in chunks])

    delete_meeting(meeting_id)
    store_chunks(meeting_id, chunks, embeddings)
    return len(chunks)
