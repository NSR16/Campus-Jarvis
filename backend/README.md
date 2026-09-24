# Campus JARVIS Backend

The Phase 0 backend is a small FastAPI application. It provides a health endpoint, reads local configuration from environment variables, and keeps PostgreSQL connection settings separate from the HTTP API. It does not connect to PostgreSQL or implement the AI/RAG system yet.

## Requirements

- Python 3.11+
- `uv`
- PostgreSQL is not required to run Phase 0 because no database connection is opened yet.

## Setup

From the `backend/` directory:

```powershell
uv sync
Copy-Item .env.example .env
```

The `.env` file is local-only and is ignored by Git.

## Run the API

```powershell
uv run uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Open `http://localhost:8000/health` to receive:

```json
{"status":"ok"}
```

Interactive API documentation is available at `http://localhost:8000/docs`.

## Test

```powershell
uv run pytest
```

## Phase 0 boundaries

- `app/main.py` creates the FastAPI application and configures local CORS.
- `app/api/routes/health.py` contains the health route only.
- `app/core/config.py` loads typed settings from environment variables and `.env`.
- `app/db/connection.py` prepares PostgreSQL connection configuration without creating a schema or opening a connection.
- `app/services/` is reserved for later application services.

Future document ingestion, text chunking, embeddings, pgvector retrieval, Ollama integration, and RAG orchestration will be added as separate services and routes after the database access approach is decided.
