"""Reference checker of the ``plane_histograms.parquet`` table, schema version 6 (ADR 0008, **proposed**).

Checks what ADR 0008 changes against version 5 (ADR 0003): the Parquet file, its column names,
order and types, the schema version (a version 5 CSV is refused by its ``schema_version`` value),
the presence column, one bin count per table, the absent/measured representation (PQ3) and the
two count lists of every measured channel with their sum rule (PQ2). It also rebuilds what version
5's ``PlaneRecord`` and ``PlaneHistogram`` check (normalization v0.7.1 ``integrity.py``,
``records.py``, ``dtypes.py``, ``channels.py`` and the v5 reader's row checks; PQ4): valid <= total
pixels; no limits and empty tails without a valid pixel; four finite, ordered limits otherwise, a
tail exactly where a limit lies inside its extremum, and tail moments possible for their range;
the limits' canonical text (PQ2 types); dtype, bit depth and the dtype's bin-count range;
``plane_id`` and ``image_file`` agreeing with path, z and t; z and t >= 0; a position ID; one
channel list per image; channel IDs that follow the Token rule. Only a table that passes every
check has a **content digest** (PQ6), the identity the run manifest records.

Needs ``pyarrow`` (``tools/requirements.txt``), imported only when a table is read; no brick
imports this module. The files in ``tools/plane_histograms_v6/`` and
``tools/test_plane_histograms_v6.py`` are its golden cases.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
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

#: Version 5's dtype rules (normalization ``dtypes.py``): the bit depth of each dtype, and the
#: bin-count range (integers 1..min(65,536, 2**bits), floats 2..65,536).
DTYPE_BITS = {"int8": 8, "int16": 16, "int32": 32, "int64": 64, "uint8": 8, "uint16": 16,
              "uint32": 32, "uint64": 64, "float32": 32, "float64": 64}
MAX_BIN_COUNT = 65_536
MIN_FLOAT_BIN_COUNT = 2
#: A canonical channel ID (normalization ``channels.py``, the Token rule of experiment-v1).
CHANNEL_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*")
#: Version 5's slack on a tail's standard deviation (``integrity.MOMENT_TOLERANCE``).
MOMENT_TOLERANCE = 1e-9
_INTEGER_TEXT = re.compile(r"-?(0|[1-9][0-9]*)")

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
    "plane_value",             # a plane column is null, a negative z or t, a blank position_id
    "dtype",                   # an unsupported dtype, or a bit_depth that is not the dtype's
    "bin_count_range",         # bin_count outside the dtype's range (v5 dtypes.validate_bin_count)
    "plane_id",                # plane_id or image_file not what path, z and t give
    "channel_id",              # a channel ID that breaks the Token rule
    "channels_cell",           # the presence column against channel_count and the header IDs
    "image_channels",          # two planes of one image list different channels
    "bin_count_differs",       # a second bin_count in one table
    "duplicate_plane",
    "absent_has_value",        # a value (also [] or 0) in a column of an absent channel
    "present_null",            # a null count, tail count or list for a listed channel
    "float_value",             # NaN, an infinity or -0.0 in a tail mean or std
    "pixel_counts",            # more valid pixels than pixels
    "limit_text",              # a limit not in version 5's canonical text for the dtype
    "limits",                  # limits or tails without a valid pixel; limits missing, not finite, unordered
    "tail_moments",            # a tail against its limits: empty with moments, or mean/std impossible
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


def _refuse_csv(path: Path) -> None:
    """A file that is not Parquet: refuse an earlier-version CSV by its ``schema_version``.

    Reads the header line and the first row only (PQ7), never the whole file: a version 5 header
    alone has 131,110 columns for two 16-bit channels.
    """
    try:
        with open(path, "rb") as handle:  # decoded line by line: nothing after the first row
            rows = csv.reader(line.decode("utf-8") for line in handle)
            header, first = next(rows), next(rows)
        version = first[header.index("schema_version")]
    except (UnicodeDecodeError, StopIteration, ValueError, IndexError, csv.Error, OSError):
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
    """Read and check a whole table (:func:`check_table`); return the decoded ``pyarrow.Table``."""
    path = Path(path)
    with open(path, "rb") as handle:
        head = handle.read(4)
    data = path.read_bytes() if head == PARQUET_MAGIC else b""
    if not (data.endswith(PARQUET_MAGIC) and len(data) >= 12):
        _refuse_csv(path)
    import pyarrow as pa
    import pyarrow.parquet as pq

    try:
        table = pq.read_table(pa.BufferReader(data))
    except (pa.ArrowException, OSError) as error:
        raise PlaneHistogramsError("not_parquet", f"not a readable Parquet file: {error}") from None
    check_table(table)
    return table


def _fail(skip: frozenset[str], reason: str, message: str, row: int | None = None) -> None:
    """Refuse the table for ``reason``, unless an audit skips that rule (:func:`check_table`)."""
    if reason not in skip:
        raise PlaneHistogramsError(reason, message, row)


def check_table(table, skip: frozenset[str] = frozenset()) -> None:
    """Check a decoded table against every rule of :data:`REASONS` (ADR 0008 PQ4).

    Raises :class:`PlaneHistogramsError` at the first rule broken; returns None when all hold.
    ``skip`` (an audit of the golden tables only) names rules not enforced: a table that breaks
    exactly one rule passes with that rule skipped, wherever the other rules can still be checked.
    """
    names = table.column_names
    if "schema_version" in names and table.num_rows:
        version = table.column("schema_version")[0].as_py()
        if str(version) in EARLIER_VERSIONS:
            _fail(skip, 
                "schema_version_refused",
                f"schema version {version} is refused: this reader reads version 6 only; recompute "
                "the table with the preprocessing brick (no converter, ADR 0008 PQ7)",
            )
    ids = header_channel_ids(names) if names[:LEADING] == [n for n, _ in PLANE_COLUMNS] + [CHANNELS_COLUMN] else None
    if ids is None:
        _fail(skip, 
            "header",
            "the columns are not the 15 plane columns, `channels`, then 13 per channel ID, IDs "
            "sorted, ending with Histogram_Bins_<ID> and Histogram_Counts_<ID>",
        )
    for (name, kind), field in zip(table_columns(ids), table.schema, strict=True):
        if _type_name(field.type) != kind:
            _fail(skip, "column_type", f"column {name} is {field.type}; version 6 has {kind}")
    bad_ids = [i for i in ids if not CHANNEL_ID.fullmatch(i)]
    if bad_ids:
        _fail(skip, "channel_id", f"channel ID(s) {bad_ids} break the Token rule (a letter, then letters, digits and single underscores)")
    if table.num_rows == 0:
        _fail(skip, "no_rows", "the table has no rows")
    columns = {name: table.column(name).to_pylist() for name in names}
    table_bins = None
    seen: set[str] = set()
    image_channels: dict[str, str] = {}
    for row in range(table.num_rows):
        meta = {name: columns[name][row] for name, _ in (*PLANE_COLUMNS, (CHANNELS_COLUMN, ""))}
        nulls = [name for name, value in meta.items() if value is None]
        if nulls:
            _fail(skip, "plane_value", f"plane column(s) {', '.join(nulls)} are null", row)
        if meta["schema_version"] != SCHEMA_VERSION:
            _fail(skip, "schema_version_unknown", f"schema version {meta['schema_version']}; this reader reads 6 only", row)
        dtype = meta["dtype"]
        if dtype not in DTYPE_BITS or meta["bit_depth"] != DTYPE_BITS[dtype]:
            _fail(skip, "dtype", f"dtype {dtype!r} with bit_depth {meta['bit_depth']}: the dtype must be one of {sorted(DTYPE_BITS)} and bit_depth its bits", row)
        low, high = _bin_count_range(dtype)
        if not low <= meta["bin_count"] <= high:
            _fail(skip, "bin_count_range", f"bin_count {meta['bin_count']} for {dtype}: allowed {low}..{high}", row)
        if meta["z"] < 0 or meta["t"] < 0 or not meta["position_id"].strip():
            _fail(skip, "plane_value", f"z {meta['z']}, t {meta['t']} (each >= 0) and position_id {meta['position_id']!r} (never blank)", row)
        path = meta["source_relative_path"]
        expected_id = f"{path}::z={meta['z']},t={meta['t']}"
        if meta["plane_id"] != expected_id or meta["image_file"] != path.rsplit("/", 1)[-1]:
            _fail(skip, "plane_id", f"plane_id {meta['plane_id']!r} and image_file {meta['image_file']!r}; path, z and t give {expected_id!r} and {path.rsplit('/', 1)[-1]!r}", row)
        present = meta[CHANNELS_COLUMN].split(";") if meta[CHANNELS_COLUMN] else []
        if not present or len(set(present)) != len(present) or any(c not in ids for c in present) \
                or meta["channel_count"] != len(present):
            _fail(skip, "channels_cell", f"channels {meta[CHANNELS_COLUMN]!r} against channel_count {meta['channel_count']} and the IDs {ids}", row)
        if table_bins is None:
            table_bins = meta["bin_count"]
        elif meta["bin_count"] != table_bins:
            _fail(skip, "bin_count_differs", f"bin_count {meta['bin_count']}; the first row has {table_bins} (one bin count per table)", row)
        if meta["plane_id"] in seen:
            _fail(skip, "duplicate_plane", f"plane {meta['plane_id']} has a second row", row)
        seen.add(meta["plane_id"])
        if image_channels.setdefault(path, meta[CHANNELS_COLUMN]) != meta[CHANNELS_COLUMN]:
            _fail(skip, "image_channels", f"image {path} lists {image_channels[path]!r} on one plane and {meta[CHANNELS_COLUMN]!r} on another (one channel list per image)", row)
        for channel in ids:
            _check_channel(columns, row, channel, channel in present, table_bins, dtype, meta["total_pixel_count"], skip)


def _bin_count_range(dtype: str) -> tuple[int, int]:
    if dtype.startswith("float"):
        return MIN_FLOAT_BIN_COUNT, MAX_BIN_COUNT
    return 1, min(MAX_BIN_COUNT, 2 ** DTYPE_BITS[dtype])


def _dtype_bounds(dtype: str) -> tuple[int, int]:
    bits = DTYPE_BITS[dtype]
    return (0, 2**bits - 1) if dtype.startswith("u") else (-(2 ** (bits - 1)), 2 ** (bits - 1) - 1)


def parse_limit(text: str, dtype: str, row: int | None = None, name: str = "limit", skip: frozenset[str] = frozenset()) -> int | float:
    """Parse one limit's text as the v5 writer writes it for ``dtype``; refuse any other spelling.

    An integer dtype: a decimal integer (no sign but ``-``, no leading zero, no ``-0``) inside the
    dtype's range. A float dtype: the shortest round-trip ``repr`` of a float64, ``0.0`` for zero
    (never ``-0.0``). Nothing is rounded or repaired (ADR 0008 PQ2 types).
    """
    if not dtype.startswith("float"):
        low, high = _dtype_bounds(dtype)
        if not _INTEGER_TEXT.fullmatch(text) or text == "-0" or not low <= int(text) <= high:
            _fail(skip, "limit_text", f"{name} {text!r} is not a {dtype} value in the v5 writer's text (a decimal integer in {low}..{high})", row)
        return int(text)
    try:
        value = float(text)
    except ValueError:
        value = None
    if value is None or text == "-0.0" or repr(value) != text:
        _fail(skip, "limit_text", f"{name} {text!r} is not the v5 writer's text of a {dtype} value (the shortest round-trip repr, 0.0 for zero)", row)
    return value


def _check_channel(columns, row: int, channel: str, present: bool, bin_count: int, dtype: str, total: int, skip: frozenset[str]) -> None:
    values = {feature: columns[f"{feature}_{channel}"][row] for feature, _ in CHANNEL_FEATURES}
    if not present:
        filled = [f"{feature}_{channel}" for feature, value in values.items() if value is not None]
        if filled:
            _fail(skip, "absent_has_value", f"channel {channel} is absent, but {', '.join(filled)} hold a value (absent is null, never [], 0 or NaN)", row)
        return
    required = ("Histogram_ValidPixelCount", "Histogram_UnderflowCount", "Histogram_UnderflowMean",
                "Histogram_UnderflowStd", "Histogram_OverflowCount", "Histogram_OverflowMean",
                "Histogram_OverflowStd", "Histogram_Bins", "Histogram_Counts")
    nulls = [f"{feature}_{channel}" for feature in required if values[feature] is None]
    if nulls:
        _fail(skip, "present_null", f"channel {channel} is listed, but {', '.join(nulls)} are null (a measured channel with no pixel in a bin has two empty lists)", row)
        return
    for feature in ("Histogram_ValidPixelCount", "Histogram_UnderflowCount", "Histogram_OverflowCount"):
        if values[feature] < 0:
            _fail(skip, "plane_value", f"{feature}_{channel} is negative", row)
    valid = values["Histogram_ValidPixelCount"]
    if valid > total:
        _fail(skip, "pixel_counts", f"channel {channel}: {valid} valid pixels but the plane has {total} pixels", row)
    for feature in ("Histogram_UnderflowMean", "Histogram_UnderflowStd", "Histogram_OverflowMean", "Histogram_OverflowStd"):
        value = values[feature]
        if not math.isfinite(value) or (value == 0.0 and math.copysign(1.0, value) < 0):
            _fail(skip, "float_value", f"{feature}_{channel} is {value!r}: a tail mean or std is finite and a zero is +0.0", row)
    tails = {}
    for side in ("Underflow", "Overflow"):
        count, mean, std = (values[f"Histogram_{side}{part}"] for part in ("Count", "Mean", "Std"))
        if (count == 0 and (mean != 0 or std != 0)) or std < 0:
            _fail(skip, "tail_moments", f"channel {channel}: {side.lower()} of {count} pixel(s) with mean {mean!r} and std {std!r} (an empty tail has 0 and 0; a std is >= 0)", row)
        tails[side] = (count, mean, std)
    limit_names = ("Intensity_MinIntensity", "Histogram_BinningMin", "Histogram_BinningMax", "Intensity_MaxIntensity")
    texts = [values[name] for name in limit_names]
    if valid == 0:
        if any(text is not None for text in texts) or tails["Underflow"][0] or tails["Overflow"][0]:
            _fail(skip, "limits", f"channel {channel} has no valid pixel, so no intensity limits and empty tails", row)
    else:
        missing = [f"{name}_{channel}" for name, text in zip(limit_names, texts) if text is None]
        if missing:
            _fail(skip, "limits", f"channel {channel} has {valid} valid pixel(s), but {', '.join(missing)} are null", row)
            return
        limits = [parse_limit(text, dtype, row, f"{name}_{channel}", skip) for name, text in zip(limit_names, texts)]
        if not all(math.isfinite(float(v)) for v in limits) or not limits[0] <= limits[1] <= limits[2] <= limits[3]:
            _fail(skip, "limits", f"channel {channel}: the limits {limits} are not finite and ordered minimum <= binning minimum <= binning maximum <= maximum", row)
        for side, extremum, limit in (("Underflow", limits[0], limits[1]), ("Overflow", limits[3], limits[2])):
            count, mean, std = tails[side]
            if (extremum == limit) != (count == 0):
                _fail(skip, "tail_moments", f"channel {channel}: the {side.lower()} holds {count} pixel(s), but the extremum {extremum!r} and the binning limit {limit!r} {'are equal' if extremum == limit else 'differ'}", row)
            if count:
                low, high = sorted((float(extremum), float(limit)))
                largest = 0.5 * high - 0.5 * low
                slack = math.ulp(max(abs(low), abs(high)))
                if not (low <= mean <= high and std <= largest * (1 + MOMENT_TOLERANCE) + slack):
                    _fail(skip, "tail_moments", f"channel {channel}: the {side.lower()} of {count} pixel(s) between {low!r} and {high!r} has mean {mean!r} and std {std!r}", row)
    bins, counts = values["Histogram_Bins"], values["Histogram_Counts"]
    if len(bins) != len(counts):
        _fail(skip, "lists_length", f"channel {channel}: {len(bins)} bin indices but {len(counts)} counts", row)
    if None in bins or None in counts:
        _fail(skip, "null_element", f"channel {channel}: a null inside Histogram_Bins or Histogram_Counts", row)
        return
    for previous, index in zip(bins, bins[1:]):
        if index <= previous:
            _fail(skip, "bins_order", f"channel {channel}: bin {index} follows {previous}; indices are strictly increasing", row)
    if bins and (bins[0] < 0 or bins[-1] >= bin_count):
        _fail(skip, "bins_range", f"channel {channel}: bin indices {bins[0]}..{bins[-1]} are not all in [0, {bin_count})", row)
    if any(count <= 0 for count in counts):
        _fail(skip, "counts_not_positive", f"channel {channel}: a count <= 0 (zero bins are not written)", row)
    expected = valid - values["Histogram_UnderflowCount"] - values["Histogram_OverflowCount"]
    if sum(counts) != expected:
        _fail(skip, "counts_sum", f"channel {channel}: the counts sum to {sum(counts)}, but valid - underflow - overflow = {expected}", row)


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
    """The canonical serialisation of a table that passes :func:`check_table` (ADR 0008 PQ6).

    A table that fails a check has no content digest: the check's error is raised instead.
    """
    check_table(table)
    return serialise(table)


def serialise(table) -> bytes:
    """The canonical serialisation of ``table``, unchecked (ADR 0008 PQ6), column by column.

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


def reference_matches(path: str | Path, reference_sha256: str) -> bool:
    """Whether ``path`` holds the plane table an EW11 window table refers to (ADR 0008 PQ9).

    ``reference_sha256`` is the plane table's ``content_sha256``, not its file bytes: a table
    rewritten with the same content (another ``pyarrow``, other writer settings) still matches,
    so its windows are not ``plane_histogram_mismatch``.
    """
    return content_sha256(read_table(path)) == reference_sha256


def check_manifest_entry(path: str | Path, file_digest: str, content_digest: str) -> None:
    """The run-manifest check of ADR 0008 PQ6: the file is the one the run wrote (its bytes),
    it is a valid version 6 table, and its content digest is the recorded one."""
    if file_sha256(path) != file_digest:
        raise ValueError(f"{path}: not the file the run wrote (its SHA-256 differs from the manifest)")
    if content_sha256(read_table(path)) != content_digest:
        raise ValueError(f"{path}: its content digest differs from the manifest")
