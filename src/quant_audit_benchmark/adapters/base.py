# -*- coding: utf-8 -*-
"""Shared adapter interfaces for benchmark reviewers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..auditor import AuditCase, AuditFinding


@dataclass(frozen=True)
class ReviewResult:
    """Normalized review output from one adapter on one benchmark case."""

    reviewer: str
    findings: tuple[AuditFinding, ...]
    raw_output: dict[str, Any]


class ReviewerAdapter(Protocol):
    """A runnable reviewer adapter used by the benchmark runner."""

    name: str

    def review(self, case: AuditCase) -> ReviewResult:
        """Review one benchmark case and return normalized findings."""
        ...
