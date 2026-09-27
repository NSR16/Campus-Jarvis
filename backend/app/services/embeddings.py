from typing import Any

import httpx

from app.core.config import Settings, get_settings

OLLAMA_EMBEDDING_TIMEOUT_SECONDS = 30.0


class OllamaEmbeddingError(Exception):
    """Base error for failures while generating an Ollama embedding."""


class OllamaConnectionError(OllamaEmbeddingError):
    """Ollama could not be reached or the request timed out."""


class OllamaHTTPError(OllamaEmbeddingError):
    """Ollama returned an unsuccessful HTTP response."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"Ollama embedding request failed with HTTP {status_code}")
        self.status_code = status_code


class OllamaResponseError(OllamaEmbeddingError):
    """Ollama returned a response that is not a valid embedding."""


async def generate_embedding(
    text: str,
    settings: Settings | None = None,
) -> list[float]:
    """Generate one embedding for non-empty text using Ollama's embed API."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Embedding text must be non-empty")

    current_settings = settings or get_settings()
    endpoint = f"{current_settings.ollama_base_url.rstrip('/')}/api/embed"
    payload = {
        "model": current_settings.embedding_model,
        "input": text,
    }

    try:
        async with httpx.AsyncClient(
            timeout=OLLAMA_EMBEDDING_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise OllamaHTTPError(error.response.status_code) from error
    except httpx.RequestError as error:
        raise OllamaConnectionError("Could not reach Ollama") from error

    try:
        response_data: Any = response.json()
    except ValueError as error:
        raise OllamaResponseError("Ollama returned invalid JSON") from error

    if not isinstance(response_data, dict):
        raise OllamaResponseError("Ollama returned an invalid embedding response")

    embeddings = response_data.get("embeddings")
    if not isinstance(embeddings, list) or not embeddings:
        raise OllamaResponseError("Ollama response did not contain embeddings")

    vector = embeddings[0]
    if not isinstance(vector, list) or not vector:
        raise OllamaResponseError("Ollama response contained an empty embedding")

    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in vector
    ):
        raise OllamaResponseError("Ollama embedding contained a non-numeric value")

    return [float(value) for value in vector]