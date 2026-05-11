# -*- coding: utf-8 -*-
"""Tests for verify module -- _check_exists, _check_substantive, _check_wired."""

import pytest
from pathlib import Path

from verify import (
    _check_exists,
    _check_substantive,
    _check_wired,
    _workspace_import_cache,
)


@pytest.fixture(autouse=True)
def clear_workspace_cache():
    """Clear the workspace import cache between tests."""
    _workspace_import_cache.clear()
    yield
    _workspace_import_cache.clear()


class TestCheckExists:
    def test_exists(self, tmp_path: Path) -> None:
        p = tmp_path / "test.py"
        p.write_text("x = 1\n")
        assert _check_exists(p)["status"] == "PASS"

    def test_not_exists(self, tmp_path: Path) -> None:
        assert _check_exists(tmp_path / "nope.py")["status"] == "FAIL"


class TestCheckSubstantive:
    def test_real_code(self, tmp_path: Path) -> None:
        p = tmp_path / "real.py"
        p.write_text(
            "def foo():\n"
            "    x = 1\n"
            "    y = 2\n"
            "    z = 3\n"
            "    return x + y + z\n"
            "    w = 4\n"
        )
        assert _check_substantive(p)["status"] == "PASS"

    def test_stub_only(self, tmp_path: Path) -> None:
        p = tmp_path / "stub.py"
        p.write_text("def foo():\n    pass\n")
        result = _check_substantive(p)
        assert result["status"] == "FAIL"


class TestCheckWired:
    def test_imported_file(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("from b import x\n")
        (tmp_path / "b.py").write_text("x = 1\n")
        assert _check_wired(tmp_path / "b.py", tmp_path)["status"] == "PASS"

    def test_not_imported(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1\n")
        assert _check_wired(tmp_path / "a.py", tmp_path)["status"] == "FAIL"

    def test_main_guard(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text('if __name__ == "__main__": pass\n')
        assert _check_wired(tmp_path / "a.py", tmp_path)["status"] == "PASS"

    def test_caching(self, tmp_path: Path) -> None:
        """Second call for same workspace should use cache."""
        (tmp_path / "a.py").write_text("from b import x\n")
        (tmp_path / "b.py").write_text("x = 1\n")
        (tmp_path / "c.py").write_text("y = 2\n")
        _check_wired(tmp_path / "b.py", tmp_path)  # builds cache
        assert tmp_path in _workspace_import_cache
        # c is not imported
        assert _check_wired(tmp_path / "c.py", tmp_path)["status"] == "FAIL"
