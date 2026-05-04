# Agent prompt log

Entries record prompts used for substantial AI-assisted changes (no secrets).

---

## 2026-04-28 — `feature/ci-cloud-run-deploy`

**Prompt (summary):** Replace placeholder GitHub Actions deploy job with automated Artifact Registry + Cloud Run deploy; document required GCP and GitHub configuration.

**Changes implemented:** `.github/workflows/ci.yml` deploy job (auth, Docker push, backend/frontend `gcloud run deploy`, CORS update); **`docs/cloud-run-ci.md`**; **`README.md`** link under Cloud Run.

**Branch:** `feature/ci-cloud-run-deploy`

---

## 2026-04-28 — `feature/ui-minimal-chat-message-driven-topic`

**Prompt (summary):** Remove all developer/sidebar topic UI in frontend; send only message/history/turn_index from client; make backend Reddit query message-driven; remove `topic`/`developer_mode` request flags; add prompt fallback to user message when topic is absent.

**Changes implemented:** Rebuilt `frontend/src/components/ChatShell.jsx` as message-thread + composer only; removed topic/developer payload fields; removed `topic` from `ChatRequest`; updated chat route to call Reddit with message-derived query/topic and infer inquiry focus from user messages; extended prompt builder topic fallback via `user_message`; updated tests and READMEs.

**Branch:** `feature/ui-minimal-chat-message-driven-topic`

---

## 2026-04-28 — `feature/reddit-always-on`

**Prompt (summary):** Make Reddit ingestion mandatory — remove frontend toggle and `fetch_sources` (and related) from chat payload and `ChatRequest`; always call Reddit in `chat.py`; remove debug UI tied to modes; verify logging/tests.

**Changes implemented:** Removed `fetch_sources` from `ChatRequest` and `ChatShell`; unconditional Reddit search + BM25 + excerpt guardrails path; `logger.info` on each ingestion; default Reddit stub in `conftest.py`; tests/README/PROMPTS updates.

**Branch:** `feature/reddit-always-on`

---

## 2026-04-28 — `feature/guardrails-three-stage`

**Prompt (summary):** Refactor `guardrails.py` into a three-stage pipeline: rule-based input guardrails before Reddit/Claude; LLM-based excerpt labeling with bias/misinformation risk flags on `SourceContent`; rule-based output guardrails after Claude; wire `chat.py`.

**Changes implemented:** `GuardrailResult`, `apply_input_guardrails`, `apply_output_guardrails`, expanded `apply_excerpt_guardrails` (prompt + parse), `SourceContent.bias_risk` / `misinformation_risk`, `formatters` / `user_content` / `reddit_handler` risk hints, `tests/test_guardrails.py`, chat test message length fix, `backend/README.md` safety note.

**Branch:** `feature/guardrails-three-stage`

---

## 2026-04-28 — `chore/remove-prompts-next-shim`

**Prompt (summary):** Point code at a single prompts shim and delete the redundant file (`prompts_next.py` vs `prompts.py`).

**Changes implemented:** Removed `backend/app/utils/prompts_next.py`; dropped its `omit` entry from `backend/.coveragerc`. Canonical compatibility imports remain only in `backend/app/utils/prompts.py` (re-exporting `app.prompts`).

**Branch:** `chore/remove-prompts-next-shim`

---

## 2026-04-28 — `refactor/modular-prompt-skills`

**Prompt (summary):** Refactor monolithic `prompts.py` into modular `backend/app/prompts/` skill architecture with conditional injection by `turn_index`; wire imports (`app/core/prompts.py`, builder); replace legacy file content after verification.

**Changes implemented:** Added `app/prompts/` (`builder.py`, `skills/` identity, interaction_model with `FIRST_TURN_INTERACTION_SKILL`, cognitive_protocol, persona_engine, reddit_handler, rag_contract, `formatters.py`, `user_content.py`), barrel `app/core/prompts.py`; thin `app/utils/prompts.py`; switched `chat.py` and `eval/evaluator.py` to `app.prompts`; README updates; `.coveragerc` omits for compatibility shims; tests (`test_prompts_build.py`, `test_prompt_user_content.py`, expanded `test_chat.py`) — pytest passes at ≥80% coverage.

**Branch:** `refactor/modular-prompt-skills`

---

## 2026-04-28 — `feature/prompts-next-staging`

**Prompt (summary):** Do not delete original `prompts.py` yet; work alongside it until all imports are confirmed for the instructions to follow.

**Changes implemented:** Added `backend/app/utils/prompts_next.py` as a parallel re-export of the public prompt helpers from `prompts.py` (no removal of `prompts.py`); noted the pattern in `backend/README.md`.

**Branch:** `feature/prompts-next-staging`

---

## 2026-04-28 — `fix/langchain-text-splitters-deps`

**Prompt (summary):** Fix unresolved import `langchain_text_splitters` in `backend/app/services/knowledge_base.py` (lines 9–12); verify and explain concisely.

**Changes implemented:** Declared `langchain-text-splitters` in `backend/requirements.txt`; updated README technology stack to mention it alongside other LangChain pieces.

**Branch:** `fix/langchain-text-splitters-deps`

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

---

## 2026-03-31 — `avalder`

**Prompt (full text):** "The GitHub Actions workflow is failing with: npm error Missing script: \"test\". This means the workflow runs npm test but package.json inside frontend/ has no \"test\" script defined. In .github/workflows/ find the workflow file (test.yml, ci.yml, or deploy.yml) and replace the Run tests step with a Build step: remove Run tests / npm test and add Build / npm run build. Keep the test job with defaults working-directory ./frontend and install step. Then commit and push: git add .github/workflows/; git commit -m \"fix: replace npm test with npm run build in CI\"; git push origin avalder."

**Changes implemented:** Replaced the `Run tests` step (`npm test`) with a `Build` step (`npm run build`) in `.github/workflows/ci.yml` to match the frontend scripts.

**Branch:** `avalder`

---

## 2026-04-09 — `feature/tiered-trusted-rag-rerank`

**Prompt (summary):** Implement tiered RAG: clear contract in prompts; Tier 1B trusted APIs (World Bank, UN, FRED) only when static KB empty; cross-verification (no single-source-as-truth); BM25 rerank for Reddit by tier assembly; no SerpAPI; preserve Candid personality.

**Changes implemented:** Added `trusted_data/` (WB + FRED + optional UN bearer clients, `cross_verify`, `TrustedFactsOrchestrator`), `rerank_bm25` for Reddit, `has_static_kb_for_topic`, extended `build_socratic_system_prompt` + RAG contract / RULE 8, wired `chat.py` with debug fields, `rank-bm25` dependency, tests, `backend/.coveragerc` + `pytest.ini`, README and `.env.example` updates.

**Branch:** `feature/tiered-trusted-rag-rerank`
