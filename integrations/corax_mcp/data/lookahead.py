# -*- coding: utf-8 -*-
"""Lookahead bias detection for CORAX.

Scans Python source files for common forward-looking data usage patterns.
"""

import ast
import re
from pathlib import Path
from typing import Any

# Patterns that suggest lookahead bias in Python code
_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\.shift\(\s*-\d+"),
        "Negative shift on label/target — likely introduces future data",
        "critical",
    ),
    (
        re.compile(r"\.shift\(\s*0\s*\)"),
        "Zero shift — no temporal offset, label aligns with same-period feature",
        "warning",
    ),
    (
        re.compile(r"\.rolling\(.*\)\.mean\(\)(?!.*\.shift)"),
        "Rolling mean without explicit shift — may include current observation in label",
        "warning",
    ),
    (
        re.compile(r"fit_transform\("),
        "fit_transform on potentially full dataset — fit on train only",
        "critical",
    ),
    (
        re.compile(r"\.pct_change\(.*\)(?!.*\.shift)"),
        "pct_change without shift — may leak current return into features",
        "warning",
    ),
    (
        re.compile(r"train_test_split\(.*shuffle\s*=\s*True"),
        "Shuffled train/test split on time-series data — destroys temporal order",
        "critical",
    ),
    (
        re.compile(r"sample\(.*frac\s*="),
        "Random sampling — may break temporal ordering",
        "warning",
    ),
    (
        re.compile(r"\.mean\(\)\s*$", re.MULTILINE),
        "Global mean (not rolling/expanding) — potential full-sample stat",
        "warning",
    ),
    (
        re.compile(r"\.std\(\)\s*$", re.MULTILINE),
        "Global std (not rolling/expanding) — potential full-sample stat",
        "warning",
    ),
]


class _ShiftVisitor(ast.NodeVisitor):
    """AST visitor to find shift() calls with negative values."""

    def __init__(self) -> None:
        self.hits: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Attribute) and node.func.attr == "shift":
            for arg in node.args:
                if isinstance(arg, ast.UnaryOp) and isinstance(arg.op, ast.USub):
                    self.hits.append(
                        {
                            "line": node.lineno,
                            "pattern": "AST: negative shift() argument",
                            "severity": "critical",
                        }
                    )
                elif isinstance(arg, ast.Constant) and isinstance(
                    arg.value, (int, float)
                ):
                    if arg.value < 0:
                        self.hits.append(
                            {
                                "line": node.lineno,
                                "pattern": f"AST: shift({arg.value}) — negative value",
                                "severity": "critical",
                            }
                        )
        self.generic_visit(node)


def validate_no_lookahead(file_path: str, shift: int = 1) -> dict[str, Any]:
    """Scan a Python file for lookahead bias patterns.

    Returns {clean: bool, violations: [{line, pattern, severity}]}.
    """
    p = Path(file_path)
    if not p.exists():
        return {
            "clean": False,
            "violations": [
                {
                    "line": 0,
                    "pattern": f"File not found: {file_path}",
                    "severity": "error",
                }
            ],
        }

    try:
        source = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return {
            "clean": False,
            "violations": [
                {"line": 0, "pattern": f"Cannot read: {e}", "severity": "error"}
            ],
        }

    violations: list[dict[str, Any]] = []
    lines = source.splitlines()

    # Regex scan
    for line_no, line in enumerate(lines, start=1):
        for pat, desc, severity in _PATTERNS:
            if pat.search(line):
                violations.append(
                    {
                        "line": line_no,
                        "pattern": desc,
                        "severity": severity,
                    }
                )

    # AST scan for shift() calls
    try:
        tree = ast.parse(source, filename=file_path)
        visitor = _ShiftVisitor()
        visitor.visit(tree)
        # Merge, dedup by line
        existing_lines = {
            v["line"] for v in violations if "shift" in v["pattern"].lower()
        }
        for hit in visitor.hits:
            if hit["line"] not in existing_lines:
                violations.append(hit)
    except SyntaxError:
        violations.append(
            {
                "line": 0,
                "pattern": "AST parse failed — syntax error in source",
                "severity": "warning",
            }
        )

    violations.sort(key=lambda v: v["line"])
    return {"clean": len(violations) == 0, "violations": violations}
