"""
eval/run_eval.py

CLI entry point for the Candid pre-deployment evaluation suite.

Usage:
    # Full run against real Claude API
    python -m eval.run_eval

    # Run only safety scenarios
    python -m eval.run_eval --category safety

    # Run in stub mode (no API calls — validates pipeline only)
    python -m eval.run_eval --stub

    # Set custom deployment gate (default: 28 = Strong tier)
    python -m eval.run_eval --min-total 21

    # See all options
    python -m eval.run_eval --help

Development-time only. No user data collected. No production telemetry.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )
    # Silence noisy third-party loggers
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m eval.run_eval",
        description=(
            "Candid AI pre-deployment evaluation suite.\n"
            "Tests the Guided Inquiry Engine against a 7-dimension rubric.\n"
            "Development-time only. No user data collected."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--category",
        metavar="CATEGORY",
        default=None,
        help=(
            "Run only scenarios in this category. "
            "Choices: analytical | committed | resistant | explorer | safety | first_contact. "
            "Omit to run all 21 scenarios."
        ),
    )
    parser.add_argument(
        "--stub",
        action="store_true",
        default=False,
        help=(
            "Run in stub mode: no real API calls are made. "
            "The agent returns a canned response and the judge returns a canned score of 4. "
            "Use this to validate the pipeline without spending API budget."
        ),
    )
    parser.add_argument(
        "--min-total",
        type=int,
        default=28,
        metavar="N",
        help=(
            "Minimum avg total score (7–35) required to pass the deployment gate. "
            "Default: 28 (Strong tier). Use 21 for a looser Acceptable gate."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        default=False,
        help="Skip writing the Markdown/JSON report files.",
    )
    return parser.parse_args(argv)


async def _main(args: argparse.Namespace) -> int:
    """Returns exit code: 0 = gate passed, 1 = gate failed."""
    # Lazy imports so --help works without a valid ANTHROPIC_API_KEY
    from eval.evaluator import EvalRunner
    from eval.report import save_reports

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not args.stub and not api_key:
        print(
            "ERROR: ANTHROPIC_API_KEY environment variable is not set.\n"
            "Set it or run with --stub for offline pipeline validation.",
            file=sys.stderr,
        )
        return 1

    if args.stub:
        # Provide a dummy key so backend Settings() initialises without error
        os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-eval-stub-key-0000000000000000")
        api_key = os.environ["ANTHROPIC_API_KEY"]

    runner = EvalRunner(api_key=api_key, stub_mode=args.stub)

    print(f"\n{'='*60}")
    print("  Candid AI — Pre-Deployment Evaluation Suite")
    mode = "STUB (no API calls)" if args.stub else "LIVE"
    cat = args.category or "all"
    print(f"  Mode: {mode}  |  Category: {cat}  |  Min total: {args.min_total}")
    print(f"{'='*60}\n")

    summary = await runner.run(
        category_filter=args.category,
        min_total=args.min_total,
    )

    # ── Print summary to stdout ─────────────────────────────────────────────
    gate = "✅ PASSED" if summary.deployment_gate_passed else "❌ FAILED"
    print(f"\n{'='*60}")
    print(f"  DEPLOYMENT GATE: {gate}")
    print(f"  Overall tier   : {summary.overall_tier}")
    print(f"  Avg total score: {summary.avg_total_score:.1f} / 35")
    print(f"  Scenarios      : {summary.scenarios_passed}/{summary.scenarios_run} passed")
    print(f"  Red flags      : {len(summary.all_red_flags)}")
    print(f"{'='*60}")

    print("\nDimension Averages:")
    for dim_id, avg in summary.dimension_averages.items():
        bar = "█" * round((avg / 5.0) * 20) + "░" * (20 - round((avg / 5.0) * 20))
        print(f"  {dim_id:<30} {avg:4.2f}  [{bar}]")

    if summary.all_red_flags:
        print("\n🚨 Red Flags Fired:")
        for flag in summary.all_red_flags:
            print(f"  • {flag}")

    if not args.no_report:
        md_path, json_path = save_reports(summary)
        print(f"\nReports saved:")
        print(f"  Markdown : {md_path}")
        print(f"  JSON     : {json_path}")

    return 0 if summary.deployment_gate_passed else 1


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    _configure_logging(args.verbose)

    # Add the backend directory to sys.path for importing app.*
    repo_root = Path(__file__).resolve().parent.parent
    backend_path = repo_root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    exit_code = asyncio.run(_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
