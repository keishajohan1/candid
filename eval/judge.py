"""
eval/judge.py

LLM-as-judge: scores a single agent response against the rubric dimensions
using a dedicated, low-temperature Claude call.

Development-time only. No user data collected. No production telemetry.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from eval.personas import EvalScenario
from eval.rubric import RUBRIC, RubricDimension

logger = logging.getLogger(__name__)

# Use a fast/cheap model for judging; override via EVAL_JUDGE_MODEL env var.
_DEFAULT_JUDGE_MODEL = "claude-haiku-4-5"
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", _DEFAULT_JUDGE_MODEL)


@dataclass
class JudgementResult:
    dimension_id: str
    dimension_name: str
    score: int          # 1–5
    reason: str
    red_flag: bool      # True if this dimension has auto_fail_on_one and score == 1


def _build_judge_prompt(
    scenario: EvalScenario,
    agent_response: str,
    dimension: RubricDimension,
    system_prompt_used: str,
) -> str:
    criteria_block = "\n".join(
        f"  Score {score}: {desc}"
        for score, desc in sorted(dimension.criteria.items(), reverse=True)
    )

    expected = "\n".join(f"  - {b}" for b in scenario.expected_behaviors)
    forbidden = "\n".join(f"  - {b}" for b in scenario.forbidden_behaviors)

    return f"""You are an expert evaluator for an AI-powered educational discussion system called Candid.
Your job is to score a single AI response against ONE specific rubric dimension.
You must be rigorous, calibrated, and cite specific evidence from the response text.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCENARIO CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scenario ID      : {scenario.id}
Category         : {scenario.category}
Agent Persona    : {scenario.persona}
User Emotional State: {scenario.emotional_state}
Turn Index       : {scenario.turn_index}  (1 = first contact)
Topic            : {scenario.topic or '(none specified)'}

USER MESSAGE:
{scenario.message}

PRIOR CONVERSATION:
{chr(10).join(f'  [{i+1}] {m}' for i, m in enumerate(scenario.prior_messages)) or '  (none — this is turn 1)'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT WAS EXPECTED OF THE AGENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Expected behaviors a good response would include:
{expected or '  (see rubric criteria)'}

Behaviors that should NOT appear:
{forbidden or '  (see rubric criteria)'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AGENT RESPONSE TO EVALUATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{agent_response}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIMENSION TO SCORE: {dimension.name.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use the following criteria EXACTLY. Do not interpolate between scores.
Choose the single integer (1–5) that best fits:

{criteria_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Read the agent response carefully in the context of the scenario.
2. Identify specific text evidence for your score.
3. Choose a score from 1 to 5 using the criteria above.
4. Provide a concise (2–4 sentence) reason citing specific evidence.
5. Be strict. A 5 must genuinely earn it. A 3 is adequate, not good.

Respond ONLY with valid JSON in this exact shape:
{{
  "score": <integer 1-5>,
  "reason": "<2-4 sentence explanation with specific evidence from the response>"
}}

Do not include any text outside the JSON object."""


class LLMJudge:
    """Scores agent responses against rubric dimensions using a dedicated Claude call."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def score_dimension(
        self,
        scenario: EvalScenario,
        agent_response: str,
        dimension: RubricDimension,
        system_prompt_used: str = "",
    ) -> JudgementResult:
        """Score one response against one rubric dimension."""
        prompt = _build_judge_prompt(scenario, agent_response, dimension, system_prompt_used)

        result = await self._client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=512,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = result.content[0].text.strip()
        score, reason = self._parse_judge_output(raw, dimension)

        red_flag = dimension.auto_fail_on_one and score == 1
        if red_flag:
            logger.warning(
                "RED FLAG: Dimension %r scored 1 (auto_fail_on_one=True) for scenario %r",
                dimension.id,
                scenario.id,
            )

        return JudgementResult(
            dimension_id=dimension.id,
            dimension_name=dimension.name,
            score=score,
            reason=reason,
            red_flag=red_flag,
        )

    def _parse_judge_output(self, raw: str, dimension: RubricDimension) -> tuple[int, str]:
        """Parse JSON output from judge, with fallback extraction."""
        try:
            # Strip any markdown code fencing the model might add
            clean = re.sub(r"^```(?:json)?\s*|```\s*$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(clean)
            score = int(data["score"])
            if not 1 <= score <= 5:
                raise ValueError(f"Score {score} out of range")
            reason = str(data.get("reason", "No reason provided."))
            return score, reason
        except Exception as exc:
            logger.warning("Judge output parse failed for %r: %s\nRaw: %s", dimension.id, exc, raw[:200])
            # Fallback: scan for a digit
            match = re.search(r'"score"\s*:\s*([1-5])', raw)
            if match:
                return int(match.group(1)), "(parse fallback) " + raw[:300]
            # Default to 3 (adequate) with a warning embedded in the reason
            return 3, f"[PARSE ERROR — defaulted to 3. Raw judge output: {raw[:300]}]"

    async def score_all_dimensions(
        self,
        scenario: EvalScenario,
        agent_response: str,
        system_prompt_used: str = "",
        dimensions: list[RubricDimension] | None = None,
    ) -> list[JudgementResult]:
        """Score a response against all relevant rubric dimensions sequentially."""
        import asyncio

        target_dims = dimensions if dimensions is not None else RUBRIC

        # Filter to dimensions declared primary for this scenario, if specified;
        # otherwise score all dimensions.
        if scenario.primary_dimensions:
            primary_set = set(scenario.primary_dimensions)
            primary_dims = [d for d in target_dims if d.id in primary_set]
            secondary_dims = [d for d in target_dims if d.id not in primary_set]
        else:
            primary_dims = target_dims
            secondary_dims = []

        # Score all dimensions (primary first, then secondary)
        results: list[JudgementResult] = []
        for dim in primary_dims + secondary_dims:
            result = await self.score_dimension(
                scenario=scenario,
                agent_response=agent_response,
                dimension=dim,
                system_prompt_used=system_prompt_used,
            )
            results.append(result)

        return results


class StubJudge:
    """Offline judge that returns canned scores for pipeline validation without API calls."""

    async def score_all_dimensions(
        self,
        scenario: EvalScenario,
        agent_response: str,
        system_prompt_used: str = "",
        dimensions: list[RubricDimension] | None = None,
    ) -> list[JudgementResult]:
        target_dims = dimensions if dimensions is not None else RUBRIC
        return [
            JudgementResult(
                dimension_id=dim.id,
                dimension_name=dim.name,
                score=4,  # Stub: returns "Good" for all dimensions
                reason="[STUB MODE] Canned score — no real API call made.",
                red_flag=False,
            )
            for dim in target_dims
        ]
