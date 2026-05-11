# -*- coding: utf-8 -*-
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Temporary SQLite DB path for testing."""
    return tmp_path / "test.db"


@pytest.fixture
def tmp_jobs_dir(tmp_path: Path) -> Path:
    """Temporary jobs directory for testing."""
    d = tmp_path / "jobs"
    d.mkdir()
    return d
