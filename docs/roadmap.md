# MorphoBricks experiment metadata — implementation roadmap

**Status:** Proposed architecture and staged implementation plan, 5 November 2026. No implementation or runtime verification is implied by this document.  
**Tracking:** [RFC #1](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1); [Claude feasibility audit](audits/rfc1-feasibility-2026-11-05.md); [Claude addendum](audits/rfc1-addendum-2026-11-05.md).  
**Release policy:** Documentation/specification work may proceed now; changes to existing bricks are deferred until after their first release tags. No part of this initiative is a blocker for those tags.

## 1. Objective and non-goals

Preprocessing discovers the actual dataset, asks the user to confirm experiment semantics once, writes a strict versioned experiment description, and exposes validated semantic identities to downstream bricks. A user must be able to start from an image folder without manually preparing metadata.

The experiment description captures **conditions, canonical channels, biological-repeat pairing, technical-repeat acquisition layouts and mask semantics**. It does not contain file inventory, calibration duplicates, FOV exclusions, processing recipes, feature requests, provider routing, normalization methods, statistical contrasts, FDR families, or Optuna settings.

Keep the spec repository lightweight: normative documents, fixtures, conformance tests and compatibility decisions. Do not introduce a separately versioned runtime package in Stage 0. Preprocessing is the initial reference reader and validator; downstream bricks use a validated RunInputs contract rather than independently parsing the file.

## 2. Decisions to freeze before implementation

| Decision | Proposed resolution | Verification / open question | Status |
|---|---|---|---|
| Format | **TOML** (`morphobricks.toml`) with strict parser and semantic validator | Owner confirmation; duplicate keys, implicit conversions and unknown fields must refuse | **Accepted** 2026-11-06 ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Biological-repeat identity | Canonical, stable, user-confirmed ID; for trivial same-name pairing default to existing source folder name | IDs are immutable once confirmed (no renames); friendly names are `display_name`; a mistyped ID is fixed only by a recorded re-confirmation | **Accepted** 2026-11-06, refined (ADR D5) ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Imaging unit | `condition × source biological repeat × technical repeat` | Each unit has one ordered canonical channel list; FOVs in a unit must conform | Accepted with scope ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Heterogeneity | Supported in **normative v1** across imaging units | Stage 1 runtime may refuse until Stage 3 coordinated enablement | **Accepted** 2026-11-06, scope ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Channel names | Stable canonical token plus optional display label and confirmed header evidence | Header name and canonical token need not be identical; never infer from pixels | **Accepted** 2026-11-06, aliases ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Masks | Confirm `instances` vs `binary`; retain source type and optional source-channel provenance | Drop redundant `axes`/`shared` under merged 2-D-only preprocessing contract; revisit if scope changes | **Accepted** 2026-11-06, scope ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Calibration | Remains in authoritative `calibration.csv` | Do not copy into experiment metadata | Accepted earlier, kept ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Compatibility | Keep `experiment_design.csv` as a derived compatibility output | Define deterministic export and migration behavior | Accepted earlier, kept ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Comparability | Preserve N35 user confirmation | Reopen only when channels, layout or grouping change; new FOVs with the same confirmed layout do not reopen it (ADR D6); log decision provenance | Accepted earlier, kept ([ADR 0001](adr/0001-experiment-description-v1.md)) |
| Histogram representation | Benchmark semantic-wide (preferred candidate) versus long/channel-keyed | Freeze only after legacy parity, pooling, missingness and pseudoreplication tests | Deferred to benchmark; candidates and criteria in [ADR 0001](adr/0001-experiment-description-v1.md) |
| Statistical references | Optional primary `condition.reference` edge; graph acyclic | Additional contrasts belong to MorphoCoverage | **Accepted** 2026-11-06, scope ([ADR 0001](adr/0001-experiment-description-v1.md)) |

**Stage 0 outcome (6 November 2026):** field spelling, header-alias representation (`header_names`) and the error catalogue are now normative in [experiment-v1.md](experiment-v1.md), with [fixtures](../fixtures/README.md) and a [conformance plan](conformance-plan.md). Per-mask applicability is an analysis-layer check (`A_*` codes). The eleven open questions of the Stage 0 pull request were decided on 6 November 2026 (ADR 0001, D1-D11). **Still open:** the physical histogram schema (benchmark); the fixed-SHA consumer audit of S0.1 (TODO before Gate G0); golden `experiment_design.csv` outputs (deferred to Stage 1).

## 3. Minimal conceptual schema

The following TOML is an **illustrative candidate**, not an implemented schema. It is superseded by the normative [experiment-v1.md](experiment-v1.md) (e.g. repeats now carry `confirmed`, `confirmed_on` and per-member `image_count`):

```toml
schema = "morphobricks-experiment"
schema_version = 1

[conditions.CTRL]
display_name = "Control"

[conditions.DrugA]
display_name = "Drug A"
reference = "CTRL"
target = "SRC"
treatment_key = "saracatinib"

[channels.DNA]
display_name = "DAPI"

[channels.ACTIN]
display_name = "F-actin"

[channels.PHASE]
display_name = "Phase contrast"

[repeats.Day1.members.CTRL]
source_repeat = "rep1"

[repeats.Day1.members.CTRL.technical_repeats.acquisition_1]
channels = ["DNA", "ACTIN", "PHASE"]

[repeats.Day1.members.CTRL.technical_repeats.acquisition_2]
channels = ["ACTIN", "DNA"]

[repeats.Day1.members.DrugA]
source_repeat = "experiment_23"

[repeats.Day1.members.DrugA.technical_repeats.single]
channels = ["ACTIN", "DNA"]

[masks.Nuclei]
source_type = "nuclei"
representation = "instances"
source_channels = ["DNA"]

[masks.TumorRegion]
source_type = "tumor_region"
representation = "binary"
```

**Interpretation:** each ordered `channels` list maps source C0, C1, … to canonical semantic IDs. `Day1` is the biological-repeat ID exported downstream, even though the source folders are `rep1` and `experiment_23`. The two CTRL technical repeats belong to **one** biological replicate. Their different channel sets are legitimate and must not create additional biological replicates.

Source repeat/technical-repeat labels are exact provenance and must not be parsed for biological meaning. A missing physical technical-repeat level uses the already-established `single` convention. A canonical ID must be immutable across reconciliation unless the user explicitly approves a recorded identity migration.

## 4. Non-negotiable scientific contracts

### 4.1 Acquisition homogeneity and detectability

- All included FOVs inside one technical-repeat imaging unit must have compatible interpreted axes and the same source channel count and ordered confirmed canonical mapping.
- Different imaging units may have different channel counts/order; no global index interpretation.
- A structural/header contradiction blocks the affected unit with exact FOV/path/C-index evidence. No per-FOV channel override in v1.
- **Limit of validation:** identical-shape, unnamed images with physically swapped fluorophores cannot be reliably detected from headers. Representative preview and explicit human confirmation are required; optional image-based anomaly checks are advisory, not proof of identity.
- Compatible axes means semantics/order, **not** identical numbers of T planes. The merged preprocessing release's Z/mask limitations remain authoritative until explicitly changed.

### 4.2 Identity and replication

- Canonical `biological_repeat` is the statistical unit/group identity. Technical repeats are subsamples, not independent biological replicates.
- Use existing folder names as default canonical IDs when unambiguous to minimize identity/cache churn. Pair differently named repeats through explicit user confirmation.
- Never auto-renumber IDs, silently pair renamed folders, reuse IDs for a different biological unit, or collapse distinct biological repeats.
- Preserve original folder labels, source path, position_id and technical-repeat identity in run provenance.
- Reconcile renamed/moved folders explicitly, using available file evidence; do not infer equivalence solely from a matching name.

### 4.3 Channel applicability and partial biological repeats

For each requested canonical channel/object set and requested analysis scope, classify every imaging unit as **present**, **absent**, or **unresolved/conflicting**. At the biological-repeat level distinguish **fully represented**, **partially represented**, and **unavailable**. Record this in the run manifest and user-facing preflight.

Default behavior: refuse incomplete requested scope. An explicit user-selected eligible subset may proceed only with recorded scope and coverage; do not silently exclude FOVs, change weights, impute missing channels, or turn technical-repeat count into biological N.

Pooling, fitted normalization, CellPatcher exports, MorphoFeature features, MorphoEmbed scaling and MorphoCoverage statistics must use **canonical channel identity** and correct biological/FOV grouping, never source C index alone.

### 4.4 Mask semantics and progressive segmentation

- Confirm instance labels vs binary regions. Do not infer semantic representation or scientific role from dtype, file names or nonzero pixels.
- `source_channels` is optional provenance, not a restriction on measurement channels.
- File-level axes, pairing, masks present/absent, fingerprints and completeness remain authoritative in discovery/run manifest.
- A binary region cannot silently become a labelled object set. Brick-specific roles such as nucleus/cell/region belong to analysis requests.
- Preserve resumable mask scanning, change-during-scan detection, and explicit partial/provisional completeness.
- Do not reintroduce `shared` or `axes` fields that contradict the merged 2-D-only preprocessing contract. Reassess when 3-D is deliberately supported.

### 4.5 Reproducibility and invalidation

- Strict parsing: reject duplicate keys, unknown fields, ambiguous identifiers, case-insensitive collisions, missing/whitespace-only identifiers, unsupported versions and invalid reference cycles.
- Validate all channel and mask identifiers against the intersection of downstream naming/reserved-name constraints.
- Write confirmed metadata atomically; retain draft state separately; pin file hash/version in run manifest.
- Full schema hash is provenance, **not** a universal cache invalidation key. Changes to controls/repeat labels must not force re-extraction of unchanged image histograms; changes to channel mapping invalidate channel-dependent products.
- Preserve N35 comparability confirmations and reopen them when relevant discovery or grouping changes.

## 5. Milestones and dependencies

### Stage 0 — specification only, before first tags

**S0.1 Owner decisions and contract freeze**
- Decide TOML, naming/alias rules, stable canonical repeat policy, mask semantics, compatibility, comparability confirmation and histogram benchmark criteria.
- Record accepted decisions and rejected alternatives in an ADR, including why no per-FOV overrides and no brick routing.
- **Done (6 November 2026):** fixed-SHA audit of the merged preprocessing mask restriction and of every consumer, with evidence and unknowns ([PR #5](https://github.com/CellMigrationLab/MorphoBricks-Spec/pull/5)); its questions Q1-Q13 are answered by the third round of owner decisions in [ADR 0001](adr/0001-experiment-description-v1.md) (AQ1-AQ13) and applied to the normative text and fixtures.

**S0.2 Normative schema**
- Write `docs/experiment-v1.md` with complete field definitions, required/optional keys, ID uniqueness/case rules, canonical/source identity and reference DAG semantics.
- Define versioning, migration, round-trip preservation, strict errors and how to handle unsupported schema versions.
- Define validation boundaries: syntax/semantics in the spec, physical file checks in preprocessing, scientific applicability in analysis layer.

**S0.3 Fixtures and conformance plan**
- Add valid/invalid TOML fixtures for single/multiple controls; paired different folder names; multiple technical repeats with differing layouts; swapped channel order; extra/missing channel; invalid within-unit divergence; instance/binary masks; partial masks; reference chains/cycles; rename/reconciliation; aliases; duplicate keys; case collisions.
- Incorporate the ten adversarial tests from RFC #1 discussion.
- Document expected pass/refuse diagnostics and exact provenance. No implementation claim until executable tests exist.

**Gate G0:** owner decisions recorded; normative schema and fixture catalogue reviewed; no runtime changes.

G0 checklist (6 November 2026, awaiting owner review of PR #3): decisions recorded (ADR 0001, three rounds); schema reviewed; fixtures conform to the text (reference-validator cross-check, [fixtures/README.md](../fixtures/README.md)); consumer audit done (PR #5); no runtime changes.

### Stage 1 — additive preprocessing authoring, after first tags

**S1.1 Discovery and UI**
- Reuse current `LeafFolder` identity (condition × source biological repeat × technical repeat).
- Scan headers, channel count, interpreted axes, calibration availability and masks with phase-aware progress.
- Detect intra-unit discrepancies before prompting for channel identity; show safe bounded-memory representative previews with C index, FOV, T/Z and header labels.
- Let user confirm canonical channels, repeat pairing, condition references and mask semantics; allow batch confirmation only for verified equivalent layouts.

**S1.2 Draft, confirmation and reconciliation**
- No initial TOML required. Generate draft, load previous confirmed TOML when present, classify unchanged/new/removed/conflicting.
- Keep stable canonical repeat IDs; explicitly resolve renames, moved files and new technical repeats.
- Preserve N35 repeat comparability confirmation, including when it must be reopened.
- Publish atomically; record exact spec hash and provenance; never silently rewrite confirmed semantics.

**S1.3 Compatibility and semantic RunInputs**
- Produce existing `experiment_design.csv` as a deterministic derived compatibility output.
- Expose canonical channel availability/index, canonical/source repeat identity, condition reference graph and mask semantics through RunInputs.
- Keep legacy homogeneous datasets numerically and structurally identical; **explicitly refuse heterogeneous processing at this stage** with a precise reason, even though the TOML schema can represent it.

**Gate G1:** notebook starts with raw folders; confirmed file reloads/reconciles; legacy exports/identities/caches are preserved; heterogeneous run refusal is explicit and tested.

### Stage 2 — downstream semantic adapters

**S2.1 MorphoFeature**
- Populate existing per-FOV `ChannelCatalogue` from validated RunInputs; remove global run-level channel mapping assumption for preprocessing-backed runs.
- Separate confirmed canonical channel ID from raw header label.
- Preserve provider feature-request semantics; refuse missing required channels/masks before computation unless scope explicitly excludes them.
- Migrate repeat grouping from raw source labels/CSV where safe, retaining compatibility paths.

**S2.2 MorphoRelate**
- Provider route continues receiving named channel planes and explicit analysis mask roles.
- Direct preprocessing-run mode resolves channel index per FOV through RunInputs, not one global `{name:index}` mapping.
- Preserve explicit array-input mappings for independent in-memory runs.

**S2.3 FiberFeatures**
- Provider route remains named-channel based.
- Direct preprocessing-run reader switches from raw header channel names to canonical RunInputs names/index resolution.
- Verify FOV-aware and technical-repeat-aware grouping and metadata exports.

**S2.4 MorphoObjects and MorphoEmbed**
- No independent experiment parser in providers; verify named channels and valid instance object sets.
- MorphoEmbed fitted normalization must group by canonical biological-repeat ID; test mixed technical-repeat membership and partial channel presence.

**S2.5 MorphoCoverage**
- Export/prefill canonical biological repeats, condition references/reference chains, target/treatment key and source provenance.
- Keep contrast selection, normalization strategy, readouts, FDR and stopping rules inside MorphoCoverage.
- Preserve correct pairing when source folder repeat labels differ across conditions.

**S2.6 CellPatcher**
- Audit and adapt every channel-selection/patch-export path that assumes one source C index has the same meaning across FOVs.
- Preserve patch-set, FOV, t/z, position_id, object_set and provider API v3 identity contracts.

**Gate G2:** all relevant consumers accept semantic identity without independently interpreting experiment TOML; homogeneous legacy parity and explicit missing-channel refusals pass.

### Stage 3 — coordinated heterogeneous-channel enablement

**S3.1 Histogram contract benchmark**
- Evaluate **semantic-wide one-row-per-plane** as preferred candidate versus **long one-row-per-plane-channel**.
- Test storage size, parser complexity, deterministic serialization, per-plane identity, pooling and grouping, absent channels, resume/parallel parity and existing N41/N42 behavior.
- Define explicit channel presence and distinguish absent from failed measurement; never fabricate zero/NaN histograms for absent channels.
- Freeze a versioned migration/compatibility policy only after evidence-backed review.

**S3.2 Normalization migration**
- Fit/select/transform by canonical channel, not C index; preserve FOV/plane/biological repeat sampling units.
- Audit all histogram readers/writers, fitted parameters, caching, scaling, global/repeat pooling, and missing-channel error paths.
- Compare numeric outputs against legacy homogeneous datasets with documented tolerances.

**S3.3 Preprocessing and CellPatcher migration**
- Replace experiment-global channel-count/name refusals with per-imaging-unit validation only when all downstream consumers are ready.
- Ensure patch extraction/export never selects the wrong semantic channel after a source order swap.
- Record per-unit and per-repeat channel coverage; scope partial repeats explicitly.

**S3.4 End-to-end adversarial suite**
- Mixed source order, mixed counts, missing optional channels, partial technical-repeat coverage, serial/parallel/resume, corrupted headers, single discrepant FOV, cache reuse, direct/provider parity.
- Verify biological N remains biological N and technical-repeat weights are never silently changed.

**Gate G3:** no wrong-channel measurements, no silent data loss/imputation, no pseudoreplication, full provenance and legacy parity; only then enable heterogeneous processing.

### Stage 4 — progressive masks and final scientific regression

**S4.1 Mask authoring and applicability**
- Confirm semantic representation and optional source provenance; preserve existing authoritative mask-file inventory and merged 2-D restrictions.
- Validate object-set compatibility for MorphoObjects/MorphoEmbed and binary/instance roles for MorphoRelate.

**S4.2 Progressive processing**
- Support growing FOV/mask inventories with exact snapshot completeness, resumable relationship scan and no changed-file races.
- Reconcile metadata and provenance without unnecessarily recomputing unrelated pixel work.

**S4.3 Cross-brick regression**
- Full pipeline: preprocessing → MorphoFeature → MorphoObjects/MorphoRelate/FiberFeatures/MorphoEmbed → MorphoCoverage.
- Test control/reference graphs, paired repeats with different source names, partial channels/masks, feature applicability, normalization, manifest provenance and reproducibility.
- Produce release notes and migration guide for existing experiments.

**Gate G4:** documented, tested end-to-end semantic interoperability with no silent fallbacks.

## 6. Cross-repository ownership matrix

| Repository | Responsibilities | Must not do |
|---|---|---|
| MorphoBricks-Spec | Normative schema, ADRs, fixtures, conformance contract | Image IO, duplicate runtime engine |
| morphobricks-preprocessing | Discover/preview/confirm/reconcile; reference validator; RunInputs; provenance | Guess channel biology; silently reassign IDs |
| morphobricks-normalization | Canonical channel-aware histogram/fits/transform; preserve plane/FOV sampling | Pool by C index across heterogeneous units |
| CellPatcher | Canonical channel-aware patch selection/export; patch/FOV identity | Infer axes/channels or invent missing patches |
| MorphoFeature | Per-FOV catalogue; request applicability/scope; provider orchestration | Require global channel list for preprocessing runs |
| MorphoRelate | Named provider inputs; direct-run semantic adapter; analysis roles | Parse schema separately or assume global C mapping |
| MorphoObjects | Consume named arrays and valid object sets | Own experiment schema/channel mapping |
| fiberfeatures | Named provider inputs; direct-run canonical adapter; FOV-aware statistics | Use raw header names as canonical identities |
| MorphoEmbed | Named channel/object-set provider; biological-repeat-aware fits | Treat technical repeats as biological replicates |
| MorphoCoverage | Condition/repeat/control metadata and explicit statistical choices | Infer missing replicates or silently rebalance |

## 7. Acceptance test matrix

**Schema/identity:** strict parse, duplicate keys, unknown fields, invalid tokens/case collisions, reference cycles, stable IDs after new/renamed folders, immutable IDs and display-name collisions, recorded ID re-confirmation, source-name pairing.

**Acquisition:** same channels different order across units, extra channel in one unit, missing channel elsewhere, one discrepant FOV within unit refused, header alias accepted only after confirmation, undetectable swaps documented as validation limit.

**Scientific replication:** one biological repeat with two differently acquired technical repeats remains N=1; unequal FOV/technical-repeat counts reported; partial channel availability reported as full/partial/unavailable; no silent changes in weighting.

**Masks:** instances versus binary, missing/in-progress masks, mask source provenance, forbidden 2-D shared/Z behavior, direct/provider object-set refusal for incompatible representation.

**Compatibility:** legacy homogeneous outputs, `experiment_design.csv`, N35 confirmation, calibration.csv authority, existing FOV/position_id/patch-set identity, metadata-only cache reuse, channel-mapping cache invalidation.

**Execution:** deterministic serial/parallel/resume, no missing/failed measurement treated as biology, exact manifest schema hash, no silent fallback or imputation, actionable errors with paths and identity.

## 8. Work tracking and change control

- Keep RFC #1 as the architectural decision thread; this document is the detailed implementation roadmap.
- Before each stage, open scoped implementation issues in the owning repositories with fixed-SHA evidence, precise acceptance tests and migration/compatibility expectations. Do not open implementation PRs before the first tags.
- Record each decision in an ADR and update fixtures first when a normative behavior changes.
- Do not silently change a published schema field or reinterpret an existing ID; use explicit version/migration rules.
- Stage completion requires code/tests review and runtime verification. Static inspection alone cannot establish numerical parity, performance, or scientific reproducibility.

## 9. Deferred work

Optional LabChronicle import/prefill is interoperability, **not** a prerequisite. Optional image-based channel anomaly detection is advisory and must not override confirmed semantics. Optional harmonized OME-TIFF/OME-Zarr export is for external tools, not a required canonical copy. Future 3-D mask/plane semantics need a separate versioned decision aligned with preprocessing and MorphoFeature; do not anticipate them with contradictory v1 fields.
