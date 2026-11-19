"""Write the golden ``plane_histograms.parquet`` tables of ADR 0008 (proposed) into this folder.

Run ``python -I tools/plane_histograms_v6/make_tables.py`` from the repository root, with the
tools' requirements installed (``tools/requirements.txt``). The files are committed; the tests
read them and never call this script. Their **content digests** (ADR 0008 PQ6) are listed in
``README.md`` and are the same whatever ``pyarrow`` version writes them; their bytes are not.

The values of ``pv01``-``pv04`` are those the normalization brick's own version 5 writer
(``write_plane_histograms`` at ``9616e12``) wrote for seeded planes (this PR's earlier CSV goldens,
Spec ``9167fe3``): the intensity and binning limits keep that writer's text, the dense bins are
the non-zero bins with their counts. ``pv05`` is a seeded full-range uint16 plane.
"""

from __future__ import annotations

import importlib.util
import random
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("plane_histograms_v6", HERE.parent / "plane_histograms_v6.py")
v6 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(v6)

ARROW = {"string": pa.string(), "int64": pa.int64(), "double": pa.float64(),
         "list<int32>": pa.list_(pa.int32()), "list<int64>": pa.list_(pa.int64())}

#: The writer profile ADR 0008 PQ5 recommends (it fixes the bytes for one pyarrow version only).
PROFILE = {"compression": "zstd", "compression_level": 3, "use_dictionary": True,
           "write_statistics": False, "write_page_checksum": True, "store_schema": False,
           "row_group_size": 32767}  # at most 32,767 rows per row group (PQ5)
#: Another profile, for pv06: other bytes, the same content digest.
OTHER_PROFILE = {"compression": "none", "use_dictionary": False, "write_statistics": True,
                 "store_schema": True, "data_page_version": "1.0", "row_group_size": 1}


def plane(image: str, z: int, condition: str, dtype: str, bits: int, channels: list[str],
          total: int, bins: int, *, version: int = 6) -> dict:
    path = f"{condition}/rep1/{image}.tif"
    return {"position_id": image, "image_file": f"{image}.tif", "z": z, "t": 0,
            "condition": condition, "biological_repeat": "rep1", "technical_repeat": "single",
            "source_relative_path": path, "plane_id": f"{path}::z={z},t=0", "dtype": dtype,
            "bit_depth": bits, "channel_count": len(channels), "total_pixel_count": total,
            "bin_count": bins, "schema_version": version, "channels": ";".join(channels)}


def channel(lo: str | None, hi: str | None, valid: int, pairs: list[tuple[int, int]], *,
            binning: tuple[str | None, str | None] | None = None,
            under: tuple[int, float, float] = (0, 0.0, 0.0),
            over: tuple[int, float, float] = (0, 0.0, 0.0)) -> tuple:
    """The 13 values of a measured channel; the binning limits default to the intensity limits."""
    blo, bhi = binning if binning is not None else (lo, hi)
    return (lo, hi, valid, blo, bhi, *under, *over, [i for i, _ in pairs], [c for _, c in pairs])


ABSENT = (None,) * v6.PER_CHANNEL


def build(ids: list[str], rows: list[tuple[dict, dict]], types: dict[str, str] | None = None) -> pa.Table:
    """A table of ``rows`` (plane values, ``{channel: 13 values}``; a missing channel is absent)."""
    columns = v6.table_columns(ids)
    data: dict[str, list] = {name: [] for name, _ in columns}
    for meta, by_channel in rows:
        for name, value in meta.items():
            data[name].append(value)
        for cid in sorted(ids):
            for (name, _), value in zip(v6.channel_columns(cid), by_channel.get(cid, ABSENT), strict=True):
                data[name].append(value)
    types = types or {}
    schema = pa.schema([(name, ARROW[types.get(name, kind)]) for name, kind in columns])
    return pa.table(data, schema=schema)


def write(table: pa.Table, name: str, profile: dict | None = None, folder: str = "valid") -> Path:
    path = HERE / folder / f"{name}.parquet"
    path.parent.mkdir(exist_ok=True)
    profile = dict(profile or PROFILE)
    pq.write_table(table, path, row_group_size=profile.pop("row_group_size", None), **profile)
    return path


