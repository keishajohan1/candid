import pytest

import app.services.trusted_data.orchestrator as orch_module
from app.core import config
from app.services.trusted_data.orchestrator import TrustedFactsOrchestrator


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_orchestrator_skips_when_static_kb_matches(monkeypatch) -> None:
    monkeypatch.setattr(orch_module, "has_static_kb_for_topic", lambda t: True)
    o = TrustedFactsOrchestrator()
    lines, refs, dbg = await o.build_trusted_facts(topic="economy", message="hello")
    assert lines == [] and refs == []
    assert dbg.get("trusted_api_reason") == "static_kb_matched"


@pytest.mark.asyncio
async def test_orchestrator_disabled_flag(monkeypatch) -> None:
    monkeypatch.setattr(orch_module, "has_static_kb_for_topic", lambda t: False)
    monkeypatch.setattr(orch_module.settings, "enable_trusted_api_fetch", False, raising=False)
    o = TrustedFactsOrchestrator()
    lines, refs, dbg = await o.build_trusted_facts(topic=None, message="inflation and GDP")
    assert lines == []
    assert dbg.get("trusted_api_reason") == "disabled"


@pytest.mark.asyncio
async def test_orchestrator_economy_corroborated_inflation(monkeypatch) -> None:
    monkeypatch.setattr(orch_module, "has_static_kb_for_topic", lambda t: False)
    monkeypatch.setattr(orch_module.settings, "enable_trusted_api_fetch", True, raising=False)

    async def fake_wb(*, country_iso2: str, indicator: str, mrv: int = 1, timeout: float = 15.0):
        if indicator == "FP.CPI.TOTL.ZG":
            return {
                "provider": "world_bank",
                "value": 3.2,
                "date": "2023",
                "citation_url": "https://data.worldbank.org/",
            }
        if indicator == "SL.UEM.TOTL.ZS":
            return {
                "provider": "world_bank",
                "value": 4.0,
                "date": "2023",
                "citation_url": "https://data.worldbank.org/",
            }
        return None

    async def fake_fred(*, series_id: str, units: str = "lin", timeout: float = 15.0):
        if series_id == "CPIAUCSL":
            return {
                "provider": "fred",
                "value": 3.4,
                "date": "2023-12-01",
                "citation_url": "https://fred.stlouisfed.org/",
            }
        if series_id == "UNRATE":
            return {
                "provider": "fred",
                "value": 3.9,
                "date": "2023-12-01",
                "citation_url": "https://fred.stlouisfed.org/",
            }
        return None

    monkeypatch.setattr(orch_module, "wb_latest", fake_wb)
    monkeypatch.setattr(orch_module, "fred_latest", fake_fred)

    o = TrustedFactsOrchestrator()
    lines, refs, dbg = await o.build_trusted_facts(topic=None, message="US inflation and unemployment")
    assert dbg.get("profile") == "economy"
    assert any("CROSS-VERIFIED INFLATION" in ln for ln in lines)
    assert any("CROSS-VERIFIED UNEMPLOYMENT" in ln for ln in lines)
    assert len(refs) >= 4


@pytest.mark.asyncio
async def test_orchestrator_climate_dual_series(monkeypatch) -> None:
    monkeypatch.setattr(orch_module, "has_static_kb_for_topic", lambda t: False)

    async def fake_wb(*, country_iso2: str, indicator: str, mrv: int = 1, timeout: float = 15.0):
        if indicator == "EN.ATM.CO2E.PC":
            return {
                "provider": "world_bank",
                "value": 14.2,
                "date": "2020",
                "citation_url": "https://data.worldbank.org/",
            }
        if indicator == "EG.FEC.RNEW.ZS":
            return {
                "provider": "world_bank",
                "value": 12.5,
                "date": "2020",
                "citation_url": "https://data.worldbank.org/",
            }
        return None

    monkeypatch.setattr(orch_module, "wb_latest", fake_wb)
    monkeypatch.setattr(orch_module, "fred_latest", lambda **k: None)

    o = TrustedFactsOrchestrator()
    lines, _, dbg = await o.build_trusted_facts(topic="climate change", message="carbon")
    assert dbg.get("profile") == "climate"
    assert any("PROVISIONAL" in ln for ln in lines)
    assert any("CORROBORATING METRIC" in ln for ln in lines)


@pytest.mark.asyncio
async def test_orchestrator_population_wb_only(monkeypatch) -> None:
    monkeypatch.setattr(orch_module, "has_static_kb_for_topic", lambda t: False)

    async def fake_wb(*, country_iso2: str, indicator: str, mrv: int = 1, timeout: float = 15.0):
        if indicator == "SP.POP.TOTL":
            return {
                "provider": "world_bank",
                "value": 331_000_000,
                "date": "2022",
                "citation_url": "https://data.worldbank.org/",
            }
        return None

    monkeypatch.setattr(orch_module, "wb_latest", fake_wb)

    async def _no_un() -> None:
        return None

    monkeypatch.setattr(orch_module, "fetch_total_population_us", _no_un)

    o = TrustedFactsOrchestrator()
    lines, refs, dbg = await o.build_trusted_facts(topic=None, message="US population demographics")
    assert dbg.get("profile") == "population"
    assert any("PROVISIONAL" in ln for ln in lines)
    assert refs and refs[0]["source"] == "world_bank"
