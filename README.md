# 🎙️ Meeting Intelligence System

Analyses meeting transcripts (speaker + timestamp) and answers questions about
discussions, **decisions**, and **action items** — with grounded, **cited** answers,
and cite-or-refuse guardrails. Built as a reusable transcript-intelligence engine
(meetings, real-estate client calls, voice bookings).

> Newpage Lead FDE assignment — Option 3.
> **Live demo:** deployed to AWS (Fargate + Aurora pgvector + Bedrock, behind CloudFront).
> **Stack:** FastAPI · React/TypeScript · AWS Bedrock (Claude + Titan) · pgvector on
> Aurora Postgres · Docker · Fargate · Terraform · GitHub Actions.

<!-- ✍️ NOTE TO SELF: the reviewers want MY thoughts, not an LLM's output. The
     technical sections below document the real system; the reasoning/"thoughts"
     sections (Key decisions, How I used AI tools, What I'd do differently) — pass
     through my own voice before submitting. -->

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

```
                      React + TypeScript (Vite)  ── CloudFront (HTTPS) ──┐
                                                                         │
Internet ─ CloudFront ─ /meetings/*, /health ─► ALB ─► Fargate (FastAPI)─┤
                                                          │              │
                        ┌─────────────────────────────────┼──────────────┘
                  Bedrock Titan (embed)   Bedrock Claude (generate/extract)
                                          │
   INGEST:  transcript ─► parse (speaker/timestamp) ─► chunk (sliding window)
            ─► embed (Titan) ─► pgvector (Aurora)     + extract decisions/action items
   QUERY:   question ─► embed ─► cosine search (pgvector) ─► Claude ─► cited answer
```

- **Clean architecture:** business logic in modules (`ingestion/`, `retrieval/`,
  `extraction/`, `generation/`); FastAPI routes are thin wrappers. Core is unit-testable
  without HTTP.
- **Attribution end-to-end:** every chunk keeps speaker + timestamp, so answers cite
  *"[Ana, 01:10]"* and action items carry an owner.

---

## RAG / LLM approach & decisions

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

- **Robustness eval** (`backend/eval/run.py`) — an **adversarial** transcript
  (`sample_tricky.txt`) with 6 traps (proposed-vs-decided, correction, distractor number,
  wrong attribution, negation, not-answerable). Each answer is graded by an **LLM-as-judge**
  on two axes — *correct* AND *avoided the bait* — because string matching fails when the
  model *mentions* a trap to dismiss it. **Current score: 6/6.**
- **Deterministic + unit tests** (`backend/tests/`) — parser, chunker, store round-trip,
  empty-transcript guard. Live DB/Bedrock tests auto-skip without creds.
- **Metrics to track** (documented): retrieval recall@k, grounding/citation rate, refusal
  accuracy, extraction recall/precision, latency p95/p99, cost per query.

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

> ✍️ **WRITE THIS IN MY OWN VOICE** — reviewers explicitly want my do's/don'ts, not prose.
> Points to cover (in my words):
> - Rules file (`AGENTS.md`) that keeps AI output consistent + maintainable across sessions.
> - Small, reviewable, incremental commits — the history shows *how* I built it.
> - Ran **AI code-review agents** (single + parallel multi-lens) then **triaged** findings —
>   fixed real bugs (atomic ingest, dead code), documented edge cases, **rejected a false
>   positive**. AI accelerates; I decide.
> - Have AI write tests, then verify they fail/pass meaningfully.
> - Don't ship code I can't explain in review; don't put logic in routes or hardcode secrets.

---

## Known limitations (deliberate, at demo scale)
Surfaced by AI code-review passes; correctness issues fixed, these documented:
- **Filtered vector search:** HNSW ranks globally then filters by `meeting_id`, so at large
  scale a scoped query could miss best chunks — fix with `hnsw.iterative_scan` or per-tenant
  partial indexes.
- **No connection pooling** (add `psycopg_pool` for production concurrency).
- **Sequential embeddings** (parallelise for large transcripts).
- **`replace_chunks` concurrency** — two simultaneous re-ingests of one meeting could duplicate
  (serialise per meeting / advisory lock).
- **Lazy Bedrock client** not lock-guarded (harmless; guard if needed).

---

## What I'd do differently / next

> ✍️ **MY VOICE.** Candidate points:
> - Add the retrieval + grounding eval layers (recall@k, LLM-judge faithfulness) and gate CI on them.
> - Rerank step (retrieve-then-rerank) to sharpen retrieval.
> - Voice → transcript (Whisper / AWS Transcribe) — the Option 3 bonus.
> - Domain-configurable extraction schema (meeting vs sales-call lens).
> - Connection pooling, parallel embeddings, HTTPS on the ALB, auth + multi-tenant.

---

## Screenshots / video
> ✍️ Add 2–3 screenshots (intelligence cards + a cited Q&A) and, if time, a short screen-recording.
```
![Intelligence cards](docs/screenshot-intelligence.png)
![Grounded Q&A](docs/screenshot-qa.png)
```
