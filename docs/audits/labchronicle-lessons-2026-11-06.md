# Lessons from LabChronicle's schema work for the experiment description (6 November 2026)

- **Status:** Read-only audit, owner request of 6 November 2026. Evidence and history, not a
  statement of current implementation status. Nothing was changed in either repository audited.
- **Tracking:** [RFC #1](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1); draft PR #3
  (branch `claude/stage0-spec`).
- **LabChronicle audited at:** `/home/user/labchronicle`, commit
  `a341912ee9eea54c824ba42eda029d7c2dd1b2b3` (abbreviated `a341912` below). All `file:line`
  citations refer to that commit. Paths are relative to its root.
- **Spec audited at:** PR #3 head `c8f2913` (`docs/experiment-v1.md`, ADR 0001, fixtures,
  conformance plan). Another agent was revising that branch while this audit was written. Its
  uncommitted revision applies the owner decisions (`display_name`, NFC, immutable IDs, no
  `retired_repeats`, transition fixtures `t01`/`t02`). Where a recommendation below is already
  covered by that revision, it says "(in-flight)". **Check those items again once the revision is
  pushed**, because uncommitted text can change.
- **Owner decisions taken as given:** TOML. IDs are immutable once confirmed. A separate, mutable
  `display_name` is used only for display and is unique within its kind. Aliases are
  user-confirmed only. Reduced v1. NFC identities. Header names are exact and case-sensitive.
  Drafts stay internal to preprocessing. No per-FOV overrides. No brick routing. Calibration
  stays in `calibration.csv`. No recommendation below overrides any of these. A recommendation
  that touches one is listed as an owner question.
- **Not run:** the LabChronicle test suite. Its imports need `ipywidgets` (`src/labchronicle/__init__.py:8`
  imports `custom_widgets`), and `ipywidgets` is not installed here. The bugs in §3 were found by
  reading the code. The arithmetic behind B1 was reproduced in plain Python. No bug was executed
  through the LabChronicle modules.

## 1. What LabChronicle's schema models

