"""FastAPI entrypoint.

Mounts the API routes (thin wrappers over the core logic) and enables CORS so the
Vite dev frontend (localhost:5173) can call the API in development.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.retrieval.store import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # ensure pgvector extension + tables exist before serving
    yield


app = FastAPI(title="Meeting Intelligence", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Any localhost port for local dev (Vite may fall back off 5173). Prod is same-origin
    # via CloudFront, so this list is irrelevant in production.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"service": "meeting-intelligence", "health": "/health", "docs": "/docs"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
