# -*- coding: utf-8 -*-
"""Command-line entrypoint for the quant audit benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import ADAPTER_NAMES, DEFAULT_ADAPTER_NAMES
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
        "--case-id",
        action="append",
        help="Run only the given case id. Can be repeated.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Run only the first N loaded cases. Useful for low-cost live smoke tests.",
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

    if args.profile:
        results = [evaluate(cases, args.profile)]
    else:
        adapters = [args.adapter] if args.adapter else list(DEFAULT_ADAPTER_NAMES)
        results = [
            evaluate_adapter(
                cases,
                adapter,
                model=args.model,
                run_dir=args.run_dir,
            )
            for adapter in adapters
        ]

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
