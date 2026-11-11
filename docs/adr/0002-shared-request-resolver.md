# ADR 0002: one shared request resolver in preprocessing, both routes kept

- **Status:** Accepted (owner, 10 November 2026: the architecture AR1-AR9 with its audit, the
  no-compatibility policy AR10 and the rulings AR11; the three questions of the first draft were
  answered the same day, [below](#owner-answers-10-november-2026)). Amended on 11 November 2026
  for parent-label masks (resolver contract version 2,
  [below](#resolver-contract-version-2-parent-label-masks-11-november-2026); ADR 0001 PL1).
  Specification only: it changes no fixture, golden or validator (`python -I tools/audit/refval.py fixtures .` unchanged).
  The first implementation is a **draft** pull request in morphobricks-preprocessing
  (`claude/resolve-request`, target v0.5.1), unmerged until after the v0.5.0 tag.
- **Tracking:** [roadmap §5 Stage 2 and §6](../roadmap.md);
  [conformance plan §4](../conformance-plan.md); [ADR 0001](0001-experiment-description-v1.md)
  (the description and its gates; this ADR changes no rule of it, and AR10 supersedes RC1's
  clause on undescribed runs, see Consequences);
  evidence: MorphoFeature `docs/restart/designs/architecture-evidence-2026-11-10.md` and
  `chatgpt-answers/batch37-answer-2026-11-09.md` on branch `claude/restart-doc` (not in this
  repository).
- **Why a second ADR file, not a section of ADR 0001.** Every decision so far is a section of
  ADR 0001 because every one of them rules on the experiment description v1 (its fields, its
  physical scenarios, the scope of its gates). This decision rules on something else: a
  **runtime contract between repositories** (who interprets a description for a run, who labels,
  who decides capability, how two routes are proven equal), with its own version number and
  conformance suite. It therefore gets its own file, numbered next, and ADR 0001 keeps a one-line
  pointer so its decision index stays complete. The decision tables keep ADR 0001's format
  (accepted decision, rejected alternative, Spec section, fixtures or scenarios).

## Context

Four entry points read a described experiment for a run today: MorphoFeature (the orchestrator),
the direct runners of MorphoRelate and fiberfeatures, and CellPatcher. Each would have to
implement the Stage 2 rules (channels by canonical ID per FOV, scope classification, the mask
representation against the request, RGB capability, the `A_*` refusals) on its own. The evidence
report of 9-10 November 2026 **measured** the alternatives (ChatGPT batch 37's options A-E):

- the only numerical cross-route discrepancy found is a **policy** difference: a disconnected
  0/1 mask gives 1 object through the fiberfeatures and MorphoRelate direct runs and 2 objects
  through MorphoFeature with the same provider (MorphoFeature #200);
- with instance masks the routes agree to the last digit on single planes and on a T=2
  time-lapse, but differ in **shape**: fiberfeatures direct gives 137 columns against the
  provider's 9, with statistics and Optuna; MorphoRelate direct gives a whole-FOV table and
  measures one time point per run; fiberfeatures direct picks CUDA automatically while the
  provider defaults to CPU;
- the direct Z-volume code of fiberfeatures is unreachable (preprocessing refuses Z-stacks), so
  both routes are 2-D today;
- making MorphoFeature a dependency of every brick (options B/C) costs 2.0 MB and no new
  third-party package, so bytes cannot decide; it costs a fourth git-URL pin per brick on the
  repository that is Stage 2's critical path, and removes the direct runners' outputs;
- a ~150-line `resolve_request` sketch in preprocessing handled `v08` and `v13` with no brick,
  CellPatcher or provider import;
- fiberfeatures' default scoring unit (`sample_id` = file stem) merges technical repeats that
  share a stem and scores N = 3 per condition from one biological repeat (fiberfeatures #195).

A provisional decision of 9 November 2026 ("one adapter via MorphoFeature") was withdrawn after
an adversarial self-audit; the owner decided on 10 November 2026 as recorded below.

## Decisions (owner, 10 November 2026; all accepted)

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| AR1 | **One resolver.** `RunInputs.resolve_request(...)` in morphobricks-preprocessing is the only interpreter of an experiment description for a run, on every route. It resolves channels by canonical ID **per FOV**, classifies scope availability and coverage (full / partial / unavailable per biological repeat), checks the declared image type against the consumer's RGB capability and the declared mask representation against the requested use, and returns an **immutable per-FOV selection plus refusals and provenance**. It imports no brick, CellPatcher or provider module, runs no kernel, reads no pixel, writes nothing and never guesses | (A) one adapter per consumer (four copies of the rules, no cross-route guarantee); (B/C) one adapter inside MorphoFeature with every brick depending on it (a fourth pin per brick on the critical path, the direct runners' extra outputs lost, a release cycle between the provider API and the bricks' `[run]` pins); (D) a new shared run library (one more package and release cycle, a three-way pin lockstep) | roadmap §6, S2.0-S2.3; conformance §4 | `v01`, `v08`, `v09`, `v13`, `v28` through `RunInputs` (conformance §4 "Resolver") |
| AR2 | **Both routes kept.** Direct runs (`fiberfeatures`, `morphorelate run`, CellPatcher) **and** the MorphoFeature route stay. No brick depends on MorphoFeature. MorphoFeature orchestrates multi-brick runs, shared fits, caching, exports and keeps the provider capability checks | Retiring the direct runners (removes 128 fiberfeatures columns, its statistics and Optuna layer and notebooks, MorphoRelate's whole-FOV table and project workflow); thin direct wrappers around MorphoFeature (same loss, plus the pin coupling) | roadmap §6 | conformance §4 "Cross-route" |
| AR3 | **3-D stays open, enabled later.** A selection is **one plane or one Z-volume**. A consumer capability flag `volume_support` **refuses** a volume request by default (`A_VOLUME_NOT_SUPPORTED`, a resolver-contract code). 3-D is for the fiberfeatures direct route only and is enabled later under its own ADR; nothing enables it now. MorphoFeature stays 2-D. A one-slice volume reads exactly what the plane selection reads | A plane-only selection type (would need a breaking change of the resolver contract for 3-D); enabling volumes now (preprocessing refuses Z-stacks, `z_stack_not_supported`; whether the fiberfeatures direct route uses fitted normalization is unknown) | roadmap §9; conformance §4 "Volume" | a plane and a volume request on `v01` (refused by default; accepted with the flag and equal to the plane selection) |
| AR4 | **Mandatory cross-route conformance** for every brick with two routes (fiberfeatures, MorphoRelate), on the **shared 2-D capabilities**. The comparison is defined exactly in conformance §4 ("Cross-route"): the same object set, FOV, plane and time point; the shared columns, values, units, missingness and refusals identical; an explicit list of direct-only capabilities that the test does **not** compare (fiberfeatures: the 137-column table against the provider's 9, its statistics and Optuna; MorphoRelate: the whole-FOV table, and its direct run measuring one time point per run). The **device** is explicit and recorded on both routes; the test fixes the device or states a tolerance | A "same outputs" claim without a definition (direct and provider shapes differ, so it is false as stated); comparing only numbers (misses the refusals and the missingness) | conformance §4 "Cross-route" | the 0/1 two-blob mask, an instance mask with labels 1 and 7, a T=2 time-lapse (the evidence report's fixtures, to be checked into each brick) |
| AR5 | **One mask rule.** A `binary` mask used as an object set is refused (`A_MASK_NOT_INSTANCES`) unless the request records the explicit P27 `binary_mask_policy` (ADR 0001 AQ9, experiment-v1 §4.5c). The resolver **returns the policy decision** (it cannot import CellPatcher, which depends on preprocessing) and **each route applies it with CellPatcher's labeller**, the one shared labeller: two call sites (MorphoFeature; the direct runners), each with a test, and the cross-route conformance test proves equal objects. MorphoFeature's automatic #180 relabelling is removed (AR10, AR11). Fixes MorphoFeature #200 | Preprocessing's mask step labelling once on disk (a larger change to the mask step, and a labelled copy of every mask); each route keeping its own labeller (the 1-vs-2-objects discrepancy stays) | conformance §4 "Mask rule"; experiment-v1 §4.5c unchanged | `v08` (P27 a/b/c) through the resolver, plus the two-blob 0/1 mask on both routes |
| AR6 | **One statistics rule.** Inferential outputs name the **biological unit** (the canonical repeat, `repeat_group`); FOV-level and position-level scores are labelled **exploratory**. Fixes fiberfeatures #195: its default scoring unit changes (with a release note; the Optuna results of existing studies change) | Keeping `sample_id` (position stem) as the default unit (merges technical repeats that share a stem, scores N = FOVs); relying on MorphoFeature's route to avoid the statistics (the direct route keeps them) | conformance §4 "Statistics rule"; roadmap §6 | the two-wells-of-one-repeat fixture of the evidence report (§3.5) |
| AR7 | **Ownership split.** The resolver **classifies** (what exists: present / absent per image, full / partial / unavailable per repeat). MorphoFeature **decides** provider capability (`rgb_support`, devices, the provider API) and **records** the scope and the device in the run manifest. The bricks own their kernels and their direct-run tables | The resolver deciding capability (it would import provider manifests); MorphoFeature re-classifying scope (a second copy of the rules) | roadmap §6 | conformance §4 "Resolver", "Scope record" |
| AR8 | **Versioned resolver contract.** The resolver has a small contract with a **version number** (`RESOLVER_VERSION`, 1 at first) and its own conformance suite driven by the Spec fixtures through `RunInputs`. Preprocessing **v0.5.1** = `Fov.image_type`, the partial-mask test helper, the lab-tool links input (`--lab-links` JSON, as decided) and the resolver, plus the AR10 removals (the first change of v0.5.1), **only** | Shipping the resolver in v0.5.0 (the release candidate is under review; preprocessing is the release bottleneck); an unversioned method (a consumer could not state which rules it was tested against) | conformance §4 "Resolver" | the resolver suite (`test_spec_resolve_request.py` in preprocessing) |
| AR9 | **Explicit device, recorded.** The user, or the notebook's default, chooses `cpu` or `cuda`; `cuda` without a GPU is **refused**, never switched silently; the device is recorded in the provenance on both routes (the resolver carries it in the request it records; the consumer refuses). fiberfeatures replaces its automatic CUDA selection in an early PR | An implicit device per route (fiberfeatures direct auto-selects CUDA, the provider defaults to CPU: no conformance test can cover a GPU machine, and "no implicit CPU/GPU fallback" is a MorphoFeature rule) | conformance §4 "Device" | the cross-route test fixes the device, or states a tolerance for a CPU-vs-GPU comparison |
| AR10 | **No backward compatibility before the first pipeline release: obsolete compatibility code is removed wherever that simplifies, and old versions are refused, not converted** (owner policy, 10 November 2026, broadened the same day: nobody uses the current code and the first pipeline is still being built, so go clean). The first concrete item: a published experiment description (`morphobricks.toml`) is **required** for every run, on every route. **Dropped, closed list of the concrete items:** (1) undescribed runs; (2) the legacy `experiment_design.csv` route as an input to grouping (the derived CSV stays an output, written by preprocessing); (3) IDs derived from folder or file names (`position_id` excepted: it stays the image file stem, AR11 (2)); (4) MorphoFeature's BY_NAME grouping and its interim 0/1 mask labelling (#180); (5) CellPatcher's empty-ID path for undescribed runs (D47 stays only as the `instances` rule: an `instances` mask holding 0 and 1 is one object); (6) the v0.4.0 parity framing: the legacy-parity gate rows and the tests that only compare with v0.4.0 (parity tests that check science stay as science goldens, AR11 (8)); (7) version migrations: an old version is refused, never converted; (8) MorphoFeature's `WAVE_1` strict expected-failure markers; (9) *(amendment of 10 November 2026, owner decision)* the one-way migration of a legacy `experiment_design.csv` found in an output folder into a draft description (experiment-v1 §7; it supersedes ADR 0001 AQ12 and FR2): a description is made only from discovery and the user's answers, and the derived `experiment_design.csv` stays an output that nothing reads back. **General rule beyond the list:** before the first pipeline release there is no backward compatibility: any code kept only for compatibility (old manifest/draft/histogram version readers and migrations, deprecated aliases or parameters, shims, fallback readers, legacy notebook paths, old CLI flags) is removed wherever that simplifies the code. Each removal is its own reviewed PR that keeps the science tests (one obsolete-code sweep PR per repository after the v0.5.0 tag, driven by an inventory; what a sweep removes is decided from its inventory, not by this ADR). **Unchanged:** no guessing, no silent fallback, explicit refusals. **Every consumer refuses a run without a published description** (`A_DESCRIPTION_REQUIRED`, a resolver-contract code like `A_VOLUME_NOT_SUPPORTED`, confirmed by the owner in AR11), naming the fix: run the notebook or `describe`. **Timing:** the removal starts right **after** the owner tags preprocessing v0.5.0, as the first change of v0.5.1 together with the resolver; v0.5.0 ships as reviewed | Keeping the undescribed path or other compatibility code beside the resolver (two interpretations of a run, a parity burden on code nobody uses); converting old versions (a migration guesses what the old data meant) | roadmap §5 Stage 2, Gate G2, §6; conformance §4 | none removed: no fixture exists only for an undescribed run (`v13`, `v33`, `v34` are described); for (9) no fixture or golden is removed (`v13` and its golden test the derived output) and P30 is amended to the derived output only |
| AR11 | **Owner rulings of 10 November 2026 on the AR10 removal (normative, closed list).** (1) **`A_DESCRIPTION_REQUIRED` is the confirmed code** for a run without a published description: a resolver-contract code defined by this ADR (like `A_VOLUME_NOT_SUPPORTED`), not an experiment-v1 §8 code. (2) **`position_id` stays the image file stem**; no Spec change (the FOV key of experiment-v1 §3.4 already combines it with the condition, biological-repeat and technical-repeat labels). (3) **CellPatcher and MorphoFeature read `repeat_group` from the published description through the resolver**, not from the derived `experiment_design.csv`; the derived CSV stays an output only and neither of them reads it back (AR10 (2)). (4) **MorphoFeature's automatic 0/1 connected-component labelling is removed** (not switched off). Only the explicit P27 `binary_mask_policy` labels a `binary` mask, applied by the one shared labeller (AR5; MorphoFeature #200). (5) **Provider API v2 is removed.** MorphoFeature supports provider API v3 only and the providers' `patches`, `calibration` and `context` arguments are required. (6) **The old `repeat` column alias is removed everywhere**, MorphoCoverage included (in its own reviewed PR). (7) **After the preprocessing clean-up (PP-C), preprocessing reads only the current run-manifest version**; an older one is refused. (8) **Parity tests are kept as science goldens without the version framing**; tests of only an old version or of a removed feature are deleted. **Not in this list:** the owner's other answers of the same day rule on single repositories' sweeps (for example `.template_sync`, CellPatcher's config version, MorphoRelate's D83 guard, normalization's old-version messages); they are not Spec rules and this ADR does not record them | Leaving the code name open (a consumer could not test for it); a position identified by its stem alone (merges technical repeats that share a stem, fiberfeatures #195); consumers reading the derived CSV back (a second source of `repeat_group` beside the description); keeping the 0/1 labelling "off" (code and tests nobody can use, a second labeller); keeping provider API v2 or the `repeat` alias beside the current form (two shapes to test, no current caller); readers of older manifest versions (a migration guesses what the old data meant); keeping the v0.4.0 framing on parity tests, or deleting their science checks with it | roadmap §5 Stage 2, S2.1, §6; conformance §4 "Description required", "Mask rule"; experiment-v1 unchanged | none new: the rulings are tested by the consumers' own suites (a run without `morphobricks.toml`; no provider API v2 path; no `repeat` alias; an older manifest refused); `v08` and the two-blob mask cover (4) |

### The resolver contract, version 1 (normative for the consumers)

Inputs (a `Request`): canonical channel IDs; masks by **mask ID** with a role (`objects` or
`region`) and, for a `binary` mask used as objects, the explicit `binary_mask_policy`
(`connected_components`); the planes (`plane` or `volume`); the consumer's `Capabilities`
(`rgb_support`, `volume_support`; both false by default); the explicit `device` (`cpu` or
`cuda`).

Output (a `ResolvedRequest`, immutable and picklable):

- one `FovSelection` per position when nothing refuses: the unchanged FOV key; `repeat_group`,
  `condition_id`, `technical_repeat_id`; the unit's declared `image_type`; the C index of
  **every requested channel in that image**; each mask as the consumer reads it (`mask_id`,
  `source_type`, `representation`, `role`, `check_status`, `conversion` = the recorded policy or
  none); the planes to read (one `(t, z)` per plane selection, or every Z of one `t` for a
  volume);
- the refusals, **all** that apply, each with its code, subject, message and files:
  `A_SCOPE_INCOMPLETE` ("present in k of n acquisitions", k may be 0, one rule for channels and
  masks; an undeclared mask ID is 0 of n), `A_MASK_UNCHECKED` ("k of n files"),
  `A_MASK_NOT_INSTANCES`, `A_RGB_NOT_SUPPORTED`, `A_VOLUME_NOT_SUPPORTED`; a run without a
  published description has no selection at all and one refusal, `A_DESCRIPTION_REQUIRED`;
- a refused request has **no selections**: no subset is taken for the user (experiment-v1 §8);
- the coverage of every biological repeat per channel and mask (full / partial / unavailable),
  given whether or not the request is refused, for the orchestrator's scope record;
- the provenance: the resolver version, the description's SHA-256 and section digests as the run
  manifest recorded them, and the request (its device included).

Rules: the resolver reads the run manifest, the published description (checked against the
run's SHA-256) and the mask step's status file only; it never reads a pixel, labels, converts,
chooses a device or imports a brick, CellPatcher or provider module (a test scans its modules).
A malformed request (an ID twice; an unknown role, policy, plane kind or device; a policy on a
mask that is not `binary` or in a `region` role) is a programming error (`ValueError`), not a
refusal. A run without a published description is refused by the resolver with `A_DESCRIPTION_REQUIRED`,
naming the fix (run the notebook or `describe`); there is no header-name path (AR10).

Codes: `A_VOLUME_NOT_SUPPORTED` and `A_DESCRIPTION_REQUIRED` are defined by this contract, not by
experiment-v1 §8, whose `A_*` list is unchanged (owner answer 1 below; AR11 (1)). Every other
code is ADR 0001's.

### Resolver contract version 2: parent-label masks (11 November 2026)

ADR 0001 PL1 (owner decisions of 11 November 2026) adds `parent_labels` to the description's
`representation` (experiment-v1 §4.5b). The contract gains one input and one output value, so it
is version 2 (`RESOLVER_VERSION = 2`, AR8); everything else above stands, and no code is added.

- **Input.** `Capabilities` gains `parent_labels_support` (false by default), beside
  `rgb_support` and `volume_support`. MorphoFeature reads it from a provider manifest's
  `parent_labels_support` key; a direct runner passes its own declaration (AR7).
- **Region.** A `parent_labels` mask in the role `region` is selected with
  `representation = "parent_labels"` and `conversion` none when the consumer declares
  `parent_labels_support`, and with `conversion = "parent_labels_as_area"` when it does not: that
  consumer reads every non-zero pixel as inside and 0 as outside, records the marker in its run
  provenance or output and shows it to the user. The resolver never splits or relabels the mask
  and reads no pixel of it.
- **Objects.** In the role `objects` it is `A_MASK_NOT_INSTANCES`, with or without the
  capability. A `binary_mask_policy` on it is a malformed request (`ValueError`), as for any mask
  that is not `binary`.

### Consequences

- The roadmap's ownership matrix (§6) and S2.1-S2.3 are amended: every consumer **consumes the
  resolver** instead of interpreting the description; a new S2.0 names the resolver itself. The
  conformance plan's Stage 2 obligations gain the resolver suite, the cross-route comparison, the
  mask rule, the statistics rule, `volume_support` and the explicit device.
- `rgb_support` (ADR 0001 RC1) is unchanged: the resolver takes the capability as a boolean from
  the consumer; MorphoFeature reads provider manifests, the direct runners read their own.
- The FOV key keeps the source labels everywhere (experiment-v1 §3.4): the selection adds the
  canonical IDs beside it and never replaces them.
- AR10 supersedes owner answer 5 of 8 November 2026: MorphoFeature's #180 relabelling of 0/1
  masks is **removed** (not only off) with the undescribed route, and CellPatcher's empty-ID path
  for undescribed runs is removed; no run is undescribed. Version migrations are not provided, nor is the migration of a legacy
  `experiment_design.csv` (AR10 (9)).
- AR10 supersedes the clause of ADR 0001 RC1 that undescribed RGB runs "keep working as today,
  with a warning" (repeated as brick behaviour in experiment-v1 §4.4b, whose text was amended on
  10 November 2026 to match): no run is undescribed, and a run without a published description is refused with
  `A_DESCRIPTION_REQUIRED` before any capability is checked.
- AR11 records the owner rulings of 10 November 2026 that bind the consumers (the confirmed code
  name, `position_id` = the file stem, `repeat_group` from the description, the 0/1 labelling
  removed, provider API v3 only, no `repeat` alias, one manifest version in preprocessing, parity
  tests kept as science goldens). The sweeps' repository-level choices are not Spec rules.
- 3-D: "fiberfeatures direct only, under a future ADR" is recorded in roadmap §9. No 3-D field,
  code or fixture is added now.

### Owner answers (10 November 2026)

The first draft asked three questions; the owner answered them as follows.

1. **Where `A_VOLUME_NOT_SUPPORTED` lives:** in the resolver contract only (this ADR), not in
   experiment-v1 §8; a capability nothing declares needs no Spec text change.
2. **Mask role names:** `objects` and `region`. MorphoRelate's `nucleus` / `cell` / `region`
   analysis roles stay brick-level, mapped onto them, so the resolver never learns a brick's
   vocabulary.
3. **The device in the request:** `device` stays in the resolver's request so the provenance
   record has one shape on both routes; the resolver checks only the spelling (`cpu`, `cuda`) and
   the consumer refuses `cuda` without a GPU.
