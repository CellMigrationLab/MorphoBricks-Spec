"""Reference checker of ``plane_histograms.csv`` schema version 6 (ADR 0008, **proposed**).

Checks the layout that ADR 0008 changes against version 5 (ADR 0003): the header, the schema
version, the presence column, one bin count per table and the sparse ``Histogram_Counts_<ID>``
cell (``docs/sparse-counts.md``) with its sum rule. The per-channel invariants that version 6 keeps
from version 5 unchanged (intensity limits, tails, binning; normalization's ``integrity.py``) are
not repeated here. Pure Python, standard library only; no brick imports it. The fixtures in
``tools/plane_histograms_v6/`` and ``tools/test_plane_histograms_v6.py`` are its golden cases.
"""

from __future__ import annotations

import csv
import importlib.util
import io
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("sparse_counts", Path(__file__).resolve().parent / "sparse_counts.py")
sparse = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sparse)

SCHEMA_VERSION = "6"
EARLIER_VERSIONS = ("1", "2", "3", "4", "5")
PLANE_COLUMNS = (
    "position_id", "image_file", "z", "t", "condition", "biological_repeat", "technical_repeat",
    "source_relative_path", "plane_id", "dtype", "bit_depth", "channel_count", "total_pixel_count",
    "bin_count", "schema_version",
)
CHANNELS_COLUMN = "channels"
CHANNEL_FEATURES = (
    "Intensity_MinIntensity", "Intensity_MaxIntensity", "Histogram_ValidPixelCount",
    "Histogram_BinningMin", "Histogram_BinningMax",
    "Histogram_UnderflowCount", "Histogram_UnderflowMean", "Histogram_UnderflowStd",
    "Histogram_OverflowCount", "Histogram_OverflowMean", "Histogram_OverflowStd",
)
COUNTS_FEATURE = "Histogram_Counts"
ID_FEATURE = "Histogram_ValidPixelCount"
PER_CHANNEL = len(CHANNEL_FEATURES) + 1  # 12
LEADING = len(PLANE_COLUMNS) + 1  # 16

REASONS = (
    "file_empty", "header", "schema_version_refused", "schema_version_unknown", "row_width",
    "channels_cell", "bin_count", "bin_count_differs", "absent_has_value", "channel_value",
    "no_rows", "duplicate_plane", *sparse.REASONS,
)


class PlaneHistogramsError(ValueError):
    """A refused table; ``reason`` is one of :data:`REASONS`, ``line`` the 1-based CSV line or 0."""

    def __init__(self, reason: str, line: int, message: str) -> None:
        if reason not in REASONS:
            raise AssertionError(f"unknown reason {reason!r}")
        super().__init__(f"line {line}: {message}" if line else message)
        self.reason, self.line = reason, line


def channel_columns(channel: str) -> list[str]:
    """The 12 columns of one channel, in table order: 11 features, then the counts cell."""
    return [*(f"{feature}_{channel}" for feature in CHANNEL_FEATURES), f"{COUNTS_FEATURE}_{channel}"]


def table_header(channel_ids) -> list[str]:
    """16 plane columns, then 12 columns per channel ID, IDs sorted (Python string order)."""
    header = [*PLANE_COLUMNS, CHANNELS_COLUMN]
    for channel in sorted(channel_ids):
        header.extend(channel_columns(channel))
    return header


def header_channel_ids(header: list[str]) -> tuple[str, ...] | None:
    """The IDs named by the ``Histogram_ValidPixelCount_<ID>`` columns (HV2), or None if the
    header is not exactly :func:`table_header` of them."""
    prefix = f"{ID_FEATURE}_"
    ids = [name[len(prefix):] for name in header[LEADING:] if name.startswith(prefix)]
    if not ids or len(set(ids)) != len(ids) or any(not i or ";" in i for i in ids):
        return None
    if header != table_header(ids):
        return None
    return tuple(sorted(ids))


def _int(text: str, what: str, line: int, minimum: int = 0) -> int:
    if not text or not text.isascii() or not text.isdigit() or (len(text) > 1 and text[0] == "0"):
        raise PlaneHistogramsError("channel_value", line, f"{what} {text!r} is not a decimal integer")
    value = int(text)
    if value < minimum:
        raise PlaneHistogramsError("channel_value", line, f"{what} {value} is below {minimum}")
    return value


