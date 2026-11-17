# `plane_histograms.parquet` schema version 6: golden tables (proposed, ADR 0008)

Test data for [ADR 0008](../../docs/adr/0008-plane-histograms-v6.md) (**proposed; owner decision
pending**). They are kept beside the reference checker [`plane_histograms_v6.py`](../plane_histograms_v6.py),
like the EW11 golden cases, and **not** under `fixtures/`: that tree is the pinned test data of
experiment-v1 (ADR 0003 kept this table out of it), and a proposal must not move every brick's pin.
Where they live once the owner decides is open question 5 of ADR 0008.

**How they were made.** [`make_tables.py`](make_tables.py) writes every `.parquet` file here with
`pyarrow` (`tools/requirements.txt`) and the writer profile of PQ5; the tests read the committed
files and check that the script still builds the same content. The values of `pv01`-`pv04` are
those the normalization brick's own version 5 writer (`write_plane_histograms` at `9616e12`) wrote
for seeded planes: this PR's earlier CSV goldens (Spec `9167fe3`), the intensity and binning limits
kept as that writer's text, the dense bins replaced by the non-zero bins and their counts. `pv05` is
a seeded full-range uint16 plane. `pi01` is that v5 writer's output unchanged; `pi02` is this PR's
earlier sparse-cell CSV draft of version 6. Every other `invalid/` table changes **one** thing in a
valid table, and breaks exactly one rule.

**Identity.** The `content_sha256` below is the table's content digest (PQ6), the identity the run
manifest records. It is the same whatever `pyarrow` version or writer settings wrote the file; the
file bytes are not (`pv06` holds `pv01`'s content in other bytes). Written with `pyarrow` 18.1.0
and 26.0.1, every file below has other bytes and the same digest. [`probe_full_range.py`](probe_full_range.py)
is a probe, not a check (ADR 0008 evidence).

## Valid (6)

| File | Content | `content_sha256` |
| --- | --- | --- |
| `pv01_two_channels_uint8` | uint8, `bin_count` 256 (exact), channels `ACTIN`, `DNA`, one image at z 0 and 1 (two rows). 16 + 13 × 2 = 42 columns | `c92de4c9b44334104d94b25bb3a2fd6bbc09e303b857ddb1bae4e3d0dd2eec2a` |
| `pv02_absent_channel_null` | IDs `ACTIN`, `DNA`, `PHASE`; the CTRL row lists `DNA;ACTIN` and its 13 `PHASE` values are **null** (absent, HV1); the DrugA row lists all three (the `v05` case) | `08c8123351fc49c5ce3081f8922b9160c28627cd1c3448f65132369b591d8f2c` |
| `pv03_measured_empty_and_tails_id_with_underscore` | float32, `bin_count` 8, robust range. `DNA` is measured with no finite pixel: `Histogram_Bins_DNA` = `Histogram_Counts_DNA` = `[]` (empty, not null), valid 0, intensity and binning limits null. `PAX_488` (an ID with `_`, HV2) has one underflow and one overflow pixel: its counts sum to 16 − 1 − 1 = 14 | `593434ddae2d1347b8e153bbcadd020e711f425f2efe0efb789ac98d16fc88f9` |
| `pv04_last_bin_index` | uint8, values 0 and 255: bins `[0, 255]`, counts `[14, 2]`; the last index `bin_count − 1` accepted | `4916c5671c8904c9a113d82bf39666777888e0b4248d497f2c5a31ef28fa195f` |
| `pv05_full_range_uint16` | uint16, `bin_count` 65536 (exact), two channels of 4,096 seeded pixels over 0..65535 with 12 saturated pixels: bins 0 and 65535 both used (the JUMP-like case) | `965e45c0b1f3b864a5e45c8f706a5d886bc1fdcc3f6f8e02789bf48b40398e50` |
| `pv06_pv01_other_writer_settings` | `pv01`'s content written without compression or dictionary, with statistics, the stored Arrow schema, data page v1 and one row per row group: other bytes, the same digest | `c92de4c9b44334104d94b25bb3a2fd6bbc09e303b857ddb1bae4e3d0dd2eec2a` |

## Invalid (25)

| File | Base | What changed | Reason (reference checker) |
| --- | --- | --- | --- |
| `pi01_schema_version_5` | - | `plane_histograms.csv` as written by the v5 writer (per-bin columns, `schema_version` 5) | `schema_version_refused` (HV4/PQ7: refused by its value, the fix named, no converter) |
| `pi02_sparse_csv_labelled_6` | - | This PR's earlier sparse-cell CSV draft, `schema_version` 6 | `not_parquet` (version 6 is Parquet only) |
| `pi03_parquet_schema_version_5` | pv01 | `schema_version` 5 | `schema_version_refused` |
| `pi04_schema_version_7` | pv01 | `schema_version` 7 | `schema_version_unknown` |
| `pi05_channel_blocks_unsorted` | pv01 | `DNA` columns before `ACTIN` | `header` |
| `pi06_bins_int64` | pv01 | `Histogram_Bins_<ID>` as `list<int64>` | `column_type` |
| `pi07_bins_unordered` | pv01 | bins `[1, 0, 2, 3]` (sum unchanged) | `bins_order` |
| `pi08_bins_repeated` | pv01 | bins `[0, 0, 2, 3]` (sum unchanged) | `bins_order` |
| `pi09_bin_index_equals_bin_count` | pv01 | bin 256 with `bin_count` 256 | `bins_range` |
| `pi10_bin_index_negative` | pv01 | bin −1 | `bins_range` |
| `pi11_zero_count` | pv01 | a fifth pair `4: 0` (sum unchanged) | `counts_not_positive` |
| `pi12_negative_count` | pv01 | counts `[4, 4, 6, 3, −1]` (sum unchanged) | `counts_not_positive` |
| `pi13_lists_length_differ` | pv01 | 4 bins, 3 counts (sum unchanged) | `lists_length` |
| `pi14_counts_sum_mismatch` | pv01 | counts sum to 15, valid 16, no tails | `counts_sum` |
| `pi15_empty_lists_with_pixels` | pv01 | `[]` and `[]` for a channel with 16 pixels in its bins | `counts_sum` |
| `pi16_listed_channel_lists_null` | pv01 | both lists null for a listed channel (null is absent, not empty) | `present_null` |
| `pi17_absent_channel_empty_lists` | pv02 | `[]` and `[]` for the absent `PHASE` (absent is null, not empty) | `absent_has_value` |
| `pi18_absent_channel_valid_zero` | pv02 | `Histogram_ValidPixelCount_PHASE` 0 for the absent `PHASE` | `absent_has_value` |
| `pi19_bin_count_differs` | pv01 | second row `bin_count` 128 (its indices still fit) | `bin_count_differs` |
| `pi20_null_in_counts` | pv01 | a null inside `Histogram_Counts_DNA` | `null_element` |
| `pi21_channel_count_mismatch` | pv01 | `channel_count` 3 for `DNA;ACTIN` | `channels_cell` |
| `pi22_duplicate_plane` | pv01 | second row with the first row's `plane_id` | `duplicate_plane` |
| `pi23_tail_mean_negative_zero` | pv03 | `Histogram_UnderflowMean_DNA` −0.0 | `float_value` |
| `pi24_truncated_file` | pv01 | the first half of the file's bytes | `not_parquet` |
| `pi25_plane_column_null` | pv01 | `condition` null | `plane_value` |
