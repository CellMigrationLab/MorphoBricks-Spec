# `plane_histograms.csv` schema version 6: golden tables (proposed, ADR 0008)

Test data for [ADR 0008](../../docs/adr/0008-plane-histograms-v6.md) (**proposed; owner decision
pending**) and the shared grammar [`docs/sparse-counts.md`](../../docs/sparse-counts.md). They are
kept beside the reference checker [`plane_histograms_v6.py`](../plane_histograms_v6.py), like the
EW11 golden cases, and **not** under `fixtures/`: that tree is the pinned test data of
experiment-v1 (ADR 0003 kept this table out of it), and a proposal must not move every brick's pin.
Where they live once the owner decides is open question 4 of ADR 0008.

**How they were made.** `valid/` tables were written by the normalization brick's own
`write_plane_histograms` at `9616e12` (v0.7.0 + #104; schema version 5) from seeded planes, then
converted cell for cell (the 11 feature cells kept as written, the dense bin columns replaced by
`sparse_counts.format_dense`, `schema_version` set to `6`). `pi01` is that v5 writer's output
unchanged. Every `invalid/` table changes one thing in a valid table. `python -I -m pytest tools`
checks every file with the reference checker.

## Valid (4)

| File | Content |
| --- | --- |
| `pv01_two_channels_uint8` | uint8, `bin_count` 256 (exact), channels `ACTIN`, `DNA`, one image at z 0 and 1 (two rows). 16 + 12 × 2 = 40 columns |
| `pv02_absent_channel_blank` | Header `ACTIN`, `DNA`, `PHASE`; the CTRL row lists `DNA;ACTIN` and its 12 `PHASE` cells are **blank** (absent, HV1); the DrugA row lists all three (the `v05` case) |
| `pv03_empty_and_tails_id_with_underscore` | float32, `bin_count` 8, robust range. `DNA` is measured with no finite pixel: `Histogram_Counts_DNA` = `empty`, valid 0, intensity limits blank. `PAX_488` (an ID with `_`, HV2) has one underflow and one overflow pixel: its counts sum to 16 − 1 − 1 = 14 |
| `pv04_last_bin_index` | uint8, values 0 and 255: `0:14;255:2`, the last index `bin_count − 1` accepted |

## Invalid (22)

| File | Base | What changed | Reason (reference checker) |
| --- | --- | --- | --- |
| `pi01_schema_version_5` | pv01 | The same planes as written by the v5 writer (per-bin columns, `schema_version` 5) | `schema_version_refused` (HV4: refused by its value, no converter) |
| `pi02_v5_bin_columns_labelled_6` | pi01 | `schema_version` changed to 6, per-bin columns kept | `header` |
| `pi03_counts_space` | pv01 | `0:4; 1:4;2:5;3:3` | `counts_syntax` |
| `pi04_counts_trailing_separator` | pv01 | `0:4;1:4;2:5;3:3;` | `counts_syntax` |
| `pi05_counts_index_leading_zero` | pv01 | `00:4;…` | `counts_leading_zero` |
| `pi06_counts_count_leading_zero` | pv01 | `0:04;…` | `counts_leading_zero` |
| `pi07_counts_zero_count` | pv01 | `…;4:0` appended (sum unchanged) | `counts_zero` |
| `pi08_counts_unordered` | pv01 | `1:4;0:4;2:5;3:3` (sum unchanged) | `counts_order` |
| `pi09_counts_repeated_index` | pv01 | `0:4;0:4;2:5;3:3` (sum unchanged) | `counts_order` |
| `pi10_counts_index_out_of_range` | pv01 | `…;256:3` with `bin_count` 256 | `counts_index_range` |
| `pi11_counts_sum_mismatch` | pv01 | `…;3:2` (sum 15, valid 16, no tails) | `counts_sum` |
| `pi12_empty_with_pixels_in_bins` | pv01 | `empty` for a channel with 16 pixels in its bins | `counts_sum` |
| `pi13_present_counts_blank` | pv01 | Blank counts cell for a listed channel (blank is not `empty`) | `counts_blank` |
| `pi14_absent_channel_empty` | pv02 | `empty` in the counts cell of the absent `PHASE` (absent is blank, not `empty`) | `absent_has_value` |
| `pi15_empty_upper_case` | pv03 | `EMPTY` | `counts_syntax` |
| `pi16_counts_sign` | pv01 | `+0:4;…` | `counts_syntax` |
| `pi17_counts_non_ascii_digit` | pv01 | `٠:4;…` (ARABIC-INDIC DIGIT ZERO) | `counts_syntax` |
| `pi18_bin_count_differs` | pv01 | Second row `bin_count` 128 (its indices still fit) | `bin_count_differs` |
| `pi19_counts_too_large` | pv01 | Count 9223372036854775808 (2^63) | `counts_too_large` |
| `pi20_counts_pair_without_count` | pv01 | `…;3:` | `counts_syntax` |
| `pi21_zero_for_absent_channel` | pv02 | `0:0` for the absent `PHASE` | `absent_has_value` |
| `pi22_header_channels_unsorted` | pv01 | `DNA` block before `ACTIN` in header and rows | `header` |
