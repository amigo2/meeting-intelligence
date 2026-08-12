"""Retrieval: embed a question and find the most relevant chunks of a meeting."""

from app.core.bedrock import embed_text
from app.retrieval.store import search


def retrieve(meeting_id: str, question: str, k: int = 4) -> list[dict]:
    """Embed the question with the same model as the chunks, then cosine-search pgvector."""
    query_embedding = embed_text(question)
    return search(query_embedding, meeting_id, k=k)
