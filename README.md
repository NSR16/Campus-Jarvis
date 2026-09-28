
# Campus Brain - JARVIS 🧠

### A Private, Locally-Powered AI Knowledge Assistant for Campus

Campus JARVIS is a campus-focused AI assistant designed to help students access information from campus notices, documents, and announcements through natural-language questions.

Built for **ASYNC'26 — Sovereign AI Track**, Campus JARVIS combines local language models, semantic search, and retrieval-augmented generation (RAG) to provide answers grounded in stored campus documents, with traceable source citations.

The current prototype implements the backend foundation, document ingestion, semantic retrieval, and grounded question answering using locally running AI models.

---

## 🎯 Problem

Campus information is often scattered across notices, PDFs, announcements, and other documents.

Students may need to search through multiple sources to find simple information about library hours, canteen timings, examination notices, and campus announcements.

Campus JARVIS aims to make this information accessible through a single natural-language interface while keeping knowledge retrieval and AI inference locally controlled.

## 💡 Solution

Campus JARVIS allows campus documents to be ingested into a private knowledge base. Students can ask questions in natural language, and the system retrieves relevant document content and uses a local language model to generate an answer grounded in that evidence.

Key principles:

- **Privacy-oriented:** Designed around locally hosted models and a self-hosted database.
- **Grounded answers:** Answers are generated using retrieved campus documents rather than relying solely on general model knowledge.
- **Traceable sources:** Responses include citations linked to the retrieved document chunks.
- **Evidence-aware:** The system supports abstaining when the available evidence does not answer a question.

---

## ✨ Current Features

The current prototype implements the following functionality:

| Feature | Description |
|---|---|
| Document ingestion | Accepts campus document text through a REST API. |
| Text chunking | Splits documents into overlapping chunks for retrieval. |
| Local embeddings | Generates 768-dimensional embeddings using `nomic-embed-text` through Ollama. |
| Semantic retrieval | Uses PostgreSQL and pgvector to retrieve relevant document chunks using cosine similarity. |
| Local LLM generation | Uses Qwen 2.5 3B through Ollama for answer generation. |
| Grounded QA | Combines retrieved evidence and the user's question to generate answers. |
| Source citations | Returns document and chunk metadata associated with the answer. |
| Insufficient-evidence handling | Supports abstention when retrieved information does not answer the question. |
| REST API | Provides endpoints for ingestion, retrieval, and question answering. |

---

## 🏗️ Architecture

```text
                  Campus Documents
                         |
                         v
                 POST /documents
                         |
                         v
                  Text Chunking
                         |
                         v
               Ollama Embeddings
               nomic-embed-text
                         |
                         v
             PostgreSQL + pgvector
              Documents + Chunks
                         |
                         |
                User asks a question
                         |
                         v
                    POST /ask
                         |
                         v
                 QA Orchestration
                     (qa.py)
                         |
               +---------+---------+
               |                   |
               v                   v
        Semantic Retrieval    Prompt Construction
        (retrieval.py)        + Retrieved Evidence
               |                   |
               v                   v
        PostgreSQL/pgvector   Ollama Generation
                              Qwen 2.5 3B
                                   |
                                   v
                          Answer + Citations
                          + Evidence Status
                                   |
                                   v
                            JSON Response
```

### Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Data validation | Pydantic |
| Database | PostgreSQL |
| Vector search | pgvector, cosine distance, HNSW index |
| Local AI runtime | Ollama |
| Embedding model | `nomic-embed-text` |
| Generation model | `qwen2.5:3b` |
| Testing | pytest, httpx |
| Frontend foundation | React, TypeScript, Vite |

---

## 🔍 How Grounded Question Answering Works

When a user submits a question through `POST /ask`, the backend performs the following steps:

1. **Query embedding:** Converts the user's question into  embedding using the local embedding model.
2. **Semantic retrieval:** Searches the stored document chunks in PostgreSQL using pgvector.
3. **Context construction:** Passes the question and retrieved evidence to the local language model.
4. **Answer generation:** Qwen generates a response based on the supplied evidence.
5. **Citation mapping:** The QA service validates citation references and maps them to actual retrieved document metadata.
6. **Response:** Returns the answer, citations, and an insufficient-evidence indicator.

The generation prompt instructs the model to treat retrieved documents as untrusted data and to avoid answering campus-specific questions using unsupported general knowledge.

Prompt instructions and citation validation reduce hallucination risks, but do not guarantee that every generated claim is factually correct. Further evaluation and stronger verification are planned.

---

## 🧪 Verified Prototype Behavior