# ------------------------------------------------------------------------------------- valid
def pv01_rows() -> tuple[list[str], list]:
    ids = ["ACTIN", "DNA"]
    return ids, [
        (plane("img01", 0, "CTRL", "uint8", 8, ["DNA", "ACTIN"], 16, 256), {
            "DNA": channel("100", "103", 16, [(0, 4), (1, 4), (2, 5), (3, 3)]),
            "ACTIN": channel("10", "39", 16, [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (9, 1),
                                              (12, 1), (14, 1), (19, 2), (22, 1), (26, 2), (29, 1)]),
        }),
        (plane("img01", 1, "CTRL", "uint8", 8, ["DNA", "ACTIN"], 16, 256), {
            "DNA": channel("100", "103", 16, [(0, 6), (1, 3), (2, 2), (3, 5)]),
            "ACTIN": channel("11", "33", 16, [(0, 1), (2, 2), (5, 1), (7, 2), (8, 1), (9, 1), (10, 3), (15, 1),
                                              (18, 2), (19, 1), (22, 1)]),
        }),
    ]


def pv02_rows() -> tuple[list[str], list]:
    ids = ["ACTIN", "DNA", "PHASE"]
    return ids, [
        (plane("img01", 0, "CTRL", "uint8", 8, ["DNA", "ACTIN"], 16, 256), {
            "ACTIN": channel("201", "209", 16, [(0, 4), (1, 2), (2, 2), (3, 1), (4, 1), (5, 2), (6, 2), (8, 2)]),
            "DNA": channel("5", "8", 16, [(0, 3), (1, 5), (2, 2), (3, 6)]),
        }),
        (plane("img01", 0, "DrugA", "uint8", 8, ["DNA", "ACTIN", "PHASE"], 16, 256), {
            "ACTIN": channel("201", "209", 16, [(0, 1), (1, 3), (2, 2), (3, 1), (4, 2), (5, 1), (6, 1), (7, 3), (8, 2)]),
            "DNA": channel("5", "8", 16, [(0, 3), (1, 4), (2, 3), (3, 6)]),
            "PHASE": channel("0", "2", 16, [(0, 9), (1, 5), (2, 2)]),
        }),
    ]


def pv03_rows() -> tuple[list[str], list]:
    ids = ["DNA", "PAX_488"]
    return ids, [
        (plane("img01", 0, "CTRL", "float32", 32, ["PAX_488", "DNA"], 16, 8), {
            "DNA": channel(None, None, 0, []),  # measured, no finite pixel: two empty lists
            "PAX_488": channel("-1000.0", "1000.0", 16, [(0, 2), (3, 6), (4, 3), (6, 1), (7, 2)],
                               binning=("89.11814880371094", "115.3962173461914"),
                               under=(1, -1000.0, 0.0), over=(1, 1000.0, 0.0)),
        }),
    ]


def pv04_rows() -> tuple[list[str], list]:
    return ["DNA"], [
        (plane("img02", 0, "CTRL", "uint8", 8, ["DNA"], 16, 256), {
            "DNA": channel("0", "255", 16, [(0, 14), (255, 2)]),
        }),
    ]


def pv05_rows() -> tuple[list[str], list]:
    """Full-range uint16 (JUMP-like): 64 x 64 seeded pixels per channel over 0..65535, exact bins."""
    rng = random.Random(20261117)
    by_channel = {}
    for cid in ("DNA", "MITO"):
        pixels = [rng.randrange(65536) for _ in range(4096 - 16)] + [0] * 4 + [65535] * 12  # saturated
        counts = Counter(pixels)
        lo, hi = min(counts), max(counts)
        by_channel[cid] = channel(str(lo), str(hi), len(pixels), [(v - lo, counts[v]) for v in sorted(counts)])
    return ["DNA", "MITO"], [(plane("img03", 0, "CTRL", "uint16", 16, ["DNA", "MITO"], 4096, 65536), by_channel)]


VALID = {
    "pv01_two_channels_uint8": pv01_rows,
    "pv02_absent_channel_null": pv02_rows,
    "pv03_measured_empty_and_tails_id_with_underscore": pv03_rows,
    "pv04_last_bin_index": pv04_rows,
    "pv05_full_range_uint16": pv05_rows,
}


