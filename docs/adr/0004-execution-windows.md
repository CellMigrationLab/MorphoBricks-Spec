# ADR 0004: execution windows, typed coordinates and the patch catalogue (first slice)

- **Status:** **Accepted** (owner, 14 November 2026). EW11 (window histograms) is an **accepted owner
  decision of 15 November 2026, not implemented**: no brick has code for it yet, and its two steps
  land in the order stated in [its section](#window-histograms-ew11). The owner decisions it encodes are recorded in
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
| EW11 | **Window histograms** (amendment, owner, 15 November 2026; not implemented). A windowed run stores histograms of the **patch interior** (never the margin) in a new table, `window_histograms.csv`, whose type, schema (version 1) and reader belong to the normalization brick ([below](#window-histograms-ew11)). **Step 1:** one histogram per source channel read for the patch, computed by MorphoFeature from the window pixels it already holds, binned with the plane's recorded binning. **Step 2:** derived-image histograms with fixed per-preset limits, the conversion identity (`conversion_id`) and the scaling applied, delivered by the provider in a new typed, versioned payload. A preset without a fixed range gets no derived histogram, with a recorded reason. | Recomputing from the source later (a second full read); histograms of the whole window (margins overlap, so counts double); extending `plane_histograms.csv` (one row per plane, one bin count, one dtype); reusing `PlaneHistogram`, whose limits must enclose the observed extrema; not storing them (the per-window scaling is not reproducible downstream). |

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

## Window histograms (EW11)

Owner decisions of 15 November 2026, **not implemented**. Code read for this section:
morphobricks-normalization `b8aa65b` (`v0.6.1`), morphobricks-preprocessing `1195038`, MorphoFeature
`b6a711e`, fiberfeatures `752b1dd`. Pixels counted: the **patch interior** only (the window record's
`local_interior`, EW4), which is also where `patch_window` takes its percentiles (EW7). Only windowed
runs write anything here; the `whole_plane` route is unchanged, bitwise (gate below).

### Two steps

| Step | What | Computed by | Delivered by |
| --- | --- | --- | --- |
| 1 (first) | One histogram per **source channel** read for the patch: a fluorescence channel, or each of the `R`, `G`, `B` of an RGB unit | MorphoFeature, from the window pixels it already holds (no extra read), with the normalization brick's binning | MorphoFeature writes `window_histograms.csv` |
| 2 (after step 1) | One histogram per **derived image** (the scalar image of a stain preset, for example `Eosin` from `he_eosin`), its `conversion_id`, its pixel-dependent diagnostics, and the **scaling applied** to each windowed feature column | The provider, which makes the derived image (MorphoFeature never converts an RGB unit, `rgb_inputs.py`), with the normalization brick's functions | A new typed, versioned provider payload (`window_report`, below), validated and written by MorphoFeature |

A derived image cannot be rebuilt from the `R`, `G`, `B` histograms (the conversions mix the three
channels nonlinearly), which is why step 2 needs the provider.

### The window histogram type (normalization)

`WindowHistogram` is a new type of the normalization brick, separate from `PlaneHistogram`.
`PlaneHistogram` and its invariants (contract §1.2.2, `integrity.py`) are **not changed or
weakened**: they require `pixel_min ≤ binning_min ≤ binning_max ≤ pixel_max` and a binning limit
equal to its extremum exactly when its tail is empty, which a patch binned with limits inherited from
its plane does not satisfy (its own extrema usually lie inside the plane's limits).

A `WindowHistogram` has a **reference binning**, fixed before any patch pixel is seen, and
**observed values**, measured on the interior:

| Field | Meaning |
| --- | --- |
| `reference` | `kind` (`plane_histogram` or `output_histogram_spec`), `bin_count`, `binning_min`, `binning_max`, and the identity of where they come from (below) |
| `total_pixel_count` | Interior pixels: `(y1 − y0) · (x1 − x0)` of the patch `bounds` |
| `valid_pixel_count` | Finite interior pixels |
| `nonfinite_pixel_count` | NaN, `+inf` and `−inf` interior pixels; `total = valid + nonfinite` exactly |
| `pixel_min`, `pixel_max` | Observed finite extrema of the interior; blank without valid pixels |
| `counts` | int64, `bin_count` non-negative values: valid pixels with `binning_min ≤ x ≤ binning_max`, binned by contract §1.2.2 with the reference limits |
| `underflow`, `overflow` | Valid pixels `x < binning_min` and `x > binning_max`: count, mean and population standard deviation, each the float64 nearest its exact value (the centred moments of §1.4, N65, computed by the same code) |

**Invariants**, checked when a `WindowHistogram` is made, computed or read (a violation is refused
with `ValueError`, never clipped or filled in):

- `counts` is a one-dimensional int64 array of `bin_count` non-negative values; the three pixel
  counts are whole numbers from 0 to 2**63 − 1 with `valid + nonfinite = total`, and the bins and
  tails hold exactly the valid pixels (an exact integer sum).
- The reference limits are both finite with `binning_min ≤ binning_max`, or both blank. They are
  blank only for a source channel whose plane has no finite pixels (the plane's limits are blank,
  §1.2.2); then `valid_pixel_count` is 0.
- Without valid pixels (an all-nonfinite patch, or a patch of an all-nonfinite plane): `pixel_min`
  and `pixel_max` blank, every count 0, both tails empty. The reference limits are kept (they
  describe the plane or preset, not the patch). The row is a measured histogram, never a missing one.
- **Empty tail:** count 0, mean `0.0` and std `0.0` exactly (`-0.0` is written `0.0`). A populated
  tail has a count of 1 or more; its mean lies in `[pixel_min, binning_min]` (underflow) or
  `[binning_max, pixel_max]` (overflow) and its std is at most half that range, with §1.2.2's slack.
- With valid pixels: `pixel_min ≤ pixel_max`, both finite; the underflow is non-empty exactly when
  `pixel_min < binning_min`, the overflow exactly when `pixel_max > binning_max`. **No ordering
  between the observed extrema and the reference limits is required otherwise**: `pixel_min >
  binning_min` and `pixel_max < binning_max` are normal.
- Nonfinite pixels are never in a bin or a tail, and a value outside the reference limits is never
  put in an end bin: the float rule "clipped to `n − 1`" of §1.2.2 applies only to `x = binning_max`.

The normalization brick provides `window_histogram(pixels, reference)` (one interior array and one
reference binning) and reuses **only its existing binning maths**: the bin of a pixel, the tail
moments and the integer/float rules are those of `compute_block_histogram`, the same code, so a pixel
falls in the same bin in a window as in its plane, bit for bit.

### Canonical JSON (hashes and parameter cells)

Every hash and JSON cell of EW11 (`conversion_id`, the spec hash, `parameters`) uses one canonical
form, implemented once in the normalization brick (`canonical_json`) and tested:

- Values are converted first: a NumPy integer to a Python `int`, a NumPy float (any width) to a
  Python `float` (float64) by value, a NumPy bool to `bool`; tuples and arrays to lists (in order);
  `-0.0` to `0.0`; `None` to `null`. A bool is never written as a number, nor a number as a bool.
  NaN, `±inf`, bytes, sets, a mapping key that is not a `str`, and any other type are refused.
- Then the JSON text: keys sorted (Python string order), separators `,` and `:`, no whitespace,
  ASCII only (`\uXXXX` escapes), integers as decimal integers, floats as Python `repr` of the float
  (shortest round trip; `1.0`, never `1`).
- A hash is the lowercase hex SHA-256 of the UTF-8 bytes of that text.

### Step 1: source channels

**Reference binning.** The plane's row in `plane_histograms.csv` (schema version 5, contract §6.2)
written by the preprocessing brick for the channel: `bin_count`, `Histogram_BinningMin_<ID>`,
`Histogram_BinningMax_<ID>`, under the run's `HistogramSettings` (`minmax` or `robust`, §1.4).
The reference identity is the `plane_id`, the channel ID, the table's SHA-256 (`csv_sha256` of the
preprocessing `run_manifest.json`) and the histogram settings. Consequences:

- An integer plane with `W ≤ n` values is exact, and bin `i` holds the value `binning_min + i`. An
  8-bit channel (an `R`, `G` or `B` of an RGB unit) with the default 256 bins therefore **inherits
  the plane's `binning_min`**: when the plane's minimum is 12, bin 0 holds 12, not 0. Window
  histograms never re-anchor to 0.
- With the robust range, a patch's tails hold its pixels beyond the **plane's** robust limits; a
  patch without such pixels has empty tails although the plane has tails.
- The window's dtype must equal the plane row's `dtype`; the bin count is the plane's, the same for
  every plane of a preprocessing run (§1.2.1).

**No guessed limits.** A plane without a row in the referenced `plane_histograms.csv` (no
preprocessing statistics), or whose row cannot be shown to describe the pixels MorphoFeature reads
(another source file, plane or dtype; a projected or converted copy on one side only; a table whose
SHA-256 differs from the one recorded when the run was planned), gets **no** source-channel histogram:
its rows are `not_measured` with the reason `no_plane_histogram` or `plane_histogram_mismatch`. It is
never binned with limits taken from the patch, from the dtype or from another plane. The features run
as before.

### Exact-sum conformance (step 1)

For one plane `P`, one source channel `c` and one patch set `S`, the window histograms of `S` sum
**exactly** to `P`'s histogram of `c` only when all of these hold:

1. **One patch set, one plane, one image**: every row has the same `plane_id`, `patch_set` and
   `image`; histograms of different patch sets are never added together.
2. **Exact cover**: the interiors cover every pixel of the plane exactly once, checked from the
   catalogue (EW3) and the rows, never assumed from the mode: every patch's global `bounds` lies in
   `[0, H) × [0, W)`, the bounds are pairwise disjoint, their areas sum to `H · W`, and each row's
   `local_interior` equals its `bounds` minus its window `origin`.
3. **Same binning**: every row has the same reference (bin count, limits, plane_id, table SHA-256,
   settings), equal to `P`'s row.
4. **Every patch measured**: every catalogue patch of `S` on `P` has a `measured` row for `c`.

Then, exactly: the bin counts, `valid_pixel_count`, `total_pixel_count`, `nonfinite_pixel_count`
(`total − valid` of `P`), the underflow and overflow counts, the smallest `pixel_min` and the largest
`pixel_max` (the plane's `Intensity_MinIntensity_<ID>` and `Intensity_MaxIntensity_<ID>`).

**Tail moments.** Pooled as in §1.4 (count-weighted mean, centred terms for the std, correctly
rounded sums) and compared with `P`'s tail as follows. If `P`'s tail is empty, every window's tail
must be empty (count 0, mean and std exactly `0.0`); nothing else is compared. If it is populated,
the pooled count must equal `P`'s exactly, and the pooled mean and std must each satisfy
`abs(pooled − p) ≤ 4 * math.ulp(max(abs(a), abs(b))) + 1e-12 * abs(p)`, in Python float64
(`math.ulp`), where `p` is `P`'s value and `[a, b]` is `P`'s tail range (`[pixel_min, binning_min]`
or `[binning_max, pixel_max]`). Each window's moments are rounded once, as the plane's are, so only
the pooled moments can differ, by these roundings.

When a condition fails, **no equality is claimed**, and what may be claimed instead is:

| Case | What may be claimed |
| --- | --- |
| A grid without partial edge patches (`include_partial = false`: the edge strips are not in the catalogue, `patch_sets.py:304–310`) | The sum is the histogram of the covered region (interiors disjoint); the covered pixel count is reported. It is never compared with or used as `P`'s histogram. |
| Several patch sets on one plane | Each set on its own, as above. Pooling across sets is refused (they may overlap). |
| Patches not measured (no eligible request, so no window unit; or a `not_measured` row) | The sum over the measured rows is the histogram of their region, with the number of missing patches reported. |
| Overlapping interiors (CellPatcher's `flush` grid edges, random or cell patches, `whole_fov` squares; outside this slice, which is grid-only) | Nothing: the pooling function refuses rows whose bounds overlap. |

### Step 2: derived images

**Fixed binning per preset.** No whole derived plane is ever seen, so the binning is fixed in advance
and is deterministic. The normalization brick provides a tested `output_histogram_spec(preset, *,
white=None, stain_vectors=None, polarizer=None)`, needing no pixel (like `check_options`, which it
runs first), returning either an `OutputHistogramSpec` or `NoFixedRange("preset_has_no_fixed_range")`.
For every bounded family:

- `bin_count = 1024`, the same for every bounded preset and option. It is recorded in every row, and
  changing it is a change of `spec_version` and of the `window_histograms.csv` schema.
- `analytic_min`, `analytic_max`: the family's analytic bounds of the output for every 8-bit input
  under the given options (table below), as float64.
- `tolerance = 4 * float(numpy.spacing(numpy.float32(m)))` with `m = max(abs(analytic_min),
  abs(analytic_max))`: four float32 units in the last place at the bound's magnitude, because the
  derived image is float32 and its rounding at the bound is up to half a float32 unit, so a value
  that is within the analytic bounds before rounding always lies inside the widened limits.
- `binning_min = analytic_min − tolerance`, `binning_max = analytic_max + tolerance` (float64).
- Values below `binning_min` or above `binning_max` go to the explicit underflow and overflow
  (count and moments), never to an end bin. The bins follow the float rule of §1.2.2 with these
  limits.

**Spec identity.** An `OutputHistogramSpec` has the fields `spec_version` (1), `preset`,
`preset_version`, `conversion_id`, `bin_count`, `analytic_min`, `analytic_max`, `tolerance`,
`binning_min`, `binning_max`; its hash (`spec_sha256`) is the SHA-256 of its canonical JSON (above)
and is stored in every derived row. This is not the preset's `fixed_range` (a scaling range, `None`
for every preset in `stain_presets.py` today), which stays as it is.

| Family (presets) | Analytic bounds |
| --- | --- |
| `custom_od` (`psr_brightfield`, `he_custom`, `trichrome_custom`, user or default vectors) | Per channel `OD ∈ [lo_j, hi_j] = [log10(white_j/255), log10(white_j/1)]` (`I` floored at 1). The target concentration is a linear map of the OD with the target column `a` of `inv(M)`, so the bound is **sign-aware**: `Σ_j min(a_j·lo_j, a_j·hi_j)` to `Σ_j max(a_j·lo_j, a_j·hi_j)`. Negative concentrations are kept (§3.4), so the lower bound can be negative. |
| `fixed_deconvolution` (`he_eosin`, `he_hematoxylin`, `trichrome_blue`; scikit-image `separate_stains`) | Per channel `log(max(I/255, 1e-6)) / log(1e-6) ∈ [0, 1]`; the component is that vector times the matrix column, then set to 0 where negative, so `[0, Σ_j max(0, m_jk)]`, from the pinned scikit-image version's matrix. |
| `cielab` (`lab_a`, `trichrome_green`) | The extremes of `rgb2lab(...)[..., 1]` over all 2**24 8-bit colours at the pinned scikit-image version (exhaustive), negated for `trichrome_green`; the white rescale keeps the input 8-bit, so the same bounds hold with `white`. |
| `luminance` (`luminance_inverted`, `psr_polarized`) | `[0, 1]` (weights 0.2125, 0.7154, 0.0721 on values in `[0, 1]`). |
| `passthrough` (`fluorescence`, `shg`) | None: `NoFixedRange("preset_has_no_fixed_range")`. |

A preset the brick cannot bound (a future family, or options for which it states no bound) also
returns `NoFixedRange("preset_has_no_fixed_range")`, the only reason of schema 1. Then (owner
ruling 3) **no derived window histogram and no `conversion_id`** are written for it in
`window_histograms.csv`: its row is `not_measured` with that reason and an empty `conversion_id`;
the features still run, and the patch's source-channel histograms are still written. A derived image
is never binned with guessed limits and never clipped into end bins. The normalization tests feed
each bounded family its extreme 8-bit inputs (all 2**24 colours for `cielab` and `luminance`) and
require empty tails. The float32-sized tolerance above covers the derived image's float32 rounding,
so a non-empty tail in these tests is a defect (a wrong analytic bound or conversion), not rounding.

**What is counted.** **Every finite derived pixel** of the interior, with nothing excluded (owner
ruling 2): `ScalarResult.exclusion` is a continuous image (the exclusion stain's concentration), not
a mask, and no exclusion threshold exists in this amendment. A future rule would be its own
versioned option, never a default. `total = finite + nonfinite` (today `ScalarResult.image` is
finite, so `nonfinite` is 0, but the type does not assume it).

**Conversion identity.** `conversion_id(preset, *, white=None, stain_vectors=None, polarizer=None)`,
in the normalization brick, needs no pixel and is defined for the bounded (RGB) presets only. It is
the SHA-256 of the canonical JSON of exactly these keys, the **fully resolved, stable** parameters:

`conversion_id_version` (1), `preset`, `preset_version`, `method`, `matrix`, `target_component`,
`exclusion_component`, `inverted`, `colour_space`, `white` (three floats, or `null` when not given),
`white_rescale`, `stain_names`, `stain_matrix` (the unit rows actually used, default or user),
`residual_completed`, `od_definition`, `polarizer`, `normalization_version`, `skimage_version`
(`null` when scikit-image is not called) and `numpy_version`.

`input_dtype` is not a key: every preset that has a `conversion_id` takes `uint8` RGB only
(`stain.py`, which refuses any other dtype), so it would never vary. The pixel-dependent
diagnostics (`zero_fraction`, `floored_fraction`, `negative_fraction`, `above_white_fraction`,
`white_clipped_fraction`, `float32_exact`), descriptive fields (`hints`, citations) and `axes`
(`YXC` and `CYX` give bitwise identical outputs) are not keys either. Required tests: two
conversions with identical settings on images with different fractions give the same id; changing
any one key (white, a vector, the polarizer, the preset version, the scikit-image version) gives a
different id; the id from the options equals the id rebuilt from any `ScalarResult.provenance` of
the same call. Pooling refuses rows of different `conversion_id`s or `spec_sha256`s.

**Diagnostics per patch.** Stored per patch as **counts over the interior** (`zero_count`,
`floored_count`, `negative_count`, `above_white_count`, `white_clipped_count`: each the numerator of
the provenance's fraction, with `total_pixel_count` as denominator), so they add up exactly across
patches; a count is blank where the preset's method does not define it. The normalization brick
computes them with `conversion_diagnostic_counts(pixels, *, axes, preset, white=None,
stain_vectors=None, polarizer=None)` on the interior's RGB pixels, with the provenance's definitions;
the provider never reimplements them. They are separate from the conversion identity.

### Step 2: the scaling applied

For every windowed feature column (`scaling_scope = patch_window`, EW7, EW8) and every patch it is
requested on, the provider reports each scaling **stage** applied on the way to that column, in
order. fiberfeatures at `752b1dd` has, for example:

- `robust_normalize` (`preprocessing.py`, applied twice by `preprocess_image`): the image as
  float32; `lo, hi = np.percentile(values, [1.0, 99.0])` (NumPy's default `linear` method, float64
  results); if `hi ≤ lo`, `hi` is replaced by the maximum; then **clip to `[lo, hi]` first**, then
  `(clipped − lo) / (hi − lo + 1e-8)`, computed in float64 and stored as float32;
- `_normalize_map_torch` (`tensor_ops.py`, `ridge_support` and the other maps per scale): float32
  tensors, the 1st and 99th linear quantiles, the same maximum fallback, then `(x − lo) / (hi − lo +
  1e-8)` **then clamp to `[0, 1]`**, in float32;
- `local_contrast_normalize` (opt-in): `p1` (1st percentile), the region mean, `floor`, `sigma`.

So the record states what was really done, not the declared settings. One entry per (plane, patch
set, patch, image, `conversion_id`, column, stage):

| Field | Meaning |
| --- | --- |
| `stage_index`, `stage` | Position in the column's chain (from 0) and the provider's stage name (`robust_normalize_1`, …) |
| `state`, `reason` | `measured`; or `not_measured` with a reason (below) and every other field blank |
| `transform` | `none` (the column uses unscaled values at this point; written only for a measured patch), `percentile_range`, `fixed_range`, `local_contrast` or `constant` (the degenerate branch: `hi ≤ lo` after the fallback, output 1 where `lo > 0`, else 0) |
| `quantile_method`, `low_quantile`, `high_quantile`, `low_value`, `high_value`, `upper_fallback` | `percentile_range`: the method (`linear`, `inverted_cdf`, …), the quantiles in percent, the values **actually used** (after any fallback) and whether the maximum replaced the upper value (`true`/`false`) |
| `offset`, `scale` | The applied linear map `y = (x − offset) / scale`, exactly as used (fiberfeatures: `offset = lo`, `scale = hi − lo + 1e-8`) |
| `arithmetic_dtype`, `output_dtype` | The dtype the map is computed in and the dtype stored (`float64`/`float32` for `robust_normalize`; `float32`/`float32` for the torch maps) |
| `clip_order`, `clip_low`, `clip_high` | `none`, `clip_then_scale` (limits in input units: `lo`, `hi`) or `scale_then_clip` (limits in output units: `0.0`, `1.0`) |
| `parameters` | Canonical JSON of the stage's other numbers (`local_contrast`: `p1`, `region_mean`, `floor`, `sigma`); `{}` when there are none |

**Canonical cells.** Numbers are float64 `repr`; blank means "not applicable to this transform".
`transform = none`: every numeric cell blank, `clip_order = none`, `parameters = {}`. `constant`:
`low_value`, `high_value` as used, `offset`, `scale` blank, `clip_order = none`. A stage the provider
does not apply to a column is not written.

**Unmeasured columns.** `not_measured` follows the provider output that MorphoFeature already
validates (`patch_output.py`): reason `patch_not_measured` when the provider lists the patch in its
manifest's `patches_not_measured` (its own reason is kept in `provider_reason`), `valid_empty` when the
window's output has `status = valid_empty` (zero rows), `no_provider_report` when the provider does
not declare `window_report`. **A `not_measured` column never has `transform = none`**, and a measured
row of the provider's table must have `measured` stages; MorphoFeature refuses any other combination
as a provider output error.

### Step 2: the provider payload (`window_report`, version 1)

A provider declares it with an optional key of its `windowed_execution` manifest field,
`window_report: {version: 1}` (EW10 stays additive; a provider without it is unchanged). For each
windowed call (one patch, EW4), its output gains the key `window_report`: `{version, derived: [...],
scaling: [...]}`, one `derived` entry per derived image the call made (`image`, `preset`,
`preset_version`, `conversion_id` and `spec_sha256` when bounded, then either the `WindowHistogram`
and the diagnostic counts, or `not_measured` with a reason) and the `scaling` entries above.
MorphoFeature refuses, as a provider output error: another version; an entry for another patch,
image or column; a missing entry; a `conversion_id` or spec that differs from what it recomputes from
the request's preset and options with the pinned normalization brick; a histogram that breaks the
invariants. Today's `check_patch_output` (`patch_output.py:201–253`) reads only `status`, `tables`,
`manifest` and `applicability`, and `PatchOutput` has no field for this: step 2 adds the field and
its validation. Until then no scaling or derived histogram is recorded.

**Two providers, one derived image.** When two providers report a derived histogram for the same key
`(plane_id, patch_set, patch_id, image, conversion_id)`:

- if their entries are equal in full (reference and spec hash, every count, extrema, both tails,
  `counts`, every diagnostic count), one row is written, `measured`;
- otherwise the row is `not_measured` with the reason `duplicate_report_disagrees`, and the run
  record's `window_histogram_errors` lists the key, the providers and the first differing field.
  Features are unaffected; the histogram write of every other key goes on.

Which providers reported is recorded per row, apart from the measurement, so a provider that reported
nothing is never hidden by another's measurement: `providers_reporting` (providers whose entry is in
the row, `;`-separated, sorted) and `providers_not_reporting` (providers with a request using that
derived image that sent no histogram: no `window_report`, or `not_measured`; same format). A derived
row with no reporting provider is `not_measured` with `no_provider_report` (or the providers' common
reason, `preset_has_no_fixed_range` or `patch_not_measured`).

### The `window_histograms.csv` table, schema 1 (normalization)

A new table with its own schema, owned by the normalization brick (type, writer, reader), **not an
extension of `plane_histograms.csv`** (schema 5 has a unique `plane_id` per row, one `bin_count` and
one `dtype` per table). MorphoFeature writes it next to the patch catalogue (EW3) through the brick's
writer. Common format of §6.1 (UTF-8, comma-separated, one header row, floats at full precision with
`repr`, blanks for missing values, temporary file then replace).

- **File:** `window_histograms.csv`.
- **Row:** one per plane x patch x image, key `(plane_id, patch_set, patch_id, image,
  conversion_id)`, unique (two derived images of one name but different options differ by
  `conversion_id`; it is empty for source channels and for `passthrough` rows).
- **Rows written:** for every catalogue patch of a set with a windowed request on the plane, one row
  per source channel read by any unit of that set on the plane, and (step 2) one per derived image of
  its requests; a patch with no window unit gets `not_measured` rows.
- **Order:** planes in the run's order, patch sets in the order they were cut, patches in catalogue
  (CellPatcher) order, then source channels before derived images, each in sorted order (Python
  string order, §6.1), then `conversion_id`. Serial and pooled runs give the same bytes (EW9).

**Header, complete and in this order** (61 columns):

```text
schema_version,
position_id,image_file,z,t,condition,biological_repeat,technical_repeat,source_relative_path,plane_id,
patch_set,patch_id,catalogue_version,
bounds_y0,bounds_y1,bounds_x0,bounds_x1,
origin_y,origin_x,interior_y0,interior_y1,interior_x0,interior_x1,
image,image_kind,dtype,
status,reason,providers_reporting,providers_not_reporting,
reference_kind,reference_sha256,histogram_range,
preset,preset_version,conversion_id,spec_version,spec_sha256,
bin_count,binning_min,binning_max,analytic_min,analytic_max,tolerance,
total_pixel_count,valid_pixel_count,nonfinite_pixel_count,pixel_min,pixel_max,
underflow_count,underflow_mean,underflow_std,overflow_count,overflow_mean,overflow_std,
counts,
zero_count,floored_count,negative_count,above_white_count,white_clipped_count
```

(one header line in the file; broken here for reading).

| Columns | Content |
| --- | --- |
| `schema_version` | `1`, its own sequence |
| `position_id` … `plane_id` | The plane columns of §6.1, same names and order |
| `patch_set`, `patch_id`, `catalogue_version` | Patch identity (EW3) |
| `bounds_*` | Global `bounds`, `pixel_edge`, plane frame: the tuple `(y0, y1, x0, x1)` as four integers |
| `origin_*`, `interior_*` | Window `origin` and `local_interior` (`pixel_edge`, window-local), integers; the reader checks `interior = bounds − origin` |
| `image`, `image_kind`, `dtype` | Channel ID or derived image name; `source_channel` or `derived`; the plane's dtype, or `float32` for a derived image |
| `status`, `reason` | `measured` (reason empty) or `not_measured` with a reason of the frozen list below |
| `providers_reporting`, `providers_not_reporting` | Derived rows (above); empty for source rows |
| `reference_kind`, `reference_sha256`, `histogram_range` | `plane_histogram`, the SHA-256 of `plane_histograms.csv`, `minmax` or `robust`; or `output_histogram_spec`, the `spec_sha256`, empty |
| `preset` … `spec_sha256` | Derived rows; empty for source rows; `conversion_id`, `spec_version`, `spec_sha256` also empty for `passthrough` |
| `bin_count`, `binning_min`, `binning_max` | Reference binning, per row (a source channel's and a derived image's bin counts differ) |
| `analytic_min`, `analytic_max`, `tolerance` | Derived rows: from the spec; empty for source rows |
| `total_pixel_count` … `pixel_max` | Observed values |
| `underflow_*`, `overflow_*` | Tails; `0`, `0.0`, `0.0` when empty |
| `counts` | Sparse bin counts (grammar below) |
| `zero_count` … `white_clipped_count` | Derived diagnostics; empty where not defined and for source rows |

**Sparse `counts` grammar.** Either the literal `empty` (no pixel in a bin), or one or more pairs
`index:count` joined by `;`, where `index` is `0` or a decimal integer without a leading zero, the
indices are strictly increasing and each lies in `[0, bin_count)`, and `count` is a positive decimal
integer without a leading zero (zero bins are not written). No spaces, signs or other characters.
The reader checks that the counts sum to `valid − underflow_count − overflow_count`.

**Reasons, frozen for schema 1.** `no_window_unit`, `no_plane_histogram`, `plane_histogram_mismatch`
(source rows); `preset_has_no_fixed_range`, `patch_not_measured`, `no_provider_report`,
`duplicate_report_disagrees` (derived rows). A new reason is a schema revision.

A `not_measured` row has its identity, image, status, reason and provider columns, every other cell
empty; the reader refuses a value there, so a zero histogram never stands for a missing one. A
measured row's cells are checked against the invariants above. The reader refuses another
`schema_version`, a missing, extra or reordered column, an unknown reason or `image_kind`, a
duplicate key, and a `plane_histograms.csv` given in its place; it never converts. If a measurement
fails (other than with a listed reason), the writer writes nothing, as for `plane_histograms.csv`
(§6.2).

### The `window_scaling.csv` table, schema 1 (MorphoFeature)

Written by MorphoFeature next to `window_histograms.csv`, from the `scaling` entries. One row per
entry (key: plane, patch set, patch, image, `conversion_id`, column, `stage_index`); a
`not_measured` column has one row with `stage_index` 0 and `stage` empty. Order: the row order of
`window_histograms.csv` up to the image, then `conversion_id`, column name (Python string order),
`stage_index`. Header, complete and in this order (40 columns):

```text
schema_version,
position_id,image_file,z,t,condition,biological_repeat,technical_repeat,source_relative_path,plane_id,
patch_set,patch_id,catalogue_version,
image,image_kind,preset,preset_version,conversion_id,
column,provider,stage_index,stage,
state,reason,provider_reason,
transform,quantile_method,low_quantile,high_quantile,low_value,high_value,upper_fallback,
offset,scale,arithmetic_dtype,output_dtype,
clip_order,clip_low,clip_high,
parameters
```

`schema_version` is `1`. Reasons, frozen for schema 1: `patch_not_measured`, `valid_empty`,
`no_provider_report`. The reader refuses another version, header or reason, and a `not_measured`
row with any transform cell filled.

### Conformance matrix

Tests the implementing PRs add (normalization for the type, spec, `canonical_json` and readers;
MorphoFeature for the writers and the run). They are test data of those bricks, not files under this
repository's `fixtures/` (which holds `experiment-v1.md` data only):

| Case | Expected |
| --- | --- |
| Clipped grid (`include_partial = true`, `clipped`), one set, all patches measured | Exact equality with the plane row; tail moments within the stated tolerance |
| Grid without partial edges | Coverage below `H · W` reported; no equality claimed; the pooling function says so |
| Two patch sets on one plane | Each set conforms on its own; pooling across sets refused |
| A catalogue patch without a window unit | `not_measured`, `no_window_unit`; equality refused, partial sum allowed |
| Overlapping bounds | Pooling refused |
| All-NaN float plane | Plane limits blank; every patch: `valid` 0, `nonfinite` = area, reference blank, counts `empty`; the sums still equal the plane's |
| All-NaN patch in a plane with finite pixels | `valid` 0, observed extrema blank, reference limits kept |
| `+inf` and `−inf` pixels | In `nonfinite_pixel_count`, never in a bin or a tail |
| Robust range with hot pixels | Tail counts sum exactly; a patch without tail pixels has empty tails; `pixel_min > binning_min` accepted; an empty plane tail compared by the empty-tail rule |
| 8-bit `R`, `G`, `B` with a plane minimum above 0 | Bin `i` holds `binning_min + i`; exact |
| Constant plane | Every valid pixel in bin 0, in every patch |
| Plane without a `plane_histograms.csv` row, or a SHA-256 mismatch | `not_measured` with the reason; features unchanged |
| Each bounded family at its extreme 8-bit inputs | `bin_count` 1024, limits `analytic ± tolerance`, empty tails |
| A derived value outside the widened limits (injected) | Counted in the tail, never an end bin |
| `passthrough` preset | Derived row `not_measured`, `preset_has_no_fixed_range`, `conversion_id` empty; features and source rows present |
| `conversion_id`: same settings, different fractions / changed settings | Same id / different id |
| `canonical_json`: NumPy scalars, `-0.0`, `None`, NaN | Same text as the Python values; `0.0`; `null`; NaN refused |
| Mixed `conversion_id`s or `spec_sha256`s | Pooling refused |
| Diagnostics pooled from the patches of a clipped grid | Each count equals `conversion_diagnostic_counts` on the whole plane |
| Two providers report one derived image, equal | One `measured` row, both in `providers_reporting` |
| Two providers report one derived image, different | `not_measured`, `duplicate_report_disagrees`; error recorded; features unchanged |
| One provider reports, the other has no `window_report` | `measured`; the other in `providers_not_reporting` |
| A valid-empty window | Scaling rows `not_measured`, `valid_empty`; no `transform = none` |
| A patch in `patches_not_measured` | Scaling rows `not_measured`, `patch_not_measured`, the provider's reason kept |
| `robust_normalize` whose 99th percentile equals the 1st (sparse structure) | `upper_fallback = true`, `high_value` the maximum, not the declared 99th percentile |
| Sparse `counts` with a leading zero, a zero count, a repeated or decreasing index, an index ≥ `bin_count` | Refused by the reader |
| A table of `schema_version` 0 or 2, or a `plane_histograms.csv`, read as either table | Refused |
| Serial vs pooled run | Identical bytes of both tables |

### Order, pins and the regression gate

Implementation order (owner ruling 1):

1. normalization: `WindowHistogram`, its invariants, `window_histogram()`, `canonical_json`, the
   pooling with the exact-cover check, the `window_histograms.csv` writer and reader (schema 1);
   released with a tag;
2. MorphoFeature: the step-1 writer, pinned to that tag, with the exact-sum test against
   `plane_histograms.csv`;
3. normalization: `output_histogram_spec()`, `conversion_id()` and `conversion_diagnostic_counts()`,
   each with its tests (the bounds per family, the id tests, the diagnostics pooled from patches
   equal to the whole plane's); tagged;
4. MorphoFeature: the `window_report` payload protocol (version 1), the duplicate rule and
   `window_scaling.csv`;
5. fiberfeatures: reports the payload, pinned to the normalization tag of step 3;
6. MorphoFeature: the integration test with fiberfeatures.

Dependencies point one way: only the importing, downstream brick pins a tag of the brick it imports
(MorphoFeature and fiberfeatures pin normalization, as MorphoFeature's `pyproject.toml` pins
`v0.6.1` today; MorphoFeature pins fiberfeatures for the integration test). **normalization never
depends on MorphoFeature** or on a provider. A reader refuses any other schema version; a test reads
a table written with another version and expects the refusal.

**Regression gate (kept explicit).** A run whose requests are all `whole_plane` writes no
`window_histograms.csv` and no `window_scaling.csv` and is **bitwise identical** to the same run
before EW11 (tables, run record, catalogue). In a windowed run, the provider tables are bitwise
identical with and without the histograms being computed: they are a side output and change no
feature value.

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
