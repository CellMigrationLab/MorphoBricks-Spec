# ADR 0001: experiment description v1 (`morphobricks.toml`)

- **Status:** Accepted (owner decisions of 6 November 2026). Specification only; nothing is
  implemented.
- **Tracking:** [RFC #1](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1);
  [roadmap §2 and §5 Stage 0](../roadmap.md);
  [feasibility audit](../audits/rfc1-feasibility-2026-11-05.md);
  [addendum](../audits/rfc1-addendum-2026-11-05.md) (the addendum wins where they differ).
- **Normative text:** [experiment-v1.md](../experiment-v1.md). Where this ADR and the normative
  text differ, the normative text wins; this ADR records why.

## Context

Preprocessing discovers an experiment and asks the user to confirm its semantics once. Today
those answers are scattered: repeat pairing and the N35 comparability confirmation in
`experiment_design.csv`, channel names per brick, mask kinds in the manifest, a boolean
`control` nobody consumes. RFC #1 proposes one strict, versioned experiment description that
preprocessing writes and validates and that downstream bricks consume through `RunInputs`.
Stage 0 freezes the decisions, the normative schema and the fixtures before any code changes.

## Decisions

### Owner decisions of 6 November 2026 (recorded verbatim, accepted)

1. **Format: TOML** (`morphobricks.toml`), strict parser + semantic validator: duplicate keys,
   unknown fields and implicit conversions refuse.
2. **Biological-repeat identity: stable, user-confirmed canonical ID** (default the source folder
   name when pairing is trivial); never changes automatically on rename/reorder; renames are
   explicit recorded migrations.
3. **Channel aliases: user-confirmed only**; canonical token + optional display label + confirmed
   header evidence; never inferred from pixels or name similarity.
4. **Scope: reduced v1**: conditions, canonical channels, repeat pairing, technical-repeat
   acquisition layouts, mask semantics (`instances` vs `binary`, source type, optional
   source-channel provenance), optional primary `condition.reference` (acyclic); heterogeneity
   representable in the schema but Stage 1 runtime refuses it until Stage 3.

### Earlier owner decisions kept

5. Calibration stays in `calibration.csv` (not copied).
6. `experiment_design.csv` stays a deterministic derived compatibility output.
7. N35 comparability confirmation kept and reopened when discovery/grouping changes.
8. 2-D planes only in v1 (Z projection is a recorded preprocessing step, preprocessing #176).
9. No per-FOV overrides.
10. No brick routing.
11. No spec runtime package (preprocessing is the reference reader).
12. Histogram representation is decided later by benchmark (candidates and criteria below only).

### Consequences fixed by this ADR

- The technical repeat (`condition × source biological repeat × technical repeat`, preprocessing's
  leaf folder) is the homogeneous imaging unit; its ordered channel list maps source C0, C1, … to
  canonical channel IDs. Different units may differ; this never creates biological repeats.
- The canonical repeat ID is the downstream `biological_repeat` / `repeat_group`; the source folder
  label is provenance (`source_repeat`) and is never parsed.
- Mask `axes`, `shared` and `plane_scope` are not v1 fields (preprocessing #173, merged as
  `6e740196`, refuses shared 2-D masks and Z > 1); a mask has its image's axes.
- `experiment`, `roles` and the boolean `control` are not v1 fields: `experiment` would be an FDR
  family declaration (MorphoCoverage configuration); "is a control" is derived from `reference`.
- Retired canonical repeat IDs are kept in the file (`retired_repeats`) so that renames are
  recorded and an ID is never reused for different data.
- Validation is split into three boundaries with distinct error namespaces: the spec (syntax and
  semantics, `E_*`), preprocessing (physical files, `R_*`) and the analysis layer (applicability,
  `A_*`).
- No machine schema (JSON Schema) in Stage 0: cross-references, case rules and graph rules are
  not expressible in it, and TOML has no standard schema language. The normative prose and the
  fixtures with exact codes are the contract.

### Histogram representation: candidates and criteria only (not decided)

| Candidate | Shape | Status |
|---|---|---|
| Semantic-wide (preferred candidate) | One row per plane (N41 kept); columns by canonical channel ID; per-row explicit channel presence; absent channel is empty, never zero | Benchmark |
| Long / channel-keyed | One row per plane × channel | Benchmark |

The decision MUST wait for evidence on both candidates for: bit-identical legacy parity on
homogeneous data; plane and image counts independent of channel count (no pseudoreplication);
pooling by canonical channel ID and biological repeat, never by C index; absent vs failed
measurement distinguished, no fabricated zero/NaN; deterministic serial/parallel/resume bytes;
N41/N42 compatibility; storage size and parser complexity; reader refusal of values outside the
declared presence.

## Rejected alternatives

### YAML (`morphobricks.yaml`, as in the RFC draft)

YAML 1.1 typing derives values from text, which violates "no parsing of identities". Reproduced
with PyYAML 6.0.1 `safe_load` (feasibility audit §3.12):

| Input | Result |
|---|---|
| `NO:` as a condition key | key `False` |
| `CTRL` declared twice | second silently wins (also with `BaseLoader`) |
| `biological_repeat: 2026-01-01` | `datetime.date(2026, 1, 1)` |
| `biological_repeat: 012` | `10` (octal) |
| `biological_repeat: 1.0` / `1_000` | `1.0` / `1000` |
| `biological_repeat: ~` / `off` | `None` / `False` |

`BaseLoader` stops typing but still accepts duplicate keys and needs anchors/aliases refused by
hand. Preprocessing has no YAML dependency today; adding one adds it to every brick. TOML via the
standard library `tomllib` (Python ≥ 3.11) refuses duplicate keys by specification, makes unquoted
text a syntax error (`012` and `NO` cannot be read as values), and types only what is written as
a typed literal, which the validator then refuses where text is required.

### Strict JSON

Workable (an `object_pairs_hook` refusing duplicates), but rejected: the default `json` module
silently keeps the last duplicate and accepts `NaN`/`Infinity`, so strictness depends on every
reader configuring it; no comments; poor to hand-review. TOML gives the same data model with
duplicate refusal built in.

### Per-FOV overrides

Rejected (RFC invariant 6, roadmap §4.1). An override would turn a structural contradiction inside
an imaging unit into an accepted exception, hide swapped or missing channels, and reintroduce file
inventory into the description. A divergent FOV blocks its unit with exact FOV/path/C-index
evidence; the remedies are exclusion or re-export.

### Brick routing

Rejected (RFC invariant 16). The file describes what the experiment is, not what is analysed.
Routing couples the schema to the current brick set and duplicates analysis requests, which own
channel/mask selection and roles (`nucleus`, `cell`, `region`).

### Auto-numbered repeat IDs (`R001`, `R002`, …)

Rejected (audit §3.7, addendum §2.4). Numbers depend on processing order and history, so two
people processing the same folders in different increments get different IDs; removal makes reuse
possible unless tombstones are kept; switching existing datasets from `rep1` to `R001` churns
`biological_repeat`, FOV identities, caches and MorphoCoverage tables for no scientific gain. The
default is the source folder name when pairing is trivial; the user confirms any other ID.

### Others

- **Inferring aliases** from pixels, embeddings or name similarity (`DAPI` ≈ `DNA`): rejected;
  identity is a user confirmation, header names are evidence only.
- **Copying calibration** into the file: rejected; `calibration.csv` is authoritative, can target
  single images, and is already SHA-pinned.
- **A spec runtime package** (`load_experiment()` in this repository): rejected for now;
  preprocessing is the reference reader and runs the fixtures (see
  [conformance plan](../conformance-plan.md)).
- **An `x-` extension namespace**: rejected; it would be a back door for unvalidated semantics.
  Any new field needs a new `schema_version`.
