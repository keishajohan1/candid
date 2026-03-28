---
name: Bootstrap Candid MVP Scaffold
overview: Create a production-minded monorepo scaffold for Candid with a FastAPI backend, React+Vite frontend, Cloud Run-ready Docker setup, and clear docs for non-venv local development.
todos:
  - id: scaffold-root
    content: "Create root-level docs/config files: README, .gitignore, .dockerignore, .env.example, optional docker-compose"
    status: pending
  - id: scaffold-backend
    content: Build FastAPI backend structure with routes, config, services, models, prompt utils, and tests
    status: pending
  - id: scaffold-frontend
    content: Build React+Vite frontend placeholder with ChatShell and backend API service module
    status: pending
  - id: containerize
    content: Add Cloud Run-ready Dockerfiles and startup strategy notes for backend/frontend deployment
    status: pending
  - id: final-output
    content: Return full architecture, tree, all file contents, setup steps, Cloud Run notes, and next steps in required order
    status: pending
isProject: false
---

# Candid MVP Bootstrap Plan

## Goal

Scaffold a runnable, production-minded starter codebase that matches your requested architecture and file set, with mock-safe behavior for `/chat` when no Anthropic key is present.

## Architecture To Implement

- Monorepo-style layout with three top-level domains:
  - `backend/` for FastAPI API, service modules, tests, and deployment image
  - `frontend/` for React + Vite UI shell and API client
  - `docs/` for future architecture/security/roadmap notes
- Clear service boundaries in backend:
  - API routes (`health`, `chat`) depend on service interfaces
  - Claude adapter encapsulated in `claude_service.py`
  - Future ingestion/retrieval/safety split into dedicated modules (`scrapers`, `rag`, `safety`)
- Frontend communicates to backend via HTTP JSON API (`POST /chat`) through `src/services/api.js`
- Initial neutral educational response contract shaped in prompt utilities and chat response model

## Files To Create/Update

- Root:
  - `[README.md](README.md)` (rewrite with full project onboarding + no-venv workflow)
  - `[.gitignore](.gitignore)`
  - `[.dockerignore](.dockerignore)`
  - `[.env.example](.env.example)`
  - Optional local orchestration: `[docker-compose.yml](docker-compose.yml)` (include only for convenience dev mode with backend+frontend)
- Backend:
  - `[backend/README.md](backend/README.md)`
  - `[backend/requirements.txt](backend/requirements.txt)`
  - `[backend/Dockerfile](backend/Dockerfile)`
  - `[backend/app/main.py](backend/app/main.py)`
  - `[backend/app/api/routes/health.py](backend/app/api/routes/health.py)`
  - `[backend/app/api/routes/chat.py](backend/app/api/routes/chat.py)`
  - `[backend/app/core/config.py](backend/app/core/config.py)`
  - `[backend/app/core/logging.py](backend/app/core/logging.py)`
  - `[backend/app/services/claude_service.py](backend/app/services/claude_service.py)`
  - `[backend/app/services/scrapers/reddit_service.py](backend/app/services/scrapers/reddit_service.py)`
  - `[backend/app/services/rag/chroma_client.py](backend/app/services/rag/chroma_client.py)`
  - `[backend/app/services/safety/moderation.py](backend/app/services/safety/moderation.py)`
  - `[backend/app/models/chat.py](backend/app/models/chat.py)`
  - `[backend/app/utils/prompts.py](backend/app/utils/prompts.py)`
  - `[backend/tests/test_health.py](backend/tests/test_health.py)`
  - `[backend/tests/test_chat.py](backend/tests/test_chat.py)`
  - package marker files (`__init__.py`) in python dirs as needed
- Frontend:
  - `[frontend/README.md](frontend/README.md)`
  - `[frontend/Dockerfile](frontend/Dockerfile)`
  - `[frontend/package.json](frontend/package.json)`
  - `[frontend/vite.config.js](frontend/vite.config.js)`
  - `[frontend/index.html](frontend/index.html)`
  - `[frontend/src/main.jsx](frontend/src/main.jsx)`
  - `[frontend/src/App.jsx](frontend/src/App.jsx)`
  - `[frontend/src/components/ChatShell.jsx](frontend/src/components/ChatShell.jsx)`
  - `[frontend/src/services/api.js](frontend/src/services/api.js)`
  - minimal CSS files for clean placeholder rendering

## Backend API Shape

- `GET /health`
  - Returns app status and environment metadata (non-sensitive)
- `POST /chat`
  - Request model with user message + optional context fields
  - Pipeline (stub-friendly): safety precheck -> prompt assembly -> Claude call (if key configured) -> fallback neutral mock response if missing key or disabled
  - Response model includes content, mode (`mock`/`live`), and placeholder source/reflection fields for future extension

## Dependency & Config Strategy

- `requirements.txt` to include:
  - runtime: `fastapi`, `uvicorn[standard]`, `anthropic`, `pydantic`, `pydantic-settings`, `httpx`, `python-dotenv`
  - roadmap-ready: `chromadb`
  - testing: `pytest`, `pytest-asyncio`, `pytest-cov`
- Config centralized with Pydantic settings from environment variables, including:
  - `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `APP_ENV`, `LOG_LEVEL`, `FRONTEND_ORIGIN`, `CHROMA_PERSIST_DIR`
  - scraper placeholders (`REDDIT_USER_AGENT`, `REDDIT_TIMEOUT_SECONDS`)

## Cloud Run & Containerization

- Backend Dockerfile:
  - Python 3.11 slim base, install requirements, expose Cloud Run port, run `uvicorn` with `${PORT}` support
- Frontend Dockerfile:
  - Multi-stage build (Node build + Nginx serve) for optional separate frontend deployment
- Deployment recommendation to document:
  - Preferred: separate services (frontend static app + backend API) for independent scaling and simpler API lifecycle
  - MVP option: frontend dev server locally, backend in Cloud Run for early integration

## Validation Criteria

- Backend starts locally with system Python interpreter and `pip install -r requirements.txt`
- Frontend starts with `npm install` + `npm run dev`
- `GET /health` returns 200
- `POST /chat` returns deterministic placeholder when no API key
- Tests pass for health/chat route basics

## Deliverable Format

- Provide in final response exactly in requested order:
  1. architecture explanation
  2. complete folder tree
  3. full file contents
  4. setup instructions (explicit no-venv workflow + IDE interpreter selection)
  5. Cloud Run deployment notes
  6. next recommended implementation steps
- Include implementation notes/TODOs for all intentionally stubbed domains (Claude orchestration depth, scraping flows, RAG retrieval quality, auth, persistence, citations, safety depth, analytics).

