"""Pipeline guard tests that need neither DB nor Bedrock.

The empty-transcript guard must fire BEFORE any embedding or DB write, so a bad
upload can never wipe a meeting's existing data. That path is testable in isolation.
"""

import pytest

from app.ingestion.pipeline import EmptyTranscriptError, ingest


def test_empty_transcript_raises_before_touching_bedrock_or_db():
    # Lines that don't match the transcript format -> 0 turns -> raise, no embed, no DB.
    with pytest.raises(EmptyTranscriptError):
        ingest("any-meeting", "just some noise\nnot a transcript line")
