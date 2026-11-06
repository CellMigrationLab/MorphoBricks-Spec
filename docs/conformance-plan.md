# Conformance plan: experiment description v1

- **Status:** Plan for Stage 1 (after the first brick tags). **Nothing described here is
  implemented or has been run.** Stage 0 delivers only the normative text and fixtures.
- **Normative text:** [experiment-v1.md](experiment-v1.md). **Fixtures:**
  [fixtures/README.md](../fixtures/README.md). **Decisions:**
  [ADR 0001](adr/0001-experiment-description-v1.md).

## 1. Principles

- This repository holds no runtime code (ADR 0001). morphobricks-preprocessing is the reference
  reader and validator; it MUST run the fixtures of this repository as executable tests.
- Preprocessing MUST pin the fixtures by full commit SHA of MorphoBricks-Spec (a vendored copy
  with the SHA recorded, or a test-time checkout of that SHA), never by branch. Updating the pin
  is a reviewed change.
- Fixtures change first: any normative change lands here as text + fixtures + a new
  `schema_version` when required, then preprocessing updates its pin and code in one PR.
- A skipped fixture test is a failure in the release gate (no silent skips).
- Other bricks do not parse `morphobricks.toml`; they are tested through `RunInputs` (Stage 2).

## 2. Spec-level tests (Stage 1, preprocessing)

One parametrised test per fixture file, discovered from `fixtures/valid/*.toml` and
`fixtures/invalid/*.toml`, so a new fixture cannot be forgotten.

| Test | Assertion |
|---|---|
| Valid files | Reader accepts; reported warnings equal the set in the `Expected` header line |
| Invalid files | Reported error codes equal **exactly** the set in the `Expected` header line, all from the first failing phase; each error carries a table path and the offending value |
| Header lines | Every fixture has `Fixture`, `Expected`, `Source` header comments; the catalogue lists every file (a test compares the directory with `fixtures/README.md`) |
| Bytes, not text | Readers are given the raw bytes, so `i01_bom` and `i02_invalid_utf8` reach the encoding check (decoding with BOM stripping would hide them) |
| Duplicate keys | `tomllib` reports duplicates as `TOMLDecodeError` with "Cannot declare … twice" / "Cannot overwrite a value"; the reader MUST map them to `E_DUPLICATE_KEY` (by its own duplicate detection or by a tested mapping), and other decode errors to `E_TOML_SYNTAX` |
| Exact types | `i14` (`true` as `schema_version`) passes only if the reader checks `type(x) is int` |
| Round trip | For every valid file: `parse(write(parse(f))) == parse(f)`; `write` is idempotent; `write(parse(v18)) == write(parse(v01))` byte for byte |
| Canonical bytes | `write` output is UTF-8, LF, no BOM, final newline, ordered per experiment-v1 §9.1 |
| Section digests | `v01` and `v21` have equal `channels`, `repeats` and `masks` digests and a different `conditions` digest; `v01` and `v16` have all four digests equal (`display_name` omitted) |
| Transitions | Each `fixtures/transitions/t*.toml` is valid on its own; checked against its named predecessor without a recorded re-confirmation it is refused with `R_CONFIRMED_ID_CHANGED`, and accepted with one |
| Derived CSV | For each valid file the derived `experiment_design.csv` matches a golden file to be added under `fixtures/expected/` in Stage 1 (byte comparison); for `v13` the golden file is produced by today's preprocessing from the equivalent legacy answers |
| Migration | Legacy CSV with 0, 1 and ≥ 2 controls: 0/1 give deterministic references, ≥ 2 give an unpublishable draft; lenient values (`yes`, empty) are refused |
| Version policy | `i09`, `i10` refused with a message naming supported version 1 |

## 3. Physical scenarios (preprocessing-owned)

These need synthetic image trees, built in preprocessing's test suite from small generated TIFFs
(OME-TIFF where header names are needed, ImageJ TIFF where none are). Each uses a valid fixture as
the confirmed file. Where several refusals could apply to one unit, `R_UNIT_NOT_HOMOGENEOUS` is
reported first (intra-unit discrepancies are detected before channel identity, roadmap S1.1).

