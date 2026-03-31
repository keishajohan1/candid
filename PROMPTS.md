# Agent prompt log

Entries record prompts used for substantial AI-assisted changes (no secrets).

---

## 2026-03-28 — `fix/reddit-service-backcompat`

**Prompt (summary):** Realign `reddit_service.py`: module-level `SORT_STRATEGIES`, `SUBREDDITS_BY_TOPIC` (incl. telecoms), `DEFAULT_SUBREDDITS`; backward-compatible `search(..., turn=0, topic="")` and `_search_posts(..., turn=0)`; `_search_subreddit` with `restrict_sr: True`; class-level `_search_all_sources`; `search` body calling `_search_all_sources` with explicit kwargs, loop posts + optional comments, dedupe/shuffle/cap 30; `asyncio` at module top.

**Changes implemented:** Refactored `backend/app/services/scrapers/reddit_service.py` per spec; updated `fake_search` parameter order in `backend/tests/test_ingest_reddit.py`.

**Branch:** `fix/reddit-service-backcompat`

---

## 2026-03-28 — `fix/social-data-tiktok-resilience`

**Prompt (summary):** Harden TikTok `search()` with a single outer try/except returning graceful `IngestError`; guard debug screenshot with `page` in `locals()`; add combined social-data route with Reddit + TikTok (TikTok in its own try/except), pass `turn`/`topic` to Reddit; verify curl for `telecoms` turns 0 and 1.

**Changes implemented:** Refactored `tiktok_scraper.py`; added `backend/app/api/routes/social_data.py`, registered in `main.py`, removed duplicate `/social-data` from `ingest.py`; added `test_social_data.py`; README updates.

**Branch:** `fix/social-data-tiktok-resilience`

---

## 2026-03-28 — `fix/reddit-comment-resilience`

**Prompt (summary):** In `reddit_service.py`, isolate `_fetch_top_comments` and `_search_subreddit` failures (403/404/429 return `[]`, try/except); wrap per-post comment fetch in `search()` with inner try/except; `asyncio.sleep(0.3)` between comment fetches; skip `[deleted]`/`[removed]` bodies.

**Changes implemented:** Updated `backend/app/services/scrapers/reddit_service.py` per items 1–4.

**Branch:** `fix/reddit-comment-resilience`

---

## 2026-03-28 — `fix/tiktok-windows-playwright-thread`

**Prompt (summary):** Run TikTok Playwright via `ThreadPoolExecutor` + `_scrape_sync` / `_scrape_async`; Windows `WindowsSelectorEventLoopPolicy` at top of `main.py`; confirm TikTok `Settings` defaults in `config.py`.

**Changes implemented:** Refactored `tiktok_scraper.py`; updated `main.py`, `config.py` (TikTok field grouping).

**Branch:** `fix/tiktok-windows-playwright-thread`

---

## 2026-03-28 — `fix/reddit-no-default-comments`

**Prompt (summary):** Default `include_top_comments=False`; `asyncio.Semaphore(3)` for comment GETs; `_is_quality_post` filter after `_search_all_sources`; `httpx.AsyncClient(timeout=8.0)`; timing log in `search()`; align API/chat/social defaults.

**Changes implemented:** `reddit_service.py`, `ingest.py` model default, `social_data.py`, `chat.py`, `test_ingest_reddit.py` fake signature.

**Branch:** `fix/reddit-no-default-comments`

---

## 2026-03-28 — `fix/tiktok-windows-loop-redux`

**Prompt (summary):** Re-apply Windows `SelectorEventLoop` policy at earliest import; align TikTok `search()` / `_scrape_sync` / `_scrape_async` with ThreadPoolExecutor + thread-local loop spec; cross-platform debug screenshot path.

**Changes implemented:** `app/__init__.py` policy; `tiktok_scraper.py` rewrite per FIX B; README note.

**Branch:** `fix/tiktok-windows-loop-redux`

---

## 2026-03-28 — `remove-tiktok-scraper`

**Prompt (summary):** Remove TikTok scraping entirely: delete `tiktok_scraper.py`, strip routes/imports/config/requirements/Dockerfile/frontend debug UI; Reddit-only social-data and chat ingestion; remove Windows event loop policy used for Playwright.

**Changes implemented:** Deleted scraper and `test_ingest_tiktok.py`; updated `ingest`, `social_data`, `chat`, `config`, `prompts`, models, tests, Docker, requirements, READMEs, `.env.example`, `plans/Initial_plan.md`.

**Branch:** `remove-tiktok-scraper`

---

## 2026-03-31 — `fix/ci-frontend-working-directory`

**Prompt (full text):** "The GitHub Actions test workflow is failing with: ENOENT: no such file or directory, open 'package.json'. This is because the workflow runs npm install from the repo root, but package.json lives inside the frontend/ subfolder. Find the failing workflow file inside .github/workflows/ — it may be named test.yml, ci.yml, or deploy.yml — and apply this fix: add a defaults block at the job level so all run steps automatically use frontend/ as their working directory under jobs.test. Keep checkout/setup steps unchanged. If the workflow has a build step, add it as `run: npm run build`. Do not add working-directory individually to each step. After editing the file commit and push."

**Changes implemented:** Updated `.github/workflows/ci.yml` by adding `defaults.run.working-directory: ./frontend` under the `test` job so `npm install` and `npm test` run in the frontend package directory.

**Branch:** `fix/ci-frontend-working-directory`
