# MorphoBricks master roadmap

Status: 5 November 2026 (owner-approved plan; owner priorities of the same day); release status refreshed 7 November 2026 from the brick tags on GitHub (the work items below are as written on 5 November). This page orders
the work across all ten repositories and links out. It copies nothing: the live state lives in
each repo's own roadmap and in the [restart notes][restart]. Nothing here is a claim that an item is
implemented or tested. Sizes are rough: S = one small PR, M = 2-4 PRs, L = 5+ PRs.

## Overview

1. **Release first.** normalization v0.3.4, preprocessing v0.4.0, CellPatcher v0.2.0, MorphoObjects v0.1.0, MorphoEmbed v0.1.0 and fiberfeatures v0.2.1 are tagged (checked 7 November 2026).
2. **Then:** repins, MorphoFeature rows 39-43, fiberfeatures rows 44-45, the full pinned gate, the brick tags.
3. **Mixed data next:** a recorded channel-subset copy (via `convert`) so the owner's datasets with EXTRA channels can run. It is not Stage 3.
4. **Spec:** Stage 0 (decisions, M0) -> Stage 1 -> Stage 2 -> Stage 3 (mixed layouts) -> Stage 4. Stage 0 is docs only.
5. **In parallel, one slot each:** bug batches, Z clean-up, code speed, CI fast lanes, MorphoCoverage (own session).
6. **Later:** projection step P1, 3-D (#157), quality checks Q1/Q2.
7. **Constraints:** at most 2 agents at a time; weekly credit is about 93%, so start no new agents beyond the in-flight ones until it resets.
8. **Core freeze:** normalization, preprocessing and CellPatcher change only for release work until the final brick tags.
9. **Science rules apply to every item:** no guessed axes/channels/calibration, no silent fill, no implicit CPU/GPU fallback, no invented data.
10. Items marked **DECISION** need the owner; the list is in the last section.

Related: the staged spec plan is [docs/roadmap.md](roadmap.md) (Stages 0-4, gates G0-G4, ownership matrix, acceptance tests); this page sequences it against everything else.

## Track 1: Release (first priority)

| # | Repos | Goal | Depends on | Size | Source |
|---|---|---|---|---|---|
| R0 | normalization, preprocessing | v0.3.4 and v0.4.0 tagged. Done. | - | done | [RESTART NOW][restart] |
| R1 | CellPatcher | Row 38 merged (#84 `ee196e2`). v0.2.0 release PR (pins v0.3.4 and v0.4.0, converts Z>1 tests per #83 list), then the owner tags. #31 closes with the tag. **Done: `v0.2.0` is tagged (checked 7 November 2026).** | R0 | S | [#31](https://github.com/CellMigrationLab/CellPatcher/issues/31); [blocker 38][restart] |
| R2 | MorphoFeature | "Batch 8": rows 39 (`--to-segment` no-clobber), 40 (release gate exact tree), 41 (skips fatal in release mode), 42 (`brick_cache` symlinks/outcome). Row 42 is delicate: Opus review. | - (can start now) | M | [blocker tracker][restart] |
| R3 | fiberfeatures | Row 44: valid non-square pixels (Y=0.5, X=0.25 um) accepted; patches square in pixels. Opus. | - | M | [blocker 44][restart] |
| R4 | all bricks | Repins to the final tags, including row 43 (MorphoFeature and MorphoRelate tests that build fresh Z>1 runs) and the Z>1 test conversions; MorphoFeature adopts `write_target_refusal`, bumps notebook pin and `RELEASE_TAG`, simplifies the CUDA cache thread identity (`ENTRY_FORMAT` bump). | R1 | M | [RESTART item 4][restart]; [MF roadmap](https://github.com/CellMigrationLab/MorphoFeature/blob/main/docs/roadmap.md) |
| R5 | fiberfeatures | Row 45 with row 26: regenerate `data/experiment_001/reference` in the final pinned environment; record full SHAs of normalization, preprocessing, CellPatcher. | R4 | S | [blocker 45, 26][restart] |
| R6 | MorphoFeature | R-bucket: #48 (enforced real-provider gate, record the tested set in `docs/install.md`), #140 (frozen-manifest test must catch drift). | R4 | M | [triage R items][triage] |
| R7 | all | Full pinned gate (CI or local gate green on exact heads; short matrix subset A2, P2, H, T, F bitwise equal to the stable point), then the brick tags. Tags are published by the owner. | R2-R6 | M | [RESTART items 5-6][restart] |

As written on 5 November: MorphoObjects `ba3f6d7`, MorphoEmbed `422cc01`, preprocessing and normalization were tag-ready at batch 8; MorphoFeature (R2), MorphoRelate (row 43), fiberfeatures (R3, R5) and CellPatcher (R1) were not. Since then the tags above exist, plus MorphoFeature `v0.1.0` and MorphoRelate `v0.1.1`; whether R2 to R6 were completed is not re-verified here.
**DECISION:** refuse run folders from EARLIER release candidates that recorded Z>1? (recommended: no).

## Track 2: Mixed data (right after the release)

The owner's datasets share the core channels, but some images have EXTRA channels. Spec Stage 3 solves this properly (extra channels analysable). This track is the near-term shortcut: a **recorded channel-subset harmonised copy**. Every image is reduced to the common channel set, what was dropped is recorded, originals are untouched, nothing is invented. Extra channels become analysable only after Stage 3.

| # | Repos | Goal | Depends on | Size | Source |
|---|---|---|---|---|---|
| MD1 | owner | Confirm: extra channels only (not order or missing channels), and which are the core channels per dataset. **DECISION** | - | S | [RESTART NOW][restart] |
| MD2 | preprocessing | Channel-selection statement: the user states, per image group, which source C indices become which named channels; checked against header names (evidence only). New `convert --channels` option and the same in the notebook. | R7 | M | finding below |
| MD3 | preprocessing | Writer and record: write only the selected planes, in the stated order; `CopyEntry` records the dropped channels (index, header name) and the selection; reuse check compares the selection. Every image with extra channels is rewritten (none is byte-copied). | MD2 | M | finding below |
| MD4 | preprocessing | Run on the copy tree gives one channel set, so existing gates (`different_channel_counts`, `channel_names_differ`) pass honestly. Tests: extra channel at the end, in the middle, order swap, header-name contradiction refused. | MD3 | S | finding below |

**Finding (checked on preprocessing `a786290`, tag v0.4.0 line):**
- **`convert` cannot subset channels today.** It rewrites axis roles only: options are `--axes`, `--exclude`, `--missing-as-singleton` (`cli_convert.py:55-90`). `--exclude` leaves an image unread and copies it byte for byte, so it removes nothing from the copy tree. `copy_layout` carries all channels (`copy_axes.py:145`); `write_named_copy` writes every plane (`ome_tiff_copy.py:75`).
- **It refuses mixed channel counts before writing anything.** `plan_conversion` stops on any error that is not an axis error (`conversion_plan.py:131-132`); `different_channel_counts` (`size_checks.py:86`, raised from `metadata.py:665-668`) and `channel_names_differ` (`metadata.py:596-611`) both are such errors. Its own hint is "split into a separate experiment, or exclude them".
- **Discovery has no channel selection either:** the refusal is experiment-global ("every image must have the same channels").
- **Missing for the shortcut:** the selection statement and CLI/notebook option (MD2); a subset-aware layout and writer, plus `CopyEntry` fields and `same_plan` (`conversion_record.py:55,106`) (MD3); the consistency checks evaluated after selection, not before (MD4); a rule that images with named axes but extra channels are rewritten, not byte-copied (`_copied`, `conversion_plan.py:184`).
- **Effort: M, about 3-4 PRs in preprocessing only, no brick change.** It reuses the copy machinery, record, locking and reuse logic. It needs a patch release (v0.4.1) after the repin, so it waits for R7. Uncertainty: if the core channels sit at different positions per image group, the statement must be per group (more UI, still M); order-only differences are fixed by the same statement.
- **Relation to the spec:** a stopgap that produces homogeneous data, which today's contracts already process. It is NOT Stage 3: it drops channels, keeps no per-unit layout and adds no schema. It does not conflict with Stage 1+; the copy record is provenance, and later runs on the originals can use all channels. The spec calls the harmonised copy optional (RFC #1 M14; [roadmap §9](roadmap.md)).

## Track 3: Spec (RFC #1)

Detail, gates and acceptance tests: [docs/roadmap.md](roadmap.md) §5, [feasibility audit](audits/rfc1-feasibility-2026-11-05.md), [addendum](audits/rfc1-feasibility-2026-11-05.md#addendum-after-chatgpts-response-5-november-2026) (the addendum wins), [RFC #1](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1). Total estimated about 20-25 PRs across 6 repos, including one breaking normalization table change.

| # | Repos | Goal | Depends on | Size | Source |
|---|---|---|---|---|---|
| S0 | spec | Stage 0: record the 10 owner decisions (TOML, mask fields, canonical repeat IDs, histogram benchmark criteria...), then write `experiment-v1.md`, fixtures (RFC's 12 plus 10 adversarial tests). Docs only; may run during the release. **DECISION** | owner | M | [roadmap §5 S0.1-S0.3](roadmap.md); [addendum §4](audits/rfc1-feasibility-2026-11-05.md#addendum-after-chatgpts-response-5-november-2026) |
| S1 | preprocessing | Stage 1 (v0.5): discover, preview, confirm and reconcile the schema; semantic `RunInputs`; derived `experiment_design.csv`; heterogeneous runs explicitly refused. Gate G1. | S0, R7 | L | [roadmap S1](roadmap.md) |
| S2 | MorphoFeature, MorphoRelate, fiberfeatures, MorphoObjects, MorphoEmbed, MorphoCoverage, CellPatcher | Stage 2: adapters read canonical channels and repeat IDs. Gate G2. | S1 | L | [roadmap S2](roadmap.md) |
| S3 | preprocessing, normalization, CellPatcher | Stage 3: mixed layouts enabled together; histogram benchmark (semantic-wide vs long); canonical-channel pooling; adversarial suite. Gate G3. | S2 | L | [roadmap S3](roadmap.md) |
| S4 | all | Stage 4: mask semantics, progressive segmentation, end-to-end regression, migration guide. Gate G4. | S3 | L | [roadmap S4](roadmap.md) |

Note: the shortcut (MD) may let the owner process mixed data before S3; S1-S3 do not wait for it.

## Track 4: Bugs (batched, in parallel)

Source: [triage 2026-11-05][triage] (396 open issues: R 3, A 64, M 121, P 198, X 10) and [brick triage 2026-11-03](https://github.com/CellMigrationLab/MorphoFeature/blob/claude/restart-doc/docs/restart/triage-bricks-2026-11-03.md). **DECISION:** the owner has not decided the buckets; the groupings below are proposals. Rule: 2-4 related issues per PR, one commit per issue, regression test each, full gate once per PR; delicate science gets its own PR and Opus review.

| # | Repos | Goal (candidate batch) | Depends on | Size |
|---|---|---|---|---|
| B1 | MorphoFeature | A-bucket batch: #145, #139, #138, #137 (identity, provenance, load integrity) | bucket decision | S-M |
| B2 | MorphoEmbed | Model identity gate: #22 and #19 (record verification binds device and torch version) | bucket decision | S |
| B3 | fiberfeatures | A-bucket (12 issues; patch identity, FOV key scoping, label identity, overwrites) in about 4 PRs | R3, R5 | M-L |
| B4 | MorphoRelate | #197 (settings vs Z/T policy; depends on [CellPatcher #30](https://github.com/CellMigrationLab/CellPatcher/issues/30)), then the A/M items | R4 | S-M |
| B5 | normalization | A-bucket (11): extreme-value numerics #27/#28/#32/#33, #67, QC pseudoreplication #21/#22 | after final tags (core) | M |
| B6 | preprocessing | A-bucket (5), e.g. #154 (consumers check tags, not SHAs) | after final tags (core) | S-M |
| B7 | CellPatcher | #46 (verify, then close), #26 (FOV status export) | after final tags (core) | S |
| B8 | all | M-bucket (121) and P-bucket (198) per the owner's buckets; X-bucket (10 proposed closures, nothing closed yet) | audit passes | L |

## Track 5: Z clean-up (2-D only v1, post-release)

Owner decision 5 Nov 2026: v1 analyses 2-D only; 3-D is [MorphoFeature #157](https://github.com/CellMigrationLab/MorphoFeature/issues/157). Keep `z` in identities and cache keys (always 0).

| # | Repos | Goal | Depends on | Size | Source |
|---|---|---|---|---|---|
| Z1 | CellPatcher | Z plane policies become dead code (keep T): one guard refusing Z>1, remove the Z projection path and the stale `shared` code (`run_reading.py:152`); Z>1 tests are converted at the repin | R1 | S | [#83](https://github.com/CellMigrationLab/CellPatcher/issues/83) |
| Z2 | MorphoFeature | One guard refusing Z>1 at the input boundary; keep Z loops (run once); convert `test_cellpatcher_file_run_parity.py:45,62` | R4 | S | [MF roadmap, Z-stack clean-up](https://github.com/CellMigrationLab/MorphoFeature/blob/main/docs/roadmap.md) |
| Z3 | MorphoRelate | `patch_planes.py`: the Z branch of rules from rows 33-34 collapses to "Z=1 or refuse"; T branch stays | R4 | S | [MorphoRelate roadmap](https://github.com/CellMigrationLab/MorphoRelate/blob/main/docs/roadmap.md) |
| Z4 | fiberfeatures | Stale "stated shared 2-D mask" wording in `run_reading.py` | R5 | S | [#145](https://github.com/CellMigrationLab/fiberfeatures/issues/145) |

One bounded PR each; Z1-Z4 can be one slot, done in series. Not a blocker for tags.

## Track 6: Speed

Rule: identical scientific outputs, benchmark before and after, no performance claim without it ([CLAUDE.md](https://github.com/CellMigrationLab/MorphoFeature/blob/main/CLAUDE.md)). Guided by the [timing audit][ci]: the slowest 5% of tests hold 47-90% of test time; real code bottlenecks are I/O, scheduling, serialization and cache validity more than kernels. Test speed is tracks 7/CI; this track is code speed.

| # | Repos | Goal | Depends on | Size | Source |
|---|---|---|---|---|---|
| P1 | MorphoFeature | I/O and scheduling: #35 bounded scheduling, #36 select T/Z before decoding, #39 reuse decoded FOVs, #49 pool sizing, #30 tables once per `write_run` | R7, benchmark first | M | [MF roadmap, Priority 1](https://github.com/CellMigrationLab/MorphoFeature/blob/main/docs/roadmap.md) |
| P2 | MorphoFeature | #33: single-pass Numba `object_sides()` (strongest core candidate) | benchmark first | S | [#33](https://github.com/CellMigrationLab/MorphoFeature/issues/33) |
| P3 | fiberfeatures | Per-worker FOV execution and memory: #96, #107, #102, #101 | R5 | M | issues list |
| P4 | MorphoObjects | MO4: measured FOV throughput, targeted Numba | tag | M | [ROADMAP MO4](https://github.com/CellMigrationLab/MorphoObjects/blob/main/ROADMAP.md) |
| P5 | normalization | #60 benchmarks first, then #34 pooling, #49 CSV I/O, #40 | after tags (core) | M | [#60](https://github.com/CellMigrationLab/morphobricks-normalization/issues/60) |
| P6 | MorphoCoverage | `report()` 96 s on 4 fields: profile (#601) | its session | S | [#601](https://github.com/CellMigrationLab/MorphoCoverage/issues/601) |

## Track 7: CI fast lanes

Source and order: [CI and timing audit][ci] ("Recommended order"). Billing is not fixed, so private repos merge on the local gate (`python tools/check.py`); heavy lanes run weekly and at tags. Only 5 of 9 repos have a workflow on main.

| # | Repos | Goal | Depends on | Size |
|---|---|---|---|---|
| C0 | owner | Billing and budget alert, read-only token for private repos, branch protection on one `ci-ok` check, branch auto-delete, CellPatcher release run #7, heavy-lane cadence. **DECISION** | - | owner |
| C1 | MorphoObjects, MorphoEmbed | New `ci.yml`, whole suite as fast lane (MorphoObjects 24 s); the template for the rest | - | S each |
| C2 | MorphoFeature | Fast lane without providers; provider lane with `check.py --release` once the token exists (#48) | C0, R6 | S-M |
| C3 | fiberfeatures | Tidy: thread limits (`-n auto` is slower than serial until `OMP_NUM_THREADS=1`), `check.py --fast` | C1 | S |
| C4 | MorphoRelate | Isolate `test_part_c_declares_pyarrow...` first, `heavy` marker, then workflow (29 min serial to a few minutes) | C0 token | S-M |
| C5 | normalization, preprocessing, CellPatcher | Fast and full lanes; update `tests/test_ci_workflow.py` in CellPatcher | final tags (core) | S each |
| C6 | all | Switch branch protection to `ci-ok`, one repo at a time, after 10 green runs | C1-C5 | owner |

## Track 8: MorphoCoverage (own session, after the release)

225 open issues (triage: A 27, M 97, P 101). Dedicated session: its accumulated issues, optimisation, a fast test lane (no `tools/check.py` yet, `heavy` marker, main-push unit lane, weekly full lane).

| # | Goal | Depends on | Size | Source |
|---|---|---|---|---|
| MC1 | A-bucket: typed-identity and silent-loss defects (e.g. #576, #541, #540, #539, #537, #499, #494, #484, #478) in batches of 2-4 | R7 | L | [triage A][triage] |
| MC2 | #603 step C (read applicability; then non-measured values stop being NaN with state) and #604 (multi-plane exports refused) | R4 | M | [#603](https://github.com/CellMigrationLab/MorphoCoverage/issues/603) |
| MC3 | CI lane (C-track) and profiling (P6) | C0 | M | [CI audit][ci] |
| MC4 | Spec S2.5: prefill canonical repeats and reference chains | S1 | M | [roadmap S2.5](roadmap.md) |

## Track 9: Future (after the above)

| # | Repos | Goal | Depends on | Size | Source |
|---|---|---|---|---|---|
| F1 | preprocessing | P1 explicit projection step: `max`/`mean`/`sum` or one stated slice, no default; new 2-D images; manifest records method and source SHA-256; 3-D masks refused | Z1-Z4; DECISION on timing | M | [preprocessing roadmap P1](https://github.com/CellMigrationLab/morphobricks-preprocessing/blob/main/docs/roadmap.md) |
| F2 | preprocessing, MorphoEmbed, MorphoObjects | Q1 whole-FOV embedding outliers, Q2 quick mask check; flag only, each brick registers its check via entry points | F1 not needed; needs migrated bricks | M each | [preprocessing roadmap Q1/Q2](https://github.com/CellMigrationLab/morphobricks-preprocessing/blob/main/docs/roadmap.md) |
| F3 | all | 3-D volume route beside the plane route: needs check first, Z calibration mandatory, MorphoObjects first | F1, own decision | L | [#157](https://github.com/CellMigrationLab/MorphoFeature/issues/157) |
| F4 | MorphoFeature, MorphoCoverage | LIVE projection and restart/idempotence, causal normalization | releases | L | [MF #4](https://github.com/CellMigrationLab/MorphoFeature/issues/4); [MorphoCoverage #607](https://github.com/CellMigrationLab/MorphoCoverage/issues/607) |
| F5 | MorphoObjects, MorphoEmbed, fiberfeatures | Native intensity additions, MO3-B/C/D, T4 microscopy benchmarks, fibre pixel categories | releases | L | [MorphoObjects ROADMAP](https://github.com/CellMigrationLab/MorphoObjects/blob/main/ROADMAP.md); [MorphoEmbed ROADMAP](https://github.com/CellMigrationLab/MorphoEmbed/blob/main/ROADMAP.md); [fiberfeatures #128](https://github.com/CellMigrationLab/fiberfeatures/issues/128) |

## Dependency sequence

```
R0 (tags done) -> R1 CellPatcher v0.2.0 ---------+
R2 MF batch 8 (rows 39-42) --------------------+  |
R3 fiberfeatures row 44 ----------------------+ |  |
                                              v v  v
                                  R4 repins (incl. row 43, Z>1 tests)
                                              |
                          R5 fiberfeatures reference, R6 #48 / #140
                                              |
                      R7 full pinned gate -> brick tags  (RELEASE)
                                              |
      +----------------+----------------------+----------------+-------------+
      v                v                      v                v             v
  MD2-MD4 shortcut   S1 (needs S0)   Z1-Z4 clean-up      core bug batches   CI C5
  (preprocessing     -> S2 -> S3     (after repins)      B5-B7, speed P5    (core CI)
   v0.4.1)           -> S4
      |
      v
  owner processes mixed data (extra channels dropped, recorded)

Parallel from now (no release dependency): S0 (docs only), brick bug batches B1-B2 (once
buckets are decided), CI C1-C4, speed P1-P3 (benchmarks first), MorphoCoverage session (after R7).
Later: F1 projection -> F3 3-D; F2 quality checks.
```

What blocks what: R4 waits for R1; R7 waits for R2-R6; the shortcut and S1 both change preprocessing and wait for R7 (a core freeze until the final tags); S3 needs S2 (normalization, preprocessing and CellPatcher migrate together); F3 needs the projection and its own needs check.

## Next 5 actions

1. **CellPatcher v0.2.0 release PR** (Sonnet): pins normalization v0.3.4 and preprocessing v0.4.0, Z>1 test conversions, CHANGELOG, notebooks. The coordinator checks it; the owner tags (prefilled link in RESTART).
2. **MorphoFeature batch 8** (rows 39-42, Sonnet; Opus review of row 42), one commit per row, regression tests.
3. **fiberfeatures row 44** (Opus): per-axis pixel spacing, patches square in pixels.
4. **Owner decisions** (can be answered in one sitting): triage buckets, the 10 Stage-0 decisions, mixed-data scope (MD1), the earlier-rc Z>1 question, CI billing and token (see below).
5. **Prepare MD2:** open the preprocessing issue "channel-subset harmonised copy" with this page's finding (file:line evidence), so the work can start the moment R7 passes. In parallel, start S0 docs (no code, no freeze conflict).

## Decisions needed from the owner

- Triage buckets R/A/M/P/X for the 396 issues, and the 10 proposed closures ([triage][triage]).
- Stage-0 spec decisions: TOML (`morphobricks.toml`), canonical repeat IDs, mask `representation`, histogram benchmark criteria, N35 and compatibility ([roadmap §2](roadmap.md)).
- Mixed data (MD1): extra channels only? Which channels are "core" per dataset? OK to drop the others in a recorded copy?
- Refuse run folders from earlier release candidates that recorded Z>1 (recommended: no).
- When the projection step P1 and the Q1/Q2 checks are placed relative to Stage 1.
- CI owner actions (C0): billing and budget alert, read-only token, `ci-ok` required check, branch auto-delete, CellPatcher release run #7, MorphoEmbed weights lane (26 skipped tests run nowhere).
- Whether MorphoFeature also offers the Q1/Q2 checks as a "quick QC" preset; default Q1 model and time budget.

## Caveats

- Per-repo state (PR numbers, SHAs) goes stale fast: verify on GitHub before acting. CellPatcher's v0.2.0 release branch was not yet on origin when this page was written.
- Issue lists for CellPatcher, fiberfeatures, normalization and MorphoCoverage were read as titles only; MorphoCoverage (225 issues) is summarised from the triage, not re-read.
- The triage and CI audit are proposals and measurements from 5 November (Python 3.12, 4 vCPU); they are not decisions.

[restart]: https://github.com/CellMigrationLab/MorphoFeature/blob/ff19de8938d5ed8c4143cff563715551ee874a05/docs/restart/RESTART.md
[triage]: https://github.com/CellMigrationLab/MorphoFeature/blob/ff19de8938d5ed8c4143cff563715551ee874a05/docs/restart/triage-2026-11-05.md
[ci]: https://github.com/CellMigrationLab/MorphoFeature/blob/ff19de8938d5ed8c4143cff563715551ee874a05/docs/restart/archive/ci-and-timing-audit-2026-11-05.md
