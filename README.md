# 🎙️ Meeting Intelligence System

Analyzes meeting transcripts (speaker + timestamp) and answers questions about
discussions, **decisions**, and **action items** — with grounded, cited answers.
Built as a reusable transcript-intelligence engine (meetings, real-estate client
calls, voice bookings).

> Newpage Lead FDE assignment — Option 3. Stack: FastAPI · React/TypeScript ·
> AWS Bedrock (Claude + Titan) · pgvector on Aurora Postgres · Docker · Fargate.

<!-- Write the README in MY OWN WORDS. The reviewers explicitly want my thinking,
     not an LLM's output. Fill each section as I build. -->

## Setup
```bash
cp .env.example .env          # add AWS creds + Bedrock model access
docker compose up --build     # Postgres+pgvector + FastAPI
# backend: http://localhost:8000/health
```

## Architecture overview
<!-- simple diagram: transcript → chunk → embed (Titan) → pgvector → retrieve+rerank
     → Q&A + structured extraction (Claude) → React UI. -->

## RAG / LLM approach & decisions
<!-- LLM (Claude via Bedrock) · embeddings (Titan) · vector DB (pgvector/Aurora) ·
     orchestration · chunking (by speaker-turn/time window + metadata) · prompt &
     context management · guardrails (cite speaker+timestamp, cite-or-refuse) ·
     quality (eval harness) · observability. Choices considered vs final choice. -->

## Key technical decisions (and why)
<!-- my reasoning, trade-offs -->

## Quality & evaluation
<!-- golden-set eval: extraction recall/precision, attribution correctness,
     grounding + refusal (LLM-as-judge + deterministic). My focus. -->

## Productionizing (AWS)
<!-- Docker → ECR → Fargate; Aurora pgvector; Bedrock; CI/CD (GitHub Actions);
     secrets, observability, scaling. Reuse VPC/NAT/cluster, new service + DB. -->

## Engineering standards (followed, and skipped)
<!-- clean architecture, SOLID, tests, observability — and what I skipped for time -->

## How I used AI tools
<!-- Claude Code workflow: do's/don'ts, how I keep it repeatable & reviewed -->

## Known limitations (deliberate, at demo scale)
Surfaced by an AI code-review pass; correctness issues fixed, these documented:
- **Filtered vector search:** HNSW ranks globally then filters by `meeting_id`, so at
  large scale a scoped query could miss best chunks — fix with `hnsw.iterative_scan`
  or per-tenant partial indexes.
- **No connection pooling** (add `psycopg_pool` for production concurrency).
- **Sequential embeddings** (parallelise for large transcripts).
- **Lazy Bedrock client** not lock-guarded (harmless; guard if needed).

## What I'd do differently with more time
<!-- honest next steps -->

## Screenshots / video
<!-- add before submitting -->
