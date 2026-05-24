# -*- coding: utf-8 -*-
"""Deterministic audit harness for quant research review cases."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ISSUE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "lookahead": [
        re.compile(r"shift\s*\(\s*-\s*\d+", re.IGNORECASE),
        re.compile(r"future_return|future_ret|next_return", re.IGNORECASE),
    ],
    "normalization_leakage": [
        re.compile(r"\.\s*(mean|std|min|max)\s*\(\s*\)", re.IGNORECASE),
        re.compile(r"StandardScaler\s*\(\s*\)\.fit_transform", re.IGNORECASE),
    ],
    "temporal_split": [
        re.compile(r"train_test_split", re.IGNORECASE),
        re.compile(r"shuffle\s*=\s*True", re.IGNORECASE),
    ],
    "missing_costs": [
        re.compile(r"strategy_return", re.IGNORECASE),
        re.compile(r"sharpe", re.IGNORECASE),
    ],
    "unsupported_claim": [
        re.compile(r"state-of-the-art|beats all|clearly .*outperform", re.IGNORECASE),
        re.compile(r"omit baseline|without baseline|no baseline", re.IGNORECASE),
    ],
}

VALID_ISSUES = frozenset(ISSUE_PATTERNS)
COST_TERMS = re.compile(r"cost|fee|slippage|commission|turnover", re.IGNORECASE)

PROFILE_THRESHOLDS = {
    "single_llm_baseline": {"drop_minor": True, "require_two_patterns": True},
    "darf_cross_model": {"drop_minor": False, "require_two_patterns": False},
    "corax_santa_sentinel": {"drop_minor": False, "require_two_patterns": False},
}


@dataclass(frozen=True)
class AuditFinding:
    """One detected audit issue."""

    issue: str
    severity: str
    evidence: str


@dataclass(frozen=True)
class AuditCase:
    """A labeled benchmark case."""

    case_id: str
    title: str
    source_type: str
    code: str
    expected_issues: frozenset[str]
    severity: str
    rationale: str
    data_fixture: Path


def load_cases(
    path: str | Path,
    root: str | Path | None = None,
    annotations_path: str | Path | None = None,
) -> list[AuditCase]:
    """Load benchmark cases and validate referenced data fixtures."""

    case_path = Path(path)
    base = Path(root) if root is not None else case_path.parent.parent
    raw_cases = json.loads(case_path.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        raise ValueError(f"Benchmark cases must be a JSON list: {case_path}")
    annotations = _load_annotations(case_path, annotations_path)
    cases: list[AuditCase] = []
    seen_case_ids: set[str] = set()

    for item in raw_cases:
        if not isinstance(item, dict):
            raise ValueError(f"Each benchmark case must be an object: {case_path}")
        case_id = _required_str(item, "id", "case")
        if case_id in seen_case_ids:
            raise ValueError(f"Duplicate benchmark case id: {case_id}")
        seen_case_ids.add(case_id)

        fixture = base / _required_str(item, "data_fixture", case_id)
        validate_real_data_fixture(fixture)
        if annotations is None:
            expected_issues = _issue_set(item.get("expected_issues"), case_id)
            severity = _required_str(item, "severity", case_id)
            rationale = str(item.get("rationale", "Inline benchmark annotation."))
        else:
            if case_id not in annotations:
                raise ValueError(f"Missing annotation for benchmark case: {case_id}")
            annotation = annotations[case_id]
            expected_issues = annotation["expected_issues"]
            severity = annotation["severity"]
            rationale = annotation["rationale"]
        cases.append(
            AuditCase(
                case_id=case_id,
                title=_required_str(item, "title", case_id),
                source_type=_required_str(item, "source_type", case_id),
                code=_required_str(item, "code", case_id),
                expected_issues=frozenset(expected_issues),
                severity=severity,
                rationale=rationale,
                data_fixture=fixture,
            )
        )

    if annotations is not None:
        unknown_annotations = sorted(set(annotations).difference(seen_case_ids))
        if unknown_annotations:
            raise ValueError(f"Annotations reference unknown case ids: {unknown_annotations}")
    return cases


def validate_real_data_fixture(path: Path) -> None:
    """Raise a clear error if the required real-data fixture is missing."""

    if not path.exists():
        raise FileNotFoundError(
            f"Required real-data fixture is missing: {path}. "
            "This project intentionally does not generate fallback synthetic data."
        )

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Real-data fixture is empty: {path}")
    required = {"date", "market_cap_usd", "volume_usd", "close_usd", "source"}
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"Real-data fixture {path} is missing columns: {sorted(missing)}")


def _load_annotations(
    case_path: Path, annotations_path: str | Path | None
) -> dict[str, dict[str, object]] | None:
    if annotations_path is None:
        candidate = case_path.with_name("annotations.json")
        if not candidate.exists():
            return None
        annotation_path = candidate
    else:
        annotation_path = Path(annotations_path)

    raw_annotations = json.loads(annotation_path.read_text(encoding="utf-8"))
    if not isinstance(raw_annotations, list):
        raise ValueError(f"Benchmark annotations must be a JSON list: {annotation_path}")

    annotations: dict[str, dict[str, object]] = {}
    for item in raw_annotations:
        if not isinstance(item, dict):
            raise ValueError(f"Each annotation must be an object: {annotation_path}")
        case_id = _required_str(item, "case_id", "annotation")
        if case_id in annotations:
            raise ValueError(f"Duplicate annotation for benchmark case: {case_id}")
        annotations[case_id] = {
            "expected_issues": _issue_set(item.get("expected_issues"), case_id),
            "severity": _required_str(item, "severity", case_id),
            "rationale": _required_str(item, "rationale", case_id),
        }
    return annotations


def _required_str(item: dict[str, object], field: str, context: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid {field!r} for {context}.")
    return value


def _issue_set(value: object, context: str) -> frozenset[str]:
    if not isinstance(value, list):
        raise ValueError(f"Missing or invalid expected_issues for {context}.")
    issues: set[str] = set()
    for issue in value:
        if not isinstance(issue, str):
            raise ValueError(f"Invalid issue value for {context}: {issue!r}")
        if issue not in VALID_ISSUES:
            raise ValueError(f"Unknown issue type for {context}: {issue}")
        issues.add(issue)
    return frozenset(issues)


def audit_case(case: AuditCase, profile: str) -> list[AuditFinding]:
    """Audit one case under a named review profile."""

    if profile not in PROFILE_THRESHOLDS:
        raise ValueError(f"Unknown profile: {profile}")

    settings = PROFILE_THRESHOLDS[profile]
    findings: list[AuditFinding] = []

    for issue, patterns in ISSUE_PATTERNS.items():
        matches = [pattern.pattern for pattern in patterns if pattern.search(case.code)]
        if issue == "normalization_leakage" and not _looks_like_global_normalization(
            case.code
        ):
            matches = []
        if issue == "missing_costs" and COST_TERMS.search(case.code):
            matches = []
        if settings["require_two_patterns"] and len(matches) < 2:
            continue
        if settings["drop_minor"] and case.severity == "minor":
            continue
        if matches:
            findings.append(
                AuditFinding(
                    issue=issue,
                    severity=_severity_for(issue),
                    evidence="; ".join(matches),
                )
            )

    if profile == "corax_santa_sentinel":
        findings = _sentinel_pass(case, findings)

    return findings


def evaluate(cases: Iterable[AuditCase], profile: str) -> dict[str, object]:
    """Evaluate a profile against labeled cases."""

    true_positive = false_positive = false_negative = 0
    per_case: list[dict[str, object]] = []

    for case in cases:
        findings = audit_case(case, profile)
        predicted = {finding.issue for finding in findings}
        expected = set(case.expected_issues)

        true_positive += len(predicted.intersection(expected))
        false_positive += len(predicted.difference(expected))
        false_negative += len(expected.difference(predicted))

        per_case.append(
            {
                "case_id": case.case_id,
                "expected": sorted(expected),
                "predicted": sorted(predicted),
                "findings": [finding.__dict__ for finding in findings],
            }
        )

    precision = _safe_div(true_positive, true_positive + false_positive)
    recall = _safe_div(true_positive, true_positive + false_negative)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    return {
        "profile": profile,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "per_case": per_case,
    }


def _sentinel_pass(case: AuditCase, findings: list[AuditFinding]) -> list[AuditFinding]:
    """Add a narrow meta-review pass for claims without evidence."""

    predicted = {finding.issue for finding in findings}
    if "unsupported_claim" not in predicted and re.search(
        r"visually compelling|clearly|state-of-the-art", case.code, re.IGNORECASE
    ):
        findings.append(
            AuditFinding(
                issue="unsupported_claim",
                severity="minor",
                evidence="Sentinel detected performance language without evidence.",
            )
        )
    return findings


def _looks_like_global_normalization(code: str) -> bool:
    """Reduce false positives from Sharpe ratios or rolling-window statistics."""

    has_scaler = re.search(r"StandardScaler|MinMaxScaler|RobustScaler", code, re.IGNORECASE)
    has_zscore_name = re.search(r"\bz_|zscore|standardized|normalized", code, re.IGNORECASE)
    has_global_stats = re.search(r"\.\s*(mean|std|min|max)\s*\(\s*\)", code, re.IGNORECASE)
    has_rolling_context = re.search(r"\.rolling\s*\(", code, re.IGNORECASE)
    return bool(has_scaler or (has_zscore_name and has_global_stats and not has_rolling_context))


def _severity_for(issue: str) -> str:
    if issue in {"lookahead", "temporal_split"}:
        return "critical"
    if issue in {"normalization_leakage", "missing_costs"}:
        return "major"
    return "minor"


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
