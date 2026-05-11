# -*- coding: utf-8 -*-
"""JSON-file-based job persistence. Each job is one file: {jobs_dir}/{job_id}.json"""

import json
import uuid
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

try:
    from config import JOBS_DIR
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from ..config import JOBS_DIR


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class JobStore:
    def __init__(self, jobs_dir: Path | None = None) -> None:
        self._dir = jobs_dir or JOBS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.json"

    def create(self, *, brief: str, rubric: str, phase: str) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = {
            "id": job_id,
            "status": JobStatus.PENDING,
            "brief": brief,
            "rubric": rubric,
            "phase": phase,
            "result": None,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        self._write(job_id, job)
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        p = self._path(job_id)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        job = self.get(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")
        if status is not None:
            job["status"] = status
        if result is not None:
            job["result"] = result
        job["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        self._write(job_id, job)

    def list_all(self) -> list[dict[str, Any]]:
        jobs = []
        for p in sorted(
            self._dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            try:
                jobs.append(json.loads(p.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return jobs

    def mark_running_as_interrupted(self) -> int:
        count = 0
        for job in self.list_all():
            if job["status"] in (JobStatus.RUNNING, JobStatus.PENDING):
                self.update(job["id"], status=JobStatus.INTERRUPTED)
                count += 1
        return count

    def _write(self, job_id: str, job: dict[str, Any]) -> None:
        self._path(job_id).write_text(
            json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8"
        )
