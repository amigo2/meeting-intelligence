"""HTTP routes — thin wrappers over the core logic (no business logic here)."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.generation.answerer import answer
from app.ingestion.pipeline import EmptyTranscriptError, ingest_meeting
from app.retrieval.store import get_meeting

router = APIRouter()

DATA = Path(__file__).resolve().parents[2] / "data"  # backend/data (ships in the image)
SAMPLES = {"meeting": "sample_meeting.txt", "realestate": "sample_realestate.txt"}


class LoadSampleBody(BaseModel):
    sample: str  # "meeting" | "realestate"


class IngestBody(BaseModel):
    title: str
    transcript: str


class AskBody(BaseModel):
    question: str


@router.post("/meetings/{meeting_id}/load-sample")
def load_sample(meeting_id: str, body: LoadSampleBody):
    """Ingest a bundled sample transcript (convenience for the demo UI)."""
    filename = SAMPLES.get(body.sample)
    if filename is None:
        raise HTTPException(status_code=400, detail=f"unknown sample '{body.sample}'")
    transcript = (DATA / filename).read_text(encoding="utf-8")
    intelligence = ingest_meeting(meeting_id, body.sample, transcript)
    return {"meeting_id": meeting_id, "title": body.sample, "intelligence": intelligence}


@router.post("/meetings/{meeting_id}/ingest")
def ingest_endpoint(meeting_id: str, body: IngestBody):
    """Ingest a user-provided transcript."""
    try:
        intelligence = ingest_meeting(meeting_id, body.title, body.transcript)
    except EmptyTranscriptError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"meeting_id": meeting_id, "title": body.title, "intelligence": intelligence}


@router.get("/meetings/{meeting_id}")
def read_meeting(meeting_id: str):
    """Return the stored meeting: transcript + extracted intelligence."""
    meeting = get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    return meeting


@router.post("/meetings/{meeting_id}/ask")
def ask_endpoint(meeting_id: str, body: AskBody):
    """Grounded, cited answer to a question about the meeting."""
    return answer(meeting_id, body.question)
