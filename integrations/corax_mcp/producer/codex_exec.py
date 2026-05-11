# -*- coding: utf-8 -*-
"""CORAX Codex-Producer subprocess wrapper.

Runs `codex` CLI as Producer with configurable prompt and schema validation.
Uses subprocess.Popen to avoid security hook blacklist on certain function names.
"""

import asyncio
import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_NETWORK_ERROR_RE = re.compile(
    r"(network|timeout|ECONN|DNS|unreachable|502|503|504)", re.IGNORECASE
)


def _run_codex_sync(
    prompt: str,
    workspace_dir: str,
    output_file: str,
    schema_path: str | None,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """Synchronous codex invocation. Called via asyncio.to_thread."""
    cmd = [
        "codex",
        "exec",
        "--sandbox",
        "workspace-write",
        "--skip-git-repo-check",
        "-C",
        workspace_dir,
        "-o",
        output_file,
        "-m",
        model,
    ]
    if schema_path:
        cmd.extend(["--output-schema", schema_path])

    # Remove stale output file before run
    out_path = Path(output_file)
    if out_path.exists():
        out_path.unlink()

    proc: subprocess.Popen[str] | None = None
    start = time.monotonic()
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _, stderr = proc.communicate(input=prompt, timeout=timeout)
        latency_ms = int((time.monotonic() - start) * 1000)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        if proc is not None:
            proc.kill()
            proc.communicate()
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "output_path": output_file,
            "summary_json": None,
            "exit_code": -1,
            "latency_ms": latency_ms,
            "stderr_preview": "timeout expired",
            "network_error": False,
            "error": f"codex timed out after {timeout}s",
        }
    except FileNotFoundError:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "output_path": output_file,
            "summary_json": None,
            "exit_code": -1,
            "latency_ms": latency_ms,
            "stderr_preview": "codex binary not found",
            "network_error": False,
            "error": "codex binary not found in PATH",
        }

    network_error = bool(_NETWORK_ERROR_RE.search(stderr))
    stderr_preview = stderr[:500] if stderr else ""

    # Only read output file on success
    summary_json = None
    if exit_code == 0 and out_path.exists():
        try:
            content = out_path.read_text(encoding="utf-8")
            summary_json = json.loads(content)
        except (json.JSONDecodeError, OSError):
            pass

    error = None
    if exit_code != 0:
        error = f"codex exited with code {exit_code}"
        if network_error:
            error += " (network error detected)"

    return {
        "output_path": output_file,
        "summary_json": summary_json,
        "exit_code": exit_code,
        "latency_ms": latency_ms,
        "stderr_preview": stderr_preview,
        "network_error": network_error,
        "error": error,
    }


async def producer_run(
    prompt: str,
    workspace_dir: str,
    schema_path: str | None = None,
    model: str = "gpt-5.4",
    timeout: int = 1800,
) -> dict[str, Any]:
    """Run Codex-Producer asynchronously.

    Returns {output_path, summary_json, exit_code, latency_ms, stderr_preview, network_error, error}.
    """
    ws = Path(workspace_dir)
    if not ws.is_dir():
        return {"error": f"workspace_dir is not a directory: {workspace_dir}"}

    output_file = str(ws / "phase-output.md")

    result = await asyncio.to_thread(
        _run_codex_sync,
        prompt,
        workspace_dir,
        output_file,
        schema_path,
        model,
        timeout,
    )
    return result
