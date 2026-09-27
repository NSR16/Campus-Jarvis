import httpx
import pytest

from app.core.config import Settings
from app.services import embeddings


class MockResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://ollama.test/api/embed")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "mock HTTP error",
                request=request,
                response=response,
            )

    def json(self) -> object:
        return self.payload


class MockAsyncClient:
    def __init__(self, response: MockResponse | Exception) -> None:
        self.response = response
        self.endpoint: str | None = None
        self.payload: dict[str, str] | None = None

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, endpoint: str, json: dict[str, str]) -> MockResponse:
        self.endpoint = endpoint
        self.payload = json
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def make_settings() -> Settings:
    return Settings(
        ollama_base_url="http://ollama.test/",
        embedding_model="test-embedding-model",
    )


@pytest.mark.anyio
async def test_generate_embedding_returns_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MockAsyncClient(MockResponse({"embeddings": [[1, 2.5, -3]]}))
    monkeypatch.setattr(embeddings.httpx, "AsyncClient", lambda **kwargs: client)

    result = await embeddings.generate_embedding("campus notice", make_settings())

    assert result == [1.0, 2.5, -3.0]
    assert client.endpoint == "http://ollama.test/api/embed"
    assert client.payload == {
        "model": "test-embedding-model",
        "input": "campus notice",
    }


@pytest.mark.anyio
async def test_generate_embedding_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        await embeddings.generate_embedding("   ", make_settings())


@pytest.mark.anyio
async def test_generate_embedding_reports_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MockAsyncClient(httpx.ConnectError("offline"))
    monkeypatch.setattr(embeddings.httpx, "AsyncClient", lambda **kwargs: client)

    with pytest.raises(embeddings.OllamaConnectionError, match="reach Ollama"):
        await embeddings.generate_embedding("campus notice", make_settings())


@pytest.mark.anyio
async def test_generate_embedding_reports_http_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MockAsyncClient(MockResponse({}, status_code=500))
    monkeypatch.setattr(embeddings.httpx, "AsyncClient", lambda **kwargs: client)

    with pytest.raises(embeddings.OllamaHTTPError, match="HTTP 500"):
        await embeddings.generate_embedding("campus notice", make_settings())


@pytest.mark.anyio
async def test_generate_embedding_reports_malformed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MockAsyncClient(MockResponse({"embeddings": [[1, "bad"]]}))
    monkeypatch.setattr(embeddings.httpx, "AsyncClient", lambda **kwargs: client)

    with pytest.raises(embeddings.OllamaResponseError, match="non-numeric"):
        await embeddings.generate_embedding("campus notice", make_settings())