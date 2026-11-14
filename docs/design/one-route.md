# One route for every image size and type (proposed design)

**Status: proposed, not normative.** Acceptance gates G1-G9 (section 9) must be met before any part
becomes Spec text. Umbrella issue: [#2](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/2).
Written 14 November 2026 from two code audits and one independent review (verdict: adopt after changes).

## 1. Goal and scope

One MorphoBricks route for **every image size** (a small crop to a whole slide of about 100k x 100k
pixels) and **every image type** (multichannel 8/16-bit fluorescence and 8-bit RGB brightfield):

- multithreaded on the CPU lane, with a GPU lane where a provider supports it;
- usable from QuPath and Fiji through the LabConstrictor bridges;
- with results the bridges can place back on the source.

A small image is the trivial case of the same route.

**Out of scope:** true 3-D tiling (Z context), which belongs to the 3-D route
([MorphoFeature #157](https://github.com/CellMigrationLab/MorphoFeature/issues/157)).
**Not yet supported:** Z stacks. CellPatcher refuses Z>1 under every `z_policy` (`config.py:45-59`,
issue #83), and tiling Z/T plane by plane needs that lifted first.

## 2. Principles

1. **One scientific analysis contract; separate storage-access and execution plans.** Storage format,
   tile size, worker count, executor and machine never decide which algorithm runs or which features
   exist. They are recorded, not scientific.
2. **Declare, never guess.** Preprocessing measures and proposes; the user confirms; the choice is
   recorded; downstream bricks read the record.
3. **Each brick keeps its role.**
   - preprocessing: sources, scenes, levels, axes, calibration, windows, resource estimates;
   - normalization: conversion and fits;
   - CellPatcher: observation geometry;
   - MorphoFeature: scheduling, fits lifecycle, outputs;
   - providers: science;
   - bridges: UI, identity, placement. Bridges never tile.
4. **A shared contract in the Spec, not shared code.** Each brick implements its scheduler against the
   same identity, frame, resource and merge fields.
5. **Execution invariance is proven, not assumed.** Every claim of equality has a conformance fixture
   and a stated tolerance.

## 3. Current state (evidence)

Commits read: preprocessing `3aa3b25` (v0.5.3), normalization `95e1d6d` (v0.6.0), CellPatcher
`3c2d437`, MorphoFeature `4dcbb08`, fiberfeatures `47f68e8`, MorphoObjects `edd1b40`, MorphoRelate
`eb9af6b`, MorphoEmbed `2b3b671`, LabConstrictor-Tools `5a28949`, -QuPath `065809e`, -Fiji `ad2fb62`.

**Already in place:**
- **preprocessing:** a bounded-memory block reader (TIFF strips/tiles, Zarr chunks), and block-streamed
  histograms equal to the whole-plane ones (`planes.py:24-42`). Histograms are binned, so a quantile
  from them is exact only where the bins are.
- **normalization:** `to_scalar` is per-pixel with declared parameters (`stain.py:235-319`).
- **CellPatcher:** grid planning needs only the shape (`grid.py:42-83`).
- **MorphoFeature:**
  - patch descriptors with half-open `bounds` (`patch_sets.py:142-172`);
  - a run-level fit machinery (`fits.py`: `repeat_scaling`, `max_object_extent`).

**Gaps:**
- **preprocessing reading:**
  - `read_plane` stacks every channel into a whole `CYX` plane, and `read_image` calls it to learn the
    shape (`run_inputs.py:299-341`);
  - mask reads, the mask scan and mask evidence read whole planes with no limit
    (`run_inputs.py:347-388`, `masks/read.py:30-79`);
  - subsampled or JPEG-header TIFF pages cannot be read in blocks (`planes.py:1187-1208`);
  - RGB block reads decode each segment once per sample (`planes.py:1265-1331`);
  - multiple series are refused (`metadata.py:468-480`);
  - Aperio/NDPI calibration is not read;
  - previews decode level 0.
- **preprocessing copies:** the OME-Zarr copy writes one chunk per whole plane and no pyramid levels.
- **MorphoFeature:**
  - the offline pool's unit is provider x FOV, each task loading the FOV (`bricks.py:268-321`); the
    in-memory `Workflow.submit` can share a loaded FOV;
  - the patch route is serial (`patch_workflow.py:448-499`);
  - results are assembled in memory and written at the end (`results.py:270-373`);
  - there is no resume.
- **fiberfeatures:** its patch route runs the whole pipeline on the whole plane, then measures patches.
  Its global dependencies:
  - percentile normalization before **and after** smoothing (`preprocessing.py:232-256`);
  - local contrast with global statistics (`:179-231`);
  - per-scale percentile rescaling (`multiscale.py:313-325`), which feeds the scale-fusion weights and
    therefore the selected scale and states (`states.py:151-203`);
  - nematic correlation over the region (`nematic.py:319-399`).
- **CellPatcher identity:**
  - `patch_id` comes from coordinates for grid patches, from `label_id` for cell patches, and from a
    draw number for repeated random rectangles (`ids.py:235-296`);
  - the FOV key has no series.
- **Bridges:**
  - coordinates are pixel-centre indices, placed with `c = x0 + (x + 0.5) * downsample`
    (SPEC_WRONG_SCIENCE 1.1);
  - QuPath applies one `ApplyTo` frame per output, not per row (`LabConstrictorTools.groovy:2627-2688`);
  - file inputs are not bound to the open slide.

## 4. Architecture

### 4.1 Request, access plan, execution plan

| Layer | Scope | Decides | Recorded |
| --- | --- | --- | --- |
| **Scientific request** | run-wide | providers, features, channels, scopes of every fit, regions, series and level selection, effective calibration | yes, scientific identity |
| **Access plan** | per source / plane | whole read or windowed read, which chunks, reader handles | yes, operational |
| **Execution plan** | per work unit | work-unit partition, executor, workers, device | yes, operational |
| **Resource policy** | run-wide, user-confirmed | CPU RAM, GPU VRAM, queued-byte budgets | yes, operational |

The resource policy is confirmed like the axes are: proposed from estimates, before any pixel is read.

- **A resource limit never changes a feature.** If a requested feature cannot run within the confirmed
  budget, the run is refused, naming the budget or the feature. It is never silently replaced by an
  approximation.
- **Storage layout never changes a feature.** A small FOV stored as tiled OME-Zarr keeps its
  whole-field features.

### 4.2 Identity, frames and coordinates

- **Canonical FOV identity gains a series (scene) discriminator.** It is carried through every
  downstream identity (CellPatcher `patch_id`, object keys), so two scenes of one file can never share
  observation identities.
- **Series, pyramid level, source-to-analysis transform and effective calibration are scientific
  selections.** They are recorded per source, never inferred. A run-wide level policy (default: level 0,
  owner decision) resolves to an explicit recorded level per source.
- **Frame record** (aligned with the LabConstrictor frame): source identity, series, level,
  `axes_offset (t, z, y, x)` in the full-resolution grid, downsample, transform. A viewer crop is a FOV
  with a non-zero offset; a file is offset 0.
- **Typed coordinates, one tested conversion each:**

  | Type | Meaning | Example |
  | --- | --- | --- |
  | `pixel_index` | centre of pixel `i` at `i` (centroids, points) | centroid `(12.0, 40.5)` |
  | `pixel_edge` | boundaries; pixel `i` spans `[i, i+1)` (patch `bounds`, polygon vertices of rectangles) | patch `[0, 256)` |
  | `local` | relative to a window's origin | inside a work unit |
  | `full_res` | continuous full-resolution coordinate of the source | what QuPath draws |

  A patch `[0, 256)` sent through today's bridge, which adds 0.5, must be written as vertices `-0.5` and
  `255.5`. A centroid needs no shift. **No blanket ±0.5 rule.**
- **Calibration** is per axis and per level, with its source (`image | file | user`) and raw text, in
  the bridge `_calibration` vocabulary. An unknown unit means unknown calibration.

### 4.3 Global observation catalogue

- **Patches are planned once, in the global FOV frame**, by CellPatcher (grid, random and cell modes),
  with immutable identities: random draw order and repeated rectangles preserved, cell patches from
  whole objects. The catalogue is persisted.
- **Each observation is assigned to exactly one work unit.** The work unit reads whatever windows that
  observation needs (interior plus context). Observations are never regenerated or cut per execution
  tile, so execution tiles need not align with any patch grid.
- **Objects come from global, integer-preserving label identities.** An object spanning two windows is
  one object. Seam merging is 8-connected, with no implicit relabelling.

### 4.4 Regions

Three separate regions, each with explicit rasterization and clipping rules:
- `sampling_region`: where observations may be placed;
- `measurement_region`: which pixels contribute to a measurement;
- `context_region`: pixels read for filters.

A QuPath ROI becomes a declared `sampling_region` and/or `measurement_region`, never implicitly both.

### 4.5 Provider execution contract

Each provider declares, per feature, its **dependency graph**:
- **input kinds and channel capability:** one channel, a channel pair, a model-specific channel set,
  RGB-derived map, labels. This is an explicit capability matrix; "the reader accepts `CYX`" is not
  "the algorithm supports every channel combination";
- **fits at every stage:** input, derived maps, per scale; each with estimator and scope;
- **global reductions** and how they combine;
- **context:** margin in physical units, converted to pixels per axis, with the exact footprint (owner
  decision);
- **border semantics at the true image edge:** padding, clipping or refusal, as the provider defines it
  today. For example, MorphoEmbed's image-edge zero padding stays; padding inside a slide is never used;
- **backend and numerical tolerance.**

The resulting class per feature is `local`, `needs_fits(<fits>)` or `whole_only`. **Unknown dependencies
are refused.** A feature is `local` only if its whole upstream chain is. For example, fiberfeatures
`curvature_proxy` is *not* local today, because its upstream maps are percentile-scaled per image and per
scale.

### 4.6 Fits

Fits are staged global estimators with **immutable fit records**: scope, inputs, estimator, exactness,
pixel population. They generalise MorphoFeature's existing fit machinery; there is no per-provider
mechanism.

| Statistic | Rule |
| --- | --- |
| Raw fluorescence intensity range | streamable per declared channel and scope; record exact vs histogram-approximate |
| RGB-to-scalar map range | fitted after the declared conversion: own pass, or a validated fused pass |
| fiberfeatures post-smoothing and per-scale percentiles | derived-map passes per stage, or a versioned fixed-range algorithm (#214); one raw fit is not enough |
| MorphoRelate fraction-of-max FOV thresholds | streamable whole-FOV maximum, same scope |
| MorphoRelate Costes thresholds | needs paired-channel global statistics; not from two marginal histograms |
| MorphoRelate object `rwc`, granularity; fiberfeatures nematic correlation and alignment length | `whole_only` until an equivalent algorithm is shown |
| MorphoEmbed plane normalization | tileable when the whole original plane's fit is frozen |

**Per-condition fits** are never an implicit default: they can erase the effect being measured. They are
allowed only when explicitly declared, as a batch correction or within-condition analysis, with their
reference and scope recorded.

### 4.7 Reductions and numerical reproducibility

- **Histograms merge exactly only with identical bin definitions.** Use fixed global bins and integer
  counts.
- **Float reductions** use stable accumulators and an order independent of the partition, or are held to
  a stated per-feature tolerance.
- **Tile size can change partial sums.** Sorting by work-unit ID controls completion order, not
  partition size.
- **No bitwise promise across unverified backends.** Device, precision and library versions are
  recorded, and a non-deterministic kernel is refused where determinism is required.

### 4.8 Resources

Preprocessing records the header decode estimate per plane and FOV (machine-independent,
`plane_layout()`). Providers declare **peak live memory per execution stage**: channels, derived maps,
labels, halos, multiscale intermediates, GPU tensors and batches, result buffers.

The scheduler admits work against separate budgets:
- CPU RAM;
- GPU VRAM;
- worker concurrency;
- queued bytes.

A provider bundle in one work unit must not force every intermediate to coexist. Bounds that cannot be
established cause a refusal at preflight, never a guess.

### 4.9 Outputs and resume

- **Storage:** partitioned part files (Parquet/Arrow) with stable row IDs, plus a **transaction manifest**
  (ledger of finished work units), merged atomically.
- **Resume:** each checkpoint is bound to the source fingerprints, request, fit records, provider
  versions and work-unit identity. Parts from different analysis definitions are never mixed.
- **Bridge-scale outputs** (selected CSV/GeoJSON) are separate from machine-scale tables. Nothing is
  silently omitted: the full table stays on disk.
- **Fingerprints:** one SHA-256 per source file, or the existing OME-Zarr folder digest, remains the
  integrity anchor (owner decision). Per-chunk digests may be added later as an optional resume index,
  never as a replacement. Strict `--verify-content` reads the whole source; its cost is stated.

### 4.10 Bridges

Two entries into the same route:

1. **Viewer crop** (at most 100M pixels): crop, `RegionOf` mask and frame record, making one FOV.
   [QuPath #49](https://github.com/CellMigrationLab/LabConstrictor-QuPath/issues/49) is the early smoke
   test and is independent of this design.
2. **File route:** the slide or OME-Zarr path, plus ROI polygons and UUIDs.

**Placing results on the slide requires new bridge work**
([QuPath #50](https://github.com/CellMigrationLab/LabConstrictor-QuPath/issues/50),
[#51](https://github.com/CellMigrationLab/LabConstrictor-QuPath/issues/51)) and a result-binding contract
in the LabConstrictor protocol:
- per-row frames, not one `ApplyTo` per output;
- authenticated source identity, with original vs converted slide mapping;
- an ROI UUID snapshot;
- placement checks.

The bridges import a bounded, selected set of overlays. The bridge reads the stored decode estimate to
choose the crop or the file route.

## 5. Work per brick

- **Spec:**
  - series in FOV identity;
  - frame record and typed coordinates;
  - levels and per-level calibration;
  - the three regions;
  - the provider dependency declaration and capability matrix;
  - fit records;
  - resource declarations;
  - output transaction manifest;
  - a conformance fixture per invariance claim.
- **preprocessing:**
  - scene and level inventory with explicit selection;
  - #294: baseline series; associated images recorded, never read; MPP/NDPI calibration; `imagecodecs`
    extra; a block path for subsampled/JPEG-header pages; one decode per segment for all samples;
  - #179: `read_window(fov, series, level, t, z, bounds, channels)`, exact bounds, chunk-aligned I/O
    internally, channels selected **before** decoding. It replaces `read_plane`'s all-channel stacking,
    and `read_image` takes its shape from the header;
  - windowed, integer-preserving mask reads and a streamed mask scan with seam merging (new issue);
  - previews from pyramid levels (#251);
  - a tiled, pyramidal OME-Zarr copy and blockwise projection (new issue);
  - #107 / #108 workers: threads first, benchmarked against processes, a pluggable executor, separate
    reader handles, and a benchmark of shared vs separate handles across codecs and stores.
- **normalization:**
  - #73 remainder;
  - fit records with estimator and exactness;
  - provenance as counts;
  - 16-bit RGB stays refused (`to_scalar` requires `uint8`) unless a conversion for it is declared.
- **CellPatcher:**
  - a persisted global patch catalogue (all modes);
  - `context_bounds(bounds, margin, shape)` as pure geometry;
  - #87: low-resolution tissue mask with an exact recorded scale; delivery through `read_window`;
  - Z/T plane tiling requires lifting the Z refusal (#83).
- **MorphoFeature:**
  - work units over catalogue observations;
  - resource-aware provider bundles;
  - the staged-fit lifecycle;
  - streamed parts and resume (#218);
  - CPU pool and GPU queue.
- **providers:** dependency declarations (section 4.5) and fits (section 4.6). fiberfeatures #160; MorphoRelate;
  MorphoEmbed; MorphoObjects (object features need context of at least the fitted maximum extent).
- **bridges:** result-binding contract, #50, #51, bounded overlays.

## 6. Order

1. **Contracts first.** Global identities (series), frames and typed coordinates, the global observation
   catalogue and ownership, the three regions.
2. **The execution-invariance contract.** Dependency declarations, context, border semantics, fits,
   reductions, tolerances, with conformance fixtures.
3. **The output and checkpoint contract.**
4. **A minimal window reader and one real OME-Zarr integration test**, before the scheduler API is
   frozen.
5. **The in-memory scheduler** over catalogue observations, validated first on a **genuinely local
   statistic** (for example MorphoObjects patch intensity), with parity and executor-invariance goldens.
6. **Fits** (#214 staged fiberfeatures fits, MorphoRelate, MorphoEmbed) and provider declarations (#160).
7. **Readers and scale:** #294, #179 full, masks at scale, CellPatcher #87, levels and tissue mask.
8. **Streamed output and resume** (#218), then the bridge result binding (#50, #51).
9. **A real-slide benchmark:** wall time, peak RAM/VRAM, bytes read, tiled vs whole on a slide that
   fits.

QuPath #49 (small ROI) runs independently, early.

## 7. First slice: tiles on the RGB route

Owner decisions of 14 November 2026, adjusted to sections 4.3 and 4.5.

- **Scope `per_patch` (declared).** Each grid patch of the global catalogue is computed by fiberfeatures
  on its own window: the patch plus the exact margin, clipped and recorded at the image edge, with its
  own percentile scaling at every stage. Results depend only on the declared catalogue and margin, never
  on execution partition or workers.
  - This is a **declared different scientific scope** from today's whole-plane patch route. It does not
    claim equality with it. Equality with whole-image needs the staged fits of section 4.6.
  - `per_patch` is one value of the declared scaling scope, so it stays valid when run-level fits
    arrive.
- **Amount features are computed and flagged.** The scope and each feature's structure/amount group
  (`fiberfeatures.feature_groups`) are recorded in the manifest and visible on the columns, so they
  cannot be pooled with whole-image values unknowingly. Structure features are the recommended set.
- **Grid patches only** in this slice. Random and cell patches follow once the persisted catalogue
  covers them.
- **Pieces:**
  - Spec: the first-slice fields of sections 4.2 and 4.5, with the scope value;
  - CellPatcher: `context_bounds`;
  - MorphoFeature: a window source (`read(fov, plane, bounds, channels)`: an in-memory slice now,
    `read_window` later) and work units over catalogue patches;
  - fiberfeatures: its margin from its own settings (largest filter, nematic sigma, correlation
    distance, pixel size; two-channel alignment included), a windowed entry point (pipeline on the
    window, existing `_single`/`_paired` on the interior), and RGB conversion per window through the
    existing `ConvertedChannels`.
- **Tests:**
  - a windowed patch equals the pipeline run on the hand-cut patch plus margin;
  - identical results for 1/2/N workers and any completion order;
  - windowed RGB conversion is bitwise equal to the same slice of the whole conversion;
  - the default route is bitwise unchanged.
- **Not in this slice:**
  - RGB-specific tiling;
  - tiling inside fiberfeatures or the bridges;
  - reader changes;
  - fields outside the Spec;
  - streamed output;
  - object tiling.

## 8. Owner decisions (14 November 2026) and review notes

| Decision | Taken | Review note | Resolution |
| --- | --- | --- | --- |
| Mode granularity | per run | split into a scientific policy and per-source execution | run-wide scientific request; per-source access and per-unit execution plans (section 4.1) |
| Fingerprint | one SHA-256 per file | agree; optional chunk index | as taken (section 4.9) |
| Pyramid level | default level 0 | no inferred default | a declared run policy resolving to a recorded level per source (section 4.2) |
| Margin | exact footprint | agree; explicit edge rule | as taken, plus provider border semantics (section 4.5) |
| Windows | exact | agree | as taken |
| TIFF layouts | tiled + splittable strips | agree | as taken |
| Output | part file per tile + ledger | Parquet/Arrow + transaction manifest | adopted (section 4.9) |
| Workers | threads first, benchmark | pluggable executor, separate handles | adopted (section 5) |
| First slice | per_patch; amount computed and flagged; grid only | n/a | section 7 |

## 9. Acceptance gates (from the independent review)

- **G1 Full-pipeline tile parity** is specified per stage. fiberfeatures percentile stages are fitted
  globally or stay `whole_only` / `per_patch`.
- **G2 Global observation identity**, including series and object labels across windows.
- **G3 Typed coordinates**, with tested conversions to the bridge frame.
- **G4 Bridge binding contract** before any claim of placement on a slide.
- **G5 Resource estimates per stage** and admission control.
- **G6 Reduction reproducibility:** bins, accumulators, partition-independent order, tolerances.
- **G7 Sampling, measurement and context regions** kept separate.
- **G8 Storage layout never changes scientific capability.**
- **G9 Series, level, transform and calibration** are scientific selections, recorded.

**Cannot be known until executed:**
- reader parity on real SVS/NDPI/SCN and pyramidal fluorescence;
- thread safety and throughput;
- CPU/GPU numerical parity;
- peak RAM/VRAM;
- resume after interruption;
- full-slide performance.

Each is a gate with a benchmark, not an assumption.
