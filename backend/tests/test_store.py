"""Live-dependency tests for the pgvector store.

These need Postgres+pgvector running (docker compose up -d db). They embed nothing
via Bedrock — they use synthetic 1024-dim vectors — so they exercise the DB layer
(store, atomic replace, cosine search, meeting scoping) in isolation. The whole
module skips when the database isn't reachable.
"""

import psycopg
import pytest

from app.core.config import settings
from app.ingestion.chunker import Chunk
from app.retrieval.store import delete_meeting, init_db, replace_chunks, search


def _db_available() -> bool:
    try:
        psycopg.connect(settings.database_url, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="needs Postgres+pgvector (docker compose up -d db)",
)

MEETING = "pytest-store"


def _chunk(text: str) -> Chunk:
    return Chunk(
        text=text, speakers=["A"], start_timestamp="00:00", end_timestamp="00:10", num_turns=1
    )


def _unit_vector(i: int) -> list[float]:
    """A one-hot 1024-dim vector, so cosine similarity is predictable in tests."""
    vec = [0.0] * settings.embed_dim
    vec[i] = 1.0
    return vec


@pytest.fixture(autouse=True)
def _clean_slate():
    init_db()
    delete_meeting(MEETING)
    yield
    delete_meeting(MEETING)


def test_replace_and_search_round_trip():
    replace_chunks(MEETING, [_chunk("alpha"), _chunk("beta")], [_unit_vector(0), _unit_vector(1)])
    hits = search(_unit_vector(0), MEETING, k=2)
    assert len(hits) == 2
    assert hits[0]["text"] == "alpha"                     # nearest to the query vector
    assert hits[0]["similarity"] > hits[1]["similarity"]  # ranked by cosine


def test_replace_is_idempotent_not_append():
    replace_chunks(MEETING, [_chunk("one")], [_unit_vector(0)])
    replace_chunks(MEETING, [_chunk("two")], [_unit_vector(1)])
    hits = search(_unit_vector(1), MEETING, k=5)
    assert len(hits) == 1          # old chunk replaced, not stacked
    assert hits[0]["text"] == "two"


def test_search_is_scoped_to_meeting():
    replace_chunks(MEETING, [_chunk("scoped")], [_unit_vector(0)])
    assert search(_unit_vector(0), "a-different-meeting", k=5) == []
