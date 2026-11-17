# What each brick needs today to run on a validated run folder (J1 inventory)

**Status: evidence for [ADR 0007](../adr/0007-run-folder-entry.md), not normative.** Read on
16 November 2026. It records what the code does at the commits below; it is not a statement of
what the bricks should do (that is ADR 0007). Dated evidence, like the files under `docs/audits/`.

A **validated run folder** is a published morphobricks-preprocessing output folder: the
experiment description is published and confirmed (`morphobricks.toml`), the run wrote
`run_manifest.json` and `plane_histograms.csv`, and the mask step checked the masks. Bricks read
it through `RunInputs.open(output_folder)` and the shared resolver (`RunInputs.resolve_request`,
resolver contract version 3, [ADR 0002](../adr/0002-shared-request-resolver.md)).

## Commits read

| Repository | Commit | What it is |
|---|---|---|
| morphobricks-preprocessing | `ce650e39032a5c5890454ec4f17052f240ea0228` | `main` (after `bd6b661`; v0.6.1 is `37c583e`) |
| CellPatcher | `c611101a2a32b1b586cdaf0ec7498b4625ff3ac7` | tag `v0.7.1` |
| MorphoObjects | `0eefed789b01c392f43fceb83edd4ff533776cd4` | `main` (0.5.0, untagged) |
| MorphoEmbed | `fc875372181f1df0fea71fc5919d08cc88dce0c8` | `main` (0.5.0, untagged) |
| MorphoRelate | `5f3a4df2ace1e042f77a4c68cdb64e01833aecf5` | `main` (#253 merged) |
| fiberfeatures | `a7f57c5db444e1b4af855dade6d2a7fe41915750` | `main` (0.7.0 release merged, untagged) |
| MorphoCoverage | `9217840b5d465d1dc5079681f62f00b2dd438996` | `main` |
| MorphoFeature | `7ac74876b382f51bb4f9bfbf1d41519c10ab955a`; PR #236 head `e83811caff2d7137cc2fc2875921ca0196912129` | `main`; ADR 0005 step 8 branch |

Evidence is `path:line` at the commit of the repository named in the table heading. `PP` is
morphobricks-preprocessing.

## What preprocessing gives every brick

| Aspect | Today | Evidence |
|---|---|---|
| Open | `RunInputs.open(output_folder, experiment_root=None, masks_root=None)`: the experiment and masks folders default to where the run recorded them | PP `src/morphobricks_preprocessing/run_inputs.py:201-244` |
| Refused when opened | no `run_manifest.json` ("run preprocessing first"); no published description (`A_DESCRIPTION_REQUIRED`); unconfirmed repeat (`A_DRAFT_REFUSED`); the table, design, calibration, description or conversion record changed since the run; an image or mask changed or gone (fingerprint; content SHA-256 when the run verified content); files added since the run (`UnrecordedFilesError`); another run publishing meanwhile | PP `run_inputs.py:233-240, 246-274, 349-377, 421-438`; `run_inputs_semantic.py:56-86` |
| Codes of those refusals | Only the description refusals carry a code. Every other refusal is a `RunInputsError` whose `code` is `None`: the brick can match the class, not the reason | PP `run_inputs_error.py:17-37` |
| Since the read (PP `main` `1b2adc3`, PR #324) | A folder without `run_manifest.json` whose final report says the run stopped is `RunStoppedError` (`RUN_FOLDER_STOPPED`, `issues` = the run's error issues, byte-equal and in order); a report that cannot be read or is of another report version is `RunReportUnreadableError` (`RUN_FOLDER_REPORT_UNREADABLE`, `path`). Every other refusal above is unchanged (`code` `None`) | PP `run_inputs_error.py:89-135`; `run_inputs_stopped.py:37-182`; `run_inputs.py:446-451`; contract §9.1 "A stopped run" |
| Masks checked | Not checked at open. A requested mask that the mask step has not checked is refused by the resolver (`A_MASK_UNCHECKED`), only when a request names it | PP `run_inputs_semantic.py:234-268`; `run_inputs_request.py:518-535` |
| Output naming | The run folder defaults to `<experiment>_MorphoBricks_Preprocessing` next to the experiment | PP `discovery.py:43, 196`; `cli.py:176` |
| Test runs from Spec fixtures | `make_described_run` writes a tree from a published description, runs preprocessing and the mask step | PP `testing_described.py:1-13, 274` |

## CellPatcher (tag v0.7.1)

| Aspect | Today | Evidence |
|---|---|---|
| Python | `run_patching_pipeline(image_folder_path, *, config, ...)` (one condition and repeat) and `run_patching_condition_repeat_tree(image_root_path, *, config, mask_root_path=None, ...)`; the run folder is `config.common.preprocessing_run` | `src/cellpatcher/orchestration.py:244-260, 406-436`; `config.py:35, 39` |
| CLI | None (no `[project.scripts]`) | `pyproject.toml` |
| Notebook | `notebooks/CellPatcher/CellPatcher.ipynb`: run folder, settings, preview, export; the output folder is prefilled `<root>_CellPatcher` | `README.md:73`; `notebook_ui.py:177, 273` |
| Required arguments | the experiment root (positional, required even though the run records it), the run folder, the mode, the output folder for an export | `orchestration.py:406-423`; `export.py:181-182` |
| Derivable from the folder | experiment and masks roots (recorded), axes, labels, IDs, channel indices, mask pairing, normalization statistics (the run's table) | `README.md:15`; `file_runs.py:213-240` |
| True user choices | mode (`cell`, `random`, `grid`, `whole_fov`); patch size, tile size, number of patches, overlap; the object set (`matching.mask_id`); `binary_mask_policy` (no default); `t_policy`; normalization settings; export format | `config.py:55-58, 93, 98, 123-124, 153` |
| Brick defaults that change values | `cell.patch_size = "auto"`, `random.patch_size = 128`, `random.n_patches = 100`, `grid.tile_size = 128`, `t_policy = "keep"`, `random.seed_scope = "plane_channel"` | `config.py:57, 93, 123-124, 153`; `README.md:51-55` |
| Outputs | `<output_dir>/<condition>/<biological_repeat>[/<technical_repeat>]`: `patches.csv`, patch files, `run_config.json` (with `mask_conversions`) | `orchestration.py:431-436`; `run_config_file.py:60-100` |
| Reruns | Writes into an existing folder (`mkdir(exist_ok=True)`); no identity check or reuse of an earlier export found | `export.py:190-191` |
| Refusals for an unvalidated or stale folder | `RunInputs.open`'s refusals, re-worded into CellPatcher issues with its own codes (`preprocessing_run_refused`, `unrecorded_files`, ...); `A_DESCRIPTION_REQUIRED` kept as the code but with a new message; resolver version checked (`RESOLVER_VERSION_UNSUPPORTED`) | `run_open.py:211-260`; `run_request.py:45, 187-201` |
| Gaps | the experiment root is typed again; two Python functions by tree depth; no CLI; value-changing defaults; refusal messages re-worded; overwrites an earlier export | as above |

## MorphoObjects (main, 0.5.0)

| Aspect | Today | Evidence |
|---|---|---|
| Python | `measure_fov(fov, channels, masks, intensity_requests, ...)` on arrays in memory only; no run-folder function | `src/morphoobjects/measure.py:182-212`; `README.md:93-108` |
| CLI | None | `pyproject.toml` |
| Notebook | None of its own; the documented route for an experiment is MorphoFeature | `README.md:76-91` |
| Run-folder route | Only as a MorphoFeature provider (provider API 3, CPU only) | `src/morphoobjects/morphofeature_provider.json:1-8` |
| Derivable from the folder | FOV key, channel planes by ID, object sets (through `read_objects`), calibration (`RunInputs.pixel_sizes`) | `calibration.py:1-20`; `contracts.py:1-17` |
| True user choices | object sets; the (object set, channel) intensity pairs (never expanded to every pair); the feature selection; `observation_unit` | `measure.py:202-212`; `morphofeature_provider.json` `parameters` |
| Brick defaults that change values | all 25 shape features when none are named; `observation_unit` "object" | `measure.py:188`; `morphofeature_provider.json` `parameters.observation_unit` |
| Outputs, reruns | In memory (`FOVResult`); on disk only through MorphoFeature | `README.md:189-217` |
| Refusals | Shared object-set refusal `A_MASK_NOT_INSTANCES` (preprocessing's checker); no folder-level refusal of its own | `errors.py:34` |
| Gaps | No direct run-folder entry; every run-folder use goes through a MorphoFeature run file | as above |

## MorphoEmbed (main, 0.5.0)

| Aspect | Today | Evidence |
|---|---|---|
| Python | `fetch_weights`, `verify_model`, `load_model`, `embed` on model-ready tensors; no run-folder function | `README.md:231-261` |
| CLI | `morphoembed verify` and `morphoembed report` (weights only) | `src/morphoembed/cli.py:30-49` |
| Notebook | `notebooks/verify_models_colab.ipynb` (weights only) | `notebooks/` |
| Run-folder route | Only as a MorphoFeature provider; the run-level fits (repeat scaling, crop extent) are MorphoFeature's generic fits | `morphofeature_provider.json:3110-3122`; MorphoFeature `src/morphofeature/fits.py:1-15` |
| Derivable from the folder | channels by ID, object sets, repeat groups for the fit, calibration | MorphoFeature README "Fitted parameters" |
| True user choices | model (feature key); `weights_dir` (required, a location); device; normalization (scope, method, percentiles); `crop_mode`; `input_size`; `l2` | `morphofeature_provider.json:3038-3109` |
| Brick defaults that change values | normalization scope `biological_repeat` and method `percentile`; `crop_mode = run_scale`; `input_size` = the model's first; `tf32 = true` | `morphofeature_provider.json:3039-3050, 3063-3078, 3097-3104`; `README.md:263-287` |
| Execution settings | `batch_size`, `num_workers` ("never changes values") | `morphofeature_provider.json:3079-3087` |
| Outputs, reruns | Through MorphoFeature only | `README.md:68-84` |
| Gaps | No direct run-folder entry; the fits it needs live in MorphoFeature, so a direct route would need them | as above |

## MorphoRelate (main 5f3a4df)

| Aspect | Today | Evidence |
|---|---|---|
| Python | `run(...)` and `write_run(result, config, directory)`; `init_project(preprocessing_run, project, ...)` | `src/morphorelate/run.py:128`; `io/outputs.py:443-468`; `project.py:254-290` |
| CLI | `morphorelate init RUN --out PROJECT [--mask ID=ROLE[:POLICY]] [--channels ...]`, `morphorelate inspect CONFIG RUN`, `morphorelate run CONFIG RUN OUTPUT_DIR` | `cli.py:109, 121-172`; `README.md:41-47` |
| Notebook | `notebooks/MorphoRelate_your_data/` (preprocessing's steps, then MorphoRelate) | `README.md:59-62` |
| Required arguments | a configuration file, the run folder, an output folder | `cli.py:124-126` |
| Derivable from the folder | experiment and masks roots, axes, pixel sizes and their source, channel IDs and their index per image, mask IDs and representations | `README.md:47-58`; `io/run_source.py:55-65` |
| True user choices | mask roles (`cell`, `nucleus`, `structure`, `region`); `binary_mask_policy`; analysis units; the time point (`input.t`) when images have several; feature parameters | `project_config.py:195-225, 267-271, 295-310` |
| Asked once? | `init` writes every undecided value as a `"<CHOOSE: ...>"` placeholder that `run` refuses until filled; it never overwrites a configuration | `placeholders.py:1-30`; `config_file.py:165-170`; `project.py:150-155` |
| Re-declared | `[input.channels]` restates each channel ID with its C index as a cross-check of the resolver's index; `input.z` placeholder still offers a Z projection although preprocessing refuses Z-stacks | `project_config.py:108-140, 213-217` |
| Outputs | `OUTPUT_DIR`, staged and published with `run_config.json` (each file's SHA-256) written last as the completion marker | `io/outputs.py:449-456` |
| Reruns | A rerun replaces the earlier run's files in the same folder; no reuse | `io/outputs.py:449-456` |
| Refusals | `RunInputs.open`'s refusals passed on unchanged; resolver version checked | `io/run_source.py:55-65`; `io/run_request.py:65, 163-175` |
| Gaps | three positional paths; the configuration is a separate project folder; one time point per run; channel indices restated; replaces an earlier output | as above |

## fiberfeatures (main a7f57c5, 0.7.0)

| Aspect | Today | Evidence |
|---|---|---|
| Python | `analyze_run(preprocessing_run, analysis_mode="ecm", *, channel_ids=None, sample_id_from="fov", **options)`; `optimize_parameters(..., preprocessing_run=...)` | `src/fiberfeatures/batch.py:649-680`; `optimize.py:198` |
| CLI | None | `pyproject.toml` |
| Notebook | `notebooks/02_batch_conditions.ipynb` (a run folder, `OUTPUT_DIR`), `03_optimize_parameters.ipynb` | notebook cells `PREPROCESSING_RUN`, `OUTPUT_DIR` |
| Derivable from the folder | channels by ID per image, masks by ID, the length unit (um when the run records pixel sizes, pixels when it states `pixels`), image type (RGB units) | `README.md:109-145` |
| True user choices | `analysis_mode`; channels; masks and roles; `binary_mask_policy`; lengths in um on a calibrated run (`scales`, `sigma_in`, `preprocess_denoise_sigma`); the RGB preset; device; patch settings | `README.md:121-145`; `config.py:76`; `batch.py:345-362` |
| Brick defaults that change values | `analysis_mode` is `"ecm"` in `analyze_run` but `"cellular"` in `analyze_metadata`; every channel when none named; `length_unit = "pixels"`; device `"cpu"` | `batch.py:347, 350, 651, 665-666`; `config.py:76` |
| Spec-defined default in use | the scoring unit of `optimize_parameters` is the biological repeat (`repeat_group`, ADR 0002 AR6) | `optimize.py:198` |
| Naming | the direct route's RGB preset is `RGBInputConfig.preset`; the provider option is `stain_preset` | `rgb_input.py:68-88`; `morphofeature_rgb.py:41` |
| Outputs | `analyze_run` returns data frames; the notebook writes them under a new timestamped `RUN_DIR` in `OUTPUT_DIR` | `batch.py:649-680`; `02_batch_conditions.ipynb` |
| Reruns | A new timestamped folder each time; no reuse | `02_batch_conditions.ipynb` |
| Refusals | `RunInputs.open`'s refusals unchanged; resolver version checked; every `A_*` refusal before any pixel | `run_reading.py:98-125`; `run_request.py:41, 65`; `README.md:128-131` |
| Gaps | no CLI, no file output from Python; two different `analysis_mode` defaults; option names differ between routes | as above |

## MorphoCoverage (main 9217840)

| Aspect | Today | Evidence |
|---|---|---|
| Input | Feature tables, not a run folder: `objects` and `fovs` tables, and MorphoFeature's export `coverage.json` (schema 3) with the description's `experiment` block | `README.md:44-56`; `src/morphocoverage/described.py:1-40, 459` |
| Python | `workflows.guide(...)`, `workflows.Setup`, `described_setup`, `report`, `optimise`, `live_session` | `README.md:40` |
| CLI | `python -m morphocoverage.workflows OBJECTS [FOVS] [--folder RESULTS]` (no console script) | `src/morphocoverage/workflows/__main__.py:17-28` |
| Notebook | `notebooks/MorphoCoverage_Workflows_Example/` | `README.md:40` |
| Depends on preprocessing | No (and not on normalization) | `pyproject.toml:13-20` |
| Derivable | conditions, references (the default controls), repeat groups, target suggestions, from the exported description block | `described.py:12-30` |
| True user choices | feature columns; a control that overrides the reference; what the acquisition must preserve; normalisation to the control; confirmed targets | `README.md:40`; `described.py:20-28` |
| Asked once? | `guide()` saves the answers in the results folder so a later session continues | `README.md:40` |
| Refusals | `DescriptionRefused` with codes (`COVERAGE_VERSION_UNKNOWN`, `DESCRIPTION_VERSION_UNKNOWN`, `NOT_EXPORTED`, `MISSING`, ...) | `described.py:31-40` |
| Gaps | not reachable from a run folder; tables are passed by path; no link from the run folder to the feature export it should read | as above |

## MorphoFeature (main 7ac7487; PR #236 e83811c)

| Aspect | Today | Evidence |
|---|---|---|
| Python | `load_run_config(path)`, `run_from_config(config)`; lower level `plan_workflow`, `run_workflow`, `write_run`, `load_run`, `TrialRunner` | `README.md:289-314`; `src/morphofeature/cli.py:167`; `run_config.py:321` |
| CLI | `morphofeature check RUN_FILE` and `morphofeature run RUN_FILE` (`--to-segment`, `--overwrite`) | `cli.py:326-360` |
| Notebook | `notebooks/MorphoBricks_end_to_end.ipynb` (preprocessing steps, a form that writes the run file, check, run, MorphoCoverage) | `README.md:275-287` |
| Required keys | `preprocessing_run`, `masks`, `requests`, `output` | `run_config.py:91-96` |
| Derivable from the folder (refused when given) | `fovs`, `image_axes`, `mask_axes`, `calibration`, `histograms`, `experiment_design` are refused by name; `channels` and `shared_channel_layout`, when given, must equal what the description says | `README.md:193-199` |
| True user choices | object sets (mask IDs) and `binary_mask_policy`; observation units; requests (provider, features, channels, compartments); per-brick parameters (fiberfeatures lengths in um on a calibrated run); patch sets; provider options (`stain_preset`, PR #236) | `README.md:83-127`; PR #236 `src/morphofeature/provider_options.py:39-58` |
| Brick defaults that change values | `fit_from_histograms: true` (fit from the run's histograms rather than the images) | `README.md:199-202` |
| Execution settings | `workers`, `window_execution` | `run_config.py:91-94` |
| Outputs | the run file's `output` (relative to the run file): `run_manifest.json`, `fovs`, `objects/`, `features/`, `coverage/`, `patches/`; folder schema 4 at PR #236 | `README.md:420-440`; `run_config.py:313`; PR #236 `docs/contracts/run-folder.md:89-94` |
| Reruns and caching | An existing output folder is never overwritten; `TrialRunner` reuses provider outputs from an on-disk cache keyed by the installed code (RECORD SHA-256, Git commit, manifest SHA-256, library versions); an editable install is never cached | `README.md:264`; `README.md:590-625` |
| Refusals | `A_DESCRIPTION_REQUIRED`, `A_DRAFT_REFUSED`, `A_MASK_UNCHECKED`, `A_SCOPE_INCOMPLETE`, `A_RGB_NOT_SUPPORTED` before anything is computed, printed as JSON (exit 1); resolver version checked at PR #236 | `README.md:183-190, 262-273`; PR #236 `mask_selection.py:69` |
| Gaps | the run folder and the output are typed in a separate run file; `run` takes a file, not a folder | as above |

## Gap summary

1. **No common entry.** Four bricks reach a run folder directly (CellPatcher, MorphoRelate,
   fiberfeatures, MorphoFeature), each with another signature: a positional experiment root
   (CellPatcher), a configuration plus run plus output (MorphoRelate), a run plus keyword options
   with no file output (fiberfeatures), a run file naming the run (MorphoFeature). MorphoObjects
   and MorphoEmbed have no run-folder route of their own; MorphoCoverage reads feature tables,
   not run folders.
2. **Paths typed again.** CellPatcher requires the experiment root that the run already
   records; MorphoRelate and MorphoFeature take the run folder inside a separate configuration;
   no brick derives its output folder from the run folder by a rule (CellPatcher's notebook
   prefills one; preprocessing has one for its own output).
3. **Settings declared again.** MorphoRelate restates channel indices; MorphoFeature accepts
   `channels` and `shared_channel_layout` that must equal the description; the RGB preset has two
   names (`preset`, `stain_preset`).
4. **Hidden defaults that change values.** CellPatcher patch sizes, tile size and number of
   patches; fiberfeatures `analysis_mode` (two different defaults), every channel, the length
   unit; MorphoEmbed normalization, crop mode and input size; MorphoObjects' feature set;
   MorphoFeature's fit source. Only a few defaults are the Spec's (the resolver capabilities,
   the scoring unit `repeat_group`, the whole-plane route, the description's `reference` as the
   control).
5. **Refusals without a code.** Preprocessing's stale-folder refusals have `code = None` (since
   PR #324 a stopped run and its unreadable report carry `RUN_FOLDER_STOPPED` and
   `RUN_FOLDER_REPORT_UNREADABLE`);
   CellPatcher re-words them under its own codes; the others pass the text through. A user cannot
   tell "stale" from "not a run" by code.
6. **Reruns differ.** Overwrite in place (CellPatcher), replace (MorphoRelate), a new timestamped
   folder (fiberfeatures notebook), never overwrite (MorphoFeature). Only MorphoFeature's trial
   cache reuses by identity.
7. **Choices asked once only in two places.** MorphoRelate's `init` placeholders and
   MorphoCoverage's saved answers; elsewhere each notebook and each script asks again.
