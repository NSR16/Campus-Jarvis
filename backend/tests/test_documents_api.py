import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import documents
from app.services.embeddings import OllamaConnectionError
from app.services.ingestion import DocumentIngestionResponse


def make_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(documents.router)
    app.state.db_pool = object()
    return TestClient(app)


def test_create_document_returns_created_response(monkeypatch) -> None:
    async def fake_ingest(payload, pool):
        assert payload.title == "Library hours"
        assert pool is not None
        return DocumentIngestionResponse(
            document_id=23,
            title=payload.title,
            document_type=payload.document_type,
            chunk_count=2,
        )

    monkeypatch.setattr(documents, "ingest_document", fake_ingest)
    client = make_test_client()

    response = client.post(
        "/documents",
        json={
            "title": "Library hours",
            "source": "library.txt",
            "document_type": "notice",
            "content": "Library is open today.",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "document_id": 23,
        "title": "Library hours",
        "document_type": "notice",
        "chunk_count": 2,
    }


def test_create_document_rejects_empty_content() -> None:
    client = make_test_client()

    response = client.post(
        "/documents",
        json={
            "title": "Library hours",
            "source": "library.txt",
            "document_type": "notice",
            "content": "  \n ",
        },
    )

    assert response.status_code == 422


def test_embedding_failure_returns_generic_gateway_error(monkeypatch) -> None:
    async def fail_ingest(payload, pool):
        raise OllamaConnectionError("secret internal details")

    monkeypatch.setattr(documents, "ingest_document", fail_ingest)
    client = make_test_client()

    response = client.post(
        "/documents",
        json={
            "title": "Library hours",
            "source": "library.txt",
            "document_type": "notice",
            "content": "Library is open today.",
        },
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Embedding generation failed."}
    assert "secret internal details" not in response.text


def test_database_failure_returns_generic_service_error(monkeypatch) -> None:
    async def fail_ingest(payload, pool):
        raise psycopg.OperationalError("credentials and server details")

    monkeypatch.setattr(documents, "ingest_document", fail_ingest)
    client = make_test_client()

    response = client.post(
        "/documents",
        json={
            "title": "Library hours",
            "source": "library.txt",
            "document_type": "notice",
            "content": "Library is open today.",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Document storage is temporarily unavailable."}
    assert "credentials" not in response.text