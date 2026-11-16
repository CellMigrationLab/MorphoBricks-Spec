# Sparse histogram counts: the shared cell grammar

- **Status:** Normative for `window_histograms.csv` (ADR 0004 EW11, accepted; its column `counts`),
  whose text it was first written in (owner, 15 November 2026). Moved here so that it is defined
  once; the EW11 rules are kept word for word in meaning, and the two points EW11 left implicit are
  listed in §6 as **proposed clarifications**. Its second use, `plane_histograms.csv` schema version 6
  (`Histogram_Counts_<ID>`), is **proposed** in [ADR 0008](adr/0008-plane-histograms-v6.md) and is
  not in force until the owner accepts it.
- **Reference codec:** [`tools/sparse_counts.py`](../tools/sparse_counts.py), golden cases in
  [`tools/test_plane_histograms_v6.py`](../tools/test_plane_histograms_v6.py) (class `Grammar`).
  No brick imports it; each brick implements its own codec and reproduces the cases.

## 1. Grammar

A **sparse counts cell** holds the bin counts of one histogram with `bin_count` bins. It is either
the literal `empty` (no pixel in a bin), or one or more pairs `index:count` joined by `;`:

```text
cell   = "empty" / pair *( ";" pair )
pair   = index ":" count
index  = "0" / nonzero *DIGIT        ; no leading zero
count  = nonzero *DIGIT               ; positive, no leading zero
nonzero = "1"-"9"
DIGIT  = "0"-"9"                      ; ASCII only
```

- The indices are **strictly increasing** (no repeated index) and each lies in `[0, bin_count)`.
- Every `count` is positive (**zero bins are not written**) and at most 2^63 − 1 (§6).
- No spaces, signs, other separators, other digits (only ASCII `0`-`9`, §6), other spellings of
  `empty` (`EMPTY`, `Empty`, `0`) or a trailing or leading `;`.
- Bin *i* has the meaning the table gives it (for both tables: the bin of the row's `bin_count`,
  `binning_min` and `binning_max`; for an exact integer histogram, the value `binning_min + i`).
  The grammar does not change what a bin means.

## 2. Canonical: one text per histogram

The cell is a function of the dense counts: a writer writes `empty` exactly when every bin is 0,
and otherwise the pairs of every non-zero bin, in index order, each number in its shortest decimal
form. Two writers of the same histogram write the same bytes, so a table's SHA-256 is as
deterministic as with dense columns.

## 3. Reader checks

A reader refuses a cell that breaks §1 and checks, against the same histogram's other cells, that

> the counts sum to `valid − underflow − overflow`

where `valid` is the histogram's valid (finite) pixel count and `underflow`, `overflow` its tail
counts. `empty` therefore means *measured, with no pixel in any bin*; it passes only when
`valid − underflow − overflow = 0`.

## 4. Blank is not part of the grammar

A **blank** cell is not a sparse counts cell. Whether a blank is allowed, and what it means, is the
table's rule, never this grammar's, and a blank is never read as `empty` or as zero counts:

| Table | Blank `counts` cell | `empty` |
| --- | --- | --- |
| `window_histograms.csv` (ADR 0004 EW11) | Required in a `not_measured` row; refused in a `measured` row | A measured window with no pixel in a bin |
| `plane_histograms.csv` v6 (ADR 0008, proposed) | Required for a channel the row does not list in `channels` (**absent**, ADR 0003 HV1); refused for a listed channel | A listed (measured) channel with no pixel in a bin, for example a float plane with no finite pixel |

## 5. Column names per table

| Table | Cell | `valid` | `underflow` | `overflow` |
| --- | --- | --- | --- | --- |
| `window_histograms.csv` | `counts` | `valid_pixel_count` | `underflow_count` | `overflow_count` |
| `plane_histograms.csv` v6 | `Histogram_Counts_<ID>` | `Histogram_ValidPixelCount_<ID>` | `Histogram_UnderflowCount_<ID>` | `Histogram_OverflowCount_<ID>` |

## 6. Proposed clarifications (with ADR 0008; owner decision pending)

The EW11 text says "decimal integer" and sets no upper bound. Two readings are made explicit here;
they refuse nothing that a writer following EW11 would write:

1. **Digits are ASCII `0`-`9` only.** A reader must not accept other Unicode decimal digits (Python's
   `str.isdigit` and `int` accept `٠` or `１`).
2. **A count is at most 2^63 − 1**, the bound of the dense in-memory counts (normalization's
   `int64`; version 5 already refuses a larger bin count with "a bin count is larger than 2**63 - 1").
