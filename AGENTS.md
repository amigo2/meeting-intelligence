# AGENTS.md — working rules for this repo (AI-assisted development)

Canonical instructions for any AI coding assistant (Claude Code, Cursor, Copilot)
and for humans. The goal: AI **accelerates** the work but the output stays *my*
code — consistent, reviewed, tested, and maintainable.

## What this project is
Meeting Intelligence System: analyses meeting/transcript conversations and answers
questions about discussions, **decisions**, and **action items**, grounded with
speaker + timestamp citations. A reusable transcript-intelligence engine.

## Stack
- **Backend:** Python 3.12, FastAPI, Pydantic
- **AI:** AWS Bedrock — Claude Sonnet (EU inference profile) for generation, Titan
  Text Embeddings V2 (1024-dim) for embeddings. London / EU for data residency.
- **Vector store:** pgvector on Postgres (local Docker) / Aurora Postgres (prod)
- **Frontend:** React + TypeScript (Vite)
- **Infra:** Docker, ECS Fargate, GitHub Actions CI/CD

## Architecture principles (do not violate)
1. **Business logic is decoupled from transport.** Core logic lives in modules
   (`ingestion/`, `retrieval/`, `extraction/`); FastAPI routes are THIN wrappers
   that call it. No business logic in route handlers.
2. **Typed domain models** (Pydantic) at boundaries — `Turn`, `Chunk`, etc.
3. **Config over hardcoding.** Model IDs, region, DB URL, embed dim come from
   `app/core/config.py` (env-driven, 12-factor). Never hardcode a model ID or secret.
4. **Bedrock only through `app/core/bedrock.py`.** One place wraps the client.
5. **Attribution end-to-end.** Every chunk keeps speaker + timestamp so answers can
   cite "Ana, 01:10". Never drop that metadata.

## Conventions
- Type hints on public functions; short docstrings that explain **why**, not what.
- Small, single-responsibility modules; clear names over cleverness.
- Match the style of the surrounding code.

## Testing
- **Every new piece of logic gets a test** (`backend/tests/`, pytest).
- Pure logic (parser, chunker) is tested without AWS/DB.
- Live-dependency tests (Bedrock, pgvector) skip when creds/DB are absent.
- Run before committing: `cd backend && .venv/bin/python -m pytest -q`.

## Security & data (health context)
- **No secrets in code or git.** Credentials via the AWS chain (`aws configure`) or
  `.env` (gitignored). `.env.example` documents variable names only.
- Models/embeddings stay in-EU (London / EU inference profile) for GDPR posture.
- Don't send PII the task doesn't need; note UK/NHS strict residency as a
  productionization concern, not a demo requirement.

## AI-assisted workflow — do's and don'ts
**Do:**
- Use AI to scaffold, draft, and refactor — then **read and review every line**.
- Keep changes small and committed incrementally (a readable history is the point).
- Have AI write the tests too, then verify they actually fail/pass meaningfully.
- Keep this file current so the assistant follows the same rules each session.

**Don't:**
- Don't accept code you can't explain. If I can't defend it in review, it doesn't ship.
- Don't let AI put business logic in FastAPI routes or hardcode config/secrets.
- Don't paste an LLM's prose into user-facing docs (READMEs) as-is — the reasoning
  must be mine.
- Don't skip tests because "it looks right".

## How to run
```bash
# DB
docker compose up -d db
# backend deps
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
# end-to-end demo (needs Bedrock access + DB)
.venv/bin/python demo.py
# tests
.venv/bin/python -m pytest -q
```
