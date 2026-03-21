# Frontend (React + Vite)

Minimal **ChatGPT-style layout** for local testing: sidebar, message thread, composer, and a small **debug** panel (mode, source counts, ingest errors).

## Prerequisites

- Backend running at `http://localhost:8000` with CORS allowing `http://localhost:5173` (default `FRONTEND_ORIGIN` in backend `.env`).

## Run locally

1. `cd frontend`
2. `npm install`
3. `npm run dev`

Open the URL Vite prints (usually `http://localhost:5173`).

## API base URL

Default: `http://localhost:8000/api/v1`

Override:

```bash
set VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

## UI behavior

- **Topic** — optional; sent as `topic` to `/chat`.
- **Fetch Reddit + TikTok** — sets `fetch_sources: true` (slow; may fail without Playwright/TikTok access).
- **turn_index** — derived from the number of assistant messages in the thread (+1 for next turn), sent to the backend for escalation rules.

## Live vs mock

If the backend has no **`ANTHROPIC_API_KEY`**, responses are **`mode: mock`** but still follow a short Socratic-style fallback. Set the key in backend `.env` for **live** Claude output.
