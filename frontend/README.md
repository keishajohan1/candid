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
- **Fetch Reddit excerpts** — sets `fetch_sources: true` (may be slow; depends on Reddit availability).
- **turn_index** — derived from the number of assistant messages in the thread (+1 for next turn), sent to the backend for escalation rules.

## Backend requirements

The API **will not start** without a non-empty **`ANTHROPIC_API_KEY`** in **`backend/.env`**. Successful chat responses use **`mode: live`** from Anthropic.

If the browser shows **Failed to fetch** but the API works in curl, open the UI at **`http://localhost:5173`** (not `127.0.0.1`) or set **`FRONTEND_ORIGIN`** in **`backend/.env`** to match the exact origin you use. The backend allows both localhost and 127.0.0.1 for the same port by default.
