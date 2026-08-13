"""Tests for the transcript parser (pure, no external deps)."""

from pathlib import Path

from app.ingestion.parser import parse_transcript


def test_parses_a_line_with_role():
    turns = parse_transcript("[00:14] Ben (Eng): Hello there")
    assert len(turns) == 1
    turn = turns[0]
    assert turn.timestamp == "00:14"
    assert turn.speaker == "Ben"
    assert turn.role == "Eng"
    assert turn.text == "Hello there"


def test_role_is_optional():
    turns = parse_transcript("[01:00] Ana: No role here")
    assert turns[0].speaker == "Ana"
    assert turns[0].role is None
    assert turns[0].text == "No role here"


def test_skips_blank_and_malformed_lines():
    text = "\n[00:01] Ana (PM): first\nnot a turn line\n\n[00:05] Ben (Eng): second\n"
    turns = parse_transcript(text)
    assert len(turns) == 2
    assert [t.speaker for t in turns] == ["Ana", "Ben"]


def test_multiword_speaker_and_punctuated_text():
    turns = parse_transcript("[02:00] Mrs. García (Owner): Three months, no penalty — okay.")
    assert turns[0].speaker == "Mrs. García"
    assert turns[0].role == "Owner"
    assert turns[0].text == "Three months, no penalty — okay."


def test_parses_both_sample_files():
    data_dir = Path(__file__).resolve().parents[1] / "data"
    for name in ("sample_meeting.txt", "sample_realestate.txt"):
        turns = parse_transcript((data_dir / name).read_text(encoding="utf-8"))
        assert len(turns) > 5
        assert all(t.timestamp and t.speaker and t.text for t in turns)
