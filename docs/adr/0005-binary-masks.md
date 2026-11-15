# ADR 0005: one policy for binary masks

- **Status:** **Proposed** (draft for the owner's review). The owner decisions it encodes (15 November
  2026, BM1-BM5 below) are final; what this ADR adds is their encoding: where the one helper and the
  one region checker live, the record, the vocabulary, the messages and the PR order. Those choices
  are listed under [modelling choices](#modelling-choices-for-the-owners-review). Specification only:
  no fixture, golden or validator of `experiment-v1.md` changes (`python -I tools/audit/refval.py
  fixtures .` unchanged), and `experiment-v1.md` is unchanged. It amends [ADR 0001](0001-experiment-description-v1.md)
  (stale "4-connected" evidence) and [ADR 0002](0002-shared-request-resolver.md) AR5 (who applies the
  conversion) and adds resolver contract version 3.
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

The owner decided BM1-BM5 and BM11-BM14 on 15 November 2026 (final). BM6-BM10 are this ADR's encoding of them.

| ID | Decision | Rejected alternative |
| --- | --- | --- |
| BM1 | **Connectivity is 8, fixed, and is not a parameter anywhere** (owner). Two foreground pixels are one object when they share an edge or a corner. No config key, argument, CLI flag, notebook control or record field chooses it; the record states it (`connectivity: 8`). CellPatcher's `cell.binary_mask_connectivity` and its notebook checkbox are removed. | A setting with 8 as default (today's CellPatcher: two routes give 1 or 2 objects for one mask, I1); 4-connected (fewer objects for the same pixels than skimage, ImageJ and MorphoRelate's CellProfiler parity). |
| BM2 | **One labeller, one record** (owner). `representation` in the description is the only declaration that a mask is binary. The conversion of a `binary` mask to objects is decided and recorded **once**, by preprocessing's request resolver, as `{mask_id, conversion, connectivity, labeller}`, and applied by **one helper**, `RunInputs.read_objects` in preprocessing (BM6). Every brick copies the record as is. There is no other labeller: MorphoRelate's own splitting of binary structures is removed, and rows per component need the recorded conversion. | Each route calling CellPatcher's labeller (ADR 0002 AR5 as written: five call sites, three record shapes, I2, I13); labelling once in the mask step on disk (a labelled copy of every mask; still rejected, AR5). |
| BM3 | **A mask used as a region is `mask != 0`, never labelled** (owner), whatever its representation. One shared region checker (BM7): 2-D, integer or boolean, no floats. **An empty region gives undefined values with a recorded reason, never 0 and never a crash; the plane still runs** (BM8). | Per-brick region rules (I5); `> 0` (equal to `!= 0` only while negative labels are refused upstream); refusing the plane or the run on an empty region (I10). |
| BM4 | **In memory (Python API) an object set is an integer instance array** (owner). A boolean array is accepted **only as a region**. Every other object set is refused with the one code `A_MASK_NOT_INSTANCES` and the one message of BM9. No in-memory API converts, labels or carries `binary_mask_policy`. | CellPatcher's in-memory policy (dtype decides "binary", I3, I4); a per-brick message (I11). |
| BM5 | **Lazy windowed route** (owner): a converted mask used as **objects** stays refused (`MASK_WINDOW_CONVERTED`); its **region and fraction reads are allowed** by window. The check keys on the objects use, not on the mask ID (I9), and runs once, before any pixel is read. **Volumes (Z) are refused for conversion.** | Refusing every read of a mask ID converted anywhere in the run (today, I9); streamed labelling with seam merging (design `one-route.md` §5; not scheduled by this ADR); labelling a Z-stack plane by plane (2-D pieces of one slice are not the objects of a 3-D mask, I7). |
| BM6 | **The helper lives in preprocessing**: `RunInputs.read_objects(selection, mask_id, t, z)` returns the plane's object labels, applying the selection's recorded conversion (reasons [below](#why-the-helper-is-in-preprocessing)). CellPatcher's `label_objects` and its constants are removed. | The helper in CellPatcher (reasons below). |
| BM7 | **The region checker lives in normalization**: `morphobricks_normalization.regions.check_region(mask, shape, *, name)` returns the boolean foreground or raises `MASK_REGION_INVALID` ([contract](#region-checker-contract-bm3-bm7)). It is the only package every brick can import, normalization's own `region_white` included. | The checker in CellPatcher (`check_region_mask` today; normalization cannot import it) or in preprocessing (same reason); one checker per brick (I5). |
| BM8 | **One undefined reason for an empty region, `empty_region`** ([vocabulary](#undefined-reason-vocabulary-bm8)). A value whose denominator is the region's pixels is undefined; a value whose denominator is another, non-empty area (the fraction of a patch inside the region) is defined and may be 0. | A refusal (`sampling_mask_empty`, fiberfeatures' row stop, normalization's `ValueError`); 0 for a mean over no pixels. |
| BM9 | **Refusal codes and messages are fixed here** ([table](#refusal-codes-and-messages)): `A_MASK_NOT_INSTANCES` (resolver and in memory), `A_VOLUME_NOT_SUPPORTED` (a conversion of a Z-stack), `MASK_WINDOW_CONVERTED`, `MASK_REGION_INVALID`, and `R_MASK_CONTRADICTS_REPRESENTATION` at read. Each is raised by one function; bricks re-raise it unchanged. | Each brick rewording the shared refusals (I11, I12). |
| BM10 | **Resolver contract version 3.** The resolver adds the conversion record to its `Provenance` and refuses a conversion on a Z-stack. Nothing else in the contract changes. | Recording the conversion only in each brick (I13); leaving the version at 2 (a consumer could not tell whether its resolver gives the record). |
| BM11 | **Strict binary at the mask step** (owner, 15 November 2026): a mask declared `binary` holds exactly 0 and **one** positive value; any other content (for example {0, 3, 7}) is refused at the mask step with `R_MASK_CONTRADICTS_REPRESENTATION`, so the refusal comes before any run, not at read (closes I14; F10 moves to the mask step). | Any non-zero as foreground (a mask that is really labels or classes passes as binary and is labelled silently). |
| BM12 | **Explicit conversion helpers in preprocessing** (owner): the user converts masks on purpose, as a recorded step that writes **new mask files** declared with their own representation: **binary → instance labels** (the BM1/BM6 labelling: connected components, 8-connected) and **class label image → one binary mask per class value** (for class/semantic segmentation). Each output carries a conversion record (source mask and its fingerprint, operation, class value or connectivity, helper and version), like preprocessing's existing named-axis copies (`convert`). The run then declares the outputs and reads them like any mask. | Converting implicitly at read only (users cannot produce instance or per-class masks they can inspect, share or edit); a labelled copy of every binary mask, made automatically (AR5, still rejected: here nothing is converted unless the user asks, and the source is unchanged). |
| BM13 | **Notebook display** (owner): CellPatcher's notebook shows the recorded conversion of a file run **read-only**; it offers no binary-mask setting. | A file-run-only control (a second place to decide what BM2 decides once). |
| BM14 | **Grouping inside `parent_labels` is a measurement, not a labeller** (owner): MorphoRelate's rows per group of an already-labelled `parent_labels` mask (`structures_table.py:89-114`) are allowed; BM2's "no other labeller" applies to binary masks only. | Routing parent-label grouping through the recorded conversion (the user's labels already define the groups). |

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

The resolver builds one record per mask of the request whose selection has a `conversion`, in request
order, and returns them in `Provenance.mask_conversions`. A record has exactly these four keys, in this
order, all always present:

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

## The helper `RunInputs.read_objects` (BM2, BM5, BM6)

`read_objects(selection, mask_id, t, z) -> numpy.ndarray` (int32, the plane's shape), for a mask of the
selection in the role `objects`:

- `representation = "instances"`, no conversion: the stored labels, checked by `check_labels`, never
  relabelled (D47: an `instances` mask holding 0 and 1 is one object).
- `conversion = "connected_components"`: the stored plane must be boolean, or integers holding 0 and at
  most one positive value; otherwise `R_MASK_CONTRADICTS_REPRESENTATION` names the file and the values
  (I14). The foreground `plane != 0` is labelled with `scipy.ndimage.label` and the 3 × 3 structure of
  ones (8-connected), numbered 1, 2, ... in row-major order of each component's first pixel. A plane
  with no foreground gives zero objects, not an error.
- It reads whole planes only; it has no window argument. A mask in the role `region`, or a
  `parent_labels` mask, passed to it is a programming error (`ValueError`).

The pure labelling function under it is public in the same module so that the mask step and the tests
import it; no brick calls it on a file run.

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
mask and patch regions; MorphoEmbed's patch masks; normalization's `region_white`.

## Undefined-reason vocabulary (BM8)

| Reason | When | Value | Recorded as |
| --- | --- | --- | --- |
| `empty_region` | the region (`mask != 0`) holds no pixel of the area being measured: the plane, a patch, a window or an object | NaN (null in JSON) | the brick's existing undefined record: MorphoFeature/#63 applicability state `undefined`, detail `empty_region`; MorphoObjects `nan_reason`; MorphoRelate and fiberfeatures their reason column; normalization's returned reason |

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

| Code | Raised by | When | Message (exact; `{…}` filled in) |
| --- | --- | --- | --- |
| `A_MASK_NOT_INSTANCES` (resolver) | `resolve_request` | a `binary` mask as objects without `binary_mask_policy`; a `parent_labels` mask as objects | unchanged (preprocessing `run_inputs_request.py:453-478`) |
| `A_MASK_NOT_INSTANCES` (in memory) | `morphobricks_preprocessing.masks.check_object_set` (exception `MaskNotInstancesError`, a `ValueError`) | an object set that is not an integer `numpy.ndarray` (boolean, float or other) | `A_MASK_NOT_INSTANCES: {name!r} is a {dtype} array, not an object set. An object set is an integer instance array (0 is background, each positive value one object). A boolean array is used only as a region. To measure the connected pieces of a binary mask as objects, describe it as binary and request binary_mask_policy='connected_components' in a run.` |
| `A_VOLUME_NOT_SUPPORTED` | `resolve_request` | a mask request with `binary_mask_policy` on a position with `z_count > 1`, as a `plane` or a `volume` request, with or without `volume_support` | `{mask_id!r} would be converted by connected_components, which labels 2-D planes only; the images of {position} have {z_count} Z planes. Converting a Z-stack is not supported (A_VOLUME_NOT_SUPPORTED).` |
| `MASK_WINDOW_CONVERTED` | MorphoFeature, when the run is planned, before any pixel is read (one check) | a windowed unit would read, as objects, a mask whose selection has `conversion = "connected_components"` | `MASK_WINDOW_CONVERTED: {plane}: the object set {object_set!r} is the binary mask {mask_id!r} converted by connected_components, which needs the whole plane, so it has no window. Run this request on the whole-plane route; region and fraction reads of {mask_id!r} are read by window.` |
| `MASK_REGION_INVALID` | `check_region` (exception `RegionMaskError`, a `ValueError`) | the five reasons of the [contract](#region-checker-contract-bm3-bm7) | `MASK_REGION_INVALID ({reason}): the region {name!r} {detail}. A region is a 2-D integer or boolean array of the plane's shape (Y, X); its non-zero pixels are inside.` with `{detail}` one of: `is not a NumPy array (got {type})`, `is a masked array`, `has {ndim} dimensions`, `has shape {shape}, not the plane's {plane}`, `has pixel type {dtype}` |
| `R_MASK_CONTRADICTS_REPRESENTATION` | `read_objects` | a `binary` plane converted at read holds a negative value or more than one foreground value | `R_MASK_CONTRADICTS_REPRESENTATION: {path} is declared binary but holds the foreground values {values}; a binary mask holds 0 and one positive value. Declare it instances or parent_labels, or fix the file.` |

`A_MASK_NOT_INSTANCES`, `A_VOLUME_NOT_SUPPORTED` and `R_MASK_CONTRADICTS_REPRESENTATION` are existing
codes (experiment-v1 §8; ADR 0002); no `A_*` or `R_*` code is added. `MASK_WINDOW_CONVERTED` is
MorphoFeature's existing code. `MASK_REGION_INVALID` is new and, like `MASK_WINDOW_CONVERTED`, is a
runtime code outside experiment-v1 §8. A malformed request (a policy on a non-`binary` mask or in the
role `region`) stays a `ValueError` raised by the resolver only (I12); bricks do not check it first.

## Breaking changes and migration notes

Before the first pipeline release there is no backward compatibility (ADR 0002 AR10): removed keys are
refused as unknown, never mapped.

| Brick | Breaking change | Migration |
| --- | --- | --- |
| normalization | none for valid inputs: `region_white` accepts integer regions (relaxing) and returns undefined values with `empty_region` instead of raising on an empty region | callers that caught the `ValueError` read the returned reason; `TypeError` on a non-boolean region becomes `MASK_REGION_INVALID` (`ValueError`) for floats only |
| preprocessing | resolver contract version 3 (`Provenance.mask_conversions`; a conversion on a Z-stack refused); new `RunInputs.read_objects`, `check_object_set`; `PIECE_STRUCTURE` imported from the helper's module, not restated | consumers check `RESOLVER_VERSION >= 3` and copy the record; additive otherwise |
| CellPatcher | **removed:** `label_objects`, `BINARY_MASK_POLICIES`, `CONNECTIVITIES`, `BINARY_MASK_CONNECTIVITY`; `cell.binary_mask_connectivity`; the notebook checkbox "The mask is binary: label its connected components"; the in-memory use of `cell.binary_mask_policy`; `_RESOLVED`/`resolved_masks()`; `check_region_mask` (moves to normalization). A boolean cell mask in memory is `A_MASK_NOT_INSTANCES`. Float fraction, random and windowed masks are `MASK_REGION_INVALID`. A Z-stack conversion is refused. `run_config.json`: `mask_conversions` replaces `cell.binary_mask_connectivity` and `preprocessing.mask_conversions` | in memory: pass integer instance labels, or run a described run with the policy; a config file with `binary_mask_connectivity` is refused (delete the key); `cell.binary_mask_policy` stays only as the file-run request field passed to the resolver; threshold probability maps before using them as fraction masks |
| MorphoObjects | the boolean object-set message becomes the shared `A_MASK_NOT_INSTANCES` one; `restrict_to` uses normalization's checker | none for valid inputs |
| MorphoEmbed | the bool object-mask refusal becomes `A_MASK_NOT_INSTANCES` (was a dtype-kind message); `BINARY_MASK_POLICY = None` and its explicit argument removed; stale `ROADMAP.md:293-296` fixed | none for valid inputs |
| MorphoRelate | **a `binary` structure without `binary_mask_policy` gives no `structures.csv` rows** (it is a region: its region columns and component-count features stay); rows need the recorded conversion and are then of kind `instance`. Its own `BINARY_MASK_POLICIES` copy, labelling call site and structure splitting of binary masks removed; `run_config.json` `masks[].conversion/labeller/connectivity` replaced by `mask_conversions`; `connectivity` 2 → 8; in memory a boolean object set is `A_MASK_NOT_INSTANCES` | add `:connected_components` to the structure's `--mask` (or `binary_mask_policy` in the config) to keep per-component rows; downstream readers of `structure_label_kind = component` for binary masks read `instance` |
| fiberfeatures | **a `region` mask is no longer handed to CellPatcher cell mode as cells** (I6): cell mode needs an `objects` mask; an empty analysis region gives undefined rows with `empty_region` instead of stopping; `> 0` becomes `!= 0`; the run record keys `binary_mask_policy`/`binary_mask_connectivity` become `mask_conversions`; `labeller_connectivity()` removed; notebooks' `BINARY_MASK_POLICY` parameter stays the request field | name an `objects` mask (with the policy for a binary one) for cell mode |
| MorphoFeature | `mask_conversions` replaces `masks[].conversion/labeller/connectivity` in the manifest (`connectivity` 2 → 8); `FovInput` accepts boolean **regions** and refuses boolean object sets with the shared message; `sampling_mask_empty` becomes the non-refusing ledger reason `empty_region`; `MASK_WINDOW_CONVERTED` only for objects reads, checked once | readers of the manifest read `mask_conversions`; cached results whose identity carries the old record are not reused (the record is part of the source identity) |

## Implementation order

One PR per brick, in dependency order, each with its tests; each later PR pins the tag of the earlier
ones it imports. A PR does not start before the tags it needs exist.

| # | Repository | Change | Tests in the same PR |
| --- | --- | --- | --- |
| 0 | MorphoBricks-Spec | this ADR; ADR 0001/0002 amendments; conformance plan "Mask rule" row | `refval.py` unchanged; tools tests |
| 1 | morphobricks-normalization | `regions.check_region`, `EMPTY_REGION`, `RegionMaskError`; `region_white` on it | the BM3/BM7 table case by case (F04, F05); empty region in `region_white` (F06) |
| 2 | morphobricks-preprocessing | resolver contract v3 (`mask_conversions`, Z-stack refusal); `RunInputs.read_objects`; `check_object_set`; `PIECE_STRUCTURE` from the helper module; strict binary at the mask step (BM11); pins normalization | F01, F02, F09, F10 at the mask step; F07's message; the resolver's import scan still passes |
| 2b | morphobricks-preprocessing | the conversion helpers (BM12): binary → instances, class labels → per-class binary; recorded outputs; CLI and notebook card | F11 (binary → instances equals `read_objects` on the same mask), F12 (class image with values {0, 1, 2} → two binary masks whose union is the foreground, records exact) |
| 3 | CellPatcher | the CellPatcher removals above; file runs read objects through `read_objects`; regions through `check_region`; record copied | F01 (no connectivity key accepted), F05 on fraction/random/windowed masks, F07, the `run_config.json` record (F02) |
| 4 | MorphoObjects | shared refusal; `check_region` | F07, F04, F06 (`empty_region` unchanged) |
| 5 | MorphoEmbed | shared refusal; constant removed; ROADMAP | F07 |
| 6 | MorphoRelate | no binary structure splitting; `read_objects`; record copied; region checker; shared refusal | F03 (no rows without the policy; instance rows and the record with it), F02, F06, F07 |
| 7 | fiberfeatures | `read_objects`; record; no region as cells; empty region undefined; `!= 0` | F03 (region not cells), F02, F06 |
| 8 | MorphoFeature | `read_objects`; record copied; one `MASK_WINDOW_CONVERTED` check for objects; `FovInput` regions; `empty_region` in the ledger | F08, F02, F06, F07; the cross-route "Mask rule" with each provider |

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
`TumorRegion` declared `binary`.

| Fixture | Rule | Input | Expected outcome (exact) |
| --- | --- | --- | --- |
| F01 | BM1 connectivity 8 | described; `TumorRegion` = two 2 × 2 blobs touching at one corner (`[1:3,1:3]` and `[3:5,3:5]` = 1); objects with the policy | one object, label 1, on every route; record `connectivity: 8`; a CellPatcher config with `binary_mask_connectivity` is refused as an unknown key |
| F02 | BM2 one labeller, one record | described; two disconnected blobs (`[1:3,1:3]`, `[5:7,5:7]` = 1); objects (a) without, (b) with the policy | (a) `A_MASK_NOT_INSTANCES`, no selection; (b) labels 1 (top-left) and 2, equal on every route; every brick's `mask_conversions` is exactly `[{"mask_id": "TumorRegion", "conversion": "connected_components", "connectivity": 8, "labeller": "morphobricks_preprocessing.RunInputs.read_objects"}]` |
| F03 | BM2 no other labeller | F02's mask (a) as a MorphoRelate `structure` without the policy; (b) as a fiberfeatures `region` with CellPatcher cell mode and no `objects` mask | (a) no `structures.csv` row for it, no record, its region columns and `component_count = 2` present; (b) refused before any pixel is read, naming the missing `objects` mask |
| F04 | BM3 region = `mask != 0` | the same pixel set as bool, `uint8` 0/255, and `int32` instances with labels 1 and 7 | `check_region` returns three equal boolean arrays; nothing is labelled; a region value measured on each is bit-identical |
| F05 | BM3/BM7 region checker | `float32` 0/1; shape `(1, 8, 8)`; shape `(8, 9)`; a masked array; a list | `MASK_REGION_INVALID` with reasons `dtype`, `not_2d`, `shape`, `masked_array`, `not_an_array`, and the exact messages |
| F06 | BM3/BM8 empty region | an all-zero region on one plane of a two-plane run | the mean intensity in the region is NaN with `undefined`/`empty_region`; the fraction of a patch inside it is `0.0`; a patch set sampled in it has no patch and the plane is listed with `empty_region`; the other plane and the plane's other requests give their values; no exception |
| F07 | BM4 in memory | a bool array as an object set (CellPatcher, MorphoFeature, MorphoObjects, MorphoRelate, MorphoEmbed); a `float32` object set; the same bool as a region | `A_MASK_NOT_INSTANCES` with the exact message in every brick for the first two; the region is accepted |
| F08 | BM5 windowed route | described with the policy; `TumorRegion` as a converted object set of one request and the fraction mask of a windowed patch request | the windowed objects read is `MASK_WINDOW_CONVERTED` before any pixel is read; the fraction read is by window and equal to the whole-plane fraction; refused once, one message |
| F09 | BM5 volumes | described; a position with `z_count = 2`; `TumorRegion` as objects with the policy, (a) as `plane`, (b) as `volume` with `volume_support` | (a) and (b) `A_VOLUME_NOT_SUPPORTED`, no selection; the same request on a `z_count = 1` position is accepted |
| F10 | BM11 strict binary at the mask step | described; a `binary` file holding {0, 3, 7} (and one holding only {3, 7}) | the mask step refuses each with `R_MASK_CONTRADICTS_REPRESENTATION` naming the file and its values; no run uses them; `read_objects` keeps the same check as a guard |
| F11 | BM12 binary → instances | a checked `binary` mask; the helper writes an `instances` mask | its labels equal `read_objects` on the source (connectivity 8, same numbering); the output's record names the source fingerprint, `binary_to_instances`, `connectivity: 8` and the helper version |
| F12 | BM12 class labels → per-class binary | a label image with values {0, 1, 2} | two `binary` masks (classes 1 and 2), disjoint, whose union is `image != 0`; each record names the source, `classes_to_binary`, its class value and the helper version; class 0 gives no mask |

## Amendments made by this ADR

- **ADR 0001**, PL1 evidence: the preprocessing pieces described as "4-connected" at `a775ebf` are
  8-connected since (`mask_pairs.py:19-21`) and are fixed at 8 by BM1; the text is kept as dated
  evidence with a pointer here.
- **ADR 0002** AR5: the conversion is applied by preprocessing's `RunInputs.read_objects`, not by each
  route with CellPatcher's labeller (BM2, BM6); the connectivity is 8, fixed (BM1); the record is the
  resolver's (BM10). The resolver contract becomes version 3 ([ADR 0002](0002-shared-request-resolver.md#resolver-contract-version-3-the-conversion-record-adr-0005)).
- **Conformance plan** §4 "Mask rule": the routes call `read_objects` and copy the record.
- `experiment-v1.md` is unchanged: §4.5c's "for example CellPatcher `binary_mask_policy`" names the
  request field, which stays, and "the numerical method stays in the brick that owns it" holds with
  preprocessing as the owner.

## Consequences

- One rule answers "was this mask labelled, and how?" for every brick: read `mask_conversions`.
- `connectivity` disappears from every input surface; it appears only in the record.
- MorphoRelate and fiberfeatures no longer import CellPatcher to read a mask (they may for other
  reasons).
- A region is the same pixel set in every brick, and an empty one never stops a run.
- **Not decided here:** streamed labelling with seam merging on the windowed route (design
  `one-route.md` §5); whether the mask step adopts the read value rule ([open point 2](#open-points));
  `parent_labels` pieces (PL1 is unchanged).

## Modelling choices for the owner's review

Not owner decisions; the owner may amend them.

1. The helper in preprocessing, not CellPatcher ([reasons](#why-the-helper-is-in-preprocessing)).
2. The region checker in normalization, the only package every brick can import.
3. `connectivity` recorded as `8` (neighbours), not SciPy's `2`.
4. `parent_labels_as_area` records share the list, with null `connectivity` and `labeller`.
5. A conversion is refused on any position with `z_count > 1`, also when one plane is requested, using
   the existing `A_VOLUME_NOT_SUPPORTED`.
6. One reason, `empty_region`, for the plane, patch, window and object scopes; coverage fractions stay
   defined.
7. The new runtime code `MASK_REGION_INVALID` and its five reasons; `R_MASK_CONTRADICTS_REPRESENTATION`
   reused at read.
8. The in-memory message names the described-run route, not a labelling function, so that BM2's "one
   labeller, decided once by the resolver" holds in notebooks too.

## Open points

None left from the draft: the CellPatcher notebook (BM13), the mask step's value rule (BM11) and
MorphoRelate's `parent_labels` grouping (BM14) were decided by the owner on 15 November 2026.
