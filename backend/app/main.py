"""FastAPI entrypoint.

Phase 0: just a health check so the container + compose stack are verifiably up.
Phase 1 will mount the ingestion / retrieval / extraction routes from app.api.
"""

from fastapi import FastAPI

app = FastAPI(title="Meeting Intelligence")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
