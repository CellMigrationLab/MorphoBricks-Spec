You are an independent, sceptical reviewer for MorphoBricks, a set of scientific image-analysis packages, and for its experiment-description specification (MorphoBricks-Spec). An AI agent ran an **executable matrix audit**: 79 synthetic experiments (folder structures, channel layouts, control designs, axes, calibration and masks) were described with the specification's file `morphobricks.toml`, validated with an audit-only reference validator, and run through the released bricks. It reports which brick behaviours match the specification, which differ and which are wrong. Your task is to **check its claims against the code and documents at the exact SHAs below**, and to find what it missed. Do not trust the audit's prose, its verdict columns or its "known" labels: read the code, the spec and the recorded results. You cannot run code, so every verdict is from reading only; use CANNOT TELL when a claim needs a run. If a repository is private or a SHA cannot be opened, say so at the top and mark every dependent claim CANNOT TELL. Never substitute another commit or a branch head.

## What your answer is for
The owner uses it to decide what must change before Stage 1 (the reference reader in preprocessing) and Stage 2 (consumers read canonical IDs), and to file the rest.
- **BLOCKER:** a wrong or silently altered scientific output, a valid input refused without a path, a guessed or filled value, an identity (condition, biological repeat, technical repeat, channel, object) that is lost or replaced between bricks, or a spec rule that cannot be implemented as written.
- **FILE:** a real defect or spec gap that is not blocking (one-line title, file:line, suggested fix).
Do not pad. A style preference is neither. If you find nothing, say so.

## Science rules (any violation is a finding)
- No guessed axes, channels, biological repeats, calibration (pixel sizes) or object identity.
- No silent fill, coercion or fallback: no zero-fill, imputation, default substituted for a missing value, CPU/GPU fallback, model substitution or download. **Refuse rather than guess.**
- Identities (FOV keys, `patch_id`, `position_id`, folder labels, canonical IDs) are **never parsed** for meaning, never repaired, never replaced by another. Objects are never joined by numeric label alone across masks or FOVs.
- Biological N is the number of confirmed biological repeats; technical repeats and FOVs never add to it (no pseudo-replication).
- Channels are resolved by confirmed canonical ID per imaging unit, never by C index alone.
- **Every NaN or unknown value is explained.** A failed measurement is never read as biology.
- **No cache reuse when source or provider identity is uncertain**; descriptive fields (`display_name`, `target`, `treatment_key`) are never cache keys.

## Repositories and exact SHAs
URL pattern: `https://github.com/CellMigrationLab/<repo>/blob/<sha>/<path>#L<line>`.

