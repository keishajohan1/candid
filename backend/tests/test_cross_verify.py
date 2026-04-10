from app.services.trusted_data.cross_verify import (
    corroborate_inflation_percent,
    corroborate_population_totals,
    corroborate_unemployment_percent,
    independent_providers,
)


def test_inflation_corroborates_within_tolerance() -> None:
    r = corroborate_inflation_percent(3.1, 3.4, tolerance=1.0)
    assert r.corroborated


def test_inflation_diverges_beyond_tolerance() -> None:
    r = corroborate_inflation_percent(2.0, 8.0, tolerance=1.0)
    assert not r.corroborated


def test_unemployment_corroborates() -> None:
    r = corroborate_unemployment_percent(4.2, 4.0, tolerance=0.5)
    assert r.corroborated


def test_population_corroborates_relative() -> None:
    r = corroborate_population_totals(330_000_000, 331_000_000, relative_tolerance=0.01)
    assert r.corroborated


def test_independent_providers() -> None:
    assert independent_providers({"provider": "world_bank"}, {"provider": "fred"})
    assert not independent_providers({"provider": "world_bank"}, {"provider": "world_bank"})
