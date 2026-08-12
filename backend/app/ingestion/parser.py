"""Transcript parsing: raw text -> structured speaker turns.

A transcript line has the shape:
    [MM:SS] Speaker (Role): spoken text
The role in parentheses is optional, so "Ana: ..." also parses. Blank lines and
anything that doesn't match the turn shape (headers, notes) are skipped.

A parsed Turn keeps the speaker + timestamp so everything downstream — retrieval,
extraction, and answer citations ("Ana, 01:10") — can attribute back to the source.
"""

import re

from pydantic import BaseModel

# One regex with named groups, kept self-documenting:
#   [00:14]  Ben        (Eng)?              : text
_LINE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+"   # [00:14]  -> timestamp (anything up to "]")
    r"(?P<speaker>.+?)"               # speaker name (non-greedy, stops at the role/":")
    r"(?:\s+\((?P<role>[^)]+)\))?"    # optional "(Role)"
    r":\s+(?P<text>.+)$"              # ": " then the spoken text
)


class Turn(BaseModel):
    """One line of the conversation, attributable to a speaker at a timestamp."""

    timestamp: str
    speaker: str
    role: str | None = None
    text: str


def parse_transcript(text: str) -> list[Turn]:
    """Parse transcript text into ordered Turns; skip blank/malformed lines."""
    turns: list[Turn] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = _LINE.match(line)
        if match is None:
            continue  # not a well-formed turn line — ignore it
        turns.append(
            Turn(
                timestamp=match.group("timestamp").strip(),
                speaker=match.group("speaker").strip(),
                role=match.group("role"),  # None when the "(Role)" group is absent
                text=match.group("text").strip(),
            )
        )
    return turns


if __name__ == "__main__":
    # Quick manual check: python -m app.ingestion.parser   (run from backend/)
    from pathlib import Path

    data_dir = Path(__file__).resolve().parents[3] / "data"
    for name in ("sample_meeting.txt", "sample_realestate.txt"):
        print(f"\n=== {name} ===")
        content = (data_dir / name).read_text(encoding="utf-8")
        turns = parse_transcript(content)
        print(f"{len(turns)} turns parsed. First 3:")
        for turn in turns[:3]:
            print(" ", turn.model_dump())
