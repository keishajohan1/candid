# Candid

Candid is a production-minded MVP scaffold for a neutral educational chatbot platform.
The project is designed to guide users through facts, sources, and multiple perspectives, with a roadmap for safety, retrieval, and source exploration.

## Technology stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Anthropic SDK, httpx, Pydantic, rank-bm25 (BM25 rerank), pytest / pytest-cov.
- **Frontend:** React, Vite.
- **Trusted data APIs (Tier 1B):** World Bank Indicators API v2 (no key), FRED (optional API key), UN Population Data Portal `data` routes (optional Bearer token).

## Repository layout

- `backend/` FastAPI API server, service modules, tests, and backend container image.
- `backend/app/services/trusted_data/` Tier 1B trusted API orchestration (World Bank, optional FRED, optional UN bearer).
- `frontend/` React + Vite web client scaffold.
- `docs/` future architecture, product, and operations docs.

## API endpoints (backend, prefix `/api/v1` unless noted)

- `GET /health`
- `POST /api/v1/chat`
- `POST /api/v1/ingest/reddit`
- `GET /api/v1/social-data` — Reddit sample (`topic`, `turn`, optional `q`)

## Core MVP behavior today

- `GET /health` returns service status and runtime metadata.
- `POST /api/v1/chat` calls Anthropic when `ANTHROPIC_API_KEY` is set in `backend/.env` (required for the app to start).
- Chat uses a **tiered RAG contract** in the system prompt: **Tier 1A** static facts (`knowledge_base.py`) when the topic matches; **Tier 1B** live **World Bank** + optional **FRED** / **UN Data Portal** facts only when Tier 1A is empty, with **cross-verification** where two independent providers apply; **Tier 2** Reddit excerpts when `fetch_sources` is true, **BM25-reranked** before guardrails.

## Local development (no virtual environment workflow)

This repo intentionally avoids a venv-first workflow.
Use your system Python interpreter (3.11+) directly and point your IDE to it.

### 1) Backend setup

1. Install Python 3.11+ and confirm:
   - `python --version`
2. Install backend dependencies:
   - `pip install -r backend/requirements.txt`
3. Copy environment file and fill values:
   - `copy .env.example .env`
4. Run backend:
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
   - Run from `backend/` directory.

### 2) Frontend setup

1. Install Node.js 20+ and confirm:
   - `node --version`
2. Install dependencies:
   - `cd frontend`
   - `npm install`
3. Start dev server:
   - `npm run dev`

Frontend defaults to `http://localhost:5173` and calls backend at `http://localhost:8000`.

### 3) Select interpreter in Cursor/VS Code manually

1. Open Command Palette.
2. Run `Python: Select Interpreter`.
3. Pick your system Python 3.11+ installation path (not a venv).
4. Confirm terminal `python --version` matches selected interpreter.

## Cloud Run readiness

- Backend image is Cloud Run-ready:
  - reads Cloud Run `PORT`
  - starts via `uvicorn app.main:app`
- Frontend can be deployed as a separate static container service.

Recommended deployment pattern:
- Deploy backend and frontend as separate Cloud Run services for independent scaling, release cadence, and simpler API lifecycle controls.

## Optional local containers

Use `docker-compose.yml` for convenience local orchestration of both services.

## Tests (backend)

From `backend/` run `pytest` (see `backend/pytest.ini` and `backend/.coveragerc` for coverage + 80% threshold).

## Implementation status (high level)

- **Done:** Health, chat (Claude), Reddit ingest + social-data, moderation precheck, excerpt guardrails, static KB, Tier 1B trusted APIs (WB + optional FRED/UN), cross-verified fact lines, BM25 Reddit rerank, tiered prompt contract.
- **Pending / stub:** Chroma vector RAG (`chroma_client.py`), durable sessions, auth, full safety policy beyond keyword precheck.

## Roadmap placeholders intentionally stubbed

- Advanced Claude prompt orchestration and multi-turn memory
- Full safety policy layer and bias/risk scoring
- Reddit ingestion/retrieval enhancements (beyond BM25 rerank)
- ChromaDB retrieval ranking and citation rendering
- Auth, durable conversation persistence, and analytics dashboards

## Team member roles

- (Update per your course team roster.)
