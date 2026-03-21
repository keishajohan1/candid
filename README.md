# Candid

Candid is a production-minded MVP scaffold for a neutral educational chatbot platform.
The project is designed to guide users through facts, sources, and multiple perspectives, with a roadmap for safety, retrieval, and source exploration.

## Repository layout

- `backend/` FastAPI API server, service modules, tests, and backend container image.
- `frontend/` React + Vite web client scaffold.
- `docs/` future architecture, product, and operations docs.

## Core MVP behavior today

- `GET /health` returns service status and runtime metadata.
- `POST /chat` returns:
  - live Claude output when `ANTHROPIC_API_KEY` is configured
  - safe placeholder educational output when API key is missing

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
4. Install Playwright browser binaries (for future scraping modules):
   - `python -m playwright install chromium`
5. Run backend:
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

## Roadmap placeholders intentionally stubbed

- Advanced Claude prompt orchestration and multi-turn memory
- Full safety policy layer and bias/risk scoring
- Real TikTok scraping workflows (Playwright pipeline)
- Reddit ingestion/retrieval logic
- ChromaDB retrieval ranking and citation rendering
- Auth, durable conversation persistence, and analytics dashboards
