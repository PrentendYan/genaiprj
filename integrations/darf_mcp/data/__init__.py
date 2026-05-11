# -*- coding: utf-8 -*-
"""Point-in-Time data validation tools for DARF.

Provides three tools for detecting lookahead bias and data leakage:
- validate_no_lookahead: checks feature/label CSV alignment and date range overlap
- check_temporal_split: validates train/val/test date ordering
- check_normalization_scope: scans Python source for full-dataset normalization
"""

import ast
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def build_tools() -> list[dict[str, Any]]:
    """Return MCP tool definitions for the data validation module."""
    return [
        {
            "name": "validate_no_lookahead",
            "description": (
                "Check two CSV/TSV files (features and labels) for lookahead bias. "
                "Verifies date column existence, row count match, and that feature "
                "dates do not extend beyond label dates with the given shift."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "feature_file": {
                        "type": "string",
                        "description": "Path to the feature CSV/TSV file.",
                    },
                    "label_file": {
                        "type": "string",
                        "description": "Path to the label CSV/TSV file.",
                    },
                    "date_col": {
                        "type": "string",
                        "description": "Name of the date column in both files.",
                    },
                    "shift": {
                        "type": "integer",
                        "description": "Number of rows the label is shifted forward (e.g. 1 means label at t+1).",
                        "default": 1,
                    },
                },
                "required": ["feature_file", "label_file", "date_col"],
            },
        },
        {
            "name": "check_temporal_split",
            "description": (
                "Validate temporal ordering of train/val/test date boundaries. "
                "Checks that train_end < val_start, val_start < val_end, "
                "val_end < test_start, and train_end < test_start."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "train_end": {
                        "type": "string",
                        "description": "ISO date string for end of training period.",
                    },
                    "val_start": {
                        "type": "string",
                        "description": "ISO date string for start of validation period.",
                    },
                    "val_end": {
                        "type": "string",
                        "description": "ISO date string for end of validation period.",
                    },
                    "test_start": {
                        "type": "string",
                        "description": "ISO date string for start of test period.",
                    },
                },
                "required": ["train_end", "val_start", "val_end", "test_start"],
            },
        },
        {
            "name": "check_normalization_scope",
            "description": (
                "Scan a Python source file for patterns that suggest full-dataset "
                "normalization (lookahead via fit_transform, global mean/std, etc.). "
                "Uses regex and AST analysis to find suspicious lines."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code_file": {
                        "type": "string",
                        "description": "Path to the Python source file to scan.",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional additional regex pattern to search for.",
                    },
                },
                "required": ["code_file"],
            },
        },
    ]


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    """Route tool calls to the appropriate handler."""
    if name == "validate_no_lookahead":
        return json.dumps(_validate_lookahead(arguments), ensure_ascii=False, indent=2)
    if name == "check_temporal_split":
        return json.dumps(_check_split(arguments), ensure_ascii=False, indent=2)
    if name == "check_normalization_scope":
        return json.dumps(_check_norm(arguments), ensure_ascii=False, indent=2)
    return json.dumps({"error": f"unknown tool: {name}"})


