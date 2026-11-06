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
- **Pin integrity.** The vendored fixture tree MUST hash to the pinned SHA: the git tree-object ID
  of the vendored `fixtures/` directory (computed with git's tree algorithm, for example
  `git hash-object`-compatible code or a scratch `git write-tree`) MUST equal
  `git rev-parse <pinned-sha>:fixtures`. A test fails if one byte of a vendored fixture differs, is
  added or is missing, so a local edit of a fixture cannot make a reader pass. A test-time checkout
  of the pinned SHA needs no copy but runs the same check.
- **No second copy of the rules.** Preprocessing MUST NOT carry a fallback, older or lenient copy
  of the rules, schema or enumerations; the fixtures and the normative text are the only source
  (experiment-v1 §2.7).
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
| Section digests | `v01`, `v16` and `v21` have all four digests equal (`display_name`, `target` and `treatment_key` omitted; `used_ids` is not a section); editing only `target`, `treatment_key` or `display_name` fields of a copy of `v01` (as `v27` varies them) leaves all four digests unchanged, while editing a `reference` changes the `conditions` digest |
| Transitions | Each `fixtures/transitions/t*.toml` is valid on its own; checked against its named predecessor it gives exactly the set of codes in its `Expected` line, all reported together (`t01`: `R_CONFIRMED_ID_CHANGED`, accepted only with a recorded re-confirmation; `t02`: `R_CONFIRMED_ID_CHANGED` and `R_USED_ID_DROPPED`; `t03`: `R_USED_ID_REUSED` only; `t04`: `R_USED_ID_DROPPED`; `t05`: `R_CONFIRMED_ON_CHANGED`; `t06`: no code, accepted: adding members is not a changed entity; `t07`, `t08`: `R_CONFIRMED_ID_CHANGED` unless a removal or reassignment confirmation is recorded; `t09`: `R_CONFIRMED_ID_CHANGED` only, accepted with a recorded re-confirmation; `t10`, `t11`: a condition or technical repeat ID changed for the same `source_folder`, and `t12`: a `source_folder` changed for an existing ID (a reassignment): each `R_CONFIRMED_ID_CHANGED` only, accepted with a recorded confirmation) |
| RGB | `v28`, `v29` are accepted; `i100`-`i106`, `i119` give their codes (`E_ENUM`, `E_TYPE`, `E_RGB_UNIT_CHANNELS`, `E_RGB_TOKEN_MISUSE`, `E_RGB_ALIAS`); a writer given a model with an RGB unit emits `channels` then `image_type = "rgb"` (field order of experiment-v1 §4, §9.1) and round-trips it |
| Reserved and forbidden names | `i59`, `i61`, `i107`-`i109` are `E_ID_RESERVED` (the reader's list equals the table of experiment-v1 §3.2, compared case-folded, and `v32` is accepted); `i113`-`i115` are `E_FORBIDDEN_FIELD` for ID keys, as `i20`-`i26` are for fields; `v33` and `v34` are accepted: the same names as folder labels are `source_folder` values and are never restricted |
| Source folders | `v33`, `v34` are accepted; `i120`, `i121` are `E_MISSING_FIELD`; `i122`, `i123` are `E_SOURCE_FOLDER_REUSED` (two IDs, one folder), `i124` is `E_SOURCE_FOLDER_CONFLICT` (one technical repeat ID, two folders); `i125` is `E_SINGLE_MISUSE`; a writer given a model in which a `source_folder` is used as a key, a `reference` value or a `used_ids` entry refuses to write; a reader never resolves an ID through a `source_folder` |
| One code per rule | `i118` gives exactly `E_ID_TEXT` and `E_ID_SYNTAX`; `i116`, `i117` give `E_ID_NOT_NFC` and never `E_UNKNOWN_CHANNEL`; `i110` is `E_DUPLICATE_VALUE` (equal after NFC); `v31` is accepted with its three whitespace aliases and a decomposed alias |
| Mask fields | `i111` (`parent_labels`) is `E_ENUM`; `i112` (`binary_mask_policy`) is `E_FORBIDDEN_FIELD` |
| Identity never repaired | `v26` is read and written back unchanged in every ID (`cl001`, `CL1000`, `R999`, `R1000`: no padding, re-casing or renumbering); `i78`, `i83`-`i85` are refused with `E_ID_NOT_NFC` and the reader output contains no normalized copy |
| Display names | `v24` round-trips with every display name byte-identical; `i86`-`i88` are `E_DISPLAY_NAME_COLLISION`; `i89`-`i91` give the unknown-ID codes, never a match through a display name |
| `used_ids` | `v25` is valid; `i92`-`i97` give their listed codes; `i126` is `E_MISSING_FIELD` and `i127` is `E_USED_ID_MISSING` (the technical repeat kind); a writer given a model whose `used_ids` lacks a declared ID refuses to write |
| Descriptive keys | `v27` is valid with no warning and no grouping: a grouping, join or cache key built on `target` or `treatment_key` fails a test that edits only those fields and expects every digest unchanged |
| `confirmed_on` | `i98` is `E_MISSING_FIELD`; a writer test with a frozen clock moved by a day writes identical bytes for an unchanged model (no clock read) |
| Provenance | `i99` is `E_FORBIDDEN_FIELD`; a run manifest test records lab-tool links and a changed link leaves every digest and cache key unchanged |
| Derived CSV | For each valid file the derived `experiment_design.csv` matches a golden file to be added under `fixtures/expected/` in Stage 1 (byte comparison); for `v13` the golden file is produced by today's preprocessing from the equivalent legacy answers; for `v33` the `condition` column holds the folder label `control`, never the ID `ctrl` (the CSV carries the `source_folder` labels, experiment-v1 §11); byte-identity is asserted only for repeat groups with a single `confirmed_on` |
| Migration | Legacy CSV with 0, 1 and ≥ 2 controls: 0/1 give deterministic references, ≥ 2 give an unpublishable draft; lenient values (`yes`, empty) are refused; a legacy `condition` label on the reserved or forbidden lists (for example `control`) migrates to `source_folder` with another confirmed ID and is not refused; a legacy group with several `confirmed_on` dates takes the latest and the migration note lists the original per-row dates (P30) |
| Version policy | `i09`, `i10` refused with a message naming supported version 1. The supported set is a code constant; the test runs with the network blocked (no socket may be opened) and passes; `i11` (missing version) is `E_SCHEMA_VERSION_MISSING` and no code path maps it to a default version |
| Pin integrity | The vendored tree's git tree-object ID equals `git rev-parse <pinned-sha>:fixtures`; a test mutates one byte of a copy and expects the check to fail |
| No fallback rules | A test scans the reader for a bundled copy of the rules (a second table of codes, enumerations or schema data not loaded from the pinned fixtures and text) and an import-time test confirms that removing the vendored tree makes the suite fail, not pass with defaults |

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
| P05 | `v08` | `TumorRegion` mask with values 0-5 | `R_MASK_CONTRADICTS_REPRESENTATION`, raised by the mask step when it reads the file, not at publication (experiment-v1 §4.5a); an `instances` mask with values 0/1 is accepted (pixels cannot prove instance semantics) |
| P06 | `v12` | Two unnamed, identical-shape units with fluorophores physically swapped | No refusal: documented limit; preview + confirmation only |
| P07 | `v13` | A new technical repeat appears in `DrugA/rep2` | Reconciliation: unit **new**, repeat `rep2` reopened (`confirmed = false` in the draft), nothing published until confirmed; `confirmed_on` of every repeat that is not reopened is byte-identical in the draft |
| P08 | `v03` | Folder `DrugA/experiment_23` renamed to `DrugA/experiment_23b` | Removed + new pending member, never auto-paired; publishing requires the user to assign it; `Day1` unchanged |
| P09 | `v01` | `morphobricks.toml` is a symlink | `R_FILE_SYMLINK` |
| P10 | `v07` | Masks folder holds an undeclared type `membrane` | `R_MASK_TYPE_NOT_DECLARED` |
| P11 | `v09` | `Nuclei` masks for 0, then 300, then all FOVs | Valid at every step; completeness recorded in the manifest |
| P12 | `v01` | A declared unit `DrugA/rep2/single` with every image excluded | `R_UNIT_NOT_FOUND` |
| P13 | `v28` | RGB (interleaved colour) TIFFs in every unit, units declared `image_type = "rgb"` | Accepted: header colour interpretation matches the declaration; the manifest records header-verified (formats without such metadata: recorded as not header-verified); channels are `R`, `G`, `B`; nothing is converted. Replaces the earlier RGB refusal (decision AQ6) |
| P14 | `v01` | `RunInputs` given a draft (reconciliation proposal, or a file with `confirmed = false`) | `A_DRAFT_REFUSED`; only the published `morphobricks.toml` is read |
| P15 | `v13` | 5 FOVs added to an existing unit, same ordered channels and headers | Confirmation kept (not reopened) with `confirmed_on` byte-identical, change reported and recorded; a changed channel list would reopen it |
| P16 | `v01` | `v01` published; `t01`/`t02` candidate offered | `R_CONFIRMED_ID_CHANGED` (`t02` also `R_USED_ID_DROPPED`); `t01` accepted only with a recorded re-confirmation; `v16` accepted with no invalidation |
| P17 | `v01` (base), `v21`, `v16` | Two drafts derived from the same published `v01` (draft A = `v21` bytes, draft B = `v16` bytes); A published first | A accepted; B refused with `R_PUBLISHED_FILE_CHANGED` and not merged; the published bytes remain A's; re-deriving B from A's file is accepted |
| P18 | `v01` | A draft with base `absent`, then another `morphobricks.toml` appears before publication; also a draft with no recorded base | `R_PUBLISHED_FILE_CHANGED`; `R_DRAFT_BASE_MISSING` respectively; nothing published |
| P19 | `v25` (base), `t03` | Candidate `t03` offered over published `v25` | `R_USED_ID_REUSED`; also refused when the returning source folder is the one the removed DrugA had |
| P20 | `v25` (base), `t04` | Candidate `t04` offered over published `v25`; also a user removing the last member of a condition | `R_USED_ID_DROPPED`; the removal itself is accepted and the ID stays in `used_ids` |
| P21 | `v01` | Two folders `Cafe\u0301` and `Caf\u00e9` (or one decomposed folder) under a condition on a file system that allows both | `R_FOLDER_NOT_NFC`; nothing renamed or normalized |
| P22 | `v01` (base), `t05` | Reconciliation after new FOVs in an existing unit (P15) and a run on a later date | Published `confirmed_on` stays `2026-11-06` byte for byte; `t05` offered over `v01`: `R_CONFIRMED_ON_CHANGED`; after a reopening (changed channel list) and a new user confirmation the new date is accepted |

### Scenarios added by the third decision round (AQ1-AQ13) and the fourth (FR1, FR2: P32, P33)

| # | Fixture | Image tree / action | Required outcome |
|---|---|---|---|
| P23 | `v28`, `v01` | (a) A unit declared `rgb` whose images are 2-channel grayscale; (b) an RGB TIFF in a `v01` unit that does not declare it; (c) an image of an undeclared type whose pixels look like RGB | (a), (b) `R_IMAGE_TYPE_CONTRADICTS_HEADER` (both directions); (c) no refusal and no inference: pixels are never examined |
| P24 | `v28` | A request through a brick that does not declare RGB support; the same request through one that does | `A_RGB_NOT_SUPPORTED` for the first (no grey conversion, no channel split); the second proceeds and the brick owns the meaning |
| P25 | `v03`, `v30` | `RunInputs` FOVs of `v03` and `v30` | Each FOV carries the key with `biological_repeat` = the source label (`rep1`, `experiment_23`) and the added `repeat_group` (`Day1`); patch IDs, scaling keys, caches and exports keep the source label; pairing and pooling use `repeat_group`; in `v30` the two `rep1` folders are in different repeats; falling back to grouping by `biological_repeat` fails a test |
| P26 | `v11`, `v31` | C0 header ` DAPI` (leading space) against `v11`; against `v31`; a decomposed header `Cafe\u0301 488` against a composed entry (and the reverse) | `R_HEADER_CONTRADICTION` against `v11` (no trimming); accepted against `v31` (the confirmed alias ` DAPI`); NFC of both sides matches the decomposed and composed spellings; the manifest records the header name as read (untrimmed) |
| P27 | `v08` | `TumorRegion` requested as an object set: (a) plainly; (b) with the per-request conversion `binary_mask_policy="connected_components"`; (c) a later request without it | (a) `A_MASK_NOT_INSTANCES`; (b) accepted, the conversion recorded in the run manifest with mask ID, method and parameters; (c) `A_MASK_NOT_INSTANCES` again; no setting is written to `morphobricks.toml` (`i112`) |
| P28 | `v09`, `v08` | Masks added in batches; a run before the mask step has read a batch; a `binary` mask with values 0-5 in the second batch | Publication reads no mask pixels and records `not yet checked`; the run refuses with `A_MASK_UNCHECKED`; the mask step checks each new batch and the third batch is `not yet checked` again; the bad batch gives `R_MASK_CONTRADICTS_REPRESENTATION` |
| P29 | `v07` | A mask folder `NA`, a mask folder ` cells`, a non-NFC mask type name | `R_MASK_TYPE_NAME_INVALID` for the first two at discovery (never reaching `E_ID_TEXT`); `R_FOLDER_NOT_NFC` for the third; nothing renamed |
| P30 | `v13` | A legacy group whose rows carry `confirmed_on` 2026-10-01 and 2026-10-15; a legacy group whose rows share one date | The repeat's `confirmed_on` is 2026-10-15 and the migration note lists both folder dates; the clock is never read; the derived CSV is byte-identical to the legacy file for the one-date group and differs for the other group only in the earlier date |
| P31 | `v27` | MorphoCoverage prefills its reagent grouping from `target`; the user confirms inside MorphoCoverage; then `target` is edited in the file | The prefill is shown as a suggestion and only the confirmed grouping is used; an unconfirmed prefill is refused for analysis; the edit changes no confirmed grouping, digest or cache key |
| P32 | `v33`, `v34` | Discovery of an experiment whose condition folder is `control` and whose technical-repeat folders are `files` and `overrides`; the user confirms the proposed IDs; a second experiment whose folders are `CTRL` and `acquisition_1` | For the first, preprocessing proposes IDs that are not the forbidden names (never `control`, `files`, `overrides`), nothing is adopted before confirmation, `display_name` may be set to the folder label, and the derived `experiment_design.csv` carries `control`, byte-identical to a legacy file for the same folders; for the second the folder label is proposed as the ID. No folder is renamed on disk |
| P33 | `v33` (base), `t10`-`t12` | Reconciliation after the folder `control` is renamed to `ctl` on disk: (a) the new folder is attached to the existing ID `ctrl` without a recorded confirmation; (b) with it; (c) the new folder gets a new ID and the old one is removed | (a) `R_CONFIRMED_ID_CHANGED` (`t12`); (b) accepted, ID `ctrl` unchanged, `source_folder` now `ctl`, N35 reopened for the affected repeats; (c) accepted only with the removal confirmation; `ctrl` stays in `used_ids` and is never reused (`R_USED_ID_REUSED`) |

## 4. Later stages (obligations recorded, not planned in detail)

- **Stage 2:** each consumer's tests use `RunInputs` built from `v03`, `v08`, `v13`, `v17`, `v28`: canonical
  repeat IDs reach MorphoCoverage as `repeat_group` beside the unchanged source label (`v03`, `v30`, P25);
  RGB support is declared or refused per brick (`v28`, P24); `A_MASK_NOT_INSTANCES` (`v08`); `A_SCOPE_INCOMPLETE`
  and full/partial/unavailable classification (`v17`); legacy parity (`v13`); the added `condition_id` and `technical_repeat_id` beside the unchanged source labels (`v33`, `v34`, P32).
- **Stage 3:** the end-to-end adversarial suite (roadmap S3.4) on trees for `v04`, `v05`, `v06`,
  `v17`: no channel mixed by C index, biological N unchanged, serial/parallel/resume identical.

## 5. Exit criteria

Gate G1 (roadmap §5) may not be declared until: every fixture test of §2 and every scenario of §3
runs (no skips) and passes on the preprocessing release candidate, with the pinned Spec SHA and the
test run recorded. Until then, no document may describe any reader as conforming.
