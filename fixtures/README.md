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
  scenarios P01-P12 in the [conformance plan](../docs/conformance-plan.md#3-physical-scenarios-preprocessing-owned),
  built on the valid files below.
- `v18` MUST parse to the same model as `v01` (round trip); `v21` differs from `v01` only in the
  `conditions` section (section digests for `channels`, `repeats`, `masks` equal).

## Syntax check (6 November 2026)

Checked with Python 3.13 `tomllib` (`tomllib.loads` on the UTF-8 decoded bytes):

- `valid/`: 21 of 21 parse.
- `invalid/`: 73 of 81 parse as TOML and are invalid only by the v1 rules. The 8 phase-1 fixtures
  fail deliberately: `i01_bom` (`TOMLDecodeError`, BOM read as an invalid statement),
  `i02_invalid_utf8` (`UnicodeDecodeError`), `i03`-`i06` (`TOMLDecodeError`, "Cannot declare ...
  twice" / "Cannot overwrite a value"), `i07`, `i08` (`TOMLDecodeError`, "Invalid value" /
  "Expected newline").

The expected codes were also cross-checked once against a throw-away script implementing
experiment-v1 (not committed, not a reference implementation): every valid file passed with the
listed warnings and every invalid file produced exactly its listed set. This is not a conformance
claim for any brick.

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
| Case collisions | `i48`-`i53`, `i68` (no folding when resolving) |
| Unknown and forbidden fields | `i16`-`i19`; `i20`-`i26` |
| Implicit-conversion traps | `i07`, `i08`, `i12`-`i14`, `i19`, `i27`-`i30`, `i33`, `i34`, `i36`, `i38`, `i39`; valid side `v15` |
| Reference DAG | `i64`-`i68`, `i41`; `v10`, `v19` |
| Swapped channel order | `v04`, `v06` |
| Extra / missing channel | `v05`, `v17`, `i69`, `i71` |
| Within-unit divergence | `i20`; P01, P02 |
| Instance vs binary masks | `v07`, `v08`, `i42`, `i43`; P05 |
| Partial masks | `v09` |
| Renames | `v16`, `i53`, `i75`-`i78`; P08 |
| Aliases (header evidence) | `v11`, `v12`, `i46`, `i81`; P03 |
| Versioning | `i09`-`i15` |
| Identities | `v14`, `v15`, `v20`, `i54`-`i63` |
| Encoding | `i01`, `i02` |

## Valid fixtures (21)

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
| [`v16_explicit_repeat_rename`](valid/v16_explicit_repeat_rename.toml) | Extra: renames | pass | yes | The user explicitly renamed canonical repeat rep1 to Day1 and removed repeat rep9; both are recorded in retired_repeats, so neither ID can be reused. Source labels are unchanged. |
| [`v17_partial_channel_presence`](valid/v17_partial_channel_presence.toml) | Adversarial 9; addendum §3 | pass | **no** | PHASE exists only in CTRL/R002/acquisition_1. For a PHASE request R002 is partially represented and R001 unavailable: the analysis layer must refuse (A_SCOPE_INCOMPLETE) or record a user-selected subset, never drop or re-weight silently. |
| [`v18_inline_and_dotted_forms`](valid/v18_inline_and_dotted_forms.toml) | Extra: round trip | pass | yes | Same model as v01 written with inline tables, dotted keys and quoted keys; parse(v18) must equal parse(v01). |
| [`v19_warnings_unpaired`](valid/v19_warnings_unpaired.toml) | Extra: reference DAG semantics | pass + `W_REFERENCE_UNPAIRED`, `W_REPEAT_MISSING_CONDITIONS` | yes | Valid with warnings: CTRL only in rep1, DrugA only in rep2, so the repeats miss conditions (W_REPEAT_MISSING_CONDITIONS) and DrugA cannot be paired with its reference (W_REFERENCE_UNPAIRED). |
| [`v20_unicode_and_spaces`](valid/v20_unicode_and_spaces.toml) | Extra: identities | pass | yes | Condition folder labels with spaces and non-ASCII text are valid labels (quoted keys); channel and mask IDs stay tokens. |
| [`v21_metadata_only_edit`](valid/v21_metadata_only_edit.toml) | Adversarial 10 | pass | yes | v01 with only the conditions section edited (labels, target, treatment_key). The channels, repeats and masks section digests equal v01's, so no pixel-derived product may be invalidated. |

## Invalid fixtures (81)

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
| [`i53_case_collision_retired_vs_current`](invalid/i53_case_collision_retired_vs_current.toml) | Extra: renames | `E_ID_CASE_COLLISION` | 4 | Retired REP1 vs current rep1. |
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
| [`i71_unused_channel`](invalid/i71_unused_channel.toml) | Extra: missing channel | `E_UNUSED_CHANNEL` | 5 | PHASE declared but acquired by no unit. |
| [`i72_member_unknown_condition`](invalid/i72_member_unknown_condition.toml) | Extra | `E_UNKNOWN_CONDITION` | 5 | A member for undeclared condition DrugB. |
| [`i73_condition_without_members`](invalid/i73_condition_without_members.toml) | Extra | `E_CONDITION_WITHOUT_MEMBERS` | 5 | Condition DrugB declared, no member. |
| [`i74_source_folder_in_two_repeats`](invalid/i74_source_folder_in_two_repeats.toml) | Extra: repeat pairing | `E_SOURCE_REPEAT_REUSED` | 5 | Source folder CTRL/exp7 belongs to repeats Day2 and Day3. |
| [`i75_repeat_id_swap`](invalid/i75_repeat_id_swap.toml) | Extra: renames | `E_REPEAT_ID_SHADOWS_SOURCE` | 5 | Repeat rep1 holds folder rep2 and repeat rep2 holds folder rep1 for CTRL. |
| [`i76_retired_id_reused`](invalid/i76_retired_id_reused.toml) | Extra: renames (never reuse an ID) | `E_REPEAT_ID_REUSED` | 5 | rep1 is both retired and current. |
| [`i77_retired_chain_dangling`](invalid/i77_retired_chain_dangling.toml) | Extra: renames | `E_RETIRED_CHAIN` | 5 | Retired Day0 replaced_by Day9, which is neither current nor retired. |
| [`i78_retired_chain_cycle`](invalid/i78_retired_chain_cycle.toml) | Extra: renames | `E_RETIRED_CHAIN` | 5 | Retired A -> B -> A never reaches a current repeat. |
| [`i79_mask_source_channel_unknown`](invalid/i79_mask_source_channel_unknown.toml) | Extra: masks | `E_UNKNOWN_CHANNEL` | 5 | source_channels names undeclared Hoechst. |
| [`i80_mask_source_type_reused`](invalid/i80_mask_source_type_reused.toml) | Extra: masks | `E_MASK_SOURCE_TYPE_REUSED` | 5 | Two masks with source_type nuclei. |
| [`i81_header_names_duplicate`](invalid/i81_header_names_duplicate.toml) | Extra: aliases | `E_DUPLICATE_VALUE` | 5 | header_names = ["DAPI", "DAPI"]. |
