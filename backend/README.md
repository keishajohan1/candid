# Backend (FastAPI)

The backend provides Candid API modules: **Socratic debate chat** (Claude consumes only backend-supplied text), **Reddit source ingestion**, and health checks. **Claude does not scrape**; retrieval is done in **`RedditIngestionService`** before the LLM call.

## Endpoints

- `GET /health`
- `POST /api/v1/chat` — body may include `turn_index`, `history`, `source_query`; see `app.models.chat.ChatRequest` (Reddit ingestion runs on every request)
- `POST /api/v1/ingest/reddit`
- `GET /api/v1/social-data` — Reddit sample (`topic`, `turn`, optional `q`); vary `turn` for a different Reddit sort/subreddit mix

## What you must provide manually

| Item | Required for | Notes |
|------|----------------|-------|
| **`ANTHROPIC_API_KEY`** | **Required** | Non-empty value in **`backend/.env`**. The app **fails startup** (Pydantic validation + lifespan) if missing. Chat always calls Anthropic; there is no mock LLM path. |
| **`CLAUDE_MAX_OUTPUT_TOKENS`** | Long replies | Default **8192** (range 256–64000). Increase when users send very long prompts and need longer assistant output; respect Anthropic model limits. |
| **`REDDIT_*`** | Reddit ingestion | **No API key** in current code — uses public JSON endpoints. Set **`REDDIT_USER_AGENT`** to something identifiable; optional **`REDDIT_TIMEOUT_SECONDS`**. |
| **`FRED_API_KEY`** | Tier 1B trusted facts | **Optional.** When set, economy-style sessions with **no static KB match** can **cross-verify** World Bank vs FRED (inflation, unemployment). |
| **`UN_DATAPORTAL_BEARER_TOKEN`** | Tier 1B population | **Optional.** UN Population Data Portal **`/data/*`** requires **Bearer** auth; without it, population corroboration falls back to **World Bank only** (provisional line). |
| **`ENABLE_TRUSTED_API_FETCH`** | Tier 1B | Default **true**. Set **false** to disable all Tier 1B HTTP fetches. |
| **`.env` file** | Local settings | Copy **`.env.example`** → **`backend/.env`** and set **`ANTHROPIC_API_KEY`**. Resolved by path from `app/core/config.py` (see note below). |

### `.env` loading note

`Settings` resolves **`backend/.env`** from the config file path, so the key and **`CLAUDE_MODEL` / `CLAUDE_MAX_OUTPUT_TOKENS`** load regardless of shell working directory.

## Local setup (system Python, no venv)

1. `pip install -r backend/requirements.txt`
2. Copy env template to **`backend/.env`**, set **`ANTHROPIC_API_KEY`** (required) and **`CLAUDE_MODEL`** if needed (default `claude-sonnet-4-20250514`)
3. `cd backend` → `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Chat behavior (rules location)

Canonical prompt assembly lives in **`app/prompts/`** (`builder.build_socratic_system_prompt`, skill modules under **`app/prompts/skills/`**, **`formatters.py`**, **`user_content.py`**). **`app/utils/prompts.py`** re-exports the same API for older imports; **`app/core/prompts.py`** is an optional barrel import. The chat route builds a **system** prompt + **user** message.

**Safety pipeline (`POST /api/v1/chat`):** Stage 1 — **`GuardrailsService.apply_input_guardrails`** (rules, no LLM) after **`ModerationService.precheck`**, before Reddit/Claude. Stage 2 — **`apply_excerpt_guardrails`** (LLM) on top Reddit excerpts, writing **`bias_risk`** / **`misinformation_risk`** on **`SourceContent`**. Stage 3 — **`apply_output_guardrails`** on assistant text before JSON is returned.

**Tiered context**

- **Tier 1A:** `knowledge_base.get_verified_facts_for_topic(...)` using an inferred inquiry focus (first user message in history, or current message) when it matches a curated bucket.
- **Tier 1B:** `TrustedFactsOrchestrator` calls **World Bank** (always, no key), **FRED** (if `FRED_API_KEY`), **UN Data Portal** (if `UN_DATAPORTAL_BEARER_TOKEN`) **only when Tier 1A returned no facts**, to avoid conflicting numbers. Economy metrics prefer **cross-verified** lines (WB+FRED). Climate uses **two distinct World Bank series** with explicit same-publisher labeling. Population uses **WB+UN** when UN auth is available.
- **Tier 2:** **Always:** Reddit → **BM25 rerank** (`rerank_bm25.py`) → **Stage 2 excerpt guardrails** (classify + **BIAS_RISK** / **MISINFO_RISK** flags + PII scrub) → excerpt block in the system prompt when any items return.

`debug` on chat responses includes **`ingestion_query`**, **`reddit_item_count`**, **`input_guardrails`**, **`trusted_api`**, **`static_kb_matched`**, **`trusted_api_lines_count`**.

## Ingestion viability (audit)

- **Reddit:** Implemented via **`httpx`** (global search + parallel subreddit searches, rotating sort by `turn`). **Comment threads are off by default** (`include_top_comments: false`) to avoid slow 403-heavy fetches; posts use title/selftext only unless clients opt in. **No response caching** in-process. **No client id/secret required**; subject to **rate limits** and API changes.

## Testing

From `backend/`:

- `pytest` (uses **`pytest.ini`**: coverage + **80%** gate with **`.coveragerc`** — omits stub `chroma_client`, integration-heavy `reddit_service`, and token-gated `un_client` from coverage totals)

## CI / Cloud Run

Automated image build and Cloud Run deploy from GitHub Actions is documented at the repo root in **`docs/cloud-run-ci.md`** (uses **`backend/Dockerfile`** from the repository root in CI).

## Limitations / not production-ready

- No conversation persistence; `turn_index` / `history` are client-supplied.
- No rate limiting or caching on `/chat` (Reddit runs every request).
