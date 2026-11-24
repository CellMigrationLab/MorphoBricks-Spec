# ADR 0010: experiment-v1 volumes (Z-stacks described and handed off without projection)

- **Status:** **Proposed** (24 November 2026). Not implemented. The owner decisions it encodes
  (preprocessing#438, owner comments of 23 and 24 November 2026, and the order decided for this
  work) are recorded below as accepted inputs and are not reopened. What this ADR adds is their
  encoding: what a described volume is, its Z calibration, how a volume is recorded in a run,
  which existing refusals change and in which order, what stays refused, and the versioning
  impact. Everything that is a choice, not an owner decision, is listed under
  [modelling choices](#modelling-choices-for-the-owners-review) with its alternatives; the
  questions left for the owner are under [open questions](#open-questions-for-the-owner).
- **Is** prerequisite **P-1** of [ADR 0009](https://github.com/CellMigrationLab/MorphoBricks-Spec/pull/55)
  (consumer manifest, draft PR #55, branch `claude/adr-0009-consumer-manifest`, read at
  `d2dfbcc2b4237437d2868e6c481e001d15eadece`): "the #438 normative amendment of experiment-v1 §1
  (separate, not written here) ... which volumes may be described, how §8's homogeneity reads `Z`,
  and that histograms, normalization and QC are recorded as not computed for them". It is the gate
  for morphobricks-preprocessing#438.
- **Order (owner decision of 24 November 2026, #438):** Stable 1, then ADR 0009 accepted, then
  this amendment, then #438. This ADR is therefore not offered for acceptance before ADR 0009 is
  accepted, and #438's first step MUST NOT land before both this ADR and ADR 0009's P-2
  (MorphoFeature's Z and mixed runtime guard) are accepted and P-2 is implemented.
- **Amends, on acceptance:** [`experiment-v1.md`](../experiment-v1.md) §1 (the 2-D-only scope
  sentence), §4.5 (one paragraph: masks of volumes), §4.7 (the "belongs to" text of the `axes`
  row; the forbidden names do **not** change), §7 (an amendment of v1, no new version), §8 (the
  reading of `R_UNIT_NOT_HOMOGENEOUS` for `Z`; one new refusal `R_VOLUME_Z_UNCALIBRATED`; one
  recorded warning `W_MIXED_PLANES_AND_VOLUMES`); [ADR 0002](0002-shared-request-resolver.md) AR3
  (the next resolver contract version: a `plane` request is never served from a volume);
  [ADR 0008](0008-plane-histograms-v6.md) (a volume has no row; no table version change); the
  [conformance plan](../conformance-plan.md) §4 row "Volume" and new scenarios; the
  [roadmap](../roadmap.md) §9 sentence on 3-D. The replacement text is given verbatim
  [below](#proposed-normative-text); it is written into the normative files only on acceptance.
  No fixture, golden or validator changes in this PR.
- **Base:** MorphoBricks-Spec `main` `232fb38880cc487510532d99dc71d46a27005f23`. Evidence read at
  morphobricks-preprocessing `main` `b683c7c553db4f5c281870730c49d63eb1b8b4bc`; MorphoFeature
  claims are those ADR 0009 cites at MorphoFeature `main` `58aa19b849946426961e5c9be495b4ab41a366e2`
  (not re-read here).
- **Why a new ADR file.** Like ADR 0006: an amendment of experiment-v1 with its own decision set,
  refusal and record, that also touches the resolver contract (ADR 0002) and the histogram table
  (ADR 0008). It changes no accepted decision of ADR 0001, 0002, 0005, 0006 or 0008.

## Context

experiment-v1 §1 says: "v1 analyses 2-D planes only. A Z stack is projected by a recorded
preprocessing step (preprocessing #176) before it is described; the file has no Z, axes or
shared-plane field." §4.7 forbids `axes`, `shared`, `plane_scope`, `z` and `projection` with the
reason "v1 is 2-D only". There are two Z gates in preprocessing today (checked at `b683c7c`):

1. **The description step.** `check_metadata(files, allow_z=False)` (`metadata.py:391-431`, through
   `_check_counts` at `:572-578` and `header_depth_slices` at `:566-569`) and the role-based check of
   the axis review (`axis_review.py:370-382`) both call `size_checks.z_stack_issues`
   (`size_checks.py:46-80`), which refuses every image with more than one depth slice as
   `z_stack_not_supported`. The notebook's projection card (`notebook_projection.py:1-24`) offers
   recorded 2-D copies; the option *Keep the 3-D stacks for 3-D-capable tools* is shown greyed
   out. `conversion_plan.py:150-151` drops the Z error only when a projection is planned.
2. **The hand-off.** `RunInputs.resolve_request` (`run_inputs_resolve.py:132`) calls
   `volume_refusals` (`run_inputs_request.py:557-598`): a `volume` request without
   `Capabilities.volume_support` is `A_VOLUME_NOT_SUPPORTED`, and so is a `binary_mask_policy` on a
   position with more than one Z plane, with or without the capability (ADR 0005 BM5). A `plane`
   request on a Z-stack is **not** refused: `plane_selections` (`run_inputs_request.py:478-482`)
   returns one selection per `(t, z)`, so a volume would be served as separate planes.
   `RESOLVER_VERSION = 3` in the code (`run_inputs_request.py:61`); the Spec's current contract is
   version 4 (ADR 0002 AR12, accepted, not yet in this code).

Three further facts at `b683c7c` shape the encoding:

- **The Z and T counts of a run's image come from its histogram rows.** `RunInputs._fov`
  (`run_inputs.py:552-582`) sets `z_count = max(zs) + 1` with `zs = {r.z for r in rows} or {0}`.
  An image with **no** histogram row gets `z_count = 1` silently. The manifest's `FileEntry`
  (`manifest_files.py:38-60`) records `axes`, `roles`, `plane_count` and `pixel_sizes`, but no
  per-role size. Disabling histograms for volumes (CM5 / #438) without changing this would turn
  every volume into a one-plane image without a word.
- **Z calibration already has a home outside the description.** `calibration.py:1-46`: for X, Y
  and Z a size comes from the header (`header`), from `calibration.csv` (`stated`), or is stated as
  deliberately uncalibrated (`pixels`); an axis with none is uncalibrated; a Z size is kept only for
  images that have the `Z` role (`fit_to_roles`, `:328-345`). `RunInputs.pixel_sizes`
  (`run_inputs.py:331-339`) returns each with its source. Nothing is guessed. experiment-v1 §1 and
  §4.7 keep calibration out of `morphobricks.toml`.
- **Masks already carry Z.** A mask's axes may include `Z` and `T` (`masks/model.py:30`,
  `masks/stated.py:29`); the masks of one image must have the image's depth slices and time points,
  and a 2-D mask is never shared by the planes of its image (`masks/checks.py:40-50`, owner
  decision of 5 November 2026). The mask step scans a Z mask one plane at a time and never matches
  objects across planes (`mask_scan.py:42-44`). Segmentation hand-off and the tissue-mask card refuse
  Z or T stacks (`segmentation_handoff.py:555-557`, `notebook_tissue_mask.py:50-51`); a projection
  is refused while masks have depth slices (`projection_masks.py`, `projection_issues.py:96-114`).

## Decisions

### Owner decisions (recorded as accepted inputs; not reopened by this ADR)

From morphobricks-preprocessing#438 (issue body and owner comments of 23 November 2026, and the
owner comment of 24 November 2026), and the instructions for this amendment:

| # | Decision | Source |
|---|---|---|
| VZ1 | **The Z gate moves from the description step to the hand-off.** A Z-stack can be described, tagged and calibrated as a stack; projection stays an explicit, recorded choice with no default, offered beside keeping the stacks. The hand-off is the one hard gate | #438 title and proposal; comment 2 ("lift the description-step refusal; describe, tag and calibrate volumes; write masks; hand volumes only to consumers that declare `volume_support`") |
| VZ2 | **Histograms, normalization and QC metrics are disabled for volumes at first** (per volume later). The run records "not computed: volume"; never an empty table, zeros, or a per-plane result passed off as the volume's. The notebook says so where the step would run. A consumer that asks `RunInputs` for them on a volume gets a **coded refusal**, never missing data treated as absent, never a fallback to raw or per-plane values. 2-D images in the same run are unaffected | #438 comment 2 (replaces comment 1's per-volume plan for the first step); ADR 0009 CM5 |
| VZ3 | **A Z run only goes to volume-capable bricks.** Nothing splits a volume into slices for a plane-only consumer | #438 comments 2 and 3; ADR 0009 CM5 |
| VZ4 | **Mixed 2-D/3-D runs:** refused by MorphoFeature (and any consumer that needs one unit per run); **only warned** in preprocessing, which can publish such a description; the warning names the counts of each kind, says MorphoFeature will refuse the run as it stands (split, or project the stacks), and is **recorded in the run's checks**, not only shown | #438 comments 4 and 5; ADR 0009 CM5 |
| VZ5 | **Z calibration is mandatory for a described volume and never guessed** | #438 "Tests": "A Z stack is described and published without projection, and its Z calibration is mandatory and never guessed" |
| VZ6 | **Order:** Stable 1, then ADR 0009 accepted, then this amendment, then #438 | #438 comment of 24 November 2026 |
| VZ7 | **This design gets an external review round** (ChatGPT) before acceptance | owner practice for important designs |

### What a described volume is

- **Definition.** An included image is a **volume** when its **confirmed** `Z` role has size > 1.
  The size of that role is the image's **Z extent** (`z_count`). An image without a `Z` role, or
  whose `Z` role has size 1, is a **plane image**, exactly as today (ADR 0002 AR3: a one-slice
  volume is a plane). Header letters are evidence only; the confirmed roles decide (contract §2,
  `axis_review.py`). A volume with a `T` role of size > 1 is one volume per time point.
- **Nothing in `morphobricks.toml`.** The description stays free of Z, axes, shared planes and
  projection: the five forbidden names of §4.7 stay forbidden, and no field is added. Whether an
  image is a volume is a fact of the image and its confirmed roles, recorded in the run manifest,
  like its channel count and pixel size; it is never a statement in the description that could
  disagree with the image ([rejected alternatives](#rejected-alternatives)). A description of a volume
  experiment is therefore byte-for-byte the same kind of file as a 2-D one (`v01` serves both).
- **Z calibration (VZ5).** Every volume MUST have a recorded Z step whose source is `header` or
  `stated` (`calibration.csv`), with a supported length unit and a finite value > 0 (the existing
  unit rule, `length_units.py`). A volume whose Z step has no source, or is stated as `pixels`
  (deliberately uncalibrated), is refused at run publication: `R_VOLUME_Z_UNCALIBRATED`
  ([refusals](#refusals-that-change-and-their-precedence)). The Z step is never taken from X or Y, from
  another image, from a projection's metadata (already excluded by `fit_to_roles`), or from a
  default. Different Z steps between images are allowed and recorded per image (today's warning
  `different_pixel_sizes` stays a warning). X and Y keep today's rules
  ([modelling choice 4](#modelling-choices-for-the-owners-review)).
- **Where the calibration check sits.** At run publication (the run manifest is written), not at
  `describe`: calibration is not part of the description (§1), and a description is published
  before any calibration exists in some flows. The notebook shows the missing Z step on the Axes
  step's calibration card as soon as the roles are confirmed, so the user meets it early; the
  refusal is the publication guard ([modelling choice 3](#modelling-choices-for-the-owners-review)).

### How a volume is recorded in a run

All of it in the run manifest (`run_manifest.json`), never in `morphobricks.toml`:

- **Per image, the confirmed sizes.** Every image entry records `z_count` and `t_count`, the sizes of
  its confirmed `Z` and `T` roles (1 for an absent role), and `spatial_unit`: `"plane"` (z_count = 1)
  or `"volume"` (z_count > 1). Both are written from the confirmed roles at the run and are
  **required** in the new manifest version. `RunInputs.fovs()` reads `Fov.z_count` and `Fov.t_count`
  from these fields, **never** from histogram rows; the `or {0}` default of `_fov` is removed. A
  manifest entry whose `spatial_unit` disagrees with its `z_count` is refused
  (`ManifestFormatError`).
- **Per image, what was not computed (VZ2).** Every image entry records `plane_statistics`:
  `"computed"` for a plane image, `"not_computed: volume"` for a volume. It covers the three
  products the owner named: plane histograms (ADR 0008), the normalization fits made from them,
  and the QC metrics (#365, `image_qc*.py`). The histogram table and the QC table hold **no row**
  for a volume; `RunInputs` cross-checks the table against the manifest and refuses a run folder
  where a volume has a row or a plane image has none (a corrupted or hand-edited run folder, never
  repaired). Normalization fits pooled over images use the plane images only, and the fit record
  names the volumes it left out ([modelling choice 6](#modelling-choices-for-the-owners-review)).
- **A coded refusal for a request (VZ2).** `RunInputs` refuses a request for the histograms,
  normalization or QC metrics of a volume with the RunInputs code `VOLUME_STATISTICS_NOT_COMPUTED`
  (one constructor, like ADR 0005's codes), naming the image, its Z extent and the reason ("not
  computed: volume; per-volume statistics are not implemented yet"). It is never an empty result,
  zeros, or the per-plane values of the volume's slices. A request on a run that mixes plane images
  and volumes returns the plane images' results and refuses only for the volumes it names.
- **The mixed-run warning (VZ4).** When the included images of a run are not all of one kind,
  preprocessing records the warning `W_MIXED_PLANES_AND_VOLUMES` in the run's checks
  (`run_manifest.json`, beside the other recorded issues): the counts of each kind, every volume
  (FOV key, path, `z_count`) and every plane image (FOV key, path), sorted by FOV key then path, and
  the text "MorphoFeature refuses this run as it stands: split it into two experiments, or project
  the stacks". It never blocks publication and never disappears because a consumer was or was not
  checked (ADR 0009, "#438 and ADR 0005").
- **The projection record is unchanged.** A projected run keeps conversion record version 4 and
  `RunInputs.projection`; its images are planes.

### Refusals that change, and their precedence

| Code (owner) | Today | After this ADR |
|---|---|---|
| `z_stack_not_supported` (preprocessing issue code; experiment-v1 §1's projection rule) | Error at header check and axis review; Z-stack never described | **Removed as a refusal.** No replacement at the description step. Projection stays an offered, recorded choice with no default, beside *Keep the 3-D stacks* (now enabled). `allow_z` loses its purpose (implementation detail of #438) |
| `R_UNIT_NOT_HOMOGENEOUS` (§8) | "interpreted axes" may differ in a unit; T counts never compared (§1) | Unchanged code and precedence. For `Z`, as for `T`, it compares the role's **meaning**, never its size; an absent `Z` role and a `Z` of size 1 read the same. A unit whose images differ only in Z extent, plane images included, is **not** refused: it is the recorded warning `W_MIXED_PLANES_AND_VOLUMES` (VZ4) when kinds mix ([choice 7](#modelling-choices-for-the-owners-review)) |
| `R_VOLUME_Z_UNCALIBRATED` (§8, **new**) | n/a | At run publication: one refusal listing **every** volume (FOV key, path, `z_count`) whose Z step has no source or is `pixels`, naming the fix (state the Z step in `calibration.csv`, or project the stacks). Reported together with every other run-publication refusal found; it replaces none and none replaces it. Nothing is computed or published |
| `A_VOLUME_NOT_SUPPORTED` (resolver contract, ADR 0002 AR3) | (a) a `volume` request without `volume_support`; (c) a `binary_mask_policy` on a Z>1 position (BM5) | (a) and (c) unchanged. **(b) new:** a `plane` request that covers a position whose `z_count` > 1 is refused, one refusal per such position (sorted by path), **with or without** `volume_support` (VZ3: a volume is never served as planes; [choice 8](#modelling-choices-for-the-owners-review)). Order in the result: (a), then (b), then (c), each as listed; all that apply are reported; a refused request has no selection (unchanged). Resolver contract: the next version ([versioning](#versioning-and-compatibility)) |
| `VOLUME_STATISTICS_NOT_COMPUTED` (RunInputs, **new**) | n/a | A request for histograms, normalization or QC metrics of a volume (above) |
| `W_MIXED_PLANES_AND_VOLUMES` (§8 preprocessing warning, **new**) | n/a | Recorded in the run's checks (above); never blocks |
| ADR 0009 `R_CONSUMER_DIMENSIONS_NOT_ALLOWED`, kinds `volume` and `mixed_volumes` | Unreachable (gate 1) | Reachable once #438 lands. Unchanged by this ADR. In the notebook flow it is met first (ADR 0009 phase 1, at axis confirmation); `R_VOLUME_Z_UNCALIBRATED` is a run-publication check, so a run that breaks both reports both at the run |

**Precedence summary.** Description-time (`E_*`, `R_*` of §8 with today's order) is unchanged: no
Z rule is added there. At run publication, `R_VOLUME_Z_UNCALIBRATED` joins the run's other refusals
and is listed with them. At the hand-off the resolver reports (a), (b), (c) of
`A_VOLUME_NOT_SUPPORTED` with every other applicable `A_*` refusal, as today. A consumer's own guard
(ADR 0009 P-2 for MorphoFeature: every Z > 1 image and every mixed run refused before any provider
runs) stays, and is the final guard on routes that do not use the resolver.

### What stays refused

- **A 2-D mask for a volume.** The masks of an image keep the image's Z and T
  (`masks/checks.py:40-50`); a 2-D mask is never shared by the slices of a volume (owner decision of 5
  November 2026). Unchanged.
- **Converting a binary mask of a volume** (`binary_mask_policy` on Z > 1): `A_VOLUME_NOT_SUPPORTED`,
  ADR 0005 BM5, unchanged; the shared labeller labels 2-D planes only.
- **Segmentation hand-off and the tissue-mask card on a volume** (`segmentation_handoff.py:555-557`,
  `notebook_tissue_mask.py:50-51`): unchanged, preprocessing's own refusals.
- **Projection while masks have depth slices** (`projection_masks.py`): unchanged.
- **Histograms, normalization and QC metrics of a volume:** not computed, recorded, refused on
  request (VZ2).
- **A plane selection of a volume**, for any consumer (VZ3, (b) above).
- **The five forbidden names** (`axes`, `shared`, `plane_scope`, `z`, `projection`) in
  `morphobricks.toml`: still `E_FORBIDDEN_FIELD` (`i21` unchanged).

**Masks of a volume (minimal reading, [choice 5](#modelling-choices-for-the-owners-review)).** A mask of a
volume has the volume's Z extent. Its declared `representation` holds over the whole volume: in an
`instances` mask one value is **one 3-D object** of that FOV, identified by FOV key, mask ID, time
point and value (never by value alone, never per slice); `binary` keeps {0, v} over all its planes
(BM11, already file-wide); a `parent_labels` value is one group over the volume. The mask step's
per-plane evidence (pieces per plane, `mask_scan.py:42-44`) is shown as per-plane evidence only and is
never presented as 3-D connectivity; the representation stays a user confirmation (§4.5). No mask
field is added: a mask's Z comes from its file and is checked against its image.

### Versioning and compatibility

- **`morphobricks.toml`: amendment of v1, `schema_version` stays 1.** No field, type, enumeration or
  ID rule changes; §1's scope sentence and §4.7's reason text do. Every file valid before is valid
  after with the same meaning. A reader pinned to an earlier Spec commit (preprocessing) still refuses
  Z-stacks at its own description step, so it never publishes or runs a description over volumes; a
  description written under this amendment carries no trace of Z, so an older reader cannot misread
  a field. A reader states which rule it implements by the Spec commit it pins (conformance plan §1).
- **Run manifest: a new version** (the next integer after the version current when #438 lands; ADR
  0008 and ADR 0009 each take one, and the implementing PR states the number). New **required**
  fields per image: `z_count`, `t_count`, `spatial_unit`, `plane_statistics`; the warning record
  `W_MIXED_PLANES_AND_VOLUMES` in the run's checks. Read strictly (closed field set, unknown or
  missing refused). Under the one-version rule (ADR 0002 AR11 (7)) every older manifest is refused
  with today's message (run preprocessing again): no reader ever infers `z_count` from histogram rows
  again. This is the guard that keeps any consumer pinned to an older preprocessing from meeting a
  volume run.
- **Resolver contract: the next version** (5 if AR12's version 4 is current when it lands). Rule (b)
  changes what a `plane` request selects (nothing, for a volume), so a consumer pinned to the previous
  version must not accept the new resolver. Consumers accept **exactly** the new version (ADR 0005
  BM10), in every consumer at once.
- **Histogram table (ADR 0008): no version change.** Version 6 already has one row per plane; a
  volume has none. The cross-check against the manifest is `RunInputs`', not the normalization
  reader's.
- **ADR 0007 identity.** The run-folder identity includes the manifest's SHA-256, so the new fields
  change it; nothing is reused across the version change.
- **AR10.** Nothing is converted: an older run folder is refused, not upgraded; a projected run stays
  as it is.

### Interactions

- **ADR 0009 (consumer manifest).** This ADR is its P-1. It makes the `volume` and
  `mixed_volumes` kinds reachable, names the mixed-run warning those rules refer to
  (`W_MIXED_PLANES_AND_VOLUMES`), and keeps projection the only conversion fix, offered only where
  the planner accepts it (ADR 0009 "Fixes offered"). ADR 0009's P-2 (MorphoFeature refuses every
  Z > 1 image and every mixed run on every route) is still required before #438 lands. ADR 0009's
  `volume_support` in a consumer manifest (no Z > 1 image in any form) and rule (b) here now say the
  same thing at the hand-off for resolver consumers.
- **ADR 0002 AR3.** "3-D stays open, enabled later ... under its own ADR; nothing enables it now."
  This ADR enables **describing and handing off** volumes, not any consumer's 3-D analysis: no
  consumer declares `volume_support` because of it (the fiberfeatures direct route, MorphoObjects,
  MorphoFeature #157 each decide that in their own reviewed change). A one-slice volume still selects
  exactly what a plane request selects.
- **ADR 0005 BM5.** Unchanged and restated above.
- **ADR 0006 (fast mode).** Channels are independent of Z: the header checks of fast mode compare
  channel count, names and image type per image, never Z. Unchanged.
- **ADR 0001 AQ6, RH1, RC1 (RGB).** An RGB volume is a volume of the declared image type: it goes only
  to a consumer that declares both `rgb_support` and `volume_support`
  ([choice 9](#modelling-choices-for-the-owners-review)). RH1's three-sample rule is per image and
  independent of Z.
- **ADR 0008.** A volume has no row (above).

## Proposed normative text

Written into the normative files on acceptance; until then the current text holds.

**experiment-v1 §1**, replacing the paragraph "v1 analyses 2-D planes only. ... the number of time
points.":

> v1 describes 2-D images and Z-stacks (volumes). An included image is a **volume** when its confirmed
> `Z` role has size > 1; otherwise it is a plane image. Whether an image is a volume is a fact of the
> image and its confirmed roles, recorded in the run manifest; the file has no Z, axes, shared-plane or
> projection field (§4.7). A volume MUST have a recorded Z step, from its header or stated in
> `calibration.csv`, in a length unit (`R_VOLUME_Z_UNCALIBRATED`, §8); it is never guessed.
> Projecting a Z-stack to 2-D is an explicit, recorded preprocessing choice, never a default.
> Histograms, normalization and QC metrics are not computed for a volume, which the run records as
> "not computed: volume" (ADR 0010). A volume is handed only to a consumer that declares
> `volume_support`, and never as separate planes (ADR 0002 resolver contract). Time-lapses (T > 1) are
> allowed: the file has no T field. The homogeneity of an imaging unit (§8, `R_UNIT_NOT_HOMOGENEOUS`)
> compares what each axis means, never the number of time points or of depth slices.

**experiment-v1 §4.5**, a paragraph after "Mask files, pairing, completeness and fingerprints stay
in the run manifest.":

> A mask of a volume has the volume's depth slices (a 2-D mask is never shared by the slices of an
> image). Its `representation` holds over the whole volume: an `instances` value is one 3-D object of
> that FOV and time point; a `parent_labels` value is one group over the volume; the `binary` rule is
> already over all planes. A per-request conversion (§4.5c) of a mask with more than one depth slice
> is refused (`A_VOLUME_NOT_SUPPORTED`, ADR 0005 BM5).

**experiment-v1 §4.7**, the first row's "Belongs to": "Image/manifest records: Z, axes and
projection are facts of the images and of preprocessing's recorded conversions, never of this file
(preprocessing #173, #176; ADR 0010)".

**experiment-v1 §7**, a bullet: "**Amendment of v1 (ADR 0010).** Volumes may be described (§1). No
field, type or enumeration changes, so every file valid before stays valid with the same meaning; a
reader pinned to an earlier Spec commit refuses Z-stacks before describing them."

**experiment-v1 §8**, one row in the `R_*` table, and one paragraph after the precedence paragraphs:

> | `R_VOLUME_Z_UNCALIBRATED` | At run publication: one or more volumes (§1) have no Z step from the header or `calibration.csv`, or one stated as `pixels`; one refusal lists every such image (FOV key, path, depth slices) and names the fix (state the Z step in `calibration.csv`, or project the stacks); nothing is computed or published. Reported with every other run-publication refusal; it replaces none |

> **Mixed plane images and volumes (ADR 0010).** A run whose included images are not all plane images
> or all volumes is not refused by preprocessing: it records the warning `W_MIXED_PLANES_AND_VOLUMES`
> in the run's checks, with the counts of each kind and every image of each kind (FOV key, path, and
> depth slices for a volume), and the description can be published. `R_UNIT_NOT_HOMOGENEOUS` does not
> compare the number of depth slices; an absent `Z` role reads as one slice. A consumer that needs one
> kind per run refuses it itself.

**ADR 0002**, a section "Resolver contract version N: volumes (ADR 0010)": rule (b) above, the order
(a), (b), (c), and the exact accepted-version set.

**Conformance plan §4, row "Volume"**, replaced by: "A `volume` request is `A_VOLUME_NOT_SUPPORTED`
unless the consumer declares `volume_support`; a `plane` request covering a position with more than
one Z plane is `A_VOLUME_NOT_SUPPORTED` with or without it; with the capability, a one-slice volume
selects exactly what the plane request selects (`v01`); a volume is selected as every Z of one `t`.
Each consumer's declared capabilities are tested; P59-P68 (ADR 0010)."

## Rejected alternatives

- **A Z field in `morphobricks.toml`** (a unit key such as `volume = true`, or `z` per unit): a second
  statement of a fact the image already gives, which could disagree with it and would need its own
  contradiction refusal; it breaks §1 and §4.7's rule that the file holds no axes; and it would make the
  amendment a new field (readers pinned earlier would refuse it). Z is recorded where axes are.
- **Keeping gate 1 and adding an opt-out** (`allow_z` for 3-D tools): two ways to describe one
  experiment, and the description step would still decide something the hand-off decides (VZ1).
- **Per-plane histograms for volumes in the first step:** the owner chose "disabled" (VZ2); a per-plane
  result would be passed off as the volume's.
- **Serving a volume as planes to a plane-only consumer, or a per-plane opt-in:** dropped by the owner
  (#438 comment 3, VZ3).
- **Refusing a mixed description in preprocessing:** the owner chose a warning (VZ4).
- **Inferring Z extent from histogram rows** (today's `_fov`): wrong as soon as volumes have no rows.

## Proposed fixtures and conformance

**No new TOML fixture.** The description of a volume experiment has no field that differs from a 2-D
one, so a single-file fixture cannot express any rule here; `v01` (and `v08` for masks) serve as the
descriptions of the scenarios below. `i21`'s header comment "(v1 is 2-D only; ...)" is reworded on
acceptance to "a mask has its image's axes" (comment only; the expected code is unchanged). The
fixture counts do not change.

Scenarios for the conformance plan §3 (P41-P58 are proposed by ADR 0009, so these start at P59):

| # | Setup | Expected |
|---|---|---|
| P59 | `v01` with ZYX TIFF stacks (Z = 5), Z step in the header (µm) | Described, tagged and published without projection; run manifest: every image `z_count = 5`, `t_count = 1`, `spatial_unit = "volume"`, `plane_statistics = "not_computed: volume"`; histogram and QC tables have no row for them; `RunInputs.fovs()` gives `z_count = 5` from the manifest; the notebook names "not computed: volume" at the Run step |
| P60 | As P59, (a) no Z step anywhere; (b) Z stated as `pixels`; (c) Z stated in `calibration.csv` (µm); (d) header Z step in an unsupported unit | (a), (b), (d) `R_VOLUME_Z_UNCALIBRATED` listing every volume with the fix, nothing published; (c) accepted, Z source `stated`; a Z step is never copied from X, Y or another image |
| P61 | `v01` with `CTRL` volumes (Z = 5) and `DrugA` planes; and a variant with both kinds in one unit | Published; `W_MIXED_PLANES_AND_VOLUMES` recorded in the run's checks with both lists and counts; no `R_UNIT_NOT_HOMOGENEOUS` for Z extent; plane images have histograms and QC, volumes none |
| P62 | Resolver on P59's run: (a) `plane` request without `volume_support`; (b) `plane` with it; (c) `volume` without it; (d) `volume` with it | (a) and (b) `A_VOLUME_NOT_SUPPORTED` per position, no selection; (c) `A_VOLUME_NOT_SUPPORTED` (rule a); (d) one selection per `t` with every Z |
| P63 | Resolver on P61's run: `volume` with `volume_support`; `plane` without it | `volume`: volumes as every Z, plane images as one-slice volumes (AR3); `plane`: refused for every volume position, listed by path, no selection |
| P64 | `RunInputs` on P61's run: histograms, normalization fit and QC of every image | Plane images: their results; each volume: `VOLUME_STATISTICS_NOT_COMPUTED` naming it; never empty, zero or per-slice values; a pooled fit names the volumes left out |
| P65 | `v08` on P59's stacks: (a) `Nuclei` masks with Z = 5; (b) 2-D masks; (c) `TumorRegion` as objects with `binary_mask_policy` | (a) accepted, `instances` values read per FOV and time point over the volume; (b) refused by the mask check (Z differs); (c) `A_VOLUME_NOT_SUPPORTED` (BM5, F09 unchanged) |
| P66 | Projection on P59's stacks | Still offered, with no default method, beside *Keep the 3-D stacks*; the copy and its conversion record version 4 as today; the projected run is all planes |
| P67 | A T-only time-lapse (T = 10, no Z) and a one-slice Z (Z = 1) | Unchanged from today: plane images, histograms and QC per plane, no Z calibration required |
| P68 | Versions | A run manifest of the previous version is refused by `RunInputs` with the fix; a consumer pinned to the previous resolver version refuses the new one before any read; a run folder whose histogram table has a row for a volume (or none for a plane image) is refused |

MorphoFeature's own rows (P-2: every Z > 1 image and every mixed run refused on every route) are
ADR 0009's P49.

## Modelling choices for the owner's review

None of these is an owner decision; each may be amended.

1. **No Z field in `morphobricks.toml`** (volume-ness from the confirmed roles, recorded in the run
   manifest). *Alternative:* a per-unit declaration `volume = true` checked against the images (a new
   field and a new contradiction code; see [rejected alternatives](#rejected-alternatives)).
2. **Amendment of v1, not `schema_version = 2`.** *Alternative:* a new schema version, so that a file
   itself says it may describe volumes; it would change no byte of the file except the version and
   force every reader to accept two versions or refuse every existing file (AR10).
3. **The Z-calibration refusal sits at run publication, not at `describe`.** The notebook shows the
   gap at the Axes step. *Alternative:* also block `describe` (calibration is not in the description,
   so `describe` would have to read `calibration.csv` and headers it does not read today).
4. **Only Z is required for volumes; X and Y keep today's rules** (they may be uncalibrated or
   `pixels`). *Alternative:* require X, Y and Z in a length unit for every volume, since any 3-D
   measure mixes the three axes and an anisotropy ratio needs all three. Recommended for the owner to
   weigh: the stricter rule is closer to "no guessed calibration" for 3-D measures.
5. **Volume masks are accepted, with the image's Z extent, and read over the whole volume** (an
   `instances` value is one 3-D object per FOV and time point). *Alternative:* refuse every mask of a
   volume in the first step (simplest; masks then need their own later amendment), or a mask field
   declaring a "volume mask" (a new field, rejected for the same reason as choice 1).
6. **One field `plane_statistics` per image covering histograms, normalization and QC together**, value
   `"not_computed: volume"`; a pooled fit names the volumes it left out. *Alternatives:* one status per
   product (more fields, the same information while all three are disabled together); a run-level
   list of volumes instead of a per-image field.
7. **A unit mixing volumes and plane images is only warned**, like a run (the owner's warning applies
   to "a description in which some images have a Z stack and others don't"). *Alternative:* refuse a
   mix **within one unit** as `R_UNIT_NOT_HOMOGENEOUS` (one acquisition, two protocols) and warn only
   across units. See open question 1.
8. **Rule (b): a `plane` request on a volume is refused even with `volume_support`.** *Alternative:*
   allow a volume-capable consumer to ask for single planes of a volume (fiberfeatures direct route
   per-plane reads); that would reintroduce a slicing path the owner dropped for MorphoFeature.
9. **RGB volumes are allowed** and need both `rgb_support` and `volume_support`. *Alternative:* refuse
   RGB volumes in the first step.
10. **Names:** `R_VOLUME_Z_UNCALIBRATED`, `W_MIXED_PLANES_AND_VOLUMES` (a preprocessing warning code in
    §8, which lists no warning today), `VOLUME_STATISTICS_NOT_COMPUTED` (a RunInputs code, not an
    experiment-v1 or resolver code), the manifest fields `z_count`, `t_count`, `spatial_unit`,
    `plane_statistics`. *Alternatives:* a lower-case preprocessing issue code for the warning
    (`mixed_planes_and_volumes`), or the RunInputs refusal as a resolver-contract code.
11. **Z extent and calibration are not compared between images** (different extents and steps are
    allowed and recorded; today's `different_plane_counts` and `different_pixel_sizes` stay warnings).
    *Alternative:* refuse a run whose volumes differ in Z step.

## Open questions for the owner

1. **Mix inside one imaging unit:** warn (as for a run, choice 7) or refuse as
   `R_UNIT_NOT_HOMOGENEOUS`?
2. **X and Y calibration for volumes** (choice 4): keep today's rules, or require all three axes?
3. **Masks of volumes in the first step** (choice 5): accept them with the whole-volume reading, or
   refuse them until a later amendment?
4. **`plane` requests on a volume by a volume-capable consumer** (choice 8): always refused, or
   allowed for a consumer that declares `volume_support`?
5. **Where `R_VOLUME_Z_UNCALIBRATED` blocks** (choice 3): the run only, or `describe` too?
