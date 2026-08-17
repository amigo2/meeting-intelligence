
# 🎙️ Meeting Intelligence System

Analyses meeting transcripts (speaker + timestamp) and answers questions about
discussions, **decisions**, and **action items** — with grounded, **cited** answers,
and cite-or-refuse guardrails. Built as a reusable transcript-intelligence engine
(meetings, real-estate client calls, voice bookings).

Newpage Lead FDE assignment — Option 3.

🔗 **Live demo:** **https://ddrphjsd31mv9.cloudfront.net/**
&nbsp;&nbsp;&nbsp;&nbsp;Deployed to AWS — Fargate + Aurora (pgvector) + Bedrock, behind CloudFront.

🛠️ **Stack:** FastAPI · React/TypeScript · AWS Bedrock (Claude + Titan) · pgvector on Aurora Postgres · Docker · Fargate · Terraform · GitHub Actions.

**Acknowledgment:** I reused a lot of my own Terraform infra and my existing VPC, so the AWS deployment wasn't a tedious task — more a routine, enjoyable one.


---

## Setup & run

### Local
```bash
# 1. Database (Postgres + pgvector), mirrors Aurora
docker compose up -d db                     # host port 5435

# 2. Backend (needs AWS creds via `aws configure` + Bedrock model access in eu-west-2)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8001            # http://localhost:8001/health

# 3. Frontend
cd ../frontend
npm install && npm run dev                  # http://localhost:5173

# End-to-end demo (ingest + retrieve + generate, from the CLI)
cd backend && python demo.py
```

### Tests & evals
```bash
cd backend
python -m pytest -q             # unit + smoke (live DB/Bedrock tests auto-skip)
python -m eval.run              # adversarial robustness eval (needs DB + Bedrock)
```

### Cloud deploy (Terraform)
```bash
cd infra
terraform init
terraform apply                 # ECR, Aurora, Fargate, ALB, CloudFront, CI role
./push-image.sh                 # build+push backend image
./deploy-frontend.sh            # build+upload frontend
terraform destroy               # tear it all down
```

---

## Architecture overview

![Architecture](docs/architecture-diagram.png)



- **Clean architecture:** business logic in modules (`ingestion/`, `retrieval/`,
  `extraction/`, `generation/`); FastAPI routes are thin wrappers. Core is unit-testable
  without HTTP.
- **Attribution end-to-end:** every chunk keeps speaker + timestamp, so answers cite
  *"[Ana, 01:10]"* and action items carry an owner.

---

## RAG / LLM approach & decisions

![RAG query pipeline](docs/rag-pipeline.png)

**Where each step lives in code:**
- **Parse / chunk** (ingest) → [`ingestion/parser.py`](backend/app/ingestion/parser.py) · [`ingestion/chunker.py`](backend/app/ingestion/chunker.py)
- **Embed** (Titan) → [`core/bedrock.py`](backend/app/core/bedrock.py)
- **Retrieve** (pgvector, cosine) → [`retrieval/store.py`](backend/app/retrieval/store.py) · [`retrieval/retriever.py`](backend/app/retrieval/retriever.py)
- **Generate** (cite-or-refuse) → [`generation/answerer.py`](backend/app/generation/answerer.py)
- **Verify gate** (grounding guard) → [`generation/verifier.py`](backend/app/generation/verifier.py)
- **Extraction** (summary / decisions / actions) → [`extraction/extractor.py`](backend/app/extraction/extractor.py)

### Key decisions (considered → chosen)

| Choice | Decision | Why (considered → chosen) |
|---|---|---|
| **LLM** | Claude (via **Bedrock**, EU inference profile) | Right-sized for retrieval+extraction; in-AWS keeps data in-EU. Would route to a bigger model only for the hardest reasoning. |
| **Embeddings** | **Titan Text Embeddings V2** (1024-d, normalized) | In-AWS (no OpenAI) → everything stays in-EU. Claude has no embeddings API, so Bedrock+Titan is the in-boundary answer. |
| **Vector DB** | **pgvector** on Postgres/Aurora | One engine local→prod; HNSW index; relational + vectors together. (vs Chroma = 2nd system; Pinecone = external dep.) |
| **Orchestration** | Thin service layer (parser→chunker→embed→store; retrieve→generate) | Decoupled from FastAPI; a CLI/queue could front the same core. |
| **Chunking** | **Sliding window of turns** (4, overlap 1), speaker/timestamp metadata | A lone turn has no context; a window keeps Q/A together; overlap keeps pairs intact across boundaries. (vs whole-doc = no precision; 1-turn = no context.) |
| **Prompt/context** | Generic role prompts; retrieved chunks for Q&A; **whole transcript** for extraction | Q&A needs the relevant slice; extraction must see everything to catch all items. |
| **Guardrails** | **Cite-or-refuse**: cite [speaker, timestamp]; refuse when evidence is absent | High-stakes context (health) — a wrong answer is worse than "I don't know". |
| **Quality** | Layered eval harness (see below) | Prove understanding, not recall. |
| **Observability** | CloudWatch logs/metrics on Fargate; structured request logs | "It works on my laptop isn't shipping." |

