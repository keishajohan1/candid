"""UN Population Data Portal — indicator metadata is public; /data/* requires Bearer token."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

UN_BASE = "https://population.un.org/dataportalapi/api/v1"


async def fetch_total_population_us(
    *,
    start_year: int = 2018,
    end_year: int = 2024,
    timeout: float = 20.0,
) -> dict[str, Any] | None:
    """
    Indicator 49 = total population by sex (UN DESA Data Portal).
    Location 840 = United States.
    """
    token = (settings.un_dataportal_bearer_token or "").strip()
    if not token:
        return None

    url = f"{UN_BASE}/data/indicators/49/locations/840/start/{start_year}/end/{end_year}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            payload = r.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.debug("UN Data Portal fetch failed: %s", exc)
        return None

    # Response shape varies by API version — collect (year_hint, numeric_value) pairs.
    pairs: list[tuple[int, float]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            val = obj.get("value")
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                y = 0
                for k in ("timeStart", "timeEnd", "year", "Time"):
                    raw = obj.get(k)
                    if raw is not None:
                        try:
                            y = int(str(raw)[:4])
                            break
                        except ValueError:
                            continue
                pairs.append((y, float(val)))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(payload)
    if not pairs:
        return None
    dated = [p for p in pairs if p[0] > 0]
    if dated:
        latest_year, latest = max(dated, key=lambda p: (p[0], p[1]))
    else:
        latest_year, latest = max(pairs, key=lambda p: p[1])

    return {
        "provider": "un_data_portal",
        "indicator_id": 49,
        "location_id": 840,
        "date": str(latest_year),
        "value": latest,
        "unit": "persons",
        "citation_url": "https://population.un.org/dataportal/",
    }
