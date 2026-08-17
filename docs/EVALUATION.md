# Evaluation & metrics

Evals are a first-class discipline here — hands-on harnesses, not theory. The goal is
to prove **understanding, not recall**, and to catch regressions when prompts/models
change. Layered, because an LLM system fails in different places.

## The layers

| Layer | Question it answers | How | Where |
|---|---|---|---|
| **Retrieval** | Did we fetch the right evidence? | golden set → recall@k, decoy rejection | (planned) |
| **Faithfulness** ⭐ | Is every claim **supported by the evidence** + cited (no hallucination)? | claim-decompose → NLI judge + deterministic citation check | `backend/eval/faithfulness.py` |
| **Robustness** ⭐ | Can the system be **fooled**? | adversarial "trap" transcript + LLM-as-judge | `backend/eval/run.py` |
| **Extraction** | Are decisions/action items right (recall) without invention (precision)? | golden set + judge | (planned) |
| **Operational** | Is it fast + affordable enough? | latency + cost metrics | (instrument) |

## The judge — where grading fires
Every "graded by an LLM" step (robustness, faithfulness, and the runtime gate) calls:
- **Claude (Sonnet 4.5) via AWS Bedrock** — the *same* model + in-EU stack used to answer,
  through `app/core/bedrock.py::generate()`. No third-party judge service; nothing leaves AWS.
- The judge returns a **strict JSON verdict** (not prose), so results are machine-checkable:
  two-axis (`correct` AND `avoided_bait`) for robustness; NLI
  (`SUPPORTED / UNSUPPORTED / CONTRADICTED`) for faithfulness.
- **Honest caveat:** the same model family judges its own output. Fine at demo scale; for high
  stakes I'd use a *different/stronger* judge model plus a **second verifier** (adversarial
  verification) to kill false positives.

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

## Faithfulness / grounding eval (built)
The direct **anti-hallucination** harness. Robustness asks *"can it be fooled?"*;
faithfulness asks the sharper question: *is every claim in the answer actually supported
by the evidence the model was given?* A fluent, confident, **unsupported** sentence is a
hallucination even when it happens to be true — so we grade **groundedness, not correctness**.

Pipeline (`backend/eval/faithfulness.py`) — deliberately isolates the **generation** step:
1. Ask the real system → `{answer, sources}`. Faithfulness is judged against **those
   retrieved excerpts**, not the full transcript — *did we retrieve well?* is the retrieval
   layer's job; this layer asks *given what it retrieved, did it stay grounded?*
2. **Decompose** the answer into atomic claims (one assertion each).
3. **NLI judge** each claim vs the sources → `SUPPORTED` / `UNSUPPORTED` / `CONTRADICTED`
   (the latter two = hallucinations).
4. **Deterministic citation check** (no LLM): every non-refusal answer must cite a
   `[speaker, timestamp]`, and every cited timestamp must exist in a retrieved chunk — a
   cited timestamp present in **no** source is a **fabricated citation**, a machine-detectable
   hallucination the judge can't rationalise away.
5. **Unanswerable** questions must refuse (0 claims, 0 fabricated citations).

**Metrics emitted:** macro faithfulness (mean supported-claim ratio), hallucinated-claim
count, fabricated-citation count, uncited-answer count, refusal errors.

Run: `cd backend && python -m eval.faithfulness`.
**Current (8 answers, 2 transcripts):** macro **93.3%** faithful · **0** fabricated citations
· **0** uncited · **0** refusal errors (both unanswerable Qs refused).

> **A finding it caught (kept, not gamed).** One answer scored 60%: asked *"what has to land
> **first**?"*, the model echoed the loaded word "first" and listed the refund fix + usability
> session as ordered — but the transcript only says **both** must land this week, with **no
> ordering**. The judge correctly flagged the two "…has to land first" claims as UNSUPPORTED.
> Root cause: the answer **accepted a false presupposition** in the question. The fix belongs in
> the *system prompt* (reject loaded questions), **not** in weakening the judge — tuning an eval
> until it goes green is how you lie to yourself. Logged as a finding for the next prompt iteration.

## Prevention: the runtime faithfulness gate (built)
Evals **measure** hallucination offline; the gate **prevents** it at request time — the
seatbelt to the eval's crash test. Lives in [`app/generation/verifier.py`](../backend/app/generation/verifier.py),
wired into `answer(..., verify=True)`:

1. Generate the answer as normal.
2. **Verify** it against the retrieved excerpts — **one** LLM call for the whole answer
   (not per-claim like the eval) + the free deterministic citation check → a verdict
   `{grounded, unsupported, fabricated_citations}`.
3. If not grounded, **self-correct once**: regenerate with the unsupported claims named,
   then re-verify. Capped at a single retry (bounded latency/cost, no loops).
4. The verdict rides back in the API response; the UI shows a **trust badge**
   (✓ grounded / ⚠ unverified).

**Design trade-off (deliberate):** the gate is *coarser* than the eval — one call vs.
per-claim — so it reliably catches blatant hallucinations (wrong dates, invented numbers,
fabricated citations) while trading away some sensitivity to subtle cases the microscope
catches. That ~13× cost saving is what makes it affordable on live traffic; for a
high-stakes deployment you'd dial granularity up. The deterministic citation check is the
**same code** the eval uses (shared in `verifier.py`), so test and guard can't drift.

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
- **Regression gate:** unit tests + the deterministic citation checks run in CI today; the
  LLM-judge evals run as a **manual** gate (they need live Bedrock). Wiring them into CI on
  every prompt/model change, blocking on a drop, is the next step.
- **Adversarial verification:** for high stakes, a second judge re-checks the first judge's verdict to kill false positives.

## One-liner
"I test that it can't be fooled, not just that it answers — adversarial traps graded by an
LLM-as-judge (Claude on Bedrock) on correctness AND bait-avoidance, plus a claim-level
faithfulness eval and a live verify gate. Unit + citation checks run in CI; the LLM evals are
a manual gate today (CI-gating next)."
