# ADR 0001: experiment description v1 (`morphobricks.toml`)

- **Status:** Accepted (owner decisions of 6 and 7 November 2026, five rounds, including the later
  refinement D5). Specification only; nothing is implemented. The fixed-SHA consumer audit
  (roadmap S0.1) is done ([PR #5](https://github.com/CellMigrationLab/MorphoBricks-Spec/pull/5)); the
  third round below answers its questions; the fourth round (FR1, FR2) separates condition and
  technical-repeat IDs from their folder labels and states the limit of CSV byte-identity; the
  fifth round (7 November 2026, SQ2, SQ6-SQ8) settles the Stage 1 design questions.
- **Tracking:** [RFC #1](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1);
  [roadmap §2 and §5 Stage 0](../roadmap.md);
  [feasibility audit](../audits/rfc1-feasibility-2026-11-05.md);
  [addendum](../audits/rfc1-feasibility-2026-11-05.md#addendum-after-chatgpts-response-5-november-2026) (the addendum wins where they differ).
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
   name when pairing is trivial); never changes automatically on rename/reorder. (The clause
   "renames are explicit recorded migrations" is superseded by D5: IDs never change.)
3. **Channel aliases: user-confirmed only**; canonical token + optional display label + confirmed
   header evidence; never inferred from pixels or name similarity.
4. **Scope: reduced v1**: conditions, canonical channels, repeat pairing, technical-repeat
   acquisition layouts, mask semantics (`instances` vs `binary`, source type, optional
   source-channel provenance), optional primary `condition.reference` (acyclic); heterogeneity
   representable in the schema but Stage 1 runtime refuses it until Stage 3.

### Earlier owner decisions kept

5. Calibration stays in `calibration.csv` (not copied).
6. `experiment_design.csv` stays a deterministic derived compatibility output.
7. N35 comparability confirmation kept; reopening is narrowed by D6.
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
- Confirmed IDs are immutable (D5). Friendly names are `display_name`; a mistyped ID is fixed
  only by a recorded re-confirmation in the run manifest, not in the file.
- Validation is split into three boundaries with distinct error namespaces: the spec (syntax and
  semantics, `E_*`), preprocessing (physical files, `R_*`) and the analysis layer (applicability,
  `A_*`).
- No machine schema (JSON Schema) in Stage 0: cross-references, case rules and graph rules are
  not expressible in it, and TOML has no standard schema language. The normative prose and the
  fixtures with exact codes are the contract.

### Owner decisions on the Stage 0 open questions (6 November 2026, all accepted)

| # | Accepted decision | Rejected alternative | Spec | Fixtures |
|---|---|---|---|---|
| D1 | Keep optional `target` and `treatment_key` on conditions: plain strings, no runtime use until Stage 2 (refined by Q4: descriptive only) | Drop them until a consumer exists | §4.2 | `v01`, `v10`, `v21`, `v27`, `i71` |
| D2 | Refuse channel IDs equal to a MorphoRelate compartment name (list in §3.2, `E_ID_RESERVED`) | Allow them and rely on a column-prefix convention | §3.2 | `i61` |
| D3 | A declared but unused channel is the warning `W_UNUSED_CHANNEL`; the file is valid | Error `E_UNUSED_CHANNEL` | §4.3 | `v22` |
| D4 | Refuse a repeat ID equal to another repeat's source folder name (`E_REPEAT_ID_SHADOWS_SOURCE`) | Allow it and resolve by context | §4.4 | `i75` |
| D5 | **Replaces** the earlier "recorded renames" decision: IDs of repeats, conditions and channels are immutable once confirmed; each has a mutable `display_name` used only for display (never identity, joins, pairing or cache keys; changing it invalidates nothing); display names are unique per kind (`E_DISPLAY_NAME_COLLISION`; comparison refined by Q2); an attempted ID change is `R_CONFIRMED_ID_CHANGED`; a mistyped ID is fixed only by a recorded re-confirmation | Renamable IDs with a `retired_repeats` table (old ID → new ID): it keeps identity mutable, needs tombstones, chain and reuse rules, and churns `biological_repeat`, FOV identities and caches | §4.6, §4.8 | `v16`, `i53`, `i76`, `i77`, `i82`, `t01`, `t02` (reuse: Q1) |
| D6 | N35 is reopened only when channels, layout or grouping change; new FOVs with the same confirmed layout do not reopen it (recorded, reported) | Reopen on any new image | §10 | P07, P15 |
| D7 | Identities are Unicode NFC. **Refined by Q3: a reader refuses a non-NFC identity (`E_ID_NOT_NFC`); it does not normalize, so `E_ID_NFC_COLLISION` no longer exists.** IDs are never otherwise transformed | Compare raw code points (look-alike duplicates); or NFKC / case folding (changes meaning) | §3.3 | `v23`, `i78`, `i83`-`i85` |
| D8 | **Superseded by AQ6 (third round).** Was: refuse RGB (interleaved colour) images in v1 (`R_RGB_NOT_SUPPORTED`, now removed) | Treat RGB as three channels | §4.4b | P13, P23, P24 |
| D9 | Header names match exactly and case-sensitively; anything else needs a user-confirmed alias | Case-insensitive or similarity matching | §4.3 | `v11`, P03 |
| D10 | Refuse a mask declared `binary` with more than two distinct values (`R_MASK_CONTRADICTS_REPRESENTATION`); declare `instances` instead | Accept and threshold | §4.5 | P05 |
| D11 | Drafts are internal to preprocessing; `RunInputs` reads only confirmed, published files and refuses drafts (`A_DRAFT_REFUSED`) | Let consumers read drafts | §12 | `i37`, P14 |

### Owner decisions of 6 November 2026, second round (LabChronicle audit, all accepted)

Evidence: the LabChronicle lessons audit (`docs/audits/labchronicle-lessons-2026-11-06.md` on
branch `claude/labchronicle-lessons`, PR #4; not yet on this branch, so not linked), an audit of
LabChronicle at `a341912`. LabChronicle is evidence of failure modes, not a dependency. Fixture
numbers refer to `fixtures/`.

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| Q1 | An append-only `used_ids` list per kind (conditions, channels, repeats; technical repeats added by FR1): IDs only, no mapping. Every declared ID MUST be listed. Publication refuses reusing a listed ID (`R_USED_ID_REUSED`) and refuses dropping one (`R_USED_ID_DROPPED`); removing an entity keeps its ID listed. The guarantee covers the lineage of published files in one output folder; a new output folder starts a new lineage and only the run manifest history spans folders | Keep retired IDs only in the manifest history (lost with the manifest or a new output folder, so reuse goes undetected); or `retired_repeats` with old-to-new mapping (already rejected, D5: tombstones, chains, mapping rules) | §4.9, §6, §8 | `v25`, `t03`, `t04`, `i92`-`i97`; P19, P20 |
| Q2 | `display_name` uniqueness within a kind is decided after Unicode case folding and NFC (`NFC(casefold(NFC(x)))`); names are kept as typed and never normalized | NFC-only (case-sensitive): `Control` and `control` would be two names that look the same in every report | §4.8 | `v24`, `i53`, `i76`, `i77`, `i86`-`i88` |
| Q3 | A reader REFUSES a non-NFC identity (`E_ID_NOT_NFC`); the writer always writes NFC; readers never transform identities. Preprocessing likewise refuses a non-NFC folder label (`R_FOLDER_NOT_NFC`, a consequence, not a separate choice: a folder label is a source identity) | Normalize to NFC on read (an identity would be silently changed; the written file and the read model differ; a reader bug becomes an identity change) | §3.3 | `v23`, `i78`, `i83`-`i85`; P21 |
| Q4 | `treatment_key` and `target` are descriptive only: never used for grouping, joins, pairing or cache keys; omitted from every digest | Make them identities (Label rules, case-collision scope, immutability): they are free text people vary, and a wrong grouping would pool biological repeats silently | §4.2a, §9.3 | `v27`, `v21`; `i71` |
| Q5 | LabChronicle (and other lab-tool) links live in the run manifest's provenance only (a preprocessing input), never in `morphobricks.toml`; any repeat-code mapping is user-confirmed; excluded from identity, pairing and cache keys | A v2 optional `[provenance]` table in the file (new `schema_version`, a second place for provenance, digest exclusions needed) | §4.7, §9.3 | `i99` |

#### Audit edits applied (A1-A5)

| # | Rule (normative) | Rejected behaviour (evidence: LabChronicle at `a341912`) | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| A1 | Publish only if the SHA-256 of the currently published file equals the draft's recorded base (`R_PUBLISHED_FILE_CHANGED`; no base: `R_DRAFT_BASE_MISSING`) | A lock alone: a stale draft silently replaces a newer file. LabChronicle applies a backfill plan by list index with no check of the state it was planned on (B3) and refuses a save only inside its editor (L7) | §10 | P17, P18 (fixtures `v01`, `v21`, `v16`) |
| A2 | Never repair, re-case, pad or renumber an ID; a malformed ID is refused with its code | Repair: LabChronicle's `Ab1000` overflows its own 3-digit width, so the validator rejects what the generator wrote (B1); a malformed ID such as `cl001` is silently replaced by a new number (B2); repeat codes are upper-cased and renumbered, order-dependently (B11). This also confirms the rejection of auto-numbered IDs below | §3.3 | `v26`, `i48`-`i52`, `i55`, `i95` |
| A3 | `confirmed_on` is a user fact: never defaulted, kept byte-identical across a reconciliation that does not reopen N35 (`R_CONFIRMED_ON_CHANGED`) | Defaults from the clock: LabChronicle evaluates `datetime.now()` once at import and uses it as the default date (B5) | §4.4a, §10 | `i98`, `t05`; P07, P15, P22 |
| A4 | `display_name` never substitutes for an ID, even when unique or equal | Resolving references through the display key: LabChronicle references reagents as `"TP53 [Remote]"` and a rename is an unlink plus recreate, so references dangle (L1) | §4.8 | `i89`-`i91` |
| A5 | The vendored fixture tree MUST match the pinned SHA's tree hash; the supported-version check is a code constant, offline, with no default for a missing version; the reader has no fallback copy of the rules | A `fallback-template` rules path, a missing version read as `0.0.1`, and a compatibility check fetched from GitHub with `minimum_labchronicle_version` never enforced (B10) | §2, §7; [conformance plan](../conformance-plan.md) §1-§2 | `i09`-`i11`; CI tests |

Also stated: expected `experiment_design.csv` outputs are deferred to Stage 1 (golden files).

### Owner decisions of 6 November 2026, third round (S0.1 consumer audit, all accepted)

Evidence: the S0.1 fixed-SHA consumer audit (`docs/audits/s01-consumer-audit-2026-11-06.md` on
branch `claude/s01-consumer-audit`, PR #5; not on this branch, so not linked), section 10, owner
questions Q1-Q13. They are numbered **AQ1-AQ13** here so that they do not collide with the Q1-Q5 of
the second round above. Where an AQ refines an earlier decision, the earlier row stays as history
and the normative text states the result. Fixture numbers refer to `fixtures/`; P-numbers to the
[conformance plan](../conformance-plan.md).

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| AQ1 | Adding a member folder to an existing repeat or condition is allowed and is not `R_CONFIRMED_ID_CHANGED`. Only **removing or reassigning** existing members (or, for a channel, positions and aliases) is a changed entity, and then only with a recorded confirmation. N35 reopens only on a layout, channel or grouping change (an added member is a grouping change) | The literal reading of the old text (§4.6 c): any change of an entity's member set is an ID change, so every legitimate new folder of the reconciliation flow would need a re-confirmation | §4.6, §10 | `t03` (corrected), `t06`, `t07`, `t08`; P07, P15 |
| AQ2 | A case-only ID correction (`ACTIN` to `Actin`) cannot be published in place: the retired spelling stays in `used_ids` and collides. It needs a new, non-colliding ID with a recorded re-confirmation; `display_name` fixes the appearance. A publication reports **every** applicable `R_*` code as a set | Dropping the retired spelling from `used_ids` to allow the re-cased ID (breaks "never reused" and the append-only registry); reporting only the first code | §4.6, §4.9, §8 | `t02`, `t09`, `i95`; P16 |
| AQ3 | `target` stays descriptive. MorphoCoverage may only **prefill** its own reagent grouping from it; the user confirms the grouping inside MorphoCoverage and only that confirmed grouping is analysed | MorphoCoverage reading `target` from the file as its reagent grouping (unconfirmed, and a wrong grouping would pool conditions silently); or making `target` an identity | §4.2a | `v27`; P31 |
| AQ4 | The MorphoRelate reserved column names (`condition`, `biological_repeat`, `repeat`, `technical_repeat`, `position_id`, `image_file`, `image_path`, `mask_file`, `patch_file`, `patch_id`, `label_id`, `z`, `z0`, `z1`, `c`, `t`; MorphoRelate v0.1.1 `registry/_expand.py:41-59`) join the compartment names in **one** reserved list for channel and mask IDs (case-folded) | Leaving them to an `A_*` refusal by MorphoRelate: valid v1 files would then name channels no brick can export | §3.2 | `i61`, `i59`, `i107`-`i109`, `v32` |
| AQ5 | The canonical repeat ID is **added** next to the FOV key as `repeat_group`; the key keeps the source folder label in `biological_repeat`, so IDs, caches and exports are unchanged; grouping and pairing use the canonical ID | Replacing the source label by the canonical ID in the key: it changes FOV and patch identities, scaling keys, caches and exports in every brick at once, and erases the provenance | §3.4 | `v03`, `v30`; P25 |
| AQ6 | **Supersedes D8.** RGB is an accepted declared image type: `image_type = "rgb"` per imaging unit, fixed channel tokens `R`, `G`, `B` in that order, no aliases; checked against header metadata and never inferred from pixels; the scientific meaning is left to each brick, which must declare RGB support and is otherwise refused at analysis (`A_RGB_NOT_SUPPORTED`). `R_RGB_NOT_SUPPORTED` is removed | Keeping D8 (RGB users, supported by preprocessing today, would lose a working path once the file is required); or letting RGB runs bypass `morphobricks.toml` until a v2 rule exists (two ways to describe an experiment) | §4.4b, §8 | `v28`, `v29`, `i100`-`i106`, `i119`; P13, P23, P24 |
| AQ7 | **No trimming.** A header name and a `header_names` entry are compared exactly after NFC of both sides; outer whitespace needs a confirmed alias. Preprocessing must stop trimming header names in Stage 1 | Normative trimming (what preprocessing does today, `zarr_input.py:68`): a trimmed name hides a header the user never confirmed | §4.3 | `v31`, `i110`; P26 |
| AQ8 | `parent_labels` (grouped) masks are out of scope in v1 (`E_ENUM`); a v1.1 design follows later | Adding the value before freeze: it needs per-feature applicability rules that nothing has specified | §4.5b | `i111` |
| AQ9 | A `binary` mask may stand in for instances only through an explicit, per-request, recorded conversion (for example CellPatcher `binary_mask_policy="connected_components"`), never automatically and never in the file | Refusing regardless (no route for users who segment regions); or an automatic conversion (today CellPatcher silently measures an integer 0/1 mask as one object) | §4.5c, §4.7, §8 | `v08`, `i112`; P27 |
| AQ10 | `R_MASK_CONTRADICTS_REPRESENTATION` is checked in the mask step, on each new batch of a progressive mask. Publication records "not yet checked"; a run that uses an unchecked mask refuses (`A_MASK_UNCHECKED`) | Checking at publication (a full pixel read of every mask at every publication, masks being unfinished) or in `run` (the failure appears late and per run) | §4.5a, §8 | `v09`; P05, P28 |
| AQ11 | A discovered mask type that breaks the Label rules has its own code, `R_MASK_TYPE_NAME_INVALID`, refused at discovery (a non-NFC name is `R_FOLDER_NOT_NFC`) | No code, leaving the failure to the later `E_ID_TEXT` on writing `source_type` | §8 | P29 |
| AQ12 | A legacy repeat group whose rows carry different `confirmed_on` dates takes the **latest** date, with a recorded note of the original dates | Refusing such groups; taking the earliest date (it would claim a confirmation before the last folder was confirmed) | §7, §11 | `v13`; P30 |
| AQ13 | (a) The forbidden names of §4.7 apply to ID keys as well as field names; (b) a non-NFC channel reference is `E_ID_NOT_NFC` in phase 4; (c) one code per broken rule: an identity that breaks two rules gets both codes | (a) Field positions only: a condition `control` would validate and then be ambiguous with the field; (b) `E_UNKNOWN_CHANNEL` in phase 5: it hides the NFC fault; (c) one code per value | §3.3, §4.7, §6 | `i113`-`i118` |

Consequences recorded with this round:

- **Stage 1 preprocessing changes** that the audit found to contradict v1, now decided: stop
  trimming header names (AQ7); keep RGB support but declare it per unit and check the header
  (AQ6); take `confirmed_on` only from a user action, never the clock; remove a folder from the
  design only on user confirmation (the audit's behaviours 1-3).
- **Superseded by FR1 (fourth round):** a condition or technical-repeat folder named like a forbidden field (`control`, `files`, `z`,
  `experiment`, ...) cannot be described in v1 (AQ13a); preprocessing must report it, and the user
  renames the folder. A `source_repeat` value is not a key and is not affected.
- A group with different legacy `confirmed_on` dates cannot keep every per-row date: the derived
  `experiment_design.csv` is byte-identical to the legacy file for every group whose rows share one
  date, and differs only in the earlier dates otherwise (AQ12).

### Owner decisions of 6 November 2026, fourth round (folder labels, derived-CSV dates; all accepted)

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| FR1 | **Folder labels are never restricted by the reserved or forbidden-name lists.** Conditions and technical repeats, like biological repeats, have a canonical ID (immutable, user-confirmed, the only identity) separate from the folder it was discovered under, recorded in the required `conditions.<ID>.source_folder` and `technical_repeats.<ID>.source_folder` (exact label; Label rules and NFC; not an identity key). The proposed ID is the folder label when allowed; when the label is a forbidden name (`control`, `files`, `z`, ...) preprocessing proposes another ID, the user confirms it, and `display_name` may carry the label. One folder, one ID over the whole file (`E_SOURCE_FOLDER_REUSED`, `E_SOURCE_FOLDER_CONFLICT`); `single` is the ID of `source_folder = "single"` only; `used_ids` gains `technical_repeats` (technical repeat IDs are now immutable and never reused); a folder change for an existing ID is a reassignment (`R_CONFIRMED_ID_CHANGED` without a recorded confirmation); the FOV key and the derived `experiment_design.csv` keep the source folder labels, so legacy datasets stay byte-identical, and the canonical IDs are added beside the key; `source_folder` is part of the `conditions` and `repeats` digests | **Reserved names only in field positions:** keys stay free and the ID remains the folder label, so a condition `control` is valid. It makes the ID key ambiguous with the forbidden field of the same name in every consumer that reads a table path, and it keeps the identity tied to a folder spelling the user does not control. Also rejected: keeping the earlier rule (the folder must be renamed on disk before it can be described): the spec would demand an edit of the user's data and break provenance and the FOV key | §3.1-§3.4, §4.2, §4.4, §4.6, §4.6a, §4.7, §4.9, §6, §7, §8, §9, §10, §11 | `v33`, `v34`, `i113`, `i115`, `i120`-`i127`, `t10`-`t12`; P32, P33 |
| FR2 | **Derived CSV dates.** Byte-identity of the derived `experiment_design.csv` with the legacy file is guaranteed only for repeat groups with a single `confirmed_on`. A legacy group with several dates gets the **latest** date (AQ12) in the derived file and the migration note records the original per-row dates | Claiming byte-identity for every legacy dataset (false for a group whose rows carry different dates: v1 stores one date per repeat); storing the per-row dates in `morphobricks.toml` (a per-member date has no meaning in v1 and would add a field only the migration reads) | §7, §11 | `v13`; P30 |

Consequences recorded with this round:

- **Schema additions (breaking for the earlier Stage 0 draft, which no reader implements):**
  required `source_folder` on every condition and technical repeat, optional `display_name` on a
  technical repeat, required `used_ids.technical_repeats`. The reserved list and the forbidden
  names still apply to **IDs** (keys), where a collision with a field or a column is real.
- The identity of a condition or technical repeat in a published file is its ID. The FOV key still
  spells the folder label in `condition` and `technical_repeat`; consumers add the canonical IDs
  beside it (`condition_id`, `technical_repeat_id`; spelling fixed by SQ8), as `repeat_group` does
  for the repeat (AQ5).
- A folder label that breaks the Label rules (for example `NA`) is still refused at discovery as
  today; this round adds no code for it.
- A renamed condition or technical-repeat folder is a removed folder plus a new pending one; giving
  the new folder to the existing ID is a reassignment that needs the recorded confirmation.

### Owner decisions of 7 November 2026, fifth round (Stage 1 design, PR 0; all recommendations accepted)

The numbers are those of the open questions of the Stage 1 design (`SQ2` is its question 2).

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| SQ2 | **Where publication records live.** A re-confirmation is made at publication, outside a run, so the run manifest cannot hold it yet. Preprocessing appends each record (old ID, new ID, date, both file SHA-256) to an append-only `morphobricks.records.jsonl` next to `morphobricks.toml`, under the publication lock, and copies the records into the next run manifest | Write the record into `morphobricks.toml` (already rejected, §4.6: nothing about it is stored in the file); hold it only in the next manifest (lost when no run follows, or when the draft is discarded); a records directory per publication (more files, no gain) | §4.6 | none (physical; P16) |
| SQ6 | **Spec gaps MS-1 and MS-2 of the matrix audit.** (a) A condition gets the same `single` rule as a technical repeat: `source_folder = "single"` means "no condition folder level" (an experiment folder that is itself the leaf), the condition ID is `single` if and only if its `source_folder` is `single`, and such a condition is the only condition of the file (`E_SINGLE_MISUSE`). (b) The proposal rule of §4.6a covers repeat IDs: the folder label is proposed when allowed; when it is not (for example `z`), no ID is proposed, nothing is repaired or derived, and the user names the repeat ID | (a) Leaving the flat experiment without a condition `source_folder` (the file could not be written for a root-level dataset), or a free choice of ID for it (no rule ties the label `single` to one ID, unlike technical repeats); (b) proposing a derived ID for a repeat (`z` to `z_1`, `R1`): an invented or repaired ID, against §3.3 | §3.2, §4.2, §4.6a, §6 | `v35`, `v36`, `i130`-`i133` |
| SQ7 | **Time-lapses (T > 1).** Allowed, as today. v1 has no T field; the homogeneity of an imaging unit compares axis semantics, not T counts, so FOVs of one unit with different numbers of time points do not make the unit heterogeneous | Refusing T > 1 in v1 (it runs through every brick today and would remove a working path); a T count in the file (a per-FOV statement, §1) | §1 | none (physical) |
| SQ8 | **Downstream field names.** Stage 1 fixes `condition_id` and `technical_repeat_id` as the fields that carry the canonical IDs beside the unchanged FOV key, next to `repeat_group` (preprocessing contract §16 records them) | Other spellings (`condition_canonical`, `tech_id`): no gain, and v1 §3.4 already proposed these | §3.4 | none (consumer contracts) |

Consequences recorded with this round:

- The records file is provenance, like the manifest: it carries no identity and no cache key.

### Clarifications proposed by the implementation (pending owner review)

The preprocessing implementation of the Stage 1 PRs (morphobricks-preprocessing PRs 187 and 188)
found places where experiment-v1 is silent. Each row below is a **clarification proposed by the
implementation**: a short sentence added to the text, **pending owner review**; it is not an owner
decision, and the owner may amend or reject any of them (the text and fixtures then change with it).

| # | Proposed clarification | Spec | Fixtures / refval |
|---|---|---|---|
| C1 | **Bytes of the derived `experiment_design.csv`.** Taken from the preprocessing contract §12 (`docs/contract.md` at `b5a47cb`, line 407 `Rows`: UTF-8, LF, header row, column order, `true`/`false`, sort; line 402: `confirmed_on` is an ISO 8601 date, line 412: `YYYY-MM-DD`). **Open, not settled by the contract:** delimiter, quoting, final line terminator, byte-order mark. The golden files follow today's writer (`design.py:662-679`: `csv.writer`, comma, minimal quoting, `lineterminator="\n"`, so LF after the last row; no BOM) and avoid any value that would need quoting | §11 | `expected/` (`v13`, `v33`, `v34`); `refval.derive_csv` |
| C2 | **Bytes of one section digest.** The form PR 187 implements: the section's table blocks as the canonical writer emits them, each followed by one blank line, descriptive fields omitted, nothing else; an empty section is the empty byte string. It does not contradict §9.1 (the digest is a slice of the canonical file with the descriptive fields removed). §9.1 does not itself say that a blank line follows each table; both the writer and `refval` emit it, so the layout of the canonical file is only implied | §9.3 | `refval.section_digests` (`v01`, `v16`, `v21` still agree) |
| C3 | **`image_count` alone does not reopen a confirmation.** New or removed FOVs in an existing unit change `image_count` only; §10 already says they do not reopen N35, so a new `confirmed_on` beside only a changed `image_count` is refused as `R_CONFIRMED_ON_CHANGED`. The behaviour of PR 188, which the first `refval` did not share (it treated a changed `image_count` as reopening and accepted the date) | §10 | `t13`; `refval.transition` |
| C4 | **Encoding of `morphobricks.records.jsonl`** (SQ2 fixed what a record holds, not the encoding): UTF-8, one JSON object per line ending in LF, keys `type`, `id_kind`, `old_id`, `new_id`, `confirmed_on`, `old_sha256`, `new_sha256`, as PR 188 writes them (`json.dumps(..., ensure_ascii=False, sort_keys=True)`); a torn last line or a non-object line is refused before publication. **Open, not proposed as a rule:** PR 188 appends the records after it replaces `morphobricks.toml`, and a process killed between the two steps leaves a published file without its records; PR 188 does not detect this (its module states that the records file is then the one that cannot be trusted to be complete). Whether, and how, a later publication or run should detect it is for the owner | §4.6 | none (physical; P16) |

### Owner decisions of 7 November 2026 (records file, accepted)

Both decisions extend the encoding of `morphobricks.records.jsonl` (SQ2, clarification C4 above):
the same encoding, and the existing `type` key (value `reconfirmation` so far) tells the three
record types apart. An existing records file stays valid unchanged.

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| RR1 | **Record type `image_count_changed`.** Written when a confirmed unit's image count changes and nothing else does; nothing reopens (§10: "reported and recorded"). It holds the unit (condition, repeat and technical repeat IDs and source folder labels), the old count, the new count and the date | Leaving the change only in the next run manifest (lost when no run follows, as SQ2 found for re-confirmations) | §4.6, §10 | none (physical; P34) |
| RR2 | **Record type `removed`.** Written for every removal of a unit, technical repeat, repeat or condition, including those whose IDs are not reused elsewhere. It holds what was removed (kind, IDs, source folder labels), the user's confirmation and the date | Recording only the removals that need a re-confirmation (a removal that drops a whole ID would leave no record that the user confirmed it) | §4.6, §10 | none (physical; P35) |

Modelling choices made when writing the two decisions into the text (not themselves owner
decisions; the owner may amend them): the discriminator is the existing `type` key, not a new
`kind` key; `image_count` belongs to a member (condition, source repeat), so `image_count_changed`
lists the member's technical repeats; a removed member folder is written as one `unit` record per
imaging unit it held; `image_count_changed` carries `recorded_on` (it is not a confirmation) and
`removed` carries `confirmed_on`; a line whose `type` is none of the three is refused.

### Owner decision of 7 November 2026 (reserved names in `used_ids`, accepted)

Closes MorphoBricks-Spec issue 11 (an external review found §3.2 and §4.9 readable two ways).

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| UR1 | **`used_ids.channels` entries follow the same reserved list as live channel IDs** (§3.2, case-folded): a listed ID reserves that ID, so a reserved name is `E_ID_RESERVED` there too. `used_ids` has no list for mask IDs, so nothing changes for masks or for the other three kinds | Leaving `used_ids` entries to the Token and NFC rules only (a reader could then accept a file whose registry reserves a name no channel can bear, and the two sections disagreed: `refval` carried an `AMBIGUITY` note) | §3.2, §4.9, §6 | `i135`, `v37`; `refval` |

The decision as given named `used_ids.channels` and `used_ids.masks`; §4.9 has no `masks` list
(the four kinds are conditions, channels, repeats and technical repeats), so it is written for
`used_ids.channels` alone. A `masks` list would be a new kind and needs a new `schema_version`.

### Owner decision of 8 November 2026 (image-count records, accepted)

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| RR3 | **`image_count_changed` is written for every confirmed member whose `image_count` changed at a publication**, also when the same publication changes other things (a removal, a new member, an ID correction). A count change alone still reopens nothing and needs no confirmation (`R_CONFIRMED_ON_CHANGED` unchanged). Replaces the "and nothing else changes" condition of RR1 | Writing the record only when the count is the sole change (RR1 as first worded: a count change that shared a publication with another change left no record) | §4.6, §10 | none (physical; P34) |

Confirmed choices for `removed` records, written as clarifications because the text was silent or
contradicted itself (§4.6 said unit lines follow their entity, P35 said they precede it): one
entity line per vanished ID; `unit` lines written once after all entity lines; an entity takes the
date of the first removal answer touching it; published IDs are used when a removal is combined
with an ID correction. No transition fixture was added: a transition fixture states only the
`R_*` set against its predecessor (`fixtures/README.md`), records are not part of that format, and
`refval` does not model the records file; P34 covers the combined case physically.

### Owner decisions of 9 November 2026 (records file byte and refusal rules, accepted)

Evidence: Spec issue 14. The reference validator `tools/audit/refrecords.py` and its goldens
(`fixtures/records/`) found that §4.6 fixed the key order and the unescaped non-ASCII text but not
the whitespace, listed only three refusals, named no code, and was silent on several byte cases;
the preprocessing reader (`read_records`) checked only the key set. All six recommendations of the
audit were accepted.

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| RF1 | **The separators are `, ` and `: `**, with no other whitespace outside strings (what every line written so far has). Any other whitespace is refused | Accepting any JSON whitespace (two spellings of one record, so no byte-stable file) | §4.6 | `ri25`, `ri27`, `ri30` |
| RF2 | **Every violation is a refusal**, not only the three first listed: torn last line, non-object line, unknown `type`, wrong key set, key order at every level, escaped non-ASCII, duplicate keys and invalid values | Refusing only the key set (the preprocessing reader at the time) | §4.6 | `ri01`-`ri24` |
| RF3 | **One catalogue code, `R_RECORDS_FILE_INVALID`**, for a refused records file; the reasons are the reference validator's `E_RECORDS_*` names | One Spec code per reason | §4.6, §8 | all `ri` files |
| RF4 | **An empty file is accepted** (no record). **A byte-order mark, or a CR before the LF, is refused. A SHA-256 is lower-case hex** | Treating an empty file as torn; tolerating a BOM or CRLF | §4.6 | `rv06`, `ri13`, `ri24`, `ri26`, `ri31` |
| RF5 | **`technical_repeats` is not empty and `old_image_count` differs from `new_image_count`** | Accepting a count record that states no change | §4.6 | `ri28`, `ri29` |
| RF6 | **The line order within one publication is stated**: `reconfirmation` lines, then `removed` lines, then `image_count_changed` lines by `condition_id` then `repeat_id`, as preprocessing writes them. It is checked by the writer tests (P34, P35), not by a reader of the file alone (the file has no publication boundary) | Adding a publication marker to the file | §4.6 | P34, P35 |

Modelling choice made when writing RF1 into the text (not itself an owner decision; the owner may
amend it): the escapes inside a string are fixed to the minimal set (`\"`, `\\`, `\b`, `\f`, `\n`,
`\r`, `\t`, `\u00xx` for other control characters), so that a line has exactly one spelling and the
whitespace rule can be checked as "the bytes are the canonical bytes". An optional escape of an
ASCII character is refused as `E_RECORDS_FORM`.

### Owner decision of 9 November 2026 (scope of gate G1, accepted)

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| GS1 | **Gate G1 is met by every §2 row and every §3 scenario of the conformance plan, except exactly four items, which are checked at the Stage 2 gate.** The four are P24 (`rgb_support`), P27 (`binary_mask_policy`), P31 (MorphoCoverage prefill) and the lab-tool-links part of the §2 "Provenance" row (no lab-tool input in Stage 1); their required outcomes belong to the bricks or MorphoCoverage. Nothing else is deferred, and preprocessing's own §2 rows on the same subjects stay in G1. A scenario that names fixtures is shown on those fixtures; extra fixtures do not replace them | Requiring G1 to run brick and MorphoCoverage outcomes in preprocessing's suite; deferring any outcome judged to belong to a brick; letting added fixtures stand in for the named ones | conformance §4, §5 | P24, P27, P31; §2 Provenance |

### Owner decision of 9 November 2026 (v17 channel case moves to gate G3, accepted)

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| GS2 | **The channel case of `v17` is checked at gate G3, not at gate G2.** Preprocessing refuses the layout until Stage 3, so Stage 2 cannot show it. At G2 the channel-scope refusal is shown by `A_SCOPE_INCOMPLETE` on `v01` for a channel no image has, and by full / unavailable coverage recorded per repeat on `v01`; partial coverage is shown for a mask request only, on `v09` (single repeat `rep1`, partially masked). Layouts are homogeneous at G2, so a partial channel request has no G2 fixture: it is the `v17` case at G3. Only the channel case of `v17` moves: no other fixture, scenario or Stage 2 item is deferred, and no fixture, golden or validator changes | Keeping `v17` at G2 (a gate that cannot pass); dropping the `v17` channel case; deferring further Stage 2 items with it | conformance §4 | `v17`, `v01`, `v09`; SI1 |

### Owner decisions of 8 November 2026 (Stage 2 design, PR 3; recommendations accepted)

Evidence: the Stage 2 design (questions 2 and 4) and matrix audit item 8
(`docs/audits/matrix-audit-2026-11-07.md`): §4.4b asked bricks to declare RGB support in "documented
capabilities", but no provider manifest could carry it, so `A_RGB_NOT_SUPPORTED` could not be
implemented as written.

| # | Accepted decision | Rejected alternative | Spec | Fixtures / scenarios |
|---|---|---|---|---|
| RC1 | **RGB support is a machine-readable capability.** A brick's provider manifest may carry the optional boolean `rgb_support`; absent or `false` = unsupported. A **described** run whose request includes an RGB unit's channels is refused with `A_RGB_NOT_SUPPORTED` by a brick that does not declare `true`. **Undescribed** RGB runs keep working as today, with a warning: that is brick behaviour, not a Spec rule | Leaving the declaration in prose (nothing to test); making the key required (every existing manifest would break); refusing undescribed runs too (breaks v0.4 RGB runs) | §4.4b, §8 | P24; `v28` |
| SI1 | **One scope rule.** A requested channel ID that no FOV has and one that only some FOVs lack are the same refusal, `A_SCOPE_INCOMPLETE`, naming the channel (or mask) and the images that lack it ("present in k of n acquisitions", k may be 0) | A separate code or message for "absent from all" (two rules to learn, and a typo in a channel ID would read differently from a partial scope) | §8 (`A_SCOPE_INCOMPLETE`) | `v17`, `v01` (request for an ID no unit lists); conformance §4 |

Modelling choices made when writing these into the text (not themselves owner decisions; the owner
may amend them): the key is top-level in the provider manifest and boolean only, and a non-boolean
value is a manifest error rather than being read as `false` or `true`; a brick with no provider
manifest states the declaration in its documented capabilities, as §4.4b already said; the Spec
does not define the manifest file itself (each brick owns its format), only this one key.

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

Supporting evidence from the LabChronicle lessons audit (PR #4, LabChronicle `a341912`): its allocator (highest number + 1) overflows its own width at 1000 (B1), reuses the
ID of a deleted highest record because it keeps no registry (L2), replaces malformed IDs instead
of reporting them (B2) and renumbers repeat codes in dict order (B11). v1 therefore has no
allocator, no ID repair and a `used_ids` registry (Q1, A2).

### Others

- **Inferring aliases** from pixels, embeddings or name similarity (`DAPI` ≈ `DNA`): rejected;
  identity is a user confirmation, header names are evidence only.
- **Copying calibration** into the file: rejected; `calibration.csv` is authoritative, can target
  single images, and is already SHA-pinned.
- **A spec runtime package** (`load_experiment()` in this repository): rejected for now;
  preprocessing is the reference reader and runs the fixtures (see
  [conformance plan](../conformance-plan.md)).
- **An `x-` extension namespace**: rejected; it would be a back door for unvalidated semantics.
  Any new field needs a new `schema_version`. LabChronicle's opposite choice (unknown fields are
  kept and ignored by validation) suits a catalogue merged from several sources; for a file of
  confirmations it lets a misspelt field validate and live on, so `E_UNKNOWN_FIELD` stays.
- **External vocabularies, several schema formats or a fallback rules copy in the reader**:
  rejected. LabChronicle turns an enumeration into free text when a vocabulary file is missing
  (B9). In v1 the only enumeration is inline (`representation`), and the reader obtains nothing
  from outside at run time.
- **Fuzzy or case-insensitive resolution** of names (LabChronicle: first match ignoring case, B8):
  rejected; resolution is exact.
