# S0.1 fixed-SHA consumer audit: experiment description v1

- **Date:** 6 November 2026. **Roadmap item:** S0.1 (TODO before Gate G0), [roadmap.md](../roadmap.md) §5.
- **Spec audited against:** `docs/experiment-v1.md`, `fixtures/` and `docs/conformance-plan.md` of
  PR #3 (branch `claude/stage0-spec`, head `e39994c`, which includes the fixture fixes of this
  audit's conformance check, §8). Section numbers (§) below are experiment-v1's unless marked.
- **Scope:** read-only. No consumer repository was changed. Every citation is `file:line` at the
  SHA in §1. This audit is evidence for Gate G0; it is not a conformance claim for any brick.

## Summary

1. **No brick reads experiment semantics except through preprocessing.** CellPatcher, MorphoFeature
   and (through MorphoFeature) MorphoEmbed use preprocessing's strict `read_confirmed_design`; the
   normalization brick takes a `repeat_groups` mapping. Only preprocessing parses
   `experiment_design.csv`. This matches the spec's single-reader rule (§8, conformance plan §1).
2. **Canonical repeat identity does not reach the statistics.** Every brick keys FOVs, patches,
   scaling and exports on the **source folder label** `biological_repeat`; the repeat group is
   used only to pool normalization/scaling. MorphoFeature's MorphoCoverage export carries no
   repeat group, and MorphoCoverage pairs repeats and derives its FDR families from the raw label.
   `v03` (`rep1` + `experiment_23` = `Day1`) would be two unpaired repeats in MorphoCoverage today.
3. **Channel identity is header names or C indices, never a confirmed canonical ID.** fiberfeatures
   selects channels by header name; MorphoFeature compares its declared names with header names
   and, without a run file list, uses the header names as channel identities; MorphoRelate and
   CellPatcher use C indices; normalization writes `_C<i>` columns. The spec's `DNA` confirmed by
   header `DAPI` (`v11`) is refused by MorphoFeature and unreachable in fiberfeatures today.
4. **Four existing behaviours contradict normative v1 text** and must change in Stage 1 (or the
   spec must change): preprocessing fills `confirmed_on` from the clock; drops removed folders
   without asking; trims header channel names; and supports RGB images, which v1 refuses (D8).
5. **Mask semantics:** the merged 2-D-only restriction and mask fingerprint binding agree with the
   spec (no axes/shared fields; files and fingerprints in the manifest). Gaps: no consumer knows a
   mask's `binary`/`instances` representation, CellPatcher and MorphoObjects treat an integer 0/1
   mask as one object, and MorphoRelate's third representation `parent_labels` has no v1 value.
6. **Fixture conformance:** a throw-away reference validator accepts 27/27 valid and refuses 99/99
   invalid fixtures exactly as catalogued; two transition fixtures were corrected in PR #3
   (`e39994c`); one transition (`t03`) depends on an ambiguity (§8, owner question Q1).

## 1. Evidence base

| Repository | Ref | Full SHA read | Commit date |
|---|---|---|---|
| morphobricks-preprocessing | `v0.4.0` | `bc7b872bd3ccb30dcd5de812e99a3485a3281825` | 2026-11-05 |
| morphobricks-preprocessing | `main` | `34cbf1c24fbd871ac2247e8cdff5518b43253c84` | 2026-11-06 |
| morphobricks-normalization | `v0.3.4` | `1c1c7b48a041e23bd390037bd6ab837e1e5f1c85` | 2026-11-05 |
| morphobricks-normalization | `main` | `5848efce8b58b59a3f54776b8d118d62089ce6ed` | 2026-11-06 |
| CellPatcher | `v0.2.0` | `498825e977f1df5be623416bcacc7464990486e9` | 2026-11-05 |
| CellPatcher | `main` | `031bba9456d491cf03adce877a1c7b9a3835a89a` | 2026-11-06 |
| MorphoFeature | `v0.1.0` | `182b3735d33eac7d40902f82d69885ef6fb3aae8` | 2026-11-06 |
| MorphoFeature | `main` | `60f4a92cb42716184b3ea7d0b804c873a8dd0852` | 2026-11-06 |
| MorphoRelate | `v0.1.1` | `160ad2314ed2f156666421add2d3ba269cf8abb7` | 2026-11-06 |
| fiberfeatures | `v0.2.1` | `8798b7585ec91f7c380f815de95bc34f82eb401a` | 2026-11-06 |
| MorphoEmbed | `v0.1.0` | `3c16bce2bb6b08f73e693dc23b15a2048bfa6649` | 2026-11-06 |
| MorphoObjects | `v0.1.0` | `478c916ea601f150c062cc4326fe9413e9e5500f` (= `main`) | 2026-11-06 |
| MorphoCoverage | `main` (no tag) | `64ff307d90fe5eb62a72630f35b85bd7fe6040a4` | 2026-11-03 |

