# MorphoBricks-Spec

The cross-brick specification repository for MorphoBricks: the place for decisions and contracts
that span several bricks (preprocessing, normalization, CellPatcher, MorphoFeature, MorphoObjects,
MorphoRelate, MorphoEmbed, fiberfeatures, MorphoCoverage). It holds documents and test fixtures, and audit tools in [tools/audit](tools/audit/README.md); there is no runtime package.

- [RFC #1](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1): the minimal experiment schema (conditions, channels, repeats, masks).
- [Master roadmap](docs/master-roadmap.md): all work across the bricks in priority order (release, mixed data, spec, bugs, clean-up, speed, CI, MorphoCoverage, future).
- [Experiment metadata roadmap](docs/roadmap.md): the staged plan (Stages 0-4) for the RFC #1 schema.
- Stage 0 specification (no runtime; preprocessing is the reference reader):
  - [ADR 0001](docs/adr/0001-experiment-description-v1.md): accepted decisions for `morphobricks.toml` and rejected alternatives;
  - [Experiment description v1](docs/experiment-v1.md): the normative schema, identity rules, error catalogue and validation boundaries;
  - [Fixtures](fixtures/README.md): valid and invalid TOML files with their expected results;
  - [Conformance plan](docs/conformance-plan.md): how preprocessing will run the fixtures in Stage 1 (not implemented).
- Audits (dated evidence, not current status; the matrix audit is the freshest finding list):
  - [RFC #1 feasibility audit and addendum](docs/audits/rfc1-feasibility-2026-11-05.md) (the addendum, at the end of the file, wins where they differ);
  - [S0.1 consumer audit](docs/audits/s01-consumer-audit-2026-11-06.md);
  - [LabChronicle lessons](docs/audits/labchronicle-lessons-2026-11-06.md);
  - [Matrix audit](docs/audits/matrix-audit-2026-11-07.md), reproducible with the [audit tools](tools/audit/README.md);
  - [Cross-check prompt for an external reviewer](docs/archive/prompts/chatgpt-matrix-cross-check-2026-11-07.md) (archived; no answer filed).
