import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import PoolTimeout

from app.api.routes import ask
from app.services.embeddings import OllamaConnectionError
from app.services.generation import GenerationResponseError
from app.services.qa import QAResponseError, QACitation, QAResult
from app.services.retrieval import RetrievalEmbeddingError


def make_test_client(pool: object | None = None) -> tuple[TestClient, object]:
    app = FastAPI()
    app.include_router(ask.router)
    db_pool = pool if pool is not None else object()
    app.state.db_pool = db_pool
    return TestClient(app), db_pool


def make_result(*, insufficient_evidence: bool = False) -> QAResult:
    return QAResult(
        answer="The library closes at 5 PM.",
        citations=[
            QACitation(
                chunk_id=41,
                document_id=7,
                title="Library hours",
                source="library.txt",
                document_type="notice",
                chunk_index=0,
            )
        ],
        insufficient_evidence=insufficient_evidence,
    )


def test_ask_returns_qa_result_and_forwards_question_pool_and_top_k(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, pool = make_test_client()

    async def fake_answer_question(
        question: str,
        received_pool: object,
        top_k: int,
    ) -> QAResult:
        assert question == "When does the library close?"
        assert received_pool is pool
        assert top_k == 3
        return make_result()

    monkeypatch.setattr(ask, "answer_question", fake_answer_question)

    response = client.post(
        "/ask",
        json={"question": "When does the library close?", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "The library closes at 5 PM.",
        "citations": [
            {
                "chunk_id": 41,
                "document_id": 7,
                "title": "Library hours",
                "source": "library.txt",
                "document_type": "notice",
                "chunk_index": 0,
            }
        ],
        "insufficient_evidence": False,
    }


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_ask_rejects_empty_or_whitespace_question(question: str) -> None:
    client, _ = make_test_client()

    response = client.post("/ask", json={"question": question})

    assert response.status_code == 422


@pytest.mark.parametrize("top_k", [0, -1, True, "3", 1.5])
def test_ask_rejects_invalid_top_k(top_k: object) -> None:
    client, _ = make_test_client()

    response = client.post("/ask", json={"question": "library hours", "top_k": top_k})

    assert response.status_code == 422


def test_ask_returns_insufficient_evidence_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_answer_question(
        question: str,
        pool: object,
        top_k: int,
    ) -> QAResult:
        return QAResult(
            answer="I could not find relevant campus documents to answer that question.",
            citations=[],
            insufficient_evidence=True,
        )

    monkeypatch.setattr(ask, "answer_question", fake_answer_question)
    client, _ = make_test_client()

    response = client.post("/ask", json={"question": "unknown campus topic"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "I could not find relevant campus documents to answer that question.",
        "citations": [],
        "insufficient_evidence": True,
    }


@pytest.mark.parametrize(
    "error",
    [
        OllamaConnectionError("embedding internal details"),
        RetrievalEmbeddingError("invalid dimensions"),
        GenerationResponseError("generation internal details"),
        QAResponseError("invalid generated JSON"),
    ],
)
def test_ask_maps_qa_and_model_errors_to_bad_gateway(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    async def fail_answer_question(
        question: str,
        pool: object,
        top_k: int,
    ) -> QAResult:
        raise error

    monkeypatch.setattr(ask, "answer_question", fail_answer_question)
    client, _ = make_test_client()

    response = client.post("/ask", json={"question": "library hours"})

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Question answering is temporarily unavailable."
    }
    assert "internal details" not in response.text


@pytest.mark.parametrize(
    "error",
    [
        psycopg.OperationalError("database credentials"),
        PoolTimeout("pool timeout"),
    ],
)
def test_ask_maps_database_and_pool_errors_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    async def fail_answer_question(
        question: str,
        pool: object,
        top_k: int,
    ) -> QAResult:
        raise error

    monkeypatch.setattr(ask, "answer_question", fail_answer_question)
    client, _ = make_test_client()

    response = client.post("/ask", json={"question": "library hours"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Question answering storage is temporarily unavailable."
    }
    assert "database credentials" not in response.text