def read_text(text: str) -> dict[str, dict[str, list[int] | None]]:
    """Check a whole table; return ``{plane_id: {channel: dense counts, or None if absent}}``."""
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        raise PlaneHistogramsError("file_empty", 0, "the file is empty")
    header, body = rows[0], rows[1:]
    if "schema_version" in header and body:
        index = header.index("schema_version")
        if index < len(body[0]) and body[0][index] in EARLIER_VERSIONS:
            raise PlaneHistogramsError(
                "schema_version_refused", 2,
                f"schema version {body[0][index]} is refused: this reader reads version 6 only; "
                "recompute the table with the preprocessing brick (no converter, ADR 0008 / AR10)",
            )
    if tuple(header[: len(PLANE_COLUMNS)]) != PLANE_COLUMNS or header[len(PLANE_COLUMNS):LEADING] != [CHANNELS_COLUMN]:
        raise PlaneHistogramsError("header", 1, "the plane columns or the presence column are not those of version 6")
    ids = header_channel_ids(header)
    if ids is None:
        raise PlaneHistogramsError("header", 1, "the per-channel columns are not 12 per channel ID, IDs sorted, ending with Histogram_Counts_<ID>")
    out: dict[str, dict[str, list[int] | None]] = {}
    table_bins: int | None = None
    for line, row in enumerate(body, 2):
        if len(row) != len(header):
            raise PlaneHistogramsError("row_width", line, f"{len(row)} cells, the header has {len(header)}")
        meta = dict(zip((*PLANE_COLUMNS, CHANNELS_COLUMN), row[:LEADING]))
        version = meta["schema_version"]
        if version != SCHEMA_VERSION:
            reason = "schema_version_refused" if version in EARLIER_VERSIONS else "schema_version_unknown"
            raise PlaneHistogramsError(reason, line, f"schema version {version!r}; this reader reads 6 only")
        present = meta[CHANNELS_COLUMN].split(";") if meta[CHANNELS_COLUMN] else []
        if not present or len(set(present)) != len(present) or any(c not in ids for c in present) \
                or meta["channel_count"] != str(len(present)):
            raise PlaneHistogramsError("channels_cell", line, f"channels {meta[CHANNELS_COLUMN]!r} against channel_count {meta['channel_count']!r} and header IDs {ids}")
        try:
            bins = _int(meta["bin_count"], "bin_count", line, minimum=1)
        except PlaneHistogramsError as error:
            raise PlaneHistogramsError("bin_count", line, str(error)) from None
        if table_bins is None:
            table_bins = bins
        elif bins != table_bins:
            raise PlaneHistogramsError("bin_count_differs", line, f"bin_count {bins}; the table's first row has {table_bins} (one bin count per table)")
        planes: dict[str, list[int] | None] = {}
        for k, channel in enumerate(ids):
            cells = row[LEADING + k * PER_CHANNEL: LEADING + (k + 1) * PER_CHANNEL]
            if channel not in present:
                filled = [name for name, value in zip(channel_columns(channel), cells) if value != ""]
                if filled:
                    raise PlaneHistogramsError("absent_has_value", line, f"channel {channel} is absent, but {', '.join(filled)} hold a value (absent is blank, never `empty`, 0 or NaN)")
                planes[channel] = None
                continue
            valid = _int(cells[2], f"{ID_FEATURE}_{channel}", line)
            under = _int(cells[5], f"Histogram_UnderflowCount_{channel}", line)
            over = _int(cells[8], f"Histogram_OverflowCount_{channel}", line)
            try:
                pairs = sparse.parse(cells[11], bins)
                sparse.check_sum(pairs, valid, under, over)
            except sparse.SparseCountsError as error:
                raise PlaneHistogramsError(error.reason, line, f"{COUNTS_FEATURE}_{channel}: {error}") from None
            planes[channel] = sparse.to_dense(pairs, bins)
        if meta["plane_id"] in out:
            raise PlaneHistogramsError("duplicate_plane", line, f"plane {meta['plane_id']} has a second row")
        out[meta["plane_id"]] = planes
    if not out:
        raise PlaneHistogramsError("no_rows", 0, "the table has a header but no rows")
    return out


def read_file(path: str | Path) -> dict[str, dict[str, list[int] | None]]:
    """:func:`read_text` of a UTF-8 file, read in binary so line ends are not translated."""
    return read_text(Path(path).read_bytes().decode("utf-8"))
