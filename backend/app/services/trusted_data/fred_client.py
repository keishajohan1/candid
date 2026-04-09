"""FRED (Federal Reserve Economic Data) — requires FRED_API_KEY."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"


async def fetch_latest_observation(
    *,
    series_id: str,
    units: str = "lin",
    timeout: float = 15.0,
) -> dict[str, Any] | None:
    key = (settings.fred_api_key or "").strip()
    if not key:
        return None
    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
        "units": units,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(FRED_OBS_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.debug("FRED fetch failed %s: %s", series_id, exc)
        return None

    obs = (data.get("observations") or []) if isinstance(data, dict) else []
    if not obs:
        return None
    raw = obs[0].get("value")
    if raw in (None, ".", ""):
        return None
    try:
        numeric = float(raw)
    except (TypeError, ValueError):
        return None
    return {
        "provider": "fred",
        "series_id": series_id,
        "date": str(obs[0].get("date", "")),
        "value": numeric,
        "units": units,
        "citation_url": f"https://fred.stlouisfed.org/series/{series_id}",
    }