# ----------------------------------------------------------------------------------- invalid
def _edit(rows_of, change) -> pa.Table:
    """``rows_of()``'s table after ``change(ids, rows)`` edits its rows in place."""
    ids, rows = rows_of()
    types = change(ids, rows)
    return build(ids, rows, types)


def _set(row: int, cid: str, feature: str, value):
    """A change that sets one channel value of one row."""
    index = [f for f, _ in v6.CHANNEL_FEATURES].index(feature)

    def change(ids, rows):
        values = list(rows[row][1].get(cid, ABSENT))
        values[index] = value
        rows[row][1][cid] = tuple(values)
    return change


def _lists(row: int, cid: str, bins, counts):
    def change(ids, rows):
        values = list(rows[row][1][cid])
        values[-2:] = [bins, counts]
        rows[row][1][cid] = tuple(values)
    return change


def _meta(row: int, name: str, value):
    def change(ids, rows):
        rows[row][0][name] = value
    return change


def _every_row(name: str, value):
    def change(ids, rows):
        for meta, _ in rows:
            meta[name] = value
    return change


def _both(*changes):
    """Several changes to one value set that together make one rule's case (each is one field)."""
    def change(ids, rows):
        for one in changes:
            one(ids, rows)
    return change


def _drop_channel(row: int, cid: str):
    """Row ``row`` no longer lists ``cid`` (absent: all 13 values null), the rest unchanged."""
    def change(ids, rows):
        meta, by_channel = rows[row]
        listed = [c for c in meta["channels"].split(";") if c != cid]
        meta["channels"], meta["channel_count"] = ";".join(listed), len(listed)
        del by_channel[cid]
    return change


def _not_token() -> pa.Table:
    """pv04 with its one channel ID ``DNA-1`` (a hyphen: not a Token)."""
    _, rows = pv04_rows()
    meta, by_channel = rows[0]
    meta["channels"] = "DNA-1"
    return build(["DNA-1"], [(meta, {"DNA-1": by_channel["DNA"]})])


def _absent_lists(row: int, cid: str):
    """An absent channel (not in ``channels``) given two empty lists, its other values null."""
    def change(ids, rows):
        rows[row][1][cid] = (*ABSENT[:-2], [], [])
    return change


def _unsorted_blocks() -> pa.Table:
    table = build(*pv01_rows())
    names = table.column_names
    order = names[:v6.LEADING] + names[v6.LEADING + v6.PER_CHANNEL:] + names[v6.LEADING:v6.LEADING + v6.PER_CHANNEL]
    return table.select(order)


