# Which brick pins which Spec commit

Owner decision of 2026-11-09: a brick gets the Spec's test material as a **pinned copy** made by
[`tools/vendor.py`](../tools/vendor.py), never as a runtime dependency. This table records which
brick pins which Spec commit. Workflow: [vendoring.md](vendoring.md).

**File set.** "Standard" means what `vendor.py` copies: `fixtures/`, `docs/experiment-v1.md`,
`tools/audit/refval.py` and `tools/audit/refrecords.py`, plus `PIN.toml`, `README.md` and
`.gitattributes`.

**README.** `vendor.py` manages the whole destination folder, `README.md` included, and writes a
generic one. morphobricks-preprocessing's current `README.md` is brick-specific; it adopts the
generic one in a later PR, after its v0.5.0 tag, and until then must not run `vendor.py --check`
([vendoring.md](vendoring.md)).

Update a row in the same Spec pull request (or a follow-up) whenever a brick's re-pin merges.

| Brick | Pinned Spec commit | Date | PR | File set |
|---|---|---|---|---|
| morphobricks-preprocessing | [`69a58b3`](https://github.com/CellMigrationLab/MorphoBricks-Spec/commit/69a58b3e2f89b318364c4c1252c54caf676fb6bb) | 2026-11-12 | [preprocessing #289](https://github.com/CellMigrationLab/morphobricks-preprocessing/pull/289) (released in v0.5.2, tag `6d81bcf`, release PR #290; normalization `v0.5.0`) | Standard |
| morphobricks-normalization | not pinned; pinned with its Stage 2 PR | | | canonical-channel / canonical-ID pooling (Stage 2-3) |
| MorphoFeature | not pinned; pinned with its Stage 2 PR | | | P24 `rgb_support` in provider manifests, P25 `repeat_group` to MorphoCoverage, P27 `binary_mask_policy` |
| fiberfeatures | [`69a58b3`](https://github.com/CellMigrationLab/MorphoBricks-Spec/commit/69a58b3e2f89b318364c4c1252c54caf676fb6bb) | 2026-11-12 | [fiberfeatures #211](https://github.com/CellMigrationLab/fiberfeatures/pull/211) (merged as `47f68e8`; W3: preprocessing `v0.5.2`, CellPatcher `v0.5.0`, normalization `v0.5.0`; was `cc9820f` from fiberfeatures #201) | Standard (PL1 `parent_labels`: no `parent_labels_support` declared; objects refused by the resolver, never CellPatcher's cells; the direct route's analysis-mask region read as its area, `parent_labels_as_area` shown and recorded; channels by canonical ID per image, Spec `v04`) |
| MorphoCoverage | not pinned; pinned with its Stage 2 PR | | | P31 `target` prefill, P25, MC4/S2.5 |
| MorphoRelate | [`cc9820f`](https://github.com/CellMigrationLab/MorphoBricks-Spec/commit/cc9820f5b84f01bbbb5c8e3f54e70ee13cb5e9eb) | 2026-11-11 | [MorphoRelate #239](https://github.com/CellMigrationLab/MorphoRelate/pull/239) (merged as `d7d166a`; preprocessing `v0.5.0`, CellPatcher `v0.3.0`) | Standard (canonical-channel adapter later) |
| MorphoObjects | [`69a58b3`](https://github.com/CellMigrationLab/MorphoBricks-Spec/commit/69a58b3e2f89b318364c4c1252c54caf676fb6bb) | 2026-11-12 | [MorphoObjects #76](https://github.com/CellMigrationLab/MorphoObjects/pull/76) (merged as `edd1b40`; W3: preprocessing `v0.5.2`, CellPatcher `v0.5.0`, normalization `v0.5.0` through them; was `cc9820f` from MorphoObjects #70) | Standard (PL1 `parent_labels`: no `parent_labels_support` declared; objects refused by the resolver, a patch region read as its area; MorphoObjects reads no run itself) |
| MorphoEmbed | [`cc9820f`](https://github.com/CellMigrationLab/MorphoBricks-Spec/commit/cc9820f5b84f01bbbb5c8e3f54e70ee13cb5e9eb) | 2026-11-11 | [MorphoEmbed #56](https://github.com/CellMigrationLab/MorphoEmbed/pull/56) (merged as `9f989f4`; preprocessing `v0.5.0`, CellPatcher `v0.3.0`) | Standard (P24, P27 later; has a `provider_manifest` module) |
| CellPatcher | [`69a58b3`](https://github.com/CellMigrationLab/MorphoBricks-Spec/commit/69a58b3e2f89b318364c4c1252c54caf676fb6bb) | 2026-11-12 | [CellPatcher #104](https://github.com/CellMigrationLab/CellPatcher/pull/104) (merged as `63e8f5e`; W3: preprocessing `v0.5.2`, normalization `v0.5.0`; was `b4b1008` from CellPatcher #99, `6d22761` from #97) | Standard (P32 `condition_id`/`technical_repeat_id` and P25 tests; P27; PL1 `parent_labels`: objects refused, random-mode area `parent_labels_as_area`) |

For the unpinned bricks the last column is the Stage 2 item that will make the brick read a
Spec-defined artefact (per the 2026-11-09 survey, preprocessing is the only brick that reads one
today). The file set for each is decided in its Stage 2 PR; fill in the first four columns then.
