"""
Tier 1B: fetch trusted API facts only when Tier 1A static KB is empty.

Cross-verification: prefer two independent providers (World Bank + FRED, or World Bank + UN).
Single-provider readings are emitted with an explicit PROVISIONAL label.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.services.knowledge_base import has_static_kb_for_topic
from app.services.trusted_data import cross_verify
from app.services.trusted_data.fred_client import fetch_latest_observation as fred_latest
from app.services.trusted_data.un_client import fetch_total_population_us
from app.services.trusted_data.worldbank_client import fetch_latest_observation as wb_latest

logger = logging.getLogger(__name__)


def _infer_profile(topic: str | None, message: str) -> str | None:
    blob = f"{topic or ''} {message[:800]}".lower()
    econ_kw = (
        "economy",
        "economic",
        "gdp",
        "inflation",
        "unemployment",
        "fed",
        "cpi",
        "jobs",
        "interest rate",
        "recession",
        "labor",
    )
    climate_kw = (
        "climate",
        "carbon",
        "emission",
        "warming",
        "co2",
        "greenhouse",
        "paris agreement",
    )
    pop_kw = ("population", "demographics", "census", "how many people")
    if any(k in blob for k in econ_kw):
        return "economy"
    if any(k in blob for k in climate_kw):
        return "climate"
    if any(k in blob for k in pop_kw):
        return "population"
    return None


class TrustedFactsOrchestrator:
    async def build_trusted_facts(
        self,
        *,
        topic: str | None,
        message: str,
    ) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
        """
        Returns (prompt_lines, client_source_refs, debug).

        Skips entirely when static KB already matched or trusted fetch disabled.
        """
        debug: dict[str, Any] = {
            "trusted_api_skipped": False,
            "trusted_api_reason": None,
            "profile": None,
        }
        topic_key = topic if topic and topic.strip() else None
        blob_for_kb = topic_key or message
        if has_static_kb_for_topic(blob_for_kb):
            debug["trusted_api_skipped"] = True
            debug["trusted_api_reason"] = "static_kb_matched"
            return [], [], debug

        if not settings.enable_trusted_api_fetch:
            debug["trusted_api_skipped"] = True
            debug["trusted_api_reason"] = "disabled"
            return [], [], debug

        profile = _infer_profile(topic_key, message)
        debug["profile"] = profile
        if not profile:
            debug["trusted_api_skipped"] = True
            debug["trusted_api_reason"] = "no_profile_match"
            return [], [], debug

        lines: list[str] = []
        refs: list[dict[str, Any]] = []

        if profile == "economy":
            lines, refs = await self._economy_facts()
        elif profile == "climate":
            lines, refs = await self._climate_facts()
        elif profile == "population":
            lines, refs = await self._population_facts()

        if not lines:
            debug["trusted_api_skipped"] = True
            debug["trusted_api_reason"] = "no_corroborated_or_provisional_facts"
        return lines, refs, debug

    async def _economy_facts(self) -> tuple[list[str], list[dict[str, Any]]]:
        lines: list[str] = []
        refs: list[dict[str, Any]] = []

        wb_inf, fred_inf, wb_uem, fred_uem = await asyncio.gather(
            wb_latest(country_iso2="us", indicator="FP.CPI.TOTL.ZG"),
            fred_latest(series_id="CPIAUCSL", units="pc1"),
            wb_latest(country_iso2="us", indicator="SL.UEM.TOTL.ZS"),
            fred_latest(series_id="UNRATE", units="lin"),
        )

        if wb_inf and fred_inf and cross_verify.independent_providers(wb_inf, fred_inf):
            c = cross_verify.corroborate_inflation_percent(wb_inf["value"], fred_inf["value"])
            if c.corroborated:
                lines.append(
                    f"CROSS-VERIFIED INFLATION (Tier 1B): US consumer-price inflation is about "
                    f"{wb_inf['value']:.2f}% (World Bank FP.CPI.TOTL.ZG, year {wb_inf['date']}) and "
                    f"{fred_inf['value']:.2f}% YoY (FRED CPIAUCSL, {fred_inf['date']}). "
                    f"Sources agree ({c.note})."
                )
                refs.extend(
                    [
                        {"source": "world_bank", "label": "FP.CPI.TOTL.ZG", "url": wb_inf["citation_url"]},
                        {"source": "fred", "label": "CPIAUCSL", "url": fred_inf["citation_url"]},
                    ]
                )
            else:
                lines.append(
                    f"INFLATION (Tier 1B — sources disagree; present carefully): World Bank "
                    f"{wb_inf['value']:.2f}% ({wb_inf['date']}) vs FRED YoY {fred_inf['value']:.2f}% "
                    f"({fred_inf['date']}). {c.note}."
                )
                refs.extend(
                    [
                        {"source": "world_bank", "label": "FP.CPI.TOTL.ZG", "url": wb_inf["citation_url"]},
                        {"source": "fred", "label": "CPIAUCSL", "url": fred_inf["citation_url"]},
                    ]
                )

        if wb_uem and fred_uem and cross_verify.independent_providers(wb_uem, fred_uem):
            c2 = cross_verify.corroborate_unemployment_percent(wb_uem["value"], fred_uem["value"])
            if c2.corroborated:
                lines.append(
                    f"CROSS-VERIFIED UNEMPLOYMENT (Tier 1B): US unemployment near "
                    f"{wb_uem['value']:.2f}% (World Bank SL.UEM.TOTL.ZS, {wb_uem['date']}) vs "
                    f"{fred_uem['value']:.2f}% (FRED UNRATE, {fred_uem['date']}). {c2.note}."
                )
                refs.extend(
                    [
                        {"source": "world_bank", "label": "SL.UEM.TOTL.ZS", "url": wb_uem["citation_url"]},
                        {"source": "fred", "label": "UNRATE", "url": fred_uem["citation_url"]},
                    ]
                )
            else:
                lines.append(
                    f"UNEMPLOYMENT (Tier 1B — sources disagree): World Bank {wb_uem['value']:.2f}% "
                    f"({wb_uem['date']}) vs FRED {fred_uem['value']:.2f}% ({fred_uem['date']}). "
                    f"{c2.note}."
                )
                refs.extend(
                    [
                        {"source": "world_bank", "label": "SL.UEM.TOTL.ZS", "url": wb_uem["citation_url"]},
                        {"source": "fred", "label": "UNRATE", "url": fred_uem["citation_url"]},
                    ]
                )

        # Provisional singles if FRED key missing but WB present
        if not lines and wb_inf:
            lines.append(
                f"PROVISIONAL (single source — World Bank only): US CPI inflation "
                f"{wb_inf['value']:.2f}% in {wb_inf['date']} (FP.CPI.TOTL.ZG). "
                f"Set FRED_API_KEY for automatic corroboration with FRED."
            )
            refs.append({"source": "world_bank", "label": "FP.CPI.TOTL.ZG", "url": wb_inf["citation_url"]})

        return lines, refs

    async def _climate_facts(self) -> tuple[list[str], list[dict[str, Any]]]:
        lines: list[str] = []
        refs: list[dict[str, Any]] = []
        co2, renew = await asyncio.gather(
            wb_latest(country_iso2="us", indicator="EN.ATM.CO2E.PC"),
            wb_latest(country_iso2="us", indicator="EG.FEC.RNEW.ZS"),
        )
        if co2:
            lines.append(
                "PROVISIONAL (World Bank only — no second independent provider this session): "
                f"US CO₂ emissions per capita {co2['value']:.3f} metric tons "
                f"(EN.ATM.CO2E.PC, {co2['date']}). Compare policy implications, not just magnitude."
            )
            refs.append({"source": "world_bank", "label": "EN.ATM.CO2E.PC", "url": co2["citation_url"]})
        if renew:
            lines.append(
                "CORROBORATING METRIC (same institution, distinct series — World Bank): "
                f"Renewable energy consumption ~{renew['value']:.2f}% of final consumption "
                f"(EG.FEC.RNEW.ZS, {renew['date']}). Use alongside CO₂ series, not as duplicate proof."
            )
            refs.append({"source": "world_bank", "label": "EG.FEC.RNEW.ZS", "url": renew["citation_url"]})
        return lines, refs

    async def _population_facts(self) -> tuple[list[str], list[dict[str, Any]]]:
        lines: list[str] = []
        refs: list[dict[str, Any]] = []
        wb_pop, un_pop = await asyncio.gather(
            wb_latest(country_iso2="us", indicator="SP.POP.TOTL"),
            fetch_total_population_us(),
        )
        if wb_pop and un_pop and cross_verify.independent_providers(wb_pop, un_pop):
            c = cross_verify.corroborate_population_totals(wb_pop["value"], un_pop["value"])
            if c.corroborated:
                lines.append(
                    f"CROSS-VERIFIED US POPULATION (Tier 1B): World Bank SP.POP.TOTL "
                    f"{wb_pop['value']:,.0f} ({wb_pop['date']}) vs UN Data Portal indicator 49 "
                    f"{un_pop['value']:,.0f} ({un_pop['date']}). {c.note}."
                )
            else:
                lines.append(
                    f"POPULATION (Tier 1B — institutions diverge): World Bank {wb_pop['value']:,.0f} "
                    f"({wb_pop['date']}) vs UN {un_pop['value']:,.0f} ({un_pop['date']}). {c.note}."
                )
            refs.extend(
                [
                    {"source": "world_bank", "label": "SP.POP.TOTL", "url": wb_pop["citation_url"]},
                    {"source": "un_data_portal", "label": "indicator/49", "url": un_pop["citation_url"]},
                ]
            )
        elif wb_pop:
            lines.append(
                "PROVISIONAL (single source — World Bank): US population total "
                f"{wb_pop['value']:,.0f} ({wb_pop['date']}, SP.POP.TOTL). "
                "Add UN_DATAPORTAL_BEARER_TOKEN for UN corroboration."
            )
            refs.append({"source": "world_bank", "label": "SP.POP.TOTL", "url": wb_pop["citation_url"]})
        return lines, refs
