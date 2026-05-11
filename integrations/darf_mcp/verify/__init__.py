# -*- coding: utf-8 -*-
"""DARF Verify module -- 4-level implementation verification (GSD-inspired).

Levels:
  1. Exists   — file present at expected path
  2. Substantive — real implementation, not stubs/placeholders
  3. Wired    — imported by other files or has __main__ entry
  4. Runnable — can be imported without errors (dry-run)
"""

import ast
import asyncio
import json
import re
from pathlib import Path
from typing import Any


# Stub/placeholder patterns
_STUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*pass\s*$", re.MULTILINE), "contains bare 'pass' statement"),
    (
        re.compile(r"^\s*raise NotImplementedError", re.MULTILINE),
        "raises NotImplementedError",
    ),
    (re.compile(r"#\s*TODO", re.IGNORECASE), "contains TODO comment"),
    (re.compile(r"#\s*FIXME", re.IGNORECASE), "contains FIXME comment"),
    (re.compile(r"\.\.\.\s*$", re.MULTILINE), "contains ellipsis placeholder"),
]

# Minimum lines for a substantive Python file (excluding blanks/comments)
_MIN_SUBSTANTIVE_LINES = 5


def build_tools() -> list[dict[str, Any]]:
    """Return MCP tool definitions for the Verify module."""
    return [
        {
            "name": "verify_implementation",
            "description": (
                "4-level verification of implementation files (GSD-inspired). "
                "Checks: (1) exists, (2) substantive (not stubs), "
                "(3) wired (imports/entry), (4) runnable (importable). "
                "Returns per-file results with level reached and issues."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to verify.",
                    },
                    "workspace_dir": {
                        "type": "string",
                        "description": "Workspace root directory for relative path resolution and wiring checks.",
                    },
                    "skip_runnable": {
                        "type": "boolean",
                        "description": "Skip level 4 (runnable) check. Useful when dependencies aren't installed.",
                        "default": False,
                    },
                },
                "required": ["files", "workspace_dir"],
            },
        },
    ]


def _count_substantive_lines(source: str) -> int:
    """Count non-blank, non-comment lines."""
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def _check_exists(path: Path) -> dict[str, Any]:
    """Level 1: File exists."""
    if path.exists() and path.is_file():
        return {"level": 1, "status": "PASS", "issue": None}
    return {"level": 1, "status": "FAIL", "issue": f"File not found: {path}"}


def _check_substantive(path: Path) -> dict[str, Any]:
    """Level 2: Real implementation, not stubs."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return {"level": 2, "status": "FAIL", "issue": f"Cannot read: {e}"}

    issues: list[str] = []

    sub_lines = _count_substantive_lines(source)
    if sub_lines < _MIN_SUBSTANTIVE_LINES:
        issues.append(
            f"Only {sub_lines} substantive lines (min {_MIN_SUBSTANTIVE_LINES})"
        )

    for pat, desc in _STUB_PATTERNS:
        matches = pat.findall(source)
        if matches:
            issues.append(f"{desc} ({len(matches)}x)")

    try:
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if len(body) == 1:
                    stmt = body[0]
                    if isinstance(stmt, ast.Pass):
                        issues.append(
                            f"Empty function: {node.name}() at line {node.lineno}"
                        )
                    elif isinstance(stmt, ast.Expr) and isinstance(
                        stmt.value, ast.Constant
                    ):
                        issues.append(
                            f"Docstring-only function: {node.name}() at line {node.lineno}"
                        )
    except SyntaxError:
        issues.append("AST parse failed — syntax error in file")

    if issues:
        return {"level": 2, "status": "FAIL", "issue": "; ".join(issues)}
    return {"level": 2, "status": "PASS", "issue": None}


_workspace_import_cache: dict[Path, set[str]] = {}


def _build_workspace_index(workspace: Path) -> set[str]:
    """Scan workspace once and cache the set of imported module stems."""
    if workspace in _workspace_import_cache:
        return _workspace_import_cache[workspace]
    imported_stems: set[str] = set()
    for py_file in workspace.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(
                r"(?:from\s+(\S+)\s+import|import\s+(\S+))", content
            ):
                module = match.group(1) or match.group(2)
                imported_stems.add(module.split(".")[-1])
        except OSError:
            pass
    _workspace_import_cache[workspace] = imported_stems
    return imported_stems


def _check_wired(path: Path, workspace: Path) -> dict[str, Any]:
    """Level 3: File is imported or has __main__ entry."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        return {"level": 3, "status": "FAIL", "issue": f"Cannot read: {e}"}

    if "if __name__" in source:
        return {"level": 3, "status": "PASS", "issue": None}

    stem = path.parent.name if path.stem == "__init__" else path.stem
    imported = _build_workspace_index(workspace)
    if stem in imported:
        return {"level": 3, "status": "PASS", "issue": None}

    return {
        "level": 3,
        "status": "FAIL",
        "issue": "Not imported by any file and no __main__ entry",
    }


