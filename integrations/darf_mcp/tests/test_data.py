# -*- coding: utf-8 -*-
import csv

from pathlib import Path
from data import _validate_lookahead, _check_split, _read_csv


class TestValidateLookahead:
    def test_valid_shift_no_overlap(self, tmp_path: Path) -> None:
        feat = tmp_path / "feat.csv"
        label = tmp_path / "label.csv"
        feat.write_text("date,val\n2024-01-01,1\n2024-01-02,2\n2024-01-03,3\n")
        label.write_text("date,val\n2024-01-02,1\n2024-01-03,2\n2024-01-04,3\n")
        result = _validate_lookahead(
            {
                "feature_file": str(feat),
                "label_file": str(label),
                "date_col": "date",
                "shift": 1,
            }
        )
        assert result["clean"] is True

    def test_detects_overlap(self, tmp_path: Path) -> None:
        feat = tmp_path / "feat.csv"
        label = tmp_path / "label.csv"
        feat.write_text("date,val\n2024-01-01,1\n2024-01-02,2\n2024-01-03,3\n")
        label.write_text("date,val\n2024-01-01,1\n2024-01-02,2\n2024-01-03,3\n")
        result = _validate_lookahead(
            {
                "feature_file": str(feat),
                "label_file": str(label),
                "date_col": "date",
                "shift": 1,
            }
        )
        assert result["clean"] is False

    def test_row_count_mismatch(self, tmp_path: Path) -> None:
        feat = tmp_path / "feat.csv"
        label = tmp_path / "label.csv"
        feat.write_text("date,val\n2024-01-01,1\n2024-01-02,2\n")
        label.write_text("date,val\n2024-01-01,1\n")
        result = _validate_lookahead(
            {
                "feature_file": str(feat),
                "label_file": str(label),
                "date_col": "date",
                "shift": 1,
            }
        )
        assert result["clean"] is False


class TestReadCsv:
    def test_tab_in_csv_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "data.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["date", "value"])
            w.writerow(["2024-01-01", "42"])
        rows, delim = _read_csv(str(p))
        assert delim == "\t"
        assert rows[0]["value"] == "42"

    def test_comma_csv(self, tmp_path: Path) -> None:
        p = tmp_path / "data.csv"
        p.write_text("date,value\n2024-01-01,42\n")
        rows, delim = _read_csv(str(p))
        assert delim == ","
        assert rows[0]["value"] == "42"

    def test_tsv_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "data.tsv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["a", "b"])
            w.writerow(["1", "2"])
        rows, delim = _read_csv(str(p))
        assert delim == "\t"


class TestCheckSplit:
    def test_valid(self) -> None:
        r = _check_split(
            {
                "train_end": "2024-01-31",
                "val_start": "2024-02-01",
                "val_end": "2024-03-31",
                "test_start": "2024-04-01",
            }
        )
        assert r["valid"] is True

    def test_overlap(self) -> None:
        r = _check_split(
            {
                "train_end": "2024-02-15",
                "val_start": "2024-02-01",
                "val_end": "2024-03-31",
                "test_start": "2024-04-01",
            }
        )
        assert r["valid"] is False
