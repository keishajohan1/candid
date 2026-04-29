from app.prompts import build_socratic_system_prompt


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
        source_items=[],
        facts=[],
        trusted_api_fact_lines=["CROSS-VERIFIED test (World Bank vs FRED)."],
    )
    assert "CROSS-VERIFIED test" in sp
    assert "TIER 1B" in sp


def test_turn_zero_uses_first_turn_interaction_skips_cognitive_and_persona() -> None:
    sp = build_socratic_system_prompt(
        topic="economy",
        turn_index=0,
        source_items=[{"source": "reddit", "url": "http://example.com", "excerpt": "x"}],
        facts=["Fact."],
        trusted_api_fact_lines=None,
    )
    assert "FIRST MESSAGE ONLY" in sp
    assert "SECTION 2 — COGNITIVE EXECUTION PROTOCOL" not in sp
    assert "SECTION 4 — PERSONA TAXONOMY" not in sp


def test_turn_two_includes_cognitive_skips_persona_without_reddit_rules_on_turn_zero_guard() -> (
    None
):
    sp = build_socratic_system_prompt(
        topic=None,
        turn_index=2,
        source_items=[],
        facts=[],
        trusted_api_fact_lines=None,
    )
    assert "SECTION 2 — COGNITIVE EXECUTION PROTOCOL" in sp
    assert "SECTION 4 — PERSONA TAXONOMY" not in sp


def test_turn_three_includes_persona_taxonomy() -> None:
    sp = build_socratic_system_prompt(
        topic=None,
        turn_index=3,
        source_items=[],
        facts=[],
        trusted_api_fact_lines=None,
    )
    assert "SECTION 4 — PERSONA TAXONOMY" in sp


def test_topic_line_falls_back_to_user_message() -> None:
    sp = build_socratic_system_prompt(
        topic=None,
        user_message="Why are housing costs increasing?",
        turn_index=1,
        source_items=[],
        facts=[],
        trusted_api_fact_lines=None,
    )
    assert "Why are housing costs increasing?" in sp


def test_reddit_rules_only_when_sources_and_turn_positive() -> None:
    item = {"source": "reddit", "url": "http://example.com", "excerpt": "hello"}
    z = build_socratic_system_prompt(
        topic=None,
        turn_index=0,
        source_items=[item],
        facts=[],
        trusted_api_fact_lines=None,
    )
    assert "RULE R1 — NEVER PRESENT REDDIT AS FACTUAL EVIDENCE" not in z

    r = build_socratic_system_prompt(
        topic=None,
        turn_index=1,
        source_items=[item],
        facts=[],
        trusted_api_fact_lines=None,
    )
    assert "RULE R1 — NEVER PRESENT REDDIT AS FACTUAL EVIDENCE" in r
