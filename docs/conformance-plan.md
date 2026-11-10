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
| Duplicate keys | `tomllib` reports duplicates as `TOMLDecodeError` with "Cannot declare … twice" / "Cannot overwrite a value" (and "Duplicate inline table key" inside an inline table, `i134`); the reader MUST map them to `E_DUPLICATE_KEY` (by its own duplicate detection or by a tested mapping), and other decode errors to `E_TOML_SYNTAX` |
| Exact types | `i14` (`true` as `schema_version`) passes only if the reader checks `type(x) is int` |
| Round trip | For every valid file: `parse(write(parse(f))) == parse(f)`; `write` is idempotent; `write(parse(v18)) == write(parse(v01))` byte for byte |
| Canonical bytes | `write` output is UTF-8, LF, no BOM, final newline, ordered per experiment-v1 §9.1 |
| Section digests | `v01`, `v16` and `v21` have all four digests equal (`display_name`, `target` and `treatment_key` omitted; `used_ids` is not a section); editing only `target`, `treatment_key` or `display_name` fields of a copy of `v01` (as `v27` varies them) leaves all four digests unchanged, while editing a `reference` changes the `conditions` digest |
| Transitions | Each `fixtures/transitions/t*.toml` is valid on its own; checked against its named predecessor it gives exactly the set of codes in its `Expected` line, all reported together (`t01`: `R_CONFIRMED_ID_CHANGED`, accepted only with a recorded re-confirmation; `t02`: `R_CONFIRMED_ID_CHANGED` and `R_USED_ID_DROPPED`; `t03`: `R_USED_ID_REUSED` only; `t04`: `R_USED_ID_DROPPED`; `t05`, `t13`: `R_CONFIRMED_ON_CHANGED` (`t13`: beside a changed `image_count` only); `t06`: no code, accepted: adding members is not a changed entity; `t07`, `t08`: `R_CONFIRMED_ID_CHANGED` unless a removal or reassignment confirmation is recorded; `t09`: `R_CONFIRMED_ID_CHANGED` only, accepted with a recorded re-confirmation; `t10`, `t11`: a condition or technical repeat ID changed for the same `source_folder`, and `t12`: a `source_folder` changed for an existing ID (a reassignment): each `R_CONFIRMED_ID_CHANGED` only, accepted with a recorded confirmation) |
| RGB | `v28`, `v29` are accepted; `i100`-`i106`, `i119` give their codes (`E_ENUM`, `E_TYPE`, `E_RGB_UNIT_CHANNELS`, `E_RGB_TOKEN_MISUSE`, `E_RGB_ALIAS`); a writer given a model with an RGB unit emits `channels` then `image_type = "rgb"` (field order of experiment-v1 §4, §9.1) and round-trips it |
| Reserved and forbidden names | `i59`, `i61`, `i107`-`i109` are `E_ID_RESERVED` (the reader's list equals the table of experiment-v1 §3.2, compared case-folded, and `v32` is accepted); `i113`-`i115` are `E_FORBIDDEN_FIELD` for ID keys, as `i20`-`i26` are for fields; `v33` and `v34` are accepted: the same names as folder labels are `source_folder` values and are never restricted |
| Source folders | `v33`, `v34` are accepted; `i120`, `i121` are `E_MISSING_FIELD`; `i122`, `i123` are `E_SOURCE_FOLDER_REUSED` (two IDs, one folder), `i124` is `E_SOURCE_FOLDER_CONFLICT` (one technical repeat ID, two folders); `i125` and `i131`-`i133` are `E_SINGLE_MISUSE` (a technical repeat or a condition `single` only with the folder `single`; a `single` condition is alone); `v35` is accepted; a writer given a model in which a `source_folder` is used as a key, a `reference` value or a `used_ids` entry refuses to write; a reader never resolves an ID through a `source_folder` |
| One code per rule | `i118` gives exactly `E_ID_TEXT` and `E_ID_SYNTAX`; `i116`, `i117` give `E_ID_NOT_NFC` and never `E_UNKNOWN_CHANNEL`; `i110` is `E_DUPLICATE_VALUE` (equal after NFC); `v31` is accepted with its three whitespace aliases and a decomposed alias |
| Mask fields | `i111` (`parent_labels`) is `E_ENUM`; `i112` (`binary_mask_policy`) is `E_FORBIDDEN_FIELD` |
| Identity never repaired | `v26` is read and written back unchanged in every ID (`cl001`, `CL1000`, `R999`, `R1000`: no padding, re-casing or renumbering); `i78`, `i83`-`i85` are refused with `E_ID_NOT_NFC` and the reader output contains no normalized copy |
| Display names | `v24` round-trips with every display name byte-identical; `i86`-`i88` are `E_DISPLAY_NAME_COLLISION`; `i89`-`i91` give the unknown-ID codes, never a match through a display name |
| `used_ids` | `v25` is valid; `i92`-`i97` give their listed codes; `i126` is `E_MISSING_FIELD` and `i127` is `E_USED_ID_MISSING` (the technical repeat kind); a writer given a model whose `used_ids` lacks a declared ID refuses to write |
| Descriptive keys | `v27` is valid with no warning and no grouping: a grouping, join or cache key built on `target` or `treatment_key` fails a test that edits only those fields and expects every digest unchanged |
| `confirmed_on` | `i98` is `E_MISSING_FIELD`; a writer test with a frozen clock moved by a day writes identical bytes for an unchanged model (no clock read) |
| Provenance | `i99` is `E_FORBIDDEN_FIELD`; a run manifest test records lab-tool links and a changed link leaves every digest and cache key unchanged |
| Derived CSV | For each valid file the derived `experiment_design.csv` matches a golden file (byte comparison; present under `fixtures/expected/` for `v13`, `v33`, `v34`, to be added for the others); for `v13` the golden file is produced by today's preprocessing from the equivalent legacy answers; for `v33` the `condition` column holds the folder label `control`, never the ID `ctrl` (the CSV carries the `source_folder` labels, experiment-v1 §11); byte-identity is asserted only for repeat groups with a single `confirmed_on` |
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
| P16 | `v01` | `v01` published; `t01`/`t02` candidate offered | `R_CONFIRMED_ID_CHANGED` (`t02` also `R_USED_ID_DROPPED`); `t01` accepted only with a recorded re-confirmation, whose line in `morphobricks.records.jsonl` has the keys of experiment-v1 §4.6; `v16` accepted with no invalidation |
| P17 | `v01` (base), `v21`, `v16` | Two drafts derived from the same published `v01` (draft A = `v21` bytes, draft B = `v16` bytes); A published first | A accepted; B refused with `R_PUBLISHED_FILE_CHANGED` and not merged; the published bytes remain A's; re-deriving B from A's file is accepted |
| P18 | `v01` | A draft with base `absent`, then another `morphobricks.toml` appears before publication; also a draft with no recorded base | `R_PUBLISHED_FILE_CHANGED`; `R_DRAFT_BASE_MISSING` respectively; nothing published |
| P19 | `v25` (base), `t03` | Candidate `t03` offered over published `v25` | `R_USED_ID_REUSED`; also refused when the returning source folder is the one the removed DrugA had |
| P20 | `v25` (base), `t04` | Candidate `t04` offered over published `v25`; also a user removing the last member of a condition | `R_USED_ID_DROPPED`; the removal itself is accepted and the ID stays in `used_ids` |
| P21 | `v01` | Two folders `Cafe\u0301` and `Caf\u00e9` (or one decomposed folder) under a condition on a file system that allows both | `R_FOLDER_NOT_NFC`; nothing renamed or normalized |
| P22 | `v01` (base), `t05` | Reconciliation after new FOVs in an existing unit (P15) and a run on a later date | Published `confirmed_on` stays `2026-11-06` byte for byte; `t05` offered over `v01`: `R_CONFIRMED_ON_CHANGED`; after a reopening (changed channel list) and a new user confirmation the new date is accepted |

### Scenarios added by the third decision round (AQ1-AQ13), the fourth (FR1, FR2: P32, P33) and the records decisions (RR1, RR2: P34, P35)

| # | Fixture | Image tree / action | Required outcome |
|---|---|---|---|
| P23 | `v28`, `v01` | (a) A unit declared `rgb` whose images are 2-channel grayscale; (b) an RGB TIFF in a `v01` unit that does not declare it; (c) an image of an undeclared type whose pixels look like RGB | (a), (b) `R_IMAGE_TYPE_CONTRADICTS_HEADER` (both directions); (c) no refusal and no inference: pixels are never examined |
| P24 | `v28` | A request on the described run through a brick whose provider manifest has (a) no `rgb_support` key, (b) `rgb_support = false`; the same request through a brick whose manifest has (c) `rgb_support = true`; (d) a manifest whose `rgb_support` is not a boolean (e.g. the string `"true"`) | (a), (b) `A_RGB_NOT_SUPPORTED` (no grey conversion, no channel split); (c) proceeds and the brick owns the meaning; (d) a manifest error, never read as support. The refusal needs no pixel read. An undescribed run is refused before this test applies (ADR 0002 AR10) |
| P25 | `v03`, `v30` | `RunInputs` FOVs of `v03` and `v30` | Each FOV carries the key with `biological_repeat` = the source label (`rep1`, `experiment_23`) and the added `repeat_group` (`Day1`); patch IDs, scaling keys, caches and exports keep the source label; pairing and pooling use `repeat_group`; in `v30` the two `rep1` folders are in different repeats; falling back to grouping by `biological_repeat` fails a test |
| P26 | `v11`, `v31` | C0 header ` DAPI` (leading space) against `v11`; against `v31`; a decomposed header `Cafe\u0301 488` against a composed entry (and the reverse) | `R_HEADER_CONTRADICTION` against `v11` (no trimming); accepted against `v31` (the confirmed alias ` DAPI`); NFC of both sides matches the decomposed and composed spellings; the manifest records the header name as read (untrimmed) |
| P27 | `v08` | `TumorRegion` requested as an object set: (a) plainly; (b) with the per-request conversion `binary_mask_policy="connected_components"`; (c) a later request without it | (a) `A_MASK_NOT_INSTANCES`; (b) accepted, the conversion recorded in the run manifest with mask ID, method and parameters; (c) `A_MASK_NOT_INSTANCES` again; no setting is written to `morphobricks.toml` (`i112`) |
| P28 | `v09`, `v08` | Masks added in batches; a run before the mask step has read a batch; a `binary` mask with values 0-5 in the second batch | Publication reads no mask pixels and records `not yet checked`; the run refuses with `A_MASK_UNCHECKED`; the mask step checks each new batch and the third batch is `not yet checked` again; the bad batch gives `R_MASK_CONTRADICTS_REPRESENTATION` |
| P29 | `v07` | A mask folder `NA`, a mask folder ` cells`, a non-NFC mask type name | `R_MASK_TYPE_NAME_INVALID` for the first two at discovery (never reaching `E_ID_TEXT`); `R_FOLDER_NOT_NFC` for the third; nothing renamed |
| P30 | `v13` | A legacy group whose rows carry `confirmed_on` 2026-10-01 and 2026-10-15; a legacy group whose rows share one date | The repeat's `confirmed_on` is 2026-10-15 and the migration note lists both folder dates; the clock is never read; the derived CSV is byte-identical to the legacy file for the one-date group and differs for the other group only in the earlier date |
| P31 | `v27` | MorphoCoverage prefills its reagent grouping from `target`; the user confirms inside MorphoCoverage; then `target` is edited in the file | The prefill is shown as a suggestion and only the confirmed grouping is used; an unconfirmed prefill is refused for analysis; the edit changes no confirmed grouping, digest or cache key |
| P32 | `v33`, `v34` | Discovery of an experiment whose condition folder is `control` and whose technical-repeat folders are `files` and `overrides`; the user confirms the proposed IDs; a second experiment whose folders are `CTRL` and `acquisition_1` | For the first, preprocessing proposes IDs that are not the forbidden names (never `control`, `files`, `overrides`), nothing is adopted before confirmation, `display_name` may be set to the folder label, and the derived `experiment_design.csv` carries `control`, byte-identical to a legacy file for the same folders; for the second the folder label is proposed as the ID. No folder is renamed on disk |
| P33 | `v33` (base), `t10`-`t12` | Reconciliation after the folder `control` is renamed to `ctl` on disk: (a) the new folder is attached to the existing ID `ctrl` without a recorded confirmation; (b) with it; (c) the new folder gets a new ID and the old one is removed | (a) `R_CONFIRMED_ID_CHANGED` (`t12`); (b) accepted, ID `ctrl` unchanged, `source_folder` now `ctl`, N35 reopened for the affected repeats; (c) accepted only with the removal confirmation; `ctrl` stays in `used_ids` and is never reused (`R_USED_ID_REUSED`) |
| P34 | `v01` (base) | `v01` published; a later publication of the same file with only one member's `image_count` changed; and a publication that also removes a confirmed member (RR3) | Accepted; no repeat reopens and `confirmed_on` is byte-identical (C3); one `image_count_changed` line is appended to `morphobricks.records.jsonl` with the keys of experiment-v1 §4.6, the old and new counts and `recorded_on`; for the combined publication one `image_count_changed` line per remaining member whose count changed is written together with the `removed` lines (RR3) |
| P35 | `v25` (base), `t07` | (a) A member removed with the user's confirmation; (b) the last member of a condition removed; (c) a technical repeat, a repeat and a condition removed, each with confirmation | Each accepted removal appends `removed` lines (entity lines first, then each `unit` line once, §4.6) whose labels are the published file's; (a) also a `reconfirmation` line where §4.6 requires one; the removed IDs stay in `used_ids`; an unconfirmed removal writes nothing and is refused |

## 4. Later stages (obligations recorded, not planned in detail)

P24, P27, P31 and the lab-tool-links part of the §2 "Provenance" row are checked at the Stage 2
gate, not at G1 (§5); the Stage 2 bullet below lists them.

- **Stage 2:** each consumer's tests use `RunInputs` built from `v03`, `v08`, `v13`, `v28`: canonical
  repeat IDs reach MorphoCoverage as `repeat_group` beside the unchanged source label (`v03`, `v30`, P25);
  RGB support is declared or refused per brick (`v28`, P24); `A_MASK_NOT_INSTANCES` and the per-request
  `binary_mask_policy` conversion (`v08`, P27); MorphoCoverage prefill of its reagent grouping from `target`, confirmed
  inside MorphoCoverage (`v27`, P31); lab-tool links recorded in the run manifest (the "Provenance" row of §2); the channel-scope refusal
  (SI1, GS2): `A_SCOPE_INCOMPLETE` on `v01` for a requested channel that no image has (a canonical channel ID
  absent from `v01` altogether: "present in 0 of n acquisitions"); and full / partial / unavailable coverage recorded per repeat, shown
  by the fixtures that can show each class at this gate (layouts are homogeneous, so a channel request is
  full or unavailable per repeat, never partial): full on `v01` (a channel every image has); unavailable on `v01`
  (the absent channel: every repeat unavailable, k = 0); partial for a mask request only, on `v09` (its single
  repeat `rep1` while the `Nuclei` masks cover 300 of 1000 FOVs, P11; the completeness is read from the run
  manifest). Partial for a channel request has no fixture at G2: it is the `v17` and `v05` case at G3 (see the Stage 3 bullet); the resolver's refusal of a run without a published description (below, ADR 0002 AR10; no legacy or undescribed parity is required); the added `condition_id` and `technical_repeat_id` beside the unchanged source labels (`v33`, `v34`, P32).
- **Stage 2, the resolver architecture ([ADR 0002](adr/0002-shared-request-resolver.md), owner decision of
  10 November 2026).** These rows are Stage 2 obligations beside the bullet above; each is shown on
  the named fixtures, through `RunInputs`, with the test run recorded at the Stage 2 gate.

  | Row | Where | Assertion |
  |---|---|---|
  | Resolver | preprocessing (resolver contract version 1, its own suite, no skips) | `RunInputs.resolve_request` on `v08`: `DNA` + `Nuclei` as objects resolves every position with the C index of each requested channel per image, `Nuclei` as `(nuclei, instances, checked)`; `TumorRegion` as objects is `A_MASK_NOT_INSTANCES` (P27 a), accepted with `binary_mask_policy = "connected_components"` and the policy returned in the selection, never applied (P27 b), refused again without it (P27 c); as a region accepted; before the mask step `A_MASK_UNCHECKED` "k of n files" (P28). `v01`: a channel no image has is `A_SCOPE_INCOMPLETE` "present in 0 of n acquisitions" and every repeat `unavailable` (SI1, GS2); an undeclared mask ID likewise. `v09` with `Nuclei` masks on 2 of 6 images: `A_SCOPE_INCOMPLETE` "present in 2 of 6" and `rep1` `partial`. `v13`: every position resolved by channel ID; a reordered channel list on one position changes that position's indices only. `v28`: `A_RGB_NOT_SUPPORTED` without `rgb_support`, accepted with it and `image_type = "rgb"` in every selection (P24, the capability as a boolean). A refused request has no selections. Every applicable refusal is reported together. The result is immutable and picklable; the provenance equals the run manifest's description SHA-256 and section digests and carries the request with its device; resolving writes nothing and reads no pixel; the resolver's modules import no brick, CellPatcher or provider module (a scan of their imports); a run without a published description is refused with `A_DESCRIPTION_REQUIRED` naming the fix (run the notebook or `describe`); `v13` is checked as a described run (every position resolved by ID), with no parity against v0.4.0 |
  | Volume | preprocessing; each consumer | A `volume` request is `A_VOLUME_NOT_SUPPORTED` unless the consumer declares `volume_support`; with it, a one-slice volume selects exactly what the plane request selects (`v01`). No consumer declares the capability in Stage 2 (a test of each consumer's declared capabilities); MorphoFeature stays 2-D |
  | Scope record | MorphoFeature | The resolver's coverage (full / partial / unavailable per repeat and subject) and the explicit device are recorded in the run manifest for a described run; a refusal stops the run before any provider computes and writes no table (`v01`, `v09` as above) |
  | Mask rule | MorphoFeature; the fiberfeatures and MorphoRelate direct runs; CellPatcher | On a described `v08`-style run with a 0/1 `binary` mask holding two disconnected blobs: without the policy every route refuses `A_MASK_NOT_INSTANCES`; with the recorded policy every route calls CellPatcher's labeller and measures **2** objects with equal label IDs; the manifest or run record of each route names the mask ID, the method and the connectivity. An `instances` mask holding only 0 and 1 is measured as stored (one object) on every route. There is no undescribed route: MorphoFeature's #180 relabelling is removed and CellPatcher has no empty-ID path (AR10). Fixes MorphoFeature #200 |
  | Cross-route | fiberfeatures; MorphoRelate (each two-route brick) | On the **same object set, FOV, plane and time point** of a described run with instance masks (labels 1 and 7) and on a T=2 time-lapse, the direct run and the MorphoFeature route give **identical shared columns**: the same values (bit-identical with the device fixed, else a stated tolerance), units, missingness (an undefined value is undefined on both, explained on both) and refusals (the same `A_*` code for the same request). The **direct-only capabilities are listed explicitly and excluded**: fiberfeatures' 137-column direct table against the provider's 9 (the 9 are the shared columns), its statistics and Optuna layer; MorphoRelate's whole-FOV table and its direct run measuring one time point per run (the comparison takes that time point). The device is explicit on both routes and recorded; the test fixes it (`cpu`) or states a tolerance |
  | Description required | every consumer: MorphoFeature, MorphoRelate, fiberfeatures, MorphoObjects, MorphoEmbed, MorphoCoverage, CellPatcher | A run without a published `morphobricks.toml` is refused before any provider computes or any file is written, with `A_DESCRIPTION_REQUIRED` naming the fix (run the notebook or `describe`). Dropped, none tested for parity: undescribed runs; `experiment_design.csv` as an input to grouping; IDs derived from folder or file names; BY_NAME grouping and the interim 0/1 labelling; CellPatcher's empty-ID path; the tests that only compare with v0.4.0 (science parity tests stay as goldens without the version framing, AR11); `position_id` stays the image file stem (AR11). A description or run manifest of an old version is refused, never converted. Beyond these, obsolete compatibility code (old version readers and migrations, deprecated aliases and parameters, shims, fallback readers, legacy notebook paths, old CLI flags) is removed in one sweep PR per repository; the science tests stay and no test of removed compatibility behaviour remains. The removal starts after the preprocessing v0.5.0 tag, as the first change of v0.5.1 |
  | Device | fiberfeatures; MorphoFeature | The device is chosen explicitly (`cpu` or `cuda`; the user or the notebook default), recorded in the run's provenance on both routes, and `cuda` without a GPU is refused, never switched. fiberfeatures' direct run no longer selects CUDA automatically |
  | Statistics rule | fiberfeatures (#195); MorphoCoverage | Inferential outputs name the biological unit: the default scoring unit is the canonical repeat (`repeat_group`); an FOV-level or position-level score is labelled exploratory and never reported as biological N; two technical repeats of one repeat sharing a position stem are never pooled into one unit of another repeat and never counted as two repeats (the two-wells fixture of the evidence report). The default change carries a release note |

- **Stage 3:** the end-to-end adversarial suite (roadmap S3.4) on trees for `v04`, `v05`, `v06`,
  `v17`: no channel mixed by C index, biological N unchanged, serial/parallel/resume identical.
  Also at Stage 3, gate G3 (owner ruling of 9 November 2026, GS2): the channel cases of `v17` and `v05`.
  `v17`: PHASE present only in `CTRL/R002/acquisition_1`; for a PHASE request R002 is partially represented and
  R001 unavailable. `v05` (variable channel count): PHASE present only in `DrugA/rep1`, while `CTRL/rep1` lists
  only DNA and ACTIN; `rep1` is the only repeat, so for a PHASE request `rep1` is partially represented (DrugA
  yes, CTRL no) and no repeat is unavailable. Both are shown as `A_SCOPE_INCOMPLETE` and full / partial /
  unavailable classification per repeat. Preprocessing refuses both layouts until Stage 3
  (`R_HETEROGENEOUS_LAYOUT_NOT_ENABLED`, P04), so the Stage 2 gate cannot show them. The list is closed: only
  these two channel cases move; nothing else is deferred and no other Stage 2 obligation, fixture or scenario changes.
- **Stage 3, the histogram table ([ADR 0003](adr/0003-plane-histograms-v5.md), owner decisions of 10 November
  2026).** A Stage 3 obligation of its own (it moves nothing from Stage 2), shown with the test run recorded at G3.

  | Row | Where | Assertion |
  |---|---|---|
  | Histogram table v5 | morphobricks-normalization (reader, writer); preprocessing (staging, `RunInputs`); CellPatcher and MorphoFeature (readers) | On image trees built from `v13`, `v04`, `v05`, `v06` and `v17`: `plane_histograms.csv` has `schema_version` 5 and **one row per plane** (row count = plane count, N41); per-channel columns by canonical channel ID, also on one tree whose channel ID contains `_` (none of these fixtures has one, so the test renames a channel, e.g. `PAX_488`); the header lists every channel ID of the description, sorted, with one presence column `channels` (`;`-separated, the IDs present in that plane, in source order) and no `failed_channels` column; an absent channel's cells are blank and a value there, or a zero/NaN histogram for it, is refused; pooling is by `repeat_group` and channel ID, never by C index (`v04`: ACTIN and DNA never mixed); the bytes are identical serially, in parallel shards and on resume. An injected measurement failure on one channel of one plane fails `plane_histograms.csv` only: that table is not written and the run reports the plane and the channel that failed. A version 4 table is refused by the version 5 reader with a message naming version 5 and how to recompute; no converter exists. The same channel-ID naming rule holds on the same trees for the fitted-parameter columns (N46/N47), CellPatcher's patch columns and the summary columns (N42 amended for all per-channel tables, ADR 0003 HV2) |

## 5. Exit criteria

Gate G1 (roadmap §5) may not be declared until: every fixture test of §2 and every scenario of §3
runs (no skips) and passes on the preprocessing release candidate, with the pinned Spec SHA and the
test run recorded. Until then, no document may describe any reader as conforming.

Scope of G1 (owner ruling of 9 November 2026, [ADR 0001](adr/0001-experiment-description-v1.md), GS1).
Exactly these items are checked at the Stage 2 gate and not at G1, and the "no skips" rule above does
not count them: P24 (a provider manifest `rgb_support`), P27 (a per-request `binary_mask_policy`),
P31 (MorphoCoverage prefill) and the lab-tool-links part of the §2 "Provenance" row (the run manifest
test; preprocessing has no lab-tool input in Stage 1). §4 records them under Stage 2. Nothing else is
deferred: every other §3 scenario and §2 row, and the `i99` assertion of the "Provenance" row, runs at
G1 in full, with every outcome it states.

Deferring them does not reduce what preprocessing shows in its own §2 rows on the same subjects: "RGB"
(`v28`, `i100`-`i106`, `i119`), "Mask fields" (`i111`, `i112`), "Descriptive keys" and "Section
digests" (editing `target` or `treatment_key` of `v27` changes no digest).

A scenario that names fixtures is shown on those fixtures. Further fixtures may be added, but they do
not replace the named ones.
