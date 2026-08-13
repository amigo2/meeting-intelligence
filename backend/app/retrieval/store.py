"""pgvector storage: persist chunk embeddings and search by cosine similarity.

The vector column dimension MUST match the embedding model (Titan V2 = 1024).
An HNSW index gives approximate-nearest-neighbour search that stays fast as the
corpus grows (O(log n) rather than scanning every row).
"""

import psycopg
from pgvector.psycopg import register_vector

from app.core.config import settings
from app.ingestion.chunker import Chunk


def _connect() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url, autocommit=True)
    register_vector(conn)  # lets us pass/read Python lists as pgvector values
    return conn


def init_db() -> None:
    """Create the pgvector extension, the chunks table, and the HNSW index (idempotent)."""
    with _connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id              BIGSERIAL PRIMARY KEY,
                meeting_id      TEXT NOT NULL,
                text            TEXT NOT NULL,
                speakers        TEXT[] NOT NULL,
                start_timestamp TEXT NOT NULL,
                end_timestamp   TEXT NOT NULL,
                embedding       vector({settings.embed_dim}) NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS chunks_embedding_idx "
            "ON chunks USING hnsw (embedding vector_cosine_ops)"
        )


def delete_meeting(meeting_id: str) -> None:
    """Remove all chunks for a meeting (keeps re-ingestion idempotent)."""
    with _connect() as conn:
        conn.execute("DELETE FROM chunks WHERE meeting_id = %s", (meeting_id,))


def _insert_chunks(cur, meeting_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    for chunk, embedding in zip(chunks, embeddings):
        cur.execute(
            "INSERT INTO chunks "
            "(meeting_id, text, speakers, start_timestamp, end_timestamp, embedding) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                meeting_id,
                chunk.text,
                chunk.speakers,
                chunk.start_timestamp,
                chunk.end_timestamp,
                embedding,
            ),
        )


def replace_chunks(meeting_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    """Atomically replace a meeting's chunks: delete old + insert new in ONE transaction.

    Using a single (non-autocommit) transaction means a failure mid-insert rolls back
    the delete too — so a re-ingest can never leave the meeting with its old data wiped
    and no new data in its place.
    """
    with psycopg.connect(settings.database_url) as conn:  # autocommit off -> real transaction
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE meeting_id = %s", (meeting_id,))
            _insert_chunks(cur, meeting_id, chunks, embeddings)
        conn.commit()


def search(query_embedding: list[float], meeting_id: str, k: int = 4) -> list[dict]:
    """Return the k chunks most similar to the query (cosine), scoped to one meeting."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT text, speakers, start_timestamp, end_timestamp, "
            "1 - (embedding <=> %s) AS similarity "
            "FROM chunks WHERE meeting_id = %s "
            "ORDER BY embedding <=> %s "
            "LIMIT %s",
            (query_embedding, meeting_id, query_embedding, k),
        ).fetchall()
    return [
        {
            "text": text,
            "speakers": speakers,
            "start": start,
            "end": end,
            "similarity": round(similarity, 4),
        }
        for text, speakers, start, end, similarity in rows
    ]
