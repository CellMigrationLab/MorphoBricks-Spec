# ADR 0003: `plane_histograms.csv` schema version 5 (semantic-wide, by canonical channel ID)

- **Status:** Accepted (owner decisions of 10 November 2026, items 1-3 of that day's batch, taken
  on the S3.1 benchmark, and the owner's answers of the same day on the points the benchmark left
  open). Specification only: it changes no fixture, golden or validator
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
| HV1 | **Schema version 5 is WIDE: one row per XYC plane**, columns by **canonical channel ID**, with **one explicit presence column, `channels`**, listing the canonical channel IDs present in that plane, `;`-separated; there is **no `failed_channels` column**; **absent is not failed**. A channel the plane's imaging unit does not list is **absent**: its cells are blank, never a zero or NaN histogram, and a reader refuses any value there. **The header lists every channel ID of the experiment, taken from the description, sorted.** The row stays the sampling unit: the row count is the plane count | (B) long, one row per plane and channel (N41 reversed, rows are not sampling units, +18-20 % at the default bins, IDs such as `NA` read as missing by default pandas); (C) long on disk, wide in memory (keeps B's size and N41 costs, two shapes to explain); (D) defer, keeping version 4 and N43 (Stage 3 cannot start; the `v05`/`v17` cases of G3 cannot be shown) | roadmap S3.1; conformance §4 Stage 3 "Histogram table v5" | trees built from `v13`, `v04`, `v05`, `v06`, `v17` |
| HV2 | **N41 is kept. N42's channel-token rule is amended, for ALL per-channel tables, not for this table only:** the per-channel token is the **canonical channel ID** instead of the C index. This covers `plane_histograms.csv` (`Intensity_MinIntensity_DNA`, `Histogram_Count_DNA_00042`), the fitted-parameter columns (`Normalization_Offset_C<i>` and `Normalization_Scale_C<i>`, N46/N47), CellPatcher's patch columns and the summary columns. The columns of the other tables change in the Stage 3 migration PRs (S3.2, S3.3), not in this ADR. Because a channel ID may contain `_` (`PAX_488`), column names no longer split on `_`: a reader takes the set of IDs from the parameter-less feature `Histogram_ValidPixelCount_<ID>` and the bin index from the last `_NNNNN`. N43 (every image has the same channel count) is replaced by the per-row presence of HV1 | Keeping the C-index token (one column names different biology on `v04`); switching the histogram table only and leaving the other per-channel tables on the C index (two naming rules for one run) | roadmap S3.1; normalization contract §6.1 (brick text, amended in S3.2) | the heterogeneous trees above; one tree with a channel ID containing `_` (no Spec fixture has one); the parameter, patch and summary columns on the same trees |
| HV3 | **A failed channel measurement fails the whole file, meaning `plane_histograms.csv` only:** that table is not written, and the run reports the plane and the channel that failed. The other outputs of the run follow their own rules; this row does not change them. The table therefore has no "failed" state: every channel a row lists as present carries a measured histogram (an empty histogram, a measured channel with no finite pixel, stays a measurement as today) | Writing the failure into the table (blank cells with a `failed_channels` column, as the benchmark's wide candidate did): a partial table every reader must filter, and a state new to the pipeline (the owner also decided against a `failed_channels` column) | roadmap S3.1; conformance §4 Stage 3 | an injected measurement failure on one channel of one plane (no `plane_histograms.csv`; the failing plane and channel are reported) |
| HV4 | **Version 4 is a hard cut.** A version 5 reader refuses a version 4 table, with a message that names schema version 5 and how to recompute it; there is **no converter** and no reader of both versions. This applies ADR 0002 AR10 (old versions are refused, never converted): the canonical IDs come from the confirmed description, not from the table | A converter from version 4 (it works only for homogeneous runs with a confirmed description, and a migration guesses what old data meant); a transition release reading both versions (two readers for a format nobody uses yet) | roadmap S3.1; conformance §4 Stage 3; ADR 0002 AR10 | a version 4 table given to a version 5 reader |

### Details written into the text (not owner decisions; ordinary format detail)

- The 15 plane columns of version 4 stay, in the same order and meaning, with
  `schema_version` = `5` and `channel_count` = the number of channels of the source image.
- Within the `channels` cell the IDs follow the source order of the imaging unit's confirmed
  `channels` list. `;` separates them (`;` cannot occur in a Token).
- Every writer of a parallel shard is given the experiment's channel-ID list, so shards share one
  header.
- Row order, number formatting, blanks for missing values, UTF-8, the atomic write and the row key
  `plane_id` are those of version 4.

### Not a Spec decision

How old installs word their refusal of a version 5 file is an implementation detail. The benchmark
proposed a last normalization 0.3.x patch release naming version 5; it is a note in the roadmap
(S3.2), not a row here. HV4 binds the version 5 reader only.

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
