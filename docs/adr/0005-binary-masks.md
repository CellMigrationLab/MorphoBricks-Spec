# ADR 0005: one policy for binary masks

- **Status:** **Accepted** (15 November 2026, after four independent review rounds; not implemented yet: the per-brick PRs follow the [order below](#implementation-order)). The owner decisions it encodes (15 November
  2026, BM1-BM5 below) are final; what this ADR adds is their encoding: where the one helper and the
  one region checker live, the record, the vocabulary, the messages and the PR order. Those choices
  are listed under [modelling choices](#modelling-choices-for-the-owners-review). It amends the
  normative [`experiment-v1.md`](../experiment-v1.md) §4.5, §4.5b and §8 (BM11: the values a `binary`
  mask may hold), [ADR 0001](0001-experiment-description-v1.md) (D10 and the stale "4-connected"
  evidence) and [ADR 0002](0002-shared-request-resolver.md) AR5 (who applies the conversion), and adds
  resolver contract version 3. No fixture, golden or validator changes: the value rule needs mask
  pixels, which no description TOML and no part of `tools/audit/refval.py` carries
  ([below](#amendments-made-by-this-adr)); `python -I tools/audit/refval.py fixtures .` is unchanged.
- **Revised** on 15 November 2026 after an independent review (verdict "merge after fixes", blockers
  B1-B6 and five filed items): the value rule in the normative text (B1), uses routed by
  `(mask ID, use)` (B2), `RegionEstimate` (B3), one constructor per refusal code (B4), the lineage
  record of the conversion helpers (B5), the supported resolver versions (B6). Revised again the same
  day after the re-check: uses sent to the resolver one entry per use and aggregated only after it
  (B2), one normalization constructor for `RESOLVER_VERSION_UNSUPPORTED` (B4), helpers on `RunInputs`
  with output mask IDs, collision refusals and paired publication (B5), the file-wide value rule and
  the dtype rule (N1), and a lineage digest over a canonical header and the pixels (N2). Revised a third time the same day after the second re-check
  (blockers B1-B3, five filed items): the run-wide `parent_labels` region rule stated, with F08d (B1);
  the lineage `root` and paths relative to the masks folder, OME-Zarr label images refused by the
  helpers (B2); idempotent retries only for the same source in every key, an equal-pixel other
  source refused (B3); class values bounded by `LARGEST_LABEL`; publication described as
  reader-consistent, not atomic. Fourth revision after the third re-check: fraction uses count in the
  run-wide `parent_labels` rule (F08d (iii)); output paths from the FOV's image identity for both
  mask layouts (F11 (n)); F12 (n) split between the mask step and the helper; lineage `root` reader
  test (F11 (o)); modelling choices marked accepted or proposed.
- **Tracking:** [#42](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/42) ("one
  consistent, simpler policy for binary masks across all bricks"). The implementing PRs follow in the
  [order below](#implementation-order), one per brick.
- **Why a fifth ADR file.** ADR 0001 rules on the description, ADR 0002 on the resolver, ADR 0003 on a
  run artefact, ADR 0004 on windowed execution. This decision rules across all of them on one
  question, *when does a binary mask become objects, who labels it, and what is a region*, and changes
  the code of eight repositories. By ADR 0002's convention it gets its own file, numbered next.

## Context

`representation = "binary"` (experiment-v1 §4.5) and the per-request conversion
`binary_mask_policy = "connected_components"` (§4.5c, ADR 0001 AQ9, ADR 0002 AR5) are specified, but
the code that applies them grew brick by brick. An inventory pass of 15 November 2026 read every place
a binary mask is declared, checked, labelled, used as a region, converted, refused or recorded, at
these `origin/main` commits:

| Repository | Commit |
| --- | --- |
| morphobricks-preprocessing | `119503841885` |
| CellPatcher | `d72e1dcb1c1d` |
| MorphoFeature | `b6a711e6a1e4` |
| MorphoObjects | `ccd030f0b409` |
| MorphoRelate | `15813f07cd99` |
| MorphoEmbed | `035cf164566f` |
| fiberfeatures | `752b1dd2b3d2` |
| morphobricks-normalization | `b8aa65bf597c` |
| MorphoBricks-Spec | `aa9cfc69a9b3` |

It found the same question answered differently (each `path:line` is in the named repository):

| # | Inconsistency | Evidence |
| --- | --- | --- |
| I1 | **Connectivity is a setting in CellPatcher and a constant elsewhere.** CellPatcher direct runs take `cell.binary_mask_connectivity` (1 or 2); MorphoFeature, MorphoRelate and fiberfeatures pass `BINARY_MASK_CONNECTIVITY = 2`. A corner-touching pair is 2 objects in one route and 1 in another; the notebook label says "8-connected" whatever the config holds. | CellPatcher `config.py:97`, `strategies/cell.py:102`, `file_runs.py:249`, `notebook_form.py:107`; `object_geometry.py:40` |
| I2 | **A second labeller.** MorphoRelate splits a binary structure mask without a policy into 8-connected component rows itself, with no conversion record and no `A_MASK_NOT_INSTANCES`; with the policy it uses the shared labeller and records it. | MorphoRelate `structures_table.py:56`, `:117-128`; `config_masks.py:96-106`; `io/run_masks.py:116-119` |
| I3 | **Who may convert in memory.** CellPatcher labels a boolean array with a policy; MorphoRelate refuses the policy in memory; MorphoFeature, MorphoObjects and MorphoEmbed refuse the array, each with its own message. | CellPatcher `strategies/cell.py:92-109`; MorphoRelate `config_masks.py:117-122`; MorphoFeature `feature_requests.py:250-254`; MorphoObjects `validation.py:57-61`; MorphoEmbed `provider_crops.py:217-218` |
| I4 | **"Binary" inferred from the dtype in memory**, against experiment-v1 §4.5 ("never inferred from dtype"): CellPatcher reads bool as binary and integer 0/1 as one object. | CellPatcher `mask_policy.py:3-7`, `strategies/cell.py:54-62`; MorphoRelate `geometry/masks.py:32-34` |
| I5 | **Region dtype and value rules differ.** One shared checker refuses floats, but CellPatcher's fraction masks, random sampling and windowed masks accept them; MorphoFeature's `FovInput` refuses boolean regions; normalization accepts **only** booleans; fiberfeatures uses `> 0`, the others `!= 0`. | CellPatcher `patch_checks.py:69-88`, `fractions.py:142-144`, `strategies/random.py:76`, `mask_windows.py:76`; MorphoFeature `feature_requests.py:250-254`; normalization `optical_density.py:293-294`; fiberfeatures `run_rows.py:210`, `channel_alignment.py:131` |
| I6 | **A region becomes cells.** fiberfeatures hands a region's foreground to CellPatcher cell mode when no object mask is given; CellPatcher may label it under its own config while the fiberfeatures record says no conversion. | fiberfeatures `batch.py:57-66`, `run_rows.py:210`, `run_request.py:342-348` |
| I7 | **Z-stacks.** CellPatcher labels each plane of a stack separately; fiberfeatures refuses a conversion when Z > 1. | CellPatcher `run_request.py:67-74`; fiberfeatures `run_request.py:308-312` |
| I8 | **Masking with a labelled mask** is refused in memory but accepted in a file run, because the check reads the dtype and is skipped under `resolved_masks()`. | CellPatcher `mask_policy.py:81`, `:94-125`, `file_runs.py:443` |
| I9 | **The windowed refusal is too broad.** `MASK_WINDOW_CONVERTED` keys on every mask ID converted anywhere in the run, so a region or fraction read of that mask, which needs no labels, is refused too. It is checked twice, with two messages. | MorphoFeature `window_reads.py:327-333`, `mask_selection.py:323-324`, `fov_files.py:412-416` |
| I10 | **Empty region: four answers.** MorphoFeature refuses the plane (`sampling_mask_empty`), fiberfeatures stops the row, normalization raises, MorphoObjects returns NaN `empty_region`. | MorphoFeature `patch_sets.py:457-462`; fiberfeatures `run_rows.py:211-215`; normalization `optical_density.py:297-298`; MorphoObjects `provider_patches.py:12-13`, `:69` |
| I11 | **One refusal, five wordings**; only the resolver and CellPatcher give the code `A_MASK_NOT_INSTANCES`. | preprocessing `run_inputs_request.py:471-478`; CellPatcher `strategies/cell.py:95-101`; MorphoObjects `validation.py:57-61`; MorphoFeature `feature_requests.py:251-254`; MorphoEmbed `provider_crops.py:179-180`; MorphoRelate `config.py:149` |
| I12 | **The policy-on-the-wrong-mask check is repeated** 4-5 times with different text. | preprocessing `run_inputs_request.py:352-363`; CellPatcher `run_request.py:156-163`, `mask_policy.py:85-91`; MorphoFeature `mask_selection.py:190-194`; MorphoRelate `config.py:164-168` |
| I13 | **Three provenance shapes.** MorphoFeature and MorphoRelate write `conversion`/`labeller`/`connectivity`; fiberfeatures `binary_mask_policy`/`binary_mask_connectivity` without a labeller; CellPatcher its whole config (connectivity written even when nothing was labelled) and `mask_conversions` for `parent_labels_as_area` only. | MorphoFeature `mask_selection.py:343-353`; MorphoRelate `io/run_masks.py:218-230`; fiberfeatures `run_request.py:346-348`, `:371-372`; CellPatcher `run_config_file.py:72`, `:103-106` |
| I14 | **"Binary" values.** The mask step accepts any ≤ 2 values ({3, 7} passes); the labeller wants 0 and one positive value. | preprocessing `mask_representation.py:45`, `:117`; CellPatcher `object_geometry.py:237-243` |

Duplicated paths: five labelling call sites (CellPatcher `run_request.py:67-74`,
`strategies/cell.py:92-109`; MorphoFeature `fov_files.py:307-314`; MorphoRelate
`io/run_masks.py:157-189`; fiberfeatures `run_request.py:267-314`), four copies of
`BINARY_MASK_POLICIES` (preprocessing `run_inputs_request.py:51`; CellPatcher `object_geometry.py:31`,
`setting_checks.py:31`; MorphoRelate `config.py:77`), a restated 8-connected structure in preprocessing
(`mask_pairs.py:19-21`, "not imported"), and the CellPatcher `_RESOLVED` bypass that exists only
because file-run masks are labelled before the in-memory checks run (`mask_policy.py:29-39`).

The dependency graph constrains where shared code can live (each brick's `pyproject.toml`/`setup.py`):
normalization (numpy only) ← preprocessing (adds scipy) ← CellPatcher ← MorphoObjects, MorphoRelate,
MorphoEmbed, fiberfeatures, MorphoFeature. Every brick that converts a mask reads it through
preprocessing's `RunInputs`; normalization can import neither preprocessing nor CellPatcher.

## Decisions

The owner decided BM1-BM5 and BM11-BM14 on 15 November 2026 and BM15 on 16 November 2026 (final). BM6-BM10 are this ADR's encoding of them.

| ID | Decision | Rejected alternative |
| --- | --- | --- |
| BM1 | **Connectivity is 8, fixed, and is not a parameter anywhere** (owner). Two foreground pixels are one object when they share an edge or a corner. No config key, argument, CLI flag, notebook control or record field chooses it; the record states it (`connectivity: 8`). CellPatcher's `cell.binary_mask_connectivity` and its notebook checkbox are removed. | A setting with 8 as default (today's CellPatcher: two routes give 1 or 2 objects for one mask, I1); 4-connected (fewer objects for the same pixels than skimage, ImageJ and MorphoRelate's CellProfiler parity). |
| BM2 | **One labeller, one record** (owner). `representation` in the description is the only declaration that a mask is binary. The conversion of a `binary` mask to objects is decided and recorded **once**, by preprocessing's request resolver, as `{mask_id, conversion, connectivity, labeller}`, and applied by **one helper**, `RunInputs.read_objects` in preprocessing (BM6). Every brick copies the record as is. There is no other labeller: MorphoRelate's own splitting of binary structures is removed, and rows per component need the recorded conversion. | Each route calling CellPatcher's labeller (ADR 0002 AR5 as written: five call sites, three record shapes, I2, I13); labelling once in the mask step on disk (a labelled copy of every mask; still rejected, AR5). |
| BM3 | **A mask used as a region is `mask != 0`, never labelled** (owner), whatever its representation. One shared region checker (BM7): 2-D, integer or boolean, no floats. **An empty region gives undefined values with a recorded reason, never 0 and never a crash; the plane still runs** (BM8). | Per-brick region rules (I5); `> 0` (equal to `!= 0` only while negative labels are refused upstream); refusing the plane or the run on an empty region (I10). |
| BM4 | **In memory (Python API) an object set is an integer instance array** (owner). A boolean array is accepted **only as a region**. Every other object set is refused with the one code `A_MASK_NOT_INSTANCES` and the one message of BM9. No in-memory API converts, labels or carries `binary_mask_policy`. | CellPatcher's in-memory policy (dtype decides "binary", I3, I4); a per-brick message (I11). |
| BM5 | **Lazy windowed route** (owner): a converted mask used as **objects** stays refused (`MASK_WINDOW_CONVERTED`); its **region and fraction reads are allowed** by window. The check keys on the objects use, not on the mask ID (I9), and runs once, before any pixel is read. Uses are routed **by use, not by mask ID**: one source mask may serve, in one run, one converted objects use (one record) and any number of unconverted region and fraction uses, which read the raw mask, `!= 0` ([uses of one mask](#uses-of-one-mask-in-one-run-bm2-bm5)). **Volumes (Z) are refused for conversion.** | Refusing every read of a mask ID converted anywhere in the run (today, I9); streamed labelling with seam merging (design `one-route.md` §5; not scheduled by this ADR); labelling a Z-stack plane by plane (2-D pieces of one slice are not the objects of a 3-D mask, I7). |
| BM6 | **The helper lives in preprocessing**: `RunInputs.read_objects(selection, mask_id, t, z)` returns the plane's object labels, applying the selection's recorded conversion (reasons [below](#why-the-helper-is-in-preprocessing)). CellPatcher's `label_objects` and its constants are removed. | The helper in CellPatcher (reasons below). |
| BM7 | **The region checker lives in normalization**: `morphobricks_normalization.regions.check_region(mask, shape, *, name)` returns the boolean foreground or raises `MASK_REGION_INVALID` ([contract](#region-checker-contract-bm3-bm7)). It is the only package every brick can import, normalization's own `region_white` included. | The checker in CellPatcher (`check_region_mask` today; normalization cannot import it) or in preprocessing (same reason); one checker per brick (I5). |
| BM8 | **One undefined reason for an empty region, `empty_region`** ([vocabulary](#undefined-reason-vocabulary-bm8)). A value whose denominator is the region's pixels is undefined; a value whose denominator is another, non-empty area (the fraction of a patch inside the region) is defined and may be 0. In normalization an estimate over a region is a [`RegionEstimate`](#region-estimates-in-normalization-bm3-bm8), never NaN. | A refusal (`sampling_mask_empty`, fiberfeatures' row stop, normalization's `ValueError`); 0 for a mean over no pixels; NaN as a fitted white or stain vector. |
| BM9 | **Refusal codes and messages are fixed here** ([table](#refusal-codes-and-messages)): `A_MASK_NOT_INSTANCES` (resolver and in memory), `A_VOLUME_NOT_SUPPORTED` (a conversion of a Z-stack), `MASK_WINDOW_CONVERTED`, `MASK_REGION_INVALID`, `R_MASK_CONTRADICTS_REPRESENTATION` (mask step and read guard) and `RESOLVER_VERSION_UNSUPPORTED`. Each code has **one constructor function**; every other place propagates the constructed error unchanged ([construction and propagation](#construction-and-propagation)). | Each brick rewording the shared refusals (I11, I12). |
| BM10 | **Resolver contract version 3.** The resolver adds the conversion record to its `Provenance`, refuses a conversion on a Z-stack, and accepts a mask ID in several request entries (one per use); entries of one `(mask_id, role)` with the same conversion give one selection, and two different conversions of the `objects` use are refused ([uses of one mask](#uses-of-one-mask-in-one-run-bm2-bm5)). Every consumer accepts **exactly** the resolver versions it supports, `{3}` in this wave, before any pixel read, output or cache reuse ([resolver version](#resolver-version-check-bm10)). | Recording the conversion only in each brick (I13); leaving the version at 2 (a consumer could not tell whether its resolver gives the record); `>= 3` (assumes every future contract is compatible). |
| BM11 | **Strict binary at the mask step** (owner, 15 November 2026): every file of a mask declared `binary` is stored as integers (signed or unsigned) or booleans, never floats (also when integer-valued), and holds values in **{0, v} for one positive v**, checked over the **whole file** (all its planes together). An **all-zero** file is accepted (zero objects; an empty region where used as a region) and an **all-foreground** file {v} is accepted. A file with two or more distinct positive values (for example {0, 3, 7} or {3, 7}), or any negative value, is refused at the mask step with `R_MASK_CONTRADICTS_REPRESENTATION`, so the refusal comes before any run, not at read (closes I14; F10 moves to the mask step). `experiment-v1.md` §4.5, §4.5b and §8 state this rule. | Any non-zero as foreground (a mask that is really labels or classes passes as binary and is labelled silently); "at most two distinct values" (today's text: {3, 7} passes). |
| BM12 | **Explicit conversion helpers in preprocessing** (owner): the user converts masks on purpose, as a recorded step that writes **new mask files** declared with their own representation: **binary → instance labels** (the BM1/BM6 labelling: connected components, 8-connected) and **class label image → one binary mask per class value** (for class/semantic segmentation). Each output carries a lineage record (source and output with their content SHA-256, operation, class value or connectivity, helper and version; [schema](#the-conversion-helpers-bm12)), like preprocessing's existing named-axis copies (`convert`). The run then declares the outputs and reads them like any mask. | Converting implicitly at read only (users cannot produce instance or per-class masks they can inspect, share or edit); a labelled copy of every binary mask, made automatically (AR5, still rejected: here nothing is converted unless the user asks, and the source is unchanged). |
| BM13 | **Notebook display** (owner): CellPatcher's notebook shows the recorded conversion of a file run **read-only**; it offers no binary-mask setting. | A file-run-only control (a second place to decide what BM2 decides once). |
| BM14 | **Grouping inside `parent_labels` is a measurement, not a labeller** (owner): MorphoRelate's rows per group of an already-labelled `parent_labels` mask (`structures_table.py:89-114`) are allowed; BM2's "no other labeller" applies to binary masks only. | Routing parent-label grouping through the recorded conversion (the user's labels already define the groups). |
| BM15 | **Derived region masks from an image** (owner, 16 November 2026): preprocessing may offer an opt-in helper that computes a `binary` **region** mask from one declared image with a **named, versioned, fixed rule** whose colour maths is called from normalization's `stain` module (never reimplemented). The first is `RunInputs.he_tissue_mask` (rule `he_tissue_v1`: nuclei, red blood cells and near-white background excluded) on a unit declared `image_type = "rgb"`. Like BM12, it writes a **new mask file** with a lineage line, never runs by default, and nothing reads the output until the user declares it (`representation = "binary"`) and the mask step has checked it. The output is a region (BM3), never an object set (`experiment-v1.md` §4.5c). | A mask built inside each consuming brick (fiberfeatures builds none); a mask made automatically for every RGB run; per-image tuned thresholds. |

### Why the helper is in preprocessing

The owner left the choice between preprocessing and CellPatcher to this ADR. The inventory decides it
for preprocessing:

1. **The read is already the only door.** After BM4 nothing converts in memory, so every conversion
   happens in a described file run, and every file run reads its masks through preprocessing's
   `RunInputs` (MorphoFeature `fov_files.py:296-314`, MorphoRelate `io/run_masks.py:157-189`,
   fiberfeatures `run_request.py:267-314`, CellPatcher `run_request.py:67-74`). Labelling at that read
   replaces five call sites, each with its own plane loop and error wrapping, by one. With CellPatcher's
   helper the four call sites would stay, each still reading the plane through `RunInputs` first.
2. **The record names code of the same release.** The resolver writes `labeller` and `connectivity`;
   with the helper in the same package they describe code covered by the same `RESOLVER_VERSION` and
   release tag. CellPatcher depends on preprocessing (AR5), so the resolver would record a labeller it
   cannot import or check.
3. **Z and windows are refused where they are read.** `Fov.z_count` and the window read
   (`masks/window.py:7-10`, `run_inputs_mask.py:82-86`) are preprocessing's.
4. **Preprocessing already has the parts:** scipy, `check_labels` (`masks/labels.py:15`) and the
   8-connected structure it restates "not imported" (`mask_pairs.py:19-21`). The restatement goes: the
   mask step's piece counter imports the helper module's structure.
5. **CellPatcher has no use left.** Its only labelling not through a file run was the in-memory policy
   (`strategies/cell.py:92-109`), which BM4 removes. MorphoRelate and fiberfeatures import CellPatcher
   for this one function.

It does not break AR1: the resolver (`resolve_request` and its modules) still reads no pixel and labels
nothing (its import-scan test stands); `read_objects` is in the reading modules of `RunInputs`, which
already read pixels. AR5's rejected alternative, labelling once in the mask step with a labelled copy
on disk, stays rejected: nothing labelled is written.

## The conversion record (BM2, BM10)

The resolver builds one record per **mask ID** of the request whose selection has a `conversion`, in
request order of that selection, and returns them in `Provenance.mask_conversions`. A mask ID has at
most one record: only its `objects` use can carry `connected_components`, only a `parent_labels`
region carries `parent_labels_as_area`, and a `parent_labels` mask is never objects, so the two never
meet on one ID ([uses of one mask](#uses-of-one-mask-in-one-run-bm2-bm5)). A record has exactly these
four keys, in this order, all always present:

| Key | Type | Value |
| --- | --- | --- |
| `mask_id` | text | the description's mask ID (never a source type) |
| `conversion` | text | `connected_components`, or `parent_labels_as_area` (ADR 0001 PL1) |
| `connectivity` | integer or null | `8` for `connected_components`; null for `parent_labels_as_area` |
| `labeller` | text or null | `morphobricks_preprocessing.RunInputs.read_objects` for `connected_components`; null for `parent_labels_as_area` |

```json
{"mask_id": "TumorRegion", "conversion": "connected_components", "connectivity": 8, "labeller": "morphobricks_preprocessing.RunInputs.read_objects"}
```

`connectivity` is `8`, the number of neighbours, not SciPy's `generate_binary_structure` rank (`2`)
written today. A mask used as instances, or as a region with no marker, has no record. Each brick
writes the list under the key `mask_conversions` in its run record (MorphoFeature's run manifest, the
`run_config.json` of MorphoRelate and CellPatcher, fiberfeatures' run record): the resolver's list,
in its order, with no key added, renamed, dropped or converted. What a brick adds about the mask (its
object-set name, the roles it mapped) goes in its own fields beside it.

`MaskSelection.conversion` is unchanged. The request keeps its input `binary_mask_policy`
(`connected_components` or none): it is the per-request choice of experiment-v1 §4.5c, and it stays
forbidden in the description (`i112`).

## Uses of one mask in one run (BM2, BM5)

Today one mask ID is one use: preprocessing's `check_request` refuses "a mask ID is requested twice"
(`run_inputs_request.py:333-337`), MorphoFeature's `mask_uses` folds every use of a mask ID into one
`MaskUse` with one resolver role, `objects` winning (`mask_selection.py:157-196`, `:141-154`), and its
window code keys the conversion on the mask's name (`window_reads.py:327`, `fov_files.py:412`). So a
run cannot use a converted mask as objects and the same mask as a region or fraction. This ADR routes
**by use, not by mask ID**:

- **Uses.** A use is `objects` (an object set: a request's object set, a relation mask, a cell patch
  set's object set), `region` (a patch request's region mask, a patch set's sampling mask, a
  `restrict_to`, an analysis region) or `fraction` (a mask whose share each patch reports). Only an
  `objects` use can carry a conversion; `region` and `fraction` uses read the **raw** mask and take
  `mask != 0` through `check_region` (BM3), never labelled.
- **One source mask, many uses.** In one run a mask ID may serve any number of object sets in the
  `objects` use, all with the **same** conversion (all with the policy, or all without), and any
  number of `region` and `fraction` uses. It then has exactly one conversion record (when its
  `objects` use is converted), and that record says nothing about its region and fraction reads.
- **Preprocessing's request resolution** (`check_request`). A `MaskRequest` is identified by
  `(mask_id, role)`, and a mask ID may appear in several entries. The version-2 refusal "a mask ID is
  requested twice" is replaced by **one** `ValueError`: the same mask ID requested as `objects` with
  two different conversions (a policy and none count as two): `{mask_id!r} is requested as objects
  with two different conversions ({a!r} and {b!r}); one run converts a mask at most one way`, with
  `a` and `b` in request order. Entries of one `(mask_id, role)` with the same conversion are
  accepted and collapse into one selection; `(mask_id, "objects")` and `(mask_id, "region")` in one
  request are accepted. Coverage, `A_SCOPE_INCOMPLETE` and `A_MASK_UNCHECKED` are computed **once per
  mask ID** (the files are the same), not once per entry or role. `FovSelection.masks` holds one
  `MaskSelection` per `(mask_id, role)`, in the order of its first entry; the `objects` one carries
  the conversion, the `region` one has none.
- **MorphoFeature sends, then aggregates** (`resolve_masks`, `mask_uses`, `region_masks`,
  `_selected`, `mask_record`). MorphoFeature does **not** merge uses before resolution and makes no
  local check of their policies (today's "different binary_mask_policy values" refusal at
  `mask_selection.py:182-187` and the region-policy refusal at `:189-194` are removed). It sends
  **one `MaskRequest` per object set and per region or fraction use**, in run order, in the one
  request it gives `resolve_request`: each object set as `(mask_id, "objects", its policy)`, each
  region or fraction use as `(mask_id, "region", its policy or None)`. The resolver validates them
  together, so a conflict (for example `CellsA` reading `TumorRegion` with `connected_components` and
  `CellsB` reading it without a policy) is refused by preprocessing's `ValueError`, propagated
  unchanged ([construction and propagation](#construction-and-propagation)); a policy on a region or
  fraction use is likewise the resolver's malformed-request `ValueError` (I12). Only **after a
  successful resolution** does `mask_uses` aggregate, into one `MaskUse` per `(mask_id, use)` with that
  use's object-set names; `objects` no longer absorbs a region or fraction use of the same ID.
  `SelectedMasks.conversions` is keyed by `(image, object set)` of the `objects` use only; nothing
  keyed by mask ID alone decides how a plane is read. The manifest's `masks` entries are one per
  `(mask_id, role)`, beside the resolver's `mask_conversions` list.
- **A `parent_labels` mask used as a region by several consumers** (owner, 15 November 2026: the
  rule already released, stated here). `parent_labels_support` is a capability of the whole
  `Request`, not of one `MaskRequest`, and this ADR does not change that. MorphoFeature asks the
  resolver with `parent_labels_support = true` only when **every** consumer of the run's region
  masks declares it (`region_parent_labels_support`), and a **`fraction` use counts as a consumer
  that does not**: a fraction is always an area (`!= 0`), so any fraction use of a `parent_labels`
  mask makes it `parent_labels_as_area` for the run. `region_masks` and
  `region_parent_labels_support` therefore take the fraction uses too (today they cover patch
  regions and sampling masks only, `mask_selection.py:141-154`, `:199-218`; PR 8 changes them);
  otherwise every `parent_labels` region of the
  run has the one selection with `conversion = "parent_labels_as_area"`, which is recorded in
  `mask_conversions` and shown (`'<ID>': parent_labels used as an area; grouping not kept`) for every
  consumer, a group-aware one included. So one `(mask_id, "region")` has exactly one interpretation
  in a run, never one per consumer, and a group-aware consumer in a mixed run reads an area that is
  recorded and shown, never silently. Under `conversion = None` (all consumers group-aware), a
  group-aware consumer reads the raw plane (`read_mask` or `read_mask_window`), calls `check_region`
  on it for its shape and dtype checks and its area, and keeps the **raw integer values** as its
  groups; `check_region`'s boolean never replaces them. Under `parent_labels_as_area` every consumer
  uses only `check_region`'s boolean. A per-use capability (one consumer reads groups and another an
  area in one run) is not decided here.
- **Reads.** The `objects` use reads `RunInputs.read_objects` (whole plane only). A `region` or
  `fraction` use reads `RunInputs.read_mask` on the whole-plane route or `read_mask_window` on the
  lazy route, then `check_region`. On the whole-plane route a name used both as objects and as a
  fraction gives the same fraction either way: labelling keeps the foreground, so `labels != 0` equals
  `raw != 0` pixel for pixel.
- **The lazy window check** keys on the `objects` use only: it refuses a windowed unit that would read
  an `objects` use whose selection has `conversion = "connected_components"`, and nothing else
  (`MASK_WINDOW_CONVERTED`, [table](#refusal-codes-and-messages)). The checks at
  `window_reads.py:327-333` and `fov_files.py:412-416`, which key on every converted name, are
  removed; the one preflight replaces both.

## The helper `RunInputs.read_objects` (BM2, BM5, BM6)

`read_objects(selection, mask_id, t, z) -> numpy.ndarray` (int32, the plane's shape) reads the
selection's `(mask_id, "objects")` mask selection:

- `representation = "instances"`, no conversion: the stored labels, checked by `check_labels`, never
  relabelled (D47: an `instances` mask holding 0 and 1 is one object).
- `conversion = "connected_components"`: the plane is labelled by `label_binary` (below), which first
  calls `mask_rules.check_binary_values` on it: the stored plane must be boolean, or signed or
  unsigned integers in {0, v} for one v > 0 (BM11), never floats; otherwise
  `R_MASK_CONTRADICTS_REPRESENTATION`. This per-plane check is the **read guard**, a defensive repeat
  of the mask step's file-wide check (I14); it cannot see values in other planes, which is why the
  mask step's check, not this one, decides whether a file is accepted. A plane with no foreground gives zero objects,
  an all-foreground plane one object; neither is an error.
- It reads whole planes only; it has no window argument. A mask ID with no `objects` selection
  (a mask used only as a region), or a `parent_labels` mask, passed to it is a programming error
  (`ValueError`).

**The pure labelling function** has one stable public name,
`morphobricks_preprocessing.masks.binary.label_binary(mask) -> numpy.ndarray`, re-exported as
`morphobricks_preprocessing.label_binary`. The same module holds `CONNECTIVITY = 8` and the 3 × 3
structure of ones (`STRUCTURE`) that the mask step's piece counter imports (`PIECE_STRUCTURE` is no
longer restated). Its contract:

- **Signature:** `label_binary(mask, *, name="the mask")`; `name` fills `{path}` in its refusal.
- **Input:** a 2-D `numpy.ndarray`. `label_binary` **calls `check_binary_values` itself** (dtype and
  values) before labelling, so a direct call is as safe as a call through `read_objects`: a float
  array (also when integer-valued), a negative value or two distinct positive values is
  `R_MASK_CONTRADICTS_REPRESENTATION` from the one constructor; a non-array or an array that is not
  2-D is `ValueError`. It never casts, thresholds or squeezes. Tests call it directly with `{0, 3, 7}`,
  `{0, -1}`, `float32` 0/1, a `(1, 8, 8)` stack and a list, and expect those refusals.
- **Output:** a new `int32` array of the input's shape; 0 where `mask == 0`; the components of
  `mask != 0` under 8-connectivity (`scipy.ndimage.label` with `STRUCTURE`) numbered **1 to n with no
  gap**, in row-major order of each component's first pixel. The input is not changed.
- **Label range and overflow:** n is at most `LARGEST_LABEL` (2,147,483,647, the int32 maximum of
  `masks/labels.py`). The count is taken before the int32 output is filled; a plane with more
  components is refused with `ValueError` naming the count and the limit, never wrapped, widened or
  truncated. (A 2-D plane reaches that count only above about 8.6 × 10⁹ pixels, but the rule is
  stated so that no implementation casts silently.)

No brick calls `label_binary` on a file run; `read_objects`, the mask step's piece counter, the
`binary_to_instances` helper (BM12) and the tests do.

## Resolver version check (BM10)

Every consumer that calls `resolve_request` (CellPatcher, MorphoRelate, fiberfeatures, MorphoFeature)
holds a constant `SUPPORTED_RESOLVER_VERSIONS = frozenset({3})` and checks
`resolved.provenance.resolver_version` against it **immediately after `resolve_request` returns and
before any pixel read, any output or record written, and any cache lookup or reuse**. A version
outside the set (2, or a future 4) is refused with `RESOLVER_VERSION_UNSUPPORTED`
([table](#refusal-codes-and-messages)); it is never read as "at least 3". A cached result is reused
only when the resolver version recorded with it is in the set as well. The check reads the
`Provenance` field that version 2 already has, so it also refuses an older preprocessing that does not
know this ADR. The error is built by **one constructor in normalization**,
`morphobricks_normalization.contracts.refuse_resolver_version(found, supported) ->
ResolverVersionError` (a `ValueError` with `code`): normalization is the lowest brick, every consumer
can import it whatever preprocessing is installed, and it imports nothing of preprocessing. Each
consumer declares and pins normalization, calls the constructor and raises the result; it may raise
its own exception type instead, with the code and message copied verbatim, never changed. Widening
the set is a later ADR's change, with its own tests.

## Region checker contract (BM3, BM7)

`morphobricks_normalization.regions.check_region(mask, shape, *, name) -> numpy.ndarray[bool]`:

| Input | Result |
| --- | --- |
| a plain `numpy.ndarray`, 2-D, of `shape` `(Y, X)`, dtype boolean or any integer | `mask != 0` (a new boolean array; the input is not changed) |
| not a `numpy.ndarray` (a list, None, a tensor) | `MASK_REGION_INVALID`, reason `not_an_array` |
| a `numpy.ma.MaskedArray` | `MASK_REGION_INVALID`, reason `masked_array` |
| not 2-D (a `(1, Y, X)` stack included: never squeezed) | `MASK_REGION_INVALID`, reason `not_2d` |
| 2-D of another shape | `MASK_REGION_INVALID`, reason `shape` (never resized or cropped) |
| float, complex, object or any other dtype | `MASK_REGION_INVALID`, reason `dtype` (a probability map is thresholded by the user first) |

Rules: the checker never labels, casts, thresholds or resizes. Any representation is accepted as a
region (`instances`, `binary`, `parent_labels`; a `parent_labels` region without the capability keeps
its recorded marker, PL1). Negative integers are inside the region (`!= 0`); `> 0` is not used for
regions. An **empty** foreground is returned, not refused: what is undefined is decided by the
measurement (BM8). Every brick that takes a region, in memory or from a run, calls it: CellPatcher's
fraction masks, random sampling and windowed masks; MorphoFeature's `FovInput` and sampling masks;
MorphoObjects' and MorphoRelate's `restrict_to`; MorphoRelate's region columns; fiberfeatures' analysis
mask and patch regions; MorphoEmbed's patch masks; normalization's `region_white` and
`region_vectors` (which replace their private `_check_region`, `optical_density.py:286-299`).

## Region estimates in normalization (BM3, BM8)

Today `region_white` returns `tuple[float, float, float]` and raises on an empty region
(`optical_density.py:297-298`, `:302-322`), and `region_vectors` (`:325-364`), which uses the same
private check, would take the mean of no pixels (a non-finite intermediate) if the raise were simply
removed. Both get one small result type, defined in `morphobricks_normalization.regions` beside
`check_region`:

```python
@dataclass(frozen=True)
class RegionEstimate:
    value: tuple[float, ...] | None   # the estimate; None when undefined
    reason: str | None                # None when defined; else a reason of the vocabulary below
```

- **Invariant** (checked in `__post_init__`, `ValueError` otherwise): exactly one of `value` and
  `reason` is set; `value` is a tuple of finite Python `float`s (three for a white or a stain vector);
  `reason` is one of `REGION_REASONS = ("empty_region",)`. NaN never appears in a `RegionEstimate`.
- **`region_white(rgb, region) -> RegionEstimate`**: `check_region` first (its refusals stand); an
  empty region gives `RegionEstimate(None, "empty_region")`, with no raise and no NumPy warning (the
  median is not taken); a non-empty region gives `RegionEstimate(value, None)` with `value` **bitwise
  equal** to today's tuple. The dark or saturated median (0 or 255) is still refused with today's
  `ValueError`: it is a non-empty region whose white is unknowable, not an empty one.
- **`region_vectors(rgb, white, regions) -> Mapping[str, RegionEstimate]`** (read-only, the input
  mapping's order): each region is checked by `check_region`; an empty one gives
  `RegionEstimate(None, "empty_region")` **before** any optical density is averaged over it; a
  non-empty one gives today's unit vector, bitwise equal, and keeps today's refusals (a pixel with a
  channel at 0, a mean optical density below `MIN_REGION_OD`). An empty or non-mapping `regions`
  argument stays a `TypeError`.

**Callers never fit or convert with an undefined estimate.** Per caller:

| Caller | With `RegionEstimate(None, "empty_region")` |
| --- | --- |
| `stain.white_from_region` (returns the white that `to_scalar(white=...)` converts with; `stain.py:450-476`) | **refuses the conversion**: `ValueError("The background region is empty (empty_region): no white can be estimated from it, so nothing is converted. Choose a region with at least one pixel, or declare the white explicitly.")`. Its return type stays `tuple[float, float, float]`, the estimate's `value` |
| `stain.stain_vectors_from_regions` (returns the vectors `to_scalar(stain_vectors=...)` converts with; `stain.py:479-512`) | **refuses the conversion**, naming every empty region in mapping order: `ValueError("The regions {names} are empty (empty_region): no stain vector can be estimated from them, so nothing is converted. Label at least one pixel of each stain.")`. Its return type stays `Mapping[str, tuple[float, float, float]]` |
| a brick that estimates per plane inside a run (none at the inventory commits; the rule binds the first one) | **records the dependent features undefined** with `empty_region` (BM8) and the plane still runs; the undefined estimate is never passed to a fit, a conversion or a pooled estimate, and a pooled fit that would need it refuses naming the planes, never drops them silently |

The wrappers refuse rather than return `None` because `to_scalar` reads an absent white as "not
given" for the `luminance` preset: a `None` passed on would change the conversion silently.

## Undefined-reason vocabulary (BM8)

| Reason | When | Value | Recorded as |
| --- | --- | --- | --- |
| `empty_region` | the region (`mask != 0`) holds no pixel of the area being measured: the plane, a patch, a window or an object | NaN (null in JSON) in a brick's table; in normalization `RegionEstimate.value = None`, never NaN | the brick's existing undefined record: MorphoFeature/#63 applicability state `undefined`, detail `empty_region`; MorphoObjects `nan_reason`; MorphoRelate and fiberfeatures their reason column; normalization's `RegionEstimate.reason` |

It is the only reason this ADR adds; it replaces `sampling_mask_empty` (MorphoFeature) and the
refusals of fiberfeatures and normalization on an empty region. The rule for which values are
undefined:

- a value computed **over the region's pixels** (a mean, median, texture, white point, a sampled patch
  set) is undefined with `empty_region`;
- a value whose denominator is another **non-empty** area is defined: the fraction of a patch inside
  the region is `0.0`, a count of region pixels is `0`.

"The plane still runs": an empty region never refuses the plane, the request or the run. A patch set
sampled inside an empty region has no patch on that plane, and the plane is listed with
`empty_region` in the run's plane ledger; the plane's other requests run.

## Refusal codes and messages

Each code has exactly **one constructor**: the one function that builds its code and message. The
constructor returns the error object; it does not decide whether to raise, so a resolver can collect
it as a `Refusal` and a checker can raise it. "Raised at" lists where it reaches the caller.

| Code | Constructor (the only one) | Raised at | When | Message (exact; `{…}` filled in) |
| --- | --- | --- | --- | --- |
| `A_MASK_NOT_INSTANCES` | `morphobricks_preprocessing.mask_rules.refuse_not_instances(subject, *, declared=None, value=None) -> MaskNotInstancesError` (a `ValueError` and a `RunInputsError` with `code`); exactly one of `declared` (the declared representation) and `value` (the in-memory object) is given | (a) `resolve_request`, which turns it into `Refusal(error.code, mask_id, str(error))`; `mask_representation_refusal` keeps only the decision and calls the constructor; (b) `morphobricks_preprocessing.masks.check_object_set(value, *, name)`, which raises it | (a) a `binary` mask as objects without `binary_mask_policy`, a `parent_labels` mask as objects; (b) an in-memory object set that is not a plain `numpy.ndarray` (`type(value) is numpy.ndarray`) of a signed or unsigned integer dtype | (a) `declared = "binary"` or `"parent_labels"`: today's two resolver messages, unchanged (preprocessing `run_inputs_request.py:453-478`). (b) for a plain `numpy.ndarray`: `A_MASK_NOT_INSTANCES: {name!r} is a {dtype} array, not an object set. An object set is an integer instance array (0 is background, each positive value one object). A boolean array is used only as a region. To measure the connected pieces of a binary mask as objects, describe it as binary and request binary_mask_policy='connected_components' in a run.`; for anything else (a list, None, a tensor, a `numpy.ma.MaskedArray`): `A_MASK_NOT_INSTANCES: {name!r} is a {type_name} (not a plain NumPy array), not an object set.` followed by the same three sentences, with `{type_name}` = `type(value).__name__` |
| `A_VOLUME_NOT_SUPPORTED` | `morphobricks_preprocessing.run_inputs_request.volume_refusals(request, z_counts) -> tuple[Refusal, ...]`, today's `volume_refusal` extended: the one place that builds the code, for a volume request (today's message, unchanged) and for a conversion | `resolve_request` | a mask request with `binary_mask_policy` on a position with `z_count > 1`, as a `plane` or a `volume` request, with or without `volume_support` | `{mask_id!r} would be converted by connected_components, which labels 2-D planes only; the images of {position} have {z_count} Z planes. Converting a Z-stack is not supported (A_VOLUME_NOT_SUPPORTED).` |
| `R_MASK_CONTRADICTS_REPRESENTATION` | `morphobricks_preprocessing.mask_rules.refuse_binary_values(path, *, values=None, dtype=None) -> MaskContradictsRepresentationError` (a `ValueError` with `code`; exactly one of `values`, `dtype` given), called only by the shared validator `mask_rules.check_binary_values(values, *, dtype, path)`, which takes the stored dtype and the distinct values of a plane or of a whole file and checks the dtype first (signed or unsigned integer, or bool; never float, complex or object, also when every value is whole) and then the values | (a) the mask step (`mask_representation.check_representation`), **file-wide**: it unions the distinct values of every plane of a new file and calls `check_binary_values` on the union (it may stop reading once the union already holds two positive values or a negative one), so a file whose planes hold {0, 3} and {0, 7} is refused with `[3, 7]`; it records the error as its `ValidationIssue` with the error's code and message verbatim and no action text added, and never records the file as `checked`; (b) `label_binary`, which calls `check_binary_values` on its plane: the per-plane read guard of `RunInputs.read_objects`, and any direct call | a file (mask step) or plane (`label_binary`) of a mask declared `binary` has a non-integer, non-bool dtype, or holds a negative value or two or more distinct positive values (BM11) | values: `R_MASK_CONTRADICTS_REPRESENTATION: {path} is declared binary but holds the values {values}; a binary mask holds 0 and at most one positive value (an all-zero or all-foreground file is accepted). Declare it instances or parent_labels, or fix the file.` with `{values}` the distinct non-zero values found when the check stopped, ascending, as a Python list of at most 10 items (`, ...]` after the tenth). dtype: `R_MASK_CONTRADICTS_REPRESENTATION: {path} is declared binary but has pixel type {dtype}; a binary mask is stored as integers or booleans, never as floats, even when its values are whole numbers. Save it as integers or booleans.` Both replace today's mask-step message "holds {n} different values. A binary mask has at most two" (`description_run_text.py:152-165`) |
| `MASK_WINDOW_CONVERTED` | MorphoFeature `window_reads.check_window_objects(plan, uses) -> None`, the single preflight, which raises `RequestError(message, "MASK_WINDOW_CONVERTED")` | MorphoFeature, once, when the run is planned, before any pixel or header of a plane is read | a request on the lazy windowed route reads, as objects, a `(mask_id, "objects")` use whose selection has `conversion = "connected_components"` (region and fraction uses are never refused) | one line per offending `(request, object set)`, in run order, joined by newlines, in one error: `MASK_WINDOW_CONVERTED: the request {request!r} runs by window and reads the object set {object_set!r}, the binary mask {mask_id!r} converted by connected_components, which needs the whole plane, so it has no window. Run this request on the whole-plane route; region and fraction reads of {mask_id!r} are read by window.` |
| `MASK_REGION_INVALID` | `morphobricks_normalization.regions.check_region` (exception `RegionMaskError`, a `ValueError` with `code` and `reason`) | wherever a region is taken (BM7's list) | the five reasons of the [contract](#region-checker-contract-bm3-bm7) | `MASK_REGION_INVALID ({reason}): the region {name!r} {detail}. A region is a 2-D integer or boolean array of the plane's shape (Y, X); its non-zero pixels are inside.` with `{detail}` one of: `is not a NumPy array (got {type})`, `is a masked array`, `has {ndim} dimensions`, `has shape {shape}, not the plane's {plane}`, `has pixel type {dtype}` |
| `RESOLVER_VERSION_UNSUPPORTED` | `morphobricks_normalization.contracts.refuse_resolver_version(found, supported) -> ResolverVersionError` (a `ValueError` with `code`); the only one | each resolver consumer (CellPatcher, MorphoRelate, fiberfeatures, MorphoFeature), right after `resolve_request` ([resolver version](#resolver-version-check-bm10)): it calls the constructor and raises the result, or its own type with code and message verbatim | `provenance.resolver_version` not in the consumer's `SUPPORTED_RESOLVER_VERSIONS` (`{3}`) | `RESOLVER_VERSION_UNSUPPORTED: the installed morphobricks-preprocessing resolver has contract version {found}; this consumer supports exactly {supported}. Install the morphobricks-preprocessing release it pins; nothing was read or written.` with `{supported}` the sorted list, `[3]` |

`A_MASK_NOT_INSTANCES`, `A_VOLUME_NOT_SUPPORTED` and `R_MASK_CONTRADICTS_REPRESENTATION` are existing
codes (experiment-v1 §8; ADR 0002); no `A_*` or `R_*` code is added. `MASK_WINDOW_CONVERTED` is
MorphoFeature's existing code. `MASK_REGION_INVALID` and `RESOLVER_VERSION_UNSUPPORTED` are new
runtime codes outside experiment-v1 §8, like `MASK_WINDOW_CONVERTED`. A malformed request (a policy on
a non-`binary` mask or in the role `region`, two conversions of one mask's objects use) stays a
`ValueError` raised by the resolver only (I12); bricks do not check it first.

### Construction and propagation

- **Construction** is the constructor's alone. No other code formats one of these messages, adds the
  code to a message of its own, or checks the same condition first with its own text (I11, I12). The
  mask step and `read_objects` share `check_binary_values`; the resolver and `check_object_set` share
  `refuse_not_instances`; nothing else builds those two codes.
- **Propagation** is unchanged re-raising. A brick that catches one of these errors either re-raises
  the same object (`raise`), or, where its public API raises its own type (MorphoFeature's
  `RequestError`), raises that type with **`code` equal to the original code and `str()` equal to the
  original message**, chained with `from`. It adds no prefix, suffix, plane name or advice; context it
  wants to keep goes in a separate attribute or its log.
- **MorphoFeature's resolver wrapping stops.** At `mask_selection.py:284-309` today a resolver
  exception becomes `wrap(f"the run file's masks cannot be resolved: {error}", error)`, and a refused
  request becomes `"the preprocessing run refuses the run file's masks; nothing was read:\n" + text`,
  plus a sentence naming the declared mask IDs. All three additions are removed: the exception's
  message is passed on as is, and a refused request raises `RequestError` whose message is exactly
  `"\n".join(r.message for r in refusals)` (the text `ResolvedRequest.require()` builds) with code
  `refusals[0].code`. Only the existing progress summary for images still to segment
  (`A_SCOPE_INCOMPLETE` of a declared mask, `refuse_missing`) stays: it is not a code of this ADR.
  The plane prefix that `fov_files.py:311-314` adds to a labelling error goes with that call site.
- **Tests, in every PR that constructs or propagates a code:** (1) the error reaching the brick's
  public boundary has the exact code and a message equal to the constructor's output for the same
  arguments (compared as strings, not by substring); (2) for `A_MASK_NOT_INSTANCES`,
  `A_VOLUME_NOT_SUPPORTED`, `MASK_WINDOW_CONVERTED` and `RESOLVER_VERSION_UNSUPPORTED`, a spy
  `RunInputs` counts `read_plane`, `read_mask`, `read_mask_window` and `read_objects` calls and the
  count is **0** when the refusal is raised, no output file exists and no cache entry was read; (3) for
  `R_MASK_CONTRADICTS_REPRESENTATION`, the mask step refuses the file before any run, and a run that
  names it is `A_MASK_UNCHECKED` without reading it; (4) the constructor is the only place the
  message text occurs in the repository (a source scan for its first fixed words).

## The conversion helpers (BM12)

Two methods of `RunInputs`, implemented in `morphobricks_preprocessing.mask_conversion`, with a CLI
command and a notebook card that call them. They take a **typed context, not paths**: the opened run
and the source's FOV and mask ID, so the run's recorded representation, mask-step status and
fingerprint decide what may be read. They write **new** mask files and never change the source. The
user then declares each output mask ID in the description (its source type is the output mask ID,
its representation the one named below) and runs the mask step on it like any mask; nothing reads an
output before that.

```python
RunInputs.binary_to_instances(fov, mask_id, *, output_mask_id) -> MaskConversionResult
RunInputs.classes_to_binary(fov, mask_id, *, output_prefix) -> MaskConversionResult
```

**Inputs.** Both refuse, before reading a pixel and writing anything, a `mask_id` that the published
description does not declare (`ValueError` naming the declared IDs), a source file of that mask for
`fov` whose mask-step status is `not yet checked`, or whose fingerprint differs from the one recorded
when it was checked (`A_MASK_UNCHECKED`, the resolver's refusal for that file), and a source that
changes while it is read (the existing `MaskChangedError`). A source mask stored as a label image
**inside an OME-Zarr** (a mask file whose source is not the masks folder) is refused before any
read with `ValueError` (`{mask_id!r} for {fov} is a label image inside an OME-Zarr; the conversion
helpers convert masks in the masks folder only`): no destination inside the user's Zarr is
inferred. Every other source lives in the run's standalone masks folder (`RunInputs.masks_root`,
which preprocessing keeps outside the experiment folder); a run without one has nothing these
helpers can convert. Then, never casting, thresholding, squeezing or selecting:

| Helper | Accepts | Refuses (`ValueError` naming the mask ID and file, unless a code is named) |
| --- | --- | --- |
| `binary_to_instances` | a mask declared `binary`, so its file passed `check_binary_values` file-wide; one Z plane; any number of time points, each labelled on its own | a mask declared `instances` or `parent_labels` (its representation named); a file with more than one Z plane (2-D labelling only, BM5); a plane `label_binary` refuses (`R_MASK_CONTRADICTS_REPRESENTATION`, its message verbatim) |
| `classes_to_binary` | a mask declared `parent_labels` or `instances` (pixels prove neither, so a class image passes the mask step under both; `parent_labels`, each value one group in any number of pieces, is the closer description) whose file is one 2-D plane `(Y, X)` of a signed or unsigned integer dtype holding class values from 0 to `LARGEST_LABEL` (2,147,483,647), class `0` the background. The helper reads the raw plane without `check_labels` and applies this table's checks itself, so its messages are the ones below | a mask declared `binary` (it has one class already: declare or use it as it is); a negative value (`holds negative values (smallest {v}); class 0 is the background and classes are positive`); a value above `LARGEST_LABEL` (`holds class values above 2147483647 (largest {v}); a class value must fit an int32 label`); a float, complex or other non-integer dtype, and **bool** (`has pixel type {dtype}; a class image holds non-negative integer class values`); anything not 2-D, a Z, T or C stack and a **one-hot** image (a class axis of 0/1 planes) included (`has {ndim} dimensions (shape {shape}); a class image is one 2-D plane of class values; a one-hot or multi-channel stack is not converted`) |

**Outputs and their mask IDs.** `binary_to_instances` writes exactly one `int32` instance mask under
the mask ID `output_mask_id`: per plane, `label_binary` of the source plane (BM1/BM6: 8-connected,
numbered 1..n), so it equals `RunInputs.read_objects` on the source plane for plane; it is declared
`instances`. `classes_to_binary` writes **one `uint8` binary mask per class value present in the
image**, in ascending class order, under the mask ID `<output_prefix>_class<value>` (for example
`Tissue_class1`, `Tissue_class2`), with `1` where `image == value` and `0` elsewhere: never a
threshold, never a subset of the classes, never a merge. Class 0 gives no output; an all-zero image
gives no output and the result says "no class present". Each output is declared `binary`. Output mask
IDs follow the Label rules of experiment-v1 §3.2 (refused otherwise). An output file's path is
derived from the **FOV's resolved image identity, never from the source file's name**: it is
`<output mask ID>/<the FOV image's path relative to the experiment folder, its extension replaced by
.tif>` in the **same masks folder as its source** (`RunInputs.masks_root`), the type-folder layout
that mask discovery pairs with that image (`masks/files.py`). So a source stored in a type folder
(`TumorRegion/CTRL/rep1/a.tif`) and one stored with a type suffix (`CTRL/rep1/a_TumorRegion.tif`)
give the same output path for image `CTRL/rep1/a.<ext>`: `TumorObjects/CTRL/rep1/a.tif`. An output
is never written in the experiment folder or anywhere else.

**Collisions are refused, never overwritten.** Before anything is written the helper refuses
(`ValueError` naming the ID or file) an output mask ID that the published description declares, a
discovered mask type of that name holding any file without a lineage line of the same operation, and
an output file that already exists, unless it is the **same** conversion already published: its
lineage line's `source` object equals the current source's **in every key** (`root`, `mask_id`,
`path`, `axes`, `shape`, `dtype`, `content_sha256`), its `output` `root`, `mask_id` and `path` equal
the requested output's, its `operation`, `connectivity`, `class_value`, `helper` and `helper_version`
equal this call's, and the existing file's digest equals the line's `output.content_sha256`. That
call is a no-op that returns the existing result (idempotent retry). Any difference, **a different
source with identical pixels included** (another mask ID or path whose digest is the same), is a
collision and is refused: equal pixels never stand in for the same source.

**Lineage record**, one per output, one line of `mask_lineage.jsonl` in the output's mask-type folder
(mask discovery MUST ignore that file and the helper's temporary files; PR 2b tests it). Keys exactly
these, in this order, all always present:

| Key | Value |
| --- | --- |
| `source` | `{"root": "masks", "mask_id": ..., "path": ..., "axes": ..., "shape": [...], "dtype": ..., "content_sha256": ...}` of the file read |
| `output` | the same keys for the file written |
| `operation` | `"binary_to_instances"` or `"classes_to_binary"` |
| `connectivity` | `8` for `binary_to_instances`; `null` for `classes_to_binary` |
| `class_value` | the class (an integer) for `classes_to_binary`; `null` for `binary_to_instances` |
| `helper` | `morphobricks_preprocessing.RunInputs.binary_to_instances` or `morphobricks_preprocessing.RunInputs.classes_to_binary` |
| `helper_version` | `morphobricks_preprocessing.__version__` at the time of writing |

`root` names the folder `path` is relative to; in this wave it is always `"masks"`, the run's
standalone masks folder (`RunInputs.masks_root`), for the source and the output alike (OME-Zarr label
images are refused above). A reader refuses a line with any other `root` value (BM15 adds one exception, the `source` of a [derived region mask](#derived-region-masks-bm15)). `path` is relative to
that root, with `/`, and never absolute, so the record holds when the masks folder is on another
volume than the experiment folder or is moved. `axes` is the stored axis letters of the file
as the run recorded them (for example `"YX"`, `"TYX"`), `shape` the stored shape in that order,
`dtype` the NumPy dtype string in little-endian form (`"|u1"`, `"<u2"`, `"<i4"`, `"|b1"`).
**`content_sha256` is the lower-case hex SHA-256 of a canonical header followed by the pixel bytes**:
the header is the UTF-8 bytes of `json.dumps({"axes": axes, "dtype": dtype, "shape": shape},
sort_keys=True, separators=(",", ":"))` followed by one byte `0x0A`; the pixel bytes are every plane of
the file as the reader returns it, in the stored axis order, C order, in that little-endian dtype. Two
files with the same pixel bytes but another shape, axes or dtype therefore have different digests.
The helper computes it when it reads the source and when it writes the output (from the array
written, then checked against a re-read of the written file; a mismatch aborts the publication). It is
never preprocessing's `Fingerprint` (size and modification time, `fingerprint.py:6-16`) and never the
file's bytes (headers and compression differ between writers).

```json
{"source": {"root": "masks", "mask_id": "TumorRegion", "path": "TumorRegion/CTRL/rep1/a.tif", "axes": "YX", "shape": [8, 8], "dtype": "|u1", "content_sha256": "<64 hex>"}, "output": {"root": "masks", "mask_id": "TumorObjects", "path": "TumorObjects/CTRL/rep1/a.tif", "axes": "YX", "shape": [8, 8], "dtype": "<i4", "content_sha256": "<64 hex>"}, "operation": "binary_to_instances", "connectivity": 8, "class_value": null, "helper": "morphobricks_preprocessing.RunInputs.binary_to_instances", "helper_version": "<version>"}
```

**Publication is consistent for readers, per output: the output file and its lineage line are published as a pair.** It is not one atomic filesystem transaction (two renames are two operations); the guarantee is what a reader that follows the rules below can observe.
For each output, in this order: (1) the pixels are written to a temporary file in the target folder
and synced, and its digest is checked by re-reading; (2) `mask_lineage.jsonl` is rewritten to a
temporary file holding its previous lines plus the new one, synced, and renamed over the old file;
(3) the temporary output is renamed to its final name. A failure in (1) or (2) removes the temporary
files and leaves `mask_lineage.jsonl` as it was: no output, no line. A failure in (3) removes the line
again (step 2 with the previous lines) and the temporary file. So a visible output always has its
line (no lineage-less output) and no output is left without one (no orphan output). If the process
dies between (2) and (3), the line names an output that does not exist; readers treat such a line as
pending and ignore it, and the next call for the same conversion completes or rolls it back before
anything else, so a retry gives the same files and lines as one uninterrupted call. A multi-output
`classes_to_binary` publishes output by output in ascending class order; a retry after a failure
skips the classes already published (idempotent, as above) and continues.

## Derived region masks (BM15)

**The FOV is the run's, resolved before any read.** A BM15 helper takes the opened run
(`RunInputs`) and one FOV, given as a `Fov` or as its image path. Before any pixel is read it
resolves that FOV **by its image path, relative to the experiment folder,** to the run's own
authoritative description of it: the position as the run's manifest and published description
record it (`RunInputs.fovs()`), with its unit's declared `image_type`, its stored axes, its Z, T and
C counts and its pixel type. Every check and every lineage value uses that record only. An
`image_type`, axes, counts or pixel type carried by a caller-supplied `Fov` object are ignored:
never trusted, never compared, never used to fill a gap. An image path that is not an image of the
run is refused. On the resolved record the helper refuses, before any pixel is read, a unit not
declared `rgb`, a FOV with more than one Z plane or time point, a C count other than 3, a pixel type
other than 8-bit (`uint8`), a run without a masks folder and an unknown rule. RH1 is honoured as
recorded, **per image**: a unit declared `rgb` whose override the run accepted is valid input; the
helper never reads the image header itself and never decides the override again. The unit's
declared `rgb_header_override` and, when it is declared, that image's own recorded override item
(`override` `used` or `unused`, `unused_reason`, `header_photometric`; experiment-v1 §4.4b, "Declared
and effective are recorded separately") are copied into the lineage unchanged. The plane is read
through the run (`RunInputs.read_plane`), which refuses an image changed since the run, and the
image fingerprint is checked again after the read, as BM12 does.

**Output and publication.** The output is one `uint8` `(Y, X)` file, `1` where the rule keeps the
pixel and `0` where it excludes it, declared by the user `binary` and used as a region (BM3). Its
path, its mask ID rules, its collision refusals and its paired publication (with the pending-line
rollback) are those of BM12. Its retry comparator is **its own** (below), not BM12's.

**Lineage line.** One per output, in the same `mask_lineage.jsonl` as BM12's lines. Keys exactly
these, in this order, all always present:

| Key | Value |
| --- | --- |
| `source` | `{"root": "experiment", "image": ..., "axes": ..., "shape": [...], "dtype": ..., "content_sha256": ...}`: `image` is the FOV image's path relative to the experiment folder, with `/`; `axes`, `shape` and `dtype` are those of the plane as read (`"CYX"`, `[3, Y, X]`, `"\|u1"`); the digest is BM12's canonical digest of the pixels read |
| `output` | BM12's file object of the file written, with `root` `"masks"` |
| `operation` | the rule's operation name (`"he_tissue_mask"` for `he_tissue_v1`) |
| `rule` | the rule's complete canonical record (below) |
| `rule_sha256` | the lower-case hex SHA-256 of the canonical JSON of `rule` |
| `code` | `{"preprocessing": <code identity>, "normalization": <code identity>}` (below) |
| `reusable` | `true` when both code identities are verified, else `false` |
| `numpy_version`, `scikit_image_version`, `scipy_version` | each package's `__version__` as imported by the process that computed the mask |
| `image_type` | `"rgb"`, from the run's record of the FOV |
| `rgb_header_override` | `{"declared": <true or false>, "image": <that image's recorded override item, or null when not declared>}`, from the run's record |
| `pixel_size` | the run's recorded X and Y size and unit of the FOV, or `null`; information only, never used |
| `fractions` | results: the kept share and each excluded component's share of all pixels, and normalization's optical-density `floored_fraction` |
| `helper`, `helper_version` | the helper's qualified name; `morphobricks_preprocessing.__version__` |

**The rule record.** A rule is identified by `rule.id` and `rule.version`; thresholds are never
chosen per image, and a change of **any** value in the record is a new version. The record is
complete: it states the input it takes (image type, pixel type, white), the stain preset and its
version, the HED matrix's source (the qualified name of the matrix normalization's `stain` module
passes to the deconvolution) and the SHA-256 of that matrix as imported (float64, little-endian,
C order), the optical-density function and its floor, every excluded component in order with every
pixel comparison (quantity, operator, value), every clean-up operation in order with its parameters
(disk radii and minimum piece sizes, in pixels), the connectivity (`8`), the disk definition, how
the components combine, and the rule's `status` (`"provisional"` or `"frozen"`). Its canonical JSON
is the UTF-8 bytes of `json.dumps(rule, sort_keys=True, separators=(",", ":"))`, as for BM12's
canonical header; a reader refuses a line whose `rule_sha256` is not the SHA-256 of that
canonical JSON.

**Acceptance before freezing.** A rule's `status` becomes `"frozen"` only when a report meets
acceptance criteria that the owning brick's design states with numeric thresholds **before** any
evaluation of the rule is run. Thresholds are never set, moved or reinterpreted after results are
seen; changed criteria need a new evaluation.

**Code identity.** For each of the distributions `morphobricks-preprocessing` (the helper) and
`morphobricks-normalization` (the colour maths), the helper records an object with keys exactly
`distribution`, `version`, `verified`, `record_sha256`, `vcs_commit` and `reason`, in this order,
all always present. `version` is from the installed distribution's metadata. `record_sha256` is
the **installed-artifact digest**: the lower-case hex SHA-256 of the exact bytes of the installed
distribution's `RECORD` file (`<name>-<version>.dist-info/RECORD`, read as bytes, never parsed
or normalised first), or `null` when there is no readable `RECORD`. `vcs_commit` is the 40-hex
commit when the installation records one (PEP 610 `direct_url.json`, `vcs_info.commit_id`), else
`null`; it is extra provenance only and never stands in for `record_sha256`. The identity is
**verified** (`verified` `true`, `reason` `null`) only when all of these hold, checked once per
process after the helper has imported every module it uses from both distributions:

1. the distribution is not an editable install (PEP 610 `dir_info.editable` is not `true`);
2. its `RECORD` exists and is readable, and `record_sha256` is its digest;
3. every file `RECORD` lists with a hash still has that hash on disk;
4. every **executable package file** of the distribution is listed in `RECORD` **with a hash**:
   every `.py` file and every extension module (`.so`, `.pyd`) on disk under each of the
   distribution's import packages (the directories its `RECORD` places them in), files under
   `__pycache__` excepted; one that is missing from `RECORD`, or listed without a hash, refuses
   verified status;
5. every imported module of the distribution's import packages (each `sys.modules` entry named
   as the package or below it) has a `__file__` whose resolved real path is the resolved path of
   a `RECORD` entry with a hash: the code that runs is that installation's, not a source tree
   or another installation earlier on the import path.

Otherwise `verified` is `false`, `reason` names the first failed check (for example
`"editable install"`, `"RECORD missing"`, `"hash differs: <file>"`, `"not in RECORD: <file>"`,
`"no hash in RECORD: <file>"`, `"module not from this installation: <module>"`), and
`record_sha256` and `vcs_commit` are recorded as found. A version string or a commit alone is
never a code identity: two builds of one commit with different `RECORD` bytes are two
identities.

**An unverified mask is written but never reused.** When either code identity is unverified the
mask is still computed, written and published, with `reusable` `false`; the helper and its result
say so.

**Retry comparator (BM15's own).** An existing output is the **same computation**, and the call is
a no-op that returns the existing result, only when (1) the existing line and this call's line
both have `reusable` `true`; (2) they are equal in every key except `output.content_sha256` and
`fractions` (the results): `source` in every key, `output` `root`, `mask_id`, `path`, `axes`,
`shape` and `dtype`, `operation`, `rule`, `rule_sha256`, `code`, `numpy_version`,
`scikit_image_version`, `scipy_version`, `image_type`, `rgb_header_override`, `pixel_size`,
`helper` and `helper_version` (`code` in every key: an equal `vcs_commit` with another
`record_sha256` is another identity); and (3) the existing file's digest equals the line's
`output.content_sha256`. Anything else is a collision and is refused, never overwritten: a
different source with identical pixels, another code identity (another installed-artifact
digest included) or library version, another rule
record (a provisional and a frozen record included), and every line with `reusable` `false` on
either side. BM12's comparator never decides a BM15 line, and a BM15 line never matches a BM12
call (their operations differ).

**Reading.** A reader selects the schema by `operation`: BM12's two operations select BM12's
schema, a BM15 rule's operation selects this one; a line that matches neither is refused, as are
BM12-schema keys under a BM15 operation and the reverse. A `root` of `"experiment"` is valid only in
a BM15 `source`.

## Breaking changes and migration notes

Before the first pipeline release there is no backward compatibility (ADR 0002 AR10): removed keys are
refused as unknown, never mapped.

| Brick | Breaking change | Migration |
| --- | --- | --- |
| normalization | the region rules of `region_white`, `region_vectors` and their wrappers `white_from_region`, `stain_vectors_from_regions` become `check_region`'s, which changes several error types, not floats only: an **integer** region is accepted (was `TypeError`); a float, complex or object region is `MASK_REGION_INVALID` `dtype` (`ValueError`, was `TypeError`); a non-array is `not_an_array` and a masked array `masked_array` (`ValueError`, were `TypeError`); a 3-D region is `not_2d` (`ValueError`, was a `TypeError` or a shape `ValueError`); a wrong shape stays a `ValueError`, now `MASK_REGION_INVALID` `shape` with the fixed message. `region_white` and `region_vectors` return `RegionEstimate` (were a tuple and a mapping of tuples) and give `empty_region` instead of raising on an empty region; the two `stain` wrappers keep their return types and refuse an empty region with the fixed `empty_region` message. New: `contracts.refuse_resolver_version` | callers of `region_white`/`region_vectors` read `.value` (bitwise today's for a non-empty region) and handle `value is None` by the [per-caller rule](#region-estimates-in-normalization-bm3-bm8); code that caught `TypeError` for a bad region catches `ValueError` (`RegionMaskError`) |
| preprocessing | resolver contract version 3: `Provenance.mask_conversions`; a conversion on a Z-stack refused; a mask ID may repeat (one entry per use), and "a mask ID is requested twice" is replaced by the one two-conversions refusal of [uses of one mask](#uses-of-one-mask-in-one-run-bm2-bm5). New `RunInputs.read_objects`, `masks.binary.label_binary`, `mask_rules` (`refuse_not_instances`, `refuse_binary_values`, `check_binary_values`), `masks.check_object_set`, `RunInputs.binary_to_instances` and `RunInputs.classes_to_binary` (BM12). The mask step's binary rule becomes {0, v} over the whole file, integers or booleans only (BM11): a file with {3, 7}, or with planes {0, 3} and {0, 7}, or a float file, that passed before is refused; its message changes. `PIECE_STRUCTURE` is imported from `masks.binary`, not restated | consumers accept exactly `SUPPORTED_RESOLVER_VERSIONS = {3}` ([resolver version](#resolver-version-check-bm10)), never `>= 3`, and copy the record; a `binary` mask whose files hold two positive values is redeclared `instances` or `parent_labels`, or its files fixed (a float file saved as integers), and the mask step run again |
| CellPatcher | **removed:** `label_objects`, `BINARY_MASK_POLICIES`, `CONNECTIVITIES`, `BINARY_MASK_CONNECTIVITY`; `cell.binary_mask_connectivity`; the notebook checkbox "The mask is binary: label its connected components"; the in-memory use of `cell.binary_mask_policy`; `_RESOLVED`/`resolved_masks()`; `check_region_mask` (moves to normalization). A boolean cell mask in memory is `A_MASK_NOT_INSTANCES`. Float fraction, random and windowed masks are `MASK_REGION_INVALID`. A Z-stack conversion is refused. `run_config.json`: `mask_conversions` replaces `cell.binary_mask_connectivity` and `preprocessing.mask_conversions`. The notebook shows a file run's recorded conversion read-only (BM13) | in memory: pass integer instance labels, or run a described run with the policy; a config file with `binary_mask_connectivity` is refused (delete the key); `cell.binary_mask_policy` stays only as the file-run request field passed to the resolver; threshold probability maps before using them as fraction masks |
| MorphoObjects | the boolean object-set message becomes the shared `A_MASK_NOT_INSTANCES` one (from `check_object_set`); `restrict_to` uses normalization's `check_region`, so MorphoObjects **declares `morphobricks-normalization` in its own dependencies and pins it** (today it would reach it only through CellPatcher and preprocessing); every brick that imports `check_region` or `RegionEstimate` does the same | none for valid inputs |
| MorphoEmbed | the bool object-mask refusal becomes `A_MASK_NOT_INSTANCES` (was a dtype-kind message); `BINARY_MASK_POLICY = None` and its explicit argument removed; stale `ROADMAP.md:293-296` fixed; declares and pins normalization for `check_region` | none for valid inputs |
| MorphoRelate | **a `binary` structure without `binary_mask_policy` gives no `structures.csv` rows** (it is a region: its region columns and component-count features stay); rows need the recorded conversion and are then of kind `instance`. Its own `BINARY_MASK_POLICIES` copy, labelling call site and structure splitting of binary masks removed; `run_config.json` `masks[].conversion/labeller/connectivity` replaced by `mask_conversions`; `connectivity` 2 → 8; in memory a boolean object set is `A_MASK_NOT_INSTANCES`. Grouping inside `parent_labels` is unchanged (BM14) | add `:connected_components` to the structure's `--mask` (or `binary_mask_policy` in the config) to keep per-component rows; downstream readers of `structure_label_kind = component` for binary masks read `instance` |
| fiberfeatures | **a `region` mask is no longer handed to CellPatcher cell mode as cells** (I6): cell mode needs an `objects` mask; an empty analysis region gives undefined rows with `empty_region` instead of stopping; `> 0` becomes `!= 0`; the run record keys `binary_mask_policy`/`binary_mask_connectivity` become `mask_conversions`; `labeller_connectivity()` removed; notebooks' `BINARY_MASK_POLICY` parameter stays the request field | name an `objects` mask (with the policy for a binary one) for cell mode |
| MorphoFeature | `mask_conversions` replaces `masks[].conversion/labeller/connectivity` in the manifest (`connectivity` 2 → 8); manifest `masks` entries are one per `(mask_id, role)`; one `MaskRequest` sent per use and `mask_uses` aggregated by `(mask_id, use)` only after resolution; its own policy-conflict and region-policy refusals removed (the resolver's are raised); `FovInput` accepts boolean **regions** and refuses boolean object sets with the shared message; `sampling_mask_empty` becomes the non-refusing ledger reason `empty_region`; `MASK_WINDOW_CONVERTED` only for objects uses, from one preflight; resolver messages passed on verbatim (no "the run file's masks cannot be resolved" or "the preprocessing run refuses ..." text) | readers of the manifest read `mask_conversions` and the per-role entries; code matching the old message prefixes matches the code instead; cached results whose identity carries the old record or another resolver version are not reused (the record and the version are part of the source identity) |

## Implementation order

One PR per brick, in dependency order, each with its tests; each later PR pins the tag of the earlier
ones it imports. A PR does not start before the tags it needs exist. Every PR that constructs or
propagates a code of this ADR carries the [exact-message and pre-read tests](#construction-and-propagation).

| # | Repository | Change | Tests in the same PR |
| --- | --- | --- | --- |
| 0 | MorphoBricks-Spec | this ADR; `experiment-v1.md` §4.5, §4.5b, §8 (BM11); ADR 0001 D10 and evidence; ADR 0002 contract version 3; conformance plan P05 and "Mask rule" row | `refval.py` unchanged; tools tests |
| 1 | morphobricks-normalization | `regions.check_region`, `RegionMaskError`, `EMPTY_REGION`, `RegionEstimate`; `region_white` and `region_vectors` on them; the two `stain` wrappers refuse an undefined estimate; `contracts.refuse_resolver_version` and `ResolverVersionError` | the BM3/BM7 table case by case (F04, F05); F06's normalization part (both functions, both wrappers, bitwise values); the exact `RESOLVER_VERSION_UNSUPPORTED` message for found 2 and 4 |
| 2 | morphobricks-preprocessing | resolver contract v3 (`mask_conversions`, Z-stack refusal, `(mask_id, role)` requests); `RunInputs.read_objects`; `masks.binary.label_binary`; `mask_rules`; `check_object_set`; strict binary at the mask step (BM11); pins normalization | F01, F02 (resolver record), F07's messages (array and non-array branches), F08c's resolver part (repeated entries collapsed; the two-conversions refusal), F09, F10 (file-wide, the dtype rule), `label_binary` called directly with invalid input and its range and overflow rules; the resolver's import scan still passes |
| 2b | morphobricks-preprocessing | the conversion helpers (BM12): `RunInputs.binary_to_instances` and `RunInputs.classes_to_binary`, their output mask IDs, collision refusals, lineage records and their reader-consistent publication; CLI and notebook card | F11, F12 (full records, every rejected input, source changed since check, lineage write failure and retry, the digest rule); mask discovery ignores `mask_lineage.jsonl` and the temporary files |
| 3 | CellPatcher | the CellPatcher removals above; file runs read objects through `read_objects`; regions through `check_region`; record copied; the resolver-version check (normalization's constructor; declares and pins normalization); the notebook shows the recorded conversion read-only (BM13) | F01 (no connectivity key accepted), F05 on fraction/random/windowed masks, F07, the `run_config.json` record (F02), F13; **a notebook test (BM13)**: for a file run whose resolver record holds a conversion, the form shows the record's text read-only (no enabled widget) and offers no binary-mask control, and a run without a conversion shows none |
| 4 | MorphoObjects | shared refusal; `check_region`; declares and pins normalization | F07, F04, F06 (`empty_region` unchanged) |
| 5 | MorphoEmbed | shared refusal; constant removed; ROADMAP; declares and pins normalization | F07 |
| 6 | MorphoRelate | no binary structure splitting; `read_objects`; record copied; region checker; shared refusal; the resolver-version check (normalization's constructor; declares and pins normalization) | F03 (no rows without the policy; instance rows and the record with it), F02, F06, F07, F13; **a regression test (BM14)**: on a described `v38` run, the `parent_labels` mask `Mito` (groups 3 and 9, each in two pieces) under a `parent_labels_support` request gives the same `structures.csv` grouping rows (`structures_table.py:89-114`), values and kinds as at the inventory commit, with no conversion record |
| 7 | fiberfeatures | `read_objects`; record; no region as cells; empty region undefined; `!= 0`; the resolver-version check (normalization's constructor; declares and pins normalization) | F03 (region not cells), F02, F06, F13 |
| 8 | MorphoFeature | `read_objects`; record copied; uses keyed by `(mask_id, use)`; one `MASK_WINDOW_CONVERTED` preflight for objects uses; resolver messages verbatim; `FovInput` regions; `empty_region` in the ledger; the resolver-version check (normalization's constructor; declares and pins normalization) | F02, F06, F07, F08a, F08b, F08c, F08d, F13; `region_masks` and `region_parent_labels_support` taking fraction uses; the message-preservation test of `resolve_masks`; the cross-route "Mask rule" with each provider |

Steps 4-7 depend only on 1-3 and may run in parallel; MorphoFeature comes last because it orchestrates
the providers changed in 4-7. The cross-route "Mask rule" test (conformance plan §4) becomes a gate of
steps 6-8.

## Conformance fixtures

The Spec's fixture framework (`fixtures/`, `tools/audit/refval.py`) holds description TOML files,
transitions and records files and checks them without pixels; none of these rules can be expressed in
it (`v08` already covers the description side: `TumorRegion` is `binary`, `i112` forbids the policy in
the file). The fixtures below are therefore **to-do**: they are written as tests in the implementing
PRs, and a later Spec PR adds them as shared arrays under `fixtures/masks/` once the framework carries
pixel data. All arrays are 8 × 8 `uint8` unless stated; "described" means a `v08`-style run with
`TumorRegion` declared `binary`. "Before any read" means the spy `RunInputs` of
[construction and propagation](#construction-and-propagation) counts 0 reads.

| Fixture | Rule | Input | Expected outcome (exact) |
| --- | --- | --- | --- |
| F01 | BM1 connectivity 8 | described; `TumorRegion` = two 2 × 2 blobs touching at one corner (`[1:3,1:3]` and `[3:5,3:5]` = 1); objects with the policy | one object, label 1, on every route; record `connectivity: 8`; a CellPatcher config with `binary_mask_connectivity` is refused as an unknown key |
| F02 | BM2 one labeller, one record | described; two disconnected blobs (`[1:3,1:3]`, `[5:7,5:7]` = 1); objects (a) without, (b) with the policy | (a) `A_MASK_NOT_INSTANCES`, no selection; (b) labels 1 (top-left) and 2, equal on every route; the run record of every **run-record owner** (MorphoFeature's run manifest, the `run_config.json` of CellPatcher and MorphoRelate, fiberfeatures' run record) holds `mask_conversions` exactly `[{"mask_id": "TumorRegion", "conversion": "connected_components", "connectivity": 8, "labeller": "morphobricks_preprocessing.RunInputs.read_objects"}]`. MorphoObjects and MorphoEmbed are provider consumers with no run record: they receive labels through MorphoFeature and are not checked here |
| F03 | BM2 no other labeller | F02's mask (a) as a MorphoRelate `structure` without the policy; (b) as a fiberfeatures `region` with CellPatcher cell mode and no `objects` mask | (a) no `structures.csv` row for it, no record, its region columns and `component_count = 2` present; (b) refused before any read, naming the missing `objects` mask |
| F04 | BM3 region = `mask != 0` | the same pixel set as bool, `uint8` 0/255, and `int32` instances with labels 1 and 7 | `check_region` returns three equal boolean arrays; nothing is labelled; a region value measured on each is bit-identical |
| F05 | BM3/BM7 region checker | `float32` 0/1; shape `(1, 8, 8)`; shape `(8, 9)`; a masked array; a list | `MASK_REGION_INVALID` with reasons `dtype`, `not_2d`, `shape`, `masked_array`, `not_an_array`, and the exact messages |
| F06 | BM3/BM8 empty region | an all-zero region on one plane of a two-plane run; in normalization, an `(8, 8, 3)` `uint8` image with an all-zero region and a non-empty one | the mean intensity in the region is NaN with `undefined`/`empty_region`; the fraction of a patch inside it is `0.0`; a patch set sampled in it has no patch and the plane is listed with `empty_region`; the other plane and the plane's other requests give their values; no exception. Normalization: `region_white` on the empty region is `RegionEstimate(None, "empty_region")` with no warning (warnings as errors); `region_vectors` with both regions gives `RegionEstimate(None, "empty_region")` for the empty one and, for the other, a value bitwise equal to the inventory commit's; `region_white` on the non-empty region likewise bitwise equal; `white_from_region` and `stain_vectors_from_regions` refuse the empty region with the exact messages |
| F07 | BM4 in memory | a bool array as an object set (CellPatcher, MorphoFeature, MorphoObjects, MorphoRelate, MorphoEmbed); a `float32` object set; a list `[[0, 1]]`, `None` and an integer `numpy.ma.MaskedArray` as object sets; the same bool as a region | `A_MASK_NOT_INSTANCES` with the exact message in every brick: the array branch (`is a bool array`, `is a float32 array`) for the first two, the non-array branch (`is a list`, `is a NoneType`, `is a MaskedArray`, each `(not a plain NumPy array)`) for the others; the region is accepted |
| F08a | BM5 windowed objects use | described with the policy; `TumorRegion` as the converted object set of a request on the lazy windowed route | `MASK_WINDOW_CONVERTED` with the exact message, raised once by the preflight, before any read; no output written |
| F08b | BM5 windowed region and fraction uses | described with the policy; `TumorRegion` converted as objects by a whole-plane request, and the region mask and the fraction mask of a patch request on the windowed route | succeeds; the windowed request reads `TumorRegion` only by `read_mask_window` (never `read_objects`, never labelled); its fractions and its region restriction equal the whole-plane route's `!= 0` on the same patches, bit for bit; no `MASK_WINDOW_CONVERTED` |
| F08c | BM2/BM5 one mask, two uses | described; one run with a whole-plane request whose object set `CellsA` reads `TumorRegion` as objects with the policy, and a windowed patch request using it as a fraction mask; then the same run with a second object set `CellsB` reading `TumorRegion` as objects (i) with the policy, (ii) without it | succeeds; MorphoFeature's request to the resolver holds one entry per use, in run order: `("TumorRegion", "objects", "connected_components")` and `("TumorRegion", "region", None)`; `mask_conversions` has exactly one record, F02's; the objects are F02's labels; the fraction equals F08b's. (i) succeeds with three entries sent, the two `objects` entries collapsed into one selection and still one record; (ii) is refused by the resolver's "two different conversions" `ValueError`, propagated by MorphoFeature with its message verbatim (`'TumorRegion' is requested as objects with two different conversions ('connected_components' and None); ...`), before any read; MorphoFeature raises no refusal of its own about the policies |
| F08d | `parent_labels` region, several consumers | described; `Mito` declared `parent_labels` with groups 3 and 9; one run in which Mito is the region mask of (i) two providers that both declare `parent_labels_support`, (ii) one provider that declares it and one that does not, (iii) one provider that declares it, plus a fraction use | (i) the resolver is asked with `parent_labels_support = true`; one `(Mito, region)` selection with `conversion` none; no `mask_conversions` entry for Mito; the group-aware providers read the raw values 3 and 9. (ii) asked with `false`; one selection with `parent_labels_as_area`, recorded in `mask_conversions` (null `connectivity` and `labeller`) and shown once with the exact message; both providers read `Mito != 0`, the group-aware one included; no refusal. (iii) one provider that declares it uses Mito as a region and another request uses Mito only as a fraction mask: asked with `false`, as (ii); the fraction is `Mito != 0`; the marker recorded and shown |
| F09 | BM5 volumes | described; a position with `z_count = 2`; `TumorRegion` as objects with the policy, (a) as `plane`, (b) as `volume` with `volume_support` | (a) and (b) `A_VOLUME_NOT_SUPPORTED`, no selection; the same request on a `z_count = 1` position is accepted; `TumorRegion` as a region only on the `z_count = 2` position is accepted |
| F10 | BM11 strict binary at the mask step (experiment-v1 §4.5) | described; `binary` files holding (a) {0, 3, 7}; (b) {3, 7}; (c) {0, -1} (`int16`); (d) all 0; (e) all 255; (f) {0, 255}; (g) bool; (h) a T = 2 file whose planes hold {0, 3} and {0, 7}; (i) `float32` holding 0.0 and 1.0 only | (a), (b), (c), (h), (i) refused by the mask step with `R_MASK_CONTRADICTS_REPRESENTATION` and the exact message (values `[3, 7]`, `[3, 7]`, `[-1]`, `[3, 7]`; for (i) the dtype message naming `float32`): (h) shows the check is **file-wide**, since each plane alone would pass; never `checked`, so a run naming them is `A_MASK_UNCHECKED` without reading them. (d)-(g) `checked`; as objects with the policy (d) gives zero objects, (e) one object covering the plane, (f) and (g) the foreground's components; (d) as a region is an empty region (F06). `read_objects` on a plane holding {0, 3, 7} (a stubbed read) raises the same message from the same constructor, through `label_binary` |
| F11 | BM12 binary → instances | (a) `run.binary_to_instances(fov, "TumorRegion", output_mask_id="TumorObjects")` on a checked `binary` mask of F02's two blobs; then (b) the same call again; rejected: (c) a mask ID that is not declared; (d) an `instances` mask; (e) a source file `not yet checked`; (f) a source file **changed since its check** (rewritten with other pixels after the mask step); (g) a `binary` file with `z_count = 2`; (h) `output_mask_id` already declared, and an output file already present that was not written by this conversion; (i) the lineage write fails (an injected error when `mask_lineage.jsonl` is replaced), then the call is repeated; (j) the digest rule: two arrays with identical pixel bytes and (j1) shapes `(8, 8)` and `(4, 16)`, (j2) axes `"TYX"` and `"ZYX"` at shape `(1, 8, 8)`; (k) a second `binary` mask `TumorCopy` with pixels identical to `TumorRegion`, then `binary_to_instances(fov, "TumorCopy", output_mask_id="TumorObjects")` after (a); (l) a source that is a label image inside an OME-Zarr; (m) (a) with the masks folder on a path outside the experiment folder (another temporary directory); (n) (a) with the source stored with a type suffix (`CTRL/rep1/a_TumorRegion.tif`) instead of a type folder; (o) a lineage file holding a line with `root: "experiment"` read by the lineage reader | (a) one `int32` output `TumorObjects` whose labels equal `read_objects` on the source (connectivity 8, same numbering) and whose `mask_lineage.jsonl` line is exactly the [schema](#the-conversion-helpers-bm12) with `operation: "binary_to_instances"`, `connectivity: 8`, `class_value: null`, `axes`, `shape` and `dtype` of both files, both `content_sha256` equal to an independent SHA-256 of the canonical header and pixel bytes, and `helper_version` the installed version; (b) a no-op, files and lines byte-identical; (c)-(h) refused before anything is written, with their messages (`A_MASK_UNCHECKED` for (e) and (f)), no output, no line, no temporary file, existing files unchanged; (i) no output file, no temporary file, `mask_lineage.jsonl` byte-identical to before; the repeated call gives exactly (a)'s files and line; (j) the digests differ in both pairs; (k) refused as a collision (the lineage's `source.mask_id` and `path` differ although the digests are equal), `TumorObjects` and its line unchanged; (l) refused before any read with the OME-Zarr message, nothing written; (m) as (a), the output under that masks folder and both lineage paths relative to it with `root: "masks"`; (n) the output at `TumorObjects/CTRL/rep1/a.tif`, discovered as the mask of image `CTRL/rep1/a`, its pixel labels equal to (a)'s, its lineage line differing from (a)'s only in `source.path` (and in nothing derived from it); (o) the reader refuses the line, naming its `root` |
| F12 | BM12 class labels → per-class binary | `run.classes_to_binary(fov, mask_id, output_prefix="Tissue")` on (a) an `uint16` class image with values {0, 1, 2}; (b) an `int32` one with {0, 2, 5}; rejected: (c) `int16` with a `-1`; (d) `float32`; (e) bool; (f) shape `(2, 8, 8)`; (g) a one-hot `(8, 8, 3)`; (k) a mask declared `binary`; (l) a source file changed since its check; (m) `Tissue_class2` already declared; (n) an `int64` image holding `2147483648`, (n1) through the mask step and (n2) given directly to the helper's pixel validation function (`mask_conversion.check_class_image(pixels, *, mask_id, path)`, which takes no run status); and (h) an all-zero image; (i) (a) with the lineage write of class 2 failing, then repeated | (a) two `uint8` `binary` outputs, `Tissue_class1` then `Tissue_class2`, disjoint, union `image != 0`, each with its exact lineage line (`operation: "classes_to_binary"`, `connectivity: null`, `class_value` 1 and 2, `axes`, `shape`, `dtype`, digests as in F11); (b) `Tissue_class2` and `Tissue_class5` only; (n1) refused by the **mask step** (`check_labels`' existing message), never `checked`, so `classes_to_binary` on it is `A_MASK_UNCHECKED` without reading it; (n2) the helper's range message; (c)-(g), (k), (l), (m), (n2) refused before anything is written, with the exact messages of the [input table](#the-conversion-helpers-bm12) (`A_MASK_UNCHECKED` for (l)), no output, no line; (h) no output, "no class present"; (i) `Tissue_class1` and its line present, no `Tissue_class2` file, line or temporary file; the repeated call skips class 1 and publishes class 2, ending exactly as (a) |
| F13 | BM10 resolver version | each run-record owner (CellPatcher, MorphoRelate, fiberfeatures, MorphoFeature) given a resolver whose `Provenance.resolver_version` is (a) 2, (b) 4, (c) 3; for (a), a cache entry written under version 3 for the same request | (a), (b) `RESOLVER_VERSION_UNSUPPORTED` with the exact message, before any read, with no output or record file written and the cache entry not read; (c) accepted |

## Amendments made by this ADR

- **`experiment-v1.md`** §4.5 (`representation` rule), §4.5b ("Declared wrongly") and §8
  (`R_MASK_CONTRADICTS_REPRESENTATION`): a `binary` file is stored as integers or booleans and holds,
  over all its planes, values in {0, v} for one v > 0; all-zero and all-foreground files are accepted;
  two or more distinct positive values, a negative value or a float file are refused at the mask step
  (BM11). It replaces "more than two distinct values", under which
  {3, 7} passed and which ADR 0001 says the normative text wins over. §4.5c is unchanged: its "for
  example CellPatcher `binary_mask_policy`" names the request field, which stays, and "the numerical
  method stays in the brick that owns it" holds with preprocessing as the owner.
- **Fixtures and validator: unchanged, on purpose.** The rule is about mask pixels. `fixtures/README.md`
  puts pixel rules in the conformance plan's physical scenarios, not in description TOML files, and
  `tools/audit/refval.py` reads no pixels: no fixture or validator line encodes the old "two distinct
  values" rule. The matrix audit (`tools/audit/matrix.py:184-187`) models mask kinds, not value counts,
  and gives the same verdicts under both rules (its `binary` and `bool` masks are {0, 1}; its
  `instances` and `grouped` masks hold several positive values). The conformance plan's P05 states
  the new cases.
- **ADR 0001**, D10: amended by BM11 (pointer in the row); PL1 evidence: the preprocessing pieces
  described as "4-connected" at `a775ebf` are 8-connected since (`mask_pairs.py:19-21`) and are fixed
  at 8 by BM1; the text is kept as dated evidence with a pointer here.
- **ADR 0002** AR5: the conversion is applied by preprocessing's `RunInputs.read_objects`, not by each
  route with CellPatcher's labeller (BM2, BM6); the connectivity is 8, fixed (BM1); the record is the
  resolver's (BM10). The resolver contract becomes version 3 ([ADR 0002](0002-shared-request-resolver.md#resolver-contract-version-3-the-conversion-record-adr-0005)),
  with one request entry per use, one selection per compatible `(mask_id, role)`, and consumers accepting exactly `{3}`.
- **Conformance plan** §3 P05 (the BM11 cases) and §4 "Mask rule" (the routes call `read_objects`,
  copy the record, route by use, check the resolver version).

## Consequences

- One rule answers "was this mask labelled, and how?" for every brick: read `mask_conversions`.
- `connectivity` disappears from every input surface; it appears only in the record.
- MorphoRelate and fiberfeatures no longer import CellPatcher to read a mask (they may for other
  reasons).
- A region is the same pixel set in every brick, and an empty one never stops a run.
- One mask can be a converted object set and an unconverted region or fraction in the same run.
- **Not decided here:** streamed labelling with seam merging on the windowed route (design
  `one-route.md` §5); `parent_labels` pieces (PL1 is unchanged); widening
  `SUPPORTED_RESOLVER_VERSIONS`.

## Modelling choices for the owner's review

Proposals unless marked **accepted by the owner**; the owner may amend the others.

1. The helper in preprocessing, not CellPatcher ([reasons](#why-the-helper-is-in-preprocessing)).
2. The region checker in normalization, the only package every brick can import.
3. `connectivity` recorded as `8` (neighbours), not SciPy's `2`.
4. `parent_labels_as_area` records share the list, with null `connectivity` and `labeller`.
5. A conversion is refused on any position with `z_count > 1`, also when one plane is requested, using
   the existing `A_VOLUME_NOT_SUPPORTED`.
6. One reason, `empty_region`, for the plane, patch, window and object scopes; coverage fractions stay
   defined.
7. The new runtime codes `MASK_REGION_INVALID` (five reasons) and `RESOLVER_VERSION_UNSUPPORTED`;
   `R_MASK_CONTRADICTS_REPRESENTATION` reused at read.
8. The in-memory message names the described-run route, not a labelling function, so that BM2's "one
   labeller, decided once by the resolver" holds in notebooks too.
9. The names of this encoding: the uses `objects`/`region`/`fraction`, `mask_rules` and its
   constructors, `masks.binary.label_binary`, `RegionEstimate`, `mask_conversion`,
   `mask_lineage.jsonl` and its temporary-file protocol, `SUPPORTED_RESOLVER_VERSIONS`,
   `check_window_objects`, `contracts.refuse_resolver_version`, `mask_conversion.check_class_image`.
10. The `stain` wrappers refuse an undefined estimate instead of returning it (an absent white means
    "not given" to `to_scalar`).
11. `content_sha256` over a canonical header (axes, dtype, shape) followed by the pixel bytes in stored axis order and dtype, not over the file.
12. `RESOLVER_VERSION_UNSUPPORTED` constructed once, in normalization (`contracts`), not in
    preprocessing: it must refuse a preprocessing that predates this ADR, and normalization is the
    lowest brick every consumer can import.
13. `classes_to_binary` takes a source declared `parent_labels` or `instances`, refuses `binary`
    (**accepted by the owner, 15 November 2026**; no class-image representation is added); output
    files go to the source's masks folder, in the mask-type folder named by the output mask ID, at
    the FOV image's relative path (choice 17).
14. The lineage digest's canonical header is sorted-key compact JSON of `axes`, `dtype` and
    `shape`, then one newline byte.
15. The lineage `root` is `"masks"` only in this wave; a BM15 `source` has the `root`
    `"experiment"`. OME-Zarr label images are refused by the helpers (**accepted by the owner,
    15 November 2026**).
16. A `fraction` use of a `parent_labels` mask counts as a consumer without
    `parent_labels_support` (a fraction is an area), under the owner's run-wide rule.
17. Helper outputs are named from the FOV's image identity in the type-folder layout, whatever the
    source's layout.

## Open points

None left from the draft: the CellPatcher notebook (BM13), the mask step's value rule (BM11, with the
all-zero and all-foreground rulings of 15 November 2026) and MorphoRelate's `parent_labels` grouping
(BM14) were decided by the owner on 15 November 2026.