def _read_csv(path: str) -> tuple[list[dict[str, str]], str]:
    """Read a CSV or TSV file, return (rows_as_dicts, delimiter).

    Delimiter is auto-detected via csv.Sniffer; falls back to extension-based
    inference (.tsv -> tab, otherwise comma) when sniffing fails.
    Raises FileNotFoundError if file does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with p.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = "\t" if p.suffix.lower() == ".tsv" else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
    return rows, delimiter


def _validate_lookahead(args: dict[str, Any]) -> dict[str, Any]:
    """Check feature/label files for lookahead bias."""
    feature_file: str = args["feature_file"]
    label_file: str = args["label_file"]
    date_col: str = args["date_col"]
    shift: int = args.get("shift", 1)

    violations: list[str] = []

    # Read files
    try:
        feat_rows, _ = _read_csv(feature_file)
    except FileNotFoundError as e:
        return {"clean": False, "violations": [str(e)]}
    try:
        label_rows, _ = _read_csv(label_file)
    except FileNotFoundError as e:
        return {"clean": False, "violations": [str(e)]}

    # Check date column exists
    if feat_rows and date_col not in feat_rows[0]:
        violations.append(f"Date column '{date_col}' not found in feature file.")
    if label_rows and date_col not in label_rows[0]:
        violations.append(f"Date column '{date_col}' not found in label file.")

    if violations:
        return {"clean": False, "violations": violations}

    # Check row count match
    if len(feat_rows) != len(label_rows):
        violations.append(
            f"Row count mismatch: feature has {len(feat_rows)} rows, "
            f"label has {len(label_rows)} rows."
        )

    # Check date range overlap with shift
    if feat_rows and label_rows:
        try:
            feat_dates = [row[date_col] for row in feat_rows]
            label_dates = [row[date_col] for row in label_rows]

            # Convert to datetime for reliable comparison
            feat_max_dt = max(datetime.fromisoformat(d) for d in feat_dates)
            label_min_dt = min(datetime.fromisoformat(d) for d in label_dates)
            label_max_dt = max(datetime.fromisoformat(d) for d in label_dates)

            # Feature dates should not extend beyond label range
            if feat_max_dt > label_max_dt:
                violations.append(
                    f"Feature dates extend beyond label dates: "
                    f"feature max={feat_max_dt.date()}, label max={label_max_dt.date()}. "
                    f"With shift={shift}, features may reference future labels."
                )
            # With shift>0, label dates should start after feature dates
            feat_min_dt = min(datetime.fromisoformat(d) for d in feat_dates)
            if shift > 0 and feat_min_dt >= label_min_dt:
                violations.append(
                    f"Potential lookahead: feature min date {feat_min_dt.date()} >= "
                    f"label min date {label_min_dt.date()} with shift={shift}"
                )
        except (ValueError, TypeError) as e:
            violations.append(f"Date parsing error: {e}")

    return {"clean": len(violations) == 0, "violations": violations}


def _parse_date(s: str) -> datetime:
    """Parse an ISO date string, raising ValueError on failure."""
    return datetime.fromisoformat(s)


def _check_split(args: dict[str, Any]) -> dict[str, Any]:
    """Validate temporal ordering of train/val/test boundaries."""
    issues: list[str] = []

    try:
        train_end = _parse_date(args["train_end"])
        val_start = _parse_date(args["val_start"])
        val_end = _parse_date(args["val_end"])
        test_start = _parse_date(args["test_start"])
    except (ValueError, TypeError) as e:
        return {"valid": False, "issues": [f"Date parsing error: {e}"]}

    if train_end >= val_start:
        issues.append(
            f"train_end ({args['train_end']}) must be before val_start ({args['val_start']})."
        )
    if val_start >= val_end:
        issues.append(
            f"val_start ({args['val_start']}) must be before val_end ({args['val_end']})."
        )
    if val_end >= test_start:
        issues.append(
            f"val_end ({args['val_end']}) must be before test_start ({args['test_start']})."
        )
    if train_end >= test_start:
        issues.append(
            f"train_end ({args['train_end']}) must be before test_start ({args['test_start']})."
        )

    return {"valid": len(issues) == 0, "issues": issues}


# Built-in suspicious patterns for normalization scope detection
_SUSPICIOUS_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\.fit_transform\("),
        "fit_transform() may apply to full dataset — split before fitting",
        "Use fit() on train set only, then transform() on val/test separately.",
    ),
    (
        re.compile(r"StandardScaler\(\)\.fit\("),
        "StandardScaler fitted on potentially full dataset",
        "Fit scaler on training data only, then transform other splits.",
    ),
    (
        re.compile(r"PCA\("),
        "PCA instantiation — check if fit() is called on full data",
        "Fit PCA on training data only, then transform other splits.",
    ),
    (
        re.compile(r"\bdf\.mean\(\)"),
        "df.mean() without windowing — may compute global mean",
        "Use rolling mean or compute on training split only.",
    ),
    (
        re.compile(r"\bdata\.mean\(\)"),
        "data.mean() without windowing — may compute global mean",
        "Use rolling mean or compute on training split only.",
    ),
    (
        re.compile(r"\bdf\.std\(\)"),
        "df.std() without windowing — may compute global std",
        "Use rolling std or compute on training split only.",
    ),
    (
        re.compile(r"\bdata\.std\(\)"),
        "data.std() without windowing — may compute global std",
        "Use rolling std or compute on training split only.",
    ),
]


class _FitTransformVisitor(ast.NodeVisitor):
    """AST visitor that finds .fit_transform() method calls with line numbers."""

    def __init__(self) -> None:
        self.hits: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Attribute) and node.func.attr == "fit_transform":
            self.hits.append(
                {
                    "line": node.lineno,
                    "code": f".fit_transform() call at line {node.lineno}",
                    "problem": "fit_transform() applies fit+transform on the same data — likely full dataset",
                    "fix": "Split into .fit(X_train) then .transform(X_val), .transform(X_test).",
                }
            )
        self.generic_visit(node)


def _check_norm(args: dict[str, Any]) -> dict[str, Any]:
    """Scan a Python source file for normalization scope issues."""
    code_file: str = args["code_file"]
    custom_pattern: str | None = args.get("pattern")

    p = Path(code_file)
    if not p.exists():
        return {
            "issues": [
                {
                    "line": 0,
                    "code": "",
                    "problem": f"File not found: {code_file}",
                    "fix": "",
                }
            ]
        }

    try:
        source = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return {
            "issues": [
                {"line": 0, "code": "", "problem": f"Cannot read file: {e}", "fix": ""}
            ]
        }

    lines = source.splitlines()
    issues: list[dict[str, Any]] = []

    # Regex scan for suspicious patterns
    for line_no, line in enumerate(lines, start=1):
        for pat, problem, fix in _SUSPICIOUS_PATTERNS:
            if pat.search(line):
                issues.append(
                    {
                        "line": line_no,
                        "code": line.strip(),
                        "problem": problem,
                        "fix": fix,
                    }
                )

    # Custom pattern scan
    if custom_pattern:
        try:
            custom_re = re.compile(custom_pattern)
            for line_no, line in enumerate(lines, start=1):
                if custom_re.search(line):
                    issues.append(
                        {
                            "line": line_no,
                            "code": line.strip(),
                            "problem": f"Matches custom pattern: {custom_pattern}",
                            "fix": "Review this line for potential data leakage.",
                        }
                    )
        except re.error as e:
            issues.append(
                {
                    "line": 0,
                    "code": custom_pattern,
                    "problem": f"Invalid regex pattern: {e}",
                    "fix": "Fix the regex pattern and retry.",
                }
            )

    # AST parse for fit_transform calls with precise line numbers
    try:
        tree = ast.parse(source, filename=code_file)
        visitor = _FitTransformVisitor()
        visitor.visit(tree)
        # Merge AST hits, avoiding duplicates with regex hits on the same line
        existing_lines = {
            i["line"] for i in issues if "fit_transform" in i.get("problem", "")
        }
        for hit in visitor.hits:
            if hit["line"] not in existing_lines:
                issues.append(hit)
    except SyntaxError:
        # If AST parse fails, we still have regex results — just note it
        issues.append(
            {
                "line": 0,
                "code": "",
                "problem": "AST parse failed (syntax error in source file) — regex results only",
                "fix": "Fix syntax errors in the source file for full analysis.",
            }
        )

    # Sort by line number
    issues.sort(key=lambda i: i["line"])

    return {"issues": issues}
