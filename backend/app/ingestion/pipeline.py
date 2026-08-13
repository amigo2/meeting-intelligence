"""Ingestion pipeline: transcript text -> parsed -> chunked -> embedded -> stored.

One entry point that ties the ingestion steps together, so the API layer just
calls ingest() without knowing the internals.
"""

from app.core.bedrock import embed_texts
from app.extraction.extractor import extract
from app.ingestion.chunker import chunk_turns
from app.ingestion.parser import parse_transcript
from app.retrieval.store import replace_chunks, save_meeting


class EmptyTranscriptError(ValueError):
    """Raised when a transcript parses to zero usable turns."""


def ingest(meeting_id: str, transcript_text: str) -> int:
    """Ingest a transcript for a meeting; returns the number of chunks stored.

    Re-ingesting the same meeting_id atomically replaces its chunks. We refuse an
    empty parse and embed BEFORE touching the DB, so a bad upload can never wipe a
    meeting's existing data.
    """
    turns = parse_transcript(transcript_text)
    chunks = chunk_turns(turns)
    if not chunks:
        raise EmptyTranscriptError("Transcript produced no parseable turns; nothing to ingest.")

    embeddings = embed_texts([c.text for c in chunks])  # if this fails, DB is untouched
    replace_chunks(meeting_id, chunks, embeddings)       # atomic delete + insert
    return len(chunks)


def ingest_meeting(meeting_id: str, title: str, transcript_text: str) -> dict:
    """Full ingest for the app: index chunks for Q&A AND extract + store intelligence.

    Returns the extracted intelligence (summary, decisions, action_items).
    """
    ingest(meeting_id, transcript_text)                 # chunks -> pgvector (for Q&A)
    intelligence = extract(transcript_text)             # decisions + action items (whole transcript)
    save_meeting(meeting_id, title, transcript_text, intelligence)
    return intelligence
