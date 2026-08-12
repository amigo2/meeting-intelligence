"""Chunking: group consecutive Turns into overlapping windows for embedding.

WHY a sliding window of turns (not one-turn-per-chunk):
a single turn ("Agreed.") carries no context alone. Grouping a few consecutive
turns keeps a question and its answer together, so each embedding captures a
coherent slice of the conversation. A small overlap means a Q/A pair that straddles
a window boundary still appears intact inside at least one chunk.

Each chunk keeps its speakers + timestamp range as metadata, so retrieval results
and answer citations stay attributable to who spoke and when.
"""

from pydantic import BaseModel

from app.ingestion.parser import Turn


class Chunk(BaseModel):
    """A window of consecutive turns, embedded as one unit."""

    text: str                 # rendered turns, e.g. "[00:14] Ben: ...\n[00:31] Ana: ..."
    speakers: list[str]       # distinct speakers in the window (order preserved)
    start_timestamp: str
    end_timestamp: str
    num_turns: int


def _render(turns: list[Turn]) -> str:
    """Render turns keeping speaker + timestamp inline, so the embedding sees them too."""
    return "\n".join(f"[{t.timestamp}] {t.speaker}: {t.text}" for t in turns)


def chunk_turns(turns: list[Turn], window: int = 4, overlap: int = 1) -> list[Chunk]:
    """Group turns into overlapping windows.

    window  = turns per chunk.
    overlap = turns shared between consecutive chunks (keeps Q/A pairs intact).
    Steps by (window - overlap); the final window is the one that reaches the end,
    so there's no redundant tiny tail chunk.
    """
    if not turns:
        return []

    step = max(1, window - overlap)   # guard against overlap >= window (infinite loop)
    chunks: list[Chunk] = []

    for start in range(0, len(turns), step):
        group = turns[start : start + window]
        if not group:
            break

        # distinct speakers, order preserved (dict keeps insertion order)
        speakers = list({t.speaker: None for t in group}.keys())
        chunks.append(
            Chunk(
                text=_render(group),
                speakers=speakers,
                start_timestamp=group[0].timestamp,
                end_timestamp=group[-1].timestamp,
                num_turns=len(group),
            )
        )

        if start + window >= len(turns):
            break  # this window already reached the end — stop (no redundant tail)

    return chunks


if __name__ == "__main__":
    # python -m app.ingestion.chunker   (run from backend/)
    from pathlib import Path

    from app.ingestion.parser import parse_transcript

    data_dir = Path(__file__).resolve().parents[3] / "data"
    for name in ("sample_meeting.txt", "sample_realestate.txt"):
        turns = parse_transcript((data_dir / name).read_text(encoding="utf-8"))
        chunks = chunk_turns(turns)
        print(f"\n=== {name}: {len(turns)} turns -> {len(chunks)} chunks ===")
        for i, c in enumerate(chunks):
            print(f"[chunk {i}] {c.start_timestamp}-{c.end_timestamp} "
                  f"speakers={c.speakers} turns={c.num_turns}")