The backend has been tested against locally stored campus documents using the actual PostgreSQL database and Ollama models.

| Test | Observed result |
|---|---|
| Library closing time | Generated an answer matching the stored library notice, with a citation. |
| Canteen breakfast hours | Retrieved the canteen document and returned the supported breakfast timings. |
| Canteen operating hours | Returned the schedule matching the stored document. |
| Campus weather question | Recognized that the retrieved evidence did not contain weather information. |

The backend test suite has reported **101 passing tests**, including unit tests, mocked API tests, retrieval tests, and QA tests. One existing Starlette/httpx deprecation warning remains.

---

## 🚀 Getting Started

### Prerequisites

Install the following before running the backend:

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL
- PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension installed
- [Ollama](https://ollama.com/)

The prototype uses local Ollama models. The models must be available on the machine running the backend.

### 1. Clone the repository

```bash
git clone https://github.com/NSR16/Campus-Jarvis.git
cd Campus-Jarvis
```

### 2. Set up the backend

```bash
cd backend
uv sync
```

### 3. Configure environment variables

Copy the example environment file:

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure the required database connection and Ollama settings in `.env` using the values and variable names documented in `.env.example`.

Do not commit `.env` or any database credentials, passwords, or private API keys.

### 4. Set up PostgreSQL

Create a PostgreSQL database for Campus JARVIS and ensure that the pgvector extension is installed.

Configure the database connection in the backend environment.

Initialize the database schema using the existing schema initialization script:

```bash
uv run python -m app.db.initialize_schema
```

Run this after configuring the database. The application does not automatically create the database schema during startup.

### 5. Pull the Ollama models

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
```

Ensure the Ollama service is running and accessible at the configured Ollama base URL.

### 6. Start the backend

From the `backend` directory:

```bash
uv run uvicorn app.main:app --reload
```

The API should be available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

---

## 📡 API Endpoints

The backend currently exposes the following core endpoints.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend health check. |
| POST | `/documents` | Ingest a campus document into the knowledge base. |
| POST | `/query` | Retrieve relevant document chunks without generating an answer. |
| POST | `/ask` | Retrieve evidence and generate a grounded answer with citations. |

### Example: Ingest a document

`POST /documents`

```json
{
  "title": "Library hours",
  "source": "library-hours.txt",
  "document_type": "notice",
  "content": "The campus library is open Monday through Friday from 9 AM to 5 PM. It is closed on public holidays."
}
```

### Example: Ask a question

`POST /ask`

```json
{
  "question": "When does the campus library close?",
  "top_k": 5
}
```

Example response:

```json
{
  "answer": "The campus library closes at 5 PM on weekdays.",
  "citations": [
    {
      "chunk_id": 1,
      "document_id": 1,
      "title": "Library hours",
      "source": "library-hours.txt",
      "document_type": "notice",
      "chunk_index": 0
    }
  ],
  "insufficient_evidence": false
}
```

The response is illustrative. Actual answers and citations depend on the documents ingested into the database and the evidence retrieved for the question.

---

## 🧪 Running Tests

From the `backend` directory:

Run the full test suite:

```bash
uv run pytest -q
```

Run individual test modules:

```bash
uv run pytest tests/test_qa.py -q
uv run pytest tests/test_ask_api.py -q
uv run pytest tests/test_retrieval.py -q
```

The automated tests use mocked model and database interactions where appropriate. Live integration tests require a configured PostgreSQL database and running Ollama models.

---

## 🗺️ Roadmap

The current prototype focuses on the backend foundation and grounded question answering.

Planned areas of development during subsequent hackathon phases include:

- React chat interface connected to the `/ask` endpoint.
- Improved document ingestion, including additional document formats and automated ingestion.
- Stronger evaluation of retrieval relevance, answer grounding, and citation accuracy.
- User-approved actions with controlled execution and audit logging.
- Additional agent capabilities and privacy-oriented deployment improvements.

These are planned features and are not represented as completed functionality in the current prototype.

---

## 🔐 Privacy and Sovereign AI

Campus JARVIS is designed around locally hosted inference and a self-hosted knowledge database.

The current implementation uses Ollama for embeddings and language-model generation, with PostgreSQL and pgvector for document storage and retrieval.

This provides a foundation for private, locally controlled AI processing. Actual privacy and deployment guarantees depend on the runtime configuration, infrastructure, and deployment environment.

---

## 👨‍💻 Project

**Project:** Campus JARVIS  
**Hackathon:** ASYNC'26 — Sovereign AI Track  
**Institution:** Ramaiah Institute of Technology

Built as a prototype exploring private, locally powered AI for campus knowledge access.

---
