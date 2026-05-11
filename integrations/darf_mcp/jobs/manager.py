# -*- coding: utf-8 -*-
"""Async job manager — runs Codex reviews in background tasks."""

import asyncio
import logging
from typing import Any

from challenger.protocol import ChallengerBackend
from .store import JobStore, JobStatus

logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self, store: JobStore, backend: ChallengerBackend) -> None:
        self.store = store
        self._backend = backend
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def submit(self, *, brief: str, rubric: str, phase: str) -> str:
        job_id = self.store.create(brief=brief, rubric=rubric, phase=phase)
        task = asyncio.create_task(self._run(job_id))
        self._tasks[job_id] = task
        logger.info("Job %s submitted", job_id)
        return job_id

    def get_status(self, job_id: str) -> dict[str, Any] | None:
        return self.store.get(job_id)

    def get_result(self, job_id: str) -> dict[str, Any] | None:
        job = self.store.get(job_id)
        if job is None:
            return None
        if job["status"] != JobStatus.COMPLETED:
            return {"error": f"Job not completed, status: {job['status']}"}
        return job["result"]

    async def cancel(self, job_id: str) -> bool:
        task = self._tasks.get(job_id)
        if task is None or task.done():
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self.store.update(job_id, status=JobStatus.CANCELLED)
        del self._tasks[job_id]
        logger.info("Job %s cancelled", job_id)
        return True

    async def wait(self, job_id: str, timeout: float = 300.0) -> None:
        task = self._tasks.get(job_id)
        if task is not None:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.store.list_all()

    async def shutdown(self) -> None:
        for job_id, task in list(self._tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.store.mark_running_as_interrupted()
        self._tasks.clear()
        logger.info("JobManager shutdown, all running jobs interrupted")

    async def _run(self, job_id: str) -> None:
        self.store.update(job_id, status=JobStatus.RUNNING)
        try:
            job = self.store.get(job_id)
            assert job is not None
            prompt = f"## Blind Brief\n\n{job['brief']}\n\n## Rubric\n\n{job['rubric']}"
            result = await self._backend.review(prompt)
            self.store.update(job_id, status=JobStatus.COMPLETED, result=result)
            logger.info("Job %s completed", job_id)
        except asyncio.CancelledError:
            logger.info("Job %s cancelled during execution", job_id)
            raise
        except Exception as exc:
            logger.exception("Job %s failed", job_id)
            self.store.update(
                job_id, status=JobStatus.FAILED, result={"error": str(exc)}
            )