async def _check_runnable(path: Path) -> dict[str, Any]:
    """Level 4: Can be imported without errors (async subprocess)."""
    cmd = (
        "import importlib.util; "
        f"spec = importlib.util.spec_from_file_location('_test', r'{path}'); "
        "assert spec"
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3",
            "-c",
            cmd,
            cwd=str(path.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0:
            return {"level": 4, "status": "PASS", "issue": None}
        err = stderr.decode(errors="ignore").strip()[:200]
        return {"level": 4, "status": "FAIL", "issue": f"Import error: {err}"}
    except asyncio.TimeoutError:
        return {"level": 4, "status": "FAIL", "issue": "Import timed out (>30s)"}
    except Exception as e:
        return {"level": 4, "status": "FAIL", "issue": f"Execution error: {e}"}


async def _verify_file(
    path: Path, workspace: Path, skip_runnable: bool
) -> dict[str, Any]:
    """Run all 4 verification levels on a single file."""
    result: dict[str, Any] = {
        "file": str(path),
        "levels": {},
        "max_level_passed": 0,
        "overall": "FAIL",
    }

    # L1-L3 are synchronous checks
    for level, check_fn in [
        (1, lambda: _check_exists(path)),
        (2, lambda: _check_substantive(path)),
        (3, lambda: _check_wired(path, workspace)),
    ]:
        level_result = check_fn()
        result["levels"][f"L{level}"] = level_result
        if level_result["status"] == "PASS":
            result["max_level_passed"] = level
        else:
            break

    # L4 is async -- only run if L1-L3 all passed
    if not skip_runnable and result["max_level_passed"] >= 3:
        l4 = await _check_runnable(path)
        result["levels"]["L4"] = l4
        if l4["status"] == "PASS":
            result["max_level_passed"] = 4

    max_possible = 3 if skip_runnable else 4
    if result["max_level_passed"] >= max_possible:
        result["overall"] = "PASS"

    return result


async def handle_tool(name: str, arguments: dict[str, Any]) -> str:
    """Route tool calls to their implementations."""
    if name == "verify_implementation":
        files: list[str] = arguments["files"]
        workspace_dir: str = arguments["workspace_dir"]
        skip_runnable: bool = arguments.get("skip_runnable", False)

        workspace = Path(workspace_dir)
        resolved_paths: list[Path] = []
        for file_path in files:
            p = Path(file_path)
            if not p.is_absolute():
                p = workspace / p
            resolved_paths.append(p)

        tasks = [_verify_file(p, workspace, skip_runnable) for p in resolved_paths]
        results = await asyncio.gather(*tasks)
        pass_count = sum(1 for r in results if r["overall"] == "PASS")

        summary = {
            "total": len(files),
            "passed": pass_count,
            "failed": len(files) - pass_count,
            "pass_rate": round(pass_count / len(files) * 100, 1) if files else 0,
            "results": results,
        }
        return json.dumps(summary, ensure_ascii=False, indent=2)

    return json.dumps({"error": f"unknown verify tool: {name}"})
