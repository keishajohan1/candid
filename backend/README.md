# Backend (FastAPI)

The backend provides Candid API modules: **Socratic debate chat** (Claude consumes only backend-supplied text), **Reddit source ingestion**, and health checks. **Claude does not scrape**; retrieval is done in **`RedditIngestionService`** before the LLM call.

## Endpoints

- `GET /health`
- `POST /api/v1/chat` — body may include `fetch_sources`, `turn_index`, `history`, `topic`, `source_query`; see `app.models.chat.ChatRequest`
- `POST /api/v1/ingest/reddit`
- `GET /api/v1/social-data` — Reddit sample (`topic`, `turn`, optional `q`); vary `turn` for a different Reddit sort/subreddit mix

## What you must provide manually

| Item | Required for | Notes |
|------|----------------|-------|
| **`ANTHROPIC_API_KEY`** | **Required** | Non-empty value in **`backend/.env`**. The app **fails startup** (Pydantic validation + lifespan) if missing. Chat always calls Anthropic; there is no mock LLM path. |
| **`CLAUDE_MAX_OUTPUT_TOKENS`** | Long replies | Default **8192** (range 256–64000). Increase when users send very long prompts and need longer assistant output; respect Anthropic model limits. |
| **`REDDIT_*`** | Reddit ingestion | **No API key** in current code — uses public JSON endpoints. Set **`REDDIT_USER_AGENT`** to something identifiable; optional **`REDDIT_TIMEOUT_SECONDS`**. |
| **`.env` file** | Local settings | Copy **`.env.example`** → **`backend/.env`** and set **`ANTHROPIC_API_KEY`**. Resolved by path from `app/core/config.py` (see note below). |

### `.env` loading note

`Settings` resolves **`backend/.env`** from the config file path, so the key and **`CLAUDE_MODEL` / `CLAUDE_MAX_OUTPUT_TOKENS`** load regardless of shell working directory.

## Local setup (system Python, no venv)

1. `pip install -r backend/requirements.txt`
2. Copy env template to **`backend/.env`**, set **`ANTHROPIC_API_KEY`** (required) and **`CLAUDE_MODEL`** if needed (default `claude-sonnet-4-20250514`)
3. `cd backend` → `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Chat behavior (rules location)

Socratic rules and prompt assembly live in **`app/utils/prompts.py`**. The chat route builds a **system** prompt + **user** message; optional **`fetch_sources: true`** runs Reddit ingestion and attaches excerpts to the user message only.

## Ingestion viability (audit)

- **Reddit:** Implemented via **`httpx`** (global search + parallel subreddit searches, rotating sort by `turn`). **Comment threads are off by default** (`include_top_comments: false`) to avoid slow 403-heavy fetches; posts use title/selftext only unless clients opt in. **No response caching** in-process. **No client id/secret required**; subject to **rate limits** and API changes.

## Testing

From `backend/`:

- `pytest -q`

## Limitations / not production-ready

- No conversation persistence; `turn_index` / `history` are client-supplied.
- No rate limiting or caching on `/chat` with `fetch_sources`.
