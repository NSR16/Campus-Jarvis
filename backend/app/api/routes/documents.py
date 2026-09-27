import psycopg
from fastapi import APIRouter, HTTPException, Request, status
from psycopg_pool import PoolTimeout

from app.services.embeddings import OllamaEmbeddingError
from app.services.ingestion import (
    DocumentIngestionRequest,
    DocumentIngestionResponse,
    EmbeddingDimensionError,
    ingest_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    payload: DocumentIngestionRequest,
    request: Request,
) -> DocumentIngestionResponse:
    try:
        return await ingest_document(payload, request.app.state.db_pool)
    except (OllamaEmbeddingError, EmbeddingDimensionError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding generation failed.",
        ) from error
    except (psycopg.Error, PoolTimeout) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document storage is temporarily unavailable.",
        ) from error