Citations without a ref are at the tag; `@main` marks the main SHA. Where main differs from the tag
only outside experiment semantics, this is stated per brick.

**Spec citation check.** experiment-v1 §3.2 cites preprocessing `a786290b` for `check_identity_text`
and MorphoFeature `803e617a` for `naming.py`. `a786290` is a main merge after `v0.4.0`; `803e617` is
on MorphoFeature's unmerged `claude/restart-doc` branch (in neither `v0.1.0` nor `main`). Both files
are byte-identical to the released tags (`git diff v0.4.0 a786290 -- discovery.py` and
`git diff v0.1.0 803e617 -- naming.py` are empty), so the rules are right, but the spec should cite
the release tags (`bc7b872`, `182b373`).

Not audited: notebooks (`.ipynb`) line by line, LabChronicle (not a consumer), test suites.

## 2. morphobricks-preprocessing (reference reader in v1)

### 2.1 How it reads experiment semantics today

| Topic | Today | Citation |
|---|---|---|
| Labels | Folder labels pass `check_identity_text` (D-e): no outer whitespace, not `""`/`NA`/`nan`/`none`/`null`/`n/a`/`<NA>` | `discovery.py:60`, `discovery.py:69-106`; contract `docs/contract.md:28` |
| Case | One spelling per level in the whole experiment (`case_conflict`), by `str.casefold`, no NFC | `discovery.py:430`, `discovery.py:146-190` |
| `single` | Lower-case `single` folder only when alone; `Single` is `reserved_folder_name` | `discovery.py:436-443`; contract `:26` |
| Design file | `experiment_design.csv` v1: `condition`, `biological_repeat`, `repeat_group`, `control`, `image_count`, `technical_repeat_count`, `confirmed`, `confirmed_on`, `schema_version` | `design.py:45-56`; contract §12 `:384-414` |
| Pairing | Default group = folder name; user moves folders; one folder per condition per group | `design.py:225-251`; contract `:405` |
| Controls | Boolean per condition, "recorded only" | `design.py:169-171`; contract §12 |
| Reconciliation | Known folders keep group/control/confirmation; a new folder joins the group named after it and reopens it; **removed folders are dropped without asking** | `design.py:375-427` (drop `:425`); contract `:408` |
| Readers | Lenient `read_experiment_design` (BOM ignored, `yes`/`no`/`1`/`0`/empty, header compared ignoring case) for the user's edits; strict `read_confirmed_design` for every other brick | `design.py:494-537`, `design_values.py:27-50`; `design.py:540-637` |
| `confirmed_on` | Filled from the clock for rows confirmed without a date: `run` uses `datetime.now()`, the CLI and notebook `date.today()` | `design.py:299-307`; `run/steps.py:95`; `cli_run.py:522-524`; `notebook_design.py:318`; contract `:411` |
| Channel names | OME `Channel@Name` / OME-Zarr labels, **outer whitespace trimmed** (`channel_names_trimmed`); compared across the experiment by C index (`channel_names_differ`) | `metadata.py:513-533`, `zarr_input.py:53-72` (strip `:68`), `metadata.py:584-622`; contract `:61` |
| Channel count | One count per experiment (`different_channel_counts`, N43) | `size_checks.py:86-121`; contract `:65` |
| RGB | `image_type = rgb` supported: TIFF RGB samples `S` become C0-C2, normalized jointly downstream | `image_type.py:29-30`, `image_type.py:98-106`; contract §13 `:416-430` |
| `RunInputs` | `fovs()` (`Fov.channel_names` by C index), `mask_types()`, `read_mask()`, `design()` via the strict reader and the manifest SHA-256 | `run_inputs.py:101-140`, `:308-352`, `:358-380` |

