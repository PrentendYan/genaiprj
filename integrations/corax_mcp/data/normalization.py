# -*- coding: utf-8 -*-
"""Normalization scope detection for CORAX.

Scans Python files for patterns suggesting full-dataset normalization
(e.g., fit_transform before train/test split, global mean/std).
"""

import ast
import re
from pathlib import Path
from typing import Any

_SUSPICIOUS_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\.fit_transform\("),
        "fit_transform() may apply to full dataset — split before fitting",
        "Use fit() on train set only, then transform() on val/test separately.",
    ),
    (
        re.compile(r"StandardScaler\(\)\.fit\("),
        "StandardScaler fitted on potentially full dataset",
        "Fit scaler on training data only.",
    ),
    (
        re.compile(r"MinMaxScaler\(\)\.fit\("),
        "MinMaxScaler fitted on potentially full dataset",
        "Fit scaler on training data only.",
    ),
    (
        re.compile(r"PCA\("),
        "PCA instantiation — check if fit() is called on full data",
        "Fit PCA on training data only.",
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
    (
        re.compile(r"\bX\.mean\(\)"),
        "X.mean() — potential full-sample statistic",
        "Compute on training split only.",
    ),
    (
        re.compile(r"\bX\.std\(\)"),
        "X.std() — potential full-sample statistic",
        "Compute on training split only.",
    ),
]


class _FitTransformVisitor(ast.NodeVisitor):
    """AST visitor for fit_transform calls."""

    def __init__(self) -> None:
        self.hits: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Attribute) and node.func.attr == "fit_transform":
            self.hits.append(
                {
                    "line": node.lineno,
                    "code": f".fit_transform() at line {node.lineno}",
                    "problem": "fit_transform() on same data — likely full dataset",
                    "fix": "Split: .fit(X_train) then .transform(X_val/.X_test).",
                }
            )
        self.generic_visit(node)


def check_normalization_scope(code_file: str) -> dict[str, Any]:
    """Scan Python source for full-dataset normalization patterns.

    Returns {clean: bool, violations: [{line, code, problem, fix}]}.
    """
    p = Path(code_file)
    if not p.exists():
        return {
            "clean": False,
            "violations": [
                {
                    "line": 0,
                    "code": "",
                    "problem": f"File not found: {code_file}",
                    "fix": "",
                }
            ],
        }

    try:
        source = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return {
            "clean": False,
            "violations": [
                {"line": 0, "code": "", "problem": f"Cannot read: {e}", "fix": ""}
            ],
        }

    lines = source.splitlines()
    violations: list[dict[str, Any]] = []

    # Regex scan
    for line_no, line in enumerate(lines, start=1):
        for pat, problem, fix in _SUSPICIOUS_PATTERNS:
            if pat.search(line):
                violations.append(
                    {
                        "line": line_no,
                        "code": line.strip(),
                        "problem": problem,
                        "fix": fix,
                    }
                )

    # AST scan
    try:
        tree = ast.parse(source, filename=code_file)
        visitor = _FitTransformVisitor()
        visitor.visit(tree)
        existing_lines = {
            v["line"] for v in violations if "fit_transform" in v.get("problem", "")
        }
        for hit in visitor.hits:
            if hit["line"] not in existing_lines:
                violations.append(hit)
    except SyntaxError:
        violations.append(
            {
                "line": 0,
                "code": "",
                "problem": "AST parse failed — regex results only",
                "fix": "Fix syntax errors for full analysis.",
            }
        )

    violations.sort(key=lambda v: v["line"])
    return {"clean": len(violations) == 0, "violations": violations}