---

## Quality & evaluation

Evals are first-class here — hands-on harnesses, not theory. (Details in `docs/EVALUATION.md`.)

**How answers are graded — LLM-as-judge:**
- A second **Claude call, via AWS Bedrock** (same in-EU stack as answering — no external judge
  service, nothing leaves AWS), scores each answer.
- It returns a **strict JSON verdict**, not prose, so grading is machine-checkable — string
  matching fails here, because the model may *mention* a trap only to dismiss it.
- *Honest caveat:* the same model family judges its own output — fine at demo scale; high-stakes
  would use a different/stronger judge plus a second verifier.

**The eval layers** (each says how to run it):
- **Robustness eval — the adversarial one** (`backend/eval/run.py`) — a booby-trapped transcript
  (`sample_tricky.txt`) with 6 traps (proposed-vs-decided, correction, distractor number, wrong
  attribution, negation, not-answerable). Asks *"can it be fooled?"*; graded on two axes — *correct*
  AND *avoided the bait*. **Score: 6/6.**
  → Run: `cd backend && python -m eval.run` *(needs live DB + Bedrock)*
- **Faithfulness eval ⭐ — the anti-hallucination one** (`backend/eval/faithfulness.py`) — asks
  *"is every claim grounded?"*: decompose each answer into atomic claims, judge each against the
  retrieved evidence (`SUPPORTED / UNSUPPORTED / CONTRADICTED`) + a deterministic fabricated-citation
  check. **Macro 93.3% faithful, 0 fabricated citations.**
  → Run: `cd backend && python -m eval.faithfulness` *(needs live DB + Bedrock)*
- **Runtime verify gate ⭐** (`app/generation/verifier.py`) — not a script; it runs **live on every
  answer**, verifying and **self-correcting once** if ungrounded (✓/⚠ trust badge in the UI).
  Toggle with `answer(verify=…)`.
- **Unit tests** (`backend/tests/`) — parser, chunker, store round-trip, empty-transcript guard,
  and the deterministic citation check.
  → Run: `cd backend && python -m pytest -q` — **these run in CI**; live DB/Bedrock tests auto-skip.
- **Metrics to track:** retrieval recall@k, grounding/citation rate, refusal accuracy, extraction
  recall/precision, latency p95/p99, cost per query.

> **Two tiers, on purpose:** the **unit tests run in CI** on every push (fast, deterministic, free);
> the **two LLM evals run manually** (they need live Bedrock and vary run-to-run) — CI-gating them
> is the next step.


---

## Productionizing (AWS) — done, as Terraform IaC

The whole stack is deployed and reproducible in `infra/`:
- **Container:** Docker image → **ECR**.
- **Compute:** **Fargate** service on an existing ECS cluster (reused VPC/subnets — no new NAT).
- **Data:** **Aurora PostgreSQL Serverless v2** + pgvector (scales down when idle).
- **Models:** **Bedrock** (Claude + Titan), called via an **IAM task role** — no static keys.
- **Edge/frontend:** **S3 + CloudFront** (HTTPS), one origin proxying `/meetings/*` to the ALB
  (no CORS/mixed-content).
- **Secrets:** the DB URL lives in **Secrets Manager**, injected at runtime.
- **CI/CD:** **GitHub Actions** — tests gate the deploy; build → ECR → ECS + S3/CloudFront,
  authenticated via **OIDC** (short-lived tokens, no long-lived keys).
- **Cost:** all resources tagged `Project=meeting-intelligence` for cost-to-serve attribution.
  Bedrock spend is negligible; infra is the cost.

Scale-up path: managed vector DB or partitioned pgvector at large scale; connection pooling;
HTTPS/ACM on the ALB; multi-AZ; blue-green ECS deploys.

---

## Engineering standards — followed, and skipped

**Followed:** clean architecture / thin routes · typed Pydantic models · unit + smoke tests ·
adversarial eval harness · Docker · IaC (Terraform) · CI/CD with a test gate · OIDC (no static
keys) · least-privilege IAM + security groups · secrets in Secrets Manager · structured logging.

**Skipped (deliberate, at demo scale — see Known limitations):** HTTPS on the ALB (CloudFront
gives HTTPS to users); DB connection pooling; parallel embeddings; auth/multi-tenant; a full
retrieval/grounding eval layer (robustness layer built). All flagged with fix paths.

---

## How I used AI tools

I use Claude with VS Code.
With AGENTS.md and rules I'm constantly updating, I keep the AI tight — from PR to deployment.
Been harnessing rules from other successfully deployed projects.

I have already experienced glitches in production.

A thing I learned about hallucination while building this: working with an AI agent over a
long session, I noticed it tends to introduce bugs unintentionally. It carries the whole
context, and with that momentum it writes code that *looks* right but isn't — to me this is
the same thing as a hallucination: the model is confident, but wrong. It got noticeably worse
on bigger changes.