### 2.2 Merged mask restriction vs the spec's mask semantics

| Preprocessing (v0.4.0 + main) | Spec v1 | Verdict |
|---|---|---|
| Z > 1 images refused (`z_stack_not_supported`); T allowed (contract `:63`); masks of a time-lapse need the same T, stated `TYX` when unnamed (contract `:469-470`) | 2-D only; no Z, axes, shared or projection field (§1, §4.7 `E_FORBIDDEN_FIELD`; `i21`) | **Agrees.** Stated mask axes (`--mask-axes Cells=TYX`) stay a run input recorded in the manifest (`axes_from: "stated"`), not in `morphobricks.toml` |
| Shared 2-D mask removed: statement `YX` is `shared_mask_not_supported` (`masks/stated.py:7`; contract `:470`); `RunInputs` refuses a recorded `shared: true` (contract §9.1) | `shared`, `plane_scope` forbidden | **Agrees** |
| Masks bound to fingerprints for the whole run; change during a scan is `mask_changed_during_scan` (`mask_binding.py:48-281@main`; contract `:495@main`) | Files, pairing, completeness, fingerprints stay in the run manifest (§4.5) | **Agrees.** Progressive segmentation (`v09`, P11) means a preprocessing re-run per mask batch: `RunInputs` refuses masks the run did not record (`UnrecordedFilesError`, contract §9.1) |
| Mask type = folder, suffix or OME-Zarr label-image name; `mask_names_differ_in_case` (`masks/files.py:265-281`; contract `:468`) | `source_type` = discovered type, Label rules, case-collision scope "mask source types" (§3.3) | Case rule agrees. **Gap:** mask type names are not checked with `check_identity_text` (`masks/files.py` has no call), so a type `NA` or ` cells` is discovered today but cannot be written as `source_type` (`E_ID_TEXT`). Stage 1 needs a discovery refusal; the spec has no `R_*` code for it (Q11) |
| Mask "kind" `empty` / `one_value` / `grouped` / `instances` inferred from pixels in the optional mask step, as a suggestion (`mask_scan.py:465-485`; contract `:487-492`) | `representation` user-confirmed, never inferred (§4.5) | Compatible only if the kind is shown as evidence and never pre-fills `representation`. `grouped` is MorphoRelate's `parent_labels`, which v1 cannot express (Q8) |
| Negative / > int32 labels refused when pixels are read (contract §15.1) | `binary` with > 2 values is `R_MASK_CONTRADICTS_REPRESENTATION` | **Unknown when it runs:** the check needs every mask's pixels; the mask step is optional and per run. Stage 1 must say whether it is part of publication, of `run`, or of the mask step (Q10) |

### 2.3 Places that change in Stages 1-3

- **Stage 1 (authoring, reference reader):** new reader/validator/writer for `morphobricks.toml`
  (phases of §6, canonical bytes §9.1, digests §9.3); `R_*` refusals of §8; derivation of
  `experiment_design.csv` (§11) replacing `write_experiment_design` as the source of truth
  (`design.py:640-674`); `reconcile_design` (`design.py:375-427`) becomes the unit-level
  reconciliation of §10 with drafts and base SHA-256; NFC refusal of folder labels
  (`R_FOLDER_NOT_NFC`; `discovery.py:69-106` has no NFC check, `design_values.py:13` imports
  `unicodedata` only for format characters); header evidence per unit replacing
  `channel_names_differ` (`metadata.py:584-622`); `different_channel_counts`
  (`size_checks.py:86-121`) becomes `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` / per-unit counts;
  `RunInputs` gains canonical channel and repeat APIs and `A_DRAFT_REFUSED`.
