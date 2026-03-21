import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

from app.core.config import settings
from app.models.ingest import IngestError, IngestResponse
from app.models.source_content import EngagementMetrics, SourceContent
from app.services.ingestion.deduper import dedupe_items
from app.services.ingestion.normalizer import normalize_items

logger = logging.getLogger(__name__)

_VIDEO_ID_PATTERN = re.compile(r"/video/(\d+)")


class TikTokScraperService:
    """Playwright-based TikTok search starter scraper with graceful fallback."""

    async def search(self, query: str, limit: int = 5) -> IngestResponse:
        errors: list[IngestError] = []
        items: list[SourceContent] = []
        search_url = f"https://www.tiktok.com/search?q={quote_plus(query)}"

        try:
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:
                errors.append(
                    IngestError(
                        code="playwright_not_installed",
                        message="Playwright package is missing in runtime environment.",
                        detail=str(exc),
                    )
                )
                return IngestResponse(source="tiktok", query=query, items=[], count=0, errors=errors)

            async with async_playwright() as playwright:
                proxy = {"server": settings.tiktok_proxy_url} if settings.tiktok_proxy_url else None
                browser = await playwright.chromium.launch(
                    headless=settings.tiktok_headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                    proxy=proxy,
                )
                context = await browser.new_context(
                    locale=settings.tiktok_locale,
                    user_agent=settings.tiktok_user_agent or None,
                )
                if settings.tiktok_session_cookie:
                    await context.add_cookies(
                        [
                            {
                                "name": "sessionid",
                                "value": settings.tiktok_session_cookie,
                                "domain": ".tiktok.com",
                                "path": "/",
                                "httpOnly": True,
                                "secure": True,
                            }
                        ]
                    )

                page = await context.new_page()
                await page.goto(search_url, wait_until="domcontentloaded", timeout=settings.tiktok_timeout_seconds * 1000)
                await page.wait_for_timeout(settings.tiktok_wait_ms)

                anchors = await page.eval_on_selector_all(
                    "a[href*='/video/']",
                    "els => els.map(el => ({href: el.href || '', text: (el.innerText || '').trim()}))",
                )
                await browser.close()

                for idx, anchor in enumerate(anchors[:limit]):
                    href = (anchor.get("href") or "").strip()
                    if not href:
                        continue
                    items.append(self._to_source_content(query=query, href=href, text=anchor.get("text", ""), index=idx))
        except Exception as exc:  # noqa: BLE001
            logger.warning("TikTok ingestion failed: %s", exc)
            errors.append(
                IngestError(
                    code="tiktok_scrape_error",
                    message="TikTok scraping failed. Platform protections may require session/cookies or different runtime.",
                    detail=str(exc),
                )
            )

        normalized = dedupe_items(normalize_items(items))
        return IngestResponse(
            source="tiktok",
            query=query,
            items=normalized,
            count=len(normalized),
            errors=errors,
        )

    def _to_source_content(self, query: str, href: str, text: str, index: int) -> SourceContent:
        match = _VIDEO_ID_PATTERN.search(href)
        platform_id = match.group(1) if match else f"unknown-{index}"
        author = self._extract_author_from_url(href)
        cleaned_text = " ".join((text or "").split()) or None
        return SourceContent(
            source="tiktok",
            platform_id=platform_id,
            content_type="video",
            author=author,
            url=href,
            title=None,
            content_text=cleaned_text,
            created_at=datetime.now(tz=timezone.utc),
            engagement=EngagementMetrics(),
            query=query,
            raw_payload={"href": href, "text": text},
        )

    @staticmethod
    def _extract_author_from_url(url: str) -> str | None:
        # Example: https://www.tiktok.com/@username/video/123
        marker = "/@"
        if marker not in url:
            return None
        part = url.split(marker, maxsplit=1)[1]
        return part.split("/", maxsplit=1)[0] or None
