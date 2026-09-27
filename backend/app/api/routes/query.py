import psycopg
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from psycopg_pool import PoolTimeout

from app.services.embeddings import OllamaEmbeddingError
from app.services.retrieval import (
    RetrievalEmbeddingError,
    RetrievedChunk,
    retrieve_chunks,
)

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, strict=True)

    @field_validator("query")
    @classmethod
    def require_non_empty_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be empty")
        return value


class QueryResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]


@router.post("", response_model=QueryResponse)
async def query_documents(
    payload: QueryRequest,
    request: Request,
) -> QueryResponse:
    try:
        results = await retrieve_chunks(
            payload.query,
            request.app.state.db_pool,
            payload.top_k,
        )
    except (OllamaEmbeddingError, RetrievalEmbeddingError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding generation failed.",
        ) from error
    except (psycopg.Error, PoolTimeout) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document retrieval is temporarily unavailable.",
        ) from error

    return QueryResponse(query=payload.query, results=results)