What caught those bugs was a **fresh agent with no context**. Because it hadn't been part of
the conversation, it wasn't anchored to the same assumptions, so it spotted the mistakes the
in-context agent had made. Claude Code has a tool for exactly this — `/code-review`, either a
paid heavier "ultra" pass or a lighter "medium" one. I ran the medium review on my own changes
and it caught a real one: the answer verifier could crash the live endpoint on a malformed
model reply. I fixed it and kept the finding.

I keep the same kind of rules for AWS — learned the hard way on past projects. The AI follows
them or the infra it writes isn't safe or cheap; in this repo the Terraform enforces them.

My do / don't from this:
- **Do** have a clean-context reviewer check AI-written code before trusting it — especially on large diffs.
- **Do** keep commits small and reviewable — the git history shows *how* I built it, not just the result.
- **Do** have the AI write tests, then check they actually fail/pass for the right reason.
- **Do** make the AI use IAM roles and OIDC — never static keys — with least-privilege IAM and security groups.
- **Do** keep everything in-region (eu-west-2) for EU data, secrets in Secrets Manager, and cost tags on every resource.
- **Don't** let the same agent that wrote the code be the only one to review it; it shares its own blind spot.
- **Don't** hardcode secrets or bury logic in the routes — AI will do both if I let it.







---

## Known limitations (deliberate, at demo scale)
These came out of the AI code-review passes. **The correctness-critical ones I fixed** (atomic
re-ingest, dead code, a live-path crash on malformed replies); **the ones below are deliberate
trade-offs** — correct and fast enough at demo scale, with the production fix noted for each:
- **Filtered vector search.** The HNSW index finds the nearest chunks across *all* meetings
  first, then filters down to this `meeting_id` — so with many meetings a scoped search could
  miss that meeting's best chunks. Fine with a handful of meetings; at scale, fix with
  `hnsw.iterative_scan` or a per-tenant partial index.
- **No connection pooling.** Every DB call opens and closes its own connection. Under heavy
  concurrency that's wasteful and can exhaust the connection limit — add `psycopg_pool` to
  reuse a set of open connections in production.
- **Sequential embeddings.** Titan embeds one chunk per call and we loop them one at a time,
  which is slow for a long transcript. Fire the calls in parallel to speed up ingest.
- **`replace_chunks` concurrency.** Re-ingesting a meeting deletes the old chunks then inserts
  new ones; two simultaneous re-ingests of the *same* meeting could interleave and duplicate.
  Serialise per meeting with a Postgres advisory lock.
- **Lazy Bedrock client not lock-guarded.** The client is created on first use, so two requests
  hitting that exact instant could both create one. Harmless (an extra client is cheap and
  discarded) — add a lock only if being strict.

---

## What I'd do differently / next

- **Finish the eval stack and gate CI on it.** I already built the faithfulness eval (grading
  each claim against the retrieved evidence) and a runtime verify gate. Next is a *retrieval*
  eval — recall@k on a golden set, i.e. "did we fetch the right chunks?" — and running the whole
  suite in CI so a prompt or model change that drops quality fails the build. Bad retrieval is
  the main upstream cause of hallucination, so I'd measure it directly.
- **Add a rerank step (retrieve-then-rerank).** Retrieval is currently a single cosine pass
  (top-4). I'd pull a wider set (~20) then rerank with a cross-encoder that scores the question
  and each chunk *together* — more accurate relevance, so sharper answers. It costs a little
  latency, but only on the candidates, not the whole corpus.
- **Voice → transcript (the Option 3 bonus).** Record or upload audio → AWS Transcribe (speaker
  labels + timestamps, stays in-EU) → feed the text straight into the existing `ingest()`. The
  pipeline already accepts raw transcript text, so it slots in cleanly — I deferred it
  deliberately to keep scope tight rather than rush a half-baked version.
- **Domain-configurable extraction.** Extraction is a fixed "meeting" lens today
  (summary/decisions/actions). I'd make the schema swappable per domain — a sales call would
  extract objections, agreed terms, price — which makes it a genuinely reusable transcript
  engine (my real-estate use case).
- **Production hardening.** Connection pooling and parallel embeddings for concurrency/speed;
  HTTPS on the ALB (CloudFront already gives users HTTPS — this makes it end-to-end); and the
  big one — **auth + multi-tenant** so each client's data is isolated, which is non-negotiable
  for a health/GDPR product.

---

## Screenshots

**1 — Extracted intelligence: summary, decisions, action items (owner + task + due).**
![Intelligence cards](docs/screenshots/01-intelligence.png)

**2 — Grounded Q&A: every claim carries a `[speaker, timestamp]` citation, and the runtime
faithfulness gate stamps the answer `✓ Verified · grounded in transcript`.**
![Grounded Q&A](docs/screenshots/02-grounded-qa.png)

**3 — "Hallucination test drive": an adversarial transcript with baited questions. Asked
*"Who owns the onboarding rebuild?"* (the bait answer is "Sara", who only expressed interest),
the system correctly answers **Tom** and verifies it — resisting the trap instead of guessing.**
![Hallucination test drive](docs/screenshots/03-hallucination-test.png)
