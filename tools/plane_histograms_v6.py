"""Reference checker of the ``plane_histograms.parquet`` table, schema version 6 (ADR 0008, **proposed**).

Checks what ADR 0008 changes against version 5 (ADR 0003): the Parquet file, its column names,
order and types, the schema version (a version 5 CSV is refused by its ``schema_version`` value),
the presence column, one bin count per table, the absent/measured representation (PQ3) and the
two count lists of every measured channel with their sum rule (PQ2). It then computes the table's
**content digest** (PQ6), the identity the run manifest records. The per-channel invariants that
version 6 keeps from version 5 unchanged (intensity limits, tails, binning; normalization's
``integrity.py``) are not repeated here.

Needs ``pyarrow`` (``tools/requirements.txt``), imported only when a table is read; no brick
imports this module. The files in ``tools/plane_histograms_v6/`` and
``tools/test_plane_histograms_v6.py`` are its golden cases.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import struct
from pathlib import Path

SCHEMA_VERSION = 6
EARLIER_VERSIONS = ("1", "2", "3", "4", "5")
OUTPUT_FILENAME = "plane_histograms.parquet"
PARQUET_MAGIC = b"PAR1"

#: The 15 plane columns and their types, then the presence column ``channels`` (string).
PLANE_COLUMNS = (
    ("position_id", "string"), ("image_file", "string"), ("z", "int64"), ("t", "int64"),
    ("condition", "string"), ("biological_repeat", "string"), ("technical_repeat", "string"),
    ("source_relative_path", "string"), ("plane_id", "string"), ("dtype", "string"),
    ("bit_depth", "int64"), ("channel_count", "int64"), ("total_pixel_count", "int64"),
    ("bin_count", "int64"), ("schema_version", "int64"),
)
CHANNELS_COLUMN = "channels"
#: The 13 columns of one channel ID, in table order, and their types.
CHANNEL_FEATURES = (
    ("Intensity_MinIntensity", "string"), ("Intensity_MaxIntensity", "string"),
    ("Histogram_ValidPixelCount", "int64"),
    ("Histogram_BinningMin", "string"), ("Histogram_BinningMax", "string"),
    ("Histogram_UnderflowCount", "int64"), ("Histogram_UnderflowMean", "double"),
    ("Histogram_UnderflowStd", "double"),
    ("Histogram_OverflowCount", "int64"), ("Histogram_OverflowMean", "double"),
    ("Histogram_OverflowStd", "double"),
    ("Histogram_Bins", "list<int32>"), ("Histogram_Counts", "list<int64>"),
)
ID_FEATURE = "Histogram_ValidPixelCount"
PER_CHANNEL = len(CHANNEL_FEATURES)  # 13
LEADING = len(PLANE_COLUMNS) + 1  # 16

#: The first bytes of the canonical serialisation hashed by :func:`content_sha256` (PQ6).
CONTENT_PREAMBLE = b"MorphoBricks plane_histograms schema_version 6 content\n"
_TYPE_CODE = {"string": 1, "int64": 2, "double": 3, "list<int32>": 4, "list<int64>": 5}

REASONS = (
    "not_parquet",             # not a Parquet file (and not an earlier-version CSV)
    "schema_version_refused",  # schema version 1-5 (a CSV of version 5, or the value in a Parquet file)
    "schema_version_unknown",  # any other schema version
    "header",                  # column names or order are not those of version 6
    "column_type",             # a column's type is not its version 6 type
    "no_rows",
    "plane_value",             # a plane column is null, or a number in it is out of range
    "channels_cell",           # the presence column against channel_count and the header IDs
    "bin_count_differs",       # a second bin_count in one table
    "duplicate_plane",
    "absent_has_value",        # a value (also [] or 0) in a column of an absent channel
    "present_null",            # a null count, tail count or list for a listed channel
    "float_value",             # NaN, an infinity or -0.0 in a tail mean or std
    "lists_length",            # Histogram_Bins and Histogram_Counts of different lengths
    "null_element",            # a null inside a list
    "bins_order",              # bin indices not strictly increasing (unordered or repeated)
    "bins_range",              # a bin index < 0 or >= bin_count
    "counts_not_positive",     # a count <= 0 (zero bins are not written)
    "counts_sum",              # the counts do not sum to valid - underflow - overflow
)


class PlaneHistogramsError(ValueError):
    """A refused table; ``reason`` is one of :data:`REASONS`, ``row`` the 0-based row or None."""

    def __init__(self, reason: str, message: str, row: int | None = None) -> None:
        if reason not in REASONS:
            raise AssertionError(f"unknown reason {reason!r}")
        super().__init__(f"row {row}: {message}" if row is not None else message)
        self.reason, self.row = reason, row


def channel_columns(channel: str) -> list[tuple[str, str]]:
    """The 13 ``(name, type)`` columns of one channel ID, in table order."""
    return [(f"{feature}_{channel}", kind) for feature, kind in CHANNEL_FEATURES]


def table_columns(channel_ids) -> list[tuple[str, str]]:
    """The 15 plane columns and ``channels``, then 13 columns per channel ID, IDs sorted."""
    columns = [*PLANE_COLUMNS, (CHANNELS_COLUMN, "string")]
    for channel in sorted(channel_ids):
        columns.extend(channel_columns(channel))
    return columns


def header_channel_ids(names: list[str]) -> tuple[str, ...] | None:
    """The IDs named by the ``Histogram_ValidPixelCount_<ID>`` columns (HV2), or None when the
    names are not exactly those of :func:`table_columns` of these IDs."""
    prefix = f"{ID_FEATURE}_"
    ids = [name[len(prefix):] for name in names[LEADING:] if name.startswith(prefix)]
    if not ids or len(set(ids)) != len(ids) or any(not i or ";" in i for i in ids):
        return None
    if names != [name for name, _ in table_columns(ids)]:
        return None
    return tuple(sorted(ids))


def _type_name(arrow_type) -> str:
    import pyarrow as pa

    if pa.types.is_list(arrow_type):  # list only: large_list and fixed_size_list are refused
        return f"list<{arrow_type.value_type}>"
    return str(arrow_type)


def _refuse_csv(data: bytes) -> None:
    """A file that is not Parquet: refuse an earlier-version CSV by its ``schema_version``."""
    try:
        rows = csv.reader(io.StringIO(data.decode("utf-8"), newline=""))
        header, first = next(rows), next(rows)
        version = first[header.index("schema_version")]
    except (UnicodeDecodeError, StopIteration, ValueError, IndexError, csv.Error):
        version = None
    if version in EARLIER_VERSIONS:
        raise PlaneHistogramsError(
            "schema_version_refused",
            f"plane_histograms.csv schema version {version} is refused: this reader reads version 6 "
            f"only ({OUTPUT_FILENAME}); recompute the table with the preprocessing brick "
            "(no converter, ADR 0008 PQ7 / ADR 0002 AR10)",
        )
    raise PlaneHistogramsError(
        "not_parquet",
        "not a Parquet file: version 6 is a Parquet table (ADR 0008 PQ1); a CSV of any other "
        "version is refused",
    )


def read_table(path: str | Path):
    """Check a whole table; return the decoded ``pyarrow.Table``.

    Every rule of :data:`REASONS` is checked; the table is returned only when all hold.
    """
    data = Path(path).read_bytes()
    if not (data.startswith(PARQUET_MAGIC) and data.endswith(PARQUET_MAGIC) and len(data) >= 12):
        _refuse_csv(data)
    import pyarrow as pa
    import pyarrow.parquet as pq

    try:
        table = pq.read_table(pa.BufferReader(data))
    except (pa.ArrowException, OSError) as error:
        raise PlaneHistogramsError("not_parquet", f"not a readable Parquet file: {error}") from None
    names = table.column_names
    if "schema_version" in names and table.num_rows:
        version = table.column("schema_version")[0].as_py()
        if str(version) in EARLIER_VERSIONS:
            raise PlaneHistogramsError(
                "schema_version_refused",
                f"schema version {version} is refused: this reader reads version 6 only; recompute "
                "the table with the preprocessing brick (no converter, ADR 0008 PQ7)",
            )
    ids = header_channel_ids(names) if names[:LEADING] == [n for n, _ in PLANE_COLUMNS] + [CHANNELS_COLUMN] else None
    if ids is None:
        raise PlaneHistogramsError(
            "header",
            "the columns are not the 15 plane columns, `channels`, then 13 per channel ID, IDs "
            "sorted, ending with Histogram_Bins_<ID> and Histogram_Counts_<ID>",
        )
    for (name, kind), field in zip(table_columns(ids), table.schema, strict=True):
        if _type_name(field.type) != kind:
            raise PlaneHistogramsError("column_type", f"column {name} is {field.type}; version 6 has {kind}")
    if table.num_rows == 0:
        raise PlaneHistogramsError("no_rows", "the table has no rows")
    columns = {name: table.column(name).to_pylist() for name in names}
    table_bins = None
    seen: set[str] = set()
    for row in range(table.num_rows):
        meta = {name: columns[name][row] for name, _ in (*PLANE_COLUMNS, (CHANNELS_COLUMN, ""))}
        nulls = [name for name, value in meta.items() if value is None]
        if nulls:
            raise PlaneHistogramsError("plane_value", f"plane column(s) {', '.join(nulls)} are null", row)
        if meta["schema_version"] != SCHEMA_VERSION:
            raise PlaneHistogramsError("schema_version_unknown", f"schema version {meta['schema_version']}; this reader reads 6 only", row)
        if meta["bin_count"] < 1 or meta["bin_count"] > 2**31 - 1:
            raise PlaneHistogramsError("plane_value", f"bin_count {meta['bin_count']} is not in [1, 2**31 - 1]", row)
        present = meta[CHANNELS_COLUMN].split(";") if meta[CHANNELS_COLUMN] else []
        if not present or len(set(present)) != len(present) or any(c not in ids for c in present) \
                or meta["channel_count"] != len(present):
            raise PlaneHistogramsError("channels_cell", f"channels {meta[CHANNELS_COLUMN]!r} against channel_count {meta['channel_count']} and the IDs {ids}", row)
        if table_bins is None:
            table_bins = meta["bin_count"]
        elif meta["bin_count"] != table_bins:
            raise PlaneHistogramsError("bin_count_differs", f"bin_count {meta['bin_count']}; the first row has {table_bins} (one bin count per table)", row)
        if meta["plane_id"] in seen:
            raise PlaneHistogramsError("duplicate_plane", f"plane {meta['plane_id']} has a second row", row)
        seen.add(meta["plane_id"])
        for channel in ids:
            _check_channel(columns, row, channel, channel in present, table_bins)
    return table


def _check_channel(columns, row: int, channel: str, present: bool, bin_count: int) -> None:
    values = {feature: columns[f"{feature}_{channel}"][row] for feature, _ in CHANNEL_FEATURES}
    if not present:
        filled = [f"{feature}_{channel}" for feature, value in values.items() if value is not None]
        if filled:
            raise PlaneHistogramsError("absent_has_value", f"channel {channel} is absent, but {', '.join(filled)} hold a value (absent is null, never [], 0 or NaN)", row)
        return
    required = ("Histogram_ValidPixelCount", "Histogram_UnderflowCount", "Histogram_UnderflowMean",
                "Histogram_UnderflowStd", "Histogram_OverflowCount", "Histogram_OverflowMean",
                "Histogram_OverflowStd", "Histogram_Bins", "Histogram_Counts")
    nulls = [f"{feature}_{channel}" for feature in required if values[feature] is None]
    if nulls:
        raise PlaneHistogramsError("present_null", f"channel {channel} is listed, but {', '.join(nulls)} are null (a measured channel with no pixel in a bin has two empty lists)", row)
    for feature in ("Histogram_ValidPixelCount", "Histogram_UnderflowCount", "Histogram_OverflowCount"):
        if values[feature] < 0:
            raise PlaneHistogramsError("plane_value", f"{feature}_{channel} is negative", row)
    for feature in ("Histogram_UnderflowMean", "Histogram_UnderflowStd", "Histogram_OverflowMean", "Histogram_OverflowStd"):
        value = values[feature]
        if not math.isfinite(value) or (value == 0.0 and math.copysign(1.0, value) < 0):
            raise PlaneHistogramsError("float_value", f"{feature}_{channel} is {value!r}: a tail mean or std is finite and a zero is +0.0", row)
    bins, counts = values["Histogram_Bins"], values["Histogram_Counts"]
    if len(bins) != len(counts):
        raise PlaneHistogramsError("lists_length", f"channel {channel}: {len(bins)} bin indices but {len(counts)} counts", row)
    if None in bins or None in counts:
        raise PlaneHistogramsError("null_element", f"channel {channel}: a null inside Histogram_Bins or Histogram_Counts", row)
    for previous, index in zip(bins, bins[1:]):
        if index <= previous:
            raise PlaneHistogramsError("bins_order", f"channel {channel}: bin {index} follows {previous}; indices are strictly increasing", row)
    if bins and (bins[0] < 0 or bins[-1] >= bin_count):
        raise PlaneHistogramsError("bins_range", f"channel {channel}: bin indices {bins[0]}..{bins[-1]} are not all in [0, {bin_count})", row)
    if any(count <= 0 for count in counts):
        raise PlaneHistogramsError("counts_not_positive", f"channel {channel}: a count <= 0 (zero bins are not written)", row)
    expected = values["Histogram_ValidPixelCount"] - values["Histogram_UnderflowCount"] - values["Histogram_OverflowCount"]
    if sum(counts) != expected:
        raise PlaneHistogramsError("counts_sum", f"channel {channel}: the counts sum to {sum(counts)}, but valid - underflow - overflow = {expected}", row)


def dense_counts(table) -> dict[str, dict[str, list[int] | None]]:
    """``{plane_id: {channel: dense counts, or None if absent}}`` of a checked table."""
    ids = header_channel_ids(table.column_names)
    plane_ids = table.column("plane_id").to_pylist()
    bin_counts = table.column("bin_count").to_pylist()
    out: dict[str, dict[str, list[int] | None]] = {}
    for channel in ids:
        bins = table.column(f"Histogram_Bins_{channel}").to_pylist()
        counts = table.column(f"Histogram_Counts_{channel}").to_pylist()
        for row, plane in enumerate(plane_ids):
            if bins[row] is None:
                out.setdefault(plane, {})[channel] = None
                continue
            dense = [0] * bin_counts[row]
            for index, count in zip(bins[row], counts[row]):
                dense[index] = count
            out.setdefault(plane, {})[channel] = dense
    return out


def content_bytes(table) -> bytes:
    """The canonical serialisation of a checked table (ADR 0008 PQ6), column by column.

    ``PREAMBLE, u64 rows, u64 columns``; per column in file order ``u64 len(name), name (UTF-8),
    u8 type code`` and per row ``u8 0`` for null or ``u8 1`` and the value: a string as ``u64
    len, UTF-8``; an int64 as ``i64``; a double as its IEEE 754 binary64 bits; a list as ``u64 n``
    and ``n`` elements (``i32`` or ``i64``). Every integer is little-endian. Nothing of the file
    (compression, encodings, row groups, statistics, key-value metadata, writer name) enters it.
    """
    out = io.BytesIO()
    out.write(CONTENT_PREAMBLE)
    out.write(struct.pack("<QQ", table.num_rows, table.num_columns))
    for field in table.schema:
        kind = _type_name(field.type)
        name = field.name.encode("utf-8")
        out.write(struct.pack("<Q", len(name)) + name + struct.pack("<B", _TYPE_CODE[kind]))
        element = {"list<int32>": "<i", "list<int64>": "<q"}.get(kind)
        for value in table.column(field.name).to_pylist():
            if value is None:
                out.write(b"\x00")
            elif kind == "string":
                text = value.encode("utf-8")
                out.write(b"\x01" + struct.pack("<Q", len(text)) + text)
            elif kind == "int64":
                out.write(b"\x01" + struct.pack("<q", value))
            elif kind == "double":
                out.write(b"\x01" + struct.pack("<d", value))
            else:
                out.write(b"\x01" + struct.pack("<Q", len(value)) + struct.pack(f"<{len(value)}{element[1]}", *value))
    return out.getvalue()


def content_sha256(table) -> str:
    """The table's content digest: SHA-256 (hex) of :func:`content_bytes` (ADR 0008 PQ6)."""
    return hashlib.sha256(content_bytes(table)).hexdigest()


def file_sha256(path: str | Path) -> str:
    """SHA-256 (hex) of the file's bytes: integrity of the file a run wrote, not its identity."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_manifest_entry(path: str | Path, file_digest: str, content_digest: str) -> None:
    """The run-manifest check of ADR 0008 PQ6: the file is the one the run wrote (its bytes),
    it is a valid version 6 table, and its content digest is the recorded one."""
    if file_sha256(path) != file_digest:
        raise ValueError(f"{path}: not the file the run wrote (its SHA-256 differs from the manifest)")
    if content_sha256(read_table(path)) != content_digest:
        raise ValueError(f"{path}: its content digest differs from the manifest")
