# -*- coding: utf-8 -*-
"""Codex CLI adapter for DARF Challenger module.

Wraps `codex` calls behind an async Python interface,
with JSON extraction and verdict validation.

Provides both a ``CodexBackend`` class (implementing
``ChallengerBackend`` protocol) and backward-compatible
module-level ``review()`` / ``get_metrics()`` functions.
"""

import asyncio
import datetime
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from config import DEBUG_LOG_PATH, ensure_runtime_dirs
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import DEBUG_LOG_PATH, ensure_runtime_dirs

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (env-overridable)
# ---------------------------------------------------------------------------
_CODEX_TIMEOUT_S = int(os.environ.get("DARF_CODEX_TIMEOUT", "600"))
_MAX_RETRIES = int(os.environ.get("DARF_CODEX_MAX_RETRIES", "3"))
_BACKOFF_BASE_S = 2

# ---------------------------------------------------------------------------
# Diagnostic file log (DARF debug)
# ---------------------------------------------------------------------------
# 独立的磁盘日志文件，记录 review() 的每个关键决策点。
# 目的：在 MCP server 子进程里排查 fallback 根因。
# 日志永远不 raise，即使写文件失败也不会打断 review。
_DEBUG_LOG_PATH = DEBUG_LOG_PATH
_DEBUG_LOG_MAX_BYTES = int(os.environ.get("DARF_DEBUG_LOG_MAX", str(5 * 1024 * 1024)))


def _debug_log(stage: str, **fields: Any) -> None:
    """Append a JSON line to the debug log. Never raises."""
    try:
        ensure_runtime_dirs()
        # Rotate: if log exceeds max size, keep only the second half
        if (
            _DEBUG_LOG_PATH.exists()
            and _DEBUG_LOG_PATH.stat().st_size > _DEBUG_LOG_MAX_BYTES
        ):
            content = _DEBUG_LOG_PATH.read_bytes()
            _DEBUG_LOG_PATH.write_bytes(content[len(content) // 2 :])

        record = {
            "ts": datetime.datetime.now().isoformat(timespec="microseconds"),
            "pid": os.getpid(),
            "stage": stage,
        }
        record.update(fields)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001 -- 日志失败绝不影响 review
        pass


def _snapshot_env() -> dict[str, Any]:
    """Capture key env vars relevant to codex subprocess spawn."""
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "USER": os.environ.get("USER", ""),
        "SHELL": os.environ.get("SHELL", ""),
        "PWD": os.environ.get("PWD", ""),
        "TMPDIR": os.environ.get("TMPDIR", ""),
        "PYTHON_VERSION": sys.version.split()[0],
        "PYTHON_EXECUTABLE": sys.executable,
        "codex_resolved": _codex_command(),
        "codex_env_keys": sorted(k for k in os.environ if k.startswith("CODEX")),
        "openai_env_keys": sorted(k for k in os.environ if k.startswith("OPENAI")),
    }


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


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"```json\s*(.*?)\s*```", re.DOTALL),
    re.compile(r"```\s*(.*?)\s*```", re.DOTALL),
    # Non-greedy nested braces (fixes old greedy [\s\S]* pattern)
    re.compile(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", re.DOTALL),
]


def _extract_json(raw: str) -> dict[str, Any]:
    """Extract a JSON verdict from potentially noisy Codex output.

    Strategy:
    1. Direct ``json.loads`` on the full text.
    2. Regex patterns (```json, ```, outermost braces) -- only accepted
       when the parsed object contains ``verdict`` or ``checks``.
    3. Fallback error dict with truncated raw output.
    """
    text = raw.strip()

    # 1. Direct parse
    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Regex patterns
    for pattern in _PATTERNS:
        for match in pattern.findall(text):
            try:
                obj = json.loads(match)
                if isinstance(obj, dict) and ("verdict" in obj or "checks" in obj):
                    return obj  # type: ignore[no-any-return]
            except (json.JSONDecodeError, TypeError):
                continue

    # 3. Fallback
    return {
        "error": "invalid_json",
        "message": "Could not extract valid JSON from Codex output",
        "raw_output": raw[:2000],
        "fallback": True,
    }


# ---------------------------------------------------------------------------
# Verdict validation
# ---------------------------------------------------------------------------