| Aspect | What LabChronicle does | Evidence |
|---|---|---|
| Entities | Lab resources: antibodies, plasmids, dyes, siRNAs, animal models, small molecules, cell lines and microscopes. **Grouped** resources keep one target file with a list of entries (an antibody target with several clones). **Flat** resources keep one record per file. Experiments are a separate YAML (`metadata.yaml`) with conditions and repeats. | `src/labchronicle/schemas.py:12-104`; `docs/lab_database/Schema_Driven_Editors.md:164-175`; `docs/experiment_init/Experiment_Folder_Migrations.md:17-21` |
| ID policy (resources) | Each resource has an `id_key`, an `id_prefix` and an `id_width` (for example `Antibody_ID`, `Ab`, 3 → `Ab001`). IDs are generated as the highest existing number + 1. Missing IDs are backfilled from a preview, then confirmed before writing. The editor keeps an existing ID across edits. | `schemas.py:21-23`; `Schema_Driven_Editors.md:108,233-240`; `src/labchronicle/lab_database/schema_forms/id_management.py:39-96`; `schema_forms/editor.py:140-161` |
| ID policy (experiments) | A repeat gets a stable code (`R001`, or `VR001` for a validation repeat) that is kept apart from its editable date. The folder name is derived as `<date>_<code>`. | `Experiment_Folder_Migrations.md:3-9`; `src/labchronicle/experiment_migration.py:192-213,292-302` |
| Display names | Each resource has a `name_key` (for example `antibody_name`), and the record name is also the file name. In the merged database a remote record is keyed `Name [Source]`. Record names are unique ignoring case. | `schemas.py:18`; `database_utils.py:30-40`; `schema_forms/editor.py:719-724` |
| Controlled vocabularies | `vocab_registry` maps each vocabulary name to a YAML file of `{id, label, description}` terms. The **ID is stored** and the label is displayed. Fields reference a vocabulary with `vocab:`, and `allowed_values` is the inline fallback. | `Schema_Driven_Editors.md:61-63,124-125,138-150`; `tests/fixtures/policies/vocab/*.yaml`; `schema_forms/parser.py:302-347,459-466` |
| Field identity | Each rule has a `path` and a `field_id`, described as a "stable semantic identifier". A field-definition vocabulary gives each field a label and a description. | `Schema_Driven_Editors.md:113-126`; `tests/fixtures/policies/vocab/field_definitions.yaml` |
| Versioning | `schema_version.yaml` has three independent values: `database_schema_version`, `schema_format_version` and `minimum_labchronicle_version`. Each rule file also has a `version: 1` key. The experiment filesystem manifest has `manifest_version`. | `database_utils.py:128-146`; `tests/test_schema_ownership.py:60-81`; `Schema_Driven_Editors.md:47`; `experiment_migration.py:32,683` |
| Migrations | **Database:** copy the policies from the template, add `schema_path` and confirm that the editor reports `policy-rules` rather than `fallback-template` (`Database_Schema_Ownership.md:33-44`). **Experiment folders:** a preview-first, journaled migration with backups, rollback, a lock, and a refusal to roll back when `metadata.yaml` has changed since. | `docs/lab_database/Database_Schema_Ownership.md:33-44`; `Experiment_Folder_Migrations.md:23-82` |
| Ownership | The engine (parsing, widgets, validation, ID generation) lives in the application. Each lab's contract (policies, vocabularies, versions) lives in its own database repository, created from the `LabChronicle_Database` template. The package deliberately does not ship production policies, "so a software upgrade cannot silently change a laboratory's database contract". A test enforces this. | `Database_Schema_Ownership.md:6-27`; `Schema_Driven_Editors.md:259-261`; `tests/test_schema_ownership.py:14-19` |
| Validation layers | (1) Per-field type, enum, pattern and range checks (`validation.py`). (2) A source audit: format and uniqueness of IDs across collections, and unknown box references (`audit.py`). (3) Optimistic concurrency in the editor, which refuses to save a field that changed elsewhere. Validation runs only when started explicitly and makes no network calls. | `schema_forms/validation.py:64-131`; `schema_forms/audit.py:39-165`; `schema_forms/editor.py:216,690-707`; `tests/test_schema_driven_workflows.py:397-413`; `Schema_Driven_Editors.md:233-236` |
| Editor and form generation | CRUD forms are generated from the active source's policy: required fields are bold and the help text starts with "*Mandatory." There are custom widgets and editor extensions (for example an Addgene lookup). Delete takes two steps. The normalizer accepts four schema formats. | `Schema_Driven_Editors.md:1-38,131-136,152-231`; `tests/test_schema_forms.py`, `tests/test_schema_policy_forms.py` |
| Unknown fields | Kept on save and ignored by validation: "deploying a narrower schema must not erase metadata". | `Schema_Driven_Editors.md:177-189`; `tests/test_schema_policy_forms.py:159-218`; `validation.py:127-131` |
| Provenance | Each merged record keeps `source_database`. The experiment export writes a manifest of exported configurations (`source_database`, `selected_subentries`). Migrations write journals and backups under `.labchronicle/`. | `schema_utils.py:318-327`; `tests/test_experiment_source_schemas.py:228-248`; `Experiment_Folder_Migrations.md:47-63` |

## 2. Lessons that transfer

Each lesson gives the LabChronicle evidence, the change proposed for PR #3, and whether it
touches an owner decision.

