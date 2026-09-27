from typing import Any

import httpx

from app.core.config import Settings, get_settings

OLLAMA_GENERATION_TIMEOUT_SECONDS = 120.0


class GenerationError(Exception):
    """Base error for failures while generating text with Ollama."""


class GenerationConnectionError(GenerationError):
    """Ollama could not be reached or the request timed out."""


class GenerationHTTPError(GenerationError):
    """Ollama returned an unsuccessful HTTP response."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"Ollama generation request failed with HTTP {status_code}")
        self.status_code = status_code


class GenerationResponseError(GenerationError):
    """Ollama returned a response that is not valid generated text."""


async def generate_text(
    prompt: str,
    settings: Settings | None = None,
) -> str:
    """Generate one non-empty text response from Ollama."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Generation prompt must be non-empty")

    current_settings = settings or get_settings()
    endpoint = f"{current_settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": current_settings.generation_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(
            timeout=OLLAMA_GENERATION_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise GenerationHTTPError(error.response.status_code) from error
    except httpx.RequestError as error:
        raise GenerationConnectionError("Could not reach Ollama") from error

    try:
        response_data: Any = response.json()
    except ValueError as error:
        raise GenerationResponseError("Ollama returned invalid JSON") from error

    if not isinstance(response_data, dict):
        raise GenerationResponseError("Ollama returned an invalid generation response")

    generated_text = response_data.get("response")
    if not isinstance(generated_text, str) or not generated_text.strip():
        raise GenerationResponseError(
            "Ollama response did not contain non-empty generated text"
        )

    return generated_text