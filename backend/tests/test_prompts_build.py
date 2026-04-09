from app.utils.prompts import build_socratic_system_prompt


def test_build_socratic_system_prompt_includes_tier1a_and_contract() -> None:
    sp = build_socratic_system_prompt(
        topic="economy",
        turn_index=1,
        history=[],
        source_items=[],
        facts=["Fact one (Source A)."],
        trusted_api_fact_lines=None,
    )
    assert "RAG DATA CONTRACT" in sp
    assert "TIER 1A" in sp
    assert "Fact one" in sp
    assert "TIER 1B" in sp
    assert "not fetched" in sp.lower()


def test_build_socratic_system_prompt_tier1b_lines() -> None:
    sp = build_socratic_system_prompt(
        topic=None,
        turn_index=2,
        history=["hello"],
        source_items=[],
        facts=[],
        trusted_api_fact_lines=["CROSS-VERIFIED test (World Bank vs FRED)."],
    )
    assert "CROSS-VERIFIED test" in sp
    assert "TIER 1B" in sp
