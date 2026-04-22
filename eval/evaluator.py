"""
eval/evaluator.py

Main evaluation orchestrator.
For each scenario: builds the agent system prompt, calls the Guided Inquiry Engine,
then dispatches scores to the LLM judge across all rubric dimensions.

Development-time only. No user data collected. No production telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Ensure the backend package is importable when running from repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND_PATH = os.path.join(_REPO_ROOT, "backend")
if _BACKEND_PATH not in sys.path:
    sys.path.insert(0, _BACKEND_PATH)

from eval.judge import JudgementResult, LLMJudge, StubJudge
from eval.personas import ALL_SCENARIOS, EvalScenario, scenarios_for_category
from eval.rubric import RUBRIC, RED_FLAG_OTHER, RubricDimension, score_tier

logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    scenario: EvalScenario
    agent_response: str
    system_prompt_used: str
    judgements: list[JudgementResult]
    usage: dict = field(default_factory=dict)
    error: str | None = None  # set if the agent call itself failed

    @property
    def dimension_scores(self) -> dict[str, int]:
        return {j.dimension_id: j.score for j in self.judgements}

    @property
    def total_score(self) -> int:
        return sum(j.score for j in self.judgements)

    @property
    def red_flags(self) -> list[str]:
        return [
            f"Score of 1 in '{j.dimension_name}' (auto-fail dimension)"
            for j in self.judgements
            if j.red_flag
        ]

    @property
    def passed(self) -> bool:
        """A scenario passes if no red flags fired and total >= 21 (Acceptable tier)."""
        return not self.red_flags and self.total_score >= 21 and self.error is None


@dataclass
class EvalSummary:
    run_id: str
    started_at: datetime
    completed_at: datetime
    category_filter: str | None
    stub_mode: bool
    scenarios_run: int
    scenarios_passed: int
    scenario_results: list[ScenarioResult]

    # Aggregate dimension scores (dimension_id → avg score across all scenarios)
    dimension_averages: dict[str, float] = field(default_factory=dict)

    # Total score averaged across scenarios
    avg_total_score: float = 0.0
    avg_latency_ms: float = 0.0
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    overall_tier: str = ""

    # Red flags fired across all scenarios
    all_red_flags: list[str] = field(default_factory=list)

    # Whether the suite as a whole passes the deployment gate
    deployment_gate_passed: bool = False

    @property
    def pass_rate(self) -> float:
        if self.scenarios_run == 0:
            return 0.0
        return self.scenarios_passed / self.scenarios_run


class EvalRunner:
    """
    Orchestrates the full evaluation run.

    Usage:
        runner = EvalRunner(api_key="sk-ant-...", stub_mode=False)
        summary = await runner.run(category_filter=None, min_total=28)
    """

    def __init__(self, api_key: str, stub_mode: bool = False) -> None:
        self._api_key = api_key
        self._stub_mode = stub_mode

        if stub_mode:
            self._judge: LLMJudge | StubJudge = StubJudge()
        else:
            self._judge = LLMJudge(api_key=api_key)

    async def run(
        self,
        category_filter: str | None = None,
        min_total: int = 28,
    ) -> EvalSummary:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        started_at = datetime.now(timezone.utc)

        scenarios = (
            ALL_SCENARIOS
            if category_filter is None
            else scenarios_for_category(category_filter)
        )

        if not scenarios:
            raise ValueError(
                f"No scenarios found for category {category_filter!r}. "
                f"Valid categories: {sorted({s.category for s in ALL_SCENARIOS})}"
            )

        results: list[ScenarioResult] = []
        for scenario in scenarios:
            logger.info("Running scenario: %s (%s)", scenario.id, scenario.description)
            result = await self._run_scenario(scenario)
            results.append(result)
            _log_scenario_result(result)

        summary = self._compute_summary(
            run_id=run_id,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            category_filter=category_filter,
            results=results,
            min_total=min_total,
        )
        return summary

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    async def _run_scenario(self, scenario: EvalScenario) -> ScenarioResult:
        system_prompt = ""
        agent_response = ""
        error: str | None = None
        usage: dict = {}

        try:
            system_prompt, agent_response, usage = await self._call_agent(scenario)
        except Exception as exc:
            error = str(exc)
            logger.error("Agent call failed for scenario %s: %s", scenario.id, exc)
            agent_response = f"[AGENT ERROR: {exc}]"

        try:
            judgements = await self._judge.score_all_dimensions(
                scenario=scenario,
                agent_response=agent_response,
                system_prompt_used=system_prompt,
            )
        except Exception as exc:
            logger.error("Judge failed for scenario %s: %s", scenario.id, exc)
            # Produce degraded results rather than crashing
            judgements = [
                __import__("eval.judge", fromlist=["JudgementResult"]).JudgementResult(
                    dimension_id=d.id,
                    dimension_name=d.name,
                    score=1,
                    reason=f"[JUDGE ERROR: {exc}]",
                    red_flag=d.auto_fail_on_one,
                )
                for d in RUBRIC
            ]

        return ScenarioResult(
            scenario=scenario,
            agent_response=agent_response,
            system_prompt_used=system_prompt,
            judgements=judgements,
            usage=usage,
            error=error,
        )

    async def _call_agent(self, scenario: EvalScenario) -> tuple[str, str, dict]:
        """Build the Candid system prompt and call the Guided Inquiry Engine."""
        from app.services.knowledge_base import get_verified_facts_for_topic
        from app.utils.prompts import (
            build_socratic_system_prompt,
            build_socratic_user_content,
        )

        facts = get_verified_facts_for_topic(scenario.topic)
        system_prompt = build_socratic_system_prompt(
            topic=scenario.topic,
            turn_index=scenario.turn_index,
            history=scenario.prior_messages,
            source_items=[],  # No social media excerpts in eval
            facts=facts,
            trusted_api_fact_lines=None,
        )

        # In stub mode, return a canned response to avoid real API calls
        if self._stub_mode:
            stub_response = (
                f"[STUB AGENT RESPONSE for scenario {scenario.id!r}] "
                "Inflation reflects a complex interplay of monetary policy, supply-chain dynamics, "
                "and fiscal stimulus — economists genuinely disagree on the dominant cause. "
                "Where would you like to focus: the monetary mechanisms, the supply-side factors, "
                "or the distributional impacts on different income groups?"
            )
            return system_prompt, stub_response, {"latency_ms": 100, "input_tokens": 10, "output_tokens": 20}

        from app.services.claude_service import ClaudeService

        user_content = build_socratic_user_content(scenario.message)
        service = ClaudeService()
        result = await service.generate_socratic_response(
            system_prompt=system_prompt,
            user_content=user_content,
            sources_for_client=[],
        )
        return system_prompt, result["response_text"], result.get("usage", {})


    def _compute_summary(
        self,
        run_id: str,
        started_at: datetime,
        completed_at: datetime,
        category_filter: str | None,
        results: list[ScenarioResult],
        min_total: int,
    ) -> EvalSummary:
        passed_count = sum(1 for r in results if r.passed)
        all_red_flags: list[str] = []
        for r in results:
            for flag in r.red_flags:
                all_red_flags.append(f"[{r.scenario.id}] {flag}")

        # Per-dimension averages
        dim_scores: dict[str, list[int]] = {d.id: [] for d in RUBRIC}
        for r in results:
            for j in r.judgements:
                if j.dimension_id in dim_scores:
                    dim_scores[j.dimension_id].append(j.score)

        dimension_averages = {
            dim_id: (sum(scores) / len(scores) if scores else 0.0)
            for dim_id, scores in dim_scores.items()
        }

        scored_results = [r for r in results if r.error is None]
        avg_total = (
            sum(r.total_score for r in scored_results) / len(scored_results)
            if scored_results
            else 0.0
        )
        overall_tier = score_tier(int(round(avg_total)))

        avg_latency = sum(r.usage.get("latency_ms", 0) for r in results) / len(results) if results else 0.0
        avg_in_tokens = sum(r.usage.get("input_tokens", 0) for r in results) / len(results) if results else 0.0
        avg_out_tokens = sum(r.usage.get("output_tokens", 0) for r in results) / len(results) if results else 0.0

        gate_passed = (
            not all_red_flags
            and avg_total >= min_total
            and all(r.error is None for r in results)
        )

        return EvalSummary(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            category_filter=category_filter,
            stub_mode=self._stub_mode,
            scenarios_run=len(results),
            scenarios_passed=passed_count,
            scenario_results=results,
            dimension_averages=dimension_averages,
            avg_total_score=avg_total,
            avg_latency_ms=avg_latency,
            avg_input_tokens=avg_in_tokens,
            avg_output_tokens=avg_out_tokens,
            overall_tier=overall_tier,
            all_red_flags=all_red_flags,
            deployment_gate_passed=gate_passed,
        )


def _log_scenario_result(result: ScenarioResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    flags = f"  RED FLAGS: {result.red_flags}" if result.red_flags else ""
    logger.info(
        "  [%s] %s | total=%d | %s%s",
        status,
        result.scenario.id,
        result.total_score,
        result.scenario.description[:60],
        flags,
    )
