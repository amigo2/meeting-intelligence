"""Faithfulness / grounding eval — the direct anti-hallucination harness.

Robustness (`run.py`) asks "can the system be fooled?". This asks the complementary,
sharper question: **is every claim in the answer actually supported by the evidence the
model was given?** A fluent, confident, *unsupported* sentence is a hallucination even
when it happens to be true — so we grade groundedness, not correctness.

Method (isolates the GENERATION step):
  1. Ask the real system → get {answer, sources}. `sources` are the exact excerpts the
     model saw. Faithfulness is judged against THOSE, not the full transcript — whether
     the right chunks were retrieved is the retrieval eval's job, not this one.
  2. Decompose the answer into atomic claims (one verifiable assertion each).
  3. Judge each claim vs the sources with an NLI-style verdict:
     SUPPORTED · UNSUPPORTED (not in context) · CONTRADICTED (context says otherwise).
     UNSUPPORTED + CONTRADICTED = hallucinations.
  4. Deterministic citation check (no LLM): does every non-refusal answer cite a
     [speaker, timestamp], and does every cited timestamp actually exist in the sources?
     A cited timestamp that appears in NO source is a *fabricated citation* — a concrete,
     machine-detectable hallucination the judge can't rationalise away.
  5. Unanswerable questions must refuse: 0 claims, 0 fabricated citations.

Metrics: faithfulness score (supported / total claims), hallucinated-claim count,
citation coverage, fabricated-citation count, refusal correctness.

Run from backend/ (needs DB + Bedrock):  python -m eval.faithfulness
"""

import json
from pathlib import Path

from app.core.bedrock import generate
from app.generation.answerer import answer
# The deterministic grounding checks live in the product (verifier.py) — the eval and the
# live guard share ONE implementation, so a test can never pass while the guard is broken.
from app.generation.verifier import citation_check
from app.ingestion.pipeline import ingest_meeting
from app.retrieval.store import init_db

SET = Path(__file__).parent / "faithfulness_set.json"
DATA = Path(__file__).resolve().parents[1] / "data"


def _parse_json(raw: str):
    """Extract the first JSON value from a model reply (tolerates prose/fences)."""
    text = raw.strip()
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start : end + 1])


# --- LLM steps: decompose then judge each claim --------------------------------

def is_refusal(answer_text: str) -> bool:
    system = (
        "Did this ANSWER refuse or say it lacks enough information from the transcript, "
        'rather than giving a specific factual answer? Reply ONLY JSON: {"refused": true|false}.'
    )
    return bool(_parse_json(generate(system, f"ANSWER: {answer_text}", max_tokens=100)).get("refused"))


def decompose(answer_text: str) -> list[str]:
    """Split an answer into atomic factual claims (strip citations/hedging)."""
    system = (
        "Break the ANSWER into a list of atomic factual claims — each a single verifiable "
        "assertion, self-contained, with citation brackets and hedging removed. Do not add "
        'facts. Reply ONLY JSON: {"claims": ["...", "..."]}.'
    )
    return _parse_json(generate(system, f"ANSWER: {answer_text}", max_tokens=600)).get("claims", [])


def judge_claim(claim: str, context: str) -> dict:
    """NLI verdict of one claim against the retrieved excerpts (the model's evidence)."""
    system = (
        "You check faithfulness. Given CONTEXT (meeting transcript excerpts) and a CLAIM, "
        "decide if the CONTEXT supports the CLAIM. Use ONLY the context, not outside knowledge.\n"
        "SUPPORTED = the context states or clearly entails the claim.\n"
        "CONTRADICTED = the context asserts something incompatible with the claim.\n"
        "UNSUPPORTED = the context neither states nor entails it (missing).\n"
        'Reply ONLY JSON: {"verdict": "SUPPORTED|CONTRADICTED|UNSUPPORTED", "reason": "one line"}.'
    )
    user = f"CONTEXT:\n{context}\n\nCLAIM: {claim}"
    return _parse_json(generate(system, user, max_tokens=250))


