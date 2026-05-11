# -*- coding: utf-8 -*-
import pytest
from pathlib import Path

from _async_io import async_read_text, async_write_text


@pytest.mark.asyncio
async def test_read_write_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "test.txt"
    await async_write_text(p, "hello world")
    content = await async_read_text(p)
    assert content == "hello world"


@pytest.mark.asyncio
async def test_read_nonexistent(tmp_path: Path) -> None:
    p = tmp_path / "nope.txt"
    with pytest.raises(FileNotFoundError):
        await async_read_text(p)
