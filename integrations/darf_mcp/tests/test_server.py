# -*- coding: utf-8 -*-
from server import MODULES


def test_all_modules_registered() -> None:
    names = [name for name, _, _ in MODULES]
    assert "challenger" in names
    assert "data" in names
    assert "lessons" in names
    assert "ops" in names
    assert "verify" in names
    assert "jobs" in names
