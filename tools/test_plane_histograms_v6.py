"""Golden cases of the shared sparse-counts grammar and of ``plane_histograms.csv`` version 6.

ADR 0008 is **proposed** (owner decision pending); these cases fix what it proposes. Run with
``python -I -m pytest tools``. A brick implementing version 6 (normalization's ``csv_io``) accepts
every file of ``tools/plane_histograms_v6/valid`` with the dense counts given here and refuses
every file of ``tools/plane_histograms_v6/invalid``; the reason labels are this checker's, and a
brick's test maps its own message to them.
"""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
FIXTURES = TOOLS / "plane_histograms_v6"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s = _load("sparse_counts")
v6 = _load("plane_histograms_v6")

INVALID = {
    "pi01_schema_version_5": "schema_version_refused",
    "pi02_v5_bin_columns_labelled_6": "header",
    "pi03_counts_space": "counts_syntax",
    "pi04_counts_trailing_separator": "counts_syntax",
    "pi05_counts_index_leading_zero": "counts_leading_zero",
    "pi06_counts_count_leading_zero": "counts_leading_zero",
    "pi07_counts_zero_count": "counts_zero",
    "pi08_counts_unordered": "counts_order",
    "pi09_counts_repeated_index": "counts_order",
    "pi10_counts_index_out_of_range": "counts_index_range",
    "pi11_counts_sum_mismatch": "counts_sum",
    "pi12_empty_with_pixels_in_bins": "counts_sum",
    "pi13_present_counts_blank": "counts_blank",
    "pi14_absent_channel_empty": "absent_has_value",
    "pi15_empty_upper_case": "counts_syntax",
    "pi16_counts_sign": "counts_syntax",
    "pi17_counts_non_ascii_digit": "counts_syntax",
    "pi18_bin_count_differs": "bin_count_differs",
    "pi19_counts_too_large": "counts_too_large",
    "pi20_counts_pair_without_count": "counts_syntax",
    "pi21_zero_for_absent_channel": "absent_has_value",
    "pi22_header_channels_unsorted": "header",
}


class Grammar(unittest.TestCase):
    def test_canonical_text(self) -> None:
        self.assertEqual(s.format_dense([0, 0, 0]), "empty")
        self.assertEqual(s.format_dense([4, 0, 2, 0, 0, 1]), "0:4;2:2;5:1")
        self.assertEqual(s.format_dense([0] * 255 + [7]), "255:7")

    def test_round_trip(self) -> None:
        for dense in ([0, 0], [1], [0, 3, 0, 9223372036854775807], [5, 0, 0, 0, 1]):
            self.assertEqual(s.to_dense(s.parse(s.format_dense(dense), len(dense)), len(dense)), dense)

    def test_refusals(self) -> None:
        cases = {
            "": "counts_blank", " empty": "counts_syntax", "Empty": "counts_syntax", "0": "counts_syntax",
            "0:1;": "counts_syntax", ";0:1": "counts_syntax", "0:1;;2:1": "counts_syntax", "0:1:2": "counts_syntax",
            "0 :1": "counts_syntax", "-1:1": "counts_syntax", "1:+1": "counts_syntax", "1.0:1": "counts_syntax",
            "0x1:1": "counts_syntax", "１:1": "counts_syntax", "01:1": "counts_leading_zero",
            "1:01": "counts_leading_zero", "1:0": "counts_zero", "1:00": "counts_leading_zero",
            "2:1;1:1": "counts_order", "1:1;1:1": "counts_order", "4:1": "counts_index_range",
            "0:9223372036854775808": "counts_too_large",
        }
        for cell, reason in cases.items():
            with self.subTest(cell=cell):
                with self.assertRaises(s.SparseCountsError) as caught:
                    s.parse(cell, 4)
                self.assertEqual(caught.exception.reason, reason)

    def test_sum_rule(self) -> None:
        s.check_sum(s.parse("0:2;3:6", 8), valid=10, underflow=1, overflow=1)
        s.check_sum(s.parse("empty", 8), valid=2, underflow=1, overflow=1)
        s.check_sum(s.parse("empty", 8), valid=0, underflow=0, overflow=0)
        with self.assertRaises(s.SparseCountsError) as caught:
            s.check_sum(s.parse("empty", 8), valid=1, underflow=0, overflow=0)
        self.assertEqual(caught.exception.reason, "counts_sum")


class Tables(unittest.TestCase):
    def test_every_valid_file_is_accepted(self) -> None:
        files = sorted((FIXTURES / "valid").glob("*.csv"))
        self.assertEqual(len(files), 4)
        for f in files:
            with self.subTest(file=f.name):
                v6.read_file(f)

    def test_dense_counts_of_the_valid_files(self) -> None:
        pv02 = v6.read_file(FIXTURES / "valid" / "pv02_absent_channel_blank.csv")
        ctrl = pv02["CTRL/rep1/img01.tif::z=0,t=0"]
        self.assertIsNone(ctrl["PHASE"])  # absent: blank, never a zero histogram
        self.assertEqual(ctrl["DNA"][:5], [3, 5, 2, 6, 0])
        self.assertEqual(len(ctrl["DNA"]), 256)
        pv03 = v6.read_file(FIXTURES / "valid" / "pv03_empty_and_tails_id_with_underscore.csv")
        plane = pv03["CTRL/rep1/img01.tif::z=0,t=0"]
        self.assertEqual(plane["DNA"], [0] * 8)  # measured, no finite pixel: `empty`
        self.assertEqual(plane["PAX_488"], [2, 0, 0, 6, 3, 0, 1, 2])  # 16 valid - 1 - 1
        pv04 = v6.read_file(FIXTURES / "valid" / "pv04_last_bin_index.csv")
        dense = pv04["CTRL/rep1/img02.tif::z=0,t=0"]["DNA"]
        self.assertEqual((dense[0], dense[255], sum(dense)), (14, 2, 16))

    def test_every_invalid_file_is_refused_with_its_reason(self) -> None:
        names = sorted(f.stem for f in (FIXTURES / "invalid").glob("*.csv"))
        self.assertEqual(names, sorted(INVALID))
        for name, reason in INVALID.items():
            with self.subTest(file=name):
                with self.assertRaises(v6.PlaneHistogramsError) as caught:
                    v6.read_file(FIXTURES / "invalid" / f"{name}.csv")
                self.assertEqual(caught.exception.reason, reason, str(caught.exception))

    def test_header_width(self) -> None:
        # 15 plane columns + `channels`, then 11 features + the counts cell per channel ID.
        for n in (1, 2, 3, 7):
            self.assertEqual(len(v6.table_header([f"C{i}" for i in range(n)])), 16 + 12 * n)

    def test_catalogue_lists_every_file(self) -> None:
        catalogue = (FIXTURES / "README.md").read_text(encoding="utf-8")
        for f in sorted(FIXTURES.glob("*/*.csv")):
            self.assertIn(f"`{f.stem}`", catalogue, f.name)
        for name, reason in INVALID.items():
            self.assertRegex(catalogue, rf"`{name}`[^\n]*`{reason}`")


class OneDefinition(unittest.TestCase):
    def test_the_grammar_is_defined_once(self) -> None:
        defining = re.compile(r"index:count[^\n]*joined by `;`")
        where = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "docs").rglob("*.md"))
                 if defining.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(where, ["docs/sparse-counts.md"])


if __name__ == "__main__":
    unittest.main()