**L1. Keep the stored ID separate from the displayed label, and never let a reference resolve
through the label.** LabChronicle stores vocabulary IDs and displays their labels
(`Schema_Driven_Editors.md:148-150`), and it separates `R001` from the editable date. But its
experiment metadata references reagents by display key: `{"target": "TP53 [Remote]", "value":
"R1"}` (`tests/test_experiment_source_schemas.py:171-182`), with sub-entries joined by a `" -|-|- "`
sentinel (`custom_widgets.py:521`). A rename is an unlink followed by a recreate
(`lab_database/source_access.py:452-462`), so those references dangle after any rename.
*Proposal:* the owner decision already covers this (in-flight §4.8 forbids `display_name` in
joins and references). Two further changes:
- Add one sentence to §4.8: a consumer MUST NOT accept a `display_name` where an ID is expected,
  even when the two strings are equal.
- Add an invalid fixture where `reference` names a condition's `display_name` instead of its ID
  (expected `E_REFERENCE_UNKNOWN`).

*Conflict:* none.

**L2. Never auto-allocate or repair IDs, and keep an ID registry so that no ID is ever reused.**
LabChronicle generates IDs as highest + 1 (`id_management.py:69-83`; `editor.py:151-161`;
`id_backfill.py:79-93`). Deleting the highest record therefore makes its ID available again,
because there are no tombstones. "Invalid-format" IDs are *replaced* rather than reported
(B2), and repeat codes are silently upper-cased and renumbered (B11). These are the failure modes
ADR 0001 gives for rejecting `R001`.
*Proposal:* add LabChronicle as supporting evidence under ADR 0001 "Auto-numbered repeat IDs". In
§7, state that no reader or writer ever repairs, re-cases or renumbers an ID: a malformed ID is
refused with its code.
*Conflict:* none. There is an **open question (Q1)**, though. The in-flight revision drops
`retired_repeats` and keeps retired IDs only in "manifest history" (in-flight §10). LabChronicle
shows that without a durable tombstone, reuse goes undetected. If the run manifest is lost, or a
new output folder is started, nothing prevents reuse.

**L3. Refuse what cannot be resolved; never degrade to free text.** When a vocabulary file is
missing, LabChronicle only logs a warning (`parser.py:340-347`). The field then has no
`allowed_values` and accepts any text (`parser.py:459-466`).
*Proposal:* keep v1 enumerations inline in the normative text (only `representation` today) with
no external vocabulary files. Add to §2 that a reader MUST NOT obtain any enumeration from outside
the reader at run time. The supported set is a constant tested by the fixtures.
*Conflict:* none.

**L4. Absent or unknown versions are refused, never assumed, and compatibility is decided offline.**
LabChronicle reads a missing version as `"0.0.1"` (`git_utils.py:920-923,946`). It judges
compatibility by comparing the local version with the latest template version, fetched from
GitHub (`git_utils.py:925-956`). It never enforces `minimum_labchronicle_version`: the value is
loaded (`database_utils.py:128-146`) and asserted only in a test (`tests/test_schema_ownership.py:63`).
§7 of the spec is already correct (missing version refused, no best-effort reading).
*Proposal:* add one row to conformance-plan §2: the reader's supported-version set is a code
constant, it is checked without network access, and `i11` (missing version) is never mapped to a
default.
*Conflict:* none.

**L5. A closed set of fields is right for a confirmation file.** LabChronicle keeps unknown keys
on purpose, because it merges several sources with lab-specific extensions. The cost is that a misspelt
field validates cleanly and lives on forever (`validation.py:127-131` only checks fields it
knows). The spec's `E_UNKNOWN_FIELD`, with no extension namespace, is the correct choice for
`morphobricks.toml`, which records confirmations, not an open catalogue.
*Proposal:* none (already in §2.4 and fixtures `i16`-`i18`). Cite this as evidence in the ADR.
*Conflict:* none.

**L6. The contract has one owner, and the reader pins it.** LabChronicle's separation of engine
from policy, with a test that the package does not ship policies (`test_schema_ownership.py:14-19`),
matches conformance-plan §1 (preprocessing pins the Spec by SHA).
*Proposal:* add a conformance test. The vendored fixture tree in preprocessing must hash to the
tree at the pinned Spec SHA, so a local edit of a fixture fails CI. Also state that preprocessing
MUST NOT carry a fallback copy of the rules (LabChronicle's `fallback-template` path,
`Database_Schema_Ownership.md:43-44`, is what that rule prevents).
*Conflict:* none.

