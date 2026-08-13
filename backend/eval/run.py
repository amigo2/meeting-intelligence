"""Robustness eval — does the LLM avoid being fooled?

Ingests the 'tricky' transcript (engineered with 6 traps) and grades each answer
with an LLM-as-judge: did it state the correct fact AND avoid the plausible bait —
or correctly refuse when the info isn't there. This is deliberately adversarial:
it proves understanding, not just recall.

Run from backend/ (needs DB + Bedrock):  python -m eval.run
"""

import json
from pathlib import Path

from app.core.bedrock import generate
from app.generation.answerer import answer
from app.ingestion.pipeline import ingest_meeting
from app.retrieval.store import init_db

SET = Path(__file__).parent / "robustness_set.json"
DATA = Path(__file__).resolve().parents[2] / "data"


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    return json.loads(text[text.find("{") : text.rfind("}") + 1])


def judge_answer(question: str, model_answer: str, correct: str, bait: str) -> dict:
    system = (
        "You are a strict grader. Given a QUESTION, an ANSWER, the CORRECT fact, and a "
        "BAIT (a plausible but wrong answer the transcript could tempt), decide two things. "
        'Reply ONLY JSON: {"correct": true|false, "avoided_bait": true|false, "reason": "one line"}. '
        "correct = the answer states the correct fact. "
        "avoided_bait = the answer does NOT assert the bait as the answer "
        "(mentioning it to dismiss it is fine)."
    )
    user = f"QUESTION: {question}\nANSWER: {model_answer}\nCORRECT: {correct}\nBAIT: {bait}"
    return _parse_json(generate(system, user, max_tokens=300))


def judge_refusal(question: str, model_answer: str) -> dict:
    system = (
        "Did this ANSWER refuse, or say it lacks enough information, rather than giving a "
        'specific factual answer? Reply ONLY JSON: {"refused": true|false, "reason": "one line"}.'
    )
    return _parse_json(generate(system, f"QUESTION: {question}\nANSWER: {model_answer}", max_tokens=200))


def run() -> None:
    init_db()
    spec = json.loads(SET.read_text())
    transcript = (DATA / f"sample_{spec['sample']}.txt").read_text(encoding="utf-8")
    ingest_meeting(spec["meeting_id"], spec["sample"], transcript)

    print(f"\n{'='*70}\nROBUSTNESS EVAL — {spec['sample']} transcript ({len(spec['cases'])} traps)\n{'='*70}")
    passed = 0
    for case in spec["cases"]:
        question = case["question"]
        model_answer = answer(spec["meeting_id"], question)["answer"]

        if case.get("refuse"):
            verdict = judge_refusal(question, model_answer)
            ok = bool(verdict.get("refused"))
            print(f"\n{'✅ PASS' if ok else '❌ FAIL'}  [not-answerable]  {question}")
            print(f"    refused={verdict.get('refused')} :: {verdict.get('reason')}")
        else:
            verdict = judge_answer(question, model_answer, case["correct"], case["bait"])
            ok = bool(verdict.get("correct")) and bool(verdict.get("avoided_bait"))
            print(f"\n{'✅ PASS' if ok else '❌ FAIL'}  [{case['category']}]  {question}")
            print(f"    correct={verdict.get('correct')} avoided_bait={verdict.get('avoided_bait')} :: {verdict.get('reason')}")

        passed += ok

    print(f"\n{'='*70}\nSCORE: {passed}/{len(spec['cases'])} traps handled robustly\n{'='*70}")


if __name__ == "__main__":
    run()
