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
| morphobricks-preprocessing | [`1bed024`](https://github.com/CellMigrationLab/MorphoBricks-Spec/commit/1bed024e278d104ba4b8f63ae76c020fb2e3470d) | 2026-11-09 | [preprocessing #242](https://github.com/CellMigrationLab/morphobricks-preprocessing/pull/242) | Standard |
| morphobricks-normalization | not pinned; pinned with its Stage 2 PR | | | canonical-channel / canonical-ID pooling (Stage 2-3) |
| MorphoFeature | not pinned; pinned with its Stage 2 PR | | | P24 `rgb_support` in provider manifests, P25 `repeat_group` to MorphoCoverage, P27 `binary_mask_policy` |
| fiberfeatures | not pinned; pinned with its Stage 2 PR | | | P24, canonical-channel adapter |
| MorphoCoverage | not pinned; pinned with its Stage 2 PR | | | P31 `target` prefill, P25, MC4/S2.5 |
| MorphoRelate | not pinned; pinned with its Stage 2 PR | | | canonical-channel adapter |
| MorphoObjects | not pinned; pinned with its Stage 2 PR | | | P27 (`A_MASK_NOT_INSTANCES`) |
| MorphoEmbed | not pinned; pinned with its Stage 2 PR | | | P24, P27 (has a `provider_manifest` module) |
| CellPatcher | not pinned yet: draft [CellPatcher #97](https://github.com/CellMigrationLab/CellPatcher/pull/97) vendors [`6d22761`](https://github.com/CellMigrationLab/MorphoBricks-Spec/commit/6d2276128ddb050fcd54de53b46d6a293c5fe135) | draft PR, pin to v0.5.0 at merge | [CellPatcher #97](https://github.com/CellMigrationLab/CellPatcher/pull/97) (draft, not merged; at merge its preprocessing pin moves to v0.5.0, and this row gets the merged Spec commit and date) | Standard (P32 `condition_id`/`technical_repeat_id` and P25 tests; P27 later) |

For the unpinned bricks the last column is the Stage 2 item that will make the brick read a
Spec-defined artefact (per the 2026-11-09 survey, preprocessing is the only brick that reads one
today). The file set for each is decided in its Stage 2 PR; fill in the first four columns then.
