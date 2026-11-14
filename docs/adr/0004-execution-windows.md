# ADR 0004: execution windows, typed coordinates and the patch catalogue (first slice)

- **Status:** **Accepted** (owner, 14 November 2026). The owner decisions it encodes are recorded in
  [the one-route design](../design/one-route.md) (section 7 and the decisions table; the design itself
  stays proposed until its gates are met). Specification only: no fixture, golden or validator of `experiment-v1.md` changes
  (`python -I tools/audit/refval.py fixtures .` unchanged). The coordinate conversions are executable
  in `tools/execution_frames.py`, with their cases in `tools/test_execution_frames.py`.
- **Tracking:** umbrella [#2](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/2); the
  design `docs/design/one-route.md` (PR #38), section 7.5, PR 1 of 8. The implementing PRs follow in
  order: CellPatcher (`context_bounds`), MorphoFeature (manifest field, window units, pool, CUDA lane),
  fiberfeatures (margin hook, windowed entry), and an OME-Zarr integration test.
- **Why a fourth ADR file.** ADR 0001 rules on the experiment description, ADR 0002 on the request
  resolver, ADR 0003 on a run artefact. This decision rules on a fourth thing: **how a provider is called
  on part of a plane**, and how the coordinates of that part are written, so that every brick and the
  QuPath/Fiji bridges read them the same way. By ADR 0002's convention it gets its own file, numbered
  next. Like ADR 0003, it adds no fixture under `fixtures/`, which holds test data for
  `experiment-v1.md` only.

## Context

Today a provider on the patch route receives the **whole plane** (every requested channel and mask)
and a list of patch descriptors with half-open `bounds` (MorphoFeature `patch_sets.PatchDescriptor`).
fiberfeatures runs its pipeline once on the whole plane and measures each patch from those maps. Its
percentile scaling is therefore whole-plane, and nothing can run on a part of a large image. The
one-route design needs a provider to be called on a **window** (a patch plus a context margin) with
results that depend only on declared inputs, never on how the work was split, and with coordinates the
bridges can place back on the source. The independent review of the design (gates G2, G3, G6) asked
for typed coordinates and globally planned identities **before** any scheduler code.

## Decisions

| ID | Decision | Rejected alternative |
| --- | --- | --- |
| EW1 | **Typed coordinates.** Every coordinate written by a brick has one of four types (table below) and is converted only by the formulas below. | One implicit convention, or a blanket ±0.5 rule: wrong for one of the two bridge cases (review B3). |
| EW2 | **Frame record (subset).** A plane analysed by MorphoBricks has a frame `{plane_shape (Y, X), axes_offset (y0, x0) in full-resolution pixels, downsample d}`, with `axes_offset = (0, 0)` and `d = 1` for a whole source at full resolution. Series, level and transform are added by a later amendment. | Inferring the frame from file names, sizes or the open viewer. |
| EW3 | **Global patch catalogue, persisted, versioned.** Patches are planned once per plane in the plane's frame (CellPatcher), written with a catalogue format version (1). A catalogue of another version is refused, never converted. Adding the series to patch identity bumps the version. | Re-cutting patches per run or per execution tile. |
| EW4 | **Window record.** A provider called on a window receives, for each patch, the patch's **global** `bounds` (`pixel_edge`, plane frame, identity unchanged) and a window record `{origin, plane_shape, context_bounds, margin_requested, margin_clipped}`. | Local bounds only: the global position would have to be rebuilt for every output and for the bridges. |
| EW5 | **`context_bounds` belongs to CellPatcher** (pure geometry: patch bounds grown by the margin, clipped at the plane edge, the clipped margin per side recorded). Its arguments are integers; a negative or non-integer margin is refused. | Geometry computed by MorphoFeature or by each provider. |
| EW6 | **Margin.** Declared by the provider per axis, in pixels, as a function of the request and the calibration (a hook, not a constant). It covers the provider's exact filter footprint. Support that only pairs pixels inside a region adds no margin. At the true plane edge the provider's existing edge rule applies and the clipped margin is recorded. Inside a plane, nothing is padded. | A truncated margin; padding inside a plane. |
| EW7 | **Scaling scope vocabulary.** `whole_plane` (today's patch route), `patch_window` (each patch computed on its own window; every percentile from the **patch interior** only; the margin is filter context), and later `run` (fits of design §4.6). The name avoids D67's normalization `scope: patch`. | `per_patch`: confusable with D67. |
| EW8 | **Column fields.** Every feature column computed under a windowed scope carries `scaling_scope` and, when the provider defines one, `feature_group` (a provider-defined label such as fiberfeatures' `structure`, `amount` or `not_assessed`). Both are recorded in the run's per-column section. Amount features are computed and flagged, not refused (owner decision). | Dropping unknown column fields (today's behaviour). |
| EW9 | **Execution record (operational, not scientific identity).** Device, precision and thread counts per library (for example torch, SciPy FFT workers) of every windowed unit are fixed for the run and recorded. Serial and pooled CPU runs must give identical values. CPU vs CUDA is held to a stated per-feature tolerance. | Library defaults (thread counts that change bits between serial and pooled runs). |
| EW10 | **Additive provider contract.** Windowed execution is declared by an optional manifest field (`windowed_execution`, MorphoFeature provider API v3, its contract §6a). A provider that does not declare it is never called on a window. Asking for a windowed scope from such a provider is refused when the run is planned, before any pixel is read. | A provider API version 4: discovery accepts version 3 exactly, so every provider would break at once. |

## Coordinate types (EW1)

| Type | Meaning | Where it is used |
| --- | --- | --- |
| `pixel_index` | the centre of pixel `i` is at `i` | centroids, points, LabConstrictor results |
| `pixel_edge` | pixel `i` spans `[i, i+1)`; a rectangle is half-open `[a, b)` | patch `bounds`, `requested_bounds`, `context_bounds`, rectangle vertices |
| `local` | the same type as above, relative to a window's `origin` | inside a provider call |
| `full_res` | the continuous coordinate in the source's full-resolution grid (pixel `i` spans `[i, i+1)`) | what QuPath and Fiji draw |

**Conversions (per axis; `o` = the window origin, `x0` = `axes_offset`, `d` = downsample):**

| From | To | Formula |
| --- | --- | --- |
| `local` `pixel_edge` `l` | plane `pixel_edge` | `e = o + l` |
| `local` `pixel_index` `l` | plane `pixel_index` | `i = o + l` |
| plane `pixel_edge` `e` | `full_res` | `c = x0 + e * d` |
| plane `pixel_index` `i` | `full_res` | `c = x0 + (i + 0.5) * d` |
| plane `pixel_edge` `e` | LabConstrictor result coordinate | `x = e - 0.5` (the bridge then computes `x0 + (x + 0.5) * d = x0 + e * d`) |
| plane `pixel_index` `i` | LabConstrictor result coordinate | `x = i` |

Example: the patch `[0, 256)` of a whole source has edge vertices `0` and `256` in `full_res`; written
for today's bridge, the vertices are `-0.5` and `255.5`. A centroid at index `12` is `12.5` in
`full_res` and `12` for the bridge.

## Window record (EW4, EW5)

For a patch with `bounds = (y0, y1, x0, x1)` (`pixel_edge`, plane frame), a margin `(my, mx)` in
pixels and a plane of shape `(H, W)`:

- `context_bounds = (max(0, y0 - my), min(H, y1 + my), max(0, x0 - mx), min(W, x1 + mx))`;
- `origin = (context_bounds[0], context_bounds[2])`;
- `margin_requested = (my, my, mx, mx)` (top, bottom, left, right);
- `margin_clipped = (y0 - cb[0], cb[1] - y1, x0 - cb[2], cb[3] - x1)`, which equals `margin_requested`
  except where the plane edge cuts it;
- the patch interior in `local` coordinates is `(y0 - origin_y, y1 - origin_y, x0 - origin_x,
  x1 - origin_x)`.

A provider declares the smallest window it accepts; a smaller one is refused, never padded.

## Consequences

- **New code:**
  - CellPatcher adds `context_bounds` and a catalogue writer and reader (format version 1).
  - MorphoFeature adds the manifest field, window units, the per-column section and the execution
    record.
  - fiberfeatures adds its margin hook and a windowed entry that takes percentiles from the patch
    interior.
- **The default route (`whole_plane`) is unchanged, bitwise.** Windowed execution is opt-in per request.
- **The bridges can place patch rectangles and centroids exactly** with the conversion table. Per-row
  frames in QuPath still need LabConstrictor-QuPath #50/#51 (design §4.10). This ADR only makes the
  numbers unambiguous.
- **Not decided here:** series and level fields (later amendment), the `run` scope's fits (design §4.6),
  streamed output and resume, object tiling, random and cell patches.

## Open points (decided in the implementing PRs)

1. Whether the catalogue file lives with the run's patch outputs or with CellPatcher's export.
2. The per-feature CPU/CUDA tolerances for fiberfeatures, measured in the CUDA-lane PR (design 7.5,
   PR 7).
