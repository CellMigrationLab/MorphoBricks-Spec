# ADR 0004: execution windows, typed coordinates and the patch catalogue (first slice)

- **Status:** **Accepted** (owner, 14 November 2026). EW11 (window histograms) is an **accepted owner
  decision of 15 November 2026, not implemented**: no brick has code for it yet, and its two steps
  land in the order stated in [its section](#window-histograms-ew11). Owner answers of 15 November 2026 (evening) on its open choices: a missing or mismatched plane histogram gives `not_measured` rows and the run continues; `conversion_id` covers the resolved settings and the scikit-image version only (not numpy or normalization), with an unset white resolved to the default; one `window_scaling.csv` row per column and scaling step; exact tail sums stored beside mean and std (**withdrawn by the owner, 16 November 2026**: no tail sums are stored, see [tail moments](#exact-sum-conformance-step-1)); sparse `counts`; a disagreeing duplicate report makes the row `not_measured`; diagnostics stored as counts. The owner decisions it encodes are recorded in
  [the one-route design](../design/one-route.md) (section 7 and the decisions table; the design itself
  stays proposed until its gates are met). Specification only: no fixture, golden or validator of `experiment-v1.md` changes
  (`python -I tools/audit/refval.py fixtures .` unchanged). The coordinate conversions are executable
  in `tools/execution_frames.py`, with their cases in `tools/test_execution_frames.py`; EW11's canonical
  JSON, conversion identity, histogram spec goldens and duplicate comparison in
  `tools/window_histogram_spec.py`, with their cases in `tools/test_window_histogram_spec.py`.
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

1. **One patch set, one plane, one image**: every row has the same `plane_id`, `patch_set`,
   `image_kind` and `image`; histograms of different patch sets are never added together.
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

**Tail moments.** Only the tail **counts** are exact. No tail sum is stored and **no bitwise
equality of pooled tail sums or moments is claimed** (owner, 16 Nov, withdrawing the `sum` and
`sum_sq` columns of 15 Nov): `math.fsum` of float64-rounded window sums is not in general the
correctly rounded plane sum (each window's sum is already rounded once), and a sum of squares of
finite float64 pixels can overflow float64, whereas the normalization brick's own moments
(`tail_moments.py`) use exact rationals. The tail's mean and std are stored, each rounded once as
the plane's are. They are pooled from the rows in exact rationals: each row's float64 `mean` and
`std` are read exactly (`fractions.Fraction`), the pooled sum is `Σ nᵢ · meanᵢ` and the pooled sum
of squares `Σ nᵢ · (stdᵢ² + meanᵢ²)`, and the pooled mean and std are rounded once by
`centred_moments` and `sqrt_nearest` of `tail_moments.py` (count-weighted mean, centred std, §1.4),
so nothing overflows for finite pixels. They are compared with `P`'s tail as follows. If `P`'s tail is empty, every window's tail
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
  under the given options (table below), evaluated in float64 as stated there and then **rounded
  outward to float32** (`analytic_min` the largest float32 `≤` the float64 bound, `analytic_max` the
  smallest float32 `≥` it), stored as the float64 of that float32 (numeric policy below).
- `tolerance = 4 * float(numpy.spacing(numpy.float32(m)))` with `m = max(abs(analytic_min),
  abs(analytic_max))` (exact: `m` is a float32): four float32 units in the last place at the bound's magnitude, because the
  derived image is float32 and its rounding at the bound is up to half a float32 unit, so a value
  that is within the analytic bounds before rounding always lies inside the widened limits.
- `binning_min = analytic_min − tolerance`, `binning_max = analytic_max + tolerance` (float64, one
  rounding each).
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
| `custom_od` (`psr_brightfield`, `he_custom`, `trichrome_custom`, user or default vectors) | Per channel `OD ∈ [lo_j, hi_j]`, evaluated as the conversion does, `lo_j = −log10(255 / white_j)`, `hi_j = −log10(1 / white_j)` (`I` floored at 1; `math.log10`). The target concentration is a linear map of the OD with the target column `a` of `inv(M)` (`concentrations = OD @ inv(M)`, target first), so the bound is **sign-aware**: `Σ_j min(a_j·lo_j, a_j·hi_j)` to `Σ_j max(a_j·lo_j, a_j·hi_j)`. `a` is evaluated by the adjugate, not LAPACK: `a_j = C_0j / det` with the row-0 cofactors `C_00 = M11·M22 − M12·M21`, `C_01 = −(M10·M22 − M12·M20)`, `C_02 = M10·M21 − M11·M20` and `det = M00·C_00 + M01·C_01 + M02·C_02`, `M` the recorded `stain_matrix` rows; every sum left to right (`j = 0, 1, 2`), plain float64 operations (`tools/window_histogram_spec.py`, `custom_od_bounds`). Negative concentrations are kept (§3.4), so the lower bound can be negative. |
| `fixed_deconvolution` (`he_eosin`, `he_hematoxylin`, `trichrome_blue`; scikit-image `separate_stains`) | Per channel `log(max(I/255, 1e-6)) / log(1e-6) ∈ [0, 1]`; the component is that vector times the matrix column, then set to 0 where negative, so `[0, Σ_j max(0, m_jk)]`, from the pinned scikit-image version's matrix, added left to right in float64. |
| `cielab` (`lab_a`, `trichrome_green`) | The float64 minimum and maximum of `rgb2lab(...)[..., 1]` over all 2**24 8-bit colours at the pinned scikit-image version (exhaustive), negated (and swapped) for `trichrome_green`; the white rescale keeps the input 8-bit, so the same bounds hold with `white`. |
| `luminance` (`luminance_inverted`, `psr_polarized`) | `[0.0, 1.0]` exactly (weights 0.2125, 0.7154, 0.0721 on values in `[0, 1]`). |
| `passthrough` (`fluorescence`, `shg`) | None: `NoFixedRange("preset_has_no_fixed_range")`. |

**Numeric policy** (F1). The float64 bound of a family is evaluated exactly as its row states (plain
IEEE-754 binary64 operations, the stated order, no fused multiply-add; `math.log10` is the only
library function of `custom_od`), then rounded outward to float32 as above. The outward rounding makes
`spec_sha256` insensitive to a last-bit difference of a float64 bound between platforms (`log10` is
not correctly rounded everywhere), except when the bound lies within that difference of a float32
boundary; the golden cases below are exact, and a platform that misses one bit of them is a defect to
report, never a tolerance. `spec_sha256` is the SHA-256 of the canonical JSON of exactly the ten
fields of the spec (below).

**Golden cases** (`tools/test_window_histogram_spec.py`, reproduced bit for bit by the normalization
brick). Stain rows are what `optical_density.stain_matrix` returns at `c6a9f9d` for the vectors given
(they enter as recorded rows; G3 to G5 call no scikit-image, so `skimage_version` is `null`; G1 and
G2 state `skimage_version = "0.26.0"` as an input). Hashes are truncated here to 16 hex digits; the
test holds them in full.

| Case | Inputs | `conversion_id` | `analytic_min`, `analytic_max` | `tolerance` | `binning_min`, `binning_max` | `spec_sha256` |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | `luminance_inverted`, white unset | `ce13f97f2d55b509…` | `0.0`, `1.0` | `4.76837158203125e-07` | `-4.76837158203125e-07`, `1.0000004768371582` | `a25dd0952d26d8f8…` |
| G2 | `luminance_inverted`, `white = (255, 255, 255)` | same as G1 | same | same | same | same as G1 |
| G3 | `he_custom`, `white = (230, 225, 240)`, default vectors (residual completed) | `d29672aa039c5694…` | `-3.27630352973938`, `2.6812243461608887` | `9.5367431640625e-07` | `-3.2763044834136963`, `2.681225299835205` | `5d4f141a41cba08b…` |
| G4 | `he_custom`, same white, user vectors `eosin (0.10, 0.95, 0.20)`, `hematoxylin (0.60, 0.75, 0.30)` | `05354c067033bc5d…` | `-3.8533785343170166`, `2.9239346981048584` | `9.5367431640625e-07` | `-3.853379487991333`, `2.923935651779175` | `9d87fcd655d5e9dd…` |
| G5 | `psr_brightfield`, `white = (250, 248, 252)`, user vectors `psr (0.15, 0.85, 0.50)`, `counterstain (0.70, 0.40, 0.55)`, `residual (0.30, 0.20, 0.90)` | `acd54b73791cd9bd…` | `-1.8734703063964844`, `3.200230598449707` | `9.5367431640625e-07` | `-1.8734712600708008`, `3.2002315521240234` | `3c3fddfc661b1638…` |

For G3 to G5, `to_scalar` on all 2**24 8-bit colours at normalization `c6a9f9d` gives extremes inside
`[analytic_min, analytic_max]` (checked when these cases were written; G3: `-3.27630352973938`,
`2.6812241077423096`).

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
`exclusion_component`, `inverted`, `colour_space`, `white`, `white_rescale` (both canonical, table
below), `stain_names`, `stain_matrix` (the unit rows actually used, default or user),
`residual_completed`, `od_definition`, `polarizer` and `skimage_version` (`null` when scikit-image
is not called). `numpy_version` and `normalization_version` are **not** keys (owner, 15 Nov): an
upgrade of either keeps the id; both versions are recorded in the run record, and a change of the
conversion's output in a new normalization release is a change of `preset_version`, which is a key.
A key the preset does not use is `null` (for example `matrix` for `luminance`, `stain_matrix` for
`cielab`).

**Canonical `white` and `white_rescale`.** The provenance does not record them uniformly
(`stain.py` at `b8aa65b`, unchanged at `v0.7.0` `c6a9f9d`): `_white_rescaled` writes `white: None,
white_applied: False, white_rescale: None` for an unset optional white and the white's three floats,
`white_applied: True, white_rescale: WHITE_RESCALE` for a given one; `_custom_od` writes `white`
and no `white_rescale` or `white_applied` key; a `fixed_deconvolution` preset writes none of the
three. The id therefore uses the canonical values below, by how the preset takes `white` (`needs`
or `accepts` of `stain_presets.py`, identical at both commits). `WHITE_RESCALE` is the frozen text
`clip(rint(I * 255 / white), 0, 255) as uint8, rint half to even` (`stain.WHITE_RESCALE` at both
commits); a change of that text is a change of `conversion_id_version`.

| Presets (how `white` is taken) | Canonical `white` | Canonical `white_rescale` | Rebuilt from `ScalarResult.provenance` |
| --- | --- | --- | --- |
| `luminance_inverted`, `lab_a`, `psr_polarized`, `trichrome_green` (optional, `accepts`) | The given white as three float64 (`check_white`), or `[255.0, 255.0, 255.0]` when unset | `WHITE_RESCALE`, whether the white is given or not (with `(255, 255, 255)` the rescale is the identity, bit for bit: `optical_density.rescale_to_white`) | `white_applied = False` with `white` and `white_rescale` both `None` gives `[255.0, 255.0, 255.0]` and `WHITE_RESCALE`; `white_applied = True` with three floats and `white_rescale == WHITE_RESCALE` gives those floats and `WHITE_RESCALE`; any other combination is refused (`ValueError`) |
| `psr_brightfield`, `he_custom`, `trichrome_custom` (required, `needs`; `custom_od`) | The given white as three float64; never defaulted (`check_options` refuses an unset white) | `null` (no rescale: the white enters the optical density) | `white` (three floats) and a `white_rescale` absent or `None`; anything else refused |
| `he_eosin`, `he_hematoxylin`, `trichrome_blue` (not taken; `fixed_deconvolution`) | `null` (a given white is refused by `check_options`) | `null` | `white` and `white_rescale` absent or `None`; anything else refused |

So an unset white and `white = (255, 255, 255)` give the same id **only for the four presets with an
optional white**, and the same derived image bit for bit. For those presets the diagnostics
`above_white_count` and `white_clipped_count` are computed with the canonical white, so both are
`0` when the white is unset or `(255, 255, 255)` (no 8-bit value exceeds 255), never blank: the two
requests give equal derived entries (duplicate rule below).

`input_dtype` is not a key: every preset that has a `conversion_id` takes `uint8` RGB only
(`stain.py`, which refuses any other dtype), so it would never vary. The pixel-dependent
diagnostics (`zero_fraction`, `floored_fraction`, `negative_fraction`, `above_white_fraction`,
`white_clipped_fraction`, `float32_exact`), descriptive fields (`hints`, citations) and `axes`
(`YXC` and `CYX` give bitwise identical outputs) are not keys either. Required tests: two
conversions with identical settings on images with different fractions give the same id; changing
any one key (white, a vector, the polarizer, the preset version, the scikit-image version) gives a
different id; for each of the four presets with an optional white, an unset white and
`white=(255, 255, 255)` give the same id (and `white=(250, 255, 255)` a different one); for a
`custom_od` preset an unset white is refused and for a `fixed_deconvolution` preset a given white is
refused, before any id is made; the id does not change with the installed numpy or normalization
version; the id from the options equals the id rebuilt from any `ScalarResult.provenance` of the same
call (both white states, every preset family), and an inconsistent white provenance is refused.
Pooling refuses rows of different `conversion_id`s or `spec_sha256`s.

**Diagnostics per patch.** Stored per patch as **counts over the interior** (`zero_count`,
`floored_count`, `negative_count`, `above_white_count`, `white_clipped_count`: each the numerator of
the provenance's fraction, with `total_pixel_count` as denominator), so they add up exactly across
patches; a count is blank where the preset's method does not define it. The normalization brick
computes them with `conversion_diagnostic_counts(pixels, *, axes, preset, white=None,
stain_vectors=None, polarizer=None)` on the interior's RGB pixels, with the provenance's definitions;
the provider never reimplements them. They are separate from the conversion identity.

### Step 2: the scaling applied

For every windowed feature column (`scaling_scope = patch_window`, EW7, EW8) and every patch it is
requested on, the provider reports each scaling **stage** applied on the way to that column. The
NumPy and the Torch percentile scalings of fiberfeatures differ in their threshold, their degenerate
output and their order of clipping, so they are specified separately. Read at fiberfeatures
`752b1dd` and checked unchanged at `main` `36819a3`: the only change to these functions between the
two commits is how the analysed region is read (`region_pixels(mask, shape)`, `mask != 0`, instead of
`mask > 0`; #224), which selects the same pixels for a binary mask and does not touch the scaling
arithmetic below.

**NumPy: `robust_normalize`** (`preprocessing.py`, applied twice by `preprocess_image`; recorded
as stages `robust_normalize_1` and `robust_normalize_2`).

1. The image as float32. Sample: the finite pixels of the analysed region (all pixels without a
   mask), restricted to `sample_region` (the patch interior under `patch_window`; an empty
   `sample_region` is refused, `ValueError`). Output pixels: the finite pixels of the analysed
   region; every other output pixel is `0.0`.
2. **Empty sample** (no sample pixel, possible only through the mask): output all `0.0`, float32.
   Recorded `transform = constant`, `constant_value = 0.0`, `constant_cause = empty_sample`.
3. `lo, hi = np.percentile(vals, [1.0, 99.0])`: NumPy's default `linear` method, float64 results.
   If either is not finite: output all `0.0`, `constant_cause = nonfinite_quantile` (not reachable
   from finite float32 input; written down because the code has the branch).
4. **Fallback test `hi <= lo`** (float64 comparison, threshold 0): if true, `hi = float(np.max(vals))`
   and `upper_fallback = true`; otherwise `upper_fallback = false`.
5. If still `hi <= lo` (a constant sample): output `1.0` on every output pixel when `lo > 0`, else
   `0.0`. Recorded `transform = constant`, `constant_value` `1.0` or `0.0`, `constant_cause =
   degenerate_range`, `fallback_rule = hi_le_lo`, `upper_fallback = true`, `low_value = lo`,
   `high_value = hi` (the maximum).
6. Otherwise **clip first, then scale**: `(np.clip(x, lo, hi) − lo) / (hi − lo + 1e-8)`, computed in
   float64 (the limits are float64) and stored as float32. Recorded `transform = percentile_range`,
   `fallback_rule = hi_le_lo`, `offset = lo`, `scale = hi − lo + 1e-8` (float64), `clip_order =
   clip_then_scale`, `clip_low = lo`, `clip_high = hi`, `arithmetic_dtype = float64`, `output_dtype
   = float32`.

**Torch: `_normalize_map_torch`** (`tensor_ops.py`; called per scale in `multiscale.py` for
`ridge_support`, and for `cornerness` (2D) or `junctionness` (3D); recorded as stage
`normalize_map_torch` with its `map` and scale, below).

1. Sample: `x[mask > 0]`, or every element without a mask; non-finite map values are refused
   before this point (`_stack_symmetric_matrix`, `check_finite`).
2. **Empty sample**: `torch.zeros_like(x)` (x's dtype, float32 at `752b1dd`). Recorded `transform =
   constant`, `constant_value = 0.0`, `constant_cause = empty_sample`, `low_value`, `high_value`
   blank.
3. `lo`, `hi`: the 0.01 and 0.99 quantiles by `_quantile_torch` (`linear`: position `q · (n − 1)` in
   Python float64, the two order statistics by `torch.kthvalue`, interpolated in float32), so float32
   values.
4. **Fallback test `float(hi − lo) < 1e-8`** (the float32 difference, converted to float64, compared
   with `1e-8`): if true, `hi = vals.max()` and `upper_fallback = true`. Unlike NumPy, this also fires
   when `0 < hi − lo < 1e-8`.
5. If still `float(hi − lo) < 1e-8`: output `torch.zeros_like(x)`, **`0.0` everywhere even when `lo
   > 0`** (a positive constant map gives 0 here and 1 in NumPy). Recorded `transform = constant`,
   `constant_value = 0.0`, `constant_cause = degenerate_range`, `fallback_rule = range_lt_1e-8`,
   `upper_fallback = true`, `low_value = lo`, `high_value = hi` (the maximum).
6. Otherwise **scale first, then clamp**: `((x − lo) / (hi − lo + 1e-8)).clamp(0.0, 1.0)`, all in
   x's dtype (float32: the Python `1e-8` does not promote, so `scale` is the float32 value of
   `float32(hi − lo) + 1e-8`). Recorded `transform = percentile_range`, `fallback_rule =
   range_lt_1e-8`, `offset = lo`, `scale` as used, `clip_order = scale_then_clip`, `clip_low = 0.0`,
   `clip_high = 1.0`, `arithmetic_dtype = output_dtype = float32`.

`local_contrast_normalize` (opt-in) is recorded as `local_contrast` with `p1` (1st percentile), the
region mean, `floor` and `sigma` in `parameters`.

So the record states what was really done, not the declared settings. A float32 value is written as
the float64 `repr` of that float32 (exact). One entry per (plane, patch set, patch, `image_kind`,
image, `conversion_id`, column, stage):

| Field | Meaning |
| --- | --- |
| `stage_index`, `stage` | Position in the column's record (from 0, order below) and the provider's stage name (`robust_normalize_1`, `normalize_map_torch`, …) |
| `map`, `scale_index`, `scale_value` | For a stage applied to an intermediate map: the map's name (`ridge_support`, `cornerness`, `junctionness`), the position of its scale in the provider's declared scale list (from 0) and that scale's value (fiberfeatures: `sigma_h`, unit in `parameters` as `scale_unit`); all three blank for a stage applied to the image itself, and `scale_index`, `scale_value` blank for a single-scale map |
| `state`, `reason` | `measured`; or `not_measured` with a reason (below) and every other field blank |
| `transform` | `none` (only as the single row of a measured column with no scaling stage, below), `percentile_range`, `fixed_range`, `local_contrast` or `constant` (a degenerate branch, NumPy step 2, 3 or 5, Torch step 2 or 5) |
| `fallback_rule` | `percentile_range`, and `constant` with `degenerate_range`: the implementation's fallback test, `hi_le_lo` (NumPy) or `range_lt_1e-8` (Torch); blank otherwise |
| `constant_value`, `constant_cause` | `constant` only: the value written to every output pixel (`0.0` or `1.0`) and why (`empty_sample`, `nonfinite_quantile`, `degenerate_range`); blank otherwise |
| `quantile_method`, `low_quantile`, `high_quantile`, `low_value`, `high_value`, `upper_fallback` | `percentile_range` (and `constant` with `degenerate_range`): the method (`linear`, `inverted_cdf`, …), the quantiles in percent, the values **actually used** (after any fallback) and whether the maximum replaced the upper value (`true`/`false`) |
| `offset`, `scale` | The applied linear map `y = (x − offset) / scale`, exactly as used (fiberfeatures: `offset = lo`, `scale = hi − lo + 1e-8` in the arithmetic dtype) |
| `arithmetic_dtype`, `output_dtype` | The dtype the map is computed in and the dtype stored (`float64`/`float32` for `robust_normalize`; `float32`/`float32` for the torch maps); `constant`: arithmetic blank, output the stored dtype |
| `clip_order`, `clip_low`, `clip_high` | `none`, `clip_then_scale` (limits in input units: `lo`, `hi`) or `scale_then_clip` (limits in output units: `0.0`, `1.0`) |
| `parameters` | Canonical JSON of the stage's other numbers (`local_contrast`: `p1`, `region_mean`, `floor`, `sigma`; a per-scale stage: `scale_unit`); `{}` when there are none |

**Canonical cells.** Numbers are float64 `repr`; blank means "not applicable to this transform".
`transform = none`: every numeric cell blank, `clip_order = none`, `parameters = {}`. `constant`:
`low_value`, `high_value` as used (blank for `empty_sample` and `nonfinite_quantile`), `offset`,
`scale`, `clip_low`, `clip_high` blank, `clip_order = none`. A stage the provider does not apply to a
column is not written.

**A measured column without scaling** (F3; for example a count, or fiberfeatures' `curvature_proxy`
if its only scaling, `sigma_h · |grad θ|` clamped to `[0, 1]`, is not declared a stage) has exactly
**one** row: `stage_index = 0`, `stage`, `map`, `scale_index`, `scale_value` blank, `state = measured`,
`transform = none`. A column with at least one stage has no `none` row. Its key is the ordinary key
with `stage_index = 0`, so it can never coincide with a stage row.

**Several maps or scales feeding one column** (F3; fiberfeatures computes `ridge_support` per
`sigma_h` of `config.scales` and combines the scales afterwards): one row per (map, scale) stage
actually applied for that column, each with its own `map`, `scale_index` and `scale_value`. **Order of
`stage_index`:** the stages applied to the image, in the order applied (`robust_normalize_1`,
`robust_normalize_2`); then the map stages, by `map` (Python string order), then `scale_index`
(ascending). The provider declares which stages feed a column; MorphoFeature checks only the
record's form (unique keys, contiguous `stage_index` from 0, the cell rules above).

**Unmeasured columns.** `not_measured` follows the provider output that MorphoFeature already
validates (`patch_output.py`). The reason of a column on a patch is the first that applies (F2):

1. `no_provider_report`: the provider does not declare `window_report`;
2. `patch_not_measured`: the provider lists the patch in its manifest's `patches_not_measured` (its
   own reason is kept in `provider_reason`), **whatever the output's `status`**;
3. `valid_empty`: the output has `status = valid_empty` (zero rows) and the patch is not listed.

Today `_not_measured` (`patch_output.py`, MorphoFeature `7ac7487`) refuses a sent patch with neither
a row nor a listing, and `valid_empty` means every table has zero rows, so a `valid_empty` window
always lists its patch and gets `patch_not_measured`; rule 3 is reachable only if step 4 relaxes that
check for windowed calls (see the open points). **A `not_measured` column never has `transform = none`**, and a measured
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

**Two providers, one derived image.** Several providers can make the same derived image of one
patch. Their entries for the key `(plane_id, patch_set, patch_id, image_kind, image, conversion_id)`
(`image_kind = derived`) give one row, by the rules below. One provider contributes at most one
entry per key; a second entry from the same provider is a provider output error. An entry that breaks
the invariants (a NaN or infinite value in a float field included) is refused as a provider output
error before any comparison, so only valid entries are compared.

**Compared fields, in this order** (the canonical comparison order; the order of the header below):
`dtype`, `reference_kind`, `reference_sha256`, `preset`, `preset_version`, `conversion_id`,
`spec_version`, `spec_sha256`, `bin_count`, `binning_min`, `binning_max`, `analytic_min`,
`analytic_max`, `tolerance`, `total_pixel_count`, `valid_pixel_count`, `nonfinite_pixel_count`,
`pixel_min`, `pixel_max`, `underflow_count`, `underflow_mean`, `underflow_std`, `overflow_count`,
`overflow_mean`, `overflow_std`, `counts` (the full array of `bin_count` integers, bin 0 first, not
its sparse text), `zero_count`, `floored_count`, `negative_count`, `above_white_count`,
`white_clipped_count`. The key columns are equal by construction; `status`, `reason` and the two
provider columns are outputs of the rule, not compared.

**Equality.** Integers by value; text by code points; blank equals only blank (a blank and a `0`
differ). Floats by their **IEEE-754 binary64 bit pattern** (recommended over decimal text or a
tolerance: the writer's `repr` round-trips, so equal bits are equal cells), after mapping `-0.0` to
`0.0` (as the writer does); for the finite values allowed here this is exact numeric equality. NaN
never reaches the comparison (refused above). Reference implementation:
`tools/window_histogram_spec.py` (`comparable`, `first_difference`).

**Order of comparison.** The reporting providers in Python string order; the first, `P1`, is the
reference; each other provider, in that order, is compared with `P1` field by field in the order
above, and the first difference found names the pair and the field (`counts[i]` for the first
differing bin). Then:

- every entry equal to `P1`'s: one row, `measured`;
- otherwise the row is `not_measured` with the reason `duplicate_report_disagrees`, and the run
  record's `window_histogram_errors` gains `{key, providers (the reporting providers, sorted),
  first_difference: {providers: [P1, Pk], field}}`. Features are unaffected; the histogram write of
  every other key goes on.

**Which providers reported**, recorded per row apart from the measurement, so a provider that
reported nothing is never hidden by another's measurement. Let `R` be the providers with a request
using that derived image on that patch (never empty for a derived row). Each provider of `R` is in
**exactly one** of the two columns: `providers_reporting`, the providers that sent a measured entry
for the key; `providers_not_reporting`, the providers that sent none (no `window_report`, or a
`not_measured` entry). A provider outside `R` is in neither. Both columns are `;`-separated in
Python string order, blank when empty, never with a repeated name, and their union is `R`.

**Reason of a derived row** (F2), the first that applies:

1. `preset_has_no_fixed_range`: `output_histogram_spec` returns `NoFixedRange` for the request's
   preset and options (MorphoFeature recomputes it; a provider entry with a histogram for such an
   image is a provider output error);
2. `duplicate_report_disagrees`: two or more measured entries, not all equal;
3. `measured` (no reason): one or more measured entries, all equal;
4. `patch_not_measured`: no measured entry, and at least one provider of `R` lists the patch in its
   `patches_not_measured`;
5. `no_provider_report`: otherwise.

### The `window_histograms.csv` table, schema 1 (normalization)

A new table with its own schema, owned by the normalization brick (type, writer, reader), **not an
extension of `plane_histograms.csv`** (schema 5 has a unique `plane_id` per row, one `bin_count` and
one `dtype` per table). MorphoFeature writes it next to the patch catalogue (EW3) through the brick's
writer. Common format of §6.1 (UTF-8, comma-separated, one header row, floats at full precision with
`repr`, blanks for missing values, temporary file then replace).

- **File:** `window_histograms.csv`.
- **Row:** one per plane x patch x image, key `(plane_id, patch_set, patch_id, image_kind, image,
  conversion_id)`, unique (owner, 16 Nov). `image_kind` is in the key because a source channel and
  a derived `passthrough` image can share a name and both have an empty `conversion_id`: the source
  channel `SHG` and the `shg` preset's derived image `SHG` (`image_name` in `stain_presets.py`) are
  two rows, `(…, source_channel, SHG, "")` and `(…, derived, SHG, "")`. Two derived images of one
  name but different options differ by `conversion_id`; it is empty for source channels and for
  `passthrough` rows. The writer refuses to write, and the reader refuses to read, two rows with one
  key (`ValueError` naming the key); neither keeps one of them.
- **Rows written:** for every catalogue patch of a set with a windowed request on the plane, one row
  per source channel read by any unit of that set on the plane, and (step 2) one per derived image of
  its requests; a patch with no window unit gets `not_measured` source rows (`no_window_unit`) and no
  derived row (no derived image was made; the pooling's condition 4 counts it as missing).
- **Order:** planes in the run's order, patch sets in the order they were cut, patches in catalogue
  (CellPatcher) order, then `image_kind` (`source_channel` before `derived`), then `image` (Python
  string order, §6.1), then `conversion_id` (Python string order; empty first). Serial and pooled
  runs give the same bytes (EW9).

**Header, complete and in this order** (61 columns; 65 before the tail sums were withdrawn, 16 Nov):

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
underflow_count,underflow_mean,underflow_std,
overflow_count,overflow_mean,overflow_std,
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
| `underflow_*`, `overflow_*` | Tails: count (exact) and mean and std (each the float64 nearest its exact value, rounded once, as the plane's; written with `repr`); `0`, `0.0`, `0.0` when empty. No sum or sum of squares is stored |
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

**Required and blank cells** (B3), by `image_kind` and status. R: required (a blank is refused);
B: blank (a value is refused, so a zero histogram never stands for a missing one); `schema_version`
and `image_kind` are required in **every** row, because the reader picks the reason list and the cell
rules by them. The reasons a status allows depend on `image_kind`: a source reason in a derived row,
or the reverse, is refused.

| Columns | Source, `measured` | Source, `not_measured` | Derived, `measured` | Derived, `not_measured` |
| --- | --- | --- | --- | --- |
| `schema_version`, `image_kind`, `image`, `status` | R | R | R | R |
| `position_id` … `plane_id` | R (blank only where §6.1 allows) | as measured | as measured | as measured |
| `patch_set`, `patch_id`, `catalogue_version`, `bounds_*` | R | R | R | R |
| `origin_*`, `interior_*` | R | B for `no_window_unit` (there is no window); R for `no_plane_histogram`, `plane_histogram_mismatch` | R | R |
| `dtype` | R (the plane's) | B | R (`float32`) | B |
| `reason` | B | R: `no_window_unit`, `no_plane_histogram`, `plane_histogram_mismatch` | B | R: `preset_has_no_fixed_range`, `patch_not_measured`, `no_provider_report`, `duplicate_report_disagrees` |
| `providers_reporting` | B | B | R (one or more) | R (two or more) for `duplicate_report_disagrees`; B otherwise |
| `providers_not_reporting` | B | B | R if a provider of `R` sent no measured entry, else B | R (one or more) except for `duplicate_report_disagrees`, where it is R if a provider of `R` sent none, else B |
| `reference_kind`, `reference_sha256` | R (`plane_histogram`) | B | R (`output_histogram_spec`) | B |
| `histogram_range` | R | B | B | B |
| `preset`, `preset_version` | B | B | R | R |
| `conversion_id` | B | B | R (B for `passthrough`, which is never measured) | R; B for `preset_has_no_fixed_range` |
| `spec_version`, `spec_sha256` | B | B | R | B |
| `bin_count` | R | B | R (`1024`) | B |
| `binning_min`, `binning_max` | R; both B only when the plane has no finite pixel | B | R | B |
| `analytic_min`, `analytic_max`, `tolerance` | B | B | R | B |
| `total_pixel_count`, `valid_pixel_count`, `nonfinite_pixel_count`, `counts` | R (`counts` may be `empty`) | B | R | B |
| `pixel_min`, `pixel_max` | R if `valid_pixel_count > 0`, else B | B | R if `valid_pixel_count > 0`, else B | B |
| `underflow_*`, `overflow_*` | R (`0`, `0.0`, `0.0` when empty) | B | R | B |
| `zero_count` | B | B | R for `fixed_deconvolution`, else B | B |
| `floored_count`, `negative_count` | B | B | R for `custom_od`, else B | B |
| `above_white_count` | B | B | R for `custom_od` and the four optional-white presets, else B | B |
| `white_clipped_count` | B | B | R for the four optional-white presets, else B | B |

The diagnostics follow the provenance of `stain.py` (`zero_fraction` for `fixed_deconvolution`;
`floored_fraction`, `negative_fraction`, `above_white_fraction` for `custom_od`;
`above_white_fraction`, `white_clipped_fraction` for `luminance` and `cielab`, with the canonical
white of B1B).

A measured row's cells are also checked against the invariants above. The reader refuses another
`schema_version`, a missing, extra or reordered column, an unknown reason or `image_kind`, a reason
of the other `image_kind`, a cell against the table above, a provider in both provider columns, a
duplicate key, and a `plane_histograms.csv` given in its place; it never converts. If a measurement
fails (other than with a listed reason), the writer writes nothing, as for `plane_histograms.csv`
(§6.2).

### The `window_scaling.csv` table, schema 1 (MorphoFeature)

Written by MorphoFeature next to `window_histograms.csv`, from the `scaling` entries. One row per
entry (key: plane, patch set, patch, `image_kind`, image, `conversion_id`, column, `stage_index`;
unique, a duplicate refused by the writer and the reader); a
`not_measured` column has one row with `stage_index` 0 and `stage` empty. Order: the row order of
`window_histograms.csv` up to the image, then `conversion_id`, column name (Python string order),
`stage_index`. Header, complete and in this order (46 columns):

```text
schema_version,
position_id,image_file,z,t,condition,biological_repeat,technical_repeat,source_relative_path,plane_id,
patch_set,patch_id,catalogue_version,
image,image_kind,preset,preset_version,conversion_id,
column,provider,stage_index,stage,map,scale_index,scale_value,
state,reason,provider_reason,
transform,fallback_rule,constant_value,constant_cause,
quantile_method,low_quantile,high_quantile,low_value,high_value,upper_fallback,
offset,scale,arithmetic_dtype,output_dtype,
clip_order,clip_low,clip_high,
parameters
```

`schema_version` is `1`. Reasons, frozen for schema 1: `patch_not_measured`, `valid_empty`,
`no_provider_report`. Frozen enumerations: `transform` (`none`, `percentile_range`, `fixed_range`,
`local_contrast`, `constant`), `fallback_rule` (`hi_le_lo`, `range_lt_1e-8`), `constant_cause`
(`empty_sample`, `nonfinite_quantile`, `degenerate_range`), `clip_order` (`none`,
`clip_then_scale`, `scale_then_clip`). The reader refuses another version, header, reason or
enumerated value; a `not_measured` row with any transform cell filled; a cell filled or blank
against the cell rules above; a `none` row beside a stage row of the same column; and a column whose
`stage_index` values are not `0, 1, …` without gaps.

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
| `not_measured` cell rules (B3), each status and `image_kind` | A row following the required/blank table is read; one value in a B cell, one blank in an R cell, a blank `schema_version` or `image_kind`, or a source reason in a derived row is refused |
| Overlapping bounds | Pooling refused |
| All-NaN float plane | Plane limits blank; every patch: `valid` 0, `nonfinite` = area, reference blank, counts `empty`; the pooled counts still equal the plane's exactly |
| All-NaN patch in a plane with finite pixels | `valid` 0, observed extrema blank, reference limits kept |
| `+inf` and `−inf` pixels | In `nonfinite_pixel_count`, never in a bin or a tail |
| Robust range with hot pixels | Tail counts sum exactly; a patch without tail pixels has empty tails; `pixel_min > binning_min` accepted; an empty plane tail compared by the empty-tail rule |
| Tail double rounding (N1): a tail whose per-window float64 sums, added with `math.fsum`, differ from the correctly rounded plane sum (for example values `1.0`, `2**-53`, `2**-53` split over windows so each window's sum rounds) | Counts equal exactly; pooled mean and std within the stated ulp tolerance; no sum column exists and none is compared bitwise |
| Tail overflow (N1): finite float64 tail values near `1e300`, whose squares overflow float64 | Window and pooled mean and std finite and within the tolerance (exact-rational pooling); no `inf` and no refusal |
| 8-bit `R`, `G`, `B` with a plane minimum above 0 | Bin `i` holds `binning_min + i`; exact |
| Constant plane | Every valid pixel in bin 0, in every patch |
| Plane without a `plane_histograms.csv` row, or a SHA-256 mismatch | `not_measured` with the reason; features unchanged |
| Each bounded family at its extreme 8-bit inputs | `bin_count` 1024, limits `analytic ± tolerance`, empty tails |
| `OutputHistogramSpec` goldens G1-G5 (F1) | `conversion_id`, every float bit for bit (`float.hex`) and `spec_sha256` as in `tools/test_window_histogram_spec.py` |
| A derived value outside the widened limits (injected) | Counted in the tail, never an end bin |
| `passthrough` preset | Derived row `not_measured`, `preset_has_no_fixed_range`, `conversion_id` empty; features and source rows present |
| Source channel `SHG` and the `shg` preset's derived image `SHG` on one patch (B1A) | Two rows, keys differing only by `image_kind` (`source_channel` first); a table holding two rows with the same six-part key is refused by the reader, and the writer refuses to write it |
| `conversion_id`: same settings, different fractions / changed settings | Same id / different id |
| `conversion_id` white identity (B1B), each optional-white preset (`luminance_inverted`, `lab_a`, `psr_polarized`, `trichrome_green`) | Unset white and `(255, 255, 255)`: same id, same derived image bit for bit, `above_white_count` and `white_clipped_count` both `0`; `(250, 255, 255)`: another id; the id rebuilt from each `provenance` equals the id from the options; an inconsistent white provenance refused |
| `conversion_id` white scope (B1B) | `custom_od` preset without white, and `fixed_deconvolution` preset with a white: refused before any id |
| `canonical_json`: NumPy scalars, `-0.0`, `None`, NaN | Same text as the Python values; `0.0`; `null`; NaN refused |
| Mixed `conversion_id`s or `spec_sha256`s | Pooling refused |
| Diagnostics pooled from the patches of a clipped grid | Each count equals `conversion_diagnostic_counts` on the whole plane |
| Two providers report one derived image, equal | One `measured` row, both in `providers_reporting` |
| Two providers report one derived image, different | `not_measured`, `duplicate_report_disagrees`; error recorded; features unchanged |
| One provider reports, the other has no `window_report` | `measured`; the other in `providers_not_reporting` |
| Duplicate floats (B4): two entries equal except `underflow_mean` one ulp apart; equal except `pixel_min` `-0.0` vs `0.0`; three providers `a`, `b`, `c` with `b` differing in `zero_count` and `c` in `pixel_min` | Disagreement naming `[a, b]` and `underflow_mean`; equal (one `measured` row); disagreement naming `[a, b]` and `zero_count` (first pair in provider order, then first field in the comparison order) |
| Duplicate `counts` (B4): two entries differing only in bins 17 and 40 | Disagreement naming `counts[17]` |
| A NaN in a provider's `underflow_mean` | Provider output error before any comparison; not a disagreement |
| Provider columns (B4): `a` measured, `b` `not_measured`, `c` without `window_report`, `d` with no request using the image | `providers_reporting = a`, `providers_not_reporting = b;c`, `d` in neither; a name in both columns refused by the reader |
| Derived reason precedence (F2): one provider lists the patch in `patches_not_measured`, another has no `window_report` | `patch_not_measured` |
| A valid-empty window that lists its patch in `patches_not_measured` (F2; the only valid-empty window today's check accepts) | Scaling rows `not_measured`, `patch_not_measured` (not `valid_empty`), the provider's reason kept; no `transform = none` |
| A patch in `patches_not_measured` | Scaling rows `not_measured`, `patch_not_measured`, the provider's reason kept |
| `robust_normalize` whose 99th percentile equals the 1st (sparse structure) | `upper_fallback = true`, `high_value` the maximum, not the declared 99th percentile |
| NumPy `robust_normalize`, positive constant sample (B2) | `constant`, `constant_value = 1.0`, `degenerate_range`, `fallback_rule = hi_le_lo`, `upper_fallback = true` |
| NumPy `robust_normalize`, zero constant sample | `constant`, `constant_value = 0.0`, `degenerate_range` |
| Torch `_normalize_map_torch`, positive constant map (B2) | `constant`, `constant_value = 0.0` (not 1), `degenerate_range`, `fallback_rule = range_lt_1e-8` |
| Torch map with `0 < hi − lo < 1e-8` and a maximum well above `lo` (B2) | Fallback fires (`upper_fallback = true`, `high_value` the maximum), `percentile_range`, `scale_then_clip`, float32 `offset` and `scale`; the same values in NumPy do not fire the fallback (`hi_le_lo` false) |
| Torch map with an empty sample (mask without a positive pixel) | `constant`, `constant_value = 0.0`, `empty_sample`, `low_value` and `high_value` blank |
| A measured column with no scaling stage (F3) | Exactly one row, `stage_index = 0`, `stage` blank, `transform = none`; a `none` row beside a stage row is refused |
| A column fed by `ridge_support` at three scales after two `robust_normalize` stages (F3) | Five rows: `stage_index` 0-1 the image stages in order, 2-4 `normalize_map_torch` with `map = ridge_support`, `scale_index` 0, 1, 2 and each `scale_value`; a gap or repeat in `stage_index` refused |
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
3. Whether a windowed call may return `valid_empty` without listing its patch in
   `patches_not_measured` (EW11 step 4). Recommendation: keep today's check, so the scaling reason
   `valid_empty` stays unused and every empty window is `patch_not_measured` with the provider's reason.