**L7. Publication is a compare-and-swap on the base file.** LabChronicle's editor refuses a save
when a field changed elsewhere after the record was opened (`editor.py:216,690-707`;
`tests/test_schema_driven_workflows.py:397-413`). Its folder-migration rollback refuses when
`metadata.yaml` has changed since (`Experiment_Folder_Migrations.md:81-82`). The spec says
publication happens "under the output folder's lock, atomically" (§2.1, §10). A lock prevents
two concurrent writes. It does not stop a stale draft from replacing a newer published file.
*Proposal (§10, and a scenario in conformance §3):* each draft records the SHA-256 of the
published file it was derived from. Publication MUST refuse when the current published SHA
differs (new code, for example `R_PUBLISHED_FILE_CHANGED`). Scenario: two drafts from one base,
one published, then the second refused.
*Conflict:* none. Drafts stay internal to preprocessing.

**L8. Confirmation dates are user facts, never defaults.** LabChronicle evaluates
`datetime.now()` when the module is imported and uses that value as the default date
(`schemas.py:208,211,235,237,256,261,281,284`). Its policies also have a dynamic `__TODAY__`
default (`Schema_Driven_Editors.md:123`; `parser.py:430`).
*Proposal (§4.4 and §10):* `confirmed_on` is the date of the user's confirmation action. A writer
MUST NOT default it from the write time. A reconciliation that does not reopen N35 MUST keep it
byte-identical. Add the second rule as an assertion to scenario P07 or P15.
*Conflict:* none.

**L9. Case variants are ambiguous, so refuse collisions and resolve exactly.** LabChronicle
resolves records and fields by case-folded fallback, taking the first match
(`schema_utils.py:308-314`; `parser.py:884-898`). Its own field vocabulary contains `siRNA_ID`
and `SiRNA_ID` as distinct IDs (`field_definitions.yaml:224-229`). This supports §3.3: exact
resolution plus `E_ID_CASE_COLLISION`. *Proposal:* none for IDs.
*Open question (Q2):* in-flight §4.8 makes `display_name` unique "equal after NFC", which is case
sensitive. LabChronicle enforces display-name uniqueness ignoring case (`editor.py:719-724`).
Should `Control` and `control` be allowed as two display names of one kind? The owner's
"unique within kind" does not say.

**L10. Validate a draft completely, and report every error with its path.** LabChronicle's audit
reports every issue with collection, record and entry (`audit.py:15-21`). The spec's phased
reporting with table paths (§6) is stronger. *Proposal:* none.

**L11. NFC: refuse or normalize?** LabChronicle does no Unicode normalization at all. Its
case-folded lookups would still treat NFC `é` and NFD `e + U+0301` as different, so two records
can look identical. The in-flight §3.3 normalizes every identity to NFC on read and refuses
collisions after NFC (`E_ID_NFC_COLLISION`).
*Open question (Q3):* "NFC identities" could also mean that a file containing a non-NFC
identity is refused (`E_ID_NOT_NFC`), because writers MUST emit NFC. Under that reading the
normalize step disappears from the reader. Separately, preprocessing should refuse two on-disk
folders whose names are equal after NFC (an `R_*` code), because Linux file systems allow both
spellings side by side. Do not choose for the owner.

**L12. Free-text fields that people will group on are identities in disguise.** LabChronicle's
`organism` is free text in one resource (`schemas.py:163`) and drawn from vocabularies in others.
Its `sex` options differ between animal models (`female,male,mixed,unknown`, `schemas.py:117`)
and cell lines (`female,male,unknown`, `schemas.py:164`). Free-text groupings drift in exactly
this way. The spec's `treatment_key` is meant for the "same perturbation under different
backgrounds" (§4.2), which is a grouping key.
*Open question (Q4):* either `treatment_key` is an identity (Label rules plus a case-collision
scope, with the same immutability), or §4.2 states that consumers MUST NOT group, join or pair on
it. The same question applies to `target`.

