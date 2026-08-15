"""Answer generation: retrieve relevant chunks, then Claude writes a grounded, cited answer.

Guardrails (important in a health/consulting context): the model answers ONLY from the
retrieved transcript excerpts, cites the speaker + timestamp for every claim, and
refuses when the evidence isn't there — rather than inventing. This is "cite-or-refuse".
"""

from app.core.bedrock import generate
from app.generation.verifier import verify_answer
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


def _generate_answer(question: str, excerpts: str, correction: str = "") -> str:
    user_prompt = f"Question: {question}\n\nTranscript excerpts:\n{excerpts}{correction}"
    return generate(SYSTEM_PROMPT, user_prompt)


def answer(meeting_id: str, question: str, k: int = 4, verify: bool = True) -> dict:
    """Return a grounded answer plus the source chunks it was based on.

    When `verify` is on, the answer passes through the runtime faithfulness gate before
    being returned: if a claim isn't supported by the retrieved excerpts, we regenerate
    ONCE with the offending claims called out, then re-check. The final grounding verdict
    rides along in `verification` so the UI can flag any answer we couldn't fully ground.
    """
    hits = retrieve(meeting_id, question, k=k)
    if not hits:
        return {
            "answer": "No transcript has been ingested for this meeting yet.",
            "sources": [],
        }

    excerpts = "\n\n".join(hit["text"] for hit in hits)  # each already tagged [ts] Speaker: ...
    text = _generate_answer(question, excerpts)

    if not verify:
        return {"answer": text, "sources": hits}

    verdict = verify_answer(text, hits)
    if not verdict["grounded"]:
        # One bounded self-correction: re-answer with the unsupported claims named, then
        # re-verify. Capped at a single retry so a stubborn case can't loop or blow up cost.
        issues = verdict["unsupported"] + [
            f"invented citation [{ts}]" for ts in verdict["fabricated_citations"]
        ]
        flagged = "; ".join(issues) or "unsupported statements"
        correction = (
            f"\n\nA previous draft included statements not supported by the excerpts: {flagged}. "
            "Rewrite using ONLY what the excerpts support; omit anything ungrounded. If the "
            "excerpts don't answer the question, say you don't have enough information."
        )
        text = _generate_answer(question, excerpts, correction)
        verdict = verify_answer(text, hits)

    return {"answer": text, "sources": hits, "verification": verdict}
