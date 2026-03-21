# Backend (FastAPI)

The backend provides Candid API modules: **Socratic debate chat** (Claude consumes only backend-supplied text), **source ingestion** (Reddit / TikTok), and health checks. **Claude does not scrape**; retrieval is done in `RedditIngestionService` / `TikTokScraperService` before the LLM call.

## Endpoints

- `GET /health`
- `POST /api/v1/chat` — body may include `fetch_sources`, `turn_index`, `history`, `topic`, `source_query`; see `app.models.chat.ChatRequest`
- `POST /api/v1/ingest/reddit`
- `POST /api/v1/ingest/tiktok`

## What you must provide manually

| Item | Required for | Notes |
|------|----------------|-------|
| **`ANTHROPIC_API_KEY`** | Live Claude chat | Optional for running the API. Put in **repo root** `.env` (see `.env.example`). Without it, `/chat` returns **`mode: mock`** with a Socratic-style fallback. |
| **`REDDIT_*`** | Reddit ingestion | **No API key** in current code — uses public JSON endpoints. Set **`REDDIT_USER_AGENT`** to something identifiable; optional **`REDDIT_TIMEOUT_SECONDS`**. |
| **Playwright + Chromium** | TikTok ingestion | Run `python -m playwright install chromium`. TikTok often **blocks** datacenter/headless traffic; optional **`TIKTOK_SESSION_COOKIE`**, **`TIKTOK_PROXY_URL`**, **`TIKTOK_USER_AGENT`**. |
| **`.env` file** | Local settings | Copy `.env.example` → `.env` at **repository root**. Pydantic loads `.env` from the process working directory (run `uvicorn` from `backend/`; if variables are missing, set them in the environment or place `.env` where the loader finds it — see note below). |

### `.env` loading note

`Settings` uses `env_file=".env"`. If you start uvicorn from `backend/`, create **`backend/.env`** or export variables in the shell. If you start from repo root, **`./.env`** at root is typical. Use one location consistently.

## Local setup (system Python, no venv)

1. `pip install -r backend/requirements.txt`
2. `python -m playwright install chromium` (only if testing TikTok)
3. Copy env template: `copy .env.example .env` (Windows) at repo root, then add `ANTHROPIC_API_KEY` if you want live mode
4. `cd backend` → `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Chat behavior (rules location)

Socratic rules and prompt assembly live in **`app/utils/prompts.py`**. The chat route builds a **system** prompt + **user** message; optional **`fetch_sources: true`** runs ingestion and attaches excerpts to the user message only.

## Ingestion viability (audit)

- **Reddit:** Implemented via **`httpx`** against public `reddit.com/.../*.json` URLs. **No client id/secret required**; subject to **rate limits** and HTML/JSON changes.
- **TikTok:** Implemented with **Playwright** (real browser automation). **Not a stub**, but **brittle**: anti-bot, login walls, and headless detection may return **empty items** with structured errors in `debug.ingest_errors`.

## Testing

From `backend/`:

- `pytest -q`

## Limitations / not production-ready

- No conversation persistence; `turn_index` / `history` are client-supplied.
- TikTok scraping on **Cloud Run** needs browser deps, memory, and often **residential proxy / session** — not guaranteed.
- No rate limiting or caching on `/chat` with `fetch_sources`.
