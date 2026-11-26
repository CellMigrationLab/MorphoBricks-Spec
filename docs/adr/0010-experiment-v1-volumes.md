# ADR 0010: experiment-v1 volumes (Z-stacks described and handed off without projection)

- **Status:** **Proposed** (24 November 2026). Not implemented. The owner decisions it encodes
  (preprocessing#438, owner comments of 23 and 24 November 2026, the order decided for this
  work, and the owner decisions of 26 November 2026) are recorded below as accepted inputs and are not reopened. What this ADR adds is their
  encoding: what a described volume is, its Z calibration, how a volume is recorded in a run,
  which existing refusals change and in which order, what stays refused, and the versioning
  impact. Everything that is a choice, not an owner decision, is listed under
  [modelling choices](#modelling-choices-for-the-owners-review) with its alternatives; the
  questions left for the owner are under [open questions](#open-questions-for-the-owner).
  **Revised** with the owner decisions of 26 November 2026 (VZ8-VZ12 below): the five open questions
  of the first draft are answered, VZ3 is narrowed and VZ5 is replaced (see
  [decision history](#decision-history)). The status stays **Proposed**. **Revised again** with the
  owner's answers of 26 November 2026 to the eight questions that revision raised (VZ13-VZ20 below):
  ADR 0009 was amended on its own branch (O9 three `volume_support` values, O10
  `requires_calibration`), the recorded calibration code is one `W_AXIS_UNCALIBRATED` naming the
  axis, and no question is open.
- **Is** prerequisite **P-1** of [ADR 0009](https://github.com/CellMigrationLab/MorphoBricks-Spec/pull/55)
  (consumer manifest, draft PR #55, branch `claude/adr-0009-consumer-manifest`, first read at
  `d2dfbcc2b4237437d2868e6c481e001d15eadece`; its O9 and O10 amendment, made for this ADR, at
  `35cb15dd0a3de1d6f8a55942121b4939d0cd684c`): "the #438 normative amendment of experiment-v1 §1
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
  reading of `R_UNIT_NOT_HOMOGENEOUS` for `Z`; one recorded calibration warning
  `W_AXIS_UNCALIBRATED` with its axis, which records and never refuses (VZ12, VZ17, VZ18); one recorded warning
  `W_MIXED_PLANES_AND_VOLUMES`); [ADR 0002](0002-shared-request-resolver.md) AR3
  (the next resolver contract version: a `plane` request on a volume is served only for the Z
  indices it names explicitly, never by expanding Z; one new resolver code `A_Z_INDEX_NOT_IN_IMAGE`);
  [ADR 0008](0008-plane-histograms-v6.md) (a volume has no row; no table version change); the
  [conformance plan](../conformance-plan.md) §4 row "Volume" and new scenarios; the
  [roadmap](../roadmap.md) §9 sentence on 3-D. The replacement text is given verbatim
  [below](#proposed-normative-text); it is written into the normative files only on acceptance.
  No fixture, golden or validator changes in this PR. The one tool change is the consistency test's
  list of codes a proposed ADR may name before acceptance (`tools/test_spec_consistency.py`,
  `PROPOSED_CODES`: `A_Z_INDEX_NOT_IN_IMAGE`, allowed in this file only until acceptance moves it to
  the resolver codes).
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
| VZ3 | **A Z run only goes to volume-capable bricks.** Nothing splits a volume into slices for a plane-only consumer. *Narrowed by VZ11 (26 November 2026): nothing splits a volume **implicitly**; a plane request that names its Z indices explicitly is served and recorded* | #438 comments 2 and 3; ADR 0009 CM5 |
| VZ4 | **Mixed 2-D/3-D runs:** refused by MorphoFeature (and any consumer that needs one unit per run); **only warned** in preprocessing, which can publish such a description; the warning names the counts of each kind, says MorphoFeature will refuse the run as it stands (split, or project the stacks), and is **recorded in the run's checks**, not only shown | #438 comments 4 and 5; ADR 0009 CM5 |
| VZ5 | ~~**Z calibration is mandatory for a described volume and never guessed**~~ *Replaced by VZ12 (26 November 2026): never guessed; when unknown it is recorded as unknown with a code, and it blocks neither `describe` nor publication* | #438 "Tests": "A Z stack is described and published without projection, and its Z calibration is mandatory and never guessed" |
| VZ6 | **Order:** Stable 1, then ADR 0009 accepted, then this amendment, then #438 | #438 comment of 24 November 2026 |
| VZ7 | **This design gets an external review round** (ChatGPT) before acceptance | owner practice for important designs |

### Owner decisions of 26 November 2026 (recorded, accepted; not reopened by this ADR)

They answer the five open questions of the first draft (one per decision) and are encoded below
where marked with their ID.

| # | Decision | Answers |
|---|---|---|
| VZ8 | **Volumes and plane images mixed in one unit** (a biological repeat or a condition): preprocessing **warns** and records the warning in the run report (`W_MIXED_PLANES_AND_VOLUMES`); it does **not** refuse, and `R_UNIT_NOT_HOMOGENEOUS` is not raised for Z extent. MorphoFeature still refuses every mixed plane/volume run for now (ADR 0009 P-2) | open question 1, modelling choice 7 |
| VZ9 | **X and Y calibration of a volume: the same rule as for a plane image.** Never guessed: the user enters it, or it is recorded as unknown with a coded reason. Nothing stricter is required of a volume | open question 2, modelling choice 4 |
| VZ10 | **Volume (3-D) label masks are accepted in the first Z release**, with the same identity checks as 2-D masks: a mask is paired with its image by recorded identity (FOV key, mask ID, file), and an object is identified by FOV key, mask ID, time point and value, never by its numeric label alone | open question 3, modelling choice 5 |
| VZ11 | **Plane requests on a volume are allowed when the consumer asks explicitly** ("if the consumer asks, they can have it"). Preprocessing records what is available: volume or plane, Z count, and the calibration of each axis, unknowns included. It can optionally read what each consumer accepts (its declared requirements, [ADR 0009](https://github.com/CellMigrationLab/MorphoBricks-Spec/pull/55)'s consumer manifest), so that a mismatch fails early, at `describe` or at the hand-off, not late. A plane request MUST be explicit and recorded (the Z index or indices); it is never an implicit projection and never a silent expansion of Z into planes. **This reverses the owner decision of 23 November 2026** ("no per-plane opt-in; `run_config._planes` stops expanding Z"; #438 comment 3) for explicit requests only | open question 4, modelling choice 8 |
| VZ12 | **An uncalibrated Z (`R_VOLUME_Z_UNCALIBRATED`) does not block `describe`.** The run records "Z step unknown" with that code. A consumer that needs a Z step refuses early through its declared requirements. The user can enter the step; it is never guessed. *Code renamed and merged by VZ17 and VZ18: `W_AXIS_UNCALIBRATED` with `axis = "z"`* | open question 5, modelling choice 3 |

### Owner answers of 26 November 2026 to the second round (VZ13-VZ20; recorded, accepted)

They answer the eight questions the first revision raised (its Q1-Q8), in that order.

| # | Answer | Encoded |
|---|---|---|
| VZ13 | **ADR 0009's `volume_support` takes three values:** `none`, `planes` (accepts explicit `z_indices` of volumes) and `volumes` (whole volumes). ADR 0009 is amended on its own PR (O9) and CM5 routes Z runs by them | ADR 0009 O9 at `35cb15d`; [plane requests](#plane-requests-on-a-volume-vz11), [interactions](#interactions) |
| VZ14 | **Calibration needs are added to consumer-manifest v1** (`requires_calibration`, for example `["x", "y", "z"]`). Preprocessing checks them at `describe` and at the hand-off and refuses early, naming the consumer. This revises ADR 0009 CM4, recorded there | ADR 0009 O10 at `35cb15d` (kind `calibration` of `R_CONSUMER_DIMENSIONS_NOT_ALLOWED`) |
| VZ15 | **MorphoFeature:** P-2 stays for now. Later MorphoFeature may serve volumes through explicit `z_indices`, by its own reviewed change | [prerequisites](#prerequisites-and-order) |
| VZ16 | **ADR 0005 BM5 is kept:** a binary-mask conversion on a position with Z > 1 is refused, also for an explicit plane request | [plane requests](#plane-requests-on-a-volume-vz11), P65 |
| VZ17 | **Rename `R_VOLUME_Z_UNCALIBRATED` to `W_VOLUME_Z_UNCALIBRATED`** | Subsumed by VZ18 (below) |
| VZ18 | **One reason code for any unknown axis**, written on every image record (planes and volumes), naming the axis (for example `W_AXIS_UNCALIBRATED` with `axis` x, y or z); check whether the per-axis volume code is still needed, prefer one code | **One code, `W_AXIS_UNCALIBRATED`.** A per-axis volume code is not needed: `W_VOLUME_Z_UNCALIBRATED` would say exactly what `W_AXIS_UNCALIBRATED` with `axis = "z"` says on a volume's record (a plane image has no Z step to lack), so VZ17's name is never introduced |
| VZ19 | **The mixed planes/volumes warning applies at run, condition, biological-repeat and imaging-unit level** and lists each place that mixes them. Confirmed | [the mixed-run warning](#how-a-volume-is-recorded-in-a-run) (unchanged) |
| VZ20 | **An unknown Z step never blocks anything in preprocessing:** not `describe`, not the run, not publication. Only a consumer that declares the need (VZ14) refuses, early and by name. Confirmed | [Z calibration](#what-a-described-volume-is) |

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
- **Z calibration (VZ12, replacing VZ5).** A volume's Z step is a length when its source is
  `header` or `stated` (`calibration.csv`), with a supported length unit and a finite value > 0 (the
  existing unit rule, `length_units.py`). Otherwise it is **recorded, never guessed**: with no source
  (none in the header, none stated, or a header step in an unsupported unit) the run records the Z
  step as `unknown` with the reason code `W_AXIS_UNCALIBRATED`, `axis = "z"` (VZ18); a Z stated as
  `pixels` (the user's deliberate statement) is recorded as `pixels` with the same code, since it
  gives no length either. Neither blocks `describe`, the run or publication, nor anything else in
  preprocessing (VZ20). The user can enter the step at any
  time (`calibration.csv`), which is a re-run, never an edit of a recorded value. A consumer that
  needs a Z step refuses early through its declared requirements (`requires_calibration` with `z`,
  ADR 0009 O10, checked at `describe --consumer` and at the run, naming the consumer; VZ14) and, on
  every route, through its own runtime guard; it
  never reads an unknown step as 1, as the X step, or as zero. The Z step is never taken from X or Y,
  from another image, from a projection's metadata (already excluded by `fit_to_roles`), or from a
  default. Different Z steps between images are allowed and recorded per image (today's warning
  `different_pixel_sizes` stays a warning).
- **X and Y calibration (VZ9).** The same rule as for a plane image, nothing stricter: from the header
  or stated, or stated as `pixels`, or, with neither, recorded as `unknown` with the same one code,
  `W_AXIS_UNCALIBRATED` with `axis = "x"` or `"y"` (VZ18), on plane images and volumes alike. Never
  guessed, never copied from Z or from another image.
- **Where calibration is shown and recorded.** The notebook shows every unknown step on the Axes
  step's calibration card as soon as the roles are confirmed, so the user meets it early; `describe`
  is never blocked by it (calibration is not part of the description, §1). The run manifest records,
  per image and per space axis, the value and unit, the source (`header`, `stated`, `pixels` or
  `unknown`) and, for `unknown` and `pixels`, the reason code `W_AXIS_UNCALIBRATED`
  ([below](#how-a-volume-is-recorded-in-a-run)). Absent stays absent: an unknown step is never written
  as 0, 1, NaN or an empty string.

### How a volume is recorded in a run

All of it in the run manifest (`run_manifest.json`), never in `morphobricks.toml`:

- **Per image, the confirmed sizes.** Every image entry records `z_count` and `t_count`, the sizes of
  its confirmed `Z` and `T` roles (1 for an absent role), and `spatial_unit`: `"plane"` (z_count = 1)
  or `"volume"` (z_count > 1). Both are written from the confirmed roles at the run and are
  **required** in the new manifest version. `RunInputs.fovs()` reads `Fov.z_count` and `Fov.t_count`
  from these fields, **never** from histogram rows; the `or {0}` default of `_fov` is removed. A
  manifest entry whose `spatial_unit` disagrees with its `z_count` is refused
  (`ManifestFormatError`).
- **Per image, the calibration of each space axis (VZ9, VZ11, VZ12).** `calibration`: one entry per
  space axis the image has (`x`, `y`, and `z` for an image with a `Z` role; lower-case names of the
  confirmed roles `X`, `Y`, `Z`, as in ADR 0009's `requires_calibration`), each
  `{"axis", "source", "size", "unit", "reason"}`: `source` is `header`, `stated`, `pixels` or
  `unknown`; `size` and `unit` are the recorded length for `header` and `stated` and `null`
  otherwise (never 0 or 1); `reason` is `null` for a length and `W_AXIS_UNCALIBRATED` for every
  axis without one (`unknown` or `pixels`), on plane images and volumes alike (VZ18). The
  field set is closed and every key is required. This is the record that lets a consumer's declared
  requirements be checked early, and its own guard late, without reading a header again.
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
- **The mixed-run warning (VZ4, VZ8).** When the included images of a run are not all of one kind,
  preprocessing records the warning `W_MIXED_PLANES_AND_VOLUMES` in the run's checks
  (`run_manifest.json`, beside the other recorded issues) and in the run report: the counts of each
  kind, every volume (FOV key, path, `z_count`) and every plane image (FOV key, path), sorted by FOV
  key then path, then every condition, biological repeat and imaging unit that itself holds both
  kinds (VZ8: a mix inside one unit is warned, never refused), and the text "MorphoFeature refuses
  this run as it stands: split it into two experiments, or project the stacks". It never blocks
  publication and never disappears because a consumer was or was not checked (ADR 0009, "#438 and
  ADR 0005").
- **The calibration warning (VZ12, VZ18, VZ20).** When any included image has a space axis without a
  length, the run's checks and the run report also list `W_AXIS_UNCALIBRATED` once per such axis,
  each naming every such image (FOV key, path, `z_count`, source) and the fix (state the step in
  `calibration.csv` and run again). It is a warning, not a refusal: it never blocks anything in
  preprocessing. A chosen consumer whose `requires_calibration` lists the axis refuses it as ADR
  0009's kind `calibration`.
- **The projection record is unchanged.** A projected run keeps conversion record version 4 and
  `RunInputs.projection`; its images are planes.

### Plane requests on a volume (VZ11)

- **The request.** The resolver `Request` gains `z_indices`: `None` (the default) or a non-empty,
  strictly increasing tuple of integers ≥ 0, the Z positions the consumer asks for, applied to every
  volume the request covers. It is only valid with `planes = "plane"`; with `volume`, or empty,
  repeated, unsorted, negative or non-integer, it is a malformed request (`ValueError`), not a
  refusal (ADR 0002's rule for malformed requests).
- **Served only when explicit.** On a position whose `z_count` > 1, a `plane` request with
  `z_indices` selects exactly `(t, z)` for every `t` and every listed `z`, nothing else. A `plane`
  request **without** `z_indices` on such a position is refused (`A_VOLUME_NOT_SUPPORTED`, rule (b)
  [below](#refusals-that-change-and-their-precedence)): Z is never expanded into planes silently, and no
  plane is chosen for the consumer (no "middle slice", no first slice, no projection). On a plane
  image (`z_count` = 1), `z_indices` must be exactly `(0,)` or `None`; any other index is refused as
  below, never ignored.
- **An index the image does not have.** A listed `z` ≥ the `z_count` of a covered position is
  `A_Z_INDEX_NOT_IN_IMAGE` (a resolver-contract code, **new**), one refusal per such position (FOV
  key, path, `z_count`, the indices it lacks), sorted by path; nothing is selected (a refused request
  has no selection). It is never clipped to the image, never wrapped and never answered for the
  positions that do have it only.
- **Capabilities.** An explicit plane request needs no `Capabilities.volume_support`: it reads
  planes; it is the consumer's own, recorded choice (VZ11). Whether a consumer may make one is its
  declaration in ADR 0009's consumer manifest (O9, VZ13): `volume_support = "none"` takes no `Z` > 1
  image in any form and is refused before the hand-off; `"planes"` takes volumes only as explicit
  `z_indices` planes and opens `RunInputs` with `Capabilities.volume_support = false`, so a whole
  `volume` request is refused (rule (a)); `"volumes"` maps to `Capabilities.volume_support = true` and
  may make both. ADR 0005 BM5 is kept (VZ16): a `binary_mask_policy` on a position with more than one
  Z plane is refused also for an explicit plane request.
- **The record.** The resolver's provenance records the request's `z_indices` (`null` when absent),
  and each `FovSelection` keeps its `(t, z)` list as today; every consumer copies them as is into its
  run record, and `z_indices` is part of every output and cache identity, like `fov_subset` (ADR 0002
  AR12). A per-plane output of a volume therefore always names the Z it came from and is never
  presented as the volume's result. Histograms, normalization and QC of a volume stay not computed
  for these planes too (VZ2): an explicit plane request reads pixels, it does not create statistics.

### Refusals and warnings that change, and their precedence

Refusals block; warnings and recorded reasons are written to the run's checks and report and never
block. The table says which each code is.

| Code (owner) | Kind | Today | After this ADR |
|---|---|---|---|
| `z_stack_not_supported` (preprocessing issue code; experiment-v1 §1's projection rule) | refusal, **removed** | Error at header check and axis review; Z-stack never described | **Removed as a refusal.** No replacement at the description step. Projection stays an offered, recorded choice with no default, beside *Keep the 3-D stacks* (now enabled). `allow_z` loses its purpose (implementation detail of #438) |
| `R_UNIT_NOT_HOMOGENEOUS` (§8) | refusal, unchanged | "interpreted axes" may differ in a unit; T counts never compared (§1) | Unchanged code and precedence. For `Z`, as for `T`, it compares the role's **meaning**, never its size; an absent `Z` role and a `Z` of size 1 read the same. A unit whose images differ only in Z extent, plane images included, is **not** refused: it is the recorded warning `W_MIXED_PLANES_AND_VOLUMES` (VZ8) |
| `W_MIXED_PLANES_AND_VOLUMES` (§8 preprocessing warning, **new**) | warning | n/a | Recorded in the run's checks and report when the run, or any condition, biological repeat or imaging unit of it, holds both kinds (VZ4, VZ8); never blocks |
| `W_AXIS_UNCALIBRATED` (§8 preprocessing warning, **new**; replaces the first revision's `R_VOLUME_Z_UNCALIBRATED`, VZ17, VZ18) | warning | Preprocessing at `b683c7c` reports an uncalibrated axis in words, with no code (`calibration.py:1-9`) | The one code for any space axis without a length (`unknown` or `pixels`), on plane images and volumes alike, with `axis` `x`, `y` or `z`: per image in `calibration` and once per axis in the run's checks and report with every such image and the fix. Blocks nothing in preprocessing (VZ20). A consumer that needs the axis refuses on it: early by `requires_calibration` (ADR 0009 O10, kind `calibration`, naming the consumer) and at run time by its own guard |
| `A_VOLUME_NOT_SUPPORTED` (resolver contract, ADR 0002 AR3) | refusal | (a) a `volume` request without `volume_support`; (c) a `binary_mask_policy` on a Z>1 position (BM5) | (a) and (c) unchanged ((c) also for an explicit plane request). **(b) new:** a `plane` request **without `z_indices`** that covers a position whose `z_count` > 1 is refused, one refusal per such position (sorted by path), with or without `volume_support`: Z is never expanded into planes implicitly (VZ11). A `plane` request **with** `z_indices` is not refused by (b). Order in the result: (a), then (b), then (c), each as listed; all that apply are reported; a refused request has no selection (unchanged). Resolver contract: the next version ([versioning](#versioning-and-compatibility)) |
| `A_Z_INDEX_NOT_IN_IMAGE` (resolver contract, **new**) | refusal | n/a | A `plane` request's `z_indices` names a Z position that a covered image does not have ([above](#plane-requests-on-a-volume-vz11)); one refusal per such position, after `A_VOLUME_NOT_SUPPORTED` in the result; never clipped or partly served |
| `VOLUME_STATISTICS_NOT_COMPUTED` (RunInputs, **new**) | refusal (of a request) | n/a | A request for histograms, normalization or QC metrics of a volume ([above](#how-a-volume-is-recorded-in-a-run)) |
| ADR 0009 `R_CONSUMER_DIMENSIONS_NOT_ALLOWED`, kinds `volume`, `mixed_volumes` and `calibration` | refusal | `volume`, `mixed_volumes` unreachable (gate 1); `calibration` did not exist | `volume` (for `volume_support = "none"`) and `mixed_volumes` reachable once #438 lands; `calibration` (ADR 0009 O10, VZ14) for an axis the consumer's `requires_calibration` lists. Met at axis confirmation (ADR 0009 phase 1), at `describe --consumer` and at the run's re-check, so a mismatch fails at describe or before the hand-off, never late (VZ11, VZ14) |

**Precedence summary.** Description-time (`E_*`, `R_*` of §8 with today's order) is unchanged: no
Z rule is added there, and no calibration rule blocks it (VZ12). At run publication nothing new
refuses in preprocessing's own rules: `W_MIXED_PLANES_AND_VOLUMES` and `W_AXIS_UNCALIBRATED` are recorded beside the run's
other checks. At the hand-off the resolver reports (a), (b), (c) of `A_VOLUME_NOT_SUPPORTED`, then
`A_Z_INDEX_NOT_IN_IMAGE`, with every other applicable `A_*` refusal, as today. A consumer's own guard
(ADR 0009 P-2 for MorphoFeature: every Z > 1 image and every mixed run refused before any provider
runs) stays, and is the final guard on routes that do not use the resolver; so is a consumer's own
refusal of an unknown Z step it needs.

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
- **An implicit plane selection of a volume**, for any consumer: a `plane` request without
  `z_indices` (VZ11, (b) above). Nothing projects, picks a slice or expands Z on the consumer's
  behalf.
- **The five forbidden names** (`axes`, `shared`, `plane_scope`, `z`, `projection`) in
  `morphobricks.toml`: still `E_FORBIDDEN_FIELD` (`i21` unchanged).

**Masks of a volume (VZ10).** Volume (3-D) label masks are accepted in the first Z release, with the
identity checks of 2-D masks: a mask is paired with its image by the recorded identity of the run
manifest (FOV key, mask ID, file), never by file order, numeric label or name similarity, and the
mask's Z and T extents must equal its image's (`masks/checks.py:40-50`). Its declared
`representation` holds over the whole volume: in an `instances` mask one value is **one 3-D object**
of that FOV, identified by FOV key, mask ID, time point and value (never by the value alone, never
per slice, and never joined with a value of another mask or FOV); `binary` keeps {0, v} over all its
planes (BM11, already file-wide); a `parent_labels` value is one group over the volume. The mask
step's per-plane evidence (pieces per plane, `mask_scan.py:42-44`) is shown as per-plane evidence
only and is never presented as 3-D connectivity; the representation stays a user confirmation
(§4.5). An explicit plane request reads the mask's planes at the same `z_indices`; an object's
identity stays the 3-D one (the value names one object across the planes read). No mask field is
added: a mask's Z comes from its file and is checked against its image.

### Versioning and compatibility

- **`morphobricks.toml`: amendment of v1, `schema_version` stays 1.** No field, type, enumeration or
  ID rule changes; §1's scope sentence and §4.7's reason text do. Every file valid before is valid
  after with the same meaning. A reader pinned to an earlier Spec commit (preprocessing) still refuses
  Z-stacks at its own description step, so it never publishes or runs a description over volumes; a
  description written under this amendment carries no trace of Z, so an older reader cannot misread
  a field. A reader states which rule it implements by the Spec commit it pins (conformance plan §1).
- **Run manifest: a new version** (the next integer after the version current when #438 lands; ADR
  0008 and ADR 0009 each take one, and the implementing PR states the number). New **required**
  fields per image: `z_count`, `t_count`, `spatial_unit`, `calibration`, `plane_statistics`; the
  warnings `W_MIXED_PLANES_AND_VOLUMES` and `W_AXIS_UNCALIBRATED` in the run's checks. Read strictly (closed field set, unknown or
  missing refused). Under the one-version rule (ADR 0002 AR11 (7)) every older manifest is refused
  with today's message (run preprocessing again): no reader ever infers `z_count` from histogram rows
  again. This is the guard that keeps any consumer pinned to an older preprocessing from meeting a
  volume run.
- **Resolver contract: the next version** (5 if AR12's version 4 is current when it lands). Rule (b)
  changes what a `plane` request without `z_indices` selects (nothing, for a volume), the request
  gains `z_indices` and the provenance records it, and `A_Z_INDEX_NOT_IN_IMAGE` is new, so a consumer
  pinned to the previous version must not accept the new resolver. Consumers accept **exactly** the new version (ADR 0005
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
  Z > 1 image and every mixed run on every route) is still required before #438 lands and is not
  relaxed by VZ11 (VZ8, VZ15).
- **Consumer-declared requirements (ADR 0009; VZ11, VZ12).** The owner's "preprocessing can
  optionally read what each consumer accepts" **is** ADR 0009's consumer manifest: when the user
  picks a consumer, its `[dimensions]` are checked against what this ADR records (volume or plane,
  `z_count`, the mix), at axis confirmation, at `describe --consumer` and at the run, so a mismatch
  fails early; with *No consumer check* nothing is read and the consumer's own guard refuses at the
  hand-off (ADR 0009 O1, O5). ADR 0009 was amended for this ADR (O9, O10 at `35cb15d`): a consumer
  that takes **explicit planes of a volume** but not whole volumes declares
  `volume_support = "planes"` (VZ13), and a consumer that **needs a step** lists the axis in
  `requires_calibration` (VZ14, revising ADR 0009 CM4); the early check reads this ADR's
  `calibration` record and refuses as kind `calibration`, naming the consumer. Each consumer still
  guards both itself, on every route, from `z_count` and `calibration` as `RunInputs` gives them.
- **ADR 0002 AR3.** "3-D stays open, enabled later ... under its own ADR; nothing enables it now."
  This ADR enables **describing and handing off** volumes, not any consumer's 3-D analysis: no
  consumer declares `volume_support` because of it (the fiberfeatures direct route, MorphoObjects,
  MorphoFeature #157 each decide that in their own reviewed change). A one-slice volume still selects
  exactly what a plane request selects. AR3's "a selection is one plane or one Z-volume" holds: an
  explicit plane request (VZ11) yields plane selections, each naming its `(t, z)`.
- **ADR 0005 BM5.** Unchanged and restated above; it also applies to an explicit plane request on a
  volume (VZ16).
- **ADR 0006 (fast mode).** Channels are independent of Z: the header checks of fast mode compare
  channel count, names and image type per image, never Z. Unchanged.
- **ADR 0001 AQ6, RH1, RC1 (RGB).** An RGB volume is a volume of the declared image type: it goes only
  to a consumer that declares `rgb_support` and a `volume_support` of `"planes"` or `"volumes"`
  (ADR 0009 O9; [choice 9](#modelling-choices-for-the-owners-review)). RH1's three-sample rule is per image and
  independent of Z.
- **ADR 0008.** A volume has no row (above).

## Proposed normative text

Written into the normative files on acceptance; until then the current text holds.

**experiment-v1 §1**, replacing the paragraph "v1 analyses 2-D planes only. ... the number of time
points.":

> v1 describes 2-D images and Z-stacks (volumes). An included image is a **volume** when its confirmed
> `Z` role has size > 1; otherwise it is a plane image. Whether an image is a volume is a fact of the
> image and its confirmed roles, recorded in the run manifest; the file has no Z, axes, shared-plane or
> projection field (§4.7). A volume's Z step, like every pixel size, comes from its header or is
> stated in `calibration.csv`; it is never guessed. Any space axis of any image without a length is
> recorded as unknown (or `pixels`) with the warning `W_AXIS_UNCALIBRATED` naming the axis (§8), which
> blocks nothing in preprocessing; a consumer that declares it needs the axis refuses (consumer
> manifest, ADR 0009). Projecting a Z-stack to 2-D is an explicit, recorded preprocessing choice, never a default.
> Histograms, normalization and QC metrics are not computed for a volume, which the run records as
> "not computed: volume" (ADR 0010). A whole volume is handed only to a consumer that declares
> `volume_support = "volumes"`; planes of a volume are handed only for Z indices the consumer names explicitly
> in its request, which is recorded, and never by an implicit expansion of Z or a projection (ADR 0002
> resolver contract). Time-lapses (T > 1) are allowed: the file has no T field. The homogeneity of an
> imaging unit (§8, `R_UNIT_NOT_HOMOGENEOUS`) compares what each axis means, never the number of time
> points or of depth slices.

**experiment-v1 §4.5**, a paragraph after "Mask files, pairing, completeness and fingerprints stay
in the run manifest.":

> A mask of a volume has the volume's depth slices (a 2-D mask is never shared by the slices of an
> image) and is paired with it by recorded identity, as a mask of a plane image is. Its
> `representation` holds over the whole volume: an `instances` value is one 3-D object of that FOV,
> mask and time point, never identified by its value alone; a `parent_labels` value is one group over the volume; the `binary` rule is
> already over all planes. A per-request conversion (§4.5c) of a mask with more than one depth slice
> is refused (`A_VOLUME_NOT_SUPPORTED`, ADR 0005 BM5).

**experiment-v1 §4.7**, the first row's "Belongs to": "Image/manifest records: Z, axes and
projection are facts of the images and of preprocessing's recorded conversions, never of this file
(preprocessing #173, #176; ADR 0010)".

**experiment-v1 §7**, a bullet: "**Amendment of v1 (ADR 0010).** Volumes may be described (§1). No
field, type or enumeration changes, so every file valid before stays valid with the same meaning; a
reader pinned to an earlier Spec commit refuses Z-stacks before describing them."

**experiment-v1 §8**, one paragraph after the precedence paragraphs (no row in the `R_*` refusal
table: both codes below record and never refuse):

> **Volumes: recorded, not refused (ADR 0010).** (1) A run whose included images are not all plane
> images or all volumes, or any condition, biological repeat or imaging unit of which holds both
> kinds, is not refused by preprocessing: it records the warning `W_MIXED_PLANES_AND_VOLUMES` in the
> run's checks and report, with the counts of each kind, every image of each kind (FOV key, path, and
> depth slices for a volume) and every condition, repeat and unit that holds both, and the
> description can be published. `R_UNIT_NOT_HOMOGENEOUS` does not compare the number of depth slices;
> an absent `Z` role reads as one slice. A consumer that needs one kind per run refuses it itself.
> (2) A space axis (`x`, `y`, or `z` of a volume) of any included image whose size has no source
> (none in the header or `calibration.csv`, or a unit that is not a supported length) or is stated as
> `pixels` is recorded with the warning `W_AXIS_UNCALIBRATED` and the axis, per image and once per
> axis in the run's checks and report with every such image (FOV key, path, depth slices, source) and
> the fix (state the step in `calibration.csv` and run again). It blocks nothing in preprocessing:
> not `describe`, the run or publication; the step is never guessed, and is never written as 0, 1 or
> another axis's size. A chosen consumer whose manifest requires the axis refuses
> (`R_CONSUMER_DIMENSIONS_NOT_ALLOWED`, kind `calibration`).

**ADR 0002**, a section "Resolver contract version N: volumes (ADR 0010)": the request field
`z_indices`, rule (b) above, `A_Z_INDEX_NOT_IN_IMAGE` (added to the contract's codes), the order (a),
(b), (c), then `A_Z_INDEX_NOT_IN_IMAGE`, the provenance record of `z_indices`, and the exact
accepted-version set.

**Conformance plan §4, row "Volume"**, replaced by: "A `volume` request is `A_VOLUME_NOT_SUPPORTED`
unless the consumer declares `volume_support`; a `plane` request without `z_indices` covering a
position with more than one Z plane is `A_VOLUME_NOT_SUPPORTED` with or without it; a `plane` request
with `z_indices` selects exactly those Z of every `t` and records them, and an index an image lacks is
`A_Z_INDEX_NOT_IN_IMAGE`; with the capability, a one-slice volume selects exactly what the plane
request selects (`v01`); a volume is selected as every Z of one `t`. Each consumer's declared
capabilities are tested; P59-P70 (ADR 0010)."

## Rejected alternatives

- **A Z field in `morphobricks.toml`** (a unit key such as `volume = true`, or `z` per unit): a second
  statement of a fact the image already gives, which could disagree with it and would need its own
  contradiction refusal; it breaks §1 and §4.7's rule that the file holds no axes; and it would make the
  amendment a new field (readers pinned earlier would refuse it). Z is recorded where axes are.
- **Keeping gate 1 and adding an opt-out** (`allow_z` for 3-D tools): two ways to describe one
  experiment, and the description step would still decide something the hand-off decides (VZ1).
- **Per-plane histograms for volumes in the first step:** the owner chose "disabled" (VZ2); a per-plane
  result would be passed off as the volume's.
- **Serving a volume as planes implicitly** (today's `plane_selections`, one selection per `(t, z)`;
  MorphoFeature's `run_config._planes`), a default slice, or a projection chosen for the consumer:
  refused by VZ3 and VZ11. *History:* the owner's decision of 23 November 2026 (#438 comment 3) also
  rejected any per-plane opt-in; the owner's decision of 26 November 2026 (VZ11) reverses that for an
  **explicit, recorded** request of Z indices ([decision history](#decision-history)).
- **Always refusing a plane request on a volume** (the first draft's rule (b), with or without
  `volume_support`): superseded by VZ11.
- **Refusing a mixed description in preprocessing,** in a run or inside one unit: the owner chose a
  warning (VZ4, VZ8).
- **A volume-only Z code** (`R_VOLUME_Z_UNCALIBRATED`, then `W_VOLUME_Z_UNCALIBRATED`, VZ17):
  replaced by the one code `W_AXIS_UNCALIBRATED` with its axis (VZ18).
- **Refusing a volume with no Z step** (the first draft's `R_VOLUME_Z_UNCALIBRATED` refusal at run
  publication, from VZ5), or requiring X and Y in a length unit for volumes: replaced by VZ12 and VZ9
  (recorded as unknown with a code; the consumer that needs it refuses).
- **Refusing volume masks in the first step:** the owner accepted them (VZ10).
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
| P59 | `v01` with ZYX TIFF stacks (Z = 5), Z step in the header (µm) | Described, tagged and published without projection; run manifest: every image `z_count = 5`, `t_count = 1`, `spatial_unit = "volume"`, `plane_statistics = "not_computed: volume"`, `calibration` with Z source `header`; histogram and QC tables have no row for them; `RunInputs.fovs()` gives `z_count = 5` from the manifest; the notebook names "not computed: volume" at the Run step |
| P60 | As P59, (a) no Z step anywhere; (b) Z stated as `pixels`; (c) Z stated in `calibration.csv` (µm); (d) header Z step in an unsupported unit; (e) no X/Y size anywhere, Z in the header | `describe` and the run succeed in every case (VZ12, VZ9). (a), (d): z `source = "unknown"`, `size` and `unit` `null`, `reason = "W_AXIS_UNCALIBRATED"`; (b): z `source = "pixels"`, same reason; (a), (b), (d) also list `W_AXIS_UNCALIBRATED` (`axis = "z"`) once in the run's checks and report with every volume and the fix; (c) z source `stated`, reason `null`; (e) x and y `unknown` with `W_AXIS_UNCALIBRATED`, exactly as for a plane image (a plane-image run without X/Y sizes records the same). A step is never copied from X, Y or another image, and never written as 0 or 1 |
| P61 | `v01` with `CTRL` volumes (Z = 5) and `DrugA` planes; and a variant with both kinds in one imaging unit, one biological repeat and one condition | Published; `W_MIXED_PLANES_AND_VOLUMES` recorded in the run's checks and report with both lists and counts, and, in the variant, the unit, repeat and condition that hold both; no `R_UNIT_NOT_HOMOGENEOUS` for Z extent (VZ8); plane images have histograms and QC, volumes none |
| P62 | Resolver on P59's run: (a) `plane` request without `z_indices`, without `volume_support`; (b) the same with it; (c) `volume` without it; (d) `volume` with it; (e) `plane` with `z_indices = (0, 2)`, without `volume_support`; (f) `plane` with `z_indices = (5,)`; (g) `volume` with `z_indices`, and `z_indices = ()` or `(2, 0)` | (a) and (b) `A_VOLUME_NOT_SUPPORTED` per position, no selection; (c) `A_VOLUME_NOT_SUPPORTED` (rule a); (d) one selection per `t` with every Z; (e) one selection per position with `(0, 0)` and `(0, 2)` only, provenance `z_indices = [0, 2]`; (f) `A_Z_INDEX_NOT_IN_IMAGE` per position naming `z_count = 5`, no selection; (g) `ValueError` (malformed), nothing read |
| P63 | Resolver on P61's run: `volume` with `volume_support`; `plane` without `z_indices`; `plane` with `z_indices = (0,)`; `plane` with `z_indices = (3,)` | `volume`: volumes as every Z, plane images as one-slice volumes (AR3); `plane` without `z_indices`: refused for every volume position, listed by path, no selection; `(0,)`: every image's Z 0, recorded; `(3,)`: `A_Z_INDEX_NOT_IN_IMAGE` for every plane image, listed by path, no selection (never served for the volumes only) |
| P64 | `RunInputs` on P61's run: histograms, normalization fit and QC of every image | Plane images: their results; each volume: `VOLUME_STATISTICS_NOT_COMPUTED` naming it; never empty, zero or per-slice values; a pooled fit names the volumes left out |
| P65 | `v08` on P59's stacks: (a) `Nuclei` masks with Z = 5; (b) 2-D masks; (c) `TumorRegion` as objects with `binary_mask_policy`, as a `volume` request and as a `plane` request with `z_indices = (1,)`; (d) two FOVs whose `Nuclei` masks both hold value 7 | (a) accepted (VZ10), paired by recorded identity, `instances` values read per FOV, mask and time point over the volume; (b) refused by the mask check (Z differs); (c) `A_VOLUME_NOT_SUPPORTED` in both forms (BM5, F09 unchanged); (d) two objects, never joined by the value |
| P66 | Projection on P59's stacks | Still offered, with no default method, beside *Keep the 3-D stacks*; the copy and its conversion record version 4 as today; the projected run is all planes |
| P67 | A T-only time-lapse (T = 10, no Z) and a one-slice Z (Z = 1) | Unchanged from today: plane images, histograms and QC per plane, no Z calibration required |
| P68 | Versions | A run manifest of the previous version is refused by `RunInputs` with the fix; a manifest without `calibration`, or with a calibration entry missing a key or holding an unknown one, is refused; a consumer pinned to the previous resolver version refuses the new one before any read; a run folder whose histogram table has a row for a volume (or none for a plane image) is refused |
| P69 | A chosen consumer (ADR 0009) on P59's and P61's runs: `volume_support = "none"`; `"planes"` and `"volumes"` with `mixed_volume_support = false` | `none`: refused early, at axis confirmation and at `describe --consumer` (ADR 0009 P45); `planes`/`volumes` on P61: `mixed_volumes` (P46); on P59 both pass, and the hand-off routes as ADR 0009 P71. Never first at the hand-off. With *No consumer check* the consumer's own guard refuses at the hand-off |
| P70 | A test consumer with `requires_calibration = ["z"]` (ADR 0009 O10), on P60 (a) and (c); then (a) with *No consumer check* | (a) refused early, at axis confirmation, at `describe --consumer` and at the run's re-check, as `R_CONSUMER_DIMENSIONS_NOT_ALLOWED` kind `calibration`, naming the consumer and every volume with its z source; nothing published. (c) passes. With *No consumer check*: published with `W_AXIS_UNCALIBRATED`; the consumer's own guard refuses at the hand-off before any computation (ADR 0009 P72) |

MorphoFeature's own rows (P-2: every Z > 1 image and every mixed run refused on every route) are
ADR 0009's P49.

## Prerequisites and order

Unchanged by the decisions of 26 November 2026, restated with what each now carries:

- **P-1: this amendment of experiment-v1's 2-D scope** (§1, §4.5, §4.7, §7, §8 above). It is
  ADR 0009's P-1 and is offered for acceptance only after ADR 0009 is accepted (VZ6).
- **P-2: MorphoFeature's Z and mixed runtime guard** (ADR 0009 P-2). MorphoFeature refuses, on every
  route, every run with a `Z` > 1 image and every run mixing plane images and volumes, before any
  provider runs (VZ8: "MorphoFeature still refuses mixed plane/volume runs for now"). VZ11 does not
  relax it (VZ15): MorphoFeature's manifest keeps `volume_support = "none"`; it may later serve
  volumes through explicit `z_indices` (`"planes"`) only by its own reviewed change.
- **Preprocessing #438: the Z gate moves to the `RunInputs` hand-off.** The description-step
  refusal (`z_stack_not_supported`) is lifted only after P-1 is accepted and P-2 is implemented. The
  hand-off then is the one hard gate (VZ1): `RunInputs` reads `z_count`, `t_count`, `spatial_unit`,
  `calibration` and `plane_statistics` from the new run-manifest version, and the resolver's next
  contract version applies rule (b), `z_indices` and `A_Z_INDEX_NOT_IN_IMAGE`. #438's first step
  lands with all of them, never with the description gate lifted and the hand-off unchanged (today's
  `plane_selections` would serve a volume as planes, and `_fov` would read `z_count = 1`).

## Consequences

- **Users** can describe, tag, calibrate and publish Z-stacks without projecting them; a missing Z
  (or X, Y) step no longer stops `describe` or the run: it is shown at the Axes step and recorded as
  unknown with its code, and can be stated later (VZ9, VZ12). A run or unit that mixes volumes and
  planes is warned about and recorded, not refused (VZ8).
- **Consumers** must read a volume's calibration from the record and refuse an unknown step they
  need themselves; nothing fills it in for them. A consumer that wants single planes of a volume
  names the Z indices in its request, and its outputs carry them (VZ11). A consumer that sends a
  `plane` request without `z_indices` on a volume is refused instead of silently receiving every
  slice, which changes today's behaviour of `plane_selections`.
- **MorphoFeature** keeps refusing every volume and every mixed run (P-2); nothing in this ADR makes
  it 3-D.
- **Early failure** for consumer mismatches comes from ADR 0009's consumer manifest when a consumer
  is picked, including an "explicit planes only" consumer (`volume_support = "planes"`) and a
  declared calibration need (`requires_calibration`); with *No consumer check* only the consumer's own
  guard refuses, at the hand-off.
- **Versions:** a new run-manifest version, a new resolver-contract version and a new resolver code;
  no `morphobricks.toml` version change and no histogram-table version change. Every run folder made
  before is refused by the new reader and must be re-run (AR10).
- **Volume masks** (VZ10) are in scope from the first Z release, so the mask identity rules (pairing
  by recorded identity, objects by FOV, mask, time point and value) must be implemented for 3-D masks
  in the same release; 2-D masks on volumes and BM5 conversions stay refused.

## Modelling choices for the owner's review

None of these is an owner decision; each may be amended. Choices 3, 4, 5, 7 and 8 of the first draft
are now owner decisions (VZ12, VZ9, VZ10, VZ8, VZ11) and are kept here, marked, for traceability.

1. **No Z field in `morphobricks.toml`** (volume-ness from the confirmed roles, recorded in the run
   manifest). *Alternative:* a per-unit declaration `volume = true` checked against the images (a new
   field and a new contradiction code; see [rejected alternatives](#rejected-alternatives)).
2. **Amendment of v1, not `schema_version = 2`.** *Alternative:* a new schema version, so that a file
   itself says it may describe volumes; it would change no byte of the file except the version and
   force every reader to accept two versions or refuse every existing file (AR10).
3. *Resolved by VZ12:* an unknown Z step blocks neither `describe` nor the run; it is recorded with
   `W_AXIS_UNCALIBRATED` (VZ18; first revision: `R_VOLUME_Z_UNCALIBRATED`). (First draft: a refusal at run publication.)
4. *Resolved by VZ9:* X and Y of a volume follow the plane rule. (First draft alternative: require
   all three axes in a length unit.)
5. *Resolved by VZ10:* volume masks accepted, read over the whole volume, with the 2-D identity
   checks.
6. **One field `plane_statistics` per image covering histograms, normalization and QC together**, value
   `"not_computed: volume"`; a pooled fit names the volumes it left out. *Alternatives:* one status per
   product (more fields, the same information while all three are disabled together); a run-level
   list of volumes instead of a per-image field.
7. *Resolved by VZ8:* a mix inside one unit is warned and recorded, never refused.
8. *Resolved by VZ11, encoded as:* an explicit request field `z_indices` (one tuple for the whole
   request, strictly increasing), served only with `planes = "plane"`, needing no `volume_support`,
   with a new code `A_Z_INDEX_NOT_IN_IMAGE` for an index an image lacks. *Alternatives of the
   encoding:* indices per FOV (a request would have to name every FOV); require `volume_support` for
   an explicit plane request (narrower than "if the consumer asks, they can have it"); serve only the
   positions that have the index (a silent subset, rejected).
9. **RGB volumes are allowed** and need `rgb_support` and, in the consumer manifest,
   `volume_support` `"planes"` or `"volumes"` (at the resolver, a whole-volume request needs
   `Capabilities.volume_support = true`; an explicit plane request of an RGB volume `rgb_support`
   only). *Alternative:* refuse RGB volumes in the
   first step.
10. **Names:** `W_AXIS_UNCALIBRATED` with `axis` `x`, `y`, `z` (the owner's example, VZ18; it is
    written for `pixels` as well as `unknown`, since neither gives a length, and the `source` says
    which; *alternative:* only for `unknown`, leaving a deliberate `pixels` statement without a
    code),
    `W_MIXED_PLANES_AND_VOLUMES` (a preprocessing warning code in §8, which lists no warning in its
    `R_*` table today), `VOLUME_STATISTICS_NOT_COMPUTED` (a RunInputs code, not an experiment-v1 or
    resolver code), `A_Z_INDEX_NOT_IN_IMAGE` (a resolver-contract code), the request field
    `z_indices`, the manifest fields `z_count`, `t_count`, `spatial_unit`, `calibration`,
    `plane_statistics`. *Alternatives:* a lower-case preprocessing issue code for the warning
    (`mixed_planes_and_volumes`), or the RunInputs refusal as a resolver-contract code.
11. **Z extent and calibration are not compared between images** (different extents and steps are
    allowed and recorded; today's `different_plane_counts` and `different_pixel_sizes` stay warnings).
    *Alternative:* refuse a run whose volumes differ in Z step.

## Decision history

- **23 November 2026** (#438 comments 2-5): describe volumes, gate at the hand-off (VZ1); statistics
  disabled for volumes (VZ2); a Z run only to volume-capable bricks, **no per-plane opt-in, and
  MorphoFeature's `run_config._planes` stops expanding Z** (VZ3); mixed runs warned in preprocessing,
  refused by MorphoFeature (VZ4).
- **24 November 2026**: order Stable 1, ADR 0009, this amendment, #438 (VZ6). Z calibration
  mandatory (VZ5) was taken from #438's "Tests" section. The first draft encoded VZ5 as a refusal at run publication and VZ3 as
  "a `plane` request on a volume is always refused", and left five questions open.
- **26 November 2026** (VZ8-VZ12): the five questions answered. **VZ11 reverses the 23 November
  decision against a per-plane opt-in**: a plane request on a volume is allowed when the consumer
  names the Z indices explicitly, and is recorded; what stays from VZ3 is that Z is never expanded
  into planes implicitly and never projected for the consumer. **VZ12 replaces VZ5**: an unknown Z
  step is recorded with `R_VOLUME_Z_UNCALIBRATED` and blocks neither `describe` nor the run; the
  consumer that needs it refuses. MorphoFeature's P-2 guard is unchanged.
- **26 November 2026, second round** (VZ13-VZ20): ADR 0009 amended on its own branch (O9: three
  `volume_support` values with CM5 routing; O10: `requires_calibration`, revising CM4); P-2 kept;
  BM5 kept for explicit planes; the Z code renamed to `W_VOLUME_Z_UNCALIBRATED` (VZ17) and then
  merged into one code for any axis, `W_AXIS_UNCALIBRATED` (VZ18); the four-level mixed warning
  and "an unknown step never blocks preprocessing" confirmed (VZ19, VZ20).

## Open questions for the owner

None. The five questions of the first draft were answered by VZ8-VZ12 and the eight questions of
the first revision by VZ13-VZ20 (26 November 2026). The one choice made in encoding them is VZ18's:
one code, `W_AXIS_UNCALIBRATED`, with no separate volume Z code (modelling choice 10 also lists
writing it for `pixels`).