## 3. What LabChronicle got wrong, or what does not transfer

### 3.1 Defects found (evidence at `a341912`)

| # | Defect | Evidence | Lesson for the spec |
|---|---|---|---|
| B1 | **ID width overflow.** The generator formats `f"{prefix}{n:0{width}d}"`. The validator requires exactly `width` digits. At n = 1000 with width 3, the generated `Ab1000` fails its own pattern, is then planned for replacement, and the next allocation can produce it again. Arithmetic reproduced: `Ab1000` does not match `^Ab\d{3}$`. | `id_management.py:53,80`; `editor.py:153,160`; `id_backfill.py:74,93` | Auto-allocation brings invariants of its own. v1 has no allocator, so keep it that way. |
| B2 | **Malformed IDs are replaced, not reported.** An existing ID such as `cl001` (wrong case) is planned as "invalid format" and gets a new number. That is a silent identity change. | `id_management.py:63-67`; `id_backfill.py:205-215` | Refuse a malformed ID (L2). |
| B3 | **A stale plan is applied by index.** The backfill plan stores `entry_index`, and apply writes `entries[index][id_key]` without checking `old_id` or the name. The plan is made in one click and applied in another. | `id_management.py:99-121`; `backfill_workflow.py:105,122` | Apply operations must check the state they were planned on (L7). |
| B4 | **Legacy paths still use the deprecated static schema.** `id_backfill.backfill_ids_schema` and `core.py` read `RESOURCE_SCHEMAS`. The documentation says ID backfill uses the active source's policy (true for the newer path only). Both are still exported. | `id_backfill.py:11,170`; `core.py:11,17,49,79-87`; `lab_database/__init__.py:7`; `Schema_Driven_Editors.md:238-240` | Exactly one reader of the rules (L6). |
| B5 | **Default dates frozen at import time.** | `schemas.py:208,211,235,237,256,261,281,284` | L8. |
| B6 | **Duplicate key in a Python literal.** The siRNA template declares `'location'` twice, and the second silently wins. | `schemas.py:254,257` | The same failure class as YAML duplicate keys. Supports TOML's refusal of duplicates (ADR, fixtures `i03`-`i06`). |
| B7 | **Field IDs that differ only by case**, with the labels apparently swapped (`siRNA_ID` labelled "SiRNA ID", `SiRNA_ID` labelled "siRNA ID"). | `tests/fixtures/policies/vocab/field_definitions.yaml:224-229` | L9. |
| B8 | **First-match lookup ignoring case.** | `schema_utils.py:308-314`; `parser.py:884-898` | L9. |
| B9 | **A missing vocabulary turns an enum into free text** (warning only). | `parser.py:340-347,459-466` | L3. |
| B10 | **Version guessed and minimum not enforced.** A missing version reads as `"0.0.1"`, compatibility depends on the network, and `minimum_labchronicle_version` is never checked. | `git_utils.py:920-956`; `database_utils.py:128-146` | L4. |
| B11 | **Repeat codes re-cased and renumbered.** `ensure_repeat_identities` upper-cases codes and keys, and gives a duplicate code the next free number, so the result depends on dict order. A missing code falls back to `R000`. | `experiment_migration.py:39-40,233-242,262-271,289` | Never repair identities (L2). |
| B12 | **The editor injects an undeclared field** (`version: "1.0"`) into every saved record and entry. | `editor.py:635,717` | A writer emits only declared fields (spec §9.1 already). |
| B13 | **The experiment metadata format is undocumented.** The reference page is an empty stub. | `docs/experiment_init/Experiment_Metadata_Format.md:7-15` | The spec's normative text plus fixtures is the right answer. LabChronicle has no stable experiment schema to reference (see §4.3). |
| B14 | **A typo frozen into an ID**: `amplification_planed`, displayed as "Amplification planned". | `schemas.py:237`; `field_definitions.yaml:11-13` | Not a defect of the policy: it is the immutable-ID-plus-display-label policy working. Use it as a worked example for `display_name`. |

