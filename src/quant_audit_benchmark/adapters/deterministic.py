# -*- coding: utf-8 -*-
"""Deterministic adapter used as the simple baseline."""

from __future__ import annotations

from ..auditor import AuditCase, audit_case
from .base import ReviewResult


class DeterministicAdapter:
    """Wrap an existing deterministic profile behind the adapter interface."""

    def __init__(self, name: str, profile: str | None = None) -> None:
        self.name = name
        self.profile = profile or name

    def review(self, case: AuditCase) -> ReviewResult:
        findings = tuple(audit_case(case, self.profile))
        return ReviewResult(
            reviewer=self.name,
            findings=findings,
            raw_output={
                "mode": "deterministic_rules",
                "profile": self.profile,
                "case_id": case.case_id,
            },
        )
