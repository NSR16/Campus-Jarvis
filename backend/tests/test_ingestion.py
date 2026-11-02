import hashlib

import psycopg
import pytest

from app.services import ingestion
from app.services.ingestion import DocumentIngestionRequest


class FakeCursor:
    def __init__(self, row: tuple[object, ...] | None) -> None:
        self.row = row

    async def fetchone(self) -> tuple[object, ...] | None:
        return self.row


class FakeTransaction:
    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection

    async def __aenter__(self) -> "FakeTransaction":
        self.connection.transaction_started = True
        return self

    async def __aexit__(self, exception_type: object, *_: object) -> None:
        self.connection.committed = exception_type is None
        self.connection.rolled_back = exception_type is not None


class FakeConnection:
    def __init__(
        self,
        fail_on_chunk: bool = False,
        existing_document: tuple[object, ...] | None = None,
        race_document: tuple[object, ...] | None = None,
    ) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.fail_on_chunk = fail_on_chunk
        self.existing_document = existing_document
        self.race_document = race_document
        self.document_insert_attempted = False
        self.transaction_started = False
        self.committed = False
        self.rolled_back = False

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)

    async def execute(self, query: str, params: tuple[object, ...]) -> FakeCursor:
        self.calls.append((query, params))
        if self.fail_on_chunk and "INSERT INTO document_chunks" in query:
            raise psycopg.OperationalError("mock database failure")
        if "SELECT documents.id" in query:
            row = (
                self.race_document
                if self.document_insert_attempted
                else self.existing_document
            )
            return FakeCursor(row)
        if "INSERT INTO documents" in query:
            self.document_insert_attempted = True
            if self.race_document is not None:
                return FakeCursor(None)
            return FakeCursor((73,))
        return FakeCursor(None)


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


def make_request() -> DocumentIngestionRequest:
    return DocumentIngestionRequest(
        title="Library Hours",
        source="library-hours.txt",
        document_type="notice",
        content="The library is open from nine until five.",
    )


def test_content_sha256_is_deterministic() -> None:
    assert ingestion._content_sha256("campus document") == ingestion._content_sha256(
        "campus document"
    )


def test_content_sha256_differs_for_different_strings() -> None:
    assert ingestion._content_sha256("campus document") != ingestion._content_sha256(
        "another campus document"
    )


def test_content_sha256_preserves_leading_and_trailing_whitespace() -> None:
    assert ingestion._content_sha256("campus document") != ingestion._content_sha256(
        " campus document "
    )


def test_content_sha256_returns_lowercase_sha256_hex() -> None:
    digest = ingestion._content_sha256("campus document")

    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


@pytest.mark.anyio
async def test_ingest_embeds_unique_chunks_and_persists_transactionally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    pool = FakePool(connection)
    generated: list[str] = []

    def fake_chunk_text(_: str) -> list[str]:
        return ["same chunk", "same chunk", "second chunk"]

    async def fake_generate_embedding(text: str) -> list[float]:
        generated.append(text)
        return [0.25] * ingestion.EMBEDDING_DIMENSIONS

    monkeypatch.setattr(ingestion, "chunk_text", fake_chunk_text)
    monkeypatch.setattr(ingestion, "generate_embedding", fake_generate_embedding)

    result = await ingestion.ingest_document(make_request(), pool)  # type: ignore[arg-type]

    assert result.document_id == 73
    assert result.title == "Library Hours"
    assert result.document_type == "notice"
    assert result.chunk_count == 2
    assert result.content_already_existed is False
    assert generated == ["same chunk", "second chunk"]
    assert connection.transaction_started is True
    assert connection.committed is True
    assert len(connection.calls) == 4
    lookup_query, lookup_params = connection.calls[0]
    assert "WHERE documents.content_sha256 = %s" in lookup_query
    expected_hash = hashlib.sha256(make_request().content.encode("utf-8")).hexdigest()
    assert lookup_params == (expected_hash,)
    document_query, document_params = connection.calls[1]
    assert "ON CONFLICT (content_sha256) DO NOTHING" in document_query
    assert "(title, source, document_type, content_sha256)" in document_query
    assert document_params == (
        "Library Hours",
        "library-hours.txt",
        "notice",
        expected_hash,
    )
    chunk_query, chunk_params = connection.calls[2]
    assert "%s::vector" in chunk_query
    assert chunk_params[:3] == (73, 0, "same chunk")
    assert chunk_params[3].startswith("[")  # pgvector literal is bound as a parameter


