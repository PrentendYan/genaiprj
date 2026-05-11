# -*- coding: utf-8 -*-
"""Command-line entrypoint for the quant audit benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import ADAPTER_NAMES
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
        help="Run one reviewer adapter. Defaults to all runnable adapters.",
    )
    args = parser.parse_args()

    case_path = Path(args.cases)
    cases = load_cases(case_path)
    if args.profile and args.adapter:
        parser.error("--profile and --adapter cannot be used together.")

    if args.profile:
        results = [evaluate(cases, args.profile)]
    else:
        adapters = [args.adapter] if args.adapter else list(ADAPTER_NAMES)
        results = [evaluate_adapter(cases, adapter) for adapter in adapters]

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
