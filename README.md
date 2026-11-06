# MorphoBricks-Spec

The cross-brick specification repository for MorphoBricks: the place for decisions and contracts
that span several bricks (preprocessing, normalization, CellPatcher, MorphoFeature, MorphoObjects,
MorphoRelate, MorphoEmbed, fiberfeatures, MorphoCoverage). It holds documents and test fixtures only, no runtime code.

- [RFC #1](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1): the minimal experiment schema (conditions, channels, repeats, masks).
- [Master roadmap](docs/master-roadmap.md): all work across the bricks in priority order (release, mixed data, spec, bugs, clean-up, speed, CI, MorphoCoverage, future).
- [Experiment metadata roadmap](docs/roadmap.md): the staged plan (Stages 0-4) for the RFC #1 schema.
- Stage 0 specification (no runtime; preprocessing is the reference reader):
  - [ADR 0001](docs/adr/0001-experiment-description-v1.md): accepted decisions for `morphobricks.toml` and rejected alternatives;
  - [Experiment description v1](docs/experiment-v1.md): the normative schema, identity rules, error catalogue and validation boundaries;
  - [Fixtures](fixtures/README.md): valid and invalid TOML files with their expected results;
  - [Conformance plan](docs/conformance-plan.md): how preprocessing will run the fixtures in Stage 1 (not implemented).
- Audits:
  - [RFC #1 feasibility audit](docs/audits/rfc1-feasibility-2026-11-05.md);
  - [RFC #1 addendum](docs/audits/rfc1-addendum-2026-11-05.md) (the addendum wins where they differ).