| # | Fixture | Image tree | Required outcome |
|---|---|---|---|
| P01 | `v01` | `CTRL/rep1`: FOV003 has header names in the order ACTIN, DNA while FOV001-002 have DNA, ACTIN | `R_UNIT_NOT_HOMOGENEOUS`, naming FOV003, path, C0/C1; no per-FOV exception; unit blocked |
| P02 | `v01` | `CTRL/rep1`: FOV004 has 1 channel, others 2 | `R_UNIT_NOT_HOMOGENEOUS` (not `R_CHANNEL_COUNT_MISMATCH`) |
| P03 | `v11` | C0 header `hoechst 33342` (lower case) | `R_HEADER_CONTRADICTION` (no case folding, no similarity); passes with `Hoechst 33342` |
| P04 | `v04`, `v05`, `v06`, `v17` | Units matching the declared lists | Stage 1-2: `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` naming the units; nothing processed |
| P05 | `v08` | `TumorRegion` mask with values 0-5 | `R_MASK_CONTRADICTS_REPRESENTATION`; an `instances` mask with values 0/1 is accepted (pixels cannot prove instance semantics) |
| P06 | `v12` | Two unnamed, identical-shape units with fluorophores physically swapped | No refusal: documented limit; preview + confirmation only |
| P07 | `v13` | A new technical repeat appears in `DrugA/rep2` | Reconciliation: unit **new**, repeat `rep2` reopened (`confirmed = false` in the draft), nothing published until confirmed |
| P08 | `v03` | Folder `DrugA/experiment_23` renamed to `DrugA/experiment_23b` | Removed + new pending member, never auto-paired; publishing requires the user to assign it; `Day1` unchanged |
| P09 | `v01` | `morphobricks.toml` is a symlink | `R_FILE_SYMLINK` |
| P10 | `v07` | Masks folder holds an undeclared type `membrane` | `R_MASK_TYPE_NOT_DECLARED` |
| P11 | `v09` | `Nuclei` masks for 0, then 300, then all FOVs | Valid at every step; completeness recorded in the manifest |
| P12 | `v01` | A declared unit `DrugA/rep2/single` with every image excluded | `R_UNIT_NOT_FOUND` |
| P13 | `v01` | An RGB (interleaved colour) TIFF in `CTRL/rep1` | `R_RGB_NOT_SUPPORTED` |
| P14 | `v01` | `RunInputs` given a draft (reconciliation proposal, or a file with `confirmed = false`) | `A_DRAFT_REFUSED`; only the published `morphobricks.toml` is read |
| P15 | `v13` | 5 FOVs added to an existing unit, same ordered channels and headers | Confirmation kept (not reopened), change reported and recorded; a changed channel list would reopen it |
| P16 | `v01` | `v01` published; `t01`/`t02` candidate offered | `R_CONFIRMED_ID_CHANGED`; accepted only with a recorded re-confirmation; `v16` accepted with no invalidation |

## 4. Later stages (obligations recorded, not planned in detail)

- **Stage 2:** each consumer's tests use `RunInputs` built from `v03`, `v08`, `v13`, `v17`: canonical
  repeat IDs reach MorphoCoverage (`v03`); `A_MASK_NOT_INSTANCES` (`v08`); `A_SCOPE_INCOMPLETE`
  and full/partial/unavailable classification (`v17`); legacy parity (`v13`).
- **Stage 3:** the end-to-end adversarial suite (roadmap S3.4) on trees for `v04`, `v05`, `v06`,
  `v17`: no channel mixed by C index, biological N unchanged, serial/parallel/resume identical.

## 5. Exit criteria

Gate G1 (roadmap §5) may not be declared until: every fixture test of §2 and every scenario of §3
runs (no skips) and passes on the preprocessing release candidate, with the pinned Spec SHA and the
test run recorded. Until then, no document may describe any reader as conforming.
