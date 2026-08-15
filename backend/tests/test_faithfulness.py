"""Unit tests for the DETERMINISTIC grounding checks (shared by the eval AND the live gate).

The LLM half (decompose / judge_claim / verify_answer) can't be unit-tested — it calls a
live model and varies run to run, so it lives as a gated eval you *run*. But `citation_check`
is pure logic: fixed input -> fixed output, no network. That's exactly what SHOULD be a fast
CI test — it's our fabricated-citation detector, live in the request path via verifier.py, and
a silent bug here would let real hallucinations slip through unflagged.
"""

from app.generation.verifier import citation_check, source_timestamps

# A stand-in for what `answer()` returns as `sources`: retrieved transcript chunks.
SOURCES = [
    {"text": "[00:10] Ana (PM): Let's commit to the 27th.", "start": "00:10", "end": "00:22"},
    {"text": "[01:12] Tom (Eng): I'll own the onboarding rebuild.", "start": "01:12", "end": "01:20"},
]


def test_collects_every_timestamp_in_the_evidence():
    assert source_timestamps(SOURCES) == {"00:10", "00:22", "01:12", "01:20"}


def test_valid_citation_is_not_flagged():
    # Cites 01:12, which exists in a source -> grounded, nothing fabricated.
    result = citation_check("Tom owns the rebuild [Tom, 01:12].", SOURCES)
    assert result["has_citation"] is True
    assert result["num_citations"] == 1
    assert result["fabricated"] == []


def test_fabricated_timestamp_is_caught():
    # 04:30 appears in NO source -> the model invented a citation (a hallucination).
    result = citation_check("The budget is 15k [Mike, 04:30].", SOURCES)
    assert result["fabricated"] == ["04:30"]


def test_uncited_answer_is_detected():
    # A confident claim with no citation at all -> has_citation must be False.
    result = citation_check("The launch is on the 27th.", SOURCES)
    assert result["has_citation"] is False
    assert result["num_citations"] == 0


def test_mix_of_real_and_fabricated_citations():
    text = "Launch is the 27th [Ana, 00:10], budget approved [Mike, 09:99... 04:30]."
    result = citation_check(text, SOURCES)
    assert "00:10" not in result["fabricated"]  # real one stays clean
    assert "04:30" in result["fabricated"]       # invented one is flagged


def test_plain_brackets_without_timestamps_are_not_citations():
    # Markdown/aside brackets shouldn't be miscounted as citations.
    result = citation_check("We discussed launch [see notes] and pricing.", SOURCES)
    assert result["has_citation"] is False
    assert result["fabricated"] == []