Also noted, not a defect: `id_backfill.py:103` annotates with `Tuple`, which is not imported (`:6`).
It is harmless only because of `from __future__ import annotations`.

### 3.2 Design choices that do not transfer

- **Unknown-field preservation** (`Schema_Driven_Editors.md:177-189`). It suits a multi-source
  catalogue that labs extend. It does not suit a file of confirmations. The spec's closed fields
  and refusal of unknown fields are correct (L5).
- **Several schema formats with a fallback template** (`Schema_Driven_Editors.md:152-159`;
  `Database_Schema_Ownership.md:43-44`). One contract only. A file the reader cannot read is
  refused, not read through a compatibility path.
- **Per-lab customization of the schema** (`Database_Schema_Ownership.md:19-27`). A lab
  customizing its reagent fields is fine. A lab customizing what a biological repeat means is
  not: MorphoBricks needs one contract across labs.
- **Fuzzy name resolution** (`schema_utils.py:19-55,142-175`: synonyms, stripping punctuation,
  case folding). It contradicts "identities are never parsed" and "exact resolution".
- **YAML.** Already rejected in ADR 0001. B6 shows the duplicate-key class even in Python literals.
- **Generated forms from a machine schema.** Useful for LabChronicle's open CRUD. ADR 0001 rejects
  a machine schema for v1 because the cross-reference, case and graph rules cannot be expressed
  in one. A preprocessing confirmation UI should be built from the normative tables, and its
  error texts should cite the `E_*` codes. Revisit only if a second writer appears.

## 4. Reuse opportunities

### 4.1 Shared vocabularies

LabChronicle's vocabularies are not yet suitable as shared identities. `species.yaml` uses
common names as IDs (`Mouse`, `Human`) plus an `Other` catch-all (`species.yaml:1-25`). Application
IDs contain spaces and mixed case (`antibody_applications.yaml:5`). Dyes and fluorophores are
records with lab-local IDs (`Dye_ID`, `schemas.py:37-48`), not a vocabulary. Reduced v1 has no
species, cell-line, antibody or fluorophore fields. Channel IDs are per-experiment canonical
tokens, and `header_names` is user-confirmed evidence, never a lookup into a vocabulary. **No
vocabulary should enter v1.**

If a later schema version adds stain or sample descriptors, use external stable accessions, not
LabChronicle's lab-local IDs. Candidates: NCBI Taxonomy for species, Cellosaurus `CVCL_` for cell
lines, RRID for antibodies (LabChronicle already has an `rrid` field, `schemas.py:128`), and
FPbase for fluorescent proteins. Any such field would need a new `schema_version` and would be
descriptive only, never an identity.

### 4.2 A shared ID policy across lab tools

Both tools would benefit from a short cross-tool identity note. The rules would be: IDs are
opaque text; immutable once confirmed; compared exactly after NFC; case collisions refused within
a scope; never repaired, re-cased or renumbered; never reused (tombstoned); display names kept
separate and never used for joins. The spec's §3 is the natural source text.

LabChronicle currently violates several of these rules (B2, B8, B11). Fixing them belongs to
LabChronicle's owners. This audit changed nothing there. A note like this could live in this
repository as an informative document after v1 is accepted. It is not a PR #3 change.

### 4.3 Referencing LabChronicle records from `morphobricks.toml`

