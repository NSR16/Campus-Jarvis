import psycopg
import pytest

from app.services import retrieval
from app.services.embeddings import OllamaConnectionError


class FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    async def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class FakeConnection:
    def __init__(self, rows: list[tuple[object, ...]] | None = None) -> None:
        self.rows = rows or []
        self.query: str | None = None
        self.params: tuple[object, ...] | None = None
        self.fail = False

    async def execute(
        self,
        query: str,
        params: tuple[object, ...],
    ) -> FakeCursor:
        self.query = query
        self.params = params
        if self.fail:
            raise psycopg.OperationalError("mock database failure")
        return FakeCursor(self.rows)


class FakePool:
    def __init__(self, connection: FakeConnection) -> None:
        self.fake_connection = connection
        self.connection_requested = False

    def connection(self) -> "FakePool":
        self.connection_requested = True
        return self

    async def __aenter__(self) -> FakeConnection:
        return self.fake_connection

    async def __aexit__(self, *_: object) -> None:
        return None


def make_embedding() -> list[float]:
    return [0.25] * retrieval.EMBEDDING_DIMENSIONS


def make_row(
    chunk_id: int,
    document_id: int,
    content: str,
    distance: float,
    title: str | None = None,
) -> tuple[object, ...]:
    return (
        chunk_id,
        document_id,
        title or f"Document {document_id}",
        f"document-{document_id}.txt",
        "notice",
        chunk_id,
        content,
        distance,
    )


async def retrieve_rows(
    monkeypatch: pytest.MonkeyPatch,
    rows: list[tuple[object, ...]],
    top_k: int,
) -> tuple[list[retrieval.RetrievedChunk], FakeConnection]:
    connection = FakeConnection(rows)

    async def fake_generate_embedding(_: str) -> list[float]:
        return make_embedding()

    monkeypatch.setattr(retrieval, "generate_embedding", fake_generate_embedding)
    results = await retrieval.retrieve_chunks(
        "question",
        FakePool(connection),  # type: ignore[arg-type]
        top_k=top_k,
    )
    return results, connection


@pytest.mark.anyio
async def test_retrieve_chunks_returns_nearest_chunks_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection(
        [
            (41, 7, "Library Hours", "library.txt", "notice", 0, "Open 9 to 5", 0.1),
            (42, 8, "Exam Schedule", "exam.pdf", "schedule", 2, "Finals start Monday", 0.2),
        ]
    )
    pool = FakePool(connection)
    embedded_queries: list[str] = []

    async def fake_generate_embedding(query: str) -> list[float]:
        embedded_queries.append(query)
        return make_embedding()

    monkeypatch.setattr(retrieval, "generate_embedding", fake_generate_embedding)

    results = await retrieval.retrieve_chunks("  campus hours  ", pool, top_k=2)  # type: ignore[arg-type]

    assert embedded_queries == ["campus hours"]
    assert [result.chunk_id for result in results] == [41, 42]
    assert results[0].source == "library.txt"
    assert results[0].content == "Open 9 to 5"
    assert results[0].distance == 0.1
    assert connection.query is not None
    assert "JOIN documents ON documents.id = document_chunks.document_id" in connection.query
    assert "<=> %s::vector" in connection.query
    assert "document_chunks.embedding <=> %s::vector ASC" in connection.query
    assert "document_chunks.id ASC" in connection.query
    assert "document_chunks.id ASC" in connection.query
    assert "LIMIT %s" in connection.query
    assert connection.params == ("[" + ",".join(["0.25"] * 768) + "]",) * 2 + (4,)


@pytest.mark.anyio
async def test_retrieve_chunks_deduplicates_exact_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results, _ = await retrieve_rows(
        monkeypatch,
        [
            make_row(1, 7, "Repeated content", 0.1),
            make_row(2, 7, "Repeated content", 0.2),
            make_row(3, 7, "Other content", 0.3),
        ],
        top_k=2,
    )

    assert [result.chunk_id for result in results] == [1, 3]


@pytest.mark.anyio
async def test_retrieve_chunks_deduplicates_content_across_documents_and_keeps_nearest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results, _ = await retrieve_rows(
        monkeypatch,
        [
            make_row(1, 7, "Shared content", 0.1, title="Nearest document"),
            make_row(2, 8, "Shared content", 0.2, title="Other document"),
            make_row(3, 9, "Unique content", 0.3),
        ],
        top_k=2,
    )

    assert [result.chunk_id for result in results] == [1, 3]
    assert results[0].document_id == 7
    assert results[0].title == "Nearest document"
    assert results[0].distance == 0.1


