# ADR 0003: `plane_histograms.csv` schema version 5 (semantic-wide, by canonical channel ID)

- **Status:** Accepted (owner decisions of 10 November 2026, items 1-3 of that day's batch, taken
  on the S3.1 benchmark). Specification only: it changes no fixture, golden or validator
  (`python -I tools/audit/refval.py fixtures .` unchanged) and implements nothing. The format text
  itself is brick-owned (below); the bricks change in Stage 3 (roadmap S3.2, S3.3).
- **Tracking:** [roadmap §5 Stage 3, S3.1](../roadmap.md#stage-3--coordinated-heterogeneous-channel-enablement);
  [conformance plan §4](../conformance-plan.md#4-later-stages-obligations-recorded-not-planned-in-detail)
  (Stage 3); [ADR 0001](0001-experiment-description-v1.md) (owner decision 12 and the section
  "Histogram representation: candidates and criteria only", which this ADR decides);
  [ADR 0002](0002-shared-request-resolver.md) AR10 (no backward compatibility); evidence:
  MorphoFeature `docs/restart/designs/s31-histogram-benchmark-2026-11-10.md` on branch
  `claude/restart-doc` (not in this repository).
- **Why a third ADR file, not rows in ADR 0001 or ADR 0002.** ADR 0001 rules on the experiment
  description v1 and only recorded the candidates and criteria for this table; ADR 0002 rules on
  the request resolver. This decision rules on a third thing: the **file format of a run
  artefact** that one brick writes (preprocessing, through the normalization brick's writer) and
  four read (normalization, preprocessing's `RunInputs`, CellPatcher, MorphoFeature), with its
  own schema version. By ADR 0002's convention (a decision on something other than the
  description gets its own file, numbered next), it is ADR 0003; ADR 0001 keeps a one-line
  pointer so its decision index stays complete. The decision table keeps ADR 0001's format.
- **Where the format text lives.** The Spec does not define this table: the normalization
  brick's contract (§6.1, §6.2, the column grammar) and preprocessing's contract (§5) do, and the
  normalization plan holds N41-N43. This ADR binds those texts; they are amended in the Stage 3
  pull requests that implement it. For that reason no Spec fixture is added: the Spec's fixtures
  are normative test data for `experiment-v1.md` (fixtures README), and this table is not part of
  it. The Stage 3 obligations (conformance §4) are shown on image trees built from the existing
  fixtures `v04`, `v05`, `v06`, `v13` and `v17`, as the benchmark did.

## Context

`plane_histograms.csv` schema version 4 addresses a channel by its C index in the image (N42:
`Histogram_Count_C<i>_<bin>`) and requires every image to have the same channel count (N43). That
is correct only for homogeneous layouts; with mixed layouts (Stage 3) the same index names
different biology (`v04`) or does not exist (`v05`, `v06`, `v17`). ADR 0001 named two candidates
(semantic-wide, one row per plane; long, one row per plane and channel) and the criteria; the S3.1
benchmark measured both with the real normalization brick (v0.3.4):

- both candidates pass every S3.1 correctness criterion: fits from either equal today's fits bit
  for bit on homogeneous data; both are byte-deterministic written twice, in four shuffled
  parallel shards and on resume; both keep per-plane identity, pool by biological repeat and
  canonical channel on `v04`/`v05`/`v06`/`v17`, encode presence explicitly and refuse every
  injected fabrication;
- they differ in shape, not in science. Wide keeps one row per plane (N41 kept; the row is the
  sampling unit for every existing consumer's plane index) and is within 1 % of today's size at
  the default 256 bins; long is +18-20 % uncompressed there, multiplies rows by the channel count
  (N41 reversed; any row count not regrouped is pseudoreplication) and is friendlier for ad-hoc
  pandas use;
- wide's costs: blank cells for absent channels (a naive pandas read can turn bin columns into
  text), a header that needs the experiment's channel IDs (every parallel shard must be given
  them), and an amended column grammar because a channel ID may contain `_` (N42).

The benchmark also listed sub-decisions (presence encoding, failed measurements, compatibility,
the scope of the N42 amendment). The owner decided on 10 November 2026 as recorded below.

## Decisions (owner, 10 November 2026; all accepted)

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| HV1 | **Schema version 5 is WIDE: one row per XYC plane**, columns by **canonical channel ID**, with **explicit presence columns**; **absent is not failed**. A channel the plane's imaging unit does not list is **absent**: its cells are blank, never a zero or NaN histogram, and a reader refuses any value there. The row stays the sampling unit: the row count is the plane count | (B) long, one row per plane and channel (N41 reversed, rows are not sampling units, +18-20 % at the default bins, IDs such as `NA` read as missing by default pandas); (C) long on disk, wide in memory (keeps B's size and N41 costs, two shapes to explain); (D) defer, keeping version 4 and N43 (Stage 3 cannot start; the `v05`/`v17` cases of G3 cannot be shown) | roadmap S3.1; conformance §4 Stage 3 "Histogram table v5" | trees built from `v13`, `v04`, `v05`, `v06`, `v17` |
| HV2 | **N41 is kept. N42's channel-token rule is amended** for this table: the per-channel token is the **canonical channel ID** instead of the C index (`Intensity_MinIntensity_DNA`, `Histogram_Count_DNA_00042`). Because a channel ID may contain `_` (`PAX_488`), column names no longer split on `_`: a reader takes the set of IDs from the parameter-less feature `Histogram_ValidPixelCount_<ID>` and the bin index from the last `_NNNNN`. N43 (every image has the same channel count) is replaced by the per-row presence of HV1 | Keeping the C-index token (one column names different biology on `v04`) | roadmap S3.1; normalization contract §6.1 (brick text, amended in S3.2) | the heterogeneous trees above; one tree with a channel ID containing `_` (no Spec fixture has one) |
| HV3 | **A failed channel measurement fails the whole file.** Nothing partial is written, and the run names the plane and the channel. The table therefore has no "failed" state: every channel a row lists as present carries a measured histogram (an empty histogram, a measured channel with no finite pixel, stays a measurement as today) | Writing the failure into the table (blank cells with a `failed_channels` list, as the benchmark's wide candidate did): a partial table every reader must filter, and a state new to the pipeline | roadmap S3.1; conformance §4 Stage 3 | an injected measurement failure on one channel of one plane |
| HV4 | **Version 4 is a hard cut.** A version 5 reader refuses a version 4 table, with a message that names schema version 5 and how to recompute it; there is **no converter** and no reader of both versions. This applies ADR 0002 AR10 (old versions are refused, never converted): the canonical IDs come from the confirmed description, not from the table | A converter from version 4 (it works only for homogeneous runs with a confirmed description, and a migration guesses what old data meant); a transition release reading both versions (two readers for a format nobody uses yet) | roadmap S3.1; conformance §4 Stage 3; ADR 0002 AR10 | a version 4 table given to a version 5 reader |

### Modelling choices made when writing these into the text (not themselves owner decisions; the owner may amend them)

These come from the benchmark's wide candidate (its §2.1), minus what HV3 removes:

- The 15 plane columns of version 4 stay, in the same order and meaning, with
  `schema_version` = `5` and `channel_count` = the number of channels of the source image.
- The presence column is `channels`: the canonical channel IDs of the source's C0, C1, … in source
  order (the imaging unit's confirmed `channels` list), `;`-separated (`;` cannot occur in a
  Token). The benchmark's second presence column, `failed_channels`, is **not** part of version 5:
  under HV3 it would always be blank.
- The per-channel column groups cover every channel ID of the experiment, from the description,
  in sorted order; every writer of a parallel shard is given that list, so shards share one header.
- Row order, number formatting, blanks for missing values, UTF-8, the atomic write and the row key
  `plane_id` are those of version 4.

### Not decided by this ADR

- **The token of the other per-channel tables** (the fitted parameters `Normalization_Offset_C<i>`
  and `Normalization_Scale_C<i>`, N46/N47, CellPatcher's patch columns, the image-summary columns):
  HV2 amends N42 for `plane_histograms.csv` only. Whether those tables also switch to the ID token
  is an open question for the owner (benchmark §5 and §8 item 5); until it is decided they keep
  N42 as written.
- How old installs word their refusal of a version 5 table (the benchmark's outline proposed a last
  normalization 0.3.x patch release naming version 5). HV4 binds the version 5 reader only.

## Consequences

- ADR 0001's "Histogram representation: candidates and criteria only (not decided)" is decided
  here: the semantic-wide candidate, with the failed state removed (HV3). ADR 0001 owner decision 12
  is fulfilled.
- Roadmap S3.1 becomes the record of this decision; S3.2 and S3.3 implement it (normalization's
  reader, writer, `PlaneRecord` by ID and fits by ID; preprocessing's staging and `RunInputs`;
  CellPatcher's and MorphoFeature's readers).
- Conformance plan §4 gains the Stage 3 row "Histogram table v5". It adds an obligation at Stage 3;
  it moves nothing from Stage 2 and does not change the closed list of the channel cases moved to
  G3 (GS2).
