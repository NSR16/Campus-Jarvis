import psycopg
import pytest

from app.services import ingestion
from app.services.ingestion import DocumentIngestionRequest


class FakeCursor:
    async def fetchone(self) -> tuple[int]:
        return (73,)


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
    def __init__(self, fail_on_chunk: bool = False) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.fail_on_chunk = fail_on_chunk
        self.transaction_started = False
        self.committed = False
        self.rolled_back = False

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)

    async def execute(self, query: str, params: tuple[object, ...]) -> FakeCursor:
        self.calls.append((query, params))
        if self.fail_on_chunk and "INSERT INTO document_chunks" in query:
            raise psycopg.OperationalError("mock database failure")
        return FakeCursor()


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
    assert generated == ["same chunk", "second chunk"]
    assert connection.transaction_started is True
    assert connection.committed is True
    assert len(connection.calls) == 3
    document_query, document_params = connection.calls[0]
    assert "VALUES (%s, %s, %s)" in document_query
    assert document_params == ("Library Hours", "library-hours.txt", "notice")
    chunk_query, chunk_params = connection.calls[1]
    assert "%s::vector" in chunk_query
    assert chunk_params[:3] == (73, 0, "same chunk")
    assert chunk_params[3].startswith("[")  # pgvector literal is bound as a parameter


@pytest.mark.anyio
async def test_invalid_embedding_dimensions_fail_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    pool = FakePool(connection)

    async def wrong_dimensions(_: str) -> list[float]:
        return [0.1, 0.2]

    monkeypatch.setattr(ingestion, "generate_embedding", wrong_dimensions)

    with pytest.raises(ingestion.EmbeddingDimensionError):
        await ingestion.ingest_document(make_request(), pool)  # type: ignore[arg-type]

    assert pool.connection_requested is False


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