| Repository | Review at | Note |
|---|---|---|
| [MorphoBricks-Spec](https://github.com/CellMigrationLab/MorphoBricks-Spec) | `cc31e4e3b8dc0e587acf399d7b66034869ea5555` (branch `claude/matrix-audit`; this prompt is added in the next commit) | Spec base `8479864e3ad80ce6b3d6e30e2fa0355fdee9e44e` (`claude/youthful-carson-klzm3w`, the default branch). Read `docs/experiment-v1.md`, `docs/adr/0001-experiment-description-v1.md`, `fixtures/README.md`, `docs/audits/matrix-audit-2026-11-07.md`, `tools/audit/*.py`, `tools/audit/results/` |
| [morphobricks-preprocessing](https://github.com/CellMigrationLab/morphobricks-preprocessing) | `bc7b872bd3ccb30dcd5de812e99a3485a3281825` (`v0.4.0`) | main `34cbf1c24fbd871ac2247e8cdff5518b43253c84`: confirm it changes nothing below |
| [morphobricks-normalization](https://github.com/CellMigrationLab/morphobricks-normalization) | `1c1c7b48a041e23bd390037bd6ab837e1e5f1c85` (`v0.3.4`) | |
| [CellPatcher](https://github.com/CellMigrationLab/CellPatcher) | `498825e977f1df5be623416bcacc7464990486e9` (`v0.2.0`) | |
| [MorphoObjects](https://github.com/CellMigrationLab/MorphoObjects) | `478c916ea601f150c062cc4326fe9413e9e5500f` (`v0.1.0`) | |
| [MorphoEmbed](https://github.com/CellMigrationLab/MorphoEmbed) | `3c16bce2bb6b08f73e693dc23b15a2048bfa6649` (`v0.1.0`) | weights were absent: planned only |
| [MorphoRelate](https://github.com/CellMigrationLab/MorphoRelate) | `160ad2314ed2f156666421add2d3ba269cf8abb7` (`v0.1.1`) | |
| [fiberfeatures](https://github.com/CellMigrationLab/fiberfeatures) | `8798b7585ec91f7c380f815de95bc34f82eb401a` (`v0.2.1`) | |
| [MorphoFeature](https://github.com/CellMigrationLab/MorphoFeature) | `182b3735d33eac7d40902f82d69885ef6fb3aae8` (`v0.1.0`) | main `60f4a92cb42716184b3ea7d0b804c873a8dd0852`: confirm claims 6 and 9 hold there too |
| [MorphoCoverage](https://github.com/CellMigrationLab/MorphoCoverage) | `64ff307d90fe5eb62a72630f35b85bd7fe6040a4` (main, no tag) | |

## Owner decisions: treat as given, do NOT challenge
- The spec text at `8479864` is normative, including ADR 0001's four rounds (AQ1-AQ13, folder labels never restricted, canonical condition/technical-repeat IDs separate from `source_folder`).
- The FOV key keeps the **source folder labels**; canonical IDs are **added** (`repeat_group`, `condition_id`, `technical_repeat_id`), never substituted (experiment-v1 3.4).
- Heterogeneous unit layouts are valid v1 but refused at Stage 1-2 with `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED`; lifted at Stage 3.
- v1 is 2-D only; Z>1 is refused until a recorded projection step exists. Grouped (`parent_labels`) masks are out of scope in v1.
- Calibration, file inventory and analysis settings are never in `morphobricks.toml`.
- The audit tools under `tools/audit/` are audit-only; the single reference reader of v1 is preprocessing.

## Claims to verify (one verdict each: CONFIRMED, WRONG, PARTLY, CANNOT TELL, with file:line)

### A. Reference validator and fixtures
1. `tools/audit/refval.py` implements experiment-v1 sections 2-6 phase by phase (stop after the first failing phase, report every error of that phase, one code per broken rule), the canonical writer of 9.1 and the predecessor checks of 4.4a/4.6/4.9. Check in particular: forbidden names on ID keys (4.7) reported in phase 3 and their subtree skipped; NFC-only checks of references, member keys, unit `channels` and `source_channels` in phase 4; the `single` rules of 3.2 including source folders; display-name collision keys `NFC(casefold(NFC(x)))` with technical repeats of one ID never colliding with each other; `E_REPEAT_ID_SHADOWS_SOURCE` compared case-insensitively. List every place where the code departs from the text, including the two places marked `AMBIGUITY` (reserved list not applied to `used_ids.channels`; byte form of a section digest).
2. The fixtures `v35`, `v36`, `i128`, `i129`, `i130` are correct under the text: v35 and v36 valid with no warnings; i128 and i129 exactly `E_SINGLE_MISUSE` (phase 4); i130 exactly `E_FORBIDDEN_FIELD` (phase 3). The README tables and counts (36 valid, 130 invalid) agree with the files.

### B. Matrix construction
3. The pruning rule (OFAT over every requested level from one base case, plus a greedy all-pairs array over five three-level factors) is what `tools/audit/matrix.py` builds, and every pair of levels of the five factors occurs in some `P` case. Section 2.1 of the audit lists a case for every requested item; name any requested item with no case.
4. The expected outcome of each case (`results/cases/<case>.toml` headers) follows from the spec: in particular F07 (same source label in two repeats) is valid; F08 is `E_REPEAT_ID_SHADOWS_SOURCE`; C14 (header `DAPI ` and `DAPI`, both confirmed) is valid; C12b is `R_HEADER_CONTRADICTION`; A13 is `R_MASK_CONTRADICTS_REPRESENTATION`; C16 requests are `A_RGB_NOT_SUPPORTED` for every brick except CellPatcher (README declares RGB). Point out any expected outcome that the spec does not support.

### C. Brick findings
5. **Pairing lost (BLOCKER claimed).** MorphoFeature's MorphoCoverage export holds only `condition`, `biological_repeat`, `technical_repeat`, `position_id` (`morphofeature/identity.py:30`, `coverage_export.py:188`), and MorphoCoverage's `condition_contrast` pairs by `biological_repeat` (`morphocoverage/metadata.py:36`, `sampling_unit/contrast.py:209`), so a user's `repeat_group` pairing (v03: rep1 + experiment_23 = Day1) is lost and a v30 pairing (CTRL/rep1 + DrugA/rep2 = Day1) is silently replaced by folder-label pairing. Is there any path in MorphoFeature or MorphoCoverage at these SHAs that carries `repeat_group` to the contrast? Is this already wrong against preprocessing's own contract §12 (repeat group = one biological repeat across conditions)?
6. **Silent channel mix-up (BLOCKER claimed).** With unnamed images, preprocessing compares no channel identity (`metadata.py:584-622` compares named channels only), and MorphoFeature resolves one global name→index list (`run_config.py:326-347`, `channels.py:149`), so units with different channel orders are pooled by C index in normalization, CellPatcher and every provider without a warning (C17, P06). Confirm, and say whether any brick could detect it from headers alone.
7. **Binary masks (BLOCKER claimed).** A 0/1 integer mask is one object per FOV in MorphoObjects (`validation.py:57-63` refuses only boolean dtype), MorphoRelate, fiberfeatures and CellPatcher cell mode (`README.md:28`); preprocessing's mask step only suggests `one_value` (`mask_scan.py:476-483`). Is there any representation input in any brick at these SHAs?
8. **No reader yet.** Preprocessing accepts swapped pairing (`design --repeat-group`), cycles and self references (a `control` boolean, `design.py:169-171`), non-NFC folder labels (`discovery.py:69-106`) and a mask declared binary that holds instances. Confirm each.
9. **Header evidence and channel IDs.** Preprocessing refuses confirmed aliases and case variants (`channel_names_differ`, `metadata.py:611`) and trims outer whitespace (`zarr_input.py:68`); MorphoFeature uses recorded header names as channel IDs and refuses a canonical ID that differs (`run_config.py:332-340`, `channels.py:93-117`); its fitted scaling refuses a v30 design ("rename one repeat", `scaling.py:212-221`).
10. **Reserved channel name (BUG claimed).** A header channel named `t` passes MorphoFeature's planning, then every FOV fails in MorphoObjects (`naming.py:86`) and MorphoRelate (`registry/_expand.py:102`) at provider time, while fiberfeatures accepts it. Is the late failure and the disagreement between providers a defect today, independently of the spec?
11. **RGB.** MorphoFeature has no RGB handling; MorphoObjects, MorphoRelate and fiberfeatures measure R, G, B as grey channels. Does any provider manifest have a field that could declare RGB support (spec 4.4b "documented capabilities")?
12. **Cache keys.** MorphoFeature's brick cache key covers provider identity, FOV key, requests and a digest of every channel plane by name and every mask (`brick_cache.py:223-246`); the fit memo key holds the whole design SHA-256 (`fits.py:226-232`), so a control toggle refits. Is anything that changes an output missing from either key?
13. **Image type.** Preprocessing `run` applies the suggested image type when `--image-type` is absent (`cli_run.py:487-489`), against its contract §13 and spec 4.4b.
14. **What the audit calls MATCH:** CellPatcher normalization pools by the confirmed `repeat_group` (`normalization.py:484`); MorphoCoverage uses `technical_repeat` as the unit; partial masks are refused, not dropped; every NaN produced has an applicability row. Look for a counter-example in the code.

### D. Spec gaps claimed (MISMATCH-SPEC)
15. A flat experiment has no condition folder; v1 4.2 cannot say what its `source_folder` is (F01, `v35`).
16. 4.6a's "propose another ID" rule covers conditions and technical repeats only, not a biological-repeat folder named like a forbidden key (`z`) (F16, `v36`, `i130`).
17. v1 is silent on time-lapses (T>1, Z=1), and MorphoFeature's export refuses several planes per FOV (MorphoCoverage#604), so time-lapses never reach MorphoCoverage (A03).
18. Grouped masks declared `instances` are undetectable (A14).

## Also look for (not claimed by the audit)
- Any place where a brick replaces a source folder label by another value, or groups/pairs by `display_name`, `target` or `treatment_key`.
- Any brick that fills, drops or re-weights FOVs, technical repeats or objects when a channel or mask is missing from part of the scope, instead of refusing (`A_SCOPE_INCOMPLETE`).
- Any default `representation`, `image_type`, channel name or repeat group taken without a user statement.
- Contradictions between experiment-v1, ADR 0001, the conformance plan and the fixture catalogue.

## Output format
1. A table: claim number, verdict, evidence (file:line URL at the SHA), one-sentence reason.
2. New findings, each tagged **BLOCKER** or **FILE**, with file:line and a suggested fix.
3. One paragraph: is the ranked list in section 5 of the audit in the right order? What would you move?
