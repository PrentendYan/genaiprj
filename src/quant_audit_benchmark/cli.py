# -*- coding: utf-8 -*-
"""Command-line entrypoint for the quant audit benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from integrations.corax_mcp.sentinel import run_sentinel_summary

from .adapters import ADAPTER_NAMES, DEFAULT_ADAPTER_NAMES
from .adapters.corax_ablation import ABLATION_CONDITIONS
from .auditor import PROFILE_THRESHOLDS, evaluate, load_cases
from .runner import evaluate_adapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the quant audit benchmark.")
    parser.add_argument("--cases", required=True, help="Path to benchmark cases JSON.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_THRESHOLDS),
        help="Run one legacy deterministic profile.",
    )
    parser.add_argument(
        "--adapter",
        choices=sorted(ADAPTER_NAMES),
        help="Run one reviewer adapter. Defaults to offline adapters only.",
    )
    parser.add_argument(
        "--model",
        help="Model for live adapters. Overrides QUANT_AUDIT_LIVE_MODEL.",
    )
    parser.add_argument(
        "--run-dir",
        help="Directory for live adapter run artifacts. Defaults to .runtime/runs/<run_id>.",
    )
    parser.add_argument(
        "--condition",
        action="append",
        choices=sorted(ABLATION_CONDITIONS),
        help=(
            "CORAX ablation condition. Only valid with --adapter corax-ablation. "
            "Can be repeated; defaults to codex_codex for that adapter."
        ),
    )
    parser.add_argument(
        "--case-id",
        action="append",
        help="Run only the given case id. Can be repeated.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Run only the first N loaded cases. Useful for low-cost live smoke tests.",
    )
    parser.add_argument(
        "--sentinel-summary",
        action="store_true",
        help="Run one optional Claude Sentinel meta-review over the final evaluation summary.",
    )
    parser.add_argument(
        "--sentinel-model",
        help="Optional Claude model for --sentinel-summary. Defaults to QUANT_AUDIT_SENTINEL_MODEL or Claude CLI default.",
    )
    args = parser.parse_args()

    case_path = Path(args.cases)
    cases = load_cases(case_path)
    if args.case_id:
        selected = set(args.case_id)
        cases = [case for case in cases if case.case_id in selected]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be greater than zero.")
        cases = cases[: args.limit]
    if not cases:
        parser.error("No benchmark cases selected.")
    if args.profile and args.adapter:
        parser.error("--profile and --adapter cannot be used together.")
    if args.condition and args.adapter != "corax-ablation":
        parser.error("--condition is only supported with --adapter corax-ablation.")

    if args.profile:
        results = [evaluate(cases, args.profile)]
    elif args.adapter == "corax-ablation":
        conditions = args.condition or ["codex_codex"]
        results = [
            evaluate_adapter(
                cases,
                args.adapter,
                model=args.model,
                sentinel_model=args.sentinel_model,
                run_dir=args.run_dir,
                condition=condition,
            )
            for condition in conditions
        ]
    else:
        adapters = [args.adapter] if args.adapter else list(DEFAULT_ADAPTER_NAMES)
        results = [
            evaluate_adapter(
                cases,
                adapter,
                model=args.model,
                sentinel_model=args.sentinel_model,
                run_dir=args.run_dir,
            )
            for adapter in adapters
        ]

    output: object = results
    if args.sentinel_summary:
        sentinel_run_dir = args.run_dir or _single_result_run_dir(results)
        output = {
            "evaluations": results,
            "sentinel_summary": run_sentinel_summary(
                results,
                run_dir=sentinel_run_dir,
                model=args.sentinel_model,
            ),
        }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def _single_result_run_dir(results: list[dict[str, object]]) -> str | None:
    if len(results) != 1:
        return None
    run_dir = results[0].get("run_dir")
    return run_dir if isinstance(run_dir, str) else None


if __name__ == "__main__":
    raise SystemExit(main())
