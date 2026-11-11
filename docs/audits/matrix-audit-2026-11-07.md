# Executable matrix audit: experiment description v1 across every brick

- **Date:** 7 November 2026 (owner request of 6 November 2026). **Refs:** issue #1.
- **Spec audited:** `docs/experiment-v1.md`, `docs/adr/0001-experiment-description-v1.md`,
  `fixtures/`, `docs/conformance-plan.md`, `docs/audits/s01-consumer-audit-2026-11-06.md` at
  `claude/youthful-carson-klzm3w` = `8479864e3ad80ce6b3d6e30e2fa0355fdee9e44e`.
- **Scope:** executable and read-only for the bricks. No brick repository was changed; every brick
  ran from a fresh environment installed from Git at the tags below. Everything is reproducible
  with [`tools/audit/`](../../tools/audit/README.md) (audit tools only, not a runtime package).
  This is evidence for the Stage 1-3 plan, not a conformance claim for any brick.

## Summary

1. **79 cases** (64 one-factor-at-a-time cases over the four requested dimensions, 15 all-pairs
   cases over five interacting factors) ran through preprocessing (check, design, run, mask step),
   normalization (CellPatcher, by biological repeat), CellPatcher (grid, random, whole_fov, cell),
   MorphoFeature with MorphoObjects, MorphoRelate and fiberfeatures (MorphoEmbed planned only:
   weights absent) and MorphoCoverage (`condition_contrast` on MorphoFeature's export): **632
   cells: 345 MATCH, 49 MISMATCH-BRICK, 4 MISMATCH-SPEC, 1 BUG, 185 N/A (an earlier brick
   refused), 48 SKIP** (47 MorphoEmbed cells without weights, 1 harness artefact).
2. **The reference validator agrees with every fixture:** 36/36 valid (exact warnings), 130/130
   invalid (exact code set and phase), 12/12 transitions, round trip and digests
   (`tools/audit/refval.py`). Five fixtures were added for structures the catalogue lacked
   (`v35`, `v36`, `i128`-`i130`).
3. **Two silent, wrong-result paths exist today** and are the top blockers for adopting v1:
   (a) the confirmed repeat pairing never reaches MorphoCoverage, which pairs by folder label:
   the v03 pairing is lost ("Not compared") and the v30 pairing is silently replaced by a
   different one (F05, F07); (b) unnamed channels whose order differs between units are pooled
   by C index everywhere (preprocessing, normalization, CellPatcher, every provider): the column
   `DAPI__Cells__mean_intensity` of DrugA holds the Actin intensity, with no warning (C17, P02,
   P06). A third is known from S0.1 and now executed: a 0/1 integer mask is measured as one object
   per FOV by every brick (A08, P02).
4. **Everything that v1 refuses at file level is accepted today** (no reader exists): swapped
   pairing, references (cycle, self, display name), non-NFC folders, a mask declared binary that
   holds instances (F08, K06, K11, K12, F21, A13). These are Stage 1 by design.
5. **Preprocessing refuses what v1 accepts** in three places: confirmed header aliases and case
   variants (`channel_names_differ`, C12, C13), heterogeneous units (as the Stage 1-2 interim
   `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` requires, so MATCH until Stage 3), and it trims header
   names (C14). MorphoFeature uses header names as channel identities, so a canonical ID that
   differs from the header (`Tub` for header `t`) is refused (C15).
6. **What works as v1 wants:** folder labels stay in every FOV key (also `control`, `z`, `files`,
   `single`); discovery refuses `Single`, case collisions, `NA`, images beside folders and Z>1;
   CellPatcher's normalization pools by the confirmed repeat group, including v03 and v30
   pairings; partial masks are refused with a progress summary (A_SCOPE_INCOMPLETE in spirit);
   every NaN produced (16, MorphoRelate correlation) has an applicability row; MorphoCoverage
   treats technical repeats as the unit (pseudo-replication guard) and says "Not compared" for a
   condition and control without a shared repeat.
7. **Spec gaps (MISMATCH-SPEC):** a flat experiment has no condition folder, but `source_folder`
   is "the folder label read from disk" (F01); 4.6a gives no "propose another ID" rule for a
   biological-repeat folder named like a forbidden key (`z`, F16); v1 is silent on time-lapses,
   and MorphoFeature does not export several planes per FOV to MorphoCoverage (A03); grouped
   masks cannot be described and are undetectable once declared `instances` (A14; described since
   PL1, 11 November 2026). RGB
   "documented capabilities" (4.4b) have no machine-readable form, so no brick declares any.

## 1. Evidence base

| Repository | Ref | Full SHA | Where it differs from main for this audit |
|---|---|---|---|
| MorphoBricks-Spec | `claude/youthful-carson-klzm3w` | `8479864e3ad80ce6b3d6e30e2fa0355fdee9e44e` | base of this branch |
| morphobricks-preprocessing | `v0.4.0` | `bc7b872bd3ccb30dcd5de812e99a3485a3281825` | `main` `34cbf1c24fbd871ac2247e8cdff5518b43253c84`: mask fingerprint binding (#160, #165), reporting (#104, #105), I/O minors; no change to design, channel names, trimming or mask representation, so no case would differ |
| morphobricks-normalization | `v0.3.4` | `1c1c7b48a041e23bd390037bd6ab837e1e5f1c85` | `main` differs in numerical refusals only (S0.1) |
| CellPatcher | `v0.2.0` | `498825e977f1df5be623416bcacc7464990486e9` | `main` `031bba9`: 2-D-only follow-up (S0.1) |
| MorphoObjects | `v0.1.0` | `478c916ea601f150c062cc4326fe9413e9e5500f` | = `main` |
| MorphoEmbed | `v0.1.0` | `3c16bce2bb6b08f73e693dc23b15a2048bfa6649` | weights absent: requests planned with `morphofeature check` |
| MorphoRelate | `v0.1.1` | `160ad2314ed2f156666421add2d3ba269cf8abb7` | |
| fiberfeatures | `v0.2.1` | `8798b7585ec91f7c380f815de95bc34f82eb401a` | |
| MorphoFeature | `v0.1.0` | `182b3735d33eac7d40902f82d69885ef6fb3aae8` | `main` `60f4a92cb42716184b3ea7d0b804c873a8dd0852`: image fits use the run's design (#95), planning of conditional parameters; the export, channel catalogue and `scaling.py:212-221` refusal are unchanged, so F07/F08 behave the same |
| MorphoCoverage | `main` (no tag) | `64ff307d90fe5eb62a72630f35b85bd7fe6040a4` | |

Environment: Python 3.13.18, numpy 2.5.4, tifffile 2026.10.15, pandas 3.1.1, torch 2.15.0+cpu, one
`uv` environment with exactly the pins above (`uv pip freeze` shows each brick at the tag's full
SHA). Citations without a ref are at these SHAs; `@main` marks main.

## 2. Method

For every case `tools/audit/runner.py`:

1. **(a) Spec expectation.** `matrix.py` turns the case's dataset and the user's confirmed answers
   (pairing, condition and technical-repeat IDs, per-unit channel lists, header aliases, mask
   representation, references) into the v1 model, writes it with the canonical writer (9.1) to
   `tools/audit/results/cases/<case>.toml` and validates it with `refval.py` (`E_*`, `W_*`). The
   physical oracle adds the `R_*` codes that need images (4.3 header evidence,
   `R_UNIT_NOT_HOMOGENEOUS`, `R_MASK_CONTRADICTS_REPRESENTATION`, `R_FOLDER_NOT_NFC`; the Stage 1-2
   `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` separately) and the `A_*` codes of the standard request set
   (`A_MASK_NOT_INSTANCES`, `A_SCOPE_INCOMPLETE`, `A_RGB_NOT_SUPPORTED`; CellPatcher declares RGB
   support in its README, no other brick does). Discovery refusals the spec leaves to preprocessing
   ("refused at discovery as today", 4.6a) are expected as such.
2. **(b) Dataset.** 32x32 uint16 OME-TIFF (ImageJ TIFF when unnamed and uncalibrated, RGB TIFF for
   RGB), 1-6 FOVs per folder, a `Cells` mask folder. Each canonical channel has its own intensity
   inside objects (DAPI/DNA 1000, ACTIN 2000, PAX 3000, PHASE 4000), so a channel mix-up is visible
   in every measured mean.
3. **(c) Bricks, as a user runs them.** `morphobricks-preprocessing check` (with `--masks`), then
   `design --repeat-group C/R=G ... --control C ... --confirm-all` (the user's pairing and the
   conditions that are some condition's `reference`), `run --axes <check's suggestion>
   --image-type <declared>`, `masks`; CellPatcher `grid` (with `NormalizationConfig(scope=
   "biological_repeat")`), `random`, `whole_fov`, `cell`; one MorphoFeature run file per provider
   with the **v1 canonical channel IDs** (MorphoObjects `area` + `mean_intensity` per channel plus a
   CellPatcher grid patch set; MorphoRelate `mean_intensity` in the `cell` compartment;
   fiberfeatures `fa_mean`; MorphoEmbed `efficientnet_b0_ra_in1k`, `check` only). When MorphoFeature
   refuses the canonical IDs because of channel names, the run is repeated with the recorded header
   names to reach the next brick (reported as `_with_header_names`). MorphoCoverage:
   `load_coverage_inputs` → `attach_feature_tables` → `condition_contrast(feature="Cells__area",
   comparisons=<v1 references by condition ID>)`, plus the same as an `own_control` contrast table,
   and, where an ID differs from its folder, again by folder label.
4. **(d) Record** (`tools/audit/results/matrix-results-2026-11-07.json`): return codes, issue codes
   of `discovery_report.json`, the recorded labels and channel names, mask kinds, CellPatcher
   patch counts and normalization groups, MorphoFeature FOV statuses, objects per FOV, per-group
   channel means, NaN cells against applicability rows, coverage export, MorphoCoverage paired
   repeats, unit and refusals.
5. **(e) Compare.** `classify.py` gives every cell a verdict by fixed rules; each judgement
   beyond them is an `OVERRIDES` entry with its reason (all quoted in the cell notes below).

**Verdicts.** MATCH: the brick does what v1 (or, for heterogeneous layouts, its Stage 1-2 interim)
expects, refusals counting as MATCH when v1 also refuses, whatever the code. MISMATCH-BRICK: the
brick differs from v1, a Stage 1-3 item (including silent acceptance of what v1 refuses at
analysis). MISMATCH-SPEC: the spec is silent or wrong. BUG: wrong today regardless of v1. N/A: not
reached (an earlier brick refused). SKIP: not runnable here.

**Pruning rule.** The full product of the requested levels (about 20 folder × 17 channel ×
14 control × 15 axes/mask levels) is ~70,000 datasets. The audit keeps (1) **every level of every
dimension once (OFAT)**, varied from one base case (A02: CTRL/DrugA × rep1/rep2, CYX, two named
channels, instance masks, square calibration, DrugA → CTRL), giving each single-dimension
extreme; plus (2) a **greedy all-pairs covering array** (15 rows) over the five factors whose
interactions decide identity end to end, three levels each: pairing (same names, different names,
repeat missing), channel layout (homogeneous, swapped across conditions, technical repeats
different), control design (one, chain, none), masks (instances, binary, partial) and header
names (named, unnamed, alias). Every pair of levels of those factors occurs in at least one row.
Cases that differ from another only in the description (no dataset change: K11, K12, C12b) are
spec-only and share that case's brick runs, since no brick reads the description today.

### 2.1 Coverage of the requested matrix

| Requested | Cases |
|---|---|
| Single flat folder; one condition; several conditions; one biological repeat | F01; F02; F03, K03, K04; F04 |
| Several repeats paired with same names / different names / same label in two repeats / swapped labels | A02, F03; F05, P04-P06; F07; F08 |
| A repeat missing in one condition | F06, K08, P07-P09 |
| Technical repeats: none (`single`) / one / several same layout / several different layouts | A02; F09; F10; F11, P03, P06, P09, P14, P15 |
| Images beside sub-folders; 1 vs many images; empty folders | F12; F13, F14; F15 |
| Reserved/forbidden folder names (`control`, `z`, `files`); `single`/`Single`; case collision; `NA`; non-NFC | F16; F17, F18; F19; F20; F21 |
| Channels 1 / 2 / 3 / 4 | C01; A02; C03; C04 |
| Same count in another order across conditions / repeats / within one unit | C05, P12, P13 (named), C17, P02 (unnamed); C06; C07 |
| Extra channel in some images / in a whole unit; missing channel | C08; C09; C10 |
| Header names present / missing / alias / case / outer whitespace / reserved (`t`) / alias not confirmed | A02; C11, P02, P06, P07; C12, P03, P04, P08; C13; C14; C15; C12b |
| RGB | C16 |
| No control; one; several for different treatments; per-treatment matched; chain; cycle; self; display-name reference | K01; A02; K03; K04; K05, P10, P15; K06; K12; K11 |
| Several reagents per target; unpaired; control missing in a repeat; control only in some technical repeats; control in another channel layout | K07; K09; K08; K10; C05, C17 |
| MorphoCoverage contrasts: comparisons, `own_control` table, per-repeat rows, technical repeat as the unit | every case reaching MC (`unit` recorded); K04, K05 for chained own controls |
| YX; CYX; TCYX with Z=1; Z>1 | C01; A02; A03; A04 |
| Square; non-square; missing; partial calibration | A02; A05; A06; A07 |
| Masks instances / binary 0-1 / boolean / explicit conversion / missing / partial / shared / declared binary holding instances / grouped | A02; A08, P02, P04, P09; A09; A08b; A10; A11, P03, P05, P07; A12; A13; A14 |
| Every NaN explained | N01 (one-pixel object, object flat in one channel, MorphoRelate correlation) |

Not covered (stated, not guessed): `across_normalised` and `vs_master_raw` contrast rows and
declared FDR families (`Setup.experiment`); OME-Zarr inputs; reconciliation/transition runs of
preprocessing (the transition rules are covered by the fixtures, not by images); MorphoEmbed
inference (weights absent); notebooks.

## 3. Case × brick table

Columns: **PP** preprocessing (check, design, run, mask step); **NORM** CellPatcher's normalization
by biological repeat (the pooling the normalization brick computes); **CP** CellPatcher grid,
random, whole_fov and cell modes; **MO** MorphoObjects, **MR** MorphoRelate, **FF** fiberfeatures,
**ME** MorphoEmbed (each through MorphoFeature); **MC** MorphoCoverage on MorphoFeature's
export. M = MATCH, MB = MISMATCH-BRICK, MS = MISMATCH-SPEC, B = BUG, - = N/A, skip = SKIP.
"Spec v1 expects" is the final (Stage 3) outcome; "Stage 1-2" names the interim refusal.

| Case | What | Spec v1 expects | PP | NORM | CP | MO | MR | FF | ME | MC |
|---|---|---|---|---|---|---|---|---|---|---|
| A02 | base: CTRL/DrugA x rep1/rep2, CYX, 2 named channels, instance masks | accepted | M | M | M | M | M | M | skip | M |
| F01 | single flat folder (root is the leaf) | accepted | MS | M | M | M | M | M | skip | M |
| F02 | one condition, two repeats | accepted | M | M | M | M | M | M | skip | M |
| F03 | three conditions, same repeat names | accepted | M | M | M | M | M | M | skip | M |
| F04 | one biological repeat | accepted | M | M | M | M | M | M | skip | M |
| F05 | repeats paired with different folder names (v03) | accepted | M | M | M | M | M | M | skip | MB |
| F06 | a repeat missing in one condition | accepted; W_REPEAT_MISSING_CONDITIONS | M | M | M | M | M | M | skip | M |
| F07 | same source label in different repeats (v30) | accepted | M | M | M | M | M | M | MB | MB |
| F08 | swapped labels: rep1 paired with the other condition's rep2 | refused: E_REPEAT_ID_SHADOWS_SOURCE | MB | M | M | M | M | M | MB | MB |
| F09 | one technical-repeat folder | accepted | M | M | M | M | M | M | skip | M |
| F10 | several technical repeats, same layout | accepted | M | M | M | M | M | M | skip | M |
| F11 | several technical repeats, different layouts (named) | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | M | - | - | - | - | - | - | - |
| F12 | images beside sub-folders | refused: discovery:tiff_outside_leaf | M | - | - | - | - | - | - | - |
| F13 | one image per folder | accepted | M | M | M | M | M | M | skip | M |
| F14 | many images per folder (6) | accepted | M | M | M | M | M | M | skip | M |
| F15 | empty folders (an empty condition and an empty repeat) | accepted | M | M | M | M | M | M | skip | M |
| F16 | reserved/forbidden folder names: condition `control`, repeat `z`, technical repeat `files` | accepted | MS | M | M | M | M | M | skip | MB |
| F17 | lower-case `single` folder as the only repeat folder | accepted | M | M | M | M | M | M | skip | M |
| F18 | `Single` folder (other case) | refused: E_SINGLE_MISUSE | M | - | - | - | - | - | - | - |
| F19 | repeat folders differing only in case (rep1 / Rep1) | refused: E_ID_CASE_COLLISION | M | - | - | - | - | - | - | - |
| F20 | folder label `NA` | refused: E_ID_TEXT | M | - | - | - | - | - | - | - |
| F21 | non-NFC folder label (decomposed e-acute) | refused: E_ID_NOT_NFC | MB | M | M | M | M | M | skip | MB |
| C01 | one channel, YX | accepted | M | M | M | M | M | M | skip | M |
| C03 | three channels | accepted | M | M | M | M | M | M | skip | M |
| C04 | four channels | accepted | M | M | M | M | M | M | skip | M |
| C05 | same count, different order across conditions (named) | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | M | - | - | - | - | - | - | - |
| C06 | different order across repeats (named) | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | M | - | - | - | - | - | - | - |
| C07 | different order within one unit (named) | refused: R_UNIT_NOT_HOMOGENEOUS | M | - | - | - | - | - | - | - |
| C08 | an extra channel in some images of one unit | refused: R_UNIT_NOT_HOMOGENEOUS; W_UNUSED_CHANNEL; requests: A_SCOPE_INCOMPLETE | M | - | - | - | - | - | - | - |
| C09 | an extra channel in a whole technical repeat | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED); requests: A_SCOPE_INCOMPLETE | M | - | - | - | - | - | - | - |
| C10 | a missing channel in one condition | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED); requests: A_SCOPE_INCOMPLETE | M | - | - | - | - | - | - | - |
| C11 | header names missing (unnamed channels) | accepted | M | M | M | M | M | M | skip | M |
| C12 | header alias: DNA confirmed by DAPI and by Hoechst | accepted | MB | - | - | - | - | - | - | - |
| C12b | header alias not confirmed (Hoechst not in header_names) | refused: R_HEADER_CONTRADICTION | M | - | - | - | - | - | - | - |
| C13 | header names differing in case (DAPI / dapi) | accepted | MB | - | - | - | - | - | - | - |
| C14 | header name with outer whitespace ('DAPI ' / 'DAPI') | accepted | MB | M | M | M | M | M | skip | M |
| C15 | header name `t` (reserved as a channel ID; channel confirmed as `Tub`) | accepted | M | M | M | MB | MB | B | MB | - |
| C16 | RGB images | accepted; requests: A_RGB_NOT_SUPPORTED | M | M | M | MB | MB | MB | skip | M |
| C17 | unnamed channels, order swapped across conditions | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | MB | MB | MB | MB | MB | MB | skip | M |
| K01 | no control | accepted | M | M | M | M | M | M | skip | M |
| K03 | several controls for different treatments | accepted | M | M | M | M | M | M | skip | M |
| K04 | per-treatment matched controls (siNC per background) | accepted | M | M | M | M | M | M | skip | M |
| K05 | reference chain B -> A -> CTRL | accepted | M | M | M | M | M | M | skip | M |
| K06 | reference cycle A -> B -> A (refused) | refused: E_REFERENCE_CYCLE | MB | M | M | M | M | M | skip | M |
| K07 | several reagents per target (si1, si2 -> SRC) | accepted | M | M | M | M | M | M | skip | M |
| K08 | control missing in one repeat | accepted; W_REPEAT_MISSING_CONDITIONS | M | M | M | M | M | M | skip | M |
| K09 | control and condition share no repeat | accepted; W_REFERENCE_UNPAIRED, W_REPEAT_MISSING_CONDITIONS | M | M | M | M | M | M | skip | M |
| K10 | control present only in some technical repeats | accepted | M | M | M | M | M | M | skip | M |
| K11 | reference names a display name / self reference (spec only) | refused: E_REFERENCE_UNKNOWN | MB | M | M | M | M | M | skip | M |
| K12 | self reference (spec only) | refused: E_REFERENCE_SELF | MB | M | M | M | M | M | skip | M |
| A03 | TCYX with T=2, Z=1 (masks TYX) | accepted | M | M | M | M | M | M | skip | MS |
| A04 | Z>1 (ZCYX, Z=3) | refused: discovery:z_stack_not_supported | M | - | - | - | - | - | - | - |
| A05 | non-square pixels (0.5 x 0.25 um) | accepted | M | M | M | M | M | M | skip | M |
| A06 | missing calibration | accepted | M | M | M | M | M | skip | skip | M |
| A07 | calibration missing in some images | accepted | M | M | M | M | M | M | M | - |
| A08 | binary masks (0/1, two blobs), declared binary | accepted; requests: A_MASK_NOT_INSTANCES | M | M | MB | MB | MB | MB | skip | M |
| A08b | binary masks, CellPatcher binary_mask_policy=connected_components | accepted; requests: A_MASK_NOT_INSTANCES | M | M | M | M | M | M | skip | - |
| A09 | binary masks stored as booleans | accepted; requests: A_MASK_NOT_INSTANCES | M | M | M | M | M | M | skip | - |
| A10 | masks missing (no masks folder) | accepted | M | M | M | M | - | - | - | - |
| A11 | masks partial (DrugA not segmented yet) | accepted; requests: A_SCOPE_INCOMPLETE | M | M | M | M | M | M | M | - |
| A12 | shared 2-D mask for a time-lapse (YX mask, T=2) | refused: discovery:mask_planes_mismatch | M | - | - | - | - | - | - | - |
| A13 | mask declared binary holding instance labels (>2 values) | refused: R_MASK_CONTRADICTS_REPRESENTATION; requests: A_MASK_NOT_INSTANCES | MB | M | MB | MB | MB | MB | skip | M |
| A14 | grouped (parent_labels) mask declared instances | accepted | MS | M | M | M | M | M | skip | M |
| P01 | P=same, L=homogeneous, K=one, M=instances, H=named | accepted | M | M | M | M | M | M | skip | M |
| P02 | P=same, L=swapped-conditions, K=chain, M=binary, H=unnamed | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED); requests: A_MASK_NOT_INSTANCES | MB | MB | MB | MB | MB | MB | skip | M |
| P03 | P=same, L=tech-different, K=none, M=partial, H=alias | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED); requests: A_SCOPE_INCOMPLETE | M | - | - | - | - | - | - | - |
| P04 | P=different, L=homogeneous, K=one, M=binary, H=alias | accepted; requests: A_MASK_NOT_INSTANCES | MB | - | - | - | - | - | - | - |
| P05 | P=different, L=swapped-conditions, K=chain, M=partial, H=named | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED); requests: A_SCOPE_INCOMPLETE | M | - | - | - | - | - | - | - |
| P06 | P=different, L=tech-different, K=none, M=instances, H=unnamed | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | MB | MB | MB | MB | MB | MB | skip | M |
| P07 | P=missing, L=homogeneous, K=one, M=partial, H=unnamed | accepted; W_REPEAT_MISSING_CONDITIONS; requests: A_SCOPE_INCOMPLETE | M | M | M | M | M | M | M | - |
| P08 | P=missing, L=swapped-conditions, K=chain, M=instances, H=alias | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED); W_REPEAT_MISSING_CONDITIONS | M | - | - | - | - | - | - | - |
| P09 | P=missing, L=tech-different, K=none, M=binary, H=named | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED); W_REPEAT_MISSING_CONDITIONS; requests: A_MASK_NOT_INSTANCES | M | - | - | - | - | - | - | - |
| P10 | P=same, L=homogeneous, K=chain, M=instances, H=named | accepted | M | M | M | M | M | M | skip | M |
| P11 | P=same, L=homogeneous, K=none, M=instances, H=named | accepted | M | M | M | M | M | M | skip | M |
| P12 | P=same, L=swapped-conditions, K=one, M=instances, H=named | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | M | - | - | - | - | - | - | - |
| P13 | P=same, L=swapped-conditions, K=none, M=instances, H=named | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | M | - | - | - | - | - | - | - |
| P14 | P=same, L=tech-different, K=one, M=instances, H=named | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | M | - | - | - | - | - | - | - |
| P15 | P=same, L=tech-different, K=chain, M=instances, H=named | accepted (Stage 1-2: R_HETEROGENEOUS_LAYOUT_NOT_ENABLED) | M | - | - | - | - | - | - | - |
| N01 | NaN probe: a one-pixel object and an object flat in one channel | accepted | M | M | M | M | M | M | skip | M |

Per column: PP 63 M, 13 MB, 3 MS; NORM 51 M, 3 MB; CP 49 M, 5 MB; MO 47 M, 7 MB; MR 46 M, 7 MB;
FF 45 M, 6 MB, 1 B, 1 SKIP; ME 3 M, 3 MB, 47 SKIP; MC 41 M, 5 MB, 1 MS (the rest N/A).

### 3.1 Cell notes

Every non-MATCH cell and every preprocessing cell, with the observation behind it (generated by
`classify.py`; MorphoEmbed cells skipped for missing weights are not repeated).

- **A02** PP M: accepted
- **F01** PP MS: pp labels the missing condition level `single`; v1 has no rule for a condition without a folder (4.2 source_folder 'as read from disk')
- **F02** PP M: accepted
- **F03** PP M: accepted
- **F04** PP M: accepted
- **F05** PP M: accepted (warnings repeat_missing_conditions); MC MB: user's pairing Day1/Day2 lost: 'Not compared (no biological repeat holds both)'; the export has no repeat_group
- **F06** PP M: accepted (warnings repeat_missing_conditions)
- **F07** PP M: accepted; ME MB: fitted scaling keyed by source repeat label: 'rename one repeat'; MC MB: silently pairs CTRL/rep1 with DrugA/rep1 by folder label; the confirmed design pairs CTRL/rep1 with DrugA/rep2 (Day1): wrong pairing, no warning
- **F08** PP MB: accepted; v1 refuses (E_REPEAT_ID_SHADOWS_SOURCE): Stage 1 reader; ME MB: fitted scaling keyed by source repeat label: 'rename one repeat'; MC MB: pairs by folder label against the confirmed design (which v1 refuses anyway, E_REPEAT_ID_SHADOWS_SOURCE)
- **F09** PP M: accepted
- **F10** PP M: accepted
- **F11** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **F12** PP M: refused (tiff_outside_leaf) ~ spec discovery:tiff_outside_leaf
- **F13** PP M: accepted
- **F14** PP M: accepted
- **F15** PP M: accepted (warnings empty_folder)
- **F16** PP MS: pp keeps folder labels (v1 agrees); v1 has no 'propose another ID' rule for a biological-repeat folder whose label is a forbidden ID (`z`), 4.6a covers conditions and technical repeats only; MC MB: comparison by canonical condition ID `ctrl` refused (export carries the folder label `control`, no condition_id); by folder label it runs
- **F17** PP M: accepted
- **F18** PP M: refused (reserved_folder_name) ~ spec E_SINGLE_MISUSE, discovery:reserved_folder_name
- **F19** PP M: refused (case_conflict) ~ spec E_ID_CASE_COLLISION, discovery:case_conflict
- **F20** PP M: refused (invalid_name) ~ spec E_ID_TEXT, discovery:invalid_name
- **F21** PP MB: accepted; v1 refuses (E_ID_NOT_NFC, R_FOLDER_NOT_NFC): Stage 1 reader; MC MB: comparison by canonical condition ID refused (folder label only)
- **C01** PP M: accepted
- **C03** PP M: accepted
- **C04** PP M: accepted
- **C05** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **C06** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **C07** PP M: refused (channel_names_differ) ~ spec R_UNIT_NOT_HOMOGENEOUS
- **C08** PP M: refused (different_channel_counts) ~ spec R_UNIT_NOT_HOMOGENEOUS
- **C09** PP M: refused (different_channel_counts) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **C10** PP M: refused (different_channel_counts, missing_axes) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **C11** PP M: accepted
- **C12** PP MB: refused (channel_names_differ); v1 accepts (confirmed aliases)
- **C12b** PP M: refused (channel_names_differ) ~ spec R_HEADER_CONTRADICTION
- **C13** PP MB: refused (channel_names_differ); v1 accepts (confirmed aliases)
- **C14** PP MB: header `DAPI ` trimmed and matched to `DAPI` (channel_names_trimmed); v1 4.3 compares untrimmed (here both spellings confirmed, so the outcome agrees, the rule does not)
- **C15** PP M: accepted; MO MB: canonical ID `Tub` refused (header names are the IDs); with the header name `t` every FOV FAILS at provider time (reserved column), not refused at planning; MR MB: as MO: `Tub` refused; `t` fails every FOV at provider time; FF B: `Tub` refused (MB); with the header name, fiberfeatures ACCEPTS the reserved name `t` (output column t__Cells__fa_mean) where MorphoObjects/MorphoRelate refuse it; ME MB: canonical channel ID refused (header names are the IDs)
- **C16** PP M: accepted; MO MB: accepted silently; v1 refuses A_RGB_NOT_SUPPORTED (objects per FOV [3]); MR MB: accepted silently; v1 refuses A_RGB_NOT_SUPPORTED; FF MB: accepted silently; v1 refuses A_RGB_NOT_SUPPORTED
- **C17** PP MB: accepted silently: unnamed units with different channel orders cannot be declared, so channels are pooled by C index; NORM MB: SILENT: normalization pools C0 over DAPI (CTRL) and ACTIN (DrugA); per-unit channel lists cannot be declared; CP MB: patches carry C indices only; C0 is DAPI in CTRL and ACTIN in DrugA; MO MB: SILENT CHANNEL MIX-UP (canonical channel measured from another fluorophore): DAPI@DrugA/rep1=2000, DAPI@DrugA/rep2=2000, ACTIN@DrugA/rep1=1000, ACTIN@DrugA/rep2=1001; MR MB: SILENT CHANNEL MIX-UP (canonical channel measured from another fluorophore): DAPI@DrugA/rep1=2000, DAPI@DrugA/rep2=2000, ACTIN@DrugA/rep1=1000, ACTIN@DrugA/rep2=1001; FF MB: SILENT: `ACTIN` resolves to C1 everywhere; in DrugA C1 is DAPI
- **K01** PP M: accepted
- **K03** PP M: accepted
- **K04** PP M: accepted
- **K05** PP M: accepted
- **K06** PP MB: accepted; v1 refuses (E_REFERENCE_CYCLE): Stage 1 reader
- **K07** PP M: accepted
- **K08** PP M: accepted (warnings repeat_missing_conditions)
- **K09** PP M: accepted (warnings repeat_missing_conditions)
- **K10** PP M: accepted
- **K11** PP MB: accepted (no reader of the file today); v1 refuses E_REFERENCE_UNKNOWN; ME skip: as A02 (bricks read no description)
- **K12** PP MB: accepted (no reader of the file today); v1 refuses E_REFERENCE_SELF; ME skip: as A02 (bricks read no description)
- **A03** PP M: accepted; MC MS: export not written for several planes per FOV (MorphoCoverage#604); v1 is silent on T>1
- **A04** PP M: refused (mask_planes_mismatch, z_stack_not_supported) ~ spec discovery:z_stack_not_supported
- **A05** PP M: accepted (warnings non_square_pixels)
- **A06** PP M: accepted; FF skip: harness artefact: fiberfeatures' pixel defaults need a larger image than 32x32 (Gaussian kernel radius too large); not a v1 question
- **A07** PP M: accepted (warnings missing_pixel_size)
- **A08** PP M: accepted; CP MB: cell mode ran on a mask v1 declares binary (no representation known; a 0/1 mask is one object per FOV); v1 A_MASK_NOT_INSTANCES; MO MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES (objects per FOV [1]); MR MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES; FF MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES
- **A08b** PP M: accepted
- **A09** PP M: accepted
- **A10** PP M: accepted
- **A11** PP M: accepted (warnings mask_missing)
- **A12** PP M: refused (mask_planes_mismatch) ~ spec discovery:mask_planes_mismatch
- **A13** PP MB: accepted; v1 refuses (R_MASK_CONTRADICTS_REPRESENTATION): Stage 1 reader; CP MB: cell mode ran on a mask v1 declares binary (no representation known; a 0/1 mask is one object per FOV); v1 A_MASK_NOT_INSTANCES; MO MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES (objects per FOV [3]); MR MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES; FF MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES
- **A14** PP MS: v1 cannot describe a grouped mask (4.5b); declared `instances` it is measured as wrong objects and nothing can detect it; preprocessing's kind heuristic (median pieces per label > 2) reports this mask `instances` (superseded 11 November 2026 by owner decision PL1: v1 now describes it as `parent_labels`, 4.5b; declared `instances` it is still undetectable, so the declaration is the guard)
- **P01** PP M: accepted
- **P02** PP MB: accepted silently: unnamed units with different channel orders cannot be declared, so channels are pooled by C index; NORM MB: SILENT: C0/C1 pooled across conditions whose orders differ; CP MB: cell mode ran on a mask v1 declares binary (no representation known; a 0/1 mask is one object per FOV); v1 A_MASK_NOT_INSTANCES; MO MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES (objects per FOV [1]); MR MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES; FF MB: accepted silently; v1 refuses A_MASK_NOT_INSTANCES
- **P03** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **P04** PP MB: refused (channel_names_differ); v1 accepts (confirmed aliases)
- **P05** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **P06** PP MB: accepted silently: unnamed units with different channel orders cannot be declared, so channels are pooled by C index; NORM MB: SILENT: C0/C1 pooled across technical repeats whose orders differ; CP MB: patches by C index; technical repeats differ in order; MO MB: SILENT CHANNEL MIX-UP (canonical channel measured from another fluorophore): DAPI@CTRL/rep1=1501, DAPI@CTRL/rep2=1500, ACTIN@CTRL/rep1=1500, ACTIN@CTRL/rep2=1500; MR MB: SILENT CHANNEL MIX-UP (canonical channel measured from another fluorophore): DAPI@CTRL/rep1=1501, DAPI@CTRL/rep2=1500, ACTIN@CTRL/rep1=1500, ACTIN@CTRL/rep2=1500; FF MB: SILENT: one global name->index list for units of different order
- **P07** PP M: accepted (warnings mask_missing, repeat_missing_conditions)
- **P08** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **P09** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **P10** PP M: accepted
- **P11** PP M: accepted
- **P12** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **P13** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **P14** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **P15** PP M: refused (channel_names_differ) = Stage 1-2 R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3
- **N01** PP M: accepted

## 4. End-to-end checks

### 4.1 Accepted or refused, with the code

Every v1 refusal at the **file** level (`E_*`) that a folder check can see is already refused by
preprocessing's discovery under another code: `E_SINGLE_MISUSE` ↔ `reserved_folder_name` (F18),
`E_ID_CASE_COLLISION` ↔ `case_conflict` (F19), `E_ID_TEXT` ↔ `invalid_name` (F20). Those that need
the user's answers are not refused, because nothing reads them yet: `E_REPEAT_ID_SHADOWS_SOURCE`
(F08: `design --repeat-group` accepts the swap), `E_REFERENCE_CYCLE`/`_SELF`/`_UNKNOWN` (K06, K12,
K11: `design --control` records a boolean per condition, `design.py:169-171`), `E_ID_NOT_NFC` and
`R_FOLDER_NOT_NFC` (F21: `check_identity_text`, `discovery.py:69-106`, has no NFC test),
`R_MASK_CONTRADICTS_REPRESENTATION` (A13: the mask step reports a kind suggestion,
`mask_scan.py:476-483`, and refuses nothing). `R_UNIT_NOT_HOMOGENEOUS` (C07, C08) is refused as
`channel_names_differ` / `different_channel_counts` (named images only; see 4.3).

### 4.2 Identities and pairing end to end

- **FOV key.** Every brick keeps `condition`, `biological_repeat`, `technical_repeat` as the
  source folder labels (also `control`, `z`, `files`, `single`, `Café`), as 3.4 requires. No brick
  carries `repeat_group`, `condition_id` or `technical_repeat_id` (MorphoFeature
  `identity.py:30`, `coverage_export.py:188`).
- **Repeat pairing.** Preprocessing records the user's pairing in `experiment_design.csv`
  (`repeat_group`), and CellPatcher's normalization pools exactly by it (NORM column: Day1/Day2 in
  F05 and F07, R1 in F16). MorphoCoverage pairs by `biological_repeat` (`metadata.py:36`,
  `sampling_unit/contrast.py:209`): F05 (v03) gives "Not compared: DrugA vs CTRL (no biological
  repeat holds both)" although the user paired them; F07 (v30: CTRL/rep1 + DrugA/rep2 = Day1)
  compares CTRL/rep1 with DrugA/rep1 instead, **silently**, with 2 "paired" repeats. MorphoEmbed's
  fitted scaling refuses F07 and F08 ("rename one repeat", MorphoFeature `scaling.py:212-221`, also
  `@main`).
- **Technical repeats** stay inside their biological repeat everywhere; MorphoCoverage uses
  `technical_repeat` as the randomization unit in every run (`unit: technical_repeat`), so FOVs
  and technical repeats never become biological N (pseudo-replication guard holds).
- **Condition IDs.** A comparison written with the canonical condition ID (`ctrl` for the folder
  `control`, F16; `Cafe` for `Café`, F21) is refused by MorphoCoverage ("absent from the tables");
  the same comparison by folder label runs. The reference/control choice itself does not travel:
  preprocessing stores a `control` boolean, MorphoFeature only displays it, the export has no
  control, and the user must type the comparisons again in MorphoCoverage. Chains (K05, P10) and
  matched controls (K04) work there as `own_control` rows; a mutual pair A↔B (K06) is accepted by
  MorphoCoverage, which is harmless there because the file refuses the cycle first.

### 4.3 Channel → index end to end

- With named headers, preprocessing compares names per C index over the whole experiment
  (`metadata.py:584-622`), so any heterogeneous layout, alias or case variant stops the run
  (`channel_names_differ`, `different_channel_counts`): that equals the Stage 1-2 interim
  `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` for layouts (MATCH) but refuses v1-valid confirmed aliases
  (C12, C13: MB). Header names are trimmed (`zarr_input.py:68`; C14 records
  `channel_names_trimmed`), against 4.3.
- With **unnamed** images nothing compares channels: preprocessing and MorphoFeature take one
  global name→index list (`run_config.py:326-347`, `channels.py:149`), CellPatcher and the
  normalization pool by C index. C17 (order swapped between conditions) and P06 (between technical
  repeats) run to the end with DAPI measured from the Actin channel (MorphoObjects and MorphoRelate
  means 2000 instead of 1000 in DrugA; 1500 = the two pooled in P06; normalization C0 pooled across
  fluorophores). No warning is given anywhere. v1 resolves this only through the per-unit lists the
  user declares (Stage 1-2 must then refuse with `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED`).
- MorphoFeature's channel identities are the recorded header names (`run_config.py:332-340`,
  `channels.py:93-117`), so a canonical ID different from the header (`DNA` for `DAPI`, `Tub` for
  `t`) is refused ("names the channel(s) ['Tub'], which the preprocessing run does not record").
- RGB (C16): preprocessing suggests `rgb` from the header and records it; MorphoObjects,
  MorphoRelate and fiberfeatures measure R, G and B as three grey channels with no capability check
  (MorphoFeature has no RGB handling at all); v1 expects `A_RGB_NOT_SUPPORTED` unless a brick
  declares support.

### 4.4 NaN, fill and masks

- **NaN.** Across all runs 16 NaN cells were produced (N01: MorphoRelate `correlation` on an object
  flat in one channel); all 16 have an applicability row with a state. No zero-fill or
  imputation was seen; MorphoObjects returns finite values for a one-pixel object.
- **Binary masks.** A 0/1 integer mask with two separate blobs is one object per FOV in
  MorphoObjects, MorphoRelate, fiberfeatures and CellPatcher cell mode (A08, P02: objects per FOV
  1 instead of 2), with no warning: no brick knows the representation (MorphoObjects refuses only
  boolean dtype, `validation.py:57-63`; CellPatcher "instance labels used as given",
  `README.md:28`). Boolean masks are refused by every provider (A09) and converted only with
  CellPatcher's explicit `binary_mask_policy="connected_components"` (A08b), as 4.5c wants.
- **Partial / missing / shared masks** are refused explicitly (A11: "Cells: 4 of 8 images
  segmented"; A12: `mask_planes_mismatch`), never dropped or filled.
- **Unchecked masks.** No analysis brick reads the mask step's result (`mask_relationships.json` is
  read only by MorphoFeature's notebook, `notebook_steps.py`), so `A_MASK_UNCHECKED` has no
  counterpart today (code reading; every case here ran the mask step).

### 4.5 Cache keys and provenance

- MorphoFeature's brick cache key holds the provider identity, the FOV key, the requests and a
  digest of every channel plane by **channel name** and every mask (`brick_cache.py:223-246`): a
  channel renamed or moved to another index changes the key, so v1's "a change to a unit's channel
  list MUST invalidate" holds for per-FOV products. The fit memo key holds the **whole**
  `experiment_design.csv` SHA-256 (`fits.py:226-232`), so toggling a control mark refits model-input
  scaling, which 9.3 forbids for `reference` (over-invalidation, not a wrong reuse).
- Preprocessing's restart reuse keys rows on the image file (size, mtime, optional content hash);
  the histogram table does not depend on the design, as 9.3 expects.
- Provenance: MorphoFeature's manifest records the preprocessing run folder, its manifest SHA-256
  and `plane_histograms.csv` SHA-256 and each FOV's calibration source; the preprocessing manifest
  records `experiment_design_sha256`; CellPatcher writes `run_config.json` beside its patches.
  The chain from a feature value back to the confirmed design is therefore complete by hash, but no
  file names the confirmed pairing or control next to the features.

## 5. Ranked loose ends

Tags: **BLOCKER** (wrong results or a v1 rule that cannot be met; fix before Stage 2 gate),
**STAGE** (planned Stage 1-3 work, evidence attached), **FILE** (file an issue; the coordinator
files them). Citations at the SHAs of section 1.

1. **BLOCKER, STAGE 2 (S2.5).** Confirmed repeat pairing is lost between preprocessing and
   MorphoCoverage: MorphoFeature exports only the FOV key (`morphofeature/identity.py:30`,
   `coverage_export.py:188`) and MorphoCoverage pairs by `biological_repeat`
   (`morphocoverage/metadata.py:36`, `sampling_unit/contrast.py:209`). v03 pairing lost (F05),
   v30 pairing silently replaced (F07). Arguably a BUG today already, since preprocessing's own
   contract §12 defines the repeat group as the biological repeat.
2. **BLOCKER, STAGE 1/3.** Unnamed images with different channel orders between units are pooled
   by C index in every brick without a warning (C17, P02, P06; MorphoFeature
   `run_config.py:326-347`, `channels.py:149`; preprocessing compares named channels only,
   `metadata.py:584-622`). Stage 1 must take the per-unit lists from the description and refuse
   with `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` until Stage 3.
3. **BLOCKER, STAGE 2.** A 0/1 integer region mask is measured as one object per FOV by
   MorphoObjects, MorphoRelate, fiberfeatures and CellPatcher (A08, P02; MorphoObjects
   `validation.py:57-63`, CellPatcher `README.md:28`): the representation must reach the analysis
   layer and raise `A_MASK_NOT_INSTANCES`.
4. **STAGE 1.** No reader: swapped pairing (F08), reference cycle/self/display name (K06, K12,
   K11), non-NFC folders (F21, `discovery.py:69-106`), declared-binary contradiction (A13,
   `mask_scan.py:476-483`) are all accepted today.
5. **STAGE 1.** Header evidence: confirmed aliases and case variants are refused
   (`channel_names_differ`, `metadata.py:611`; C12, C13) and outer whitespace is trimmed
   (`zarr_input.py:68`; C14).
6. **STAGE 2.** MorphoFeature uses header names as channel IDs; canonical IDs differing from the
   header are refused (C15; `run_config.py:332-340`, `channels.py:93-117`).
7. **BUG, FILE (MorphoFeature, fiberfeatures).** A header channel name `t` (a MorphoBricks reserved
   column) passes MorphoFeature's planning, then every FOV **fails** in MorphoObjects
   (`naming.py:86`) and MorphoRelate (`registry/_expand.py:102`) at provider time (exit 3), while
   fiberfeatures accepts it and writes `t__Cells__fa_mean` (C15). The shared name rules are applied
   inconsistently and too late; v1's reserved list (AQ4) is the intended single rule.
8. **STAGE 2, FILE (spec).** RGB units are measured as three grey channels by every provider (C16);
   4.4b requires bricks to declare RGB support in "documented capabilities", but there is no
   machine-readable capability field (provider manifests have none), so `A_RGB_NOT_SUPPORTED`
   cannot be implemented as written.
9. **STAGE 2.** MorphoFeature's fitted scaling is keyed by source repeat label and refuses v30
   designs ("rename one repeat", `scaling.py:212-221`, unchanged `@main`; F07, F08); its fit memo key
   holds the whole design SHA-256 (`fits.py:226-232`), so a control toggle refits (9.3).
10. **STAGE 2.** Canonical condition IDs cannot be used downstream: MorphoCoverage refuses a
    comparison by `ctrl` when the folder is `control` (F16, F21); the export needs `condition_id`
    (3.4, fourth round).
11. **FILE (spec), MS-4.** v1 is silent on time-lapses (T>1, Z=1). They run through every brick,
    but MorphoFeature does not export several planes per FOV to MorphoCoverage (A03,
    MorphoCoverage#604), so a time-lapse never reaches the statistics.
12. **FILE (spec), MS-1.** A flat experiment (images in the root) has no condition folder;
    preprocessing labels it `single`; v1 4.2 defines `source_folder` as the folder label read from
    disk and has no `single` rule for conditions (F01; fixture `v35`).
13. **FILE (spec), MS-2.** A biological-repeat folder named like a forbidden key (`z`) defaults to
    the repeat ID `z` (3.1), which is `E_FORBIDDEN_FIELD` (`i130`); 4.6a's "propose another ID" rule
    names conditions and technical repeats only (F16; fixture `v36`).
14. **FILE (spec), MS-5.** Grouped masks cannot be described (4.5b) and, declared `instances`, are
    measured as wrong objects; preprocessing's kind heuristic (`mask_scan.py:480-481`, median pieces
    per label > 2) calls a mask with a two-piece label `instances` (A14). **Since 11 November 2026** (owner
    decision PL1, ADR 0001) v1 describes grouped masks (`parent_labels`, 4.5b); the rest stands.
15. **FILE (preprocessing).** `run` applies the suggested image type when `--image-type` is absent
    (`cli_run.py:487-489`), against preprocessing contract §13 ("never applied without the user's
    confirmation") and v1 4.4b ("never inferred"). Code reading; every case here passed
    `--image-type`.
16. **STAGE 1-2.** `A_MASK_UNCHECKED` has no counterpart: no analysis brick reads the mask step's
    result (code reading, 4.4).

## 6. Limitations

- Tiny synthetic images (32x32) suit identity checks, not numerical ones; fiberfeatures' pixel
  defaults need larger images (A06 SKIP).
- MorphoEmbed was planned only (no weights): 47 SKIP cells; its six other reached cells are
  refusals before the checkpoint, three MB (F07, F08: repeat label; C15: channel name) and three
  M (A07 mixed calibration; A11, P07 missing masks).
- The physical oracle implements the `R_*`/`A_*` rules for the situations the cases build; it is
  not a full preprocessing reconciliation (drafts, base SHA-256, transitions on disk).
- Brick behaviour was observed through public entry points with the settings named in section 2;
  other settings (CellPatcher `apply_mask`, MorphoFeature `workers > 0`, MorphoCoverage families)
  were not varied.

## 7. Reproduction

See [`tools/audit/README.md`](../../tools/audit/README.md). `python -I tools/audit/refval.py
fixtures .` needs only Python 3.11+; the brick run needs the environment of section 1 and about 20
minutes; `classify.py` regenerates section 3 from `tools/audit/results/`.
