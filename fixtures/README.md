# Fixture catalogue: experiment description v1

Normative test data for [experiment-v1.md](../docs/experiment-v1.md). Each file starts with a
comment header (`Fixture`, `Expected`, `Source`, description). How these become executable tests
in preprocessing is described in the [conformance plan](../docs/conformance-plan.md); nothing here
is executed by this repository.

## Rules

- A conforming reader MUST accept every file in `valid/` and report exactly the warnings listed
  (none unless stated).
- For every file in `invalid/` it MUST report exactly the listed **set** of error codes, all from
  the first failing validation phase (experiment-v1 §6), and nothing from later phases.
- "Homogeneous: **no**" marks a valid file whose units have different ordered channel lists. The
  spec accepts it; the Stage 1-2 runtime MUST refuse to process it with
  `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` (lifted at Stage 3).
- Physical cases that need images (within-unit divergence, header contradictions, mask pixel
  contradictions, reconciliation) cannot be expressed by a TOML file alone; they are listed as
  scenarios P01-P16 in the [conformance plan](../docs/conformance-plan.md#3-physical-scenarios-preprocessing-owned),
  built on the valid files below.
- `v18` MUST parse to the same model as `v01` (round trip); `v21` differs from `v01` only in
  `display_name`, `target` and `treatment_key` values and `v16` only in `display_name` values, so
  for both all four section digests equal `v01`'s (experiment-v1 §9.3).
- Every file carries the required `used_ids` table (experiment-v1 §4.9) listing at least all of its
  declared condition, channel and repeat IDs; `i92` is the file without it. The eight undecodable
  or unparsable phase-1 fixtures (`i01`-`i08`) are unchanged and fail before it matters.
- `transitions/` holds five files that are valid alone but are refused against a named published
  predecessor (`R_CONFIRMED_ID_CHANGED`, `R_USED_ID_REUSED`, `R_USED_ID_DROPPED`,
  `R_CONFIRMED_ON_CHANGED`; experiment-v1 §4.4a, §4.6, §4.9); they need the predecessor file and
  are not part of the single-file valid/invalid rules. Publication-base and folder-name rules need
  no TOML of their own: they run on named fixtures in scenarios P17-P22.
- A copy of this tree vendored by a reader MUST hash to the pinned SHA's `fixtures` tree
  (conformance plan §1).
- Expected `experiment_design.csv` outputs (golden files) are deferred to Stage 1. The fixed-SHA
  consumer audit (roadmap S0.1) is still TODO before Gate G0.

## Syntax check (6 November 2026)

Checked with Python 3.13 `tomllib` (`tomllib.loads` on the UTF-8 decoded bytes), after the second
round of owner decisions:

- `valid/`: 27 of 27 parse.
- `transitions/`: 5 of 5 parse.
- `invalid/`: 91 of 99 parse as TOML and are invalid only by the v1 rules. The 8 phase-1 fixtures
  fail deliberately: `i01_bom` (`TOMLDecodeError`, BOM read as an invalid statement),
  `i02_invalid_utf8` (`UnicodeDecodeError`), `i03`-`i06` (`TOMLDecodeError`, "Cannot declare ...
  twice" / "Cannot overwrite a value"), `i07`, `i08` (`TOMLDecodeError`, "Invalid value" /
  "Expected newline").

For the valid and transition files, a throw-away script (not committed) also checked that every
declared ID is listed in `used_ids`, that every identity and `used_ids` entry is NFC, and that no
display names collide within a kind after NFC and case folding; for `i86`-`i88` it confirmed the
collision. The earlier full cross-check of every expected code (first round) was **not repeated**
after the second round: the expected codes of the new and rewritten fixtures are by construction,
not by execution. This is not a conformance claim for any brick.

## Coverage of RFC #1 and its discussion

**RFC #1, M0 fixture list (12 cases)**, from the
[RFC body](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1):

| # | RFC case | Fixtures |
|---|---|---|
| 1 | One control | `v01` |
| 2 | Several controls | `v02` |
| 3 | Differently named source folders paired into one canonical repeat | `v03` |
| 4 | Swapped channel order between imaging units | `v04` |
| 5 | Variable channel counts | `v05` |
| 6 | Two technical repeats of one biological repeat with different layouts | `v06` |
| 7 | One FOV diverging inside a technical repeat (invalid) | `i20` (no override can express it); physical P01, P02 |
| 8 | Instance masks | `v07` |
| 9 | Binary masks | `v08` |
| 10 | Incomplete/progressive masks | `v09` |
| 11 | Reference chains | `v10` |
| 12 | Invalid reference cycles | `i64`, `i65` |

**Ten adversarial tests** from the independent review comment in the
[RFC #1 discussion](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1#issuecomment-6667477114)
(5 November 2026). Most are end-to-end obligations of later stages; the fixture fixes the input:

| # | Adversarial test | Fixtures | Obligation |
|---|---|---|---|
| 1 | Two technical repeats of different counts/orders stay ONE biological replicate | `v06` | Stage 2-3: N per repeat in normalization, embeddings, MorphoCoverage |
| 2 | One deviating FOV in a technical repeat refused with image/C-index evidence | `i20`; P01, P02 | Stage 1: `R_UNIT_NOT_HOMOGENEOUS` |
| 3 | Swapped C order never mixes ACTIN and DNA in normalization or CellPatcher | `v04`, `v06` | Stage 1 refusal; Stage 3 pooling by canonical ID |
| 4 | Homogeneous legacy datasets keep numerical parity and existing refusals | `v13` | Stage 1: byte-identical derived CSV; Stage 3 parity |
| 5 | `DNA` with confirmed header `DAPI` passes; unconfirmed contradiction refuses | `v11`; P03 | Stage 1: `R_HEADER_CONTRADICTION` |
| 6 | A binary region mask never becomes an instance object set | `v08` | Stage 2: `A_MASK_NOT_INSTANCES` |
| 7 | N35 confirmation survives migration and reopens on discovery changes | `v13`, `i37`; P07 | Stage 1 migration and reconciliation |
| 8 | Distinct source repeat names paired by the user give one canonical ID in MorphoCoverage | `v03` | Stage 2 (S2.5) |
| 9 | Missing channels in requested scope: refusal or recorded user subset, never silent drop | `v05`, `v17` | Stage 2: `A_SCOPE_INCOMPLETE` |
| 10 | Metadata-only changes keep valid pixel-derived caches | `v01` vs `v21` | Stage 1: section digests |

**Further required cases:**

| Topic | Fixtures |
|---|---|
| Duplicate keys | `i03`-`i06` |
| Case collisions | `i48`-`i52`, `i68` (no folding when resolving), `i95` |
| NFC (refused, never normalized) | `v23`, `i78`, `i83`-`i85`; P21 |
| Display names | `v16`, `v24`, `i53`, `i76`, `i77`, `i86`-`i88` |
| Display name is not an ID | `i89`-`i91` |
| IDs never repaired, re-cased or renumbered | `v26`, `i48`-`i52`, `i55`, `i95` |
| `used_ids` registry | `v25`, `i92`-`i97`, `t03`, `t04`; P19, P20 |
| `confirmed_on` is a user fact | `i98`, `t05`; P07, P15, P22 |
| Publish only from the current base | P17, P18 (on `v01`, `v21`, `v16`) |
| Lab-tool provenance stays out of the file | `i99` |
| Unknown and forbidden fields | `i16`-`i19`; `i20`-`i26`; `i97`, `i99` |
| Implicit-conversion traps | `i07`, `i08`, `i12`-`i14`, `i19`, `i27`-`i30`, `i33`, `i34`, `i36`, `i38`, `i39`; valid side `v15` |
| Reference DAG | `i64`-`i68`, `i41`; `v10`, `v19` |
| Swapped channel order | `v04`, `v06` |
| Extra / missing channel | `v05`, `v17`, `v22`, `i69` |
| Within-unit divergence | `i20`; P01, P02 |
| Instance vs binary masks | `v07`, `v08`, `i42`, `i43`; P05 |
| Partial masks | `v09` |
| Immutable IDs (no renames) | `v16`, `i75`, `i82`, `t01`, `t02`; P08, P16 |
| Aliases (header evidence) | `v11`, `v12`, `i46`, `i81`; P03 |
| Versioning (offline constant, no default) | `i09`-`i15` |
| Identities | `v14`, `v15`, `v20`, `v23`, `v26`, `i54`-`i63`, `i78` |
| Target / treatment key (descriptive only) | `v01`, `v10`, `v21`, `v27`, `i71` |
| Encoding | `i01`, `i02` |

### Owner decisions of 6 November 2026 (ADR 0001) and their fixtures

| # | Decision | Fixtures / scenarios |
|---|---|---|
| D1 | Optional `target`, `treatment_key` (refined by Q4: descriptive only) | `v01`, `v10`, `v21`, `v27`; `i71` (non-string) |
| D2 | Channel ID = compartment name refused | `i61` |
| D3 | Unused channel is a warning | `v22` |
| D4 | Repeat ID = another repeat's source folder refused | `i75` |
| D5 | IDs immutable; `display_name` mutable and unique; no `retired_repeats` | `v16` (display names change, identity identical), `i53`, `i76`, `i77` (collisions), `i82` (no table), `t01`, `t02`; P16 |
| D6 | N35 reopens only on channel/layout/grouping change | P07, P15 |
| D7 | NFC identities (refined by Q3: non-NFC refused, never normalized; no NFC-collision code) | `v23`, `i78`, `i83`-`i85` |
| D8 | RGB refused | P13 |
| D9 | Header names exact, case-sensitive | `v11`; P03 |
| D10 | `binary` mask with > 2 values refused | P05 |
| D11 | Drafts internal; `RunInputs` refuses them | `i37`; P14 |
| Q1 | Append-only `used_ids` per kind; no reuse, no drop | `v25`, `i92`-`i97`, `t03`, `t04`; P19, P20 |
| Q2 | Display names unique per kind after NFC + case folding | `v24`, `i86`-`i88` |
| Q3 | Reader refuses non-NFC identities | `v23`, `i78`, `i83`-`i85`; P21 |
| Q4 | `treatment_key`, `target` descriptive only | `v27`, `v21` |
| Q5 | Lab-tool links in the run manifest only | `i99` |
| A1 | Publish only from the current base SHA | P17, P18 |
| A2 | IDs never repaired, re-cased or renumbered | `v26`, `i95` |
| A3 | `confirmed_on` is a user fact | `i98`, `t05`; P22 |
| A4 | `display_name` never substitutes for an ID | `i89`-`i91` |
| A5 | Pin integrity, offline version check, no fallback rules | `i09`-`i11`; conformance plan §1-§2 |

## Valid fixtures (27)

| Fixture | Source | Expected | Homogeneous | Case |
|---|---|---|---|---|
| [`v01_single_control`](valid/v01_single_control.toml) | RFC case 1 | pass | yes | One control; trivial pairing, so canonical repeat IDs default to the folder names. |
| [`v02_multiple_controls`](valid/v02_multiple_controls.toml) | RFC case 2 | pass | yes | Two controls (DMSO, WT), each referenced by two conditions. |
| [`v03_paired_different_folder_names`](valid/v03_paired_different_folder_names.toml) | RFC case 3; adversarial 8 | pass | yes | Source folders rep1 (CTRL) and experiment_23 (DrugA) paired by the user into canonical repeat Day1; rep2/rep2_drug into Day2. MorphoCoverage must see Day1 and Day2 as the biological repeats. |
| [`v04_swapped_channel_order`](valid/v04_swapped_channel_order.toml) | RFC case 4; adversarial 3 | pass | **no** | Same channels, opposite source order between conditions (CTRL C0=DNA, DrugA C0=ACTIN). Valid schema; heterogeneous, so Stage 1-2 runtime refuses (R_HETEROGENEOUS_LAYOUT_NOT_ENABLED). From Stage 3, ACTIN and DNA are never mixed by C index. |
| [`v05_variable_channel_counts`](valid/v05_variable_channel_counts.toml) | RFC case 5 | pass | **no** | Extra channel PHASE in DrugA/rep1 only; CTRL lacks it (missing elsewhere). Heterogeneous. |
| [`v06_technical_repeats_different_layouts`](valid/v06_technical_repeats_different_layouts.toml) | RFC case 6; adversarial 1 | pass | **no** | One biological repeat (R002) whose CTRL member has two technical repeats with different counts and orders. It stays ONE biological repeat (N = 2 repeats in total, not 3). Heterogeneous. |
| [`v07_instance_masks`](valid/v07_instance_masks.toml) | RFC case 8 | pass | yes | Two instance masks with source-channel provenance; canonical mask IDs differ from discovered source types. |
| [`v08_binary_masks`](valid/v08_binary_masks.toml) | RFC case 9; adversarial 6 | pass | yes | A binary region mask beside an instance mask. Valid; an analysis request using TumorRegion as an object set must refuse (A_MASK_NOT_INSTANCES). |
| [`v09_partial_masks`](valid/v09_partial_masks.toml) | RFC case 10 | pass | yes | Masks declared while segmentation is in progress (e.g. 0/1000 or 300/1000 FOVs). Completeness lives in the run manifest, so the file is valid at every stage; scope checks belong to the analysis layer (A_SCOPE_INCOMPLETE). |
| [`v10_reference_chain`](valid/v10_reference_chain.toml) | RFC case 11 | pass | yes | Reference chains VEC_SiCol6a1 -> VEC_SiNC -> VEC and THBS5_SiCol6a1 -> THBS5_SiNC -> THBS5; shared treatment_key across backgrounds. |
| [`v11_header_aliases`](valid/v11_header_aliases.toml) | Adversarial 5 | pass | yes | Canonical DNA confirmed with header evidence DAPI and Hoechst 33342; canonical ACTIN with an exact-match header name that still had to be confirmed. A header name outside these lists is R_HEADER_CONTRADICTION. |
| [`v12_unnamed_headers`](valid/v12_unnamed_headers.toml) | Extra: aliases | pass | yes | No header evidence at all (ImageJ TIFFs carry no channel names); the user's confirmation is the only guard. Undetectable physical swaps are a documented limit. |
| [`v13_homogeneous_legacy`](valid/v13_homogeneous_legacy.toml) | Adversarial 4 | pass | yes | A legacy homogeneous dataset: folder-name repeat IDs, one control, same layout everywhere. The derived experiment_design.csv must be byte-identical to today's; numerical outputs must keep parity. |
| [`v14_no_repeat_folders`](valid/v14_no_repeat_folders.toml) | Extra: single convention | pass | yes | No biological-repeat or technical-repeat folders: the source label is `single` (N31, one group for the whole experiment). |
| [`v15_toml_keys_are_text`](valid/v15_toml_keys_are_text.toml) | Extra: implicit-conversion traps (valid side) | pass | yes | Folder labels that YAML would retype (2026-01-01, 012, NO, 1.0, off) stay exact text in TOML keys and strings. The quoted key "1.0" is needed: a bare 1.0 would be a dotted key. |
| [`v16_display_name_change`](valid/v16_display_name_change.toml) | Owner refinement: immutable IDs | pass | yes | v01 with every `display_name` changed or added (conditions, channels, repeats). Identity is identical: all four section digests equal v01's, nothing may be invalidated. |
| [`v17_partial_channel_presence`](valid/v17_partial_channel_presence.toml) | Adversarial 9; addendum §3 | pass | **no** | PHASE exists only in CTRL/R002/acquisition_1. For a PHASE request R002 is partially represented and R001 unavailable: the analysis layer must refuse (A_SCOPE_INCOMPLETE) or record a user-selected subset, never drop or re-weight silently. |
| [`v18_inline_and_dotted_forms`](valid/v18_inline_and_dotted_forms.toml) | Extra: round trip | pass | yes | Same model as v01 written with inline tables, dotted keys and quoted keys; parse(v18) must equal parse(v01). |
| [`v19_warnings_unpaired`](valid/v19_warnings_unpaired.toml) | Extra: reference DAG semantics | pass + `W_REFERENCE_UNPAIRED`, `W_REPEAT_MISSING_CONDITIONS` | yes | Valid with warnings: CTRL only in rep1, DrugA only in rep2, so the repeats miss conditions (W_REPEAT_MISSING_CONDITIONS) and DrugA cannot be paired with its reference (W_REFERENCE_UNPAIRED). |
| [`v20_unicode_and_spaces`](valid/v20_unicode_and_spaces.toml) | Extra: identities | pass | yes | Condition folder labels with spaces and non-ASCII text are valid labels (quoted keys); channel and mask IDs stay tokens. |
| [`v21_metadata_only_edit`](valid/v21_metadata_only_edit.toml) | Adversarial 10 | pass | yes | v01 with only descriptive condition fields edited (display name, target removed, treatment_key changed). All four section digests equal v01's (descriptive fields are omitted, experiment-v1 9.3), so no pixel-derived product may be invalidated. |
| [`v22_unused_channel_warning`](valid/v22_unused_channel_warning.toml) | Owner decision 3 | pass + `W_UNUSED_CHANNEL` | yes | PHASE is declared but acquired by no unit: valid with a warning, never an error. |
| [`v23_nfc_identity`](valid/v23_nfc_identity.toml) | Owner decision Q3 | pass | yes | A condition key written composed (U+00E9, NFC) and referenced composed: the only form a writer emits and a reader accepts. |
| [`v24_display_name_as_typed`](valid/v24_display_name_as_typed.toml) | Owner decision Q2 | pass | yes | Display names kept as typed (one decomposed, one lower case); a channel and a condition share the display name "Drug A" because uniqueness is per kind. |
| [`v25_removed_condition_id_retained`](valid/v25_removed_condition_id_retained.toml) | Owner decision Q1 | pass | yes | v01 after DrugA was removed: DrugA stays listed in `used_ids.conditions`. Predecessor of t03 and t04. |
| [`v26_ids_kept_as_written`](valid/v26_ids_kept_as_written.toml) | Audit B1, B2, B11 | pass | yes | IDs `cl001`, `CL1000`, `R999`, `R1000`: no width, prefix or case rule; kept exactly as written. |
| [`v27_descriptive_keys_collide`](valid/v27_descriptive_keys_collide.toml) | Owner decision Q4 | pass | yes | Identical and case-differing `target` / `treatment_key` values on different conditions: valid, no warning, no grouping. |

## Transition fixtures (5)

Valid alone; refused against the named published predecessor.

| Fixture | Predecessor | Expected | Case |
|---|---|---|---|
| [`t01_repeat_id_changed`](transitions/t01_repeat_id_changed.toml) | `valid/v01` | `R_CONFIRMED_ID_CHANGED` unless re-confirmation is recorded | Repeats rep1/rep2 (same member folders) are now Day1/Day2. |
| [`t02_channel_id_changed`](transitions/t02_channel_id_changed.toml) | `valid/v01` | `R_CONFIRMED_ID_CHANGED` unless re-confirmation is recorded | Channel ACTIN (same header evidence and positions) is now Actin. |
| [`t03_used_id_reused`](transitions/t03_used_id_reused.toml) | `valid/v25` | `R_USED_ID_REUSED` | DrugA (retired in v25) is declared again for a new source folder. Valid alone, with `W_REPEAT_MISSING_CONDITIONS` (rep2 has no DrugA member). |
| [`t04_used_id_dropped`](transitions/t04_used_id_dropped.toml) | `valid/v25` | `R_USED_ID_DROPPED` | DrugA is no longer listed in `used_ids.conditions`. |
| [`t05_confirmed_on_changed`](transitions/t05_confirmed_on_changed.toml) | `valid/v01` | `R_CONFIRMED_ON_CHANGED` (N35 not reopened) | rep1 unchanged except `confirmed_on` 2026-11-07. |

## Invalid fixtures (99)

| Fixture | Source | Expected code(s) | Phase | Case |
|---|---|---|---|---|
| [`i01_bom`](invalid/i01_bom.toml) | Extra: encoding | `E_FILE_ENCODING` | 1 | The file starts with a UTF-8 byte-order mark. |
| [`i02_invalid_utf8`](invalid/i02_invalid_utf8.toml) | Extra: encoding | `E_FILE_ENCODING` | 1 | A label contains the byte 0xFF (not UTF-8). |
| [`i03_duplicate_condition_table`](invalid/i03_duplicate_condition_table.toml) | Extra: duplicate keys; audit §3.12 | `E_DUPLICATE_KEY` | 1 | [conditions.CTRL] declared twice (YAML would keep the second silently). |
| [`i04_duplicate_key_quoted_vs_bare`](invalid/i04_duplicate_key_quoted_vs_bare.toml) | Extra: duplicate keys | `E_DUPLICATE_KEY` | 1 | [conditions."CTRL"] is the same key as [conditions.CTRL]. |
| [`i05_duplicate_field`](invalid/i05_duplicate_field.toml) | Extra: duplicate keys | `E_DUPLICATE_KEY` | 1 | `label` written twice in one condition. |
| [`i06_duplicate_member_dotted_vs_table`](invalid/i06_duplicate_member_dotted_vs_table.toml) | Extra: duplicate keys | `E_DUPLICATE_KEY` | 1 | A member declared as a table and again by a dotted key (two members of one condition in one repeat). |
| [`i07_unquoted_bareword`](invalid/i07_unquoted_bareword.toml) | Extra: implicit conversion (YAML `NO` -> False) | `E_TOML_SYNTAX` | 1 | source_repeat = NO, unquoted. |
| [`i08_leading_zero_integer`](invalid/i08_leading_zero_integer.toml) | Extra: implicit conversion (YAML `012` -> 10) | `E_TOML_SYNTAX` | 1 | source_repeat = 012, unquoted. |
| [`i09_schema_version_2`](invalid/i09_schema_version_2.toml) | Extra: versioning | `E_SCHEMA_VERSION_UNSUPPORTED` | 2 | schema_version = 2 is refused, never read best effort. |
| [`i10_schema_version_0`](invalid/i10_schema_version_0.toml) | Extra: versioning | `E_SCHEMA_VERSION_UNSUPPORTED` | 2 | schema_version = 0. |
| [`i11_schema_version_missing`](invalid/i11_schema_version_missing.toml) | Extra: versioning | `E_SCHEMA_VERSION_MISSING` | 2 | No schema_version. |
| [`i12_schema_version_string`](invalid/i12_schema_version_string.toml) | Extra: implicit conversion | `E_TYPE` | 2 | schema_version = "1" (a string is not converted to an integer). |
| [`i13_schema_version_float`](invalid/i13_schema_version_float.toml) | Extra: implicit conversion | `E_TYPE` | 2 | schema_version = 1.0. |
| [`i14_schema_version_bool`](invalid/i14_schema_version_bool.toml) | Extra: implicit conversion | `E_TYPE` | 2 | schema_version = true (a boolean is not the integer 1). |
| [`i15_schema_id_wrong`](invalid/i15_schema_id_wrong.toml) | Extra: versioning | `E_SCHEMA_ID` | 2 | schema = "morphobricks-experiments". |
| [`i16_unknown_top_level_field`](invalid/i16_unknown_top_level_field.toml) | Extra: unknown fields | `E_UNKNOWN_FIELD` | 3 | Top-level `notes`. |
| [`i17_unknown_condition_field`](invalid/i17_unknown_condition_field.toml) | Extra: unknown fields | `E_UNKNOWN_FIELD` | 3 | Condition field `colour`. |
| [`i18_misspelled_field`](invalid/i18_misspelled_field.toml) | Extra: unknown fields | `E_MISSING_FIELD`, `E_UNKNOWN_FIELD` | 3 | `representaton` (typo) is not silently ignored; `representation` is then also missing. |
| [`i19_dotted_float_key`](invalid/i19_dotted_float_key.toml) | Extra: implicit conversion | `E_UNKNOWN_FIELD` | 3 | [conditions.1.0] is condition `1` with a sub-table `0`, not condition `1.0`. |
| [`i20_per_fov_override`](invalid/i20_per_fov_override.toml) | Extra: within-unit divergence; ADR (no per-FOV overrides) | `E_FORBIDDEN_FIELD` | 3 | A per-FOV channel override inside a technical repeat. |
| [`i21_mask_axes_shared`](invalid/i21_mask_axes_shared.toml) | Extra: masks; preprocessing #173 | `E_FORBIDDEN_FIELD` | 3 | Mask `axes = "YX"` and `shared = true` (v1 is 2-D only; a mask has its image's axes). |
| [`i22_brick_routing`](invalid/i22_brick_routing.toml) | Extra: ADR (no brick routing) | `E_FORBIDDEN_FIELD` | 3 | A channel routed to bricks. |
| [`i23_calibration_in_file`](invalid/i23_calibration_in_file.toml) | Extra: calibration stays in calibration.csv | `E_FORBIDDEN_FIELD` | 3 | pixel_size on a repeat. |
| [`i24_control_boolean`](invalid/i24_control_boolean.toml) | Extra: audit §3.3 | `E_FORBIDDEN_FIELD` | 3 | Legacy boolean `control` (derived from `reference` in v1). |
| [`i25_experiment_field`](invalid/i25_experiment_field.toml) | Extra: audit §3.4 | `E_FORBIDDEN_FIELD` | 3 | Condition `experiment` (an FDR family; MorphoCoverage configuration). |
| [`i26_source_index_field`](invalid/i26_source_index_field.toml) | Extra: RFC (order is the mapping) | `E_FORBIDDEN_FIELD` | 3 | A unit states `source_index` beside its ordered list. |
| [`i27_toml_date_source_repeat`](invalid/i27_toml_date_source_repeat.toml) | Extra: implicit conversion (YAML date) | `E_TYPE` | 3 | source_repeat = 2026-01-01 is a TOML date, not text. |
| [`i28_integer_source_repeat`](invalid/i28_integer_source_repeat.toml) | Extra: implicit conversion | `E_TYPE` | 3 | source_repeat = 12 (integer). |
| [`i29_bool_label`](invalid/i29_bool_label.toml) | Extra: implicit conversion (YAML `off`) | `E_TYPE` | 3 | label = false. |
| [`i30_confirmed_on_toml_date`](invalid/i30_confirmed_on_toml_date.toml) | Extra: implicit conversion | `E_TYPE` | 3 | confirmed_on = 2026-11-06 (TOML date literal, not a string). |
| [`i31_confirmed_on_bad_format`](invalid/i31_confirmed_on_bad_format.toml) | Extra: preprocessing contract §12 (spreadsheet dates) | `E_DATE_FORMAT` | 3 | confirmed_on = "06/11/2026". |
| [`i32_confirmed_on_impossible_date`](invalid/i32_confirmed_on_impossible_date.toml) | Extra | `E_DATE_FORMAT` | 3 | confirmed_on = "2026-02-30". |
| [`i33_image_count_string`](invalid/i33_image_count_string.toml) | Extra: implicit conversion | `E_TYPE` | 3 | image_count = "12". |
| [`i34_image_count_float`](invalid/i34_image_count_float.toml) | Extra: implicit conversion | `E_TYPE` | 3 | image_count = 12.0. |
| [`i35_image_count_zero`](invalid/i35_image_count_zero.toml) | Extra | `E_VALUE_RANGE` | 3 | image_count = 0. |
| [`i36_confirmed_string`](invalid/i36_confirmed_string.toml) | Extra: implicit conversion (legacy yes/no) | `E_TYPE` | 3 | confirmed = "yes". |
| [`i37_repeat_unconfirmed`](invalid/i37_repeat_unconfirmed.toml) | Adversarial 7 (N35) | `E_REPEAT_UNCONFIRMED` | 3 | A published file with an unconfirmed repeat. |
| [`i38_mixed_type_channel_list`](invalid/i38_mixed_type_channel_list.toml) | Extra: implicit conversion | `E_TYPE` | 3 | channels = ["DNA", 2]. |
| [`i39_channels_as_string`](invalid/i39_channels_as_string.toml) | Extra | `E_TYPE` | 3 | channels = "DNA,ACTIN" (no splitting of text). |
| [`i40_empty_channel_list`](invalid/i40_empty_channel_list.toml) | Extra | `E_EMPTY` | 3 | A unit with channels = []. |
| [`i41_reference_list`](invalid/i41_reference_list.toml) | Extra: reference DAG | `E_TYPE` | 3 | Two references in an array; v1 has one primary reference. |
| [`i42_representation_invalid`](invalid/i42_representation_invalid.toml) | Extra: masks | `E_ENUM` | 3 | representation = "labels". |
| [`i43_representation_missing`](invalid/i43_representation_missing.toml) | Extra: masks (never inferred from pixels) | `E_MISSING_FIELD` | 3 | A mask without representation. |
| [`i44_missing_channels_table`](invalid/i44_missing_channels_table.toml) | Extra | `E_MISSING_FIELD` | 3 | No [channels] at all. |
| [`i45_member_without_technical_repeats`](invalid/i45_member_without_technical_repeats.toml) | Extra | `E_MISSING_FIELD` | 3 | A member with no technical_repeats. |
| [`i46_header_name_empty`](invalid/i46_header_name_empty.toml) | Extra: aliases | `E_TEXT_EMPTY` | 3 | header_names = [""]. |
| [`i47_label_whitespace_only`](invalid/i47_label_whitespace_only.toml) | Extra | `E_TEXT_EMPTY` | 3 | label = "  ". |
| [`i48_case_collision_conditions`](invalid/i48_case_collision_conditions.toml) | Extra: case collisions | `E_ID_CASE_COLLISION` | 4 | Conditions CTRL and ctrl. |
| [`i49_case_collision_channels`](invalid/i49_case_collision_channels.toml) | Extra: case collisions | `E_ID_CASE_COLLISION` | 4 | Channels DNA and dna. |
| [`i50_case_collision_source_repeats`](invalid/i50_case_collision_source_repeats.toml) | Extra: case collisions; preprocessing check_identity_case | `E_ID_CASE_COLLISION` | 4 | Source folders Rep1 (CTRL) and rep1 (DrugA): a label is spelled one way in the whole run. |
| [`i51_case_collision_repeat_ids`](invalid/i51_case_collision_repeat_ids.toml) | Extra: case collisions | `E_ID_CASE_COLLISION` | 4 | Canonical repeats rep1 and REP1. |
| [`i52_case_collision_technical_repeats`](invalid/i52_case_collision_technical_repeats.toml) | Extra: case collisions | `E_ID_CASE_COLLISION` | 4 | Technical repeats acq_1 and Acq_1 in different members. |
| [`i53_display_name_collision_conditions`](invalid/i53_display_name_collision_conditions.toml) | Owner refinement | `E_DISPLAY_NAME_COLLISION` | 5 | Two conditions with display_name "Control". |
| [`i54_channel_id_missing_text`](invalid/i54_channel_id_missing_text.toml) | Extra: identities (decision D-e) | `E_ID_TEXT` | 4 | Channel ID `NA` (tables read it as missing). |
| [`i55_condition_outer_whitespace`](invalid/i55_condition_outer_whitespace.toml) | Extra: identities (decision D-e) | `E_ID_TEXT` | 4 | Condition key " CTRL" with a leading space. |
| [`i56_source_repeat_null`](invalid/i56_source_repeat_null.toml) | Extra: identities | `E_ID_TEXT` | 4 | source_repeat = "null". |
| [`i57_channel_id_hyphen`](invalid/i57_channel_id_hyphen.toml) | Extra: identities (token rule) | `E_ID_SYNTAX` | 4 | Channel ID F-actin. |
| [`i58_channel_id_double_underscore`](invalid/i58_channel_id_double_underscore.toml) | Extra: identities (feature-column separator) | `E_ID_SYNTAX` | 4 | Channel ID DNA__2. |
| [`i59_mask_id_reserved`](invalid/i59_mask_id_reserved.toml) | Extra: MorphoFeature object-set rule | `E_ID_RESERVED` | 4 | Mask ID `Nucleus` (reserved compartment, any case). |
| [`i60_mask_id_reserved_in`](invalid/i60_mask_id_reserved_in.toml) | Extra: MorphoFeature object-set rule | `E_ID_RESERVED` | 4 | Mask ID `Cells_in_Tumor` (an `in` part). |
| [`i61_channel_id_reserved`](invalid/i61_channel_id_reserved.toml) | Extra: audit §3.8 | `E_ID_RESERVED` | 4 | Channel ID `Ring` (MorphoRelate compartment token). |
| [`i62_single_wrong_case`](invalid/i62_single_wrong_case.toml) | Extra: single convention | `E_SINGLE_MISUSE` | 4 | Technical repeat `Single` (spelled one way, so no case collision). |
| [`i63_single_not_alone`](invalid/i63_single_not_alone.toml) | Extra: single convention | `E_SINGLE_MISUSE` | 4 | Technical repeat `single` beside `acquisition_2`. |
| [`i64_reference_cycle`](invalid/i64_reference_cycle.toml) | RFC case 12 | `E_REFERENCE_CYCLE` | 5 | CTRL -> DrugA -> CTRL. |
| [`i65_reference_cycle_long`](invalid/i65_reference_cycle_long.toml) | RFC case 12 | `E_REFERENCE_CYCLE` | 5 | CTRL -> DrugB -> DrugA -> CTRL. |
| [`i66_reference_self`](invalid/i66_reference_self.toml) | Extra: reference DAG | `E_REFERENCE_SELF` | 5 | DrugA references itself. |
| [`i67_reference_unknown`](invalid/i67_reference_unknown.toml) | Extra: reference DAG | `E_REFERENCE_UNKNOWN` | 5 | Reference to undeclared DMSO. |
| [`i68_reference_case_mismatch`](invalid/i68_reference_case_mismatch.toml) | Extra: case rules (no folding on resolution) | `E_REFERENCE_UNKNOWN` | 5 | reference = "ctrl" does not resolve to CTRL. |
| [`i69_unknown_channel_in_unit`](invalid/i69_unknown_channel_in_unit.toml) | Extra: extra channel not declared | `E_UNKNOWN_CHANNEL` | 5 | A unit lists PHASE, which is not declared. |
| [`i70_duplicate_channel_in_unit`](invalid/i70_duplicate_channel_in_unit.toml) | Extra | `E_DUPLICATE_CHANNEL_IN_UNIT` | 5 | channels = ["DNA", "ACTIN", "DNA"]. |
| [`i71_target_not_text`](invalid/i71_target_not_text.toml) | Owner decision 1 | `E_TYPE` | 3 | target = 5 (plain strings only). |
| [`i72_member_unknown_condition`](invalid/i72_member_unknown_condition.toml) | Extra | `E_UNKNOWN_CONDITION` | 5 | A member for undeclared condition DrugB. |
| [`i73_condition_without_members`](invalid/i73_condition_without_members.toml) | Extra | `E_CONDITION_WITHOUT_MEMBERS` | 5 | Condition DrugB declared, no member. |
| [`i74_source_folder_in_two_repeats`](invalid/i74_source_folder_in_two_repeats.toml) | Extra: repeat pairing | `E_SOURCE_REPEAT_REUSED` | 5 | Source folder CTRL/exp7 belongs to repeats Day2 and Day3. |
| [`i75_repeat_id_swap`](invalid/i75_repeat_id_swap.toml) | Extra: renames | `E_REPEAT_ID_SHADOWS_SOURCE` | 5 | Repeat rep1 holds folder rep2 and repeat rep2 holds folder rep1 for CTRL. |
| [`i76_display_name_collision_repeats`](invalid/i76_display_name_collision_repeats.toml) | Owner refinement | `E_DISPLAY_NAME_COLLISION` | 5 | Repeats rep1 and rep2 both display as "Day 1". |
| [`i77_display_name_collision_channels`](invalid/i77_display_name_collision_channels.toml) | Owner refinement | `E_DISPLAY_NAME_COLLISION` | 5 | Channels DNA and ACTIN both display as "DAPI". |
| [`i78_non_nfc_condition_key`](invalid/i78_non_nfc_condition_key.toml) | Owner decision Q3 | `E_ID_NOT_NFC` | 4 | The condition key is decomposed "Cafe\u0301"; refused, never normalized. |
| [`i79_mask_source_channel_unknown`](invalid/i79_mask_source_channel_unknown.toml) | Extra: masks | `E_UNKNOWN_CHANNEL` | 5 | source_channels names undeclared Hoechst. |
| [`i80_mask_source_type_reused`](invalid/i80_mask_source_type_reused.toml) | Extra: masks | `E_MASK_SOURCE_TYPE_REUSED` | 5 | Two masks with source_type nuclei. |
| [`i81_header_names_duplicate`](invalid/i81_header_names_duplicate.toml) | Extra: aliases | `E_DUPLICATE_VALUE` | 5 | header_names = ["DAPI", "DAPI"]. |
| [`i82_retired_repeats_forbidden`](invalid/i82_retired_repeats_forbidden.toml) | Owner refinement | `E_FORBIDDEN_FIELD` | 3 | A `retired_repeats` table: IDs are immutable, v1 has no rename table. |
| [`i83_non_nfc_reference`](invalid/i83_non_nfc_reference.toml) | Owner decision Q3 | `E_ID_NOT_NFC` | 4 | A composed key referenced decomposed: refused in phase 4, not resolved through normalization. |
| [`i84_non_nfc_source_repeat`](invalid/i84_non_nfc_source_repeat.toml) | Owner decision Q3 | `E_ID_NOT_NFC` | 4 | A decomposed `source_repeat`. |
| [`i85_non_nfc_used_id`](invalid/i85_non_nfc_used_id.toml) | Owner decisions Q1, Q3 | `E_ID_NOT_NFC` | 4 | A decomposed retired ID in `used_ids`. |
| [`i86_display_name_collision_case`](invalid/i86_display_name_collision_case.toml) | Owner decision Q2 | `E_DISPLAY_NAME_COLLISION` | 5 | "Control" and "control". |
| [`i87_display_name_collision_casefold`](invalid/i87_display_name_collision_casefold.toml) | Owner decision Q2 | `E_DISPLAY_NAME_COLLISION` | 5 | Channels "Stra\u00dfe" and "STRASSE" (full case folding). |
| [`i88_display_name_collision_nfc_and_case`](invalid/i88_display_name_collision_nfc_and_case.toml) | Owner decision Q2 | `E_DISPLAY_NAME_COLLISION` | 5 | Repeats "Cafe\u0301 1" and "CAF\u00c9 1". |
| [`i89_reference_names_display_name`](invalid/i89_reference_names_display_name.toml) | Audit L1; owner decision A4 | `E_REFERENCE_UNKNOWN` | 5 | `reference` is the display name "Control" of CTRL. |
| [`i90_member_keyed_by_display_name`](invalid/i90_member_keyed_by_display_name.toml) | Audit L1 | `E_UNKNOWN_CONDITION` | 5 | A member keyed by the display name "Control". |
| [`i91_unit_lists_channel_display_name`](invalid/i91_unit_lists_channel_display_name.toml) | Audit L1 | `E_UNKNOWN_CHANNEL` | 5 | A unit lists the channel display name "DAPI". |
| [`i92_used_ids_missing`](invalid/i92_used_ids_missing.toml) | Owner decision Q1 | `E_MISSING_FIELD` | 3 | No `used_ids` table. |
| [`i93_used_id_not_listed`](invalid/i93_used_id_not_listed.toml) | Owner decision Q1 | `E_USED_ID_MISSING` | 5 | DrugA declared but not in `used_ids.conditions`. |
| [`i94_used_ids_duplicate`](invalid/i94_used_ids_duplicate.toml) | Owner decision Q1 | `E_DUPLICATE_VALUE` | 5 | rep1 listed twice. |
| [`i95_used_id_case_collision`](invalid/i95_used_id_case_collision.toml) | Audit B2, B11; owner decision Q1 | `E_ID_CASE_COLLISION` | 4 | Retired `ctrl` against declared CTRL. |
| [`i96_used_ids_mapping`](invalid/i96_used_ids_mapping.toml) | Owner decision Q1 | `E_TYPE` | 3 | `used_ids.repeats` is a mapping table, not a list. |
| [`i97_used_ids_unknown_kind`](invalid/i97_used_ids_unknown_kind.toml) | Owner decision Q1 | `E_UNKNOWN_FIELD` | 3 | `used_ids.masks`. |
| [`i98_confirmed_on_missing`](invalid/i98_confirmed_on_missing.toml) | Audit L8; owner decision A3 | `E_MISSING_FIELD` | 3 | No `confirmed_on`: no default exists. |
| [`i99_labchronicle_provenance`](invalid/i99_labchronicle_provenance.toml) | Owner decision Q5 | `E_FORBIDDEN_FIELD` | 3 | A top-level `labchronicle` table. |