def grade_answer(question: str, result: dict, unanswerable: bool) -> dict:
    """Faithfulness + citation grade for a single answer."""
    answer_text, sources = result["answer"], result["sources"]
    context = "\n\n".join(s["text"] for s in sources)
    cite = citation_check(answer_text, sources)

    # Refusals carry no factual claims — grade them on refusal behaviour instead.
    if is_refusal(answer_text):
        return {
            "question": question,
            "refused": True,
            "unanswerable": unanswerable,
            # An unanswerable question SHOULD refuse; an answerable one should not have.
            "refusal_ok": unanswerable,
            "claims": [],
            "faithfulness": None,
            "hallucinated": 0,
            "citation": cite,
        }

    claims = decompose(answer_text)
    verdicts = [{"claim": c, **judge_claim(c, context)} for c in claims]
    supported = sum(v["verdict"] == "SUPPORTED" for v in verdicts)
    hallucinated = sum(v["verdict"] in ("UNSUPPORTED", "CONTRADICTED") for v in verdicts)
    return {
        "question": question,
        "refused": False,
        "unanswerable": unanswerable,
        # An answerable question answered = fine; an unanswerable one answered = a miss.
        "refusal_ok": not unanswerable,
        "claims": verdicts,
        "faithfulness": round(supported / len(claims), 3) if claims else None,
        "hallucinated": hallucinated,
        "citation": cite,
    }


# --- runner --------------------------------------------------------------------

def run(verify: bool = False) -> None:
    """Grade the system's answers for faithfulness.

    verify=False measures the RAW generator (baseline). verify=True routes answers through
    the runtime faithfulness gate first — so the two runs quantify the gate's benefit.
    """
    init_db()
    spec = json.loads(SET.read_text())

    graded: list[dict] = []
    for meeting in spec["meetings"]:
        transcript = (DATA / f"sample_{meeting['sample']}.txt").read_text(encoding="utf-8")
        ingest_meeting(meeting["meeting_id"], meeting["sample"], transcript)
        for q in meeting["questions"]:
            result = answer(meeting["meeting_id"], q["question"], verify=verify)
            graded.append(grade_answer(q["question"], result, q.get("unanswerable", False)))

    mode = "GATE ON (verified)" if verify else "GATE OFF (raw generator)"
    print(f"\n{'='*74}\nFAITHFULNESS / GROUNDING EVAL — {len(graded)} answers — {mode}\n{'='*74}")
    for g in graded:
        cite = g["citation"]
        if g["refused"]:
            tag = "✅" if g["refusal_ok"] else "❌"
            print(f"\n{tag} [refused]  {g['question']}")
            print(f"    expected refusal={g['unanswerable']}")
            continue
        # A faithful answer: no hallucinated claims, cited, no invented timestamps.
        clean = g["hallucinated"] == 0 and cite["has_citation"] and not cite["fabricated"]
        print(f"\n{'✅' if clean else '❌'} [{g['faithfulness']:.0%} faithful]  {g['question']}")
        print(f"    claims={len(g['claims'])} hallucinated={g['hallucinated']} "
              f"citations={cite['num_citations']} fabricated={cite['fabricated'] or 'none'}")
        for v in g["claims"]:
            if v["verdict"] != "SUPPORTED":
                print(f"      ⚠ {v['verdict']}: {v['claim']}  ({v['reason']})")

    # Aggregate — macro faithfulness over answered questions, plus safety counters.
    answered = [g for g in graded if not g["refused"]]
    scores = [g["faithfulness"] for g in answered if g["faithfulness"] is not None]
    macro = sum(scores) / len(scores) if scores else 0.0
    total_hallucinated = sum(g["hallucinated"] for g in answered)
    total_fabricated = sum(len(g["citation"]["fabricated"]) for g in graded)
    uncited = sum(not g["citation"]["has_citation"] for g in answered)
    refusal_wrong = sum(not g["refusal_ok"] for g in graded)

    print(f"\n{'='*74}")
    print(f"Macro faithfulness      : {macro:.1%}  (mean supported-claim ratio over answers)")
    print(f"Hallucinated claims     : {total_hallucinated}  (unsupported or contradicted)")
    print(f"Fabricated citations    : {total_fabricated}  (cited timestamp in no source)")
    print(f"Uncited answers         : {uncited}")
    print(f"Refusal errors          : {refusal_wrong}  (answered when should refuse, or vice-versa)")
    print(f"{'='*74}")


if __name__ == "__main__":
    import sys

    # `python -m eval.faithfulness --verify` grades the guarded pipeline; default is raw.
    run(verify="--verify" in sys.argv)