def _validate_verdict(obj: dict[str, Any]) -> dict[str, Any]:
    """Annotate verdict dict with validation warnings."""
    if "error" in obj:
        return obj

    missing = [k for k in ("verdict", "checks") if k not in obj]
    if missing:
        obj["_validation_warning"] = f"Missing required fields: {missing}"

    if not obj.get("counter_arguments"):
        obj["_challenger_warning"] = (
            "No counter_arguments provided -- review may be insufficient"
        )

    return obj


# ---------------------------------------------------------------------------
# CodexBackend class
# ---------------------------------------------------------------------------


class CodexBackend:
    """Codex CLI backend implementing the ``ChallengerBackend`` protocol."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model
        self._env_snapshot: dict[str, Any] | None = None
        self._metrics: dict[str, Any] = {
            "total_calls": 0,
            "failures": 0,
            "last_latency_ms": 0,
            "last_error": None,
            "retries_total": 0,
        }

    # -- Protocol methods ---------------------------------------------------

    def is_available(self) -> bool:
        """Check whether ``codex`` binary is on PATH."""
        return _codex_command() is not None

    def get_metrics(self) -> dict[str, Any]:
        """Return current metrics with computed fail_rate and status."""
        total = self._metrics["total_calls"]
        fail_rate = (self._metrics["failures"] / total) if total > 0 else 0.0
        codex_available = self.is_available()
        if not codex_available:
            status = "unavailable"
        elif fail_rate > 0.5 and total >= 3:
            status = "degraded"
        else:
            status = "healthy"
        return {
            **self._metrics,
            "fail_rate": round(fail_rate, 4),
            "status": status,
        }

    async def review(self, prompt: str) -> dict[str, Any]:
        """Send *prompt* to Codex CLI with retry and return parsed verdict.

        Retries up to ``_MAX_RETRIES`` times with exponential backoff.
        On exhaustion returns ``{"fallback": True, ...}`` so callers can
        trigger the Claude fallback path.
        """
        if not self.is_available():
            return {"fallback": True, "reason": "codex_not_found"}

        self._metrics["total_calls"] += 1
        last_error: str | None = None

        for attempt in range(_MAX_RETRIES):
            t0 = time.monotonic()
            try:
                result = await self._single_attempt(prompt)
                latency = int((time.monotonic() - t0) * 1000)
                self._metrics["last_latency_ms"] = latency

                # Success: result has verdict/checks and no error
                if "error" not in result and (
                    "verdict" in result or "checks" in result
                ):
                    return _validate_verdict(result)

                # Soft failure: got a response but no usable verdict
                last_error = result.get("error", "no verdict in response")
                _debug_log("retry", attempt=attempt, reason=last_error)

            except asyncio.TimeoutError:
                last_error = f"timeout after {_CODEX_TIMEOUT_S}s"
                _debug_log("retry", attempt=attempt, reason=last_error)
            except OSError as exc:
                last_error = f"os_error: {exc}"
                # Don't retry auth/permission failures
                if "auth" in str(exc).lower() or "permission" in str(exc).lower():
                    _debug_log("retry_abort_auth", attempt=attempt, reason=last_error)
                    break
                _debug_log("retry", attempt=attempt, reason=last_error)

            # Backoff before next attempt (skip after last attempt)
            if attempt < _MAX_RETRIES - 1:
                self._metrics["retries_total"] += 1
                await asyncio.sleep(_BACKOFF_BASE_S * (2**attempt))

        # All retries exhausted
        self._metrics["failures"] += 1
        self._metrics["last_error"] = last_error
        return {"fallback": True, "reason": last_error}

    # -- Internal -----------------------------------------------------------

    def _get_env_snapshot(self) -> dict[str, Any]:
        """Lazily cached env snapshot for debug logging."""
        if self._env_snapshot is None:
            self._env_snapshot = _snapshot_env()
        return self._env_snapshot

    async def _single_attempt(self, prompt: str) -> dict[str, Any]:
        """Execute a single Codex CLI call. Returns raw parsed dict.

        Raises ``asyncio.TimeoutError`` or ``OSError`` on failure;
        the retry loop in ``review()`` handles these.
        """
        call_id = f"{int(time.time() * 1000)}-{os.getpid()}"
        _debug_log(
            "review_enter",
            call_id=call_id,
            prompt_len=len(prompt),
            env=self._get_env_snapshot(),
        )

        tmp_path: Path | None = None
        tmp_dir: str | None = None
        proc: asyncio.subprocess.Process | None = None
        try:
            # Isolate cwd: codex runs in a fresh temp dir so it cannot read
            # the parent process working directory (blind-review boundary).
            tmp_dir = tempfile.mkdtemp(prefix="darf_codex_cwd_")
            tmp_path = Path(tmp_dir) / "verdict.json"
            _debug_log(
                "tmpfile_created",
                call_id=call_id,
                tmp_dir=tmp_dir,
                tmp_path=str(tmp_path),
            )

            codex_cmd = _codex_command()
            if codex_cmd is None:
                return {"fallback": True, "reason": "codex_not_found"}

            cmd = [
                codex_cmd,
                "exec",
                "-",
                "--skip-git-repo-check",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "-C",
                tmp_dir,
                "-o",
                str(tmp_path),
            ]
            if self.model:
                cmd.extend(["-m", self.model])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _debug_log("subprocess_spawned", call_id=call_id, pid=proc.pid)

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=_CODEX_TIMEOUT_S,
            )

            tmp_file_size = tmp_path.stat().st_size if tmp_path.exists() else -1
            _debug_log(
                "subprocess_done",
                call_id=call_id,
                returncode=proc.returncode,
                stdout_len=len(stdout_bytes or b""),
                stderr_len=len(stderr_bytes or b""),
                stdout_head=(stdout_bytes or b"")[:800].decode(
                    "utf-8", errors="replace"
                ),
                stderr_head=(stderr_bytes or b"")[:800].decode(
                    "utf-8", errors="replace"
                ),
                tmp_file_size=tmp_file_size,
            )

            # Non-zero exit
            if proc.returncode != 0:
                raw_err = (stderr_bytes or stdout_bytes or b"").decode(
                    "utf-8", errors="replace"
                )
                _debug_log(
                    "branch_nonzero_exit",
                    call_id=call_id,
                    exit_code=proc.returncode,
                    raw_err_head=raw_err[:500],
                )
                return {
                    "error": "codex_error",
                    "exit_code": proc.returncode,
                    "message": raw_err[:500],
                    "fallback": True,
                }

            # Read output: prefer -o file, fallback to stdout
            raw_output = ""
            output_source = "none"
            if tmp_path.exists() and tmp_path.stat().st_size > 0:
                raw_output = tmp_path.read_text(encoding="utf-8")
                output_source = "tmp_file"
            else:
                raw_output = (stdout_bytes or b"").decode("utf-8", errors="replace")
                output_source = "stdout"

            _debug_log(
                "output_read",
                call_id=call_id,
                source=output_source,
                raw_len=len(raw_output),
                raw_head=raw_output[:800],
            )

            result = _extract_json(raw_output)
            if "error" not in result:
                result["_raw_output"] = raw_output[:2000]

            if "error" in result:
                _debug_log(
                    "branch_invalid_json",
                    call_id=call_id,
                    error=result.get("error"),
                    message=str(result.get("message", ""))[:300],
                )
            else:
                _debug_log(
                    "branch_success",
                    call_id=call_id,
                    verdict=result.get("verdict"),
                    confidence=result.get("confidence"),
                )

            return result

        except (asyncio.TimeoutError, OSError):
            raise  # Let retry loop handle these
        except Exception as exc:  # noqa: BLE001 catch-all for unexpected
            _debug_log(
                "branch_unexpected_exception",
                call_id=call_id,
                exc_type=type(exc).__name__,
                exc_str=str(exc),
            )
            return {
                "error": "unexpected_exception",
                "exc_type": type(exc).__name__,
                "message": str(exc),
                "fallback": True,
            }
        finally:
            # Ensure codex subprocess is reaped before cleaning tmp_dir.
            # On timeout path, proc may still be running and holding file
            # handles inside tmp_dir, which would race with rmtree.
            if proc is not None and proc.returncode is None:
                try:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                except ProcessLookupError:
                    pass
            if tmp_dir is not None:
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# Backward-compatible module-level API
# ---------------------------------------------------------------------------
# challenger/__init__.py imports ``review`` and ``get_metrics`` at module
# level.  Keep thin wrappers around a lazily-created default instance.

_default_backend: CodexBackend | None = None


def _get_default() -> CodexBackend:
    global _default_backend  # noqa: PLW0603
    if _default_backend is None:
        _default_backend = CodexBackend()
    return _default_backend


def get_metrics() -> dict[str, Any]:
    """Return current metrics (backward-compat wrapper)."""
    return _get_default().get_metrics()


async def review(prompt: str) -> dict[str, Any]:
    """Send *prompt* to Codex CLI (backward-compat wrapper)."""
    return await _get_default().review(prompt)
