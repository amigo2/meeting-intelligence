"""Answer generation: retrieve relevant chunks, then Claude writes a grounded, cited answer.

Guardrails (important in a health/consulting context): the model answers ONLY from the
retrieved transcript excerpts, cites the speaker + timestamp for every claim, and
refuses when the evidence isn't there — rather than inventing. This is "cite-or-refuse".
"""

from app.core.bedrock import generate
from app.retrieval.retriever import retrieve

SYSTEM_PROMPT = (
    "You answer questions about a meeting using ONLY the transcript excerpts provided.\n"
    "Rules:\n"
    "- Ground every statement in the excerpts and cite the speaker and timestamp in "
    "square brackets, e.g. [Ana, 01:10].\n"
    "- If the excerpts do not contain the answer, say you don't have enough information "
    "from the transcript. Never invent facts, names, dates, or commitments.\n"
    "- Be concise and direct."
)


def answer(meeting_id: str, question: str, k: int = 4) -> dict:
    """Return a grounded answer plus the source chunks it was based on."""
    hits = retrieve(meeting_id, question, k=k)
    if not hits:
        return {
            "answer": "No transcript has been ingested for this meeting yet.",
            "sources": [],
        }

    excerpts = "\n\n".join(hit["text"] for hit in hits)  # each already tagged [ts] Speaker: ...
    user_prompt = f"Question: {question}\n\nTranscript excerpts:\n{excerpts}"
    text = generate(SYSTEM_PROMPT, user_prompt)
    return {"answer": text, "sources": hits}
