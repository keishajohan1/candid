# Backend (FastAPI)

The backend provides Candid API modules for neutral educational chat and source ingestion.

## Endpoints

- `GET /health`
- `POST /api/v1/chat`
- `POST /api/v1/ingest/reddit`
- `POST /api/v1/ingest/tiktok`

## Local setup (system Python, no venv)

1. Install Python dependencies from repo root:
   - `pip install -r backend/requirements.txt`
2. Install Playwright Chromium runtime:
   - `python -m playwright install chromium`
3. Copy environment template:
   - Windows: `copy .env.example .env`
4. Start backend:
   - `cd backend`
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Ingestion usage

### Reddit ingestion

- Sample request:
  - `POST /api/v1/ingest/reddit`
  - Body:
    - `{"query":"student loans","limit":5,"include_top_comments":true,"comments_limit":3}`
- Behavior:
  - Uses public Reddit JSON search endpoints.
  - Works without Reddit API keys.
  - Applies `REDDIT_USER_AGENT` and `REDDIT_TIMEOUT_SECONDS`.
  - Returns normalized `items` plus structured `errors` if partial/failed.

### TikTok ingestion

- Sample request:
  - `POST /api/v1/ingest/tiktok`
  - Body:
    - `{"query":"financial literacy","limit":5}`
- Behavior:
  - Uses Playwright (Chromium) to load TikTok search and extract video links/metadata.
  - Can run with only Playwright installed, but TikTok may block or throttle automated traffic.
  - Returns graceful structured errors when blocked or browser runtime is missing.

## Environment variables

### Required now

- `APP_NAME`
- `APP_ENV`
- `LOG_LEVEL`
- `API_PREFIX`
- `FRONTEND_ORIGIN`

### Optional now (used by ingestion/chat if provided)

- `ANTHROPIC_API_KEY` (chat falls back to mock if missing)
- `CLAUDE_MODEL`
- `REDDIT_USER_AGENT`
- `REDDIT_TIMEOUT_SECONDS`
- `TIKTOK_HEADLESS`
- `TIKTOK_LOCALE`
- `TIKTOK_TIMEOUT_SECONDS`
- `TIKTOK_WAIT_MS`
- `TIKTOK_USER_AGENT`
- `TIKTOK_SESSION_COOKIE` (improves access when TikTok blocks unauthenticated scraping)
- `TIKTOK_PROXY_URL` (optional proxy for scraper egress)
- `PLAYWRIGHT_BROWSERS_PATH` (optional browser cache/runtime location)

### Likely needed later

- RAG/vector store credentials and DB secrets.
- Source API credentials if migrating from public scrape/search mode.
- Secret Manager integration for production keys.

## Testing

From `backend/`:

- `pytest -q`
- `pytest -q tests/test_ingest_reddit.py tests/test_ingest_tiktok.py`

Tests mock ingestion services and do not require live external secrets.

## Limitations and deployment notes

- Reddit public endpoints can rate-limit aggressively; keep limits modest and set a clear user-agent.
- TikTok scraping reliability is best-effort and may fail due to anti-bot protections, geofencing, or consent walls.
- Cloud Run can run Playwright/Chromium, but needs container/browser dependencies and enough CPU/memory.
- Prefer storing session cookies/API keys in Secret Manager for production deployments.
