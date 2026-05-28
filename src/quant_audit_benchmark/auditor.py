# -*- coding: utf-8 -*-
"""Deterministic audit harness for quant research review cases."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


VALID_ISSUES = frozenset(
    {
        "lookahead",
        "normalization_leakage",
        "temporal_split",
        "missing_costs",
        "unsupported_claim",
    }
)


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
    """Raise a clear error if the required real-data/workflow fixture is missing."""

    if not path.exists():
        raise FileNotFoundError(
            f"Required real-data fixture is missing: {path}. "
            "This project intentionally does not generate fallback synthetic data."
        )

    if path.suffix == ".ipynb":
        _validate_notebook_fixture(path)
        return

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        first_row = next(reader, None)
    if first_row is None:
        raise ValueError(f"Real-data fixture is empty: {path}")

    schemas = [
        {"date", "market_cap_usd", "volume_usd", "close_usd", "source"},
        {
            "ticker",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
        },
        {"ticker", "exchange", "company_name"},
    ]
    columns = set(first_row)
    if not any(required.issubset(columns) for required in schemas):
        expected = sorted(set().union(*schemas))
        raise ValueError(
            f"Real-data fixture {path} has unsupported columns. "
            f"Expected one known schema containing columns like: {expected}"
        )


def _validate_notebook_fixture(path: Path) -> None:
    raw_notebook = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_notebook, dict):
        raise ValueError(f"Notebook fixture is malformed: {path}")
    cells = raw_notebook.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError(f"Notebook fixture is empty: {path}")
    has_source = any(
        isinstance(cell, dict) and cell.get("source") for cell in cells
    )
    if not has_source:
        raise ValueError(f"Notebook fixture has no cell source: {path}")


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
