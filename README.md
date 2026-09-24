# Campus JARVIS

Campus JARVIS is a private, campus-specific AI assistant for the ASYNC'26 Sovereign AI track.

This repository currently contains only the Phase 0 foundation:

- `backend/`: FastAPI application with configuration, PostgreSQL connection settings, and `GET /health`.
- `frontend/`: minimal React + TypeScript + Vite application.
- `data/`: reserved for local development data in later phases.

AI/RAG functionality is intentionally not implemented yet. Future phases will add document ingestion, chunking, embeddings, pgvector retrieval, local Ollama generation, grounded sources, and user-approved actions with audit logging.

## Run locally

Start the backend from `backend/`:

```powershell
uv sync
uv run uvicorn app.main:app --reload
```

Start the frontend from `frontend/`:

```powershell
npm install
npm run dev
```

See `backend/README.md` for backend configuration and test instructions.
