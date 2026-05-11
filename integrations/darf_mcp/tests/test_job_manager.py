# -*- coding: utf-8 -*-
import asyncio

import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from jobs.manager import JobManager
from jobs.store import JobStore, JobStatus


@pytest.fixture
def mock_backend() -> AsyncMock:
    backend = AsyncMock()
    backend.review.return_value = {"verdict": "PASS", "checks": []}
    backend.is_available.return_value = True
    return backend


@pytest.fixture
def manager(tmp_jobs_dir: Path, mock_backend: AsyncMock) -> JobManager:
    return JobManager(store=JobStore(tmp_jobs_dir), backend=mock_backend)


@pytest.mark.asyncio
async def test_submit_returns_job_id(manager: JobManager) -> None:
    job_id = await manager.submit(brief="test", rubric="rubric", phase="research")
    assert isinstance(job_id, str) and len(job_id) == 12
    await manager.shutdown()


@pytest.mark.asyncio
async def test_job_completes(manager: JobManager) -> None:
    job_id = await manager.submit(brief="test", rubric="r", phase="p")
    await asyncio.sleep(0.1)
    await manager.wait(job_id, timeout=5.0)
    job = manager.store.get(job_id)
    assert job["status"] == JobStatus.COMPLETED
    assert job["result"]["verdict"] == "PASS"


@pytest.mark.asyncio
async def test_cancel_job(manager: JobManager) -> None:
    async def slow(prompt: str) -> dict:
        await asyncio.sleep(10)
        return {"verdict": "PASS"}

    manager._backend.review = slow
    job_id = await manager.submit(brief="test", rubric="r", phase="p")
    await asyncio.sleep(0.05)
    assert await manager.cancel(job_id) is True
    assert manager.store.get(job_id)["status"] == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_shutdown(manager: JobManager) -> None:
    async def slow(prompt: str) -> dict:
        await asyncio.sleep(10)
        return {"verdict": "PASS"}

    manager._backend.review = slow
    job_id = await manager.submit(brief="test", rubric="r", phase="p")
    await asyncio.sleep(0.05)
    await manager.shutdown()
    job = manager.store.get(job_id)
    assert job["status"] in (JobStatus.INTERRUPTED, JobStatus.CANCELLED)


@pytest.mark.asyncio
async def test_get_result_not_completed(manager: JobManager) -> None:
    async def slow(prompt: str) -> dict:
        await asyncio.sleep(10)
        return {"verdict": "PASS"}

    manager._backend.review = slow
    job_id = await manager.submit(brief="test", rubric="r", phase="p")
    result = manager.get_result(job_id)
    assert "error" in result
    await manager.shutdown()


@pytest.mark.asyncio
async def test_list_jobs(manager: JobManager) -> None:
    await manager.submit(brief="b1", rubric="r", phase="p")
    await manager.submit(brief="b2", rubric="r", phase="p")
    await asyncio.sleep(0.1)
    assert len(manager.list_jobs()) == 2
    await manager.shutdown()
