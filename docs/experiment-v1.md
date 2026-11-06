# MorphoBricks experiment description, schema version 1 (normative)

- **Status:** Normative specification, Stage 0 (6 November 2026). No reader implements it yet.
  **TODO before Gate G0:** the fixed-SHA audit of current consumers (roadmap S0.1) is not done;
  until it is, the consumer statements here are not audited.
- **Decisions:** [ADR 0001](adr/0001-experiment-description-v1.md).
- **Fixtures:** [fixtures/README.md](../fixtures/README.md). **Conformance:**
  [conformance-plan.md](conformance-plan.md).

The key words MUST, MUST NOT, SHOULD and MAY are normative. "Reader" means any program that
parses the file (in v1, preprocessing is the only reference reader); "writer" means any program
that produces it.

## 1. Scope

The file `morphobricks.toml` describes **what one preprocessing experiment is**: conditions,
canonical channels, biological-repeat pairing, technical-repeat acquisition layouts, mask
semantics and an optional primary reference per condition. It MUST NOT contain file inventory,
fingerprints, calibration, exclusions, per-FOV statements, axes, brick names or routing, feature
requests, normalization, statistics, histogram or model settings. Those stay in
`calibration.csv`, the run manifest, analysis requests and MorphoCoverage configuration.

v1 analyses 2-D planes only. A Z stack is projected by a recorded preprocessing step
(preprocessing #176) before it is described; the file has no Z, axes or shared-plane field.

## 2. File, encoding and parsing

1. The file name is `morphobricks.toml`, in the preprocessing output folder. It is written by the
   preprocessing notebook/CLI under the output folder's lock, atomically, and never by `run`.
   Readers MUST refuse a symlinked file (`R_FILE_SYMLINK`).
2. The bytes MUST be UTF-8 without a byte-order mark (`E_FILE_ENCODING`) and MUST be valid TOML
   1.0 (`E_TOML_SYNTAX`). A key declared twice, in any spelling TOML treats as the same key
   (bare vs quoted, table vs dotted vs inline), MUST be refused as `E_DUPLICATE_KEY`.
3. Readers MUST NOT convert types. A value whose TOML type differs from §4 is `E_TYPE`. In
   particular a TOML integer, float, boolean, date, time or datetime where text is required, a
   string where an integer or boolean is required, and a boolean where an integer is required
   (implementations whose booleans are integers MUST check the exact type).
4. Every table has a closed set of fields. A field not listed in §4 is `E_UNKNOWN_FIELD`, except
   the names in §4.7, which are `E_FORBIDDEN_FIELD`. There is no extension namespace.
5. Comments are allowed and carry no meaning. Writers do not preserve them (§9).
6. The SHA-256 of the exact bytes read is the file's provenance identity (run manifest). It is not
   a cache key (§9.3).

## 3. Identities

### 3.1 Kinds of identity

| Identity | Where | Canonical or source | Rule set |
|---|---|---|---|
| Condition ID | key of `conditions` | Source = canonical (the condition folder label) | Label |
| Canonical repeat ID | key of `repeats` | Canonical (user-confirmed; default the source folder label) | Label |
| Source repeat | `source_repeat` | Source (biological-repeat folder label) | Label |
| Technical repeat | key of `technical_repeats` | Source = canonical (folder label, or `single`) | Label |
| Channel ID | key of `channels` | Canonical | Token |
| Mask ID | key of `masks` | Canonical (object-set name) | Token + object set |
| Mask source type | `source_type` | Source (discovered mask type) | Label |
| Display name | `display_name` | Display only, never an identity | Non-empty text (§4.8) |

### 3.2 Rule sets

- **Label** (preprocessing decision D-e, `check_identity_text`, preprocessing `a786290b`): text;
  no leading or trailing whitespace; not `""`, `NA`, `nan`, `none`, `null`, `n/a` or `<NA>` in any
  case (`E_ID_TEXT`).
- **Token** (MorphoFeature `naming.py`, `803e617a`): the Label rules, plus the regular expression
  `^[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*$` (`E_ID_SYNTAX`; this also excludes the feature-column
  separator `__`). A channel ID whose case-folded form is one of `whole`, `cell`, `nucleus`,
  `cytoplasm`, `ring`, `expanded_nucleus` (the MorphoRelate compartment names; this is the whole
  reserved list for channels, and a new compartment name needs a new `schema_version`) is
  `E_ID_RESERVED`. A channel ID MUST NOT equal one of them in any case.
- **Object set** (MorphoFeature `is_reserved_object_set`): a mask ID whose case-folded form is one
  of the six names above, or whose case-folded `_`-separated parts include `in`, is
  `E_ID_RESERVED`.
- **`single`:** an identity of any kind whose case-folded form is `single` MUST be exactly
  `single`. A technical repeat `single` MUST be the only technical repeat of its member; a member
  with `source_repeat = "single"` MUST be the only member of its condition in the file
  (`E_SINGLE_MISUSE`; preprocessing contract §1).

### 3.3 Normalization, uniqueness and case

- **NFC.** Identities (the keys and identity fields of §3.1) are Unicode NFC. A reader MUST
  normalize every identity it reads to NFC before applying any rule, including reference
  resolution; a writer MUST emit NFC. This is the only transformation an identity ever undergoes:
  no trimming, case folding, parsing or other normalization. (Folder names read from disk are
  compared after NFC; the on-disk spelling is not stored.)
- After NFC, identities are compared exactly, code point by code point. Two distinct keys or
  values of one scope that are equal after NFC are `E_ID_NFC_COLLISION` (not also reported as a
  case collision).
- Within each of these scopes, two identities that differ after NFC but whose `str.casefold()`
  forms are equal are `E_ID_CASE_COLLISION`: condition IDs; repeat IDs; source repeats over the
  whole file; technical repeats over the whole file; channel IDs; mask IDs; mask source types.
  (Preprocessing `check_identity_case`: a label is spelled one way in the whole run.) Case folding
  is never applied when resolving a reference (`ctrl` does not resolve to `CTRL`).
- Identities are never parsed. `rep1`, `2026-01-01`, `012` and `acquisition_2` are opaque text;
  no number, date, order or meaning is derived from them.
- **Immutability.** Once a repeat, condition or channel is confirmed, its ID never changes (§4.6).
  Only `display_name` may change, at any time.

## 4. Tables and fields

Types are TOML types. "Text" is a TOML string. "Date" is a TOML **string** `YYYY-MM-DD` naming a
real calendar day (`E_DATE_FORMAT`); a TOML date literal is `E_TYPE`. "Non-empty text" refuses
`""` and whitespace-only strings (`E_TEXT_EMPTY`). "Req" = required; a missing required field is
`E_MISSING_FIELD`. An empty table or array where at least one entry is required is `E_EMPTY`.

### 4.1 Top level

| Key | Type | Req | Rule |
|---|---|---|---|
| `schema` | text | yes | Exactly `morphobricks-experiment` (`E_SCHEMA_ID`) |
| `schema_version` | integer | yes | Exactly `1` (missing: `E_SCHEMA_VERSION_MISSING`; other integer: `E_SCHEMA_VERSION_UNSUPPORTED`) |
| `conditions` | table of condition | yes | ≥ 1 entry |
| `channels` | table of channel | yes | ≥ 1 entry |
| `repeats` | table of repeat | yes | ≥ 1 entry |
| `masks` | table of mask | no | May be absent or empty |

### 4.2 `conditions.<condition ID>`

| Key | Type | Req | Rule |
|---|---|---|---|
| `display_name` | non-empty text | no | Display only (§4.8) |
| `reference` | text | no | One condition ID: the primary reference (§5) |
| `target` | non-empty text | no | Declarative plain string, e.g. `SRC`; no runtime use before Stage 2 and never part of identity |
| `treatment_key` | non-empty text | no | Declarative plain string: same perturbation under different backgrounds; no runtime use before Stage 2 |

Every condition MUST be the condition of at least one member (`E_CONDITION_WITHOUT_MEMBERS`).

### 4.3 `channels.<channel ID>`

| Key | Type | Req | Rule |
|---|---|---|---|
| `display_name` | non-empty text | no | Display only (§4.8), e.g. `DAPI` |
| `header_names` | array of non-empty text | no (default `[]`) | Header channel names the user confirmed as evidence for this channel; no duplicates (`E_DUPLICATE_VALUE`); order not semantic |

A channel that appears in no technical repeat's `channels` is **valid**; the reader reports the warning `W_UNUSED_CHANNEL`. A declared but unused channel is never an error, and never an implicit zero or default.

Header evidence (enforced by preprocessing, §8): a non-empty header channel name read at source
index *i* of an image in a unit MUST match **exactly and case-sensitively** (after NFC, no
trimming, no folding, no similarity) a member of `header_names` of the channel at position *i* of
that unit's list, else `R_HEADER_CONTRADICTION`; any other spelling needs a user-confirmed alias
(a new `header_names` entry). This holds even when the header
name equals the channel ID or display name: aliases are only ever user-confirmed, never inferred from
name similarity, case or pixels. An image without header names needs no evidence. The same header
name MAY be evidence for different channels (fluorophores are reused across acquisitions).

### 4.4 `repeats.<canonical repeat ID>`

| Key | Type | Req | Rule |
|---|---|---|---|
| `display_name` | non-empty text | no | Display only (§4.8) |
| `confirmed` | boolean | yes | MUST be `true` in a published file (`E_REPEAT_UNCONFIRMED`): the N35 answer "prepared and acquired under the same circumstances" |
| `confirmed_on` | date | yes | Date of that confirmation |
| `members` | table of member | yes | ≥ 1 entry |

`repeats.<R>.members.<condition ID>` (one member = one source biological-repeat folder of one
condition; at most one per condition per repeat, guaranteed by TOML key uniqueness):

| Key | Type | Req | Rule |
|---|---|---|---|
| `source_repeat` | text | yes | Exact source folder label (Label rules) |
| `image_count` | integer ≥ 1 | yes | Images to analyse at confirmation (N35 evidence; `E_VALUE_RANGE`) |
| `technical_repeats` | table of technical repeat | yes | ≥ 1 entry |

`repeats.<R>.members.<C>.technical_repeats.<technical repeat>` (one imaging unit):

| Key | Type | Req | Rule |
|---|---|---|---|
| `channels` | array of channel IDs | yes | ≥ 1 entry; ordered: entry *i* is source channel C*i*; every entry declared (`E_UNKNOWN_CHANNEL`); no repeats (`E_DUPLICATE_CHANNEL_IN_UNIT`) |

Repeat rules:

- The member key MUST be a declared condition ID (`E_UNKNOWN_CONDITION`).
- A source folder `(condition, source_repeat)` MUST belong to exactly one repeat
  (`E_SOURCE_REPEAT_REUSED`).
- If a canonical repeat ID R equals, ignoring case, the `source_repeat` S of a member, that member
  MUST belong to R (`E_REPEAT_ID_SHADOWS_SOURCE`). This forbids swapped labels such as repeat
  `rep1` holding folder `rep2` while repeat `rep2` holds folder `rep1`.
- A repeat MAY lack some conditions (warning `W_REPEAT_MISSING_CONDITIONS`).
- Technical repeats inside one biological repeat MAY have different channel counts and orders.
  They remain one biological repeat; they never create additional biological replicates.

### 4.5 `masks.<mask ID>`

| Key | Type | Req | Rule |
|---|---|---|---|
| `source_type` | text | yes | Exact discovered mask type (Label rules); one mask per source type (`E_MASK_SOURCE_TYPE_REUSED`) |
| `representation` | text | yes | `instances` or `binary` (`E_ENUM`); user-confirmed, never inferred from dtype, values or names. A mask declared `binary` with more than two distinct values is refused by preprocessing (`R_MASK_CONTRADICTS_REPRESENTATION`); the user must declare `instances` |
| `source_channels` | array of channel IDs | no | Provenance only (what the mask was derived from); not a restriction on measured channels; each declared (`E_UNKNOWN_CHANNEL`); no duplicates (`E_DUPLICATE_VALUE`); order not semantic |
| `display_name` | non-empty text | no | Display only (§4.8) |

Mask files, pairing, completeness and fingerprints stay in the run manifest. A declared mask with
files for none, some or all FOVs is valid (progressive segmentation, 0/1000 → 1000/1000).

### 4.6 Immutable IDs

- Once confirmed, the ID of a repeat, condition or channel MUST NOT change. There is no rename
  and no retired-ID table. A rename in the file would be a different ID for the same data.
- Preprocessing MUST refuse, as `R_CONFIRMED_ID_CHANGED`, a candidate file (compared with the
  last published file and the manifest history) in which (a) a repeat with the same member folders
  `(condition, source_repeat)` carries another ID, (b) a channel's ID is replaced by another ID at
  every unit position it held with the same header evidence, or (c) an ID that was confirmed for
  some entity now names a different one (reuse). A condition ID is its folder label, so a renamed
  folder is a removed member plus a new pending one (§7).
- A mistyped ID is fixed only by an explicit, recorded re-confirmation: a user action that
  writes a new file and records old ID, new ID, date and both file SHA-256 in the run manifest.
  Products keyed on that ID are invalidated. Nothing about it is stored in the file.
- The friendly name of any entity is `display_name` (§4.8), not the ID.

### 4.8 Display names

`display_name` (conditions, repeats, channels, masks) is for display only (reports, notebooks,
plots). It MUST NOT be used for identity, joins, pairing, references or cache keys, and changing
or adding it invalidates nothing (§9.3). Within one kind, two display names equal after NFC are
`E_DISPLAY_NAME_COLLISION`. Uniqueness does not make a display name an identity.

### 4.7 Forbidden fields

These names are refused as `E_FORBIDDEN_FIELD` in **any** table, with a message naming where the
information belongs:

| Field | Belongs to |
|---|---|
| `axes`, `shared`, `plane_scope`, `z`, `projection` | Image/manifest records; v1 is 2-D only (preprocessing #173, #176) |
| `pixel_size`, `calibration` | `calibration.csv` |
| `fovs`, `files`, `paths`, `overrides`, `exclude`, `fingerprints` | Run manifest / preprocessing inputs; no per-FOV statements |
| `bricks`, `routes`, `features`, `normalization`, `statistics`, `contrasts` | Analysis requests / brick and MorphoCoverage configuration |
| `control`, `roles`, `experiment` | Derived from `reference` / analysis requests / MorphoCoverage FDR families |
| `source_index`, `channel_count` | Implied by the order and length of `channels` |
| `retired_repeats`, `replaced_by` | None: IDs are immutable (§4.6) |


## 5. Reference graph

- `reference` names the primary matched control of a condition. It is experiment metadata, not
  a contrast table; further contrasts belong to MorphoCoverage.
- It MUST name a declared condition, exactly (`E_REFERENCE_UNKNOWN`; `ctrl` does not resolve to
  `CTRL`), MUST NOT name its own condition (`E_REFERENCE_SELF`), and the graph of all `reference`
  edges MUST be acyclic (`E_REFERENCE_CYCLE`). A condition has at most one `reference` (an array
  is `E_TYPE`).
- Chains are allowed (`VEC_SiCol6a1 → VEC_SiNC → VEC`). A condition is a *control* iff some
  condition references it.
- If a condition and its reference share no repeat, MorphoCoverage cannot pair them: warning
  `W_REFERENCE_UNPAIRED`.

## 6. Validation phases and error catalogue

A reader MUST run the phases in order and stop after the first phase that reports an error. It
MUST report every error of that phase, each with the code, the table path (e.g.
`repeats.Day1.members.CTRL.technical_repeats.single.channels[2]`) and the offending value.
Warnings are reported only for a file without errors and never block publication. Conformance
compares the **set of codes** of the reported phase ([fixtures](../fixtures/README.md)).

| Phase | Code | Meaning |
|---|---|---|
| 1 Decode | `E_FILE_ENCODING` | Not UTF-8, or starts with a byte-order mark |
| 1 | `E_TOML_SYNTAX` | Not TOML 1.0 (includes unquoted text such as `NO`, and `012`) |
| 1 | `E_DUPLICATE_KEY` | A key or table declared twice |
| 2 Header | `E_SCHEMA_ID` | `schema` missing or not `morphobricks-experiment` |
| 2 | `E_SCHEMA_VERSION_MISSING` | `schema_version` missing |
| 2 | `E_SCHEMA_VERSION_UNSUPPORTED` | `schema_version` an integer other than 1 |
| 2 | `E_TYPE` | `schema` or `schema_version` of the wrong TOML type |
| 3 Structure | `E_UNKNOWN_FIELD` | Field not defined for its table |
| 3 | `E_FORBIDDEN_FIELD` | Field from §4.7 |
| 3 | `E_MISSING_FIELD` | Required field absent |
| 3 | `E_TYPE` | Wrong TOML type (no conversion) |
| 3 | `E_EMPTY` | Required table/array is empty |
| 3 | `E_TEXT_EMPTY` | Non-empty text is empty or whitespace only |
| 3 | `E_ENUM` | Value outside its enumeration |
| 3 | `E_DATE_FORMAT` | Not a real `YYYY-MM-DD` date string |
| 3 | `E_VALUE_RANGE` | Integer outside its range |
| 3 | `E_REPEAT_UNCONFIRMED` | `confirmed = false` in a published file |
| 4 Identity | `E_ID_TEXT` | Label rule violated |
| 4 | `E_ID_SYNTAX` | Token regular expression violated |
| 4 | `E_ID_RESERVED` | Reserved compartment / object-set name (channel IDs: §3.2 list) |
| 4 | `E_ID_NFC_COLLISION` | Two identities of one scope equal after NFC |
| 4 | `E_ID_CASE_COLLISION` | Two identities of one scope equal ignoring case |
| 4 | `E_SINGLE_MISUSE` | `single` in another case or not alone |
| 5 Semantics | `E_UNKNOWN_CONDITION` | Member key is not a declared condition |
| 5 | `E_UNKNOWN_CHANNEL` | Unit or `source_channels` names an undeclared channel |
| 5 | `E_DUPLICATE_CHANNEL_IN_UNIT` | A channel twice in one unit |
| 5 | `E_DUPLICATE_VALUE` | Duplicate in `header_names` or `source_channels` |
| 5 | `E_DISPLAY_NAME_COLLISION` | Two display names of one kind equal after NFC |
| 5 | `E_CONDITION_WITHOUT_MEMBERS` | Declared condition in no repeat |
| 5 | `E_SOURCE_REPEAT_REUSED` | One source folder in two repeats |
| 5 | `E_REPEAT_ID_SHADOWS_SOURCE` | Repeat ID equal to the source folder name of another repeat's member |
| 5 | `E_MASK_SOURCE_TYPE_REUSED` | Two masks with one `source_type` |
| 5 | `E_REFERENCE_UNKNOWN` | `reference` names no declared condition |
| 5 | `E_REFERENCE_SELF` | `reference` names its own condition |
| 5 | `E_REFERENCE_CYCLE` | The reference graph has a cycle |
| warn | `W_UNUSED_CHANNEL` | A declared channel is in no unit |
| warn | `W_REPEAT_MISSING_CONDITIONS` | A repeat lacks some declared conditions |
| warn | `W_REFERENCE_UNPAIRED` | A condition and its reference share no repeat |

Phase-2 `E_TYPE` concerns only `schema`/`schema_version`. An unsupported or missing version stops
validation: a reader MUST NOT try to interpret fields of a version it does not support.

## 7. Versioning and migration

- `schema_version` is an integer. Any change to fields, types, rules or meanings requires a new
  version. Readers MUST refuse any version they do not implement (`E_SCHEMA_VERSION_UNSUPPORTED`)
  with a message naming the supported versions; they MUST NOT read a newer file "best effort".
- A migration between versions MUST be an explicit, recorded operation that writes a new file and
  never changes canonical identities silently.
- **Repeat, condition and channel IDs are immutable** (§4.6). There is no rename migration; a
  friendlier name is `display_name`. A mistyped ID is corrected only by a recorded re-confirmation.
- **Source folder renamed or moved:** a removed member plus a new, unpaired, pending member. It is
  never auto-paired with the removed one; the user may assign it to the existing canonical repeat
  (the canonical ID does not change).
- **Legacy `experiment_design.csv` → v1:** read with the strict reader (no `yes`/`no`/empty
  coercion). `repeat_group` → canonical repeat ID; `biological_repeat` → `source_repeat`;
  `image_count`, `confirmed`, `confirmed_on` copied; technical repeats and channel lists come from
  discovery and user confirmation. Controls: 0 marked → no `reference`; 1 marked → every other
  condition references it; ≥ 2 marked → a draft with unresolved references that cannot be
  published until the user answers (no name-stem guessing). A legacy design that violates v1
  rules (e.g. `E_REPEAT_ID_SHADOWS_SOURCE`) MUST be refused with the code, not repaired.

## 8. Validation boundaries

| Layer | Owns | Codes |
|---|---|---|
| Spec (this document) | Syntax, types, identities, cross-references, graphs; no files read except this one | `E_*`, `W_*` |
| Preprocessing (reference reader) | Physical agreement of the file with the experiment folder; reconciliation; publication | `R_*` |
| Analysis layer (MorphoFeature, MorphoRelate, fiberfeatures, MorphoEmbed, MorphoCoverage, CellPatcher, normalization) | Applicability of a request to the described units | `A_*` |

Required preprocessing refusals (`R_*`):

| Code | Meaning |
|---|---|
| `R_FILE_SYMLINK` | `morphobricks.toml` is a symlink |
| `R_CONFIRMED_ID_CHANGED` | A confirmed ID was changed or reused (§4.6) without a recorded re-confirmation |
| `R_UNIT_NOT_FOUND` | A declared imaging unit has no included image |
| `R_UNIT_NOT_DECLARED` | A discovered imaging unit is not in the file (reconciliation draft required) |
| `R_CHANNEL_COUNT_MISMATCH` | An image's channel count differs from its unit's list length |
| `R_UNIT_NOT_HOMOGENEOUS` | FOVs of one unit differ in channel count, interpreted axes or header names at one C index; the message names FOV, path and C index |
| `R_HEADER_CONTRADICTION` | A header name at C*i* is not in the confirmed `header_names` of the unit's channel at *i* |
| `R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` | Stage 1–2 only: the units do not all have the same ordered list; names the units; lifted at Stage 3 |
| `R_MASK_TYPE_NOT_DECLARED` | A discovered mask type has no `masks` entry |
| `R_MASK_CONTRADICTS_REPRESENTATION` | A mask declared `binary` holds more than two distinct values |
| `R_RGB_NOT_SUPPORTED` | Interleaved colour (RGB) image: refused in v1, no channel semantics |

Within one unit, `R_UNIT_NOT_HOMOGENEOUS` is reported first and replaces
`R_CHANNEL_COUNT_MISMATCH` and `R_HEADER_CONTRADICTION` for that unit: intra-unit discrepancies
are detected before channel identity is checked.

Undetectable by any layer: identical-shape, unnamed images with physically swapped fluorophores.
Representative previews and explicit confirmation are the guard; image-based checks are advisory.

Required analysis-layer refusals (`A_*`): `A_SCOPE_INCOMPLETE` (a requested canonical channel or
mask is absent from part of the requested scope; refuse unless the user selects and records an
eligible subset; never drop FOVs, impute, re-weight technical repeats or change biological N);
`A_MASK_NOT_INSTANCES` (a `binary` mask requested as an object set); `A_DRAFT_REFUSED` (§10: `RunInputs` given a draft or an unconfirmed file). Each biological repeat is
classified **fully represented**, **partially represented** or **unavailable** per request and
recorded in the run manifest. Consumers resolve channels by canonical ID per unit, never by C
index alone, and group by canonical repeat ID.

## 9. Serialization, round trip and caching

### 9.1 Canonical serialization (writers)

Writers MUST produce deterministic bytes: UTF-8, no BOM, LF, a final newline, no comments.
Order: `schema`, `schema_version`, then `conditions`, `channels`, `repeats`, `masks` (an empty
optional table is omitted); identities are NFC. Entries of each table sorted by key in code
point order; fields in the order of §4; each table as a standard `[header]`; arrays inline;
`header_names` and `source_channels` sorted, unit `channels` in declared order; keys bare when
they match `[A-Za-z0-9_-]+`, else basic quoted strings; strings as TOML basic strings with the
minimal escapes.

### 9.2 Round trip

For every valid file F: `parse(write(parse(F)))` MUST equal `parse(F)`, and `write` MUST be
idempotent. Any field a reader would drop is refused instead (§2.4), so no confirmed semantics can
be lost silently. Reordering tables or entries, or switching between bare/quoted keys or
standard/inline/dotted tables, never changes meaning.

### 9.3 Provenance vs cache keys

The whole-file SHA-256 is provenance. Preprocessing SHOULD also record per-section digests (SHA-256
of the canonical serialization of `conditions`, `channels`, `repeats`, `masks`) so that consumers
key derived products only on the sections they use. Digests are computed with every `display_name`
omitted: a change to `display_name` MUST NOT change any digest, a change to `reference` MUST NOT
invalidate pixel-derived products; a change to a unit's channel list MUST invalidate the products
that depend on that unit's channels.

## 10. Reconciliation and confirmation (preprocessing behaviour)

On every run, preprocessing compares fresh discovery with the published file and classifies each
unit **unchanged**, **new**, **removed** or **conflicting**. It never rewrites confirmed semantics
silently; edits go to a separate draft and are published atomically after validation.

- **N35 reopening.** The confirmation of a repeat is reopened (draft `confirmed = false`) only when
  channels, layout or grouping change: a new or removed unit or member, a unit's ordered channel
  list, or the pairing of folders into repeats. New FOVs (or removed ones) inside an existing unit
  whose confirmed layout still holds do **not** reopen it; they are reported and recorded.
- A removed member is reported and removed only on user confirmation; a repeat left without
  members is removed from the file, and its ID stays in the manifest history and is never reused
  for other members (`R_CONFIRMED_ID_CHANGED`).
- A new folder whose label equals an existing repeat ID is proposed for that repeat but stays
  pending until confirmed.
- A conflicting unit (`R_*`) blocks publication; no per-FOV exception is created.

## 11. Derived `experiment_design.csv` (compatibility output)

Preprocessing MUST derive the legacy file (schema version 1, preprocessing contract §12)
deterministically from a published file, with the contract's byte rules:

| CSV column | Value |
|---|---|
| `condition` | member's condition ID |
| `biological_repeat` | member's `source_repeat` |
| `repeat_group` | canonical repeat ID |
| `control` | `true` iff some condition's `reference` names this condition |
| `image_count` | member's `image_count` |
| `technical_repeat_count` | 0 if the only technical repeat is `single`, else the number of technical repeats |
| `confirmed` | `true` |
| `confirmed_on` | repeat's `confirmed_on` |
| `schema_version` | `1` |

One row per member, sorted by `condition`, then `biological_repeat`, in code point order. For a
legacy dataset whose canonical IDs equal its folder labels and whose controls migrate
deterministically, the derived file MUST be byte-identical to the one preprocessing writes today.
Known loss: a legacy design marking a control that no other condition references (e.g. one
condition only) exports `control = false`.

Expected `experiment_design.csv` outputs (golden files) are **deferred to Stage 1**; Stage 0 fixes
only the derivation rules above.

## 12. Drafts

A draft (reconciliation proposal, unconfirmed repeats, unresolved legacy references) is internal
to preprocessing. It is never named `morphobricks.toml`. Downstream consumers (`RunInputs`) read
only the confirmed, published `morphobricks.toml` and MUST refuse a draft or any file with an
unconfirmed repeat (`A_DRAFT_REFUSED`; a published-path file with `confirmed = false` is also
`E_REPEAT_UNCONFIRMED`).
