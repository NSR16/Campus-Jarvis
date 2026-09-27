# Campus JARVIS Backend

The backend is a small FastAPI application. It provides a health endpoint, reads local configuration from environment variables, manages PostgreSQL connections with Psycopg 3's async pool, and contains an isolated async client for Ollama embeddings. Schema setup is an explicit command; API startup never creates or modifies database objects.

## Requirements

- Python 3.11+
- `uv`
- PostgreSQL with the pgvector extension installed is required to run the API or initialize the schema.
- Ollama is not required to run the test suite because the embedding client tests use mocked HTTP responses.

## Setup

From the `backend/` directory:

```powershell
uv sync
Copy-Item .env.example .env
```

The `.env` file is local-only and is ignored by Git. Set its `DATABASE_*` values to the PostgreSQL database you intend to use.

## PostgreSQL and schema setup

Create the database if it does not exist, for example from PowerShell with PostgreSQL command-line tools installed:

```powershell
createdb -U postgres campus_jarvis
```

The PostgreSQL server must have pgvector installed. Schema initialization runs `CREATE EXTENSION IF NOT EXISTS vector` against the exact database selected by `.env`. This extension must be available and enabled in that actual database; if the configured database user cannot create extensions, have an administrator enable it there first:

```powershell
psql -U postgres -d campus_jarvis -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

From `backend/`, initialize or re-check the schema explicitly:

```powershell
uv run python -m app.db.initialize_schema
```

The schema script is safe to run repeatedly for this initial schema. It creates tables and indexes only when absent; it is not a versioned migration system and will not rewrite existing objects. The API process opens its connection pool at startup and requires PostgreSQL to be reachable, but does not initialize the schema.

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

## Embedding service

`app/services/embeddings.py` calls Ollama's `POST /api/embed` endpoint with the configured model and text. It returns the first non-empty numeric vector from the `embeddings` response field and raises application-level errors for connection failures, HTTP failures, and malformed responses.

It can be called later from an application service or route without coupling it to FastAPI:

```python
from app.services.embeddings import generate_embedding

vector = await generate_embedding("A campus notice", settings)
```

Configure `OLLAMA_BASE_URL` and `EMBEDDING_MODEL` in `.env`. The default values are `http://localhost:11434` and `nomic-embed-text`.

## Document ingestion

`POST /documents` accepts JSON containing `title`, `source`, `document_type`, and `content`. The API chunks the text into 500-word pieces with 50-word overlap, generates one embedding for each distinct chunk, checks that each vector has 768 finite numeric values, and writes the document and chunks in one database transaction. The embedding and persistence work lives in `app/services/ingestion.py`; the route does not contain SQL or Ollama client logic.

## Manual end-to-end verification

These steps are explicit and are not run by pytest. They create a real document in the configured database.

1. Ensure PostgreSQL and the schema are ready using the setup above. Confirm `.env` points at the intended database.
2. In an Ollama terminal, start the server if it is not already running:

	```powershell
	ollama serve
	```

3. In another terminal, make sure the embedding model is available:

	```powershell
	ollama pull nomic-embed-text
	```

4. From `backend/`, start FastAPI:

	```powershell
	uv run uvicorn app.main:app --reload
	```

5. In a PowerShell terminal, submit a sample campus notice:

	```powershell
	$body = @{
		 title = "Library hours"
		 source = "manual-verification-library-hours.txt"
		 document_type = "notice"
		 content = "The campus library is open Monday through Friday from 9 AM to 5 PM. It is closed on public holidays."
	} | ConvertTo-Json

	$result = Invoke-RestMethod `
		 -Uri "http://localhost:8000/documents" `
		 -Method Post `
		 -ContentType "application/json" `
		 -Body $body

	$result
	```

	Record the returned `document_id`.

6. Connect to that same database and check metadata and chunk count (replace `DOCUMENT_ID` with the returned ID):

	```sql
	SELECT d.id, d.title, d.source, d.document_type, COUNT(c.id) AS chunk_count
	FROM documents AS d
	LEFT JOIN document_chunks AS c ON c.document_id = d.id
	WHERE d.id = DOCUMENT_ID
	GROUP BY d.id, d.title, d.source, d.document_type;
	```

7. Check that every chunk has a non-null 768-dimensional embedding:

	```sql
	SELECT document_id, chunk_index,
			 vector_dims(embedding) AS embedding_dimensions,
			 embedding IS NOT NULL AS has_embedding
	FROM document_chunks
	WHERE document_id = DOCUMENT_ID
	ORDER BY chunk_index;
	```

Pytest uses mocked embedding and database boundaries and does not insert this sample or modify the live database.

## Database foundation boundaries

- `app/main.py` creates the FastAPI application, configures local CORS, and opens/closes the connection pool through its lifespan.
- `app/api/routes/health.py` contains the health route; `app/api/routes/documents.py` validates and delegates ingestion requests.
- `app/core/config.py` loads typed settings from environment variables and `.env`.
- `app/db/connection.py` builds safely escaped connection info from the existing PostgreSQL settings and creates the async pool.
- `app/db/schema.sql` defines the initial tables and indexes; `app/db/initialize_schema.py` is the explicit schema command.
- `app/services/chunking.py` splits plain text into configurable word chunks.
- `app/services/embeddings.py` contains the direct async Ollama embedding client.
- `app/services/ingestion.py` coordinates embeddings and transactional document/chunk persistence.

This phase does not add semantic search, chat, PDF extraction, or frontend changes. Database values are passed as Psycopg query parameters; vector data is serialized to pgvector's input format and bound with an explicit `::vector` cast.