- **Behaviour that contradicts v1 and must change:**
  1. `confirmed_on` from the clock (`design.py:299-307`, `run/steps.py:95`, `cli_run.py:524`;
     contract `:411` "Confirmed rows without a date get the date of the run") vs §4.4a
     ("A writer MUST NOT default, infer or refresh it", "absent is `E_MISSING_FIELD`"). The
     notebook/CLI confirmation actions (`notebook_design.py:318`, `run/design_file.py:135`) record
     the date of a user action, which §4.4a allows; filling a hand-confirmed row at run time does not.
  2. Removed folders dropped without asking (`design.py:425`; contract `:408`) vs §10 ("removed only
     on user confirmation").
  3. Header names trimmed (`zarr_input.py:68`; contract `:61`) vs §4.3 ("exactly ... no trimming").
     Either the spec states that header names are compared as preprocessing records them (trimmed,
     `channel_names_trimmed` in the manifest) or Stage 1 keeps the raw names for evidence (Q7).
  4. RGB supported (`image_type.py`; contract §13) vs D8 `R_RGB_NOT_SUPPORTED`. A user with RGB data
     loses a working path once the file is required (Q6).
- **Legacy migration (§7):** the strict reader refuses `yes`/`no` (good), but a legacy group's
  `confirmed_on` is per row and `ExperimentDesign.confirmed_on` takes the latest
  (`design.py:216-218`); v1 has one date per repeat. A group whose rows carry different dates cannot
  migrate byte-identically to §11 (Q12). Groups that swapped folder labels (`rep1` holding `rep2`)
  are refused (`E_REPEAT_ID_SHADOWS_SOURCE`), as §7 requires: a deliberate break, to be named in
  the release notes.
- **Unchanged and consistent:** Label rules (`check_identity_text` = spec Label), case scope
  (`check_identity_case` = spec scopes for labels), `single` rules, strict reader as the only
  cross-brick reader, manifest SHA-256 binding of the design.

## 3. morphobricks-normalization

`main@5848efc` differs from `v0.3.4` only in numerical refusals (`normalization.py`, `pooling.py`);
experiment semantics are identical.

| Topic | Today | Citation |
|---|---|---|
| Repeat groups | `scope_groups(..., repeat_groups)`; `None` **groups by the `biological_repeat` folder label** | `scopes.py:1-20`, `scopes.py:33-75`, `_repeat_group` `scopes.py:135-141` |
| Pairing checks | Missing pair refused; non-text/empty label refused; two repeats of one condition in a group refused | `scopes.py:118-132`, `_check_pairing` `scopes.py:144-170` |
| Missing conditions | Warning `repeat_missing_conditions` (= `W_REPEAT_MISSING_CONDITIONS`) | `scopes.py:182-200` |
| Group name | `normalization_group` = repeat group label (with `::t=<t>` per time point) | `scopes.py:77-79`, `fitting.py:48-53` |
| Channels | Per C index: `Normalization_Offset_C<i>`, `Normalization_Scale_C<i>`, histogram `_C<i>` columns; one channel count per experiment (N43) | `fitting.py:56-66`, `csv_io.py:86-91`, `records.py:203-220` |
| RGB | Joint RGB normalization (`check_rgb`) | `rgb.py:77`, `fitting.py:387` |

**Spec implications.** The pairing input is already a mapping, so v1's canonical repeat IDs fit
without an API change (Stage 2: pass canonical IDs). The `None` fallback (folder-name grouping) is
the behaviour v1 forbids when a description exists: callers must always pass the mapping. Pooling
and parameter columns by C index are the Stage 3 breaking change (a table schema keyed by
canonical channel ID); until then, `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` keeps C index = canonical
position for every unit. `normalization_group` text with `::t=` is built by concatenation: a
repeat ID containing `::t=` is a valid Label and would be ambiguous in that column (minor; Stage 2).

## 4. CellPatcher

`main@031bba9` differs from `v0.2.0` in Z handling only (2-D-only follow-up #83); experiment
semantics are identical.

| Topic | Today | Citation |
|---|---|---|
| Design | `load_experiment_design` reads the run's published design with `read_confirmed_design` and the manifest SHA-256; scope `biological_repeat` only | `normalization.py:133-175` |
| Labels | FOV key from `RunInputs`; in-memory runs take labels from `config.common` | `file_runs.py:78`, `file_runs.py:290-341`; `config.py:42-49` |
| Patch identity | `patch_id = condition/biological_repeat/technical_repeat/position_id/...` with `c=<c>` | `ids.py:8-16`, `ids.py:209` |
| Channels | By C index: `split_channels` (indices), `mask_channel` (index into a multi-channel mask) | `config.py:88`, `config.py:201-230` |
| Masks | `mask_type` names the recorded type; integer masks are instances, **a 0/1 integer mask is one object**; boolean masks refused unless `binary_mask_policy="connected_components"` | `config.py:70-95`, `config.py:351-363`, `pipeline.py:805-810` |

**Spec implications.** Repeat groups: already canonical-ready (Stage 2 swaps the source). Patch
IDs and the FOV key use the source folder label, which v1 keeps as provenance; whether the key stays
the source label is open (Q5). Channels by index must become canonical IDs (Stage 3; adversarial
test 3, `v04`, `v06`). A `binary` mask requested as an object set must be refused before
CellPatcher sees it (`A_MASK_NOT_INSTANCES`): today a 0/1 region mask silently becomes one object
per FOV, and `connected_components` is an explicit opt-in that turns a binary mask into instances
(Q9).

## 5. MorphoFeature

`main@60f4a92` changes experiment semantics only in `fits.py` (#95: an image fit uses the design the
run recorded, `fits.py:127@main`); channels, naming and export are unchanged.

| Topic | Today | Citation |
|---|---|---|
| Design | `ExperimentDesign.read` / `from_run` via preprocessing; without a design, **repeats of one name are one group** (`BY_NAME`) | `experiment_design.py:22-95`, `experiment_design.py:97` |
| Scaling keys | Fitted scaling is keyed by **source `biological_repeat` name**; a design that puts two same-named source folders in different groups is refused ("rename one repeat") | `scaling.py:13-20`, `scaling.py:211-221` |
| Cache key | Fit memo key includes the **whole-file** design SHA-256 | `fits.py:224-232` (`fits.py:288@main`) |
| Channels | Run file `channels:` one global list by C index; without it, the **header names become the channel names**; declared names must equal header names (`check_metadata_names`); FOVs must declare the same set | `run_config.py:1-35`, `run_config.py:326-347`; `channels.py:93-117`, `channels.py:149-177` |
| Naming | Token regex, compartment list, `in`-part object-set rule (the spec's Token and Object-set rules) | `naming.py:15-20`, `naming.py:44-59` |
| Masks | Run file `masks:` object set → recorded mask type (= spec mask ID → `source_type`); no representation | `run_config.py:11-13`, `run_config.py:408`; `fov_files.py:222-230` |
| Controls | Displayed only | `notebook_steps.py:166`, `notebook_steps.py:250` |
| MorphoCoverage export | FOV key fields only (`condition`, `biological_repeat`, `technical_repeat`, `position_id`); no repeat group | `identity.py:30`; `coverage_export.py:67`, `coverage_export.py:102`, `coverage_export.py:188` |

**Spec implications.**

- `check_metadata_names` and the header-names-as-IDs fallback contradict §4.3 (header names are
  evidence only, never inferred as IDs, even when equal): `v11` (`DNA` with header `DAPI`) is
  refused today. Stage 2: channel catalogues come from `RunInputs` per unit.
- `require_same_channels` refuses heterogeneous units (`v05`, `v17`): Stage 3, with
  `A_SCOPE_INCOMPLETE` and full/partial/unavailable classification instead.
- Scaling keyed by source name breaks valid v1 designs: `CTRL/rep1 → Day1`, `DrugA/rep1 → Day2`
  is valid (no shadowing: neither repeat is named `rep1`) and is refused by `scaling.py:211-221`.
  Stage 2: key by canonical repeat ID, with MorphoEmbed's lookup (§7).
- The fit cache key uses the whole design SHA-256; §9.3 says whole-file SHA is provenance and
  derived products key on the `repeats` section digest only (a `display_name` or `reference`
  edit must not refit).
- `BY_NAME` folder-name grouping is the fallback v1 removes once a description exists.
- The export must carry the canonical repeat ID for S2.5 (adversarial 8).
- Object-set naming agrees with the spec's mask-ID rules (`naming.py:44-59` = §3.2 Object set).

## 6. MorphoRelate (`v0.1.1`)

| Topic | Today | Citation |
|---|---|---|
| Channels | Config `channels`: name → C index, one count for the experiment; default placeholders `ch0`, `ch1`, ... | `project_config.py:101-128`; `project.py:121-127` |
| Name rules | NFC, no outer spaces, no `__`, no outer `_`, case-insensitive uniqueness, `in` part refused for masks, and **reserved column names** `condition`, `biological_repeat`, `repeat`, `technical_repeat`, `position_id`, `image_file`, `image_path`, `mask_file`, `patch_file`, `patch_id`, `label_id`, `z`, `z0`, `z1`, `c`, `t` | `registry/_expand.py:41-59`, `registry/_expand.py:68-115` |
| Mask representation | User-declared, never inferred: `instances`, `binary`, **`parent_labels`**; features accept representations by a table | `registry/_spec.py:59-83`; `project.py:107-118` |
| Repeats | FOV key from `RunInputs` only; no pairing | `io/run_source.py:261-264` |

**Spec implications.** The spec's channel/mask Token rule does not exclude MorphoRelate's
reserved column names: a channel `t`, `c` or `z`, or a mask `label_id`, is valid v1 and refused by
MorphoRelate (roadmap §4.5 requires the intersection of downstream constraints; Q4). v1's
`representation` enum lacks `parent_labels`, which MorphoRelate supports and preprocessing detects
(`grouped`): such a mask can be declared neither `instances` (wrong objects) nor `binary` (> 2
values: `R_MASK_CONTRADICTS_REPRESENTATION`) (Q8). MorphoRelate's `binary` accepted by features
declared `binary` (`_spec.py:75-83`) matches v1's meaning. The `ch<i>` defaults are positional
names: Stage 2 should take canonical IDs from `RunInputs`.

## 7. fiberfeatures, MorphoEmbed, MorphoObjects

| Brick | Today | Citation | Spec implication |
|---|---|---|---|
| fiberfeatures `v0.2.1` | Channels chosen **by header name** ("by the names in the image metadata, never by position"); `None` = every channel | `run_reading.py:110-145`, `run_reading.py:256-270` | Header names are evidence, not identity: the same header may be evidence for different channels across units (§4.3), so name selection can mix channels once layouts differ, and `DNA`/`DAPI` cannot be requested. Stage 2: select by canonical ID |
| fiberfeatures | FOV labels and identity columns from the run | `batch.py:97`, `batch.py:369`, `batch.py:446` | Source labels as provenance (Q5) |
| MorphoEmbed `v0.1.0` | Fitted scaling looked up by `fov["biological_repeat"]` (source label) or the full FOV key; no fallback | `provider_request.py:395-425`; `provider_crops.py:57`, `provider_crops.py:249` | Must look up the canonical repeat ID together with MorphoFeature's change (§5) |
| MorphoObjects `v0.1.0` | Boolean object set refused ("a binary mask is not an instance mask"); any integer mask is instances, a 0/1 mask one object; feature `representation` default `instances` | `validation.py:57-63`; `spec.py:182` | An integer `binary` region mask is measured as one object: `A_MASK_NOT_INSTANCES` must be raised by MorphoFeature before the provider (Q9) |

## 8. MorphoCoverage (`main@64ff307`, no release)

| Topic | Today | Citation |
|---|---|---|
| Group columns | `condition`, `biological_repeat`, `technical_repeat` from the linked tables | `metadata.py:36` |
| FDR families | Derived from conditions sharing a biological repeat (`experiments`), or declared `Setup(experiment=...)` | `sampling_unit/_experiments.py:1-20`, `:38-52`, `:55-66`; `contrast_cells.py:521` |
| Comparisons | `(condition, reference)` pairs, per biological repeat where both are imaged | `_control.py:1-10`, `_control.py:83-103` |
| Control guess | Name words (`ctrl`, `mock`, `dmso`, `nt`, ...) and reagent stems | `workflows/scan.py:102-105`, `workflows/scan.py:247-262` |
| `target` | Optional FOV-table column; `reagent_agreement` **groups conditions by `target`** | `metadata.py:38-40`; `contrast_repeats.py:283-313` |

**Spec implications.** Pairing and FDR families depend on repeat identity: with source labels,
`v03` gives no shared repeat for `DrugA` vs `CTRL`. S2.5 must deliver canonical repeat IDs in the
`biological_repeat` column (or a new one; Q5). `reference` edges replace name guessing for the
primary control, consistent with §7 (no name-stem guessing). `reagent_agreement` grouping by
`target` contradicts §4.2a ("MUST NOT use either for grouping ... contrasts, family definitions")
if the column is filled from `morphobricks.toml` (Q3). The forbidden `experiment` field (§4.7,
`i25`) correctly leaves FDR families to MorphoCoverage configuration.

## 9. Fixture conformance check

A throw-away reference validator (Python 3.13 `tomllib`, about 670 lines, not committed: the Spec
repository holds no runtime code) implemented §2-§6 phase by phase and the predecessor checks of
§4.4a, §4.6 and §4.9 expressible from two files. It was run on every fixture at `a9e9697`, then at
`e39994c` after the fixes.

| Set | Result at `a9e9697` | Result at `e39994c` |
|---|---|---|
| `valid/` (27) | 27 accepted, exact warnings | same |
| `invalid/` (99) | 99 refused with exactly the catalogued code set and phase | same |
| `transitions/` alone (5) | 5 valid (`t03` with `W_REPEAT_MISSING_CONDITIONS`) | same |
| `v18` = `v01`; `v16`, `v21` digests = `v01` | equal | equal |
| Transitions vs predecessor | **3 mismatches:** `t01`, `t02` also `R_USED_ID_DROPPED`; `t03` also `R_CONFIRMED_ID_CHANGED` | `t01`, `t02`, `t04`, `t05` match; `t03` open (Q1) |

Fixes committed on `claude/stage0-spec` (`e39994c`):

- `t01`: `used_ids.repeats` dropped `rep1`, `rep2`, so §4.9(a) also refused it. It now keeps them
  (append-only); the candidate is refused only with `R_CONFIRMED_ID_CHANGED`.
- `t02`: ACTIN → Actin cannot keep `ACTIN` in `used_ids` (`E_ID_CASE_COLLISION`, §4.9), so the
  candidate is necessarily also `R_USED_ID_DROPPED`; the expected set now lists both (see Q2).
- Stale descriptions: `i05`, `i29`, `i47` said `label` (the field is `display_name`); the catalogue
  said P01-P16 (the plan has P01-P22); experiment-v1 §4.8 came before §4.7 (reordered, no rule
  changed). The catalogue records the cross-check.

## 10. Owner questions (spec ambiguities and conflicts; not guessed)

| # | Question | Evidence |
|---|---|---|
| Q1 | §4.6(c) "a declared ID now names a different entity (other member folders for a repeat or condition)": does **adding** a member to an existing repeat (or a new member folder to a condition) count? Read literally, `t03` (DrugA joins `rep1`) is also `R_CONFIRMED_ID_CHANGED`, and so is every legitimate new folder of §10 | `t03`; §10 "A new folder whose label equals an existing repeat ID is proposed for that repeat" |
| Q2 | A mistyped ID differing only in case (`ACTIN` → `Actin`, `ctrl` → `CTRL`) can never be corrected by re-confirmation within a lineage: the retired spelling stays in `used_ids` and collides (`E_ID_CASE_COLLISION`). Intended (correction needs a new, non-colliding ID or a new output folder)? Also: does a publication report every applicable `R_*` code (a set, as now assumed for `t02`) or the first? | §4.6, §4.9; `t02`, `i95` |
| Q3 | MorphoCoverage groups conditions by `target` for reagent agreement. Keep `target` a MorphoCoverage input not sourced from the file, or allow descriptive aggregation in reports? | `contrast_repeats.py:283-313`; §4.2a |
| Q4 | Add MorphoRelate's reserved names (`c`, `t`, `z`, `z0`, `z1`, `label_id`, `patch_id`, `condition`, ...) to the channel/mask reserved list before v1 is frozen, or leave them to an `A_*` refusal? | `registry/_expand.py:41-59`; roadmap §4.5 |
| Q5 | Does the canonical repeat ID **replace** the source label in the FOV key (`biological_repeat`, D02) used by `RunInputs`, patch IDs, caches and exports, or is it an added field? This decides Stage 2's blast radius in every brick | §§2-8 above; §8 "group by canonical repeat ID" |
| Q6 | v0.4.0 supports RGB images (`image_type = rgb`); D8 refuses them. Accept the regression for RGB users, or keep RGB runs working without `morphobricks.toml` until a v2 rule exists? | contract §13; ADR D8 |
| Q7 | Header names: preprocessing trims outer whitespace; §4.3 says "no trimming". Which is normative? And does "after NFC" normalize both the image header and the `header_names` entries (which are not identities and are not NFC-checked)? | `zarr_input.py:68`; §4.3 |
| Q8 | `parent_labels` masks (MorphoRelate; preprocessing kind `grouped`) have no v1 representation. Add the value before freeze, or declare them out of scope in v1? | `registry/_spec.py:59-83`; `mask_scan.py:465-485` |
| Q9 | For a mask declared `binary`, is an explicit, recorded conversion (CellPatcher `binary_mask_policy="connected_components"`) allowed, or must `A_MASK_NOT_INSTANCES` refuse regardless? | `config.py:70-95` (CellPatcher); §8 |
| Q10 | When is `R_MASK_CONTRADICTS_REPRESENTATION` checked: at publication (full pixel read), in `run`, or only in the optional mask step? With progressive masks, on each new batch? | §4.5; contract §15.1 |
| Q11 | A discovered mask type or folder label that breaks the Label rules (e.g. a mask folder `NA`) has no `R_*` code; preprocessing would refuse at discovery (`invalid_name`) for folders but not for mask types. Add an `R_*` code or require the discovery refusal? | `masks/files.py:265-281`; §8 |
| Q12 | Legacy migration: a repeat group whose rows carry different `confirmed_on` dates (today the latest wins) — which date does v1 take, and is the derived CSV then still byte-identical (§11)? | `design.py:216-218`; §7, §11 |
| Q13 | Smaller text ambiguities found by the reference validator: (a) §4.7 forbidden names "in any table": field positions only, or also ID keys (a condition folder `control`, channel `z`)? The validator applied it to fields only, and all fixtures pass either way; (b) NFC check of unit `channels` entries and `source_channels` (references): `E_ID_NOT_NFC` in phase 4 or `E_UNKNOWN_CHANNEL` in phase 5? (c) a Token breaking both the Label rule and the regex (` DNA`): one code or two? | §2.4, §3.3, §4.7 |

## 11. Unknowns

- How `RunInputs` will expose units (condition × source repeat × technical repeat) and canonical
  channel lists: not designed yet (Stage 1-2).
- Notebooks were not read cell by cell; their design steps call the cited Python
  (`notebook_design.py:318`).
- MorphoCoverage has no release; `main@64ff307` predates the other mains by three days.
- CellPatcher's in-memory `run_patching` (labels from `config.common`, no run) has no experiment
  description at all; whether v1 applies to it is not stated.
- Performance of a full pixel check of `binary` masks (Q10) on large experiments: not measured.
