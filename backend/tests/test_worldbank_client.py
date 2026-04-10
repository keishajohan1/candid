import pytest
import httpx

from app.services.trusted_data.worldbank_client import fetch_latest_observation


@pytest.mark.asyncio
async def test_worldbank_parses_latest_value(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list:
            return [
                {"page": 1},
                [{"value": 2.5, "date": "2022", "indicator": {"id": "X"}, "country": {"id": "US"}}],
            ]

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    def fake_client(*args: object, **kwargs: object) -> FakeClient:
        return FakeClient()

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)

    out = await fetch_latest_observation(country_iso2="us", indicator="FP.CPI.TOTL.ZG")
    assert out is not None
    assert out["value"] == 2.5
    assert out["date"] == "2022"
    assert out["provider"] == "world_bank"


@pytest.mark.asyncio
async def test_worldbank_returns_none_on_http_error(monkeypatch) -> None:
    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, *args: object, **kwargs: object) -> None:
            raise httpx.HTTPError("fail")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **k: FakeClient())

    out = await fetch_latest_observation(country_iso2="us", indicator="BAD")
    assert out is None