@pytest.mark.anyio
async def test_repeated_content_returns_existing_document_before_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection(existing_document=(91, "Canonical title", "guide", 3))
    pool = FakePool(connection)
    generated: list[str] = []

    async def unexpected_embedding(text: str) -> list[float]:
        generated.append(text)
        raise AssertionError("duplicate content must be checked before embedding")

    monkeypatch.setattr(ingestion, "generate_embedding", unexpected_embedding)

    request = DocumentIngestionRequest(
        title="Different title",
        source="different-source.txt",
        document_type="notice",
        content=make_request().content,
    )
    result = await ingestion.ingest_document(request, pool)  # type: ignore[arg-type]

    assert result.document_id == 91
    assert result.title == "Canonical title"
    assert result.document_type == "guide"
    assert result.chunk_count == 3
    assert result.content_already_existed is True
    assert generated == []
    assert len(connection.calls) == 1
    assert all("INSERT INTO" not in query for query, _ in connection.calls)
    assert connection.calls[0][1] == (
        hashlib.sha256(request.content.encode("utf-8")).hexdigest(),
    )


@pytest.mark.anyio
async def test_different_content_from_same_source_is_ingested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    pool = FakePool(connection)

    async def fake_generate_embedding(_: str) -> list[float]:
        return [0.1] * ingestion.EMBEDDING_DIMENSIONS

    monkeypatch.setattr(ingestion, "generate_embedding", fake_generate_embedding)
    request = DocumentIngestionRequest(
        title="Updated hours",
        source="library-hours.txt",
        document_type="notice",
        content="The library closes at six today.",
    )

    result = await ingestion.ingest_document(request, pool)  # type: ignore[arg-type]

    assert result.document_id == 73
    assert result.content_already_existed is False
    insert_query, insert_params = next(
        (query, params)
        for query, params in connection.calls
        if "INSERT INTO documents" in query
    )
    assert "ON CONFLICT (content_sha256) DO NOTHING" in insert_query
    assert insert_params[1] == "library-hours.txt"
    assert insert_params[3] == hashlib.sha256(request.content.encode("utf-8")).hexdigest()


@pytest.mark.anyio
async def test_legacy_null_hash_document_does_not_match_hash_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    pool = FakePool(connection)

    async def fake_generate_embedding(_: str) -> list[float]:
        return [0.1] * ingestion.EMBEDDING_DIMENSIONS

    monkeypatch.setattr(ingestion, "generate_embedding", fake_generate_embedding)

    result = await ingestion.ingest_document(make_request(), pool)  # type: ignore[arg-type]

    assert result.content_already_existed is False
    lookup_query, lookup_params = connection.calls[0]
    assert "WHERE documents.content_sha256 = %s" in lookup_query
    assert "IS NULL" not in lookup_query
    assert lookup_params == (
        hashlib.sha256(make_request().content.encode("utf-8")).hexdigest(),
    )
    assert all(
        "UPDATE documents" not in query and "DELETE FROM documents" not in query
        for query, _ in connection.calls
    )


@pytest.mark.anyio
async def test_concurrent_duplicate_insert_returns_canonical_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection(race_document=(82, "Winning title", "notice", 2))
    pool = FakePool(connection)
    generated: list[str] = []

    async def fake_generate_embedding(text: str) -> list[float]:
        generated.append(text)
        return [0.1] * ingestion.EMBEDDING_DIMENSIONS

    monkeypatch.setattr(ingestion, "generate_embedding", fake_generate_embedding)

    result = await ingestion.ingest_document(make_request(), pool)  # type: ignore[arg-type]

    assert result.document_id == 82
    assert result.title == "Winning title"
    assert result.chunk_count == 2
    assert result.content_already_existed is True
    assert generated
    assert sum("INSERT INTO documents" in query for query, _ in connection.calls) == 1
    assert not any("INSERT INTO document_chunks" in query for query, _ in connection.calls)


@pytest.mark.anyio
async def test_invalid_embedding_dimensions_fail_without_writing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    pool = FakePool(connection)

    async def wrong_dimensions(_: str) -> list[float]:
        return [0.1, 0.2]

    monkeypatch.setattr(ingestion, "generate_embedding", wrong_dimensions)

    with pytest.raises(ingestion.EmbeddingDimensionError):
        await ingestion.ingest_document(make_request(), pool)  # type: ignore[arg-type]

    assert pool.connection_requested is True
    assert len(connection.calls) == 1
    assert "SELECT documents.id" in connection.calls[0][0]
    assert all("INSERT INTO" not in query for query, _ in connection.calls)


@pytest.mark.anyio
async def test_chunk_insert_failure_rolls_back_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection(fail_on_chunk=True)
    pool = FakePool(connection)

    async def fake_generate_embedding(_: str) -> list[float]:
        return [0.1] * ingestion.EMBEDDING_DIMENSIONS

    monkeypatch.setattr(ingestion, "generate_embedding", fake_generate_embedding)

    with pytest.raises(psycopg.OperationalError):
        await ingestion.ingest_document(make_request(), pool)  # type: ignore[arg-type]

    assert connection.rolled_back is True
    assert connection.committed is False