@pytest.mark.anyio
async def test_retrieve_chunks_keeps_different_content_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results, _ = await retrieve_rows(
        monkeypatch,
        [
            make_row(1, 7, "First content", 0.1),
            make_row(2, 7, "Different content", 0.2),
        ],
        top_k=2,
    )

    assert [result.content for result in results] == [
        "First content",
        "Different content",
    ]


@pytest.mark.anyio
async def test_retrieve_chunks_returns_fewer_when_candidate_pool_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results, connection = await retrieve_rows(
        monkeypatch,
        [
            make_row(1, 7, "Repeated content", 0.1),
            make_row(2, 8, "Repeated content", 0.2),
            make_row(3, 9, "Only other content", 0.3),
        ],
        top_k=3,
    )

    assert [result.chunk_id for result in results] == [1, 3]
    assert connection.params is not None
    assert connection.params[-1] == 6


@pytest.mark.anyio
async def test_retrieve_chunks_top_k_one_fetches_two_candidates_and_returns_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results, connection = await retrieve_rows(
        monkeypatch,
        [
            make_row(1, 7, "Repeated content", 0.1),
            make_row(2, 8, "Repeated content", 0.2),
        ],
        top_k=1,
    )

    assert [result.chunk_id for result in results] == [1]
    assert connection.params is not None
    assert connection.params[-1] == 2


@pytest.mark.anyio
async def test_retrieve_chunks_content_deduplication_is_whitespace_sensitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results, _ = await retrieve_rows(
        monkeypatch,
        [
            make_row(1, 7, "Exact content", 0.1),
            make_row(2, 7, "Exact content ", 0.2),
        ],
        top_k=2,
    )

    assert [result.content for result in results] == [
        "Exact content",
        "Exact content ",
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["", "   ", None])
async def test_retrieve_chunks_rejects_invalid_query_before_embedding(
    monkeypatch: pytest.MonkeyPatch,
    query: object,
) -> None:
    pool = FakePool(FakeConnection())

    async def unexpected_embedding(_: str) -> list[float]:
        raise AssertionError("embedding should not be called")

    monkeypatch.setattr(retrieval, "generate_embedding", unexpected_embedding)

    with pytest.raises(ValueError, match="Query must be non-empty"):
        await retrieval.retrieve_chunks(query, pool)  # type: ignore[arg-type]

    assert pool.connection_requested is False


@pytest.mark.anyio
@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
async def test_retrieve_chunks_rejects_invalid_top_k(top_k: object) -> None:
    pool = FakePool(FakeConnection())

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        await retrieval.retrieve_chunks("query", pool, top_k=top_k)  # type: ignore[arg-type]

    assert pool.connection_requested is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    "embedding",
    [
        [0.1, 0.2],
        [0.1] * (retrieval.EMBEDDING_DIMENSIONS - 1) + [float("nan")],
        [0.1] * (retrieval.EMBEDDING_DIMENSIONS - 1) + [True],
    ],
)
async def test_retrieve_chunks_rejects_invalid_embedding_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
    embedding: list[float],
) -> None:
    pool = FakePool(FakeConnection())

    async def fake_generate_embedding(_: str) -> list[float]:
        return embedding

    monkeypatch.setattr(retrieval, "generate_embedding", fake_generate_embedding)

    with pytest.raises(retrieval.RetrievalEmbeddingError):
        await retrieval.retrieve_chunks("query", pool)  # type: ignore[arg-type]

    assert pool.connection_requested is False


@pytest.mark.anyio
async def test_retrieve_chunks_propagates_embedding_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = FakePool(FakeConnection())

    async def fail_embedding(_: str) -> list[float]:
        raise OllamaConnectionError("offline")

    monkeypatch.setattr(retrieval, "generate_embedding", fail_embedding)

    with pytest.raises(OllamaConnectionError, match="offline"):
        await retrieval.retrieve_chunks("query", pool)  # type: ignore[arg-type]

    assert pool.connection_requested is False


@pytest.mark.anyio
async def test_retrieve_chunks_propagates_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    connection.fail = True
    pool = FakePool(connection)

    async def fake_generate_embedding(_: str) -> list[float]:
        return make_embedding()

    monkeypatch.setattr(retrieval, "generate_embedding", fake_generate_embedding)

    with pytest.raises(psycopg.OperationalError, match="mock database failure"):
        await retrieval.retrieve_chunks("query", pool)  # type: ignore[arg-type]

    assert pool.connection_requested is True