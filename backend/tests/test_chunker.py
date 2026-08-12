"""Tests for the sliding-window chunker."""

from pathlib import Path

from app.ingestion.parser import Turn, parse_transcript
from app.ingestion.chunker import chunk_turns


def _turns(n: int) -> list[Turn]:
    return [Turn(timestamp=f"00:{i:02d}", speaker=f"S{i % 2}", text=f"line {i}") for i in range(n)]


def test_empty_returns_no_chunks():
    assert chunk_turns([]) == []


def test_fewer_turns_than_window_is_one_chunk():
    chunks = chunk_turns(_turns(2), window=4, overlap=1)
    assert len(chunks) == 1
    assert chunks[0].num_turns == 2


def test_consecutive_chunks_overlap():
    # window=4, overlap=1 -> step=3; chunk0 covers 0..3, chunk1 covers 3..6
    chunks = chunk_turns(_turns(7), window=4, overlap=1)
    assert "line 3" in chunks[0].text
    assert "line 3" in chunks[1].text  # the shared (overlapping) turn


def test_metadata_is_populated():
    chunk = chunk_turns(_turns(4), window=4, overlap=1)[0]
    assert chunk.start_timestamp == "00:00"
    assert chunk.end_timestamp == "00:03"
    assert set(chunk.speakers) == {"S0", "S1"}
    assert chunk.num_turns == 4


def test_no_redundant_tail_and_full_coverage():
    turns = _turns(13)
    chunks = chunk_turns(turns, window=4, overlap=1)
    # every turn appears in at least one chunk
    joined = "\n".join(c.text for c in chunks)
    for t in turns:
        assert t.text in joined
    # the last chunk actually reaches the final turn
    assert "line 12" in chunks[-1].text


def test_runs_on_real_transcripts():
    data_dir = Path(__file__).resolve().parents[2] / "data"
    for name in ("sample_meeting.txt", "sample_realestate.txt"):
        turns = parse_transcript((data_dir / name).read_text(encoding="utf-8"))
        chunks = chunk_turns(turns)
        assert len(chunks) >= 2
        joined = "\n".join(c.text for c in chunks)
        for t in turns:
            assert t.text in joined  # nothing dropped
