# Evaluation & metrics

Evals are a first-class discipline here — hands-on harnesses, not theory. The goal is
to prove **understanding, not recall**, and to catch regressions when prompts/models
change. Layered, because an LLM system fails in different places.

## The layers

| Layer | Question it answers | How | Where |
|---|---|---|---|
| **Retrieval** | Did we fetch the right evidence? | golden set → recall@k, decoy rejection | (planned, mirrors Mighty) |
| **Grounding** | Is the answer grounded + cited + does it refuse when it should? | LLM-as-judge + deterministic citation check | (planned) |
| **Robustness** ⭐ | Can the system be **fooled**? | adversarial "trap" transcript + LLM-as-judge | `backend/eval/run.py` |
| **Extraction** | Are decisions/action items right (recall) without invention (precision)? | golden set + judge | (planned) |
| **Operational** | Is it fast + affordable enough? | latency + cost metrics | (instrument) |

## Robustness eval (built)
`sample_tricky.txt` is engineered with 6 traps; each case has a `correct` fact and a
plausible `bait`. A case passes only if the answer is **correct AND avoids the bait**
(or correctly **refuses** when unanswerable). Judged by an LLM (string matching fails
here — the model may *mention* the bait to dismiss it, which is fine).

**Trap categories:** proposed-vs-decided · correction · distractor-number ·
wrong-attribution · negation/undecided · not-answerable.
**Extend with:** conditional · multi-hop · temporal · hypothetical · pronoun-resolution.

Run: `cd backend && python -m eval.run` → prints per-trap PASS/FAIL + a score
(current: **6/6**).

## Metrics to track

### Quality
- **Retrieval recall@k** — % of expected chunks retrieved.
- **Decoy rejection** — decoys not ranked as relevant.
- **Grounding rate** — % of answers fully supported by retrieved evidence (judge).
- **Citation coverage** — % of claims carrying a [speaker, timestamp].
- **Refusal accuracy** — refuses when unanswerable; answers when answerable.
- **Robustness trap pass-rate** — per category, and **consistency over N runs**
  (a trap passed 2/3 times is a weakness, not a pass).
- **Extraction** — action-item/decision **recall** and **precision** (no invented owners/dates).

### Operational
- **Latency** p50 / p95 / **p99** (optimise the tail), and **TTFT** if streaming.
- **Cost per query** — Bedrock tokens (embed + generate) × price.
- **Cache hit-rate** (once a cache exists).

## Discipline
- **Consistency:** run evals N times; track pass-rate, not a single run (LLMs vary; temp 0 helps but isn't a guarantee).
- **Regression gate:** run the suite in CI on every prompt/model change; block on a drop.
- **Adversarial verification:** for high stakes, a second judge re-checks the first judge's verdict to kill false positives.

## One-liner
"I test that it can't be fooled, not just that it answers — adversarial traps graded
by an LLM-as-judge on correctness AND bait-avoidance, run for consistency and gated
in CI. Plus retrieval/grounding/extraction layers and operational latency/cost metrics."
