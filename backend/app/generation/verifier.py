"""Runtime faithfulness guard — the live anti-hallucination gate.

The faithfulness *eval* (backend/eval/) MEASURES grounding offline. This module PREVENTS
ungrounded answers reaching the user, at request time. Same idea (check every claim against
the retrieved evidence), tuned for production instead of thoroughness:

  - the eval fans out one judge call PER claim (~a dozen) — great coverage, too slow live;
  - this gate does ONE verification call for the whole answer + a free deterministic
    citation check, so it adds bounded latency/cost to a request.

`answerer.py` calls `verify_answer`; if it fails, the answerer self-corrects once and
re-checks. The deterministic helpers here are the single source of truth — the eval imports
them too, so test and guard can never drift apart.
"""

import json
import re

from app.core.bedrock import generate

# A citation is a bracketed span containing a MM:SS timestamp, e.g. [Ana, 01:10].
_TS = re.compile(r"\b\d{1,2}:\d{2}\b")
_CITATION = re.compile(r"\[[^\]]*\b\d{1,2}:\d{2}\b[^\]]*\]")


def _parse_json(raw: str) -> dict:
    """Extract the first JSON object from a model reply, or {} if it isn't parseable.

    The verifier runs on the live request path, so a stray prose reply or a response
    truncated at max_tokens (no closing brace) must never raise — it degrades to {}.
    """
    text = raw.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


# --- deterministic checks (no LLM — cheap, exact, un-gameable) ------------------

def source_timestamps(sources: list[dict]) -> set[str]:
    """Every MM:SS timestamp that appears anywhere in the retrieved excerpts."""
    stamps: set[str] = set()
    for s in sources:
        stamps.update(_TS.findall(s.get("text", "")))
        stamps.update(_TS.findall(s.get("start", "")))
        stamps.update(_TS.findall(s.get("end", "")))
    return stamps


def citation_check(answer_text: str, sources: list[dict]) -> dict:
    """Has ≥1 citation? Any cited timestamp that exists in NO source (fabricated)?"""
    cited = _CITATION.findall(answer_text)
    cited_stamps = {ts for span in cited for ts in _TS.findall(span)}
    available = source_timestamps(sources)
    fabricated = sorted(cited_stamps - available)
    return {
        "has_citation": bool(cited),
        "num_citations": len(cited),
        "fabricated": fabricated,  # cited but present in no retrieved chunk
    }


# --- the runtime gate ----------------------------------------------------------

_VERIFY_SYSTEM = (
    "You are a strict faithfulness verifier. Given EVIDENCE (meeting transcript excerpts) "
    "and an ANSWER, find any statement in the ANSWER that is NOT supported by the EVIDENCE. "
    "Use ONLY the evidence, not outside knowledge. An answer that declines/says it lacks "
    "information is grounded by definition. "
    'Reply ONLY JSON: {"grounded": true|false, "unsupported": ["the unsupported claim", ...]}. '
    "unsupported must be empty when grounded is true."
)


def verify_answer(answer_text: str, sources: list[dict]) -> dict:
    """One-shot grounding verdict for a live answer: LLM check + deterministic citations.

    Returns {grounded, unsupported, fabricated_citations}. `grounded` is only true when the
    model finds no unsupported claim AND no citation points to a non-existent source.
    """
    context = "\n\n".join(s["text"] for s in sources)
    verdict = _parse_json(
        generate(_VERIFY_SYSTEM, f"EVIDENCE:\n{context}\n\nANSWER:\n{answer_text}", max_tokens=600)
    )
    unsupported = verdict.get("unsupported", []) or []
    fabricated = citation_check(answer_text, sources)["fabricated"]
    # Deterministic citation check ALWAYS runs. If the LLM verdict was unparseable ({}),
    # default its axis to grounded (fail-open on the LLM, not on the exact citation check)
    # so a flaky verifier reply degrades gracefully instead of spuriously self-correcting.
    llm_grounded = verdict.get("grounded", True)
    grounded = bool(llm_grounded) and not unsupported and not fabricated
    return {
        "grounded": grounded,
        "unsupported": unsupported,
        "fabricated_citations": fabricated,
    }
