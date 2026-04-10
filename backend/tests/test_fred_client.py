import pytest

import app.services.trusted_data.fred_client as fred_mod
from app.core import config
from app.services.trusted_data.fred_client import fetch_latest_observation


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_fred_returns_none_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "")
    config.get_settings.cache_clear()
    out = await fetch_latest_observation(series_id="UNRATE")
    assert out is None
