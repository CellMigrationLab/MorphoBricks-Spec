"""Golden cases of ``plane_histograms.parquet``, schema version 6 (ADR 0008, accepted 19 November 2026).

ADR 0008 was accepted on 19 November 2026; these cases fix its format. Run with
``python -I -m pytest tools`` after ``pip install -r tools/requirements.txt`` (``pyarrow``; without
it this module fails to import, it is never skipped). A brick implementing version 6
(normalization's reader) accepts every file of ``tools/plane_histograms_v6/valid`` with the dense
counts and content digests given here and refuses every file of ``tools/plane_histograms_v6/invalid``;
the reason labels are this checker's, and a brick's test maps its own message to them.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

import pyarrow.parquet as pq

TOOLS = Path(__file__).resolve().parent
FIXTURES = TOOLS / "plane_histograms_v6"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v6 = _load("plane_histograms_v6", TOOLS / "plane_histograms_v6.py")
mt = _load("make_tables", FIXTURES / "make_tables.py")

INVALID = {
    "pi01_schema_version_5": "schema_version_refused",
    "pi02_sparse_csv_labelled_6": "not_parquet",
    "pi03_parquet_schema_version_5": "schema_version_refused",
    "pi04_schema_version_7": "schema_version_unknown",
    "pi05_channel_blocks_unsorted": "header",
    "pi06_bins_int64": "column_type",
    "pi07_bins_unordered": "bins_order",
    "pi08_bins_repeated": "bins_order",
    "pi09_bin_index_equals_bin_count": "bins_range",
    "pi10_bin_index_negative": "bins_range",
    "pi11_zero_count": "counts_not_positive",
    "pi12_negative_count": "counts_not_positive",
    "pi13_lists_length_differ": "lists_length",
    "pi14_counts_sum_mismatch": "counts_sum",
    "pi15_empty_lists_with_pixels": "counts_sum",
    "pi16_listed_channel_lists_null": "present_null",
    "pi17_absent_channel_empty_lists": "absent_has_value",
    "pi18_absent_channel_valid_zero": "absent_has_value",
    "pi19_bin_count_differs": "bin_count_differs",
    "pi20_null_in_counts": "null_element",
    "pi21_channel_count_mismatch": "channels_cell",
    "pi22_duplicate_plane": "duplicate_plane",
    "pi23_tail_mean_negative_zero": "float_value",
    "pi24_truncated_file": "not_parquet",
    "pi25_plane_column_null": "plane_value",
    "pi26_bin_count_above_dtype_range": "bin_count_range",
    "pi27_valid_above_total": "pixel_counts",
    "pi28_no_valid_pixel_with_limit": "limits",
    "pi29_limits_unordered": "limits",
    "pi30_limit_text_not_canonical": "limit_text",
    "pi31_tail_mean_out_of_range": "tail_moments",
    "pi32_bit_depth_not_dtype": "dtype",
    "pi33_plane_id_not_path_z_t": "plane_id",
    "pi34_negative_z": "plane_value",
    "pi35_image_channels_differ": "image_channels",
    "pi36_channel_id_not_token": "channel_id",
}
#: Refused before any row is read (file, version, header, types): no single-rule audit applies.
FILE_LEVEL = {"pi01_schema_version_5", "pi02_sparse_csv_labelled_6", "pi03_parquet_schema_version_5",
              "pi05_channel_blocks_unsorted", "pi06_bins_int64", "pi24_truncated_file"}


def _catalogue() -> str:
    return (FIXTURES / "README.md").read_text(encoding="utf-8")


def _valid(name: str) -> Path:
    return FIXTURES / "valid" / f"{name}.parquet"


class Tables(unittest.TestCase):
    def test_every_valid_file_is_accepted(self) -> None:
        files = sorted((FIXTURES / "valid").glob("*"))
        self.assertEqual([f.suffix for f in files], [".parquet"] * 6)
        for f in files:
            with self.subTest(file=f.name):
                v6.read_table(f)

    def test_dense_counts_of_the_valid_files(self) -> None:
        pv02 = v6.dense_counts(v6.read_table(_valid("pv02_absent_channel_null")))
        ctrl = pv02["CTRL/rep1/img01.tif::z=0,t=0"]
        self.assertIsNone(ctrl["PHASE"])  # absent: null, never an empty or zero histogram
        self.assertEqual(ctrl["DNA"][:5], [3, 5, 2, 6, 0])
        self.assertEqual(len(ctrl["DNA"]), 256)
        pv03 = v6.dense_counts(v6.read_table(_valid("pv03_measured_empty_and_tails_id_with_underscore")))
        plane = pv03["CTRL/rep1/img01.tif::z=0,t=0"]
        self.assertEqual(plane["DNA"], [0] * 8)  # measured, no finite pixel: two empty lists
        self.assertEqual(plane["PAX_488"], [2, 0, 0, 6, 3, 0, 1, 2])  # 16 valid - 1 - 1
        pv04 = v6.dense_counts(v6.read_table(_valid("pv04_last_bin_index")))
        dense = pv04["CTRL/rep1/img02.tif::z=0,t=0"]["DNA"]
        self.assertEqual((dense[0], dense[255], sum(dense)), (14, 2, 16))
        pv05 = v6.dense_counts(v6.read_table(_valid("pv05_full_range_uint16")))
        for cid, dense in pv05["CTRL/rep1/img03.tif::z=0,t=0"].items():
            with self.subTest(channel=cid):
                self.assertEqual((len(dense), sum(dense), dense[0] > 0, dense[65535]), (65536, 4096, True, 12))

    def test_every_invalid_file_is_refused_with_its_reason(self) -> None:
        names = sorted(f.stem for f in (FIXTURES / "invalid").glob("*.*"))
        self.assertEqual(names, sorted(INVALID))
        for name, reason in INVALID.items():
            path = next((FIXTURES / "invalid").glob(f"{name}.*"))
            with self.subTest(file=path.name):
                with self.assertRaises(v6.PlaneHistogramsError) as caught:
                    v6.read_table(path)
                self.assertEqual(caught.exception.reason, reason, str(caught.exception))

    def test_each_invalid_table_breaks_exactly_one_rule(self) -> None:
        """B4 audit: with its own rule skipped, every row-level invalid table passes every other
        check, so it breaks that one rule and no other."""
        for name, reason in INVALID.items():
            if name in FILE_LEVEL:
                continue
            with self.subTest(file=name):
                table = pq.read_table(FIXTURES / "invalid" / f"{name}.parquet")
                v6.check_table(table, skip=frozenset({reason}))

    def test_version_5_csv_is_read_by_its_prefix_only(self) -> None:
        """PQ7: the header and first row decide; bytes after them are never decoded."""
        data = (FIXTURES / "invalid" / "pi01_schema_version_5.csv").read_bytes()
        lines = data.split(b"\n")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plane_histograms.csv"
            path.write_bytes(b"\n".join(lines[:2]) + b"\n" + b"\xff\xfe not UTF-8 \xff\n" * 3)
            with self.assertRaises(v6.PlaneHistogramsError) as caught:
                v6.read_table(path)
        self.assertEqual(caught.exception.reason, "schema_version_refused")

    def test_limit_text_is_the_v5_writers_only(self) -> None:
        for text, dtype in (("100", "uint8"), ("-5", "int16"), ("0", "uint8"), ("0.0", "float32"),
                            ("89.11814880371094", "float32"), ("-1000.0", "float64"), ("1e-05", "float64")):
            with self.subTest(text=text, dtype=dtype):
                v6.parse_limit(text, dtype)
        for text, dtype in (("0100", "uint8"), ("+5", "uint8"), ("-0", "int16"), ("256", "uint8"),
                            ("-1", "uint8"), ("5.0", "uint8"), (" 5", "uint8"), ("-0.0", "float32"),
                            ("0.10", "float64"), ("1E-05", "float64"), ("100", "float64")):
            with self.subTest(text=text, dtype=dtype), self.assertRaises(v6.PlaneHistogramsError) as caught:
                v6.parse_limit(text, dtype)
            self.assertEqual(caught.exception.reason, "limit_text")

    def test_bin_count_range_follows_the_dtype(self) -> None:
        self.assertEqual(v6._bin_count_range("uint8"), (1, 256))
        self.assertEqual(v6._bin_count_range("uint16"), (1, 65536))
        self.assertEqual(v6._bin_count_range("int64"), (1, 65536))
        self.assertEqual(v6._bin_count_range("float32"), (2, 65536))
        ids, rows = mt.pv03_rows()  # float32, bin_count 8; 1 is below the float minimum
        for meta, _ in rows:
            meta["bin_count"] = 1
        with self.assertRaises(v6.PlaneHistogramsError) as caught:
            v6.check_table(mt.build(ids, rows))
        self.assertEqual(caught.exception.reason, "bin_count_range")

    def test_import_does_not_load_pyarrow(self) -> None:
        """PQ8: pyarrow is imported when a table is read, never at import."""
        import subprocess
        code = ("import importlib.util, sys; s = importlib.util.spec_from_file_location('v6', sys.argv[1]); "
                "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); print('pyarrow' in sys.modules)")
        done = subprocess.run([sys.executable, "-I", "-c", code, str(TOOLS / "plane_histograms_v6.py")],
                              capture_output=True, text=True, check=True)
        self.assertEqual(done.stdout.strip(), "False")

    def test_version_5_is_refused_with_the_fix(self) -> None:
        with self.assertRaises(v6.PlaneHistogramsError) as caught:
            v6.read_table(FIXTURES / "invalid" / "pi01_schema_version_5.csv")
        self.assertIn("version 6", str(caught.exception))
        self.assertIn("recompute the table with the preprocessing brick", str(caught.exception))

    def test_column_count(self) -> None:
        # 15 plane columns + `channels`, then 11 features + 2 lists per channel ID.
        for n in (1, 2, 3, 7):
            self.assertEqual(len(v6.table_columns([f"C{i}" for i in range(n)])), 16 + 13 * n)

    def test_catalogue_lists_every_file(self) -> None:
        catalogue = _catalogue()
        for f in sorted([*FIXTURES.glob("valid/*"), *FIXTURES.glob("invalid/*")]):
            self.assertIn(f"`{f.stem}`", catalogue, f.name)
        for name, reason in INVALID.items():
            self.assertRegex(catalogue, rf"`{name}`[^\n]*`{reason}`")

    def test_the_generator_wrote_the_committed_tables(self) -> None:
        for name, rows_of in mt.VALID.items():
            with self.subTest(file=name):
                self.assertEqual(v6.content_sha256(mt.build(*rows_of())), v6.content_sha256(v6.read_table(_valid(name))))


class ContentDigest(unittest.TestCase):
    """PQ6: the identity of a table is the digest of its decoded content, not its bytes."""

    def test_digests_of_the_catalogue(self) -> None:
        listed = dict(re.findall(r"`(pv\d\d_[a-z0-9_]+)`[^\n]*`([0-9a-f]{64})`", _catalogue()))
        self.assertEqual(sorted(listed), sorted(f.stem for f in (FIXTURES / "valid").glob("*.parquet")))
        for name, digest in listed.items():
            with self.subTest(file=name):
                self.assertEqual(v6.content_sha256(v6.read_table(_valid(name))), digest)

    def test_other_writer_settings_other_bytes_same_digest(self) -> None:
        pv01, pv06 = _valid("pv01_two_channels_uint8"), _valid("pv06_pv01_other_writer_settings")
        self.assertNotEqual(v6.file_sha256(pv01), v6.file_sha256(pv06))
        self.assertEqual(v6.content_sha256(v6.read_table(pv01)), v6.content_sha256(v6.read_table(pv06)))

    def test_digest_ignores_every_writer_setting(self) -> None:
        table = mt.build(*mt.pv02_rows())
        profiles = [
            mt.PROFILE, mt.OTHER_PROFILE,
            {"compression": "snappy"}, {"compression": "gzip", "use_dictionary": False},
            {"compression": "zstd", "compression_level": 19, "data_page_size": 64, "row_group_size": 1},
        ]
        digests, sizes = set(), set()
        with tempfile.TemporaryDirectory() as folder:
            for k, profile in enumerate(profiles):
                path = Path(folder) / f"{k}.parquet"
                profile = dict(profile)
                pq.write_table(table, path, row_group_size=profile.pop("row_group_size", None), **profile)
                digests.add(v6.content_sha256(v6.read_table(path)))
                sizes.add(v6.file_sha256(path))
        self.assertEqual(len(digests), 1)
        self.assertEqual(len(sizes), len(profiles))

    def test_digest_changes_with_the_content(self) -> None:
        base = v6.content_sha256(mt.build(*mt.pv01_rows()))
        ids, rows = mt.pv01_rows()
        mt._lists(0, "DNA", [0, 1, 2, 3], [4, 5, 4, 3])(ids, rows)  # one pixel moved to the next bin
        self.assertNotEqual(v6.content_sha256(mt.build(ids, rows)), base)
        ids, rows = mt.pv01_rows()
        self.assertNotEqual(v6.content_sha256(mt.build(ids, rows[::-1])), base)  # row order is content

    def test_null_and_empty_digest_differently(self) -> None:
        # A valid pair: the same plane with DNA absent (null, unlisted) and measured empty ([]).
        ids, rows = mt.pv03_rows()
        measured_empty = mt.build(ids, rows)
        rows[0][0]["channels"], rows[0][0]["channel_count"] = "PAX_488", 1
        del rows[0][1]["DNA"]
        self.assertNotEqual(v6.content_sha256(mt.build(ids, rows)), v6.content_sha256(measured_empty))

    def test_serialiser_one_field_at_a_time(self) -> None:
        """Each change of exactly one cell changes the serialisation: one cell per column type,
        and a null list against an empty one in the same cell (the serialiser, unchecked)."""
        import pyarrow as pa

        base = mt.build(*mt.pv03_rows())
        changes = {
            "plane_id": "x",                              # string
            "z": 7,                                       # int64
            "Histogram_UnderflowMean_PAX_488": -999.0,    # double
            "Histogram_Bins_PAX_488": [0, 3, 4, 6, 6],    # list<int32>
            "Histogram_Counts_PAX_488": [2, 6, 3, 1, 3],  # list<int64>
            "Intensity_MinIntensity_PAX_488": None,       # a value against null
            "Histogram_Bins_DNA": None,                   # [] against null, nothing else changed
        }
        for name, value in changes.items():
            with self.subTest(column=name):
                index = base.column_names.index(name)
                cells = base.column(name).to_pylist()
                cells[0] = value
                changed = base.set_column(index, base.schema.field(index), pa.array(cells, base.schema.field(index).type))
                differing = [n for n in base.column_names if base.column(n).to_pylist() != changed.column(n).to_pylist()]
                self.assertEqual(differing, [name])
                self.assertNotEqual(v6.serialise(changed), v6.serialise(base))

    def test_no_digest_for_an_invalid_table(self) -> None:
        ids, rows = mt.pv01_rows()
        mt._lists(0, "DNA", [0, 1, 2, 3], [4, 4, 5, 2])(ids, rows)  # counts sum to 15 of 16
        with self.assertRaises(v6.PlaneHistogramsError):
            v6.content_sha256(mt.build(ids, rows))

    def test_ew11_reference_is_the_content_digest(self) -> None:
        """PQ9 (supersedes EW11's file SHA): the same content in other bytes is no mismatch."""
        pv01, pv06 = _valid("pv01_two_channels_uint8"), _valid("pv06_pv01_other_writer_settings")
        reference = v6.content_sha256(v6.read_table(pv01))  # recorded when the window run was planned
        self.assertNotEqual(v6.file_sha256(pv01), v6.file_sha256(pv06))
        self.assertTrue(v6.reference_matches(pv06, reference))
        self.assertFalse(v6.reference_matches(pv06, v6.file_sha256(pv01)))

    def test_manifest_check(self) -> None:
        path = _valid("pv01_two_channels_uint8")
        content = v6.content_sha256(v6.read_table(path))
        v6.check_manifest_entry(path, v6.file_sha256(path), content)
        with self.assertRaises(ValueError):
            v6.check_manifest_entry(path, v6.file_sha256(path), "0" * 64)
        with self.assertRaises(ValueError):
            v6.check_manifest_entry(path, "0" * 64, content)


if __name__ == "__main__":
    unittest.main()
