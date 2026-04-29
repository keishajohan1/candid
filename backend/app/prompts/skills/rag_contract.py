"""RAG tier definitions plus Tier 1A / Tier 1B blocks (same numbering as legacy builder)."""


def get_rag_contract_skill(
    facts: list[str],
    trusted_api_fact_lines: list[str] | None,
    *,
    idx_start: int,
) -> str:
    """Return RAG DATA CONTRACT plus formatted Tier 1A / Tier 1B sections."""
    idx = idx_start
    t1b_lines = trusted_api_fact_lines or []

    if t1b_lines:
        tier1b = "TIER 1B — TRUSTED API FACTS (live; cross-verified or labeled provisional):\n" + "\n".join(
            f"[{i}] {line}" for i, line in enumerate(t1b_lines, start=idx)
        )
        idx += len(t1b_lines)
    elif facts:
        tier1b = (
            "TIER 1B — TRUSTED API FACTS: (not fetched — Tier 1A static knowledge base "
            "already matched this topic; live APIs are skipped to avoid conflicting figures.)"
        )
    else:
        tier1b = (
            "TIER 1B — TRUSTED API FACTS: (none produced this turn — no matching trusted "
            "API profile, missing optional keys, or providers returned no usable series.)"
        )

    if facts:
        tier1a = (
            "TIER 1A — STATIC VERIFIED FACTS (curated knowledge base):\n"
            + "\n".join(f"[{i}] {f}" for i, f in enumerate(facts, start=idx))
        )
        idx += len(facts)
    else:
        tier1a = "TIER 1A — STATIC VERIFIED FACTS: (none matched for this session's topic.)"

    _ = idx  # numbering parity with legacy builder (may extend future tiers)

    rag_data_contract = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAG DATA CONTRACT (backend-enforced)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
· TIER 1A — Static verified facts: curated knowledge base strings (when any match the topic).
· TIER 1B — Trusted API facts: World Bank (open), FRED (optional key), UN Data Portal (optional bearer token).
  The backend calls Tier 1B only when Tier 1A matched nothing for this session, to avoid duplicate or conflicting figures.
  Lines may read CROSS-VERIFIED (two providers agree within tolerance), PROVISIONAL (single provider or same-publisher add-on),
  or explicit disagreement text—preserve that nuance in how you speak about certainty.
· TIER 2 — Social excerpts below (e.g. Reddit): public discourse and opinion only; never factual proof.
· Do not invent statistics, URLs, or study results. If a tier is empty, acknowledge uncertainty rather than filling gaps.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".strip()

    return rag_data_contract + "\n\n" + tier1a + "\n\n" + tier1b
