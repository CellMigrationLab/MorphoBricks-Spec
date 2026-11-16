"""Reference codec of the shared sparse histogram-counts grammar (``docs/sparse-counts.md``).

One definition for every table that stores bin counts sparsely: ``window_histograms.csv``
(ADR 0004 EW11, column ``counts``) and, if the owner accepts ADR 0008, ``plane_histograms.csv``
schema version 6 (column ``Histogram_Counts_<ID>``). Pure Python, standard library only; no brick
imports it. The normalization brick implements its own codec and reproduces the golden cases of
``tools/test_sparse_counts.py``.
"""

from __future__ import annotations

from collections.abc import Sequence

EMPTY = "empty"
PAIR_SEPARATOR = ";"
INDEX_SEPARATOR = ":"
MAX_COUNT = 2**63 - 1
_DIGITS = frozenset("0123456789")


class SparseCountsError(ValueError):
    """A cell that breaks the grammar, or counts that break the sum rule.

    ``reason`` is one of :data:`REASONS`; the message says what is wrong.
    """

    def __init__(self, reason: str, message: str) -> None:
        if reason not in REASONS:
            raise AssertionError(f"unknown reason {reason!r}")
        super().__init__(message)
        self.reason = reason


REASONS = (
    "counts_blank",        # a blank cell where the table requires counts
    "counts_syntax",       # not `empty`, or not pairs of ASCII decimal integers joined by `;` and `:`
    "counts_leading_zero",  # an index other than `0`, or any count, written with a leading zero
    "counts_zero",         # a pair with count 0 (zero bins are not written)
    "counts_too_large",    # a count above 2**63 - 1
    "counts_order",        # indices not strictly increasing (unordered or repeated)
    "counts_index_range",  # an index >= bin_count
    "counts_sum",          # the counts do not sum to valid - underflow - overflow
)


def _decimal(text: str, what: str, cell: str) -> int:
    if not text or not set(text) <= _DIGITS:
        raise SparseCountsError("counts_syntax", f"{what} {text!r} in {cell!r} is not an ASCII decimal integer")
    if len(text) > 1 and text[0] == "0":
        raise SparseCountsError("counts_leading_zero", f"{what} {text!r} in {cell!r} has a leading zero")
    return int(text)


def parse(cell: str, bin_count: int) -> list[tuple[int, int]]:
    """Return the ``(index, count)`` pairs of ``cell``; ``[]`` for ``empty``.

    Checks the grammar only: the sum rule needs the histogram's other cells (:func:`check_sum`).
    """
    if isinstance(bin_count, bool) or not isinstance(bin_count, int) or bin_count < 1:
        raise ValueError(f"bin_count must be a positive integer, got {bin_count!r}")
    if cell == "":
        raise SparseCountsError("counts_blank", "the counts cell is blank")
    if cell == EMPTY:
        return []
    pairs: list[tuple[int, int]] = []
    previous = -1
    for part in cell.split(PAIR_SEPARATOR):
        index_text, sep, count_text = part.partition(INDEX_SEPARATOR)
        if not sep or INDEX_SEPARATOR in count_text:
            raise SparseCountsError("counts_syntax", f"{part!r} in {cell!r} is not one index:count pair")
        index = _decimal(index_text, "index", cell)
        count = _decimal(count_text, "count", cell)
        if count == 0:
            raise SparseCountsError("counts_zero", f"bin {index} in {cell!r} has count 0; zero bins are not written")
        if count > MAX_COUNT:
            raise SparseCountsError("counts_too_large", f"bin {index} in {cell!r} has a count above 2**63 - 1")
        if index <= previous:
            raise SparseCountsError("counts_order", f"index {index} in {cell!r} does not follow {previous}: indices must be strictly increasing")
        if index >= bin_count:
            raise SparseCountsError("counts_index_range", f"index {index} in {cell!r} is not below bin_count {bin_count}")
        pairs.append((index, count))
        previous = index
    return pairs


def check_sum(pairs: Sequence[tuple[int, int]], valid: int, underflow: int, overflow: int) -> None:
    """Refuse pairs whose counts do not sum to ``valid - underflow - overflow``."""
    total = sum(count for _, count in pairs)
    expected = valid - underflow - overflow
    if total != expected:
        raise SparseCountsError(
            "counts_sum",
            f"the counts sum to {total}, but valid - underflow - overflow = {valid} - {underflow} - {overflow} = {expected}",
        )


def to_dense(pairs: Sequence[tuple[int, int]], bin_count: int) -> list[int]:
    """The dense counts: ``bin_count`` integers, zero where no pair names the bin."""
    dense = [0] * bin_count
    for index, count in pairs:
        dense[index] = count
    return dense


def format_dense(dense: Sequence[int]) -> str:
    """The one cell text of dense counts (canonical: one text per count vector)."""
    pairs = []
    for index, count in enumerate(dense):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > MAX_COUNT:
            raise ValueError(f"bin {index}: a count is an integer in [0, 2**63 - 1], got {count!r}")
        if count:
            pairs.append(f"{index}{INDEX_SEPARATOR}{count}")
    return PAIR_SEPARATOR.join(pairs) if pairs else EMPTY
