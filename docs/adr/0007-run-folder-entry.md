# ADR 0007: one entry per brick on a validated run folder

- **Status:** **Proposed** (draft for an external review; not accepted, not implemented). Owner
  request of 16 November 2026: "an easy entry for all the bricks, so that we can make it as easy as
  possible to run on a validated folder" (milestone one, after the binary-masks release wave;
  roadmap track J, steps J0 and J1). What this ADR adds is the encoding of that request: one entry
  contract, one refusal family, the rule for choices and defaults, the output naming and reuse rule,
  the conformance tests and the order of the per-brick PRs (J2). Its modelling choices are listed
  [below](#modelling-choices-for-the-owners-review) and its open questions
  [at the end](#open-questions-for-the-owner).
- **Amends:** nothing normative of experiment-v1, ADR 0001, ADR 0002, ADR 0004 or ADR 0005. It adds
  one row to the [conformance plan](../conformance-plan.md) §4 ("Run-folder entry"). No fixture,
  golden or validator changes (`python -I tools/audit/refval.py fixtures .` unchanged): the entry
  is a runtime contract over run folders, which no description TOML carries.
- **Evidence:** the per-brick inventory (J1),
  [`docs/design/run-folder-entry-inventory.md`](../design/run-folder-entry-inventory.md), read at
  morphobricks-preprocessing `ce650e3`, CellPatcher `v0.7.1` (`c611101`), MorphoObjects `0eefed7`,
  MorphoEmbed `fc87537`, MorphoRelate `5f3a4df`, fiberfeatures `a7f57c5`, MorphoCoverage `9217840`,
  MorphoFeature `7ac7487` and its PR #236 head `e83811c`. The two stopped-run codes
  (`RUN_FOLDER_STOPPED`, `RUN_FOLDER_REPORT_UNREADABLE`) are encoded from what preprocessing
  ships since PR #324, read at preprocessing `main` `1b2adc3` (contract §9.1 "A stopped run").
- **Base:** MorphoBricks-Spec `main` `1167108`. [ADR 0006](https://github.com/CellMigrationLab/MorphoBricks-Spec/pull/47)
  (fast-mode channel layout) is an open pull request; this ADR does not depend on it
  ([interactions](#adr-0006-fast-mode-channel-layout-proposed)).
- **Why a new ADR file.** By ADR 0002's convention a runtime contract between repositories, with
  its own version and conformance suite, gets its own file. This one rules on how every brick is
  started on a run folder; it changes no field, no resolver rule and no mask rule.

## Context

A **validated run folder** is a published morphobricks-preprocessing output folder: the experiment
description is published and confirmed (`morphobricks.toml`), the run wrote `run_manifest.json` and
`plane_histograms.csv` (schema 5, ADR 0003), the mask step checked the masks, and nothing recorded
has changed since. Bricks read it through `RunInputs.open` and the shared resolver (resolver contract
version 3, ADR 0002 and ADR 0005).

The inventory finds seven gaps (its [gap summary](../design/run-folder-entry-inventory.md#gap-summary)):
four bricks reach a run folder with four different signatures, two (MorphoObjects, MorphoEmbed) only
through a MorphoFeature run file, and MorphoCoverage reads feature tables, not run folders; paths the
run records are typed again (CellPatcher's experiment root); settings the description holds are
declared again (MorphoRelate's channel indices, MorphoFeature's `channels`); several defaults change
values without the Spec defining them (CellPatcher patch sizes, fiberfeatures' two `analysis_mode`
defaults, MorphoEmbed normalization); preprocessing's stale-folder refusals carry no code
(`RunInputsError.code` is `None`, preprocessing `run_inputs_error.py:17-21`) and CellPatcher rewords
them; reruns overwrite, replace, make a new timestamped folder or refuse, depending on the brick; and
only MorphoRelate (`init` placeholders) and MorphoCoverage (saved answers) ask a choice once.

## Decisions (proposed)

| # | Proposed decision | Rejected alternative | Evidence |
|---|---|---|---|
| RE1 | **One entry contract, the same in every brick.** Python `<brick>.run_folder(run_folder, output=None, *, experiment_root=None, masks_root=None, check=False, choices_from=None, **choices) -> EntryResult`; CLI `<brick> run <run_folder> [--output DIR] [--choices FILE] [--<choice> VALUE ...]` and `<brick> check <run_folder> [same options]`; a notebook card "Run on a validated folder" built from the same declaration ([the contract](#the-entry-contract)) | One wrapper package that runs every brick (a new package and pin, against ADR 0002 AR2 "no brick depends on MorphoFeature"); keeping each brick's own signature and documenting it (the gap stays) | inventory, gap 1 |
| RE2 | **Same folder in.** The run folder is the only required path. Everything the run records is taken from it: experiment and masks folders, axes, channel indices, mask pairing and representation, image type, calibration, conditions, repeats, references. Only the location of a moved experiment or masks folder may be given (`experiment_root`, `masks_root`), as `RunInputs.open` already allows; it is never part of the identity | Accepting the experiment root as an argument (CellPatcher today); letting a choice override a recorded fact (a calibration, a channel index) | inventory, gaps 2-3; preprocessing `run_inputs.py:201-244` |
| RE3 | **Reading only through `RunInputs` and the resolver.** The entry opens the folder with `RunInputs.open`, builds one resolver `Request` from the choices, checks the resolver version (ADR 0005 BM10) and reads pixels and objects only through `RunInputs` (`read_plane`, `read_mask`, `read_objects`, the window readers). MorphoCoverage, which reads feature tables and not images, reads the entry output of a feature brick instead ([MorphoCoverage](#morphocoverage)) | A brick reading files itself (removed by ADR 0002 and the AR10 sweeps) | ADR 0002 AR1; ADR 0005 BM10 |
| RE4 | **A folder that is not validated, or is stale, is refused before any read, with the fix named, by one code family** (`RUN_FOLDER_*`, plus the existing `A_DESCRIPTION_REQUIRED` and `A_DRAFT_REFUSED`), each built by one constructor in preprocessing and raised by `RunInputs.open` ([refusals](#refusals)) | One code per brick (CellPatcher's `preprocessing_run_refused` today); a code-less `RunInputsError` (a user cannot tell "not a run" from "stale") | inventory, gap 5; preprocessing `run_inputs_error.py:17-37` (at `ce650e3`); `RUN_FOLDER_STOPPED` and `RUN_FOLDER_REPORT_UNREADABLE` already shipped (preprocessing `1b2adc3`, `run_inputs_error.py:89-135`, `run_inputs_stopped.py:37-182`) |
| RE5 | **Defaults only where the Spec defines one.** A closed list ([Spec defaults](#spec-defaults-closed-list)); every other choice that can change a value has no default in the entry. Brick defaults stay in the bricks' in-memory APIs and are not used by the entry | Using each brick's documented defaults (hidden choices that change results: CellPatcher's 128-pixel tiles, MorphoEmbed's normalization) | inventory, gap 4 |
| RE6 | **Every remaining choice is asked once.** Each brick declares its choices in a static file ([declaration](#the-choice-declaration)); a call missing any is refused with one `ENTRY_CHOICE_MISSING` listing **all** of them with their allowed values from the folder; the given values are written to the output's record and can be given again from it (`--choices` with a record or a choices file) | Asking one at a time (several failed runs); notebook-only prompts (the CLI and Python ask again) | MorphoRelate `placeholders.py:1-30`; MorphoCoverage saved answers |
| RE7 | **Execution settings are not choices.** A setting a brick shows to leave every output byte unchanged (worker counts, batch size where proven, thread counts) may keep its brick default; it is recorded in the execution record (ADR 0004 EW9), never in the identity | Treating thread counts as identity (a reuse lost for nothing); treating batch size as execution without a test (CUDA batch size can change bits) | ADR 0004 EW9; MorphoRelate `n_jobs`; MorphoEmbed `num_workers` |
| RE8 | **One run record per output,** `morphobricks_entry.json`, written last, listing every output file with its SHA-256, the folder identity, the brick identity, every choice with its source, the resolver provenance as is (`mask_conversions` included) and the execution record ([record](#the-run-record)) | Each brick's own record only (MorphoRelate and CellPatcher `run_config.json`, MorphoFeature `run_manifest.json`): kept, but no common check of reuse or upstream identity is possible without one shared block | inventory, gap 6 |
| RE9 | **A fixed output name next to the run folder:** `<parent>/<run folder name>__<brick_id>`, or the given `--output`. Never inside the run, experiment or masks folder, nor inside another entry output | Inside the run folder (it is preprocessing's publication; writing there makes its own checks fail); a timestamped folder per run (no reuse; unbounded folders) | preprocessing `discovery.py:43, 196` (its own `<experiment>_MorphoBricks_Preprocessing`) |
| RE10 | **Reruns reuse or refuse, by identity.** Equal and certain identity with an intact output: reused, nothing computed or written. Any difference: refused, naming what differs. Uncertain identity (an editable install, an unknown record version, an output file whose SHA-256 differs): refused. An output is never overwritten or deleted by the entry | Overwriting (CellPatcher, MorphoRelate today); reusing on a partial match | MorphoFeature `README.md:264, 590-625` |
| RE11 | **MorphoFeature is the orchestrator with the same contract.** `morphofeature run <run_folder> --choices FILE` runs several bricks; its choices file is today's run file without paths; each brick's part is checked against that brick's own declaration. The provider-only bricks (MorphoObjects, MorphoEmbed) are run by `morphofeature run <run_folder> --brick <id>` ([orchestrator](#morphofeature-the-orchestrator)) | A direct route in MorphoEmbed (needs MorphoFeature's run-level fits, `fits.py:1-15`, or their move to normalization; open question 1) | inventory (MorphoObjects, MorphoEmbed rows) |
| RE12 | **Conformance tests on the Spec fixtures** in every brick: same folder in, refusal codes, outputs identical to the brick's existing route, reuse and refusal of reruns ([conformance](#conformance-tests)) | Unit tests per brick without shared fixtures (no cross-brick guarantee) | conformance plan §4 |
| RE13 | **Migration one PR per brick (J2), right after that brick's ADR 0005 release**, after one preprocessing PR and one normalization PR that add the shared pieces ([migration](#migration-per-brick-j2)) | One big release wave (blocks on the slowest brick) | ADR 0005 [implementation order](0005-binary-masks.md#implementation-order) |

## The entry contract

### Python

```python
result = <brick>.run_folder(
    run_folder,                 # the validated run folder; the only required path
    output=None,                # default: <parent>/<run folder name>__<brick_id> (RE9)
    *,
    experiment_root=None,       # only if the experiment folder moved (RunInputs.open)
    masks_root=None,            # only if the masks folder moved
    check=False,                # True: every check and refusal, nothing computed or written
    choices_from=None,          # a choices file or an earlier output's record (RE6)
    **choices,                  # the brick's declared choices, by name
) -> EntryResult
```

`EntryResult` is `{output: Path, reused: bool, record: Mapping}`; each brick's own loader reads
the tables from `output` (CellPatcher's patch table, MorphoFeature's `load_run`, ...). A keyword not
in the brick's declaration is `ENTRY_CHOICE_INVALID`, never ignored.

### Command line

```text
<brick> run   <run_folder> [--output DIR] [--choices FILE] [--<choice> VALUE ...]
              [--experiment-root DIR] [--masks-root DIR]
<brick> check <run_folder> [same options]
<brick> run   <run_folder> --write-choices FILE
```

- A scalar or list choice is a flag named after it (`stain_preset` -> `--stain-preset`; a list is
  comma-separated). A structured choice (MorphoFeature's requests, MorphoRelate's feature
  parameters) is given only in the choices file (TOML).
- `--write-choices FILE` writes every declared choice of this folder: values already given, Spec
  defaults with their citation as a comment, and a `"<CHOOSE: ...>"` placeholder with the allowed
  values from the folder for each other one (MorphoRelate's placeholder form, `placeholders.py`). It
  never overwrites a file and computes nothing. `run` refuses a file that still holds a placeholder
  (`ENTRY_CHOICE_MISSING`).
- Exit status, as MorphoFeature's today: `0` done or reused; `1` refused (one JSON object on stderr:
  `code`, `message`, `fix`, `subjects`), nothing written; `3` the output is written and some plane
  failed (its record says which).
- **Old forms are removed, not aliased** (ADR 0002 AR10): `morphorelate run CONFIG RUN OUTPUT_DIR`
  and `morphofeature run RUN_FILE` are refused with the new form named, never re-read.

### Notebook card "Run on a validated folder"

One card per brick notebook, the same in each, generated from the brick's declaration:

1. **Folder.** The user picks the run folder; the card runs the folder check and shows either "This
   run folder is validated: N images, M conditions, K biological repeats" or the refusal with its
   code and fix (RE4). The output path from RE9 is shown, editable.
2. **Choices.** One control per declared choice. Allowed values come from the folder (channel IDs,
   mask IDs of the right representation, time points). No control is prefilled, except a Spec
   default, shown with its citation, and the device under ADR 0002 AR9 ("the notebook's default").
3. **Check, then Run.** *Check* is `check=True`; *Run* stays disabled until it passes. A reused
   output says "Already computed with the same inputs: reused" and opens it.
4. **Save choices.** Writes the choices file of `--write-choices`, for the same run from the CLI.

### Order of the checks

Every refusal below comes **before any pixel or mask is read and before any output file is
written**. The checks stop at the first step that refuses, and that step lists every problem it
finds:

1. `run_folder` exists and is a directory holding `run_manifest.json`. A folder without one is
   refused by what its run report says (`RunInputs.open` reads the report for the brick; no brick
   reads it): the final report of a stopped `run` is `RUN_FOLDER_STOPPED`, a report that cannot be
   read or is of another report version is `RUN_FOLDER_REPORT_UNREADABLE`, and any other folder
   (no report, the report of `check`, a provisional or a `written` report) is
   `RUN_FOLDER_NOT_A_RUN`. A stopped run's issues are passed on unchanged ([a stopped
   run](#a-stopped-run)), before any brick notice. A folder that holds a manifest is never
   `RUN_FOLDER_STOPPED`, whatever its report says: its last good generation is opened at step 2.
2. `RunInputs.open(run_folder, experiment_root, masks_root)`: the description, version and stale
   checks (`RUN_FOLDER_*`, `A_DESCRIPTION_REQUIRED`, `A_DRAFT_REFUSED`). It reads the manifest, the
   histogram table, the design, the calibration, the description and the conversion record, and
   the images' and masks' fingerprints; when the run verified content it also hashes the image
   files (preprocessing `run_inputs.py:18-24, 349-377`). It decodes no pixel.
3. The choices against the declaration and the folder (`ENTRY_CHOICE_MISSING`,
   `ENTRY_CHOICE_INVALID`), all problems in one refusal.
4. `resolve_request(request)`, then the resolver version (`RESOLVER_VERSION_UNSUPPORTED`, ADR 0005
   BM10), then the resolver's refusals as is (`A_SCOPE_INCOMPLETE`, `A_MASK_UNCHECKED`,
   `A_MASK_NOT_INSTANCES`, `A_RGB_NOT_SUPPORTED`, `A_VOLUME_NOT_SUPPORTED`).
5. The output: its place (`ENTRY_OUTPUT_PLACE`), then reuse or refusal by identity (RE10). A reuse
   returns here.
6. The brick's own request checks (for example the provider request-check hook, fiberfeatures'
   lengths in micrometres, MorphoEmbed's verified weights).
7. Compute, write to a staging folder inside the output's parent, publish, write the record last.

`check=True` (and `<brick> check`) runs steps 1-6 and stops.

## Refusals

### The run-folder family (built by preprocessing)

Each code has one constructor in morphobricks-preprocessing, a function returning an error that is
a `RunInputsError` with `code` set (the ADR 0005 [construction and
propagation](0005-binary-masks.md#construction-and-propagation) rules apply unchanged: bricks pass the
error on with the same code and the same `str()`, never reworded). `RunInputs.open` raises them; the
messages below are the proposed text, fixed at acceptance.

| Code | When | Message (proposed) |
|---|---|---|
| `RUN_FOLDER_NOT_A_RUN` | the path is missing, not a directory, or holds no `run_manifest.json` and no report of a stopped run (no report, the report of `check`, a provisional or a `written` report) | `RUN_FOLDER_NOT_A_RUN: {path} is not a preprocessing run folder (no run_manifest.json). Give the output folder of a preprocessing run (by default <experiment>_MorphoBricks_Preprocessing next to the experiment), or run preprocessing first. Nothing was read or written.` |
| `RUN_FOLDER_STOPPED` | no `run_manifest.json`, and the folder's final report (`report_version` `"1"`, `step` `"run"`, `status` `"stopped"`, `provisional` false) says preprocessing stopped the run (for example fixture `v29`, `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED`). **Shipped** (`RunStoppedError`, preprocessing PR #324); its `issues` are the run's error issues ([a stopped run](#a-stopped-run)) | preprocessing's text, unchanged (`run_inputs_stopped.py:164-172` at `1b2adc3`): `RUN_FOLDER_STOPPED: the preprocessing run in {output} stopped with {n} error(s) ({codes}) and published no results. First: {first error's message} Fix what the errors say and run preprocessing again. No image or mask was read.` |
| `RUN_FOLDER_REPORT_UNREADABLE` | no `run_manifest.json`, and the report cannot be read (not UTF-8, not JSON, a key given twice, `NaN`), is not of the shape report version 1 writes, says the run stopped without recording an error, or is of another `report_version`. **Shipped** (`RunReportUnreadableError`, with `path`, preprocessing PR #324); kept as its own code for now ([open question 8](#open-questions-for-the-owner)) | preprocessing's text, unchanged (`run_inputs_stopped.py:80-86, 175-182` at `1b2adc3`): `RUN_FOLDER_REPORT_UNREADABLE: {path} cannot be read as a preprocessing run report: {why}. ...` or, for another version, `RUN_FOLDER_REPORT_UNREADABLE: {path} is report version {found}; this preprocessing reads report version {expected}, ...` |
| `A_DESCRIPTION_REQUIRED` | no published description (existing, ADR 0002 AR10, AR11) | today's message, unchanged (preprocessing `required_description.py:42-47` and `FIX`) |
| `A_DRAFT_REFUSED` | an unconfirmed repeat (existing, experiment-v1 §8) | today's message, unchanged |
| `RUN_FOLDER_VERSION` | the run manifest, histogram table or conversion record is of a version this preprocessing does not read (not the run report: its version is `RUN_FOLDER_REPORT_UNREADABLE` today, [open question 8](#open-questions-for-the-owner)) | `RUN_FOLDER_VERSION: {path} was written by another preprocessing ({what} version {found}; this one reads {expected}). Run preprocessing {release} again into the same output folder; nothing is converted. Nothing was read or written.` |
| `RUN_FOLDER_STALE` | a file the run recorded (histogram table, design, calibration, description, conversion record, an image, a mask) changed, was added (`calibration.csv`) or is gone since the run | `RUN_FOLDER_STALE: {n} file(s) the run recorded changed or are gone since the run: {first 10, then ", and k more"}. Run preprocessing again (and the mask step when a mask changed). Nothing was read or written.` |
| `RUN_FOLDER_MOVED` | every recorded image is missing at the recorded experiment root (or every mask at the masks root) | `RUN_FOLDER_MOVED: none of the {n} images the run recorded is in {root}. If the experiment folder was moved, give where it is now (experiment_root / --experiment-root; masks_root / --masks-root for the masks folder). Nothing was read or written.` |
| `RUN_FOLDER_UNRECORDED` | images or masks added since the run (today's `UnrecordedFilesError`) | `RUN_FOLDER_UNRECORDED: {n} image(s) or mask(s) were added since the run: {first 10}. Run preprocessing again to record them, or exclude them there. Nothing was read or written.` |
| `RUN_FOLDER_BUSY` | another run kept publishing while the folder was opened | `RUN_FOLDER_BUSY: another preprocessing run kept publishing in {path} while it was opened. Run again once it has finished. Nothing was read or written.` |
| `RUN_FOLDER_LAYOUT` | the folder rules refuse the layout (an output folder inside the masks folder, a masks folder inside the experiment, ...; today's `masks_folder_issues`) | `RUN_FOLDER_LAYOUT: ` followed by the folder rule's message, unchanged |

#### A stopped run

A stopped run published nothing: its refusal is only in its run report, which bricks never read.
`RunInputs.open` reads it for them, only when the folder holds no `run_manifest.json`, before
anything else of the run is read and before any image or mask is opened (preprocessing contract
§9.1 "A stopped run"). `RunStoppedError.issues` holds the stopped run's **error** issues, in the
report's order, each with its `code`, `message`, `paths` (in order) and `action` exactly as the
report records them (byte-equal when written back with the report's serialiser); warnings are not
carried. Under the ADR 0005 propagation rule a brick passes it on **unchanged**: the same object, or
its own error type with the same `code`, the same `str()` and the same issues, unsorted, untrimmed
and untranslated. It is the first thing the brick reports: no brick notice, warning or summary of
its own comes before it, and none is added to it. No brick reads the report itself.

Masks are checked by request, not by folder: an unchecked mask the choices do not use does not
refuse the folder; one they use is `A_MASK_UNCHECKED` at step 4, with the mask step named as the fix.
A missing optional extra (OME-Zarr images without `zarr`) keeps its own message; it is an install
problem, not a folder state.

### The entry family (built by normalization)

Each code has one constructor in `morphobricks_normalization.contracts`, beside
`refuse_resolver_version` (ADR 0005 BM10): normalization is the lowest brick and every brick that
reads a run folder pins it. Proposed messages:

| Code | When | Message (proposed) |
|---|---|---|
| `ENTRY_CHOICE_MISSING` | a declared choice without a Spec default is not given, or a choices file holds a placeholder | `ENTRY_CHOICE_MISSING: {brick} needs {n} choice(s) that have no default: {name} ({allowed}); ... Give each once (Python keyword, --{flag}, or a --choices file; --write-choices writes one to fill). Nothing was read or written.` |
| `ENTRY_CHOICE_INVALID` | an unknown name; a value outside the allowed set; a value of the wrong type; a fact the run records given as a choice (a channel index, a calibration, an axis, a connectivity); a choice not applicable to this folder | one line per problem, joined: `ENTRY_CHOICE_INVALID: {name}: {reason}. {fix}` (for a recorded fact: `{name} is read from the run folder ({where}); it is not a choice. Change it in preprocessing and run it again.`) |
| `ENTRY_OUTPUT_PLACE` | the output is inside the run, experiment or masks folder, inside another entry output, or is a file | `ENTRY_OUTPUT_PLACE: {output} is inside {what} ({path}); an output is written next to the run folder. Give another --output.` |
| `ENTRY_OUTPUT_EXISTS` | the output holds a complete entry output whose identity differs | `ENTRY_OUTPUT_EXISTS: {output} already holds a {brick} output computed with other inputs: {differences}. Give another --output, or remove that folder yourself; an output is never overwritten.` |
| `ENTRY_OUTPUT_INCOMPLETE` | the output exists but has no readable record, or a listed file's SHA-256 differs, or it holds files and no record | `ENTRY_OUTPUT_INCOMPLETE: {output} is not a complete {brick} output ({reason}). Remove it yourself or give another --output; it is never overwritten or reused.` |
| `ENTRY_IDENTITY_UNCERTAIN` | an output exists and its identity, or the installed code's, cannot be established (an editable install, a record of an unknown entry version, a brick without a RECORD) | `ENTRY_IDENTITY_UNCERTAIN: the output {output} cannot be compared with this run ({reason}), so it is neither reused nor overwritten. Install a released {brick}, or give another --output.` |
| `ENTRY_UPSTREAM_MISSING` | MorphoCoverage (or another consumer of an entry output) finds no complete upstream output by the naming rule | `ENTRY_UPSTREAM_MISSING: no {upstream} output was found for {run_folder} ({expected path}). Run {upstream} on the run folder first, or give its output with --features-from.` |
| `ENTRY_UPSTREAM_STALE` | the upstream output's recorded folder identity is not the run folder's now | `ENTRY_UPSTREAM_STALE: {upstream output} was computed from another state of {run_folder} ({difference}). Run {upstream} again into a new output.` |

`RESOLVER_VERSION_UNSUPPORTED` (ADR 0005) and the resolver's `A_*` refusals are passed on as they
are; the entry adds no prefix and no second code.

## The choice declaration

Each brick ships one static file, `entry_choices.json`, in its package, read without importing
the brick's computing modules (discovery stays inert). For a MorphoFeature provider the same
entries sit in its provider manifest (`options` and `parameters`, extended with the fields below),
so a choice has one name on both routes (fiberfeatures' direct `RGBInputConfig.preset` becomes
`stain_preset`, the provider option's name).

| Field | Meaning |
|---|---|
| `name` | the choice's name (snake_case), the Python keyword and the CLI flag |
| `type` | `string`, `integer`, `number`, `boolean`, `list[...]`, or `table` (choices file only) |
| `allowed` | a static list, or `{"from_folder": <source>}` with a source the shared reader computes from `RunInputs` without a pixel: `channel_ids`, `mask_ids` (with a `representation` filter), `time_points`, `rgb_units` |
| `required` | `always`, or `{"when": <condition>}` on the folder or other choices (for example `rgb_unit`, as in the provider options of MorphoFeature PR #236) |
| `default` | allowed only with `spec`, a citation from the [closed list](#spec-defaults-closed-list); any other default is a declaration error, found by the brick's own test |
| `affects_values` | `true` for a choice (identity, RE10); `false` only for an execution setting with a test proving byte-identical outputs across its values (RE7) |
| `help` | one sentence shown in the card and in `ENTRY_CHOICE_MISSING` |

A choice that has exactly one allowed value on this folder (a CPU-only brick's device, a run with
one time point) is not asked: it is recorded with source `fixed`. `"all"` is an allowed value of a
channel list: every channel ID the description gives the run's units, then checked by the resolver
like any list (`A_SCOPE_INCOMPLETE` for a channel some units lack).

Each recorded choice has a source: `given` (Python, flag or choices file), `record` (taken from an
earlier output's record), `spec_default` (with its citation), `notebook_default` (the device, ADR
0002 AR9) or `fixed`.

## Spec defaults (closed list)

Only these may fill a choice the user did not give. Anything else is asked.

| Choice | Default | Spec |
|---|---|---|
| execution route of a request (`whole_plane` or a windowed scope) | `whole_plane` | ADR 0004 EW7, EW10 (windowed execution is opt-in per request; the default route is unchanged) |
| inferential unit of a score or a statistical comparison | the biological repeat (`repeat_group`) | ADR 0002 AR6 |
| device, in the notebook card only | the notebook's default | ADR 0002 AR9 |

Not defaults, because nothing is chosen: the resolver capabilities (the brick's declaration, ADR
0002 AR3, AR8 and contract version 2); connectivity 8 (fixed, ADR 0005 BM1; a choice naming it is
`ENTRY_CHOICE_INVALID`); `parent_labels_as_area` (the resolver's record, contract version 2); the
controls of MorphoCoverage (the description's `reference`, read from the folder). A missing
`binary_mask_policy` is not a default either: the binary mask used as objects is refused
(experiment-v1 §4.5c). A missing `stain_preset` on an RGB unit is refused by the provider
(`provider_option_missing`, MorphoFeature PR #236).

## The run record

`<output>/morphobricks_entry.json`, canonical JSON (sorted keys, UTF-8, LF), written last; its
presence marks a complete output. Fields:

- `entry_version` (1), `brick` (`brick_id`, distribution, version, code identity: the SHA-256 of
  the installed `RECORD` and the Git commit when installed from Git, or `uncertain` with the
  reason), and the same for its pinned MorphoBricks libraries (normalization, preprocessing,
  CellPatcher when imported);
- `run_folder`: its path (information only), the SHA-256 of `run_manifest.json`, the description's
  SHA-256 and section digests, the histogram table's SHA-256;
- `resolver`: `Provenance` as the resolver returned it, `mask_conversions` included, copied as is
  (ADR 0005 BM2, BM10);
- `choices`: every declared choice with its value and source; `execution`: the execution settings
  and the ADR 0004 EW9 execution record;
- `locations`: `experiment_root` and `masks_root` as used (information only);
- `outputs`: every file the entry wrote, with its SHA-256; the brick's own record
  (`run_config.json`, `run_manifest.json`) is one of them;
- `identity`: the SHA-256 of the canonical JSON of `entry_version`, `brick`, `run_folder` without
  its path, `resolver`, and the choices with `affects_values: true`;
- `written_at`, the one volatile field.

### Reuse or refuse (RE10)

| The output folder | The entry |
|---|---|
| does not exist | computes and publishes it |
| holds a complete output, identity equal, every listed file's SHA-256 verified, the brick's and the record's code identities certain | **reuses** it: nothing computed, nothing written, `reused = true` |
| holds a complete output with another identity | `ENTRY_OUTPUT_EXISTS`, naming each differing field |
| holds files without a record, or a listed file differs | `ENTRY_OUTPUT_INCOMPLETE` |
| holds an output whose identity, or the installed code's, is uncertain | `ENTRY_IDENTITY_UNCERTAIN` |

A reuse also requires the recorded resolver version to be in the brick's
`SUPPORTED_RESOLVER_VERSIONS` (ADR 0005 BM10). MorphoFeature's `TrialRunner` cache is unchanged: it
caches provider outputs inside a run and keeps its own, stricter key.

## MorphoFeature: the orchestrator

- `morphofeature run <run_folder> --choices FILE` and `morphofeature.run_folder(run_folder, ...,
  requests=..., bricks=..., masks=..., patch_sets=...)`. The choices file is today's run file
  without `preprocessing_run`, `experiment_root`, `masks_root` and `output` (the entry's arguments)
  and without `channels` and `shared_channel_layout` (read from the description; MorphoFeature
  checks them today against it, `README.md:193-199`).
- Each brick's part (its parameters and options, MorphoFeature PR #236's `provider_options`) is
  checked against that brick's declaration: the same names, allowed values and Spec defaults as
  its direct entry. MorphoFeature's own choices (`fit_from_histograms`, which changes the fitted
  values, `observation_units`, `keep_border_objects`) follow RE5: asked, or `fixed`.
- `--brick <id>` restricts the run to one provider; its output name is `<run folder>__<id>`, with
  the orchestrator named in the record. This is the entry of MorphoObjects and MorphoEmbed (RE11).
- Its output is one run folder (schema 4 at PR #236) plus `morphobricks_entry.json`; the
  per-brick tables are inside it, never copied into the bricks' own entry outputs.

## MorphoCoverage

MorphoCoverage reads no image and depends on neither preprocessing nor normalization today
(`pyproject.toml:13-20`). Its entry takes the same run folder argument and reads the feature
brick's entry output found by RE9: the choice `features_from` (allowed: the `brick_id`s whose
output next to the run folder holds a MorphoCoverage export, `coverage.json` schema 3) selects it.
It checks that output's record (complete, files verified) and compares its recorded
`run_manifest.json` SHA-256 with the folder's file now (`ENTRY_UPSTREAM_STALE`); it opens no
`RunInputs`. The description block it already reads from `coverage.json` (`described.py:1-40`) gives
the controls. Its saved `guide()` answers become its recorded choices.

## Interactions

### ADR 0002 (resolver) and ADR 0005 (binary masks)

- The entry is a front door over the existing routes, not a third route: AR2's two routes stay, and
  AR4's cross-route test is unchanged. RE12 adds that each entry's output equals its own route's.
- The resolver is the only interpreter of the description (AR1); the entry builds one `Request`
  from the choices and never classifies scope itself (AR7).
- The device is a choice (AR9): asked in Python and on the command line when the brick declares
  more than one device, the notebook default in the card, `cuda` without a GPU refused, recorded.
- BM10 applies at step 4 and to every reuse. The conversion record is copied as is. Connectivity is
  not a choice (BM1). The refusal codes of ADR 0005 keep their constructors and messages; the new
  codes follow the same construction and propagation rules.
- J2 for a brick starts after that brick's ADR 0005 release, so that the entry is written once,
  against the resolver contract version 3 it ships with.

### ADR 0004 (execution windows)

- The execution route is the one choice with a Spec default (`whole_plane`). A windowed scope is
  allowed only for a provider that declares `windowed_execution` (EW10); otherwise it is
  `ENTRY_CHOICE_INVALID` at step 3, before any read.
- The execution record (EW9: device, precision, thread counts) is the record's `execution` part,
  not its identity. Window margins are the provider's (EW6), not choices.
- The patch catalogue (EW3) and window histograms (EW11) are outputs listed in the record; a
  catalogue of another format version stays refused (EW3), whatever RE10 says.

### ADR 0006 (fast-mode channel layout, proposed)

- It changes no reader (its "Readers need no change"): the entry resolves channels per unit by ID
  through the resolver whether the file is fast-mode or strict.
- With ADR 0006, `"all"` in a channel list is the description's channel IDs; for a fast-mode file
  every unit that follows the experiment list has `channel_layout.channels`, and a unit tagged on its
  own is resolved on its own. MorphoFeature's `shared_channel_layout` is then read from the
  description (no unit with `channels_from = "unit"`), not given.
- `R_FAST_LAYOUT_CONTRADICTION` is refused by preprocessing before the description is published, so
  a folder with it never passes step 2; the entry adds no code.
- If ADR 0006 changes or is rejected, only the `"all"` sentence above changes.

### ADR 0001 and ADR 0003

No description field, identity rule or histogram rule changes. The histogram table (schema 5) is
one of the files `RunInputs.open` checks at step 2.

## Conformance tests

Run folders are built by preprocessing's `make_described_run` from the Spec fixtures `v01` (one
control), `v08` (binary masks), `v13` (homogeneous), `v28` (RGB units) and `v38` (parent labels), and
`v41` once ADR 0006 lands. A new preprocessing helper (J2-0) derives the folder states: no
description, a draft, an image changed after the run, every image moved, an image added, a mask
unchecked, a manifest of another version, a path that is not a run folder, a report of another
version and an unreadable report. The stopped run is preprocessing's own run of `v29`
(`R_HETEROGENEOUS_LAYOUT_NOT_ENABLED`), as preprocessing's tests build it today.

Every brick's suite (each test with a spy `RunInputs` counting `read_plane`, `read_mask`,
`read_mask_window` and `read_objects`, as ADR 0005's tests do):

| Row | Assertion |
|---|---|
| E1 Same folder in | The entry runs with the run folder as its only path; every recorded fact in the record equals the run's (`RunInputs`), and a recorded fact given as a choice is `ENTRY_CHOICE_INVALID` |
| E2 Refusals | Each folder state gives its code (table above), with `str()` equal to the constructor's output for the same arguments, 0 reads and no output folder created; the stopped run gives `RUN_FOLDER_STOPPED` as the brick's first report (no brick notice before it), with its issues equal, in order, to the report's error issues (code, message, paths, action, compared byte for byte); the two bad reports give `RUN_FOLDER_REPORT_UNREADABLE` naming the report file; on `v08` without the policy `A_MASK_NOT_INSTANCES`; on `v28` without `stain_preset` the provider's refusal; resolver versions 2 and 4 give `RESOLVER_VERSION_UNSUPPORTED` and a cached output is not read (ADR 0005 F13) |
| E3 Same outputs | With the same choices, the entry's output files are byte-identical to the brick's existing route on the same folder (CellPatcher `run_patching_condition_repeat_tree`, MorphoRelate `run` and `write_run`, fiberfeatures `analyze_run` written by the entry's writer, MorphoFeature `run_from_config`), the volatile field excepted |
| E4 Asked once | A call without choices gives one `ENTRY_CHOICE_MISSING` naming every choice with no Spec default; `--write-choices` then `--choices` reproduces E3; `choices_from=<output>` reproduces it again |
| E5 No hidden default | Every `default` of the declaration has a citation of the closed list; a run given only the required choices records every other one as `spec_default`, `notebook_default` or `fixed` |
| E6 Rerun | A second identical call reuses (0 reads, no write, `reused = true`); one changed choice is `ENTRY_OUTPUT_EXISTS` naming it; a changed output file is `ENTRY_OUTPUT_INCOMPLETE`; an editable install is `ENTRY_IDENTITY_UNCERTAIN` |
| E7 Orchestrator | MorphoFeature checks each brick's choices against that brick's declaration (one wrong name or value refused per brick, before any read); `--brick morphoobjects` and `--brick morphoembed` meet E1-E6 |
| E8 Coverage | MorphoCoverage on a folder without the upstream output is `ENTRY_UPSTREAM_MISSING`; after the run folder is republished, `ENTRY_UPSTREAM_STALE` |

## Migration per brick (J2)

From the [inventory](../design/run-folder-entry-inventory.md). Each PR adds the conformance rows
above for its brick.

| Step | Repository | What it adds or removes |
|---|---|---|
| J2-0 | morphobricks-preprocessing | the `RUN_FOLDER_*` constructors, raised by `RunInputs.open` with `code` set (today's code-less refusals; `RUN_FOLDER_STOPPED` and `RUN_FOLDER_REPORT_UNREADABLE` are already shipped, PR #324, and keep their text); the shared choice reader (`from_folder` sources); the record writer and checker (one implementation for every brick that depends on preprocessing); the notebook card renderer; the folder-state test helper |
| J2-0 | morphobricks-normalization | the `ENTRY_*` constructors in `contracts` |
| J2 | CellPatcher | `cellpatcher.run_folder`, a `cellpatcher` console script, the card in its notebook; the experiment root taken from the run (no positional path); one call for every tree depth; `entry_choices.json` (mode, patch and tile sizes, number of patches, overlap, object set, `binary_mask_policy`, `t_policy`, normalization, export format), with no brick default used by the entry; RunInputs refusals passed on, not reworded (`run_open.py:211-260`); RE9 and RE10 instead of writing into an existing folder |
| J2 | MorphoObjects | its choices declared in the provider manifest (object sets, intensity pairs, features, observation unit), no default; its entry is `morphofeature run --brick morphoobjects` |
| J2 | MorphoEmbed | the same (model, normalization scope and method, crop mode, input size, `tf32`, device; `weights_dir` as a location, outside the identity; the model's verified checksum inside it); entry through `--brick morphoembed` |
| J2 | MorphoRelate | `morphorelate run <run_folder>` and `morphorelate.run_folder`; the configuration becomes the choices file, `init` becomes `--write-choices`, `inspect` becomes `check`; the restated channel indices and the Z placeholder go (the resolver gives the indices; Z-stacks are refused upstream); RE9 and RE10 instead of replacing an earlier output |
| J2 | fiberfeatures | `fiberfeatures.run_folder`, a `fiberfeatures` console script, file outputs (features, patches, status) with the record; one `analysis_mode` with no default; `preset` renamed `stain_preset`; the length unit read from the run, the lengths asked on a calibrated run; the device asked; channels explicit (`"all"` allowed) |
| J2 | MorphoFeature | `morphofeature run <run_folder> --choices FILE`, `--brick`, `morphofeature.run_folder`; the run-file keys that the folder gives leave the choices; `fit_from_histograms` asked; checks of every brick's declaration |
| J2 | MorphoCoverage | a `morphocoverage` console script with `run <run_folder>`, `features_from`, the upstream checks, the saved answers as recorded choices |

**Order.** J2-0 first (a preprocessing patch release and a normalization patch release; no brick
change). Then each brick right after its ADR 0005 release, pinning the J2-0 tags: CellPatcher
(v0.7.1 is tagged), then fiberfeatures, MorphoRelate, MorphoObjects and MorphoEmbed as their ADR 0005
releases are tagged, in any order; MorphoFeature after the release of PR #236 and after every provider
it runs has declared its choices; MorphoCoverage last, since it reads MorphoFeature's entry output.

## Modelling choices for the owner's review

1. **The codes.** `RUN_FOLDER_*` for folder states, `ENTRY_*` for the entry; snake-case runtime
   codes outside experiment-v1 §8, like `RESOLVER_VERSION_UNSUPPORTED`. The two description codes
   keep their `A_*` names.
2. **Where the constructors live.** Folder codes in preprocessing (`RunInputs.open` raises them);
   entry codes in normalization (the lowest brick, as ADR 0005 BM10 placed its constructor).
3. **The output name** `<run folder name>__<brick_id>`: one rule that does not parse the run
   folder's name.
4. **`check` as part of the contract,** because MorphoFeature (`check`) and MorphoRelate (`inspect`)
   have it and it is the notebook card's step 3.
5. **The record as a new file** beside each brick's own record, so one checker serves every brick
   and MorphoCoverage.
6. **`"all"` as an explicit channel value,** not a default.

## Open questions for the owner

Each with the recommendation first.

1. **MorphoObjects and MorphoEmbed: entry through MorphoFeature (`--brick`).** *Recommended.* Their
   runs need MorphoFeature's run-level fits and output layout; a direct route would duplicate them or
   move the fits to normalization (a larger change, and a new cross-route test under AR4).
   Alternative: a direct `morphoobjects run` now (feasible: CPU only, no fits), MorphoEmbed later.
2. **No brick default in the entry.** *Recommended:* none, with an optional, versioned **named
   recipe** that a brick may declare (for example `grid_128_v1` for CellPatcher): choosing it is one
   explicit choice, expanded in full into the record. Alternative: allow each brick's documented
   defaults, recorded with source `brick_default` (easier, but a value-changing default the user did
   not see).
3. **One output per brick and run folder.** *Recommended:* the fixed name, and a second set of
   choices refused with "give another `--output`". Alternative: a suffix from the choices' digest
   (several outputs side by side automatically, names that are harder to read).
4. **MorphoCoverage's dependencies.** *Recommended:* MorphoCoverage pins normalization for the
   `ENTRY_*` constructors (a small dependency, one shared text). Alternative: it copies the messages
   verbatim with a source-scan test.
5. **MorphoCoverage's argument.** *Recommended:* the run folder, with the feature output found by
   RE9 (`features_from`). Alternative: the feature output folder itself.
6. **The notebook card's code.** *Recommended:* one renderer in preprocessing (every brick but
   MorphoCoverage depends on it, and its notebook guidelines exist). Alternative: each brick renders
   the card from the declaration.
7. **Brick defaults in the in-memory APIs** (`CellPatcherConfig`, `analyze_run`). *Recommended:* left
   as they are now, outside this ADR, and decided in each brick's AR10 sweep. Alternative: removed
   with the entry.
8. **A run report of another version.** *Recommended:* keep `RUN_FOLDER_REPORT_UNREADABLE` as the
   one code for a stopped run's report that preprocessing cannot read, its unknown version included,
   as preprocessing ships it now (preprocessing reviewer's recommendation on PR #324), and move the
   report's and the manifest's version refusals to `RUN_FOLDER_VERSION` together, in one later
   preprocessing PR (J2-0, when the manifest's version refusal gets its code); after that,
   `RUN_FOLDER_REPORT_UNREADABLE` keeps only a report that cannot be read or is malformed.
   Alternative: fold the report's unknown version into `RUN_FOLDER_VERSION` now (a second
   preprocessing change to a shipped refusal, made ahead of and apart from the manifest's).