LabChronicle has no experiment ID. An experiment is identified by `experiment_name` and its
folder, and its repeats by codes `R001`/`VR001` that are unique only within that experiment
(`experiment_migration.py:216-277`; B13). v1 has closed fields with no extension namespace, and
`experiment` is a forbidden field (§4.7). A LabChronicle link inside `morphobricks.toml` would
therefore need a new `schema_version`. It would also collide with the reduced-v1 decision.

**Recommendation:** record LabChronicle provenance in the **run manifest** as an optional,
user-supplied preprocessing input, not in `morphobricks.toml`. Record repository URL, commit SHA,
experiment path and, per canonical repeat, the LabChronicle repeat code. It MUST be excluded from
every identity, pairing and cache key. A mapping from `R001` to a MorphoBricks canonical repeat ID
MUST be user-confirmed: equal strings are not evidence, because both namespaces use `R001`-style
labels.

If the owner prefers the description file, a v2 optional `[provenance]` table would need the same
exclusions, plus omission from the section digests (§9.3). This is **open question Q5**.

## 5. Recommended edits to PR #3 (ranked) and owner questions

| Rank | Edit | Where |
|---|---|---|
| 1 | **Publish only from the current base.** A draft records the SHA-256 of the published file it was derived from. Publication refuses when that file has since changed (new `R_*` code). Add a scenario with two drafts from one base. (L7) | experiment-v1 §10 and §8 `R_*` table; conformance-plan §3 |
| 2 | **No repair, re-casing or renumbering of IDs**, ever. A malformed or colliding ID is refused with its code, never rewritten. Cite LabChronicle B1, B2 and B11 as evidence in the ADR's rejection of auto-numbered IDs. (L2) | experiment-v1 §3.3/§7; ADR 0001 "Auto-numbered repeat IDs" |
| 3 | **`confirmed_on` is a user fact.** It is never defaulted from the write time and is kept byte-identical by a reconciliation that does not reopen N35. Add the second rule as an assertion to P07/P15. (L8) | experiment-v1 §4.4, §10; conformance-plan §3 |
| 4 | **A display name is never an ID substitute.** Add one sentence to §4.8, plus an invalid fixture where `reference` names a `display_name` (expect `E_REFERENCE_UNKNOWN`). (L1) | experiment-v1 §4.8; `fixtures/invalid/`; fixtures/README |
| 5 | **Pin-integrity and offline version tests.** The vendored fixture tree must hash-match the pinned Spec SHA. The supported versions are a code constant, with no network access and no default for a missing version. The reader carries no fallback copy of the rules. (L4, L6) | conformance-plan §1/§2 |
| 6 | **No external enumerations at run time.** Enumerations live in the normative text, and any future vocabulary is refused when unresolved. (L3) | experiment-v1 §2 |
| 7 | **Record LabChronicle and other lab-tool provenance in the run manifest only**, excluded from identity and cache keys, with any repeat-code mapping user-confirmed. (§4.3) | experiment-v1 §9.3 (one sentence) or roadmap Stage 1 note |

**Open owner questions**

- **Q1. Durable tombstones.** With `retired_repeats` removed (in-flight), where is the registry of
  retired IDs that guarantees "never reused" when the run manifest is lost or a new output folder
  is started? Options: keep `retired_repeats` in the file, or accept the risk and document it.
- **Q2. Display-name collisions and case.** Is `display_name` unique *ignoring case* within a kind
  (LabChronicle's choice) or only after NFC (in-flight)?
- **Q3. NFC policy.** Should a reader normalize non-NFC identities on read (in-flight), or refuse a
  file containing them (`E_ID_NOT_NFC`)? In either case, should preprocessing refuse two folders
  equal after NFC?
- **Q4. `treatment_key` and `target`.** Are they grouping identities (then Label rules, a
  case-collision scope and immutability apply) or strictly descriptive (then §4.2 says consumers
  MUST NOT group, join or pair on them)?
- **Q5. LabChronicle provenance.** Run manifest only (recommended), or a future-version
  `[provenance]` table in `morphobricks.toml`?
