# ADR 0008: plane histograms schema version 6 (`plane_histograms.parquet`), proposed

- **Status:** **Proposed**, revised after the external review of 18 November 2026 (ACCEPT AFTER
  CHANGES). The owner decided on 17 November 2026 (open questions below): **keep exact bins**;
  version 6 **as Parquet** (not the sparse-count CSV cell of the first draft), **one row per plane
  with two list columns per channel** (Q4); **the content digest is the identity and the file
  SHA-256 is for integrity** (Q2); **`pyarrow>=18`, no upper bound, imported lazily** (Q3; the
  review challenges it, so it goes back to the owner); **limits as version 5's text** (Q7); EW11's
  grammar unchanged. The recommendations of Q5, Q6 and Q8 stand. The owner also stated that
  **full-range 16-bit data (JUMP-like) is common**, so the format is designed for it. Nothing here
  is in force until the owner accepts this text: version 5 ([ADR 0003](0003-plane-histograms-v5.md))
  stays the format, and no brick may write or read version 6 before then.
- **Evidence:** morphobricks-normalization draft PR #107 (not for merge), head
  `6aac296e24f07432084cc588dc0fc204de0fbd5e`, `experiments/histogram_storage_study/README.md` and
  `results.md` (study D9, 16 November 2026), measured on normalization `9616e12` (v0.7.0 + #104)
  with preprocessing `ce650e3`, this repository at `1167108`, CellPatcher `e0e56bc`, MorphoFeature
  `7ac7487`; and, for the Parquet choices below, this PR's probe and golden tables (§Evidence).
  The current v5 writer and reader were read at normalization `main` `fcfaeac` (v0.7.1).
- **Amends, if accepted:** ADR 0003 HV2 (the bin-index-from-header rule, the per-bin columns) and
  HV4 (the version number and the file); HV1 and HV3 are kept with a Parquet representation (PQ3).
  ADR 0004 EW11: its sparse `counts` grammar and window-table schema are **unchanged** (they stay
  where they were merged, #44). Two things change: its pointer to the plane table (the version 6
  table), and **the meaning of `reference_sha256`**, which becomes the plane table's content digest
  ([normative clause](#ew11s-reference-digest-normative-supersedes-adr-0004-ew11-on-this-point)).
  ADR 0004's own text is amended in a later PR, at these places, stale once this ADR is accepted:
  L171 and L186 (`plane_histograms.csv`, schema version 5), L174 (the reference identity as "the
  table's SHA-256 (`csv_sha256` of the preprocessing `run_manifest.json`)"), L625 (`reference_sha256`
  as "the SHA-256 of `plane_histograms.csv`") and L742 (a "SHA-256 mismatch").
- **Where the format text lives:** as for version 5 (ADR 0003, "Where the format text lives"),
  the normalization brick's contract (§6.1, §6.2, N42) holds the table's text; this ADR binds it.
  Unlike ADR 0003, it ships golden tables and a reference checker (`tools/plane_histograms_v6/`,
  `tools/plane_histograms_v6.py`), outside the pinned `fixtures/` tree (open question 5).

## Context

Version 5 stores one text cell per bin: `Histogram_Count_<ID>_<NNNNN>`, 65,536 columns per
16-bit channel, a 131,110-column header for two channels. The study measured, on the
normalization brick's own functions and four datasets (synthetic 12-bit-in-16, CMU-1 uint8 RGB,
HPMEC uint16, JUMP full-range uint16):

- a plane uses 1.7 % (study), 4.1 % (HPMEC) and **34 % (JUMP)** of the 65,536 bins;
- exact formats read back bit for bit (0 differences over 6,515 numbers per format), while coarse
  bins (4,096 or 1,024) change user-visible decisions on real 16-bit data (32 of 90 JUMP saturated
  fractions blank, every group flagged inexact, robust z-score scales off by 6-60 %, one fit
  refused, one new warning). The owner kept exact bins;
- the sparse CSV cell of the first draft is 16-44× smaller on partial-range data but **only 1.4×
  on full-range 16-bit (JUMP)**, which the owner now calls common. The study's **long** Parquet
  layout (one row per plane, channel and non-zero bin; **not** PQ2's list layout) is **58× (study),
  91× (HPMEC) and 3.8× (JUMP)** smaller than version 5, and on JUMP 3.5× faster to write and
  6.8× faster to read (§Evidence). These figures are long-layout evidence: PQ2 itself is measured
  only on this PR's synthetic full-range probe. Its costs, named by the study, are a `pyarrow` dependency
  (about 170 MB, 0.15 s import), a new file name, and bytes that are not deterministic across
  `pyarrow` versions (untested by the study; tested here, PQ6).

## Proposed decisions (owner decision pending)

| # | Proposed decision | Rejected alternative | Spec | Golden tables |
|---|---|---|---|---|
| PQ1 | **Version 6 is one Parquet file, `plane_histograms.parquet`**, written by the normalization brick in place of `plane_histograms.csv`. The bins stay **exact**: `bin_count`, the meaning of a bin (`Histogram_BinningMin + i` for an exact integer histogram) and the default bin counts (`dtypes.default_bin_count`: one bin per value for 8- and 16-bit) are those of version 5. Only the storage changes | Coarse bins (rejected by the owner; they change decisions); the sparse `index:count` CSV cell of the first draft (1.4× on full-range 16-bit data, a Python string per pair); trimmed `.npz` or zarr (NumPy-specific, a directory of files for zarr, slowest per-image writes); `.csv.gz` (2.1-2.8× only) | normalization contract §6.1, §6.2 | `pv01`-`pv06` |
| PQ2 | **Layout: one row per XYC plane (HV1, N41 kept), the version 5 columns, and two list columns per channel ID instead of the per-bin columns.** Columns, in this order: the 15 plane columns of version 5 and `channels`; then, for every channel ID of the description, **sorted**, its 11 feature columns and `Histogram_Bins_<ID>` (the indices of the non-zero bins) and `Histogram_Counts_<ID>` (their counts): **16 + 13 × (number of IDs)** columns, independent of `bin_count`. The types are fixed (table below); the IDs still come from `Histogram_ValidPixelCount_<ID>` (an ID may contain `_`, HV2); no column carries a bin index | **Long/tidy** (one row per plane × channel × non-zero bin, the study's layout): a row is no longer a plane (N41 reversed, as ADR 0003 HV1 (B) rejected); the plane and feature values need a second table or key-value metadata (the study put CSV text there); a measured channel with no pixel has no row at all, so absent and empty differ only through `channels`; and it is larger on JUMP-like data (5,161 KiB against 3,324 KiB in the probe). A `list<struct<index, count>>` column (nulls at two levels to rule out); a dense fixed-size list (65,536 values per channel again) | ADR 0003 HV1, HV2; normalization contract §6.1 | `pv01`, `pv03` (ID `PAX_488`); `pi05`, `pi06` |
| PQ3 | **Absent ≠ measured-empty, natively (HV1 kept).** **Absent** (the row's `channels` does not list the ID): **all 13 columns of the ID are null**; any value there, `[]` or `0` included, is refused. **Measured with no pixel in any bin** (for example a float plane with no finite pixel): `Histogram_Bins_<ID>` = `Histogram_Counts_<ID>` = **`[]`** (empty, not null), with the counts and tails of version 5. A listed channel whose lists (or count, tail columns) are null is refused, never read as empty | One spelling for both (absent would look like measured-zero again, the confusion HV1 removed); reading null lists of a listed channel as empty | ADR 0003 HV1 | `pv02`, `pv03`; `pi15`, `pi16`, `pi17`, `pi18` |
| PQ4 | **Reader checks** (every rule a refusal, never a repair): it is a Parquet file; the column names, order and **types** are exactly PQ2's; `schema_version` is 6 (PQ7); no plane column is null; `channels` names distinct header IDs and `channel_count` equals their number; **one `bin_count` per table** (version 5's writer rule, now a row check because the header no longer fixes it); `plane_id` unique; PQ3; for every listed channel: both lists non-null, **of equal length**, **no null element**, indices **strictly increasing** and in **`[0, bin_count)`**, counts **positive** (zero bins are not written), and counts **sum to `valid − underflow − overflow`** (the check `integrity.py` already makes on dense counts); tail means and stds finite and never `-0.0`. **Every check of version 5 as well:** the reader rebuilds version 5's `PlaneRecord` and `PlaneHistogram` (dense counts) from each row and runs all of their checks (normalization v0.7.1 `integrity.py`, `records.py`, `dtypes.py`, `channels.py` and the v5 reader's row checks): valid ≤ total pixels; a channel without a valid pixel has no limits and empty tails; otherwise four limits present, finite and ordered (minimum ≤ binning minimum ≤ binning maximum ≤ maximum), a tail exactly where a limit lies inside its extremum, an empty tail with mean and std 0, and tail moments possible for their range; the limits' canonical text and the dtype's `bin_count` range (types table); a supported dtype with its `bit_depth`; `plane_id` and `image_file` equal to what path, z and t give; z, t ≥ 0 and a non-blank `position_id`; **one channel list per image** (every plane of a source file); channel IDs that follow the Token rule. **A table that fails any check has no content digest** (PQ6) | Accepting non-canonical lists (unordered pairs, zero counts) and normalizing them: two encodings of one histogram would give two content digests (PQ6); checking only what version 6 changes (a table version 5 refuses would pass) | normalization contract §6.2; the v5 checks at normalization `fcfaeac` | `pi03`-`pi36` |
| PQ5 | **Writer.** The normalization writer is **vectorised** (D8): per channel `index = np.flatnonzero(counts)` on the dense counts it already holds (themselves from `np.bincount`-style counting) and `counts[index]`; the list columns are built from the concatenated arrays and their offsets (`pyarrow.ListArray.from_arrays`); **no per-bin or per-pair Python loop** in the writer or the reader (the reader fills `dense[bins] = counts`, checks order with `np.diff`). It keeps version 5's rules: rows in the order given, `-0.0` written as `0.0` (#105), refuses mixed bin counts, writes atomically (temporary file, `os.replace`), and a failed measurement writes nothing (HV3). **Fixed writer profile**, so one environment writes the same bytes: `compression="zstd"` (level 3), dictionary encoding on, statistics off, page checksums on, no stored Arrow schema, **row groups of at most 32,767 rows**, one row group for a table of up to 32,767 rows, the split fixed by that rule so one environment still writes the same bytes. A list column holds at most 65,536 elements per row, so one row group's column is at most 32,767 × 65,536 = 2^31 − 65,536 elements and always fits `list`'s int32 offsets (never `large_list`; types table). Several row groups are required beyond that size, because `pyarrow`'s Parquet reader does not split a nested column of one row group into chunks on read; the content digest ignores row groups (PQ6). **No meaning in key-value metadata**: nothing is written there and a reader ignores it | A per-pair formatter in Python (the first draft's cost on JUMP: 470 ms for 90 planes); writer options left to `pyarrow` defaults (they change between releases) | normalization contract §6.2 | `make_tables.py` (`PROFILE`) |
| PQ6 | **Identity is a content digest, not the file's bytes.** `content_sha256` = SHA-256 of the **canonical serialisation of the decoded, checked table** (below). The **run manifest records two digests**: the file's byte SHA-256 (**integrity**: this file is the one the run wrote; publication, `RunInputs` and reuse keep comparing it, as today) and `content_sha256` (**identity**: what serial, parallel, resumed and re-run tables, other platforms and other `pyarrow` versions must share; what consumers record as provenance; what EW11's `reference_sha256` holds, PQ9). Serial, parallel and resumed runs in **one environment** write identical bytes (PQ5) and conformance tests check both; across environments only `content_sha256` is compared. A table that fails PQ4 has no content digest | **Pinned bytes** (pin `pyarrow` to one exact release and every writer option, then rely on file bytes): the bytes change with every `pyarrow` release (`created_by` and the data pages: every golden table here has other bytes under `pyarrow` 18.1.0 and 26.0.1 with the same profile, `pv05` 40,184 against 40,576 bytes); byte equality across platforms would still need proof per release; one exact pin in four bricks plus the optional extras of MorphoFeature and MorphoRelate; and every upgrade would change every byte golden and manifest digest | normalization contract §6.2; preprocessing contract §9 (manifest) | `pv06` (= `pv01`'s content, other bytes); every valid table's digest in the catalogue |
| PQ7 | **HV4 for version 6: `schema_version` = 6 (int64) in every row. A version 6 reader refuses version 5 (and 1-4) by that value**: given a `plane_histograms.csv`, it reads the CSV header and first row only to find `schema_version`, and refuses it naming version 6 and the fix (recompute the table with the preprocessing brick); a Parquet file with `schema_version` 5 is refused the same way; any other non-Parquet file is refused. **No converter** and no reader of both versions (ADR 0002 AR10) | A v5→v6 converter (lossless here, but AR10 forbids converters); keeping the `.csv` name for a Parquet file | ADR 0003 HV4; ADR 0002 AR10 | `pi01`, `pi02`, `pi03`, `pi04`, `pi24` |
| PQ8 | **`pyarrow` becomes required** for every brick that reads or writes plane histograms: **normalization** (a core dependency, `pyarrow>=18`), and through it **preprocessing, CellPatcher and MorphoFeature**, which declare the same minimum explicitly (MorphoFeature's `cli` extra rises from `pyarrow>=14`). **No upper bound** (owner, 17 November 2026; challenged by the review, back with the owner: open question 3): PQ6 makes the version irrelevant to identity. **Import stays inert**: `pyarrow` is imported inside the histogram read and write functions, never at package import, so `import morphobricks_normalization` and MorphoFeature's discovery do not load it. A missing `pyarrow` is an installation error naming the requirement; there is no CSV fallback | An optional extra (every route reads the table: the run would fail late); a lower floor than the oldest version tested (18 is the first release with wheels for Python 3.13, the study's interpreter; 18.1.0 is tested) | each brick's dependency list; `tools/requirements.txt` for the Spec's own tools only | the tests run under `pyarrow` 18.1.0 and 26.0.1 |
| PQ9 | **Unchanged:** one row per XYC plane (N41); the presence column and HV3; the in-memory `PlaneHistogram` with dense counts; pooling, `fit`, summaries and checks (bit-identical, study); the exact bins (PQ1); the text of the intensity and binning limits (version 5's, kept as `string`, PQ2 types). **ADR 0004 EW11 keeps its CSV `window_histograms.csv` and its sparse `counts` grammar exactly as merged**; if this ADR is accepted, EW11's references to "`plane_histograms.csv` (schema version 5)" read as the version 6 table, and its `reference_sha256` holds the table's `content_sha256` (still 64 hex characters), so a window table stays valid across environments that write other bytes ([normative clause](#ew11s-reference-digest-normative-supersedes-adr-0004-ew11-on-this-point)) | Moving EW11 to Parquet too (EW11 is accepted, unimplemented and small; nothing measured asks for it); keeping `reference_sha256` on file bytes (a re-run under another `pyarrow` would report `plane_histogram_mismatch` for the same histograms) | ADR 0003; ADR 0004 EW11 | the bit-identity table of the study |

### Column types (PQ2)

| Columns | Arrow / Parquet type | Null |
| --- | --- | --- |
| `position_id`, `image_file`, `condition`, `biological_repeat`, `technical_repeat`, `source_relative_path`, `plane_id`, `dtype`, `channels` | `string` (UTF-8) | never |
| `z`, `t`, `bit_depth`, `channel_count`, `total_pixel_count`, `bin_count`, `schema_version` | `int64`. `bin_count` follows version 5's dtype rule (normalization `dtypes.validate_bin_count`): an integer dtype 1 to min(65,536, 2^bits), a float dtype 2 to 65,536; `z`, `t` ≥ 0; `bit_depth` the dtype's bits | never |
| `Intensity_MinIntensity_<ID>`, `Intensity_MaxIntensity_<ID>`, `Histogram_BinningMin_<ID>`, `Histogram_BinningMax_<ID>` | `string`: **exactly** version 5's writer text of the value. For an integer dtype, a decimal integer inside the dtype's range (`-` the only sign, no leading zero, never `-0`); for a float dtype, the shortest round-trip `repr` of the float64 value, `0.0` for a zero of either sign (#105). The reader parses the text with the dtype and refuses any other spelling (`0100`, `+5`, `5.0` for an integer, `-0.0`, `0.10`, `1E-05`): two spellings of one value would give two content digests. A float64 column would lose integers above 2^53 of `int64`/`uint64` planes, and one column serves every dtype | where version 5 leaves the cell blank (no valid pixel), and for an absent channel |
| `Histogram_ValidPixelCount_<ID>`, `Histogram_UnderflowCount_<ID>`, `Histogram_OverflowCount_<ID>` | `int64`, ≥ 0 | absent channel only |
| `Histogram_UnderflowMean_<ID>`, `Histogram_UnderflowStd_<ID>`, `Histogram_OverflowMean_<ID>`, `Histogram_OverflowStd_<ID>` | `double`, finite, `0.0` never `-0.0` | absent channel only |
| `Histogram_Bins_<ID>` | `list<int32>` (bin indices < `bin_count` ≤ 65,536). Its offsets are int32: the PQ5 row-group limit (at most 32,767 rows) keeps every row group's column under 2^31 − 1 elements; a writer never casts to `large_list` | absent channel only; `[]` = measured, no pixel in a bin |
| `Histogram_Counts_<ID>` | `list<int64>` (positive counts) | as `Histogram_Bins_<ID>` |

`string` is not `large_string`, `list` is not `large_list`; a reader refuses another type
(`pi06`). Field nullability flags and the list item's field name carry no meaning.

### The content digest (PQ6)

`content_sha256` is the lowercase hex SHA-256 of these bytes, built from the **decoded** table
(after the PQ4 checks), every integer little-endian:

1. the ASCII preamble `MorphoBricks plane_histograms schema_version 6 content` and `\n`;
2. `u64` row count, `u64` column count;
3. for every column **in file order**: `u64` byte length and the UTF-8 name, a `u8` type code
   (`string` 1, `int64` 2, `double` 3, `list<int32>` 4, `list<int64>` 5); then for every row in
   file order `u8 0` for null, or `u8 1` and the value: a string as `u64` byte length and UTF-8;
   an `int64` as `i64`; a `double` as its IEEE 754 binary64 bits; a list as `u64` length and its
   elements as `i32` (bins) or `i64` (counts).

Compression, encodings, page and row-group boundaries, statistics, key-value metadata and the
writer's name never enter it. Row order does (version 5's row order is the writer's order, kept).
The reference implementation is `content_bytes` / `content_sha256` in
`tools/plane_histograms_v6.py`; `probe_full_range.py` shows a NumPy implementation (one slice per
plane and channel, no per-bin loop) giving the same digest. A brick reproduces the digests listed
in `tools/plane_histograms_v6/README.md`.

**What the run manifest records.** **Both digests, always**: `histogram_table_sha256` (file bytes)
and `histogram_table_content_sha256` (PQ6), with `pyarrow`'s version added to the recorded package
versions. Neither is optional, and the new manifest version keeps **no `csv_sha256` alias**: a
manifest missing either digest, or holding `csv_sha256`, is refused as a manifest of another
version (AR11 (7)). The field names are preprocessing's (recommended here). **How the reference
reader checks it** (`check_manifest_entry`): the file's SHA-256 equals the recorded file digest,
the file passes every PQ4 check, and its `content_sha256` equals the recorded content digest.

### EW11's reference digest (normative; supersedes ADR 0004 EW11 on this point)

From the acceptance of this ADR, ADR 0004 EW11's `reference_sha256` (in a window table whose
`reference_kind` is `plane_histogram`) is the plane table's **`content_sha256`** (PQ6), not the
SHA-256 of the file's bytes, and EW11's "a table whose SHA-256 differs from the one recorded when the
run was planned" (`plane_histogram_mismatch`) compares content digests. A plane table rewritten with
the same content (another `pyarrow`, other writer settings, another platform) is therefore no
mismatch; a table with other content is. The column keeps its name and its 64 hex characters, and
the window table's grammar and schema are unchanged. The reference check is `reference_matches` in
`tools/plane_histograms_v6.py`, tested with `pv01` against `pv06` (same content, other bytes: no
mismatch). ADR 0004's own text is amended to say so in a later PR.

## Evidence

**Sizes and times of the study's long layout, not PQ2** (study, `results.md`, exact bins, 90 JUMP
planes, 76 study planes, 8 HPMEC, 27 CMU-1; medians). PQ2's list layout was not benchmarked on
these four datasets; on the synthetic full-range probe below it is smaller than the long layout
(3,324 against 5,161 KiB). A benchmark of PQ2 on the study, HPMEC, JUMP and CMU-1 data before the
normalization release would replace this label with measured figures:

| Dataset | v5 dense CSV | Sparse CSV cell (first draft) | Long Parquet (study layout) | Long Parquet vs v5 |
| --- | ---: | ---: | ---: | ---: |
| study (12-bit in 16) | 13,296 KiB, write 423 ms, read 352 ms | 816 KiB, 35 ms, 32 ms | 230 KiB, 20 ms, 19 ms | **58×** smaller |
| HPMEC (uint16) | 7,707 KiB, 189 ms, 155 ms | 175 KiB, 7 ms, 6 ms | 84 KiB, 5 ms, 4 ms | **91×** |
| JUMP (full-range uint16) | 20,905 KiB, 646 ms, 505 ms | 15,407 KiB, 470 ms, 365 ms | 5,572 KiB, 183 ms, 74 ms | **3.8×**; write 3.5× faster, read 6.8× faster |
| CMU-1 (uint8) | 58 KiB | 63 KiB | 35 KiB | 1.7× |

Every format, Parquet included, read back to the same records: 0 bit differences over 6,515
numbers. Per image, 4 threads, Parquet writes JUMP in 82 ms (sparse CSV 511 ms).

**This PR (probe and golden tables; `tools/plane_histograms_v6/`):**

- **Layout, full-range uint16** (`probe_full_range.py`; 90 seeded channel planes of 1080 × 1080
  over 0..65535, median 20,524 distinct values = 31 % of the bins, close to JUMP's 34 %;
  `pyarrow` 26.0.1, NumPy 2.5.5, one shared 4-CPU machine): **PQ2 list columns 3,324 KiB, write
  121 ms, read 68 ms**; long layout 5,161 KiB, 102 ms, 17 ms. Exact histograms by `np.bincount` +
  `np.flatnonzero`: 269 ms for the 90 planes (PQ5). The reference checker (pure Python, every
  PQ4 rule) takes 206 ms; the content digest 26 ms vectorised, 123 ms in the reference code
  (equal digests). Indicative only: synthetic data, one machine.
- **Bytes vs content**: the same `make_tables.py` and writer profile under `pyarrow` 18.1.0 and
  26.0.1 give **other bytes for every one of the 6 valid tables** (`created_by` differs, and so do
  the data pages: `pv05` is 40,184 against 40,576 bytes) and **the same `content_sha256` for all
  of them**; each version reads the other's files. Rewriting with one version gives identical
  bytes. Other writer settings (`pv06`; snappy, gzip, zstd 19, no dictionary, page size 64, one
  row per row group in `test_digest_ignores_every_writer_setting`) give other bytes and the same
  digest.
- **Small tables cost more than CSV**: Parquet's per-column metadata makes the 2-row `pv01` 8.2 KiB
  (its sparse CSV draft was 1.3 KiB). Real tables have hundreds to thousands of planes; staging
  writes one small table per source file (migration, preprocessing).

## Migration, per brick (if accepted)

Checked against `main` of each brick: normalization `fcfaeac` (v0.7.1), preprocessing `93f15fe`,
CellPatcher `de5b5ae`, MorphoFeature `b9a6734`.

- **morphobricks-normalization** (the format's owner): `csv_io.py` gives way to a Parquet module
  (or keeps its name; brick's choice): `SCHEMA_VERSION` 6, `OUTPUT_FILENAME`
  `plane_histograms.parquet`, the PQ2 columns and types, the vectorised writer (PQ5, replacing
  `_row`'s `map(str, hist.counts.tolist())`), the reader (PQ4, replacing `_record` / `_histogram`
  / `_check_absent`; `header_channels` no longer derives a bin count), the v5 refusal by value
  (`_EARLIER_VERSIONS` + `"5"`, `_earlier_version_message` naming `plane_histograms.parquet`),
  and a `content_sha256` function reproducing the catalogue digests. `pyarrow>=18` in
  `dependencies`, imported lazily, with a test that `import morphobricks_normalization` leaves `pyarrow` unloaded (as `tools/test_plane_histograms_v6.py` does for the reference checker). Its tests reproduce `tools/plane_histograms_v6/` (accept the 6
  valid tables with their dense counts and digests, refuse the 36 invalid ones with no content digest). Contract §6.1,
  §6.2, N42, CHANGELOG. `CsvFormatError` may keep its name for consumers or be renamed (brick's
  choice; consumers catch it today).
- **preprocessing**: no histogram parsing of its own, but: the normalization pin and `pyarrow>=18`;
  `OUTPUT_FILENAME` users (generation `MOVED_IN_ORDER`, `result.py`, `reuse.py`, `log_target.py`,
  `notebook_folder.py`) follow the new name; the manifest records `histogram_table_sha256` (today
  `csv_sha256`: `run/pipeline.py`, `run_inputs.py` `published_path`/`_check_sha`, `run/reuse.py`)
  **and** `histogram_table_content_sha256` (PQ6), both mandatory and no `csv_sha256` alias, plus
  `pyarrow`'s version, a new manifest version
  (`manifest_versions.py`, today 5; older ones refused, AR11 (7)); staging (`run/staging.py`)
  writes each file's rows with the same writer (a small `.parquet` per file; its SHA-256 stays an
  integrity check of the staged file); the byte goldens (`tests/test_run_workers_bytes.py`, the
  Spec fixture trees) compare content digests across modes and bytes within one environment;
  `tests/test_histogram_goldens.py` (L113 `schema_version == "5"`, L124 the per-bin
  `Histogram_Count_<ID>_<NNNNN>` columns) and the docstrings that say "schema version 5". Runs
  written with version 5 are recomputed (PQ7). Tests: a run folder holding a v5 table is refused
  through `RunInputs.open` with the fix; the writer gives the same bytes (one environment) and the
  same `content_sha256` with 1, 2, 4 and auto workers and after a resume; and the staging cost of
  one small `.parquet` per source file (about 8 KiB of metadata each, `pv01`) is measured on a
  many-file run before the staging layout is chosen (below, "Not decided here").
- **CellPatcher**: opens the table through `RunInputs` (`run_open.py`, catching `CsvFormatError`),
  so: the pins and `pyarrow>=18`; its provenance fields copy `manifest.csv_sha256` today
  (`run_open.py` L144, `statistics.py` `csv_sha256`, `normalization.py` L195
  `plane_histograms_sha256`, `file_runs.py` L374): they record `content_sha256` (identity, PQ6);
  the test runs that hold v5 tables, the user message for a v5 run (recompute), the docstrings and
  messages naming `plane_histograms.csv`.
- **MorphoFeature**: through `RunInputs` (`histogram_fit.py`), so: the pins, and its `cli` extra
  `pyarrow>=14` → `>=18`; `run_config.py` L521 (`histograms_sha256`) and `histogram_fit.py` L81
  record `content_sha256`; `tests/test_earlier_runs_refused.py` (L42 asserts `SCHEMA_VERSION ==
  "5"`, L75 the rows' version); the docstrings naming `plane_histograms.csv`. Core import and
  provider discovery stay inert (PQ8).
- **This repository**: ADR 0003 gets a pointer; the conformance plan's "Histogram table v5" row
  becomes "v6" (one row per plane, PQ2-PQ7, content digests); `tools/requirements.txt` holds
  `pyarrow` for the Spec's own reference tools (no brick reads it).
- **ADR 0007** (run-folder entry, proposed, Spec #48): the run-folder identity of its entry record
  should use the plane table's `content_sha256`, not its file SHA-256. Its text refers to schema 5
  and the file digest (ADR 0007 L38, L326, L437 at #48's head `68cf7e1`); it is aligned in #48, not
  here.
- **Window histograms (EW11)**: not implemented yet; its grammar is unchanged (PQ9). When it is
  implemented, `reference_sha256` is the plane table's `content_sha256`.

## Open questions for the owner (recommendation first)

1. **Accept version 6 as `plane_histograms.parquet` (PQ1-PQ9)?** Recommended: **yes**, as the
   next normalization change; it changes no number. The study's long Parquet layout was 3.8× (JUMP)
   to 91× (HPMEC) smaller than version 5; PQ2 was measured on the synthetic probe only (§Evidence).
   **Owner, 17 November 2026: yes, Parquet.**
2. **Identity on the content digest, with the file SHA-256 kept for integrity (PQ6)?** **Owner,
   17 November 2026: yes.**
   Recommended: **yes**. Pinning bytes needs one exact `pyarrow` everywhere and still changes every
   digest at each upgrade; the content digest costs one decode (26 ms on 90 JUMP-like planes).
3. **`pyarrow>=18`, no upper bound, required in normalization and declared by preprocessing,
   CellPatcher and MorphoFeature (PQ8)?** Recommended: **yes** (18.1.0 and 26.0.1 tested). A lower
   floor (MorphoFeature's and MorphoRelate's current `>=14`) only for Python 3.11/3.12 users, after
   testing it. **Owner, 17 November 2026: yes, no upper bound.** **Challenged by the external review
   of 18 November 2026; for the owner to decide again.** The review holds that compatibility with
   releases not yet tested is not established, and asks for one of: (a) a tested range (for example
   `>=18,<27`, raised in a reviewed change); or (b) no upper bound plus a **release-gate matrix**:
   each brick release runs, under the oldest and newest `pyarrow` it allows, a cross-version write
   and read of the golden tables, their content digests, null against empty lists and the `int64`
   limits of 64-bit planes. The text keeps the owner's choice until then.
4. **One row per plane with two list columns per channel (PQ2), not the long layout?**
   Recommended: **yes**: it keeps HV1/N41, absent ≠ empty without a second table, and was smaller
   on the JUMP-like probe (3,324 against 5,161 KiB). **The trade-off is read time:** on the same
   probe PQ2 read in 68 ms against 17 ms for the long layout (recorded above); two reruns on
   19 November 2026 gave 62 against 27 ms and 193 against 22 ms (one shared machine, noisy).
   Reading PQ2 is 2-4× slower there, tens of milliseconds for 90 full-range planes; writes were
   similar (100-121 against 101-109 ms). **Owner, 17 November 2026: yes.**
5. **Golden tables under `tools/plane_histograms_v6/`** rather than the pinned `fixtures/`?
   Recommended: **yes**, as for EW11's golden cases; normalization reproduces them.
6. **EW11's `reference_sha256` = the plane table's `content_sha256` (PQ9)?** Recommended: **yes**,
   decided with this ADR since EW11 is not implemented.
7. **Intensity and binning limits as version 5's text (`string`)?** Recommended: **yes**: exact for
   64-bit integer planes, one type for every dtype. **Owner, 17 November 2026: yes**; the text is the
   v5 writer's canonical text only (types table). Alternative: `double` columns plus a rule that
   64-bit integer planes are refused or stored elsewhere.
8. **The two EW11 grammar clarifications of the first draft** (ASCII digits only; a count at most
   2^63 − 1): no longer part of this ADR. Recommended: a separate one-paragraph EW11 clarification
   if wanted; they refuse nothing a conforming writer writes.

## Not decided here

How old installs word their refusal of a version 6 table; the release numbers of the bricks; the
manifest field names and manifest version (preprocessing's); whether staging keeps one small
table per source file or stages rows otherwise (preprocessing's, given the per-file Parquet
overhead).
