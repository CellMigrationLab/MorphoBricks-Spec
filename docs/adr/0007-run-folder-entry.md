# ADR 0007: one entry per brick on a validated run folder

- **Status:** **Proposed**, revised after the external review of 18 November 2026 (MERGE AFTER
  FIXES, ten points; [revision](#revision-after-the-external-review-of-18-november-2026)). The owner
  accepted the recommendations of open questions 1-7 on 17 November 2026
  ([owner decisions](#owner-decisions-of-17-november-2026)), and on 19 November 2026 decided that
  MorphoCoverage takes feature tables, not a run folder, and gets no new MorphoBricks dependency ([MorphoCoverage](#morphocoverage)).
  Aligned with ADR 0002 AR12 (resolver contract version 4, Spec #52). Not implemented. Owner
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
- **Base:** MorphoBricks-Spec `main` `1167108`; revised on `main` `de166f3`, where [ADR 0006](0006-fast-channel-layout.md)
  (fast-mode channel layout) is merged. This ADR does not depend on it
  ([interactions](#adr-0006-fast-mode-channel-layout)). The review revision reads CellPatcher
  `v0.8.0`, MorphoRelate `v0.6.0`, fiberfeatures `v0.8.0`, preprocessing `v0.7.0` and MorphoFeature
  `main` `d277314` (its `brick_cache`).
- **Why a new ADR file.** By ADR 0002's convention a runtime contract between repositories, with
  its own version and conformance suite, gets its own file. This one rules on how every brick is
  started on a run folder; it changes no field, no resolver rule and no mask rule.

## Context

A **validated run folder** is a published morphobricks-preprocessing output folder: the experiment
description is published and confirmed (`morphobricks.toml`), the run wrote `run_manifest.json` and
the plane histogram table (`plane_histograms.parquet`, schema 6, [ADR 0008](0008-plane-histograms-v6.md);
`plane_histograms.csv`, schema 5, ADR 0003, until the normalization release that implements
version 6), the mask step checked the masks, and nothing recorded
has changed since. Bricks read it through `RunInputs.open` and the shared resolver (ADR 0002; at
the resolver contract version in ADR 0005 BM10's supported set).

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
| RE3 | **Reading only through `RunInputs` and the resolver.** The entry opens the folder with `RunInputs.open`, builds one resolver `Request` from the choices, checks the resolver version (ADR 0005 BM10) and reads pixels and objects only through `RunInputs` (`read_plane`, `read_mask`, `read_objects`, the window readers). MorphoCoverage reads neither images nor run folders: it takes a feature brick's output, validates its tables' structure and proceeds (owner decision of 19 November 2026, [MorphoCoverage](#morphocoverage)) | A brick reading files itself (removed by ADR 0002 and the AR10 sweeps) | ADR 0002 AR1; ADR 0005 BM10 |
| RE4 | **A folder that is not validated, or is stale, is refused before any read, with the fix named, by one code family** (`RUN_FOLDER_*`, plus the existing `A_DESCRIPTION_REQUIRED` and `A_DRAFT_REFUSED`), each built by one constructor in preprocessing and raised by `RunInputs.open` ([refusals](#refusals)) | One code per brick (CellPatcher's `preprocessing_run_refused` today); a code-less `RunInputsError` (a user cannot tell "not a run" from "stale") | inventory, gap 5; preprocessing `run_inputs_error.py:17-37` (at `ce650e3`); `RUN_FOLDER_STOPPED` and `RUN_FOLDER_REPORT_UNREADABLE` already shipped (preprocessing `1b2adc3`, `run_inputs_error.py:89-135`, `run_inputs_stopped.py:37-182`) |
| RE5 | **Defaults only where the Spec defines one.** A closed list ([Spec defaults](#spec-defaults-closed-list)); every other choice that can change a value has no default in the entry. Brick defaults stay in the bricks' in-memory APIs and are not used by the entry | Using each brick's documented defaults (hidden choices that change results: CellPatcher's 128-pixel tiles, MorphoEmbed's normalization) | inventory, gap 4 |
| RE6 | **Every remaining choice is asked once.** Each brick declares its choices in a static file ([declaration](#the-choice-declaration)); a call missing any is refused with one `ENTRY_CHOICE_MISSING` listing **all** of them with their allowed values from the folder; the given values are written to the output's record and can be given again from it (`--choices` with a record or a choices file) | Asking one at a time (several failed runs); notebook-only prompts (the CLI and Python ask again) | MorphoRelate `placeholders.py:1-30`; MorphoCoverage saved answers |
| RE7 | **Execution settings are not choices.** A setting a brick shows to leave every output byte unchanged (worker counts, batch size where proven) may keep its brick default; it is recorded in the execution record (ADR 0004 EW9), never in the identity. **Thread settings are in the identity** as MorphoFeature's `brick_cache` keys them (matrix-run F3: a provider's own thread count, else the process's thread variables, the effective BLAS count on CUDA) | Treating thread counts as execution only (a model whose sums depend on the count would be reused across counts); treating batch size as execution without a test (CUDA batch size can change bits) | ADR 0004 EW9; MorphoRelate `n_jobs`; MorphoEmbed `num_workers` |
| RE8 | **One run record per output,** `morphobricks_entry.json`, written last, listing every output file with its SHA-256, the folder identity, the brick identity, every choice with its source, the resolver provenance as is (`mask_conversions` included) and the execution record ([record](#the-run-record)) | Each brick's own record only (MorphoRelate and CellPatcher `run_config.json`, MorphoFeature `run_manifest.json`): kept, but no common check of reuse or upstream identity is possible without one shared block | inventory, gap 6 |
| RE9 | **A fixed output name next to the run folder:** `<parent>/<run folder name>__<brick_id>`, or the given `--output`. Never inside the run, experiment or masks folder, nor inside another entry output | Inside the run folder (it is preprocessing's publication; writing there makes its own checks fail); a timestamped folder per run (no reuse; unbounded folders) | preprocessing `discovery.py:43, 196` (its own `<experiment>_MorphoBricks_Preprocessing`) |
| RE10 | **Reruns reuse or refuse, by identity.** Equal and certain identity with an intact output: reused, nothing computed or written. Any difference: refused, naming what differs. Uncertain identity (an editable install, an installed file of the brick that differs from its `RECORD`, an unknown record version, an output file whose SHA-256 differs, a moved source whose content was not verified): refused. A first run under an uncertain identity computes and publishes, records `uncertain` with the reason, and is never reused. An output is never overwritten or deleted by the entry | Overwriting (CellPatcher, MorphoRelate today); reusing on a partial match | MorphoFeature `README.md:264, 590-625` |
| RE11 | **MorphoFeature is the orchestrator with the same contract.** `morphofeature run <run_folder> --choices FILE` runs several bricks; its choices file is today's run file without paths; each brick's part is checked against that brick's own declaration. The provider-only bricks (MorphoObjects, MorphoEmbed) are run by `morphofeature run <run_folder> --brick <id>` ([orchestrator](#morphofeature-the-orchestrator)). **This is an explicit exception to J0's "one entry per brick"** (owner decision of 17 November 2026, Q1): these two bricks get no `<brick>.run_folder` and no console script of their own until a later decision | A direct route in MorphoEmbed (needs MorphoFeature's run-level fits, `fits.py:1-15`, or their move to normalization; open question 1) | inventory (MorphoObjects, MorphoEmbed rows) |
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
  runs after the folder checks (steps 1-2), refuses an existing file, and computes nothing. `run` refuses a file that still holds a placeholder
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
   `ENTRY_CHOICE_INVALID`), all problems in one refusal. A missing **provider option** (for example
   `stain_preset` on an RGB unit) is not an `ENTRY_CHOICE_MISSING` item: the provider refuses it at
   step 5 with its own `provider_option_missing`, unchanged; the notebook card shows it among the
   missing choices before *Run* ([missing provider options](#spec-defaults-closed-list)).
4. `resolve_request(request)`, then the resolver version (`RESOLVER_VERSION_UNSUPPORTED`, ADR 0005
   BM10), then the resolver's refusals as is (`A_FOV_NOT_IN_RUN` alone, ADR 0002 AR12; else
   `A_SCOPE_INCOMPLETE`, `A_MASK_UNCHECKED`, `A_MASK_NOT_INSTANCES`, `A_RGB_NOT_SUPPORTED`,
   `A_VOLUME_NOT_SUPPORTED`).
5. The brick's own request checks and every provider artifact and identity check, **before any
   reuse decision**: the provider request-check hook (`provider_option_missing` included),
   fiberfeatures' lengths in micrometres, MorphoEmbed's weights verified against their checksum, the
   device (`cuda` without a GPU refused), and the code identity of the record ([the run
   record](#the-run-record)). An output is never reused by a run that would have been refused.
6. The output: its place (`ENTRY_OUTPUT_PLACE`), then reuse or refusal by identity (RE10). A reuse
   returns here.
7. Compute into a staging folder inside the output's parent, write the record last inside it, then
   publish it exclusively ([publication](#publication)).

`check=True` (and `<brick> check`) runs steps 1-6 and stops. `--write-choices FILE` runs steps 1-2
first (it writes nothing for a folder that is refused), and refuses a `FILE` that already exists.

### Publication

Publication is exclusive, atomic and never overwrites. The staging folder, complete with its record,
is moved onto the output path in one rename that fails when the path exists (`renameat2` with
`RENAME_NOREPLACE` on Linux; on a platform without it, an exclusive `mkdir` of the output path as a
lock, then the move of each file into it, the record last). Of concurrent runs for one output path
exactly one publishes. Each other one removes its own staging folder and then decides as at step 6
against the published output: equal identity, reused; another identity, `ENTRY_OUTPUT_EXISTS`. An
output holds only the files its record lists, regular files and folders, no link; any other file or
any link makes it `ENTRY_OUTPUT_INCOMPLETE`.

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
reads a run folder pins it. MorphoCoverage, which reads no run folder and pins no MorphoBricks
library (owner decision of 19 November 2026), copies the texts of the codes it raises
([MorphoCoverage](#morphocoverage)). Proposed messages:

| Code | When | Message (proposed) |
|---|---|---|
| `ENTRY_CHOICE_MISSING` | a declared choice without a Spec default is not given, or a choices file holds a placeholder | `ENTRY_CHOICE_MISSING: {brick} needs {n} choice(s) that have no default: {name} ({allowed}); ... Give each once (Python keyword, --{flag}, or a --choices file; --write-choices writes one to fill). Nothing was read or written.` |
| `ENTRY_CHOICE_INVALID` | an unknown name; a value outside the allowed set; a value of the wrong type; a fact the run records given as a choice (a channel index, a calibration, an axis, a connectivity); a choice not applicable to this folder | one line per problem, joined: `ENTRY_CHOICE_INVALID: {name}: {reason}. {fix}` (for a recorded fact: `{name} is read from the run folder ({where}); it is not a choice. Change it in preprocessing and run it again.`) |
| `ENTRY_OUTPUT_PLACE` | the output is inside the run, experiment or masks folder, inside another entry output, or is a file | `ENTRY_OUTPUT_PLACE: {output} is inside {what} ({path}); an output is written next to the run folder. Give another --output.` |
| `ENTRY_OUTPUT_EXISTS` | the output holds a complete entry output whose identity differs | `ENTRY_OUTPUT_EXISTS: {output} already holds a {brick} output computed with other inputs: {differences}. Give another --output, or remove that folder yourself; an output is never overwritten.` |
| `ENTRY_OUTPUT_INCOMPLETE` | the output exists but has no readable record, or a listed file's SHA-256 differs, or it holds files and no record | `ENTRY_OUTPUT_INCOMPLETE: {output} is not a complete {brick} output ({reason}). Remove it yourself or give another --output; it is never overwritten or reused.` |
| `ENTRY_IDENTITY_UNCERTAIN` | an output exists and its identity, or the installed code's, cannot be established: (a) an editable install of the brick or of a library in its identity; (b) a brick or library without a `RECORD`; (c) an installed file **of the brick** whose hash differs from its `RECORD` entry (libraries are compared by name, version and `RECORD` digest, not file by file); (d) a record of an unknown entry version, or one whose own identity is `uncertain`; (e) the experiment or masks folder at another location than the output records, and an image or mask the request reads not content-verified ([a moved source](#reuse-or-refuse-re10)) | `ENTRY_IDENTITY_UNCERTAIN: the output {output} cannot be compared with this run ({reason}), so it is neither reused nor overwritten. {fix}` where `{fix}` is, for (a)-(c): `Install a released {brick} (not editable, its files as its RECORD lists them), or give another --output.`; for (d): `Give another --output.`; for (e): `Open the run folder with the experiment and masks folders at the location the output records, or give another --output.` |

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
| `type` | `string`, `integer`, `number`, `boolean`, `list[...]`, `table` (choices file only), or `fov_subset`: either the string `"all"` or a non-empty `list[fov_key]` (choices file only), where a `fov_key` is a list of exactly four strings, `[condition, biological_repeat, technical_repeat, position_id]`, as `RunInputs.fovs()` gives the FOV key (experiment-v1 §3.4; ADR 0002 AR12). No other union type exists |
| `allowed` | a static list, or `{"from_folder": <source>}` with a source the shared reader computes from `RunInputs` without a pixel: `channel_ids`, `mask_ids` (with a `representation` filter), `time_points`, `rgb_units`, `fov_keys` (the run's FOV keys as `RunInputs.fovs()` gives them, for `fov_subset`) |
| `required` | `always`, or `{"when": <condition>}` on the folder or other choices (for example `rgb_unit`, as in the provider options of MorphoFeature PR #236) |
| `default` | allowed only with `spec`, a citation from the [closed list](#spec-defaults-closed-list); any other default is a declaration error, found by the brick's own test |
| `affects_values` | `true` for a choice (identity, RE10); `false` only for an execution setting with a test proving byte-identical outputs across its values (RE7) |
| `help` | one sentence shown in the card and in `ENTRY_CHOICE_MISSING` |

**The declaration is complete, field by field.** Every field of the brick's configuration
dataclasses, every flag of its command line and every `options` and `parameters` entry of its
provider manifest is exactly one of: a declared choice, a declared execution setting (RE7, with its
byte-identity test), or a fact the run records (refused as a choice). A test in each brick
enumerates them (`dataclasses.fields`, the parser's actions, the manifest's keys) and fails on any
field that is none of these; at run time a field the declaration does not list is
`ENTRY_CHOICE_INVALID`, never ignored. Seeds and sampling settings are choices like any other
(CellPatcher `seed`, `seed_scope`, `min_mask_fraction`; MorphoRelate `random_seed`; fiberfeatures
`sample_id_from`), and so is a compute backend that is not proven value-neutral (MorphoRelate
`analysis.backend`, Numba or NumPy: `affects_values: true` until a test shows byte-identical
outputs across backends).

A choice that has exactly one allowed value on this folder (a CPU-only brick's device, a run with
one time point) is not asked: it is recorded with source `fixed`. `"all"` is an allowed value of a
channel list: every channel ID the description gives the run's units, then checked by the resolver
like any list (`A_SCOPE_INCOMPLETE` for a channel some units lack).

Each recorded choice has a source: `given` (Python, flag or choices file), `record` (taken from an
earlier output's record), `spec_default` (with its citation), `notebook_default` (the device, ADR
0002 AR9) or `fixed`.

## Spec defaults (closed list)

Only these may fill a choice the user did not give. Anything else is asked.

| Choice | Declaration `name` and `type` | Default | Spec |
|---|---|---|---|
| execution route of a request (`whole_plane` or a windowed scope) | `execution_route`, `string` | `"whole_plane"` | ADR 0004 EW7, EW10 (windowed execution is opt-in per request; the default route is unchanged) |
| inferential unit of a score or a statistical comparison | `scoring_unit`, `string` | `"repeat_group"` | ADR 0002 AR6 |
| device, in the notebook card only | `device`, `string` | the notebook's default (`"cpu"` or `"cuda"`) | ADR 0002 AR9 |
| the images a request uses | `fov_subset`, `fov_subset` (its keys allowed from `fov_keys`) | `"all"` (the resolver's `fov_subset = None`, recorded as `all`) | ADR 0002 AR12 |

A `default` in a declaration is valid only on a field with that `name` and `type` and that value;
any other default is a declaration error (row E5).

Not defaults, because nothing is chosen: the resolver capabilities (the brick's declaration, ADR
0002 AR3, AR8 and contract version 2); connectivity 8 (fixed, ADR 0005 BM1; a choice naming it is
`ENTRY_CHOICE_INVALID`); `parent_labels_as_area` (the resolver's record, contract version 2); the
controls of MorphoCoverage (the description's `reference`, read from the description block the feature brick exported in `coverage.json`). A missing
`binary_mask_policy` is not a default either: the binary mask used as objects is refused
(experiment-v1 §4.5c).

**Missing provider options: one precedence.** A missing `stain_preset` on an RGB unit (and any other
missing provider option) is refused by the provider with `provider_option_missing` (MorphoFeature
PR #236), passed on unchanged at step 5; it is never also an `ENTRY_CHOICE_MISSING` item, so one
missing option has one code on every route. The notebook card renders provider options from the
same declaration and shows a missing one with the other missing choices before *Run*.

## The run record

`<output>/morphobricks_entry.json`, canonical JSON (sorted keys, UTF-8, LF), written last; its
presence marks a complete output. Fields:

- `entry_version` (1), `brick` (`brick_id`, distribution, version, code identity, or `uncertain`
  with the reason). The code identity is **at least as strong as MorphoFeature's `brick_cache`
  key** (`implementation_identity`, `library_identity`, `thread_identity` at MorphoFeature `main`
  `d277314`): the SHA-256 of the installed `RECORD` and the Git commit when installed from Git; the
  Python version and the machine; for every library the brick may compute with (each requirement of
  its distribution, directly or through another, MorphoFeature's `RESULT_LIBRARIES`, every installed
  `nvidia-*` library), its name, installed version (and Git commit) and **the SHA-256 of its
  `RECORD` file**, as `brick_cache` records it (an absent library recorded as absent); the provider
  manifest's SHA-256 for a provider; the thread setting (RE7); and the SHA-256 of every model weight
  file the run uses, verified against the brick's published checksum. **Verification on each run**
  (owner decision of 19 November 2026): **every installed file of the brick itself** is hashed and
  compared with its hash in the brick's `RECORD`; the computing libraries are checked by name,
  version and `RECORD` digest only, with **no per-file hashing of libraries** on each run. Only a
  brick file that differs from its `RECORD`, an editable install of the brick or of such a library,
  or a brick or library without a `RECORD` makes the identity `uncertain`
  (`ENTRY_IDENTITY_UNCERTAIN`). A library's name, version and `RECORD` digest are identity fields:
  one that differs from the existing output's record is **another identity**
  (`ENTRY_OUTPUT_EXISTS`, naming it), never `uncertain`. One implementation computes and checks it: preprocessing's record writer
  and checker (J2-0), which MorphoFeature's `brick_cache` key then also uses;
- `run_folder`: its path (information only), the SHA-256 of `run_manifest.json`, the description's
  SHA-256 and section digests, the histogram table's **`content_sha256`** (ADR 0008 PQ6; for a
  version 5 table, before the normalization release that implements version 6, its file SHA-256)
  in the identity, and the table's file SHA-256 as information only (`RunInputs.open` checks it for
  integrity at step 2), so a table rewritten with the same content under another `pyarrow` keeps the
  identity; `source`: for every image and mask the
  request reads, its content SHA-256 as `RunInputs.open` verified it, or `fingerprint_only` when the
  run recorded no content hash;
- `resolver`: `Provenance` as the resolver returned it, `mask_conversions` included, copied as is
  (ADR 0005 BM2, BM10);
- `choices`: every declared choice with its value and source; `execution`: the execution settings
  and the ADR 0004 EW9 execution record;
- `locations`: `experiment_root` and `masks_root` as used (information only);
- `outputs`: every file the entry wrote, with its SHA-256; the brick's own record
  (`run_config.json`, `run_manifest.json`) is one of them;
- `identity`: the SHA-256 of the canonical JSON of `entry_version`, `brick`, `run_folder` without
  its path, `resolver` (its `fov_scope` included, so the `scope_digest` of ADR 0002 AR12 is part of
  the identity), and the choices with `affects_values: true`;
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
`SUPPORTED_RESOLVER_VERSIONS` (ADR 0005 BM10).

**A moved source.** Equal fingerprints (size, modification time) do not prove equal pixels. When
`experiment_root` or `masks_root` differs from the location recorded in the existing output's
record, the output is reused only when every image and mask the request reads was content-verified
by `RunInputs.open` and its content SHA-256 equals the recorded `source`; otherwise the identity is
`uncertain` (`ENTRY_IDENTITY_UNCERTAIN`: not reused, not overwritten). A first run at a new location
computes as usual. MorphoFeature's `TrialRunner` cache is unchanged: it
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
  values, `observation_units`, `keep_border_objects`) follow RE5: asked, or `fixed`. One
  `fov_subset` for the whole run, passed unchanged to every brick's part and every resolver call
  (ADR 0002 AR12, "One scope per analysis").
- `--brick <id>` restricts the run to one provider; its output name is `<run folder>__<id>`, with
  the orchestrator named in the record. This is the entry of MorphoObjects and MorphoEmbed (RE11).
- Its output is one run folder (schema 4 at PR #236) plus `morphobricks_entry.json`; the
  per-brick tables are inside it, never copied into the bricks' own entry outputs.

## MorphoCoverage

**Owner decision of 19 November 2026** ("Feature tables are feature tables. Checks should happen
before. MorphoCoverage validates the table structure and goes with it."), superseding the
17 November wording "MorphoCoverage takes the run folder" (Q5) and the review's refinement of Q4:

- **MorphoCoverage takes feature tables, not a run folder.** Its entry's one required path is a
  feature brick's output (MorphoFeature's entry output holding its export, `coverage.json` schema 3,
  with the `objects` and `fovs` tables): `morphocoverage run <feature_output>` and
  `morphocoverage.run_folder(feature_output, ...)` (the name kept for one contract). It opens no run
  folder, calls no `RunInputs.open` and **does not depend on preprocessing**. This is a stated
  exception to RE1-RE2's "the run folder is the only required path", as Q1 is for MorphoObjects and
  MorphoEmbed.
- **Upstream validation is the feature brick's, done before.** A stale, stopped or unvalidated run
  folder is refused by the feature brick's own entry (steps 1-2), so its output exists only for a
  validated folder. MorphoCoverage does not re-check the run folder.
- **It validates the tables' structure, then proceeds.** Its existing in-table checks stay and are
  its refusals, passed on as they are: the export's description block (`DescriptionRefused`, with
  its codes, `_described_shape.py` at MorphoCoverage `209b9be`), the pairing of conditions
  (`PairingRefused`), and one acquisition per report (the acquisition identity of MorphoCoverage
  #637, `_acquisition.py`: results of different acquisitions are never assembled). No
  `ENTRY_UPSTREAM_*` code exists: a path that is not a feature output fails these structure checks.
- **Its dependencies: no new MorphoBricks dependency** (owner decision of 19 November 2026,
  superseding the 17 November "MorphoCoverage pins normalization", Q4). It imports neither
  normalization nor preprocessing and keeps its current dependencies (at `main` `209b9be`,
  `pyproject.toml`: matplotlib, numpy, pandas, scikit-learn, scipy, umap-learn). The `ENTRY_*`
  refusals it raises for its own choices and output carry the code and the exact text of
  normalization's constructors, copied into MorphoCoverage; its conformance test compares them with
  normalization's constructors in the test environment only, never at run time.
- **Output and record.** Its output is named `<feature output name>__morphocoverage` next to the
  feature output (RE9 applied to its input), never inside it. The choice `features_from` is gone (the
  path names the output). Its record lists the SHA-256 of each input table it read and the feature
  output's own entry identity (information), and its identity is those table digests, its code and
  its choices (RE10). The controls come from the export's description block (`described.py`). Its
  saved `guide()` answers become its recorded choices. It writes `morphobricks_entry.json` with its
  own code (preprocessing's writer is not available to it), and its conformance test checks the
  record with preprocessing's checker in the test environment only. Its notebook card is its own, rendered from
  the same declaration format, since it does not depend on preprocessing's renderer (Q6).

## Interactions

### ADR 0002 (resolver) and ADR 0005 (binary masks)

- The entry is a front door over the existing routes, not a third route: AR2's two routes stay, and
  AR4's cross-route test is unchanged. RE12 adds that each entry's output equals its own route's.
- The resolver is the only interpreter of the description (AR1); the entry builds one `Request`
  from the choices and never classifies scope itself (AR7).
- AR12 (resolver contract version 4): the entry's `fov_subset` choice becomes `Request.fov_subset`
  unchanged (`"all"` as None); the resolver's `fov_scope` is copied as is into the record's
  `resolver` part, and its `scope_digest` is part of the entry identity (below), so an output of
  another subset is `ENTRY_OUTPUT_EXISTS`, never reused. The entry accepts the resolver versions of
  BM10's supported set (`{4}` after the AR12 wave) and checks them as BM10 and F13 state.
- The device is a choice (AR9): asked in Python and on the command line when the brick declares
  more than one device, the notebook default in the card, `cuda` without a GPU refused, recorded.
- BM10 applies at step 4 and to every reuse. The conversion record is copied as is. Connectivity is
  not a choice (BM1). The refusal codes of ADR 0005 keep their constructors and messages; the new
  codes follow the same construction and propagation rules.
- J2 for a brick starts after that brick's ADR 0005 release, so that the entry is written once,
  against the resolver contract version that release supports (ADR 0005 BM10's supported set).

### ADR 0004 (execution windows)

- The execution route is the one choice with a Spec default (`whole_plane`). A windowed scope is
  allowed only for a provider that declares `windowed_execution` (EW10); otherwise it is
  `ENTRY_CHOICE_INVALID` at step 3, before any read.
- The execution record (EW9: device, precision, thread counts) is the record's `execution` part.
  The device and the thread settings are **also part of the identity**: the device as a choice
  (AR9), the thread setting in the code identity (RE7), and so is a precision setting that is a
  declared choice (MorphoEmbed `tf32`). Only the other execution settings (RE7: worker counts, a
  batch size proven byte-neutral) are outside the identity. Window margins are the provider's
  (EW6), not choices.
- The patch catalogue (EW3) and window histograms (EW11) are outputs listed in the record; a
  catalogue of another format version stays refused (EW3), whatever RE10 says.

### ADR 0006 (fast-mode channel layout)

- It changes no reader (its "Readers need no change"): the entry resolves channels per unit by ID
  through the resolver whether the file is fast-mode or strict.
- With ADR 0006, `"all"` in a channel list is the description's channel IDs; for a fast-mode file
  every unit that follows the experiment list has `channel_layout.channels`, and a unit tagged on its
  own is resolved on its own. MorphoFeature's `shared_channel_layout` is then derived from the
  description, not given: the layout is shared exactly when every unit's channel-ID list (and image
  type) is equal, **whatever the units' `channels_from` markers say**. `v41` (one unit tagged on its
  own with the experiment's list) is shared; `v42` (that unit with another order) is not.
- `R_FAST_LAYOUT_CONTRADICTION` is refused by preprocessing before the description is published, so
  a folder with it never passes step 2; the entry adds no code.
- If ADR 0006 changes or is rejected, only the `"all"` sentence above changes.

### ADR 0001 and ADR 0003

No description field, identity rule or histogram rule changes. The histogram table (schema 6,
`plane_histograms.parquet`, ADR 0008, from the normalization release that implements it; schema 5
before) is one of the files `RunInputs.open` checks at step 2, and its `content_sha256` is the
entry identity's histogram digest ([the run record](#the-run-record)).

## Conformance tests

Run folders are built by preprocessing's `make_described_run` from the Spec fixtures `v01` (one
control), `v08` (binary masks), `v13` (homogeneous), `v28` (RGB units) and `v38` (parent labels), and
`v41` once ADR 0006 lands. A new preprocessing helper (J2-0) derives the folder states: no
description, a draft, an image changed after the run, every image moved, an image added, a mask
unchecked, a manifest of another version, a path that is not a run folder, a report of another
version and an unreadable report. The stopped run is preprocessing's own run of `v29`
(`R_HETEROGENEOUS_LAYOUT_NOT_ENABLED`), as preprocessing's tests build it today.

Every brick's suite, each test with a spy at the **decoder layer**: it counts every call that turns
stored bytes into pixels, whichever `RunInputs` method, window reader or mask conversion makes it.
At preprocessing `v0.7.0` these are tifffile's `TiffPage.asarray`, `TiffPage.decode` (one strip or
tile), `TiffPageSeries.asarray`, `TiffFile.asarray`, `FileHandle.read_array` (uncompressed pieces)
and `tifffile.imread`, and the indexing of a zarr array. They are reached from `read_plane`,
`read_image`, both `read_window`s (`RunWindowReader` included), `read_mask`, `read_mask_window`,
`read_objects`, and from `RunInputs.binary_to_instances` and `classes_to_binary`, which decode
through `read_mask_plane` without `read_mask` (`mask_conversion.py:250, 299`). Preprocessing ships
the spy as a test helper (J2-0), with its own test that each of those routes is counted; a format
reader added later joins the helper in the same PR. "0 reads" means 0 counted calls:

| Row | Assertion |
|---|---|
| E1 Same folder in | The entry runs with the run folder as its only path; every recorded fact in the record equals the run's (`RunInputs`), and a recorded fact given as a choice is `ENTRY_CHOICE_INVALID` |
| E2 Refusals | Each folder state gives its code (table above), with `str()` equal to the constructor's output for the same arguments, 0 reads and no output folder created; the stopped run gives `RUN_FOLDER_STOPPED` as the brick's first report (no brick notice before it), with its issues equal, in order, to the report's error issues (code, message, paths, action, compared byte for byte); the two bad reports give `RUN_FOLDER_REPORT_UNREADABLE` naming the report file; on `v08` without the policy `A_MASK_NOT_INSTANCES`; on `v28` without `stain_preset` the provider's `provider_option_missing`, unchanged and not also an `ENTRY_CHOICE_MISSING` item; the unsupported resolver versions of ADR 0005 F13 (a) and (b) give `RESOLVER_VERSION_UNSUPPORTED` and a cached output is not read; a `fov_subset` naming a key the run does not have gives `A_FOV_NOT_IN_RUN` alone, with 0 reads |
| E3 Same outputs | With the same choices, the entry's output files are byte-identical to the brick's existing route on the same folder (CellPatcher `run_patching_condition_repeat_tree`, MorphoRelate `run` and `write_run`, MorphoFeature `run_from_config`), the volatile field excepted. fiberfeatures, whose direct route writes no file, is compared with an **independent serialised baseline**: files committed in fiberfeatures, written once from `analyze_run`'s data frames by a test-only writer that shares no code with the entry's writer. AR4's cross-route comparison of shared columns stays as it is, beside this row |
| E4 Asked once | A call without choices gives one `ENTRY_CHOICE_MISSING` naming every choice with no Spec default (provider options excepted, E2); `--write-choices` then `--choices` reproduces E3; `choices_from=<output>` reproduces it again |
| E5 No hidden default | Every `default` of the declaration is on a field whose `name`, `type` and value are a row of the closed list, with its citation; the field-by-field inventory test passes (every configuration field, CLI flag and manifest entry declared or refused); a run given only the required choices records every other one as `spec_default`, `notebook_default` or `fixed` |
| E6 Rerun | A second identical call reuses (0 reads, no write, `reused = true`); one changed choice is `ENTRY_OUTPUT_EXISTS` naming it (another `fov_subset` included: its `scope_digest` differs); so is each of: a changed version of a library in the identity, a changed `RECORD` digest of a library at the same version, a changed model weight file, another device, another thread setting; a changed file of the brick itself (its `RECORD` unchanged) is found by the per-run hashing (`ENTRY_IDENTITY_UNCERTAIN`), and the run hashes no library file one by one (a spy on the hashing counts only the brick's files); a changed output file, an extra file or a link in the output is `ENTRY_OUTPUT_INCOMPLETE`; an editable install, an installed file of the brick that differs from its `RECORD` hash, and a moved experiment folder whose content was not verified are `ENTRY_IDENTITY_UNCERTAIN`; a moved, content-verified folder with equal content is reused; changed image content is refused at step 2 (`RUN_FOLDER_STALE`); provider checks run before reuse (a missing weight file refuses even when an equal output exists); two concurrent calls for one output publish exactly one output, the other reuses or refuses, and no staging folder is left |
| E7 Orchestrator | MorphoFeature checks each brick's choices against that brick's declaration (one wrong name or value refused per brick, before any read); `--brick morphoobjects` and `--brick morphoembed` meet E1-E6 |
| E8 Coverage | MorphoCoverage given a feature output computes from its tables alone: it imports no normalization or preprocessing module (an import scan of its package and its declared dependencies unchanged) and opens no run folder; the `ENTRY_*` texts it raises equal normalization's constructors' (in its test environment only); a malformed export, a description block that does not fit the tables, or results of two acquisitions are refused with its own codes before anything is computed; a run folder given in place of a feature output is refused by the same structure checks; E4-E6 apply to its own output |

## Migration per brick (J2)

From the [inventory](../design/run-folder-entry-inventory.md). Each PR adds the conformance rows
above for its brick.

| Step | Repository | What it adds or removes |
|---|---|---|
| J2-0 | morphobricks-preprocessing | the `RUN_FOLDER_*` constructors, raised by `RunInputs.open` with `code` set (today's code-less refusals; `RUN_FOLDER_STOPPED` and `RUN_FOLDER_REPORT_UNREADABLE` are already shipped, PR #324, and keep their text); the shared choice reader (`from_folder` sources); the record writer and checker, with the code identity of [the run record](#the-run-record) (one implementation for every brick that depends on preprocessing, MorphoFeature's `brick_cache` included; MorphoCoverage writes the same record schema with its own code, tested against this checker); the notebook card renderer, which reads only the static declarations; the folder-state test helper |
| J2-0 | morphobricks-normalization | the `ENTRY_*` constructors in `contracts` |
| J2 | CellPatcher | `cellpatcher.run_folder`, a `cellpatcher` console script, the card in its notebook; the experiment root taken from the run (no positional path); one call for every tree depth; `entry_choices.json` (mode, patch and tile sizes, number of patches, overlap, `seed`, `seed_scope`, `min_mask_fraction`, object set, `binary_mask_policy`, `t_policy`, normalization, export format), with no brick default used by the entry; RunInputs refusals passed on, not reworded (`run_open.py:211-260`); RE9 and RE10 instead of writing into an existing folder |
| J2 | MorphoObjects | its choices declared in the provider manifest (object sets, intensity pairs, features, observation unit), no default; its entry is `morphofeature run --brick morphoobjects` |
| J2 | MorphoEmbed | the same (model, normalization scope and method, crop mode, input size, `tf32`, device; `weights_dir` as a location, outside the identity; the model's verified checksum inside it); entry through `--brick morphoembed` |
| J2 | MorphoRelate | `morphorelate run <run_folder>` and `morphorelate.run_folder`; the configuration becomes the choices file, `init` becomes `--write-choices`, `inspect` becomes `check`; the restated channel indices and the Z placeholder go (the resolver gives the indices; Z-stacks are refused upstream); `analysis.backend` and `random_seed` are choices; RE9 and RE10 instead of replacing an earlier output |
| J2 | fiberfeatures | `fiberfeatures.run_folder`, a `fiberfeatures` console script, file outputs (features, patches, status) with the record; one `analysis_mode` with no default; `sample_id_from` a choice with no default; `preset` renamed `stain_preset`; the length unit read from the run, the lengths asked on a calibrated run; the device asked; channels explicit (`"all"` allowed) |
| J2 | MorphoFeature | `morphofeature run <run_folder> --choices FILE`, `--brick`, `morphofeature.run_folder`; the run-file keys that the folder gives leave the choices; `fit_from_histograms` asked; checks of every brick's declaration |
| J2 | MorphoCoverage | a `morphocoverage` console script with `run <feature_output>` (no run folder, no preprocessing dependency; owner decision of 19 November 2026); its structure checks as they are; no new MorphoBricks dependency (owner decision of 19 November 2026), the `ENTRY_*` texts copied and tested against normalization's; the saved answers as recorded choices |

**Order** (refreshed on 19 November 2026). Every brick's ADR 0005 release is tagged: CellPatcher
v0.8.0, MorphoObjects, MorphoEmbed and MorphoRelate v0.6.0, fiberfeatures v0.8.0, MorphoFeature v0.5.0
(PR #236 merged), on normalization v0.7.1 and preprocessing v0.7.0. J2-0 comes first, after the
preprocessing v0.7.1 release passes its own gate: a preprocessing release and a normalization
release with the shared pieces, and no brick change. Then each brick that reads a run folder pins
the J2-0 tags: CellPatcher, fiberfeatures, MorphoRelate, MorphoObjects and MorphoEmbed in any
order; MorphoFeature once every provider it runs has declared its choices. MorphoCoverage comes last,
since it reads MorphoFeature's entry output; it pins no MorphoBricks library (owner decision of
19 November 2026) and uses the J2-0 checker in its tests only.

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
   that depends on preprocessing; MorphoCoverage writes the same record schema with its own code and
   meets the checker in its tests only.
6. **`"all"` as an explicit channel value,** not a default.

## Owner decisions of 17 November 2026

The owner accepted the recommendation of each of open questions 1-7 below; Q5 and the review's
refinement of Q4 were superseded on 19 November 2026, and Q4 itself (the normalization pin) on the
same day ([MorphoCoverage](#morphocoverage)). The external review of
18 November 2026 agreed with all of them, and refined three, as recorded here:

| # | Decision | Refinement by the review, applied in this text |
|---|---|---|
| Q1 | MorphoObjects and MorphoEmbed are run through `morphofeature run --brick` | An explicit exception to J0's one entry per brick (RE11) |
| Q2 | No brick default in the entry; optional, versioned named recipes | none |
| Q3 | One output per brick and run folder, under the fixed name | Exclusive publication ([publication](#publication)) |
| Q4 | ~~MorphoCoverage pins normalization~~ **Superseded on 19 November 2026:** MorphoCoverage gets no new MorphoBricks dependency (neither normalization nor preprocessing); it copies the `ENTRY_*` texts it raises, tested against normalization's constructors | The review's refinement (pin preprocessing too) is superseded with it ([MorphoCoverage](#morphocoverage)) |
| Q5 | ~~MorphoCoverage takes the run folder, with `features_from`~~ **Superseded on 19 November 2026:** it takes a feature brick's output and validates the tables' structure | n/a |
| Q6 | One notebook-card renderer, in preprocessing | It reads only the static declaration; MorphoCoverage, which does not depend on preprocessing, renders its own card from the same declaration format |
| Q7 | Brick defaults in the in-memory APIs are left to each brick's AR10 sweep | The entry never inherits them (RE5) |

Question 8 stays open; the review agrees with its recommendation.

**Owner decision of 19 November 2026 (reuse verification).** On each run the entry hashes every
installed file of the brick itself against the brick's `RECORD`, and checks each computing library
(torch, numpy, `nvidia-*`, ...) by name, version and the SHA-256 of its `RECORD` file, as
MorphoFeature's `brick_cache` does; it does not hash library files one by one
([the run record](#the-run-record); RE10; E6).

## Revision after the external review of 18 November 2026

The review (MERGE AFTER FIXES) kept the architecture (RE1-RE3, RE5-RE6, RE8-RE9, RE11-RE13). Its
ten blockers, and where each is fixed:

| # | Blocker | Fixed in |
|---|---|---|
| 1 | Provider artifact and identity checks came after the reuse decision | [Order of the checks](#order-of-the-checks), steps 5-6 |
| 2 | The reuse identity was weaker than MorphoFeature's `brick_cache` | [The run record](#the-run-record), `brick`; RE7 (threads) |
| 3 | A moved source was reused on fingerprints | [Reuse or refuse](#reuse-or-refuse-re10), "A moved source"; `source` in the record; RE10 |
| 4 | MorphoCoverage read tables without validating the folder | Answered differently by the owner on 19 November 2026: the feature brick validates the folder before; MorphoCoverage validates the tables' structure ([MorphoCoverage](#morphocoverage); RE3; E8) |
| 5 | The choice inventory was incomplete | [The choice declaration](#the-choice-declaration), "complete, field by field"; J2 rows; inventory |
| 6 | The shared layout was taken from `channels_from` markers | [ADR 0006](#adr-0006-fast-mode-channel-layout) |
| 7 | A missing `stain_preset` had two refusals | "Missing provider options: one precedence"; step 3; E2, E4 |
| 8 | Conformance rows could pass without testing their claims | [Conformance tests](#conformance-tests): the spy, E3, E5, E6 |
| 9 | Publication was not exclusive | [Publication](#publication) |
| 10 | The J2 order named old releases | [Migration](#migration-per-brick-j2), "Order" |

## Open questions for the owner

Each with the recommendation first. Questions 1-7 are decided
([owner decisions](#owner-decisions-of-17-november-2026)); question 8 is open.

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
   verbatim with a source-scan test. **Decided (19 November 2026, superseding the 17 November
   choice of the pin): no new MorphoBricks dependency;** MorphoCoverage copies the messages, tested
   against normalization's constructors in its test environment.
5. **MorphoCoverage's argument.** *Recommended at first:* the run folder, with the feature output
   found by RE9 (`features_from`). Alternative: the feature output folder itself. **Decided
   (19 November 2026): the feature output itself;** MorphoCoverage validates the tables' structure
   and opens no run folder.
6. **The notebook card's code.** *Recommended:* one renderer in preprocessing (every brick but
   MorphoCoverage depends on it, and its notebook guidelines exist). Alternative: each brick renders
   the card from the declaration. **Decided (17 November 2026): one renderer in preprocessing;**
   MorphoCoverage renders its own card from the same declaration format.
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
