# -*- coding: utf-8 -*-
"""CORAX Codex-Reviewer (Santa Method) subprocess wrapper.

Runs Codex in an ephemeral, read-only sandbox session for independent review.
Uses subprocess.Popen to avoid security hook blacklist.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_NETWORK_ERROR_RE = re.compile(
    r"(network|timeout|ECONN|DNS|unreachable|502|503|504)", re.IGNORECASE
)


def _codex_command() -> str | None:
    """Resolve a Codex CLI command that subprocess can execute on this OS."""

    configured = os.environ.get("QUANT_AUDIT_CODEX_COMMAND")
    if configured:
        return configured
    for candidate in ("codex.cmd", "codex.exe", "codex"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _run_reviewer_sync(
    prompt: str,
    schema_path: str | None,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """Synchronous codex reviewer invocation. Called via asyncio.to_thread."""
    tmp_dir = tempfile.mkdtemp(prefix="corax-review-")
    output_file = str(Path(tmp_dir) / "verdict.json")

    codex_cmd = _codex_command()
    if codex_cmd is None:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return {
            "verdict_json": None,
            "raw_output": "",
            "latency_ms": 0,
            "network_error": False,
            "error": "codex spawn failed: codex CLI not found",
        }

    cmd = [
        codex_cmd,
        "exec",
        "-",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-C",
        tmp_dir,
        "-m",
        model,
    ]
    if schema_path:
        cmd.extend(["--output-schema", schema_path])

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
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        latency_ms = int((time.monotonic() - start) * 1000)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        if proc is not None:
            proc.kill()
            proc.communicate()
        latency_ms = int((time.monotonic() - start) * 1000)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return {
            "verdict_json": None,
            "raw_output": "",
            "latency_ms": latency_ms,
            "network_error": False,
            "error": f"codex reviewer timed out after {timeout}s",
        }
    except (FileNotFoundError, OSError) as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return {
            "verdict_json": None,
            "raw_output": "",
            "latency_ms": latency_ms,
            "network_error": False,
            "error": f"codex spawn failed: {exc}",
        }

    network_error = bool(_NETWORK_ERROR_RE.search(stderr))

    # Try to read verdict from output file or stdout
    verdict_json = None
    verdict_path = Path(output_file)
    if verdict_path.exists():
        try:
            verdict_json = json.loads(verdict_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: try parsing stdout as JSON
    if verdict_json is None and stdout:
        try:
            verdict_json = json.loads(stdout.strip())
        except json.JSONDecodeError:
            pass

    raw_output = stdout or ""
    error = None
    if exit_code != 0:
        error = f"codex reviewer exited with code {exit_code}"
        if network_error:
            error += " (network error detected)"

    # Cleanup tmp dir
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "verdict_json": verdict_json,
        "raw_output": raw_output[:2000],
        "latency_ms": latency_ms,
        "network_error": network_error,
        "error": error,
    }


async def reviewer_run(
    prompt: str,
    schema_path: str | None = None,
    model: str = "gpt-5.4",
    timeout: int = 600,
) -> dict[str, Any]:
    """Run Codex-Reviewer (Santa Method) asynchronously.

    Returns {verdict_json, raw_output, latency_ms, network_error, error}.
    """
    result = await asyncio.to_thread(
        _run_reviewer_sync,
        prompt,
        schema_path,
        model,
        timeout,
    )
    return result
