import hashlib
import math

from pydantic import BaseModel, field_validator
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.services.chunking import chunk_text
from app.services.embeddings import generate_embedding

EMBEDDING_DIMENSIONS = 768


def _content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class DocumentIngestionRequest(BaseModel):
    title: str
    source: str
    document_type: str
    content: str

    @field_validator("title", "source", "document_type")
    @classmethod
    def require_non_empty_metadata(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("content")
    @classmethod
    def require_non_empty_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be empty")
        return value


class DocumentIngestionResponse(BaseModel):
    document_id: int
    title: str
    document_type: str
    chunk_count: int
    content_already_existed: bool = False


class EmbeddingDimensionError(Exception):
    """An embedding did not match the database vector contract."""


def _to_pgvector_literal(vector: list[float]) -> str:
    """Serialize validated floats to pgvector's input format for a SQL parameter."""
    return "[" + ",".join(repr(value) for value in vector) + "]"


def _validate_embedding(vector: list[float]) -> list[float]:
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise EmbeddingDimensionError(
            f"Embedding must have {EMBEDDING_DIMENSIONS} dimensions"
        )

    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in vector
    ):
        raise EmbeddingDimensionError("Embedding must contain finite numeric values")

    return [float(value) for value in vector]


async def ingest_document(
    request: DocumentIngestionRequest,
    pool: AsyncConnectionPool,
) -> DocumentIngestionResponse:
    """Avoid duplicate content, then persist new documents and chunks atomically."""
    content_sha256 = _content_sha256(request.content)

    async with pool.connection() as connection:
        existing_document = await _find_document_by_hash(connection, content_sha256)
        if existing_document is not None:
            return existing_document

    chunks = list(dict.fromkeys(chunk_text(request.content)))
    embedded_chunks: list[tuple[str, str]] = []

    for chunk in chunks:
        embedding = await generate_embedding(chunk)
        validated_embedding = _validate_embedding(embedding)
        embedded_chunks.append((chunk, _to_pgvector_literal(validated_embedding)))

    async with pool.connection() as connection:
        async with connection.transaction():
            document_cursor = await connection.execute(
                """
                INSERT INTO documents
                    (title, source, document_type, content_sha256)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (content_sha256) DO NOTHING
                RETURNING id
                """,
                (
                    request.title,
                    request.source,
                    request.document_type,
                    content_sha256,
                ),
            )
            document_row = await document_cursor.fetchone()
            if document_row is None:
                existing_document = await _find_document_by_hash(
                    connection,
                    content_sha256,
                )
                if existing_document is None:
                    raise RuntimeError(
                        "Document insert conflicted but the existing document "
                        "could not be found"
                    )
                return existing_document

            document_id = int(document_row[0])
            for chunk_index, (chunk, vector_literal) in enumerate(embedded_chunks):
                await connection.execute(
                    """
                    INSERT INTO document_chunks
                        (document_id, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s::vector)
                    """,
                    (document_id, chunk_index, chunk, vector_literal),
                )

    return DocumentIngestionResponse(
        document_id=document_id,
        title=request.title,
        document_type=request.document_type,
        chunk_count=len(embedded_chunks),
    )


async def _find_document_by_hash(
    connection: AsyncConnection,
    content_sha256: str,
) -> DocumentIngestionResponse | None:
    cursor = await connection.execute(
        """
        SELECT documents.id, documents.title, documents.document_type,
               COUNT(document_chunks.id)
        FROM documents
        LEFT JOIN document_chunks ON document_chunks.document_id = documents.id
        WHERE documents.content_sha256 = %s
        GROUP BY documents.id, documents.title, documents.document_type
        """,
        (content_sha256,),
    )
    document_row = await cursor.fetchone()
    if document_row is None:
        return None

    return DocumentIngestionResponse(
        document_id=int(document_row[0]),
        title=document_row[1],
        document_type=document_row[2],
        chunk_count=int(document_row[3]),
        content_already_existed=True,
    )