INVALID = {
    "pi03_parquet_schema_version_5": lambda: _edit(pv01_rows, _every_row("schema_version", 5)),
    "pi04_schema_version_7": lambda: _edit(pv01_rows, _every_row("schema_version", 7)),
    "pi05_channel_blocks_unsorted": _unsorted_blocks,
    "pi06_bins_int64": lambda: _edit(pv01_rows, lambda ids, rows: {f"Histogram_Bins_{c}": "list<int64>" for c in ids}),
    "pi07_bins_unordered": lambda: _edit(pv01_rows, _lists(0, "DNA", [1, 0, 2, 3], [4, 4, 5, 3])),
    "pi08_bins_repeated": lambda: _edit(pv01_rows, _lists(0, "DNA", [0, 0, 2, 3], [4, 4, 5, 3])),
    "pi09_bin_index_equals_bin_count": lambda: _edit(pv01_rows, _lists(0, "DNA", [0, 1, 2, 256], [4, 4, 5, 3])),
    "pi10_bin_index_negative": lambda: _edit(pv01_rows, _lists(0, "DNA", [-1, 1, 2, 3], [4, 4, 5, 3])),
    "pi11_zero_count": lambda: _edit(pv01_rows, _lists(0, "DNA", [0, 1, 2, 3, 4], [4, 4, 5, 3, 0])),
    "pi12_negative_count": lambda: _edit(pv01_rows, _lists(0, "DNA", [0, 1, 2, 3, 4], [4, 4, 6, 3, -1])),
    "pi13_lists_length_differ": lambda: _edit(pv01_rows, _lists(0, "DNA", [0, 1, 2, 3], [8, 5, 3])),
    "pi14_counts_sum_mismatch": lambda: _edit(pv01_rows, _lists(0, "DNA", [0, 1, 2, 3], [4, 4, 5, 2])),
    "pi15_empty_lists_with_pixels": lambda: _edit(pv01_rows, _lists(0, "DNA", [], [])),
    "pi16_listed_channel_lists_null": lambda: _edit(pv01_rows, _lists(0, "DNA", None, None)),
    "pi17_absent_channel_empty_lists": lambda: _edit(pv02_rows, _absent_lists(0, "PHASE")),
    "pi18_absent_channel_valid_zero": lambda: _edit(pv02_rows, _set(0, "PHASE", "Histogram_ValidPixelCount", 0)),
    "pi19_bin_count_differs": lambda: _edit(pv01_rows, _meta(1, "bin_count", 128)),
    "pi20_null_in_counts": lambda: _edit(pv01_rows, _lists(0, "DNA", [0, 1, 2, 3], [4, 4, None, 3])),
    "pi21_channel_count_mismatch": lambda: _edit(pv01_rows, _meta(0, "channel_count", 3)),
    # the second row moved to z 0 with its plane_id: a duplicate whose plane_id agrees with z
    "pi22_duplicate_plane": lambda: _edit(pv01_rows, _both(_meta(1, "z", 0), _meta(1, "plane_id", "CTRL/rep1/img01.tif::z=0,t=0"))),
    "pi23_tail_mean_negative_zero": lambda: _edit(pv03_rows, _set(0, "DNA", "Histogram_UnderflowMean", -0.0)),
    "pi25_plane_column_null": lambda: _edit(pv01_rows, _meta(0, "condition", None)),
    # version 5's checks, rebuilt (PQ4): each table breaks exactly one of them
    "pi26_bin_count_above_dtype_range": lambda: _edit(pv01_rows, _every_row("bin_count", 512)),
    "pi27_valid_above_total": lambda: _edit(pv01_rows, _meta(0, "total_pixel_count", 15)),
    "pi28_no_valid_pixel_with_limit": lambda: _edit(pv03_rows, _set(0, "DNA", "Intensity_MinIntensity", "0.0")),
    "pi29_limits_unordered": lambda: _edit(pv01_rows, _both(_set(0, "DNA", "Intensity_MinIntensity", "103"), _set(0, "DNA", "Histogram_BinningMin", "103"), _set(0, "DNA", "Histogram_BinningMax", "100"), _set(0, "DNA", "Intensity_MaxIntensity", "100"))),
    "pi30_limit_text_not_canonical": lambda: _edit(pv01_rows, _set(0, "DNA", "Intensity_MinIntensity", "0100")),
    "pi31_tail_mean_out_of_range": lambda: _edit(pv03_rows, _set(0, "PAX_488", "Histogram_UnderflowMean", -2000.0)),
    "pi32_bit_depth_not_dtype": lambda: _edit(pv01_rows, _every_row("bit_depth", 16)),
    "pi33_plane_id_not_path_z_t": lambda: _edit(pv01_rows, _meta(1, "plane_id", "CTRL/rep1/img01.tif::z=2,t=0")),
    "pi34_negative_z": lambda: _edit(pv01_rows, _both(_meta(1, "z", -1), _meta(1, "plane_id", "CTRL/rep1/img01.tif::z=-1,t=0"))),
    "pi35_image_channels_differ": lambda: _edit(pv01_rows, _drop_channel(1, "ACTIN")),
    "pi36_channel_id_not_token": _not_token,
}


def write_invalid(names) -> None:
    """Write only the named invalid tables (leaves every other committed file's bytes alone)."""
    for name in names:
        write(INVALID[name](), name, folder="invalid")


def main() -> None:
    for name, rows_of in VALID.items():
        write(build(*rows_of()), name)
    write(build(*pv01_rows()), "pv06_pv01_other_writer_settings", OTHER_PROFILE)
    for name, make in INVALID.items():
        write(make(), name, folder="invalid")
    data = (HERE / "valid" / "pv01_two_channels_uint8.parquet").read_bytes()
    (HERE / "invalid" / "pi24_truncated_file.parquet").write_bytes(data[: len(data) // 2])


if __name__ == "__main__":
    main()
