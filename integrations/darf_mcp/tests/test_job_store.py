# -*- coding: utf-8 -*-
from pathlib import Path

from jobs.store import JobStore, JobStatus


def test_create_and_get(tmp_jobs_dir: Path) -> None:
    store = JobStore(tmp_jobs_dir)
    job_id = store.create(brief="test", rubric="rubric", phase="research")
    job = store.get(job_id)
    assert job is not None
    assert job["status"] == JobStatus.PENDING
    assert job["brief"] == "test"


def test_update_status(tmp_jobs_dir: Path) -> None:
    store = JobStore(tmp_jobs_dir)
    job_id = store.create(brief="b", rubric="r", phase="p")
    store.update(job_id, status=JobStatus.RUNNING)
    assert store.get(job_id)["status"] == JobStatus.RUNNING


def test_set_result(tmp_jobs_dir: Path) -> None:
    store = JobStore(tmp_jobs_dir)
    job_id = store.create(brief="b", rubric="r", phase="p")
    store.update(job_id, status=JobStatus.COMPLETED, result={"verdict": "PASS"})
    job = store.get(job_id)
    assert job["result"]["verdict"] == "PASS"


def test_list_jobs(tmp_jobs_dir: Path) -> None:
    store = JobStore(tmp_jobs_dir)
    store.create(brief="b1", rubric="r", phase="p")
    store.create(brief="b2", rubric="r", phase="p")
    assert len(store.list_all()) == 2


def test_mark_interrupted(tmp_jobs_dir: Path) -> None:
    store = JobStore(tmp_jobs_dir)
    j1 = store.create(brief="b", rubric="r", phase="p")
    store.update(j1, status=JobStatus.RUNNING)
    store.mark_running_as_interrupted()
    assert store.get(j1)["status"] == JobStatus.INTERRUPTED


def test_get_nonexistent(tmp_jobs_dir: Path) -> None:
    assert JobStore(tmp_jobs_dir).get("nonexistent") is None
