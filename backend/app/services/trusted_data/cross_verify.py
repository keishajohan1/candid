"""Numeric corroboration between independent (or labeled) providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CorroborationResult:
    corroborated: bool
    note: str


def corroborate_inflation_percent(a: float, b: float, *, tolerance: float = 5.0) -> CorroborationResult:
    """World Bank annual CPI % vs FRED CPI pc1 (both in % points)."""
    if abs(a - b) <= tolerance:
        return CorroborationResult(True, f"within {tolerance} pp (World Bank vs FRED)")
    return CorroborationResult(
        False,
        f"diverged by {abs(a - b):.2f} pp — do not present as a single reconciled figure",
    )


def corroborate_unemployment_percent(a: float, b: float, *, tolerance: float = 3.0) -> CorroborationResult:
    """Modeled ILO (WB) vs BLS-style monthly (FRED UNRATE); allow timing mismatch."""
    if abs(a - b) <= tolerance:
        return CorroborationResult(True, f"within {tolerance} pp (World Bank vs FRED)")
    return CorroborationResult(
        False,
        f"diverged by {abs(a - b):.2f} pp — cite both separately if mentioned",
    )


def corroborate_population_totals(a: float, b: float, *, relative_tolerance: float = 0.04) -> CorroborationResult:
    """Large population totals: relative difference."""
    if a <= 0 or b <= 0:
        return CorroborationResult(False, "non-positive population value")
    rel = abs(a - b) / max(a, b)
    if rel <= relative_tolerance:
        return CorroborationResult(True, f"within {relative_tolerance:.1%} relative (World Bank vs UN Data Portal)")
    return CorroborationResult(False, f"relative gap {rel:.1%} — cite both separately")


def independent_providers(obs_a: dict[str, Any], obs_b: dict[str, Any]) -> bool:
    pa = obs_a.get("provider")
    pb = obs_b.get("provider")
    return bool(pa and pb and pa != pb)
