# Decision log & dev notes

Running record of key technical decisions and why — feeds the README's
"Key technical decisions" and "RAG/LLM approach" sections. Newest at the bottom.

## Option choice
- Chose **Option 3 (Meeting Intelligence)** over "chat with docs": richer to test
  (decisions, action items, attribution) and a **reusable engine** across products
  (meetings, real-estate captación calls, voice bookings) — the same pipeline with a
  domain-configurable extraction lens.

## AWS region — London / EU
- Deploy in **eu-west-2 (London)** for UK/EU **data residency** (life-sciences).
- Claude Sonnet is **cross-region inference only** in London → use the **EU inference
  profile** (`eu.` prefix); data stays in the EU.
- **NHS note (productionization):** strict UK-only residency would need a
  single-region UK model or self-hosting, plus DSPT/DTAC/DCB0129-0160 — flagged, not
  built. Demo uses synthetic data, so EU is fine.

## Models
- **Generation:** Claude Sonnet (`eu.anthropic.claude-sonnet-4-5-...`). Right-sized:
  capability-per-cost for retrieval+extraction; would route to Opus only for the
  hardest reasoning. Cheap iteration matters because the eval loop makes many calls.
- **Embeddings:** Titan Text Embeddings V2, 1024-dim, normalized (pairs with cosine).
  Kept in-AWS (no OpenAI) so everything stays in-EU.

## Vector store
- **pgvector on Postgres/Aurora.** One engine, one code path local→prod (Docker
  pgvector image locally, Aurora in prod). HNSW index for O(log n) ANN as data grows.
- Alternatives considered: Chroma (simpler but a second system to prod), Pinecone
  (scale + ops, external dependency). pgvector wins for AWS-native + relational.

## Chunking
- **Sliding window of consecutive turns** (window 4, overlap 1), not one-turn-per-chunk.
  A lone turn has no context; a window keeps a question + its answer together;
  overlap keeps a Q/A pair intact across boundaries. Speaker + timestamp kept as
  metadata so retrieval and citations stay attributable.

## Clean architecture
- Business logic in modules (`ingestion/`, `retrieval/`, `extraction/`); FastAPI
  routes are thin wrappers. Core is unit-testable without HTTP; could put a CLI or
  queue worker in front of the same logic.

---

## Progress log
- Phase 0 — scaffold, docker-compose (pgvector), README, sample transcripts, eval seed.
- Parser — transcript → typed `Turn`s (regex, optional role), tested.
- Chunker — sliding-window `Chunk`s with speaker/timestamp metadata, tested.
- Bedrock — Titan embeddings **verified live** (1024-dim, EU).
- Storage — pgvector table + HNSW index + cosine search; ingestion pipeline; retriever.
- Next — Claude generation (grounded, cited) → extraction (decisions/action items)
  → eval harness → FastAPI routes → React UI → Fargate deploy.
