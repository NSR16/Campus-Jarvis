import httpx
import pytest

from app.core.config import Settings
from app.services import generation


class MockResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://ollama.test/api/generate")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "mock HTTP error",
                request=request,
                response=response,
            )

    def json(self) -> object:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class MockAsyncClient:
    def __init__(self, response: MockResponse | Exception) -> None:
        self.response = response
        self.endpoint: str | None = None
        self.payload: dict[str, str | bool] | None = None

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(
        self,
        endpoint: str,
        json: dict[str, str | bool],
    ) -> MockResponse:
        self.endpoint = endpoint
        self.payload = json
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def make_settings() -> Settings:
    return Settings(
        ollama_base_url="http://ollama.test/",
        embedding_model="test-embedding-model",
        generation_model="test-generation-model",
    )


@pytest.mark.anyio
async def test_generate_text_sends_expected_request_and_returns_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MockAsyncClient(MockResponse({"response": "Library closes at 5 PM."}))
    client_options: dict[str, object] = {}

    def make_client(**kwargs: object) -> MockAsyncClient:
        client_options.update(kwargs)
        return client

    monkeypatch.setattr(generation.httpx, "AsyncClient", make_client)

    result = await generation.generate_text("When does the library close?", make_settings())

    assert result == "Library closes at 5 PM."
    assert client.endpoint == "http://ollama.test/api/generate"
    assert client.payload == {
        "model": "test-generation-model",
        "prompt": "When does the library close?",
        "stream": False,
    }
    assert client_options["timeout"] == generation.OLLAMA_GENERATION_TIMEOUT_SECONDS
    assert generation.OLLAMA_GENERATION_TIMEOUT_SECONDS > 30.0


@pytest.mark.anyio
async def test_generate_text_honors_custom_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MockAsyncClient(MockResponse({"response": "Generated."}))
    monkeypatch.setattr(generation.httpx, "AsyncClient", lambda **kwargs: client)
    settings = Settings(
        ollama_base_url="http://custom-ollama.test",
        generation_model="custom-model:latest",
    )

    await generation.generate_text("prompt", settings)

    assert client.endpoint == "http://custom-ollama.test/api/generate"
    assert client.payload == {
        "model": "custom-model:latest",
        "prompt": "prompt",
        "stream": False,
    }


@pytest.mark.anyio
async def test_generate_text_rejects_invalid_prompt() -> None:
    for prompt in ("", "   ", None):
        with pytest.raises(ValueError, match="prompt must be non-empty"):
            await generation.generate_text(prompt)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_generate_text_reports_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MockAsyncClient(httpx.ConnectError("offline"))
    monkeypatch.setattr(generation.httpx, "AsyncClient", lambda **kwargs: client)

    with pytest.raises(generation.GenerationConnectionError, match="reach Ollama"):
        await generation.generate_text("prompt", make_settings())


@pytest.mark.anyio
async def test_generate_text_reports_http_failure_and_preserves_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MockAsyncClient(MockResponse({}, status_code=503))
    monkeypatch.setattr(generation.httpx, "AsyncClient", lambda **kwargs: client)

    with pytest.raises(generation.GenerationHTTPError, match="HTTP 503") as error:
        await generation.generate_text("prompt", make_settings())

    assert error.value.status_code == 503


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        ValueError("invalid JSON"),
        {},
        {"response": 42},
        {"response": ""},
        {"response": "   "},
        ["not", "an", "object"],
    ],
)
async def test_generate_text_rejects_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
) -> None:
    client = MockAsyncClient(MockResponse(payload))
    monkeypatch.setattr(generation.httpx, "AsyncClient", lambda **kwargs: client)

    with pytest.raises(generation.GenerationResponseError):
        await generation.generate_text("prompt", make_settings())