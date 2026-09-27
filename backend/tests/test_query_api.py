import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import PoolTimeout

from app.api.routes import query
from app.services.embeddings import OllamaConnectionError
from app.services.retrieval import RetrievalEmbeddingError, RetrievedChunk


def make_test_client(pool: object | None = None) -> tuple[TestClient, object]:
    app = FastAPI()
    app.include_router(query.router)
    db_pool = pool if pool is not None else object()
    app.state.db_pool = db_pool
    return TestClient(app), db_pool


def make_result() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=41,
        document_id=7,
        title="Library hours",
        source="library.txt",
        document_type="notice",
        chunk_index=0,
        content="The library closes at 5 PM.",
        distance=0.12,
    )


def test_query_returns_results_and_passes_request_to_retrieval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, pool = make_test_client()

    async def fake_retrieve_chunks(query_text: str, received_pool: object, top_k: int):
        assert query_text == "When does the library close?"
        assert received_pool is pool
        assert top_k == 3
        return [make_result()]

    monkeypatch.setattr(query, "retrieve_chunks", fake_retrieve_chunks)

    response = client.post(
        "/query",
        json={"query": "When does the library close?", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "When does the library close?",
        "results": [
            {
                "chunk_id": 41,
                "document_id": 7,
                "title": "Library hours",
                "source": "library.txt",
                "document_type": "notice",
                "chunk_index": 0,
                "content": "The library closes at 5 PM.",
                "distance": 0.12,
            }
        ],
    }


@pytest.mark.parametrize("query_text", ["", "   ", "\n\t"])
def test_query_rejects_empty_or_whitespace_query(query_text: str) -> None:
    client, _ = make_test_client()

    response = client.post("/query", json={"query": query_text})

    assert response.status_code == 422


@pytest.mark.parametrize("top_k", [0, -1, True, "3", 1.5])
def test_query_rejects_invalid_top_k(top_k: object) -> None:
    client, _ = make_test_client()

    response = client.post("/query", json={"query": "library hours", "top_k": top_k})

    assert response.status_code == 422


def test_query_returns_empty_results_when_no_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_retrieve_chunks(query_text: str, pool: object, top_k: int):
        return []

    monkeypatch.setattr(query, "retrieve_chunks", fake_retrieve_chunks)
    client, _ = make_test_client()

    response = client.post("/query", json={"query": "unknown campus topic"})

    assert response.status_code == 200
    assert response.json() == {"query": "unknown campus topic", "results": []}


@pytest.mark.parametrize(
    "error",
    [
        RetrievalEmbeddingError("invalid dimensions"),
        OllamaConnectionError("internal embedding details"),
    ],
)
def test_query_maps_embedding_errors_to_bad_gateway(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    async def fail_retrieval(query_text: str, pool: object, top_k: int):
        raise error

    monkeypatch.setattr(query, "retrieve_chunks", fail_retrieval)
    client, _ = make_test_client()

    response = client.post("/query", json={"query": "library hours"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Embedding generation failed."}
    assert "internal embedding details" not in response.text


@pytest.mark.parametrize(
    "error",
    [
        psycopg.OperationalError("database credentials"),
        PoolTimeout("pool timeout"),
    ],
)
def test_query_maps_database_and_pool_errors_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    async def fail_retrieval(query_text: str, pool: object, top_k: int):
        raise error

    monkeypatch.setattr(query, "retrieve_chunks", fail_retrieval)
    client, _ = make_test_client()

    response = client.post("/query", json={"query": "library hours"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Document retrieval is temporarily unavailable."
    }
    assert "database credentials" not in response.text