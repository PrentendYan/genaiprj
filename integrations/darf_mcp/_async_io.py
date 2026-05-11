# -*- coding: utf-8 -*-
"""Async file I/O utilities wrapping aiofiles."""

from pathlib import Path

import aiofiles


async def async_read_text(path: Path, encoding: str = "utf-8") -> str:
    """Read entire file as text, async."""
    async with aiofiles.open(path, mode="r", encoding=encoding) as f:
        return await f.read()


async def async_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text to file, async. Creates parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, mode="w", encoding=encoding) as f:
        await f.write(content)
