# ADR 0008: `plane_histograms.csv` schema version 6 (sparse counts), proposed

- **Status:** **Proposed. Owner decision pending.** Nothing here is in force: version 5
  ([ADR 0003](0003-plane-histograms-v5.md)) stays the format until the owner accepts this ADR, and
  no brick may write or read version 6 before then. This draft states what version 6 would be, so
  the owner decides on exact text.
- **Evidence:** morphobricks-normalization draft PR #107 (not for merge), head
  `6aac296e24f07432084cc588dc0fc204de0fbd5e`, `experiments/histogram_storage_study/README.md` and
  `results.md` (study D9, 16 November 2026), measured on normalization `9616e12` (v0.7.0 + #104)
  with preprocessing `ce650e3`, this repository at `1167108`, CellPatcher `e0e56bc`, MorphoFeature
  `7ac7487`. Line numbers below are of that README.
- **Amends, if accepted:** ADR 0003 HV2 (the bin-index-from-header rule) and HV4 (the version
  number); HV1 and HV3 are unchanged. ADR 0004 EW11 is unchanged in meaning: its sparse `counts`
  grammar now lives in [`docs/sparse-counts.md`](../sparse-counts.md), and both tables cite it.
- **Where the format text lives:** as for version 5 (ADR 0003, "Where the format text lives"),
  the normalization brick's contract (§6.1, §6.2, N42) holds the table's text; this ADR binds it.
  Unlike ADR 0003, it ships golden tables and a reference checker
  (`tools/plane_histograms_v6/`, `tools/plane_histograms_v6.py`), outside the pinned `fixtures/`
  tree (open question 4).

## Context

Version 5 stores one text cell per bin: `Histogram_Count_<ID>_<NNNNN>`, 65,536 columns per
16-bit channel, a 131,110-column header for two channels (README L3-5). The study measured, on
the normalization brick's own functions and four datasets (synthetic 12-bit-in-16 range from
preprocessing PR #318, CMU-1 uint8 RGB, HPMEC uint16, JUMP full-range uint16; README L57-70):

- a plane uses 1.7 % (study), 4.1 % (HPMEC) and 34 % (JUMP) of the 65,536 bins (README L74-79);
- a sparse cell per channel in the ADR 0004 grammar is **16× (study) to 44× (HPMEC) smaller** and
  12× to 27× faster to write; preprocessing's staging cycle goes from 2.7 s to 0.11 s on the PR
  #318 data and from 0.86 s to 0.02 s on HPMEC (README L119-137, L276-277). On full-range 16-bit
  data (JUMP) it is **only 1.4× smaller and 1.4× faster** (README L134, L280-282); uint8 is 0.9×
  (dense 58 KiB, sparse 63 KiB; README L138-139);
- every format read back to the same `PlaneRecord`s, and **0 bit differences** over 6,515 numbers
  (every fit, summary, check and warning) per format (README L166-185);
- coarse bins (4,096 or 1,024) change user-visible decisions on real 16-bit data (32 of 90 JUMP
  saturated fractions blank, every group flagged inexact, robust z-score scales off by 6-60 %, one
  fit refused, one new warning; README L187-259), so the bins stay exact and only their storage
  changes.

## Proposed decisions (owner decision pending)

| # | Proposed decision | Rejected alternative | Spec | Fixtures |
|---|---|---|---|---|
| PV1 | **Version 6 is version 5 with the per-bin columns replaced by ONE sparse cell per channel**, `Histogram_Counts_<ID>`, placed after that channel's 11 feature columns. Its text follows the **shared grammar** of [`docs/sparse-counts.md`](../sparse-counts.md) exactly (the grammar of ADR 0004 EW11, defined once there; this ADR does not restate it). Bin *i* keeps its version 5 meaning (`Histogram_BinningMin + i` for an exact integer histogram) | Keep version 5 (the 2.7 s staging cycle and 13-20 MiB tables of the study, README L123, L133); coarse bins (change decisions, README L234-259); long Parquet (3.8× smaller on JUMP but a 170 MB `pyarrow` core dependency in normalization, preprocessing, CellPatcher and MorphoFeature, a file-name change and an untested byte-determinism across `pyarrow` versions, README L280-290, L353-360); trimmed `.npz` or zarr (binary, not readable, NumPy- or directory-specific, README L291-296); `.csv.gz` (2.1-2.8× on sparse tables, changes the file name, README L375-377) | normalization contract §6.1, §6.2 (brick text, amended in its PR) | `pv01`-`pv04` |
| PV2 | **Reader checks of the cell**, for every channel the row lists in `channels`: the grammar (ASCII digits, no leading zero, no sign or space, `empty` exactly so spelled); indices **strictly increasing** and **below `bin_count`**; **no zero count written**; counts **sum to `valid − underflow − overflow`** (`Histogram_ValidPixelCount_<ID>` − `Histogram_UnderflowCount_<ID>` − `Histogram_OverflowCount_<ID>`), the check normalization's `integrity.py` already makes on dense counts. The other per-channel invariants of version 5 are unchanged | Accepting non-canonical text (leading zeros, zero pairs, unordered pairs) and normalizing it: two texts for one histogram break the table's SHA-256 identity in the run manifest and EW11's `reference_sha256` | `docs/sparse-counts.md` §1-§3 | `pi03`-`pi13`, `pi15`-`pi17`, `pi19`, `pi20` |
| PV3 | **`empty` and blank stay distinct (HV1 kept).** `empty` = a **measured** channel (listed in `channels`) with no pixel in any bin, e.g. a float plane with no finite pixel. **Blank** = the channel is **absent** from the plane: all 12 of its cells blank, and any value there (`empty`, `0:0`, a number) is refused. A blank counts cell for a listed channel is refused, never read as `empty` | One spelling for both (absent would again look like measured-zero, the confusion HV1 removed) | ADR 0003 HV1; `docs/sparse-counts.md` §4 | `pv02`, `pv03`; `pi12`, `pi13`, `pi14`, `pi21` |
| PV4 | **HV2 amended: the bin-index-from-header rule goes.** No column carries a bin index. The IDs still come from the `Histogram_ValidPixelCount_<ID>` columns (an ID may contain `_`). The header is exactly **16 + 12 × (number of channel IDs)** columns (the 15 plane columns and `channels`; per ID, sorted, 11 features and `Histogram_Counts_<ID>`), **independent of `bin_count`** (verified: `csv_io.METADATA_COLUMNS` has 15 entries and `CHANNEL_FEATURES` 11 at normalization `9616e12`, L65-81 and L87-99; the study states the same count, README L278, L315). Because the header no longer fixes the bin count, **one `bin_count` per table** (the version 5 writer's rule, `write_plane_histograms`: "all use the same bin count") becomes an explicit row check | Keeping a per-bin header (the study's cost) | ADR 0003 HV2; normalization contract §6.1 | `pv01`, `pv03` (ID `PAX_488`); `pi02`, `pi18`, `pi22` |
| PV5 | **HV4 for version 6: `schema_version` = `6`; a version 6 reader refuses version 5 (and 1-4) by that value**, naming version 6 and the fix (recompute the table with the preprocessing brick). **No converter** and no reader of both versions (ADR 0002 AR10) | A v5→v6 converter (lossless here, but AR10 forbids converters; the run's other digests change anyway) | ADR 0003 HV4; ADR 0002 AR10 | `pi01` |
| PV6 | **Unchanged:** `bin_count` and the meaning of a bin; one row per XYC plane (N41); the presence column `channels` and HV3 (a failed measurement fails the whole table); the in-memory `PlaneHistogram` with dense counts; pooling, `fit`, summaries and checks (bit-identical, README L166-185); the default bin counts (`dtypes.default_bin_count`: one bin per value for 8- and 16-bit, so histograms stay exact); the file name `plane_histograms.csv`; row order, number formatting, UTF-8, the atomic write; ADR 0004 EW11 `window_histograms.csv` (it uses the plane's `bin_count` and binning limits, which version 6 keeps) | - | ADR 0003; ADR 0004 EW11 | the bit-identity table of the study |

## Migration, per brick (if accepted)

From the study (README L329-352), checked against `main` of each brick at the commits above:

- **morphobricks-normalization** (the only code change): in `csv_io.py`, `SCHEMA_VERSION` (`"5"`
  → `"6"`, L62), `_EARLIER_VERSIONS` (+ `"5"`, L105) and `_earlier_version_message`,
  `table_header` (L146) and `header_channels` (L158: no bin count from the header), `_row` (L356),
  `_record` / `_histogram` (L398, L506: parse the sparse cell) and `_check_absent` (L488). A
  **shared codec** (`sparse_counts_text` / `parse_sparse_counts` in the study's naming) used by
  both tables, reproducing `tools/test_plane_histograms_v6.py` (class `Grammar`). The contract §6.1,
  §6.2 and N42 text, CHANGELOG, tests, and its version 5 test tables rewritten as version 6.
- **preprocessing**: no production code of its own reads the bin columns (staging
  `run/staging.py`, reuse `run/reuse.py`, `RunInputs` and the notebook go through normalization's
  `write_plane_histograms` / `read_plane_histograms` / `read_plane_histogram_table`). Changes: the
  normalization pin; the byte goldens (`tests/test_run_workers_bytes.py`, the Spec fixture
  trees) and the table SHA-256 in `run_manifest.json` (a new file, a new digest, as intended);
  **one test reads the bin columns directly** (`tests/test_histogram_goldens.py` L113, L124:
  `schema_version == "5"` and `Histogram_Count_<ID>_<NNNNN>`), and docstrings that say "schema
  version 5" (`run_inputs.py` L476, `run_labels.py` L3, `channel_plan.py` L7, `run/rows.py` L38,
  `size_checks.py` L93). Runs written with version 5 are recomputed (PV5); resume and reuse already
  refuse a table they cannot read.
- **CellPatcher**: no parsing of its own (the table is opened through `RunInputs`, `run_open.py`,
  catching `CsvFormatError`). Changes: the preprocessing and normalization pins, the test runs that
  hold version 5 tables, the user message for a version 5 run (recompute), docstrings
  (`statistics.py` L201).
- **MorphoFeature**: the same, through `RunInputs` (`histogram_fit.py`). Changes: the pins,
  `tests/test_earlier_runs_refused.py` (L42 asserts `SCHEMA_VERSION == "5"`, L75 the rows'
  version), the docstring of `histogram_fit.py` L20.
- **This repository**: ADR 0003 gets a pointer; the conformance plan's "Histogram table v5" row
  becomes "v6" (one row per plane, the sparse cell, the refusals of PV2-PV5).
- **Window histograms (EW11)**: not implemented yet. Its `reference_sha256` is the SHA-256 of
  `plane_histograms.csv`, so a window table made against a version 5 table no longer matches a
  recomputed version 6 table (`plane_histogram_mismatch`) and is recomputed with it.

## Open questions for the owner (recommendation first)

1. **Accept version 6 with the sparse cell (PV1-PV6)?** Recommended: **yes**, as the next
   normalization change after #104, with one shared codec for both tables. It changes no number
   (0 bit differences) and gives 16-44× on partial-range 16-bit data.
2. **Full-range 16-bit (JUMP-like) data gains only 1.4×; is it the main load?** Recommended:
   decide from the lab's cameras; if yes, vectorise the sparse formatter inside normalization (no
   format change) before reconsidering Parquet (README L280-290, L372-374).
3. **One `bin_count` per table (PV4)?** Recommended: **yes**, keep version 5's rule as an explicit
   row check. Allowing a bin count per row would be a new meaning (mixed uint8 and uint16 planes in
   one table) and needs its own decision.
4. **Where the golden tables live.** Recommended: keep them under `tools/plane_histograms_v6/`
   (like EW11's golden cases) and let normalization reproduce them; moving them into `fixtures/`
   would change every brick's pinned tree for a table that is not part of experiment-v1.
5. **The two grammar clarifications** (`docs/sparse-counts.md` §6: ASCII digits only; a count at
   most 2^63 − 1). Recommended: **accept**; they apply to EW11 too and refuse nothing a conforming
   writer writes.
6. **Compress (`.csv.gz`)?** Recommended: **no** (README L375-377).

## Not decided here

How old installs word their refusal of a version 6 table (as for version 5, an implementation
detail); the release numbers of the bricks.
