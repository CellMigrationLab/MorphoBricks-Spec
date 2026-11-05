# RFC #1: addendum after ChatGPT's response (5 November 2026)

This addendum updates [rfc1-feasibility-2026-11-05.md](rfc1-feasibility-2026-11-05.md). It is
checked against the **revised** RFC body (technical repeat = homogeneous imaging unit; `Rxxx`
= canonical `biological_repeat`) and the ChatGPT review in the issue thread. Where this file
and the first audit disagree, this file wins.

## 1. Corrections to the first audit
- **Hierarchy (ChatGPT point A): accepted.** The first audit judged the earlier
  per-biological-repeat layout. The technical repeat as the imaging unit is better:
  - it matches preprocessing's existing leaf folder (condition × biological repeat × technical
    repeat);
  - it avoids pseudoreplication from splitting acquisitions into fake biological repeats.
  The audit's advice to "require one layout per member" is withdrawn.
- **Schema capability vs runtime support (B): accepted.** The v1 schema may describe
  heterogeneous layouts while preprocessing still refuses them at run time, until normalization
  and CellPatcher are migrated (Stage 3). The refusal must name the unit and the reason.
- **Mask `representation` (D): accepted.** `instances` vs `binary` is scientific meaning, and it
  is never inferred from pixels.
- **2-D-only contract (E): now verified on the merged release code.** preprocessing #173 is merged
  (`6e740196`), and v0.4.0 is being released from it.
  - `--mask-axes Type=YX` is refused (`shared_mask_not_supported`).
  - `MaskFile.shared` is gone.
  - Z > 1 is refused.

## 2. Remaining conflicts in the current RFC text
1. **Masks: `axes: YX` and `shared: true`** contradict merged preprocessing. Remove `shared`, and
   remove `axes` too: in v1 a mask has the axes of its image (YX, or TYX for time-lapses), so the
   field adds nothing but a way to disagree. The 3-D strategy is MorphoFeature #157.
2. **File format.** The RFC still names `morphobricks.yaml`; ChatGPT now agrees on TOML or strict
   JSON (duplicate keys, `NO`→false, `012`→10 and dates under PyYAML `safe_load`). Owner
   decision needed; the recommendation is TOML (`morphobricks.toml`).
3. **Histogram layout.**
   - The RFC still calls "one row per plane × channel" the leading design; ChatGPT now
     prefers a semantic-wide table with one row per plane.
   - Recommendation: semantic-wide is the default candidate, because the plane stays the
     sampling row (normalization rules N41/N42).
   - Freeze nothing until the parity, pooling, missing-channel and pseudoreplication tests pass
     on both candidates.
4. **Canonical repeat IDs.**
   - The RFC says `R001`… are generated. ChatGPT (C) says stable, user-confirmed IDs.
   - Recommendation: when a pairing is trivial (the same folder name across conditions), the
     canonical ID **defaults to that name**. That way existing datasets keep their
     `biological_repeat` values, and their FOV identities, cache keys and MorphoCoverage tables
     do not churn.
   - Only paired, differently named folders need a new ID, and the user confirms it.
   - IDs are never renumbered or reused.
   - Changing `biological_repeat` for an existing dataset is an identity migration, so it must be
     explicit and recorded.

## 3. New risks the revised model brings
- **Partial channel presence inside one biological repeat.** Example: PHASE only in
  `acquisition_1` of R002/CTRL.
  - A PHASE analysis then sees part of a biological repeat. Per-repeat normalization and
    MorphoCoverage blocking must state that the repeat is partially represented.
  - Its technical repeats must never be silently mixed or weighted differently.
  - The scope check must be per imaging unit and visible in the run manifest.
- **Normalization by biological repeat with mixed layouts.** Each canonical channel pools only
  the units that have it, by canonical ID and never by C index. CellPatcher's per-channel
  selection and export must follow the same rule. This is the Stage 3 gate.
- **Identity change downstream.** `technical_repeat` names such as `single` or `acquisition_1`
  come from folders. Check uniqueness and case rules with preprocessing's existing identity rules,
  and never parse them.

## 4. Agreed plan (merges the audit's and ChatGPT's orders)
0. **Owner decisions (docs only, now):**
   - the format (TOML recommended);
   - the canonical repeat-ID policy (§2.4);
   - the mask fields (§2.1);
   - the histogram candidates to benchmark;
   - that calibration stays in `calibration.csv`;
   - that `experiment_design.csv` stays a derived compatibility file;
   - that the N35 comparability confirmation is kept and reopened when discovery changes;
   - header aliases are user-confirmed.
   Then M0: docs, JSON Schema or TOML schema, fixtures (the RFC's 12 plus ChatGPT's 10
   adversarial tests).
1. **Stage 1 (after the first tags):** preprocessing authors, confirms and reconciles the file; a
   semantic `RunInputs`; the derived `experiment_design.csv`; heterogeneous runs are still refused.
2. **Stage 2:** bricks adopt canonical channels and repeat IDs one by one; MorphoCoverage gets the
   reference graph.
3. **Stage 3:** normalization, preprocessing and CellPatcher enable heterogeneous layouts together,
   after the histogram benchmark and legacy parity.
4. **Stage 4:** the mask semantics, progressive segmentation, and end-to-end scientific regression.

No spec runtime package at first: the Spec repo owns the normative docs, fixtures and conformance
tests, and preprocessing is the reference reader.
