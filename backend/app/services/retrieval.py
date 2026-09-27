import math

from pydantic import BaseModel
from psycopg_pool import AsyncConnectionPool

from app.services.embeddings import generate_embedding

EMBEDDING_DIMENSIONS = 768
DEFAULT_TOP_K = 5


class RetrievalEmbeddingError(Exception):
    """A query embedding did not match the database vector contract."""


class RetrievedChunk(BaseModel):
    chunk_id: int
    document_id: int
    title: str
    source: str
    document_type: str
    chunk_index: int
    content: str
    distance: float


def _to_pgvector_literal(vector: list[float]) -> str:
    return "[" + ",".join(repr(value) for value in vector) + "]"


def _validate_embedding(vector: list[float]) -> list[float]:
    if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSIONS:
        raise RetrievalEmbeddingError(
            f"Embedding must have {EMBEDDING_DIMENSIONS} dimensions"
        )

    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in vector
    ):
        raise RetrievalEmbeddingError("Embedding must contain finite numeric values")

    return [float(value) for value in vector]


async def retrieve_chunks(
    query: str,
    pool: AsyncConnectionPool,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Return the nearest document chunks for a non-empty query."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be non-empty")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer")

    embedding = _validate_embedding(await generate_embedding(query.strip()))
    vector_literal = _to_pgvector_literal(embedding)

    async with pool.connection() as connection:
        cursor = await connection.execute(
            """
            SELECT document_chunks.id AS chunk_id,
                   document_chunks.document_id,
                   documents.title,
                   documents.source,
                   documents.document_type,
                   document_chunks.chunk_index,
                   document_chunks.content,
                   document_chunks.embedding <=> %s::vector AS distance
            FROM document_chunks
            JOIN documents ON documents.id = document_chunks.document_id
            ORDER BY document_chunks.embedding <=> %s::vector ASC
            LIMIT %s
            """,
            (vector_literal, vector_literal, top_k),
        )
        rows = await cursor.fetchall()

    return [
        RetrievedChunk(
            chunk_id=row[0],
            document_id=row[1],
            title=row[2],
            source=row[3],
            document_type=row[4],
            chunk_index=row[5],
            content=row[6],
            distance=row[7],
        )
        for row in rows
    ]