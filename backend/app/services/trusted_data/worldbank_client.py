"""World Bank Indicators API v2 — no API key required."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WB_BASE = "https://api.worldbank.org/v2"


async def fetch_latest_observation(
    *,
    country_iso2: str,
    indicator: str,
    mrv: int = 1,
    timeout: float = 15.0,
) -> dict[str, Any] | None:
    """
    Return the most recent numeric observation or None.

    Response shape: [meta, [ { indicator, country, date, value }, ... ] ]
    """
    url = f"{WB_BASE}/country/{country_iso2.lower()}/indicator/{indicator}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, params={"format": "json", "mrv": mrv})
            r.raise_for_status()
            payload = r.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.debug("World Bank fetch failed %s/%s: %s", country_iso2, indicator, exc)
        return None

    if not isinstance(payload, list) or len(payload) < 2:
        return None
    rows = payload[1]
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    val = row.get("value")
    if val is None:
        return None
    try:
        numeric = float(val)
    except (TypeError, ValueError):
        return None
    return {
        "provider": "world_bank",
        "indicator": indicator,
        "country_iso2": country_iso2.upper(),
        "date": str(row.get("date", "")),
        "value": numeric,
        "unit": "world_bank_native",
        "citation_url": f"https://data.worldbank.org/indicator/{indicator}",
    }
