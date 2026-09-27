import psycopg
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from psycopg_pool import PoolTimeout

from app.services.embeddings import OllamaEmbeddingError
from app.services.generation import GenerationError
from app.services.qa import QAResponseError, QAResult, answer_question
from app.services.retrieval import DEFAULT_TOP_K, RetrievalEmbeddingError

router = APIRouter(prefix="/ask", tags=["ask"])


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, strict=True)

    @field_validator("question")
    @classmethod
    def require_non_empty_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty")
        return value


@router.post("", response_model=QAResult)
async def ask_question(
    payload: AskRequest,
    request: Request,
) -> QAResult:
    try:
        return await answer_question(
            payload.question,
            request.app.state.db_pool,
            payload.top_k,
        )
    except (
        OllamaEmbeddingError,
        RetrievalEmbeddingError,
        GenerationError,
        QAResponseError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Question answering is temporarily unavailable.",
        ) from error
    except (psycopg.Error, PoolTimeout) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Question answering storage is temporarily unavailable.",
        ) from error