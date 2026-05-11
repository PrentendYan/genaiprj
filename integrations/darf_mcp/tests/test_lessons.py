# -*- coding: utf-8 -*-
import pytest
from pathlib import Path

from persistence.db import SqliteStore
from lessons.db import LessonDB


@pytest.fixture
def lesson_db(tmp_db: Path) -> LessonDB:
    store = SqliteStore(tmp_db)
    store.initialize()
    return LessonDB(store)


def test_add_and_search(lesson_db: LessonDB) -> None:
    r = lesson_db.add(
        title="lookahead",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    assert "id" in r
    assert len(lesson_db.search("lookahead")) == 1


def test_duplicate_ignored(lesson_db: LessonDB) -> None:
    lesson_db.add(
        title="dup",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    r = lesson_db.add(
        title="dup",
        domain="quant_method",
        trigger="t2",
        correct="c2",
        wrong="w2",
    )
    assert r.get("duplicate") is True
    assert len(lesson_db.search("dup")) == 1


def test_bump(lesson_db: LessonDB) -> None:
    r = lesson_db.add(
        title="test",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    lesson_db.bump(r["id"])
    assert lesson_db.search("test")[0]["frequency"] == 2


def test_top_violations(lesson_db: LessonDB) -> None:
    lesson_db.add(
        title="a",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    lesson_db.add(
        title="b",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    # bump "a" to frequency 2
    found = lesson_db.search("a")
    if found:
        lesson_db.bump(found[0]["id"])
    top = lesson_db.top_violations(n=1)
    assert top[0]["title"] == "a"


def test_top_violations_with_domain(lesson_db: LessonDB) -> None:
    lesson_db.add(
        title="x",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    lesson_db.add(
        title="y",
        domain="darf_flow",
        trigger="t",
        correct="c",
        wrong="w",
    )
    top = lesson_db.top_violations(n=10, domain="darf_flow")
    assert len(top) == 1
    assert top[0]["title"] == "y"


def test_search_with_domain(lesson_db: LessonDB) -> None:
    lesson_db.add(
        title="alpha",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    lesson_db.add(
        title="alpha_flow",
        domain="darf_flow",
        trigger="t",
        correct="c",
        wrong="w",
    )
    results = lesson_db.search("alpha", domain="quant_method")
    assert len(results) == 1
    assert results[0]["domain"] == "quant_method"


def test_get_syncable(lesson_db: LessonDB) -> None:
    r = lesson_db.add(
        title="sync_me",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    # bump to frequency 3
    for _ in range(2):
        lesson_db.bump(r["id"])
    syncable = lesson_db.get_syncable(min_frequency=3)
    assert len(syncable) == 1
    assert syncable[0]["title"] == "sync_me"


def test_get_syncable_excludes_low_frequency(lesson_db: LessonDB) -> None:
    lesson_db.add(
        title="low_freq",
        domain="quant_method",
        trigger="t",
        correct="c",
        wrong="w",
    )
    syncable = lesson_db.get_syncable(min_frequency=3)
    assert len(syncable) == 0


def test_bump_nonexistent(lesson_db: LessonDB) -> None:
    result = lesson_db.bump(99999)
    assert result.get("error") == "not found"
