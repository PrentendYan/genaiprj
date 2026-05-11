# -*- coding: utf-8 -*-
"""Command-line entrypoint for the quant audit benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .auditor import PROFILE_THRESHOLDS, evaluate, load_cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the quant audit benchmark.")
    parser.add_argument("--cases", required=True, help="Path to benchmark cases JSON.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_THRESHOLDS),
        help="Run one profile instead of all profiles.",
    )
    args = parser.parse_args()

    case_path = Path(args.cases)
    cases = load_cases(case_path)
    profiles = [args.profile] if args.profile else sorted(PROFILE_THRESHOLDS)
    results = [evaluate(cases, profile) for profile in profiles]

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
