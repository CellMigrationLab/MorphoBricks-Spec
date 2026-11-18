# ADR 0006: fast-mode channel layout (one channel list for the experiment)

- **Status:** **Proposed** (owner decisions of 16 November 2026, FC1-FC4 below, final and not to be
  reopened by the review). What this ADR adds is their encoding: the description field, how the
  confirmation is represented, the refusal code, its place among the existing codes, and the
  interactions with RGB, heterogeneous layouts, reconciliation and aliases. Those choices are
  listed under [modelling choices](#modelling-choices-for-the-owners-review). Nothing is
  implemented; preprocessing implements it after this ADR is accepted and its Spec pin moves.
- **Amends** the normative [`experiment-v1.md`](../experiment-v1.md): §3.3 (NFC), §4.1 (a new
  optional top-level table), §4.3 and the new §4.3a, §4.4 (a new unit key), §6 (two `E_*` codes,
  four extended), §7 (an amendment of v1, no new version), §8 (`R_FAST_LAYOUT_CONTRADICTION` and its
  precedence), §9.1, §9.3 and §10. Amends [ADR 0001](0001-experiment-description-v1.md) (a default
  for the per-unit tagging of its "Consequences"; D9 and AQ7 are unchanged and applied as they are).
  Fixtures `v41`-`v43`, `i142`-`i151`, `t16`-`t20`; the audit validator `tools/audit/refval.py`;
  conformance plan §2 row "Fast mode" and scenarios P37-P40.
- **Base:** MorphoBricks-Spec `main` `1167108`. Evidence about preprocessing is read at
  morphobricks-preprocessing `main` `9115f39d6d088a45475118349d5fb0879c957b6a`.

## Context

Today every imaging unit (a technical repeat of one member) carries its own ordered `channels`
list, and the preprocessing notebook asks the user to tag the channels of each acquisition, with the
header names as evidence (experiment-v1 §4.3, §4.4; ADR 0001 "Consequences fixed by this ADR").
For the common experiment, where every acquisition has the same channels in the same order, that is
the same answer typed once per unit: tens of units for a modest plate, each a chance to click the
wrong row. The owner decided on 16 November 2026 that the usual case should be one statement, made
once, and that the per-unit path stays for the experiments that need it.

The rules this must keep: no guessed channels (identity is a user confirmation; header names are
evidence only, ADR 0001 D3), header names match exactly after NFC with no trimming (D9, AQ7), no
silent repair or reordering (§3.3), and every refusal names what is wrong and how to fix it.

## Decisions

### Owner decisions of 16 November 2026 (recorded, accepted; not reopened by this ADR)

| # | Decision |
|---|---|
| FC1 | **Fast mode is the default everywhere**: the notebook and a one-command CLI path (for example `describe --fast`). The strict per-unit mode stays available. |
| FC2 | **A declared assumption, recorded.** In fast mode the description records one ordered channel list for the whole experiment: "every imaging unit has the same channels in the same order". It is a user statement, made once, and recorded in the description so that downstream bricks and audits can see it. It is not a guess. |
| FC3 | **Trust the headers.** When every image's header channel names match the confirmed label list exactly (exact after NFC, no trimming, D9/AQ7, or a saved alias), the channels are accepted with no per-unit confirmation. Images without header names follow the one tagged unit's order. |
| FC4 | **A contradiction is refused before any pixel read**, listing **every** contradicting image with the fix: tag those units on their own, that is switch them to per-unit, then re-run. Contradictions are a different channel count, header names in another order, other names, or a different image type. Nothing is reordered or guessed. |

### Where the change is recorded: a new ADR

A new ADR, not a round inside ADR 0001. The repository's practice: a single field added to an
existing decision of ADR 0001 is recorded there (RH1 refines AQ6, PL1 supersedes AQ8; each adds one
key or one value and changes no workflow); a new policy with its own decision set, refusal code and
cross-section rules gets its own ADR that names what it amends (ADR 0005 amends experiment-v1 §4.5,
§4.5b, §8 and ADR 0001 D10). Fast mode is the second kind: it changes the default authoring workflow
(FC1), adds a top-level table and a unit key, a preprocessing refusal with its own precedence, and
rules in reconciliation. ADR 0001 gains one status line pointing here.

### The description field

| | |
|---|---|
| **Name** | `channel_layout` |
| **Place** | Top level, a table, written after `channels` (experiment-v1 §4.1, §9.1) |
| **Type** | Table with `channels` (array of channel IDs, required, ≥ 1, ordered: entry *i* is C*i*), `image_type` (text, optional, only `rgb`) and `confirmed_on` (date, required: the date of the user's statement, a user fact under §4.4a) |
| **Default** | Writers: fast mode for a **new** description (FC1). Readers: none. No reader supplies the table, and its absence never means fast mode |
| **Absent** | The file is a **strict per-unit** file: every unit's list was confirmed per unit, as every published file before this ADR |
| **Per unit** | `channels_from`, required on every unit of a fast-mode file: `experiment` (the unit follows the experiment list) or `unit` (tagged on its own, FC4); not allowed in a strict file |

A unit with `channels_from = "experiment"` MUST list exactly `channel_layout.channels` and the same
`image_type` (`E_FAST_LAYOUT_MISMATCH`). The table's own `channels` follows every rule of a unit's
list (declared, no duplicate, NFC, the RGB rules).

The statement FC2 is, in the file's words: *every imaging unit whose `channels_from` is
`experiment` has the channels of `channel_layout.channels`, in that order, of `channel_layout`'s
image type*. Its scope is the units that say so, so a unit tagged on its own (FC4) never makes the
statement false.

### How the confirmation is represented: materialised lists plus a marker

Each unit keeps its full `channels` list (materialised from the experiment list) and states how the
list was confirmed (`channels_from`). Reasons:

1. **Readers need no change.** `RunInputs`, the shared resolver (ADR 0002) and every brick resolve
   channels per unit, by canonical ID, from the unit's list (experiment-v1 §8, last paragraph). A
   unit that referenced the experiment list instead would change every reader and the resolver
   contract, for a file that only preprocessing parses.
2. **Complete and auditable.** Each unit says, in the file, what C*i* is and whether the user tagged
   it or it was accepted under the statement; the statement itself is the table with its date. An
   audit needs neither the run manifest nor the notebook history to tell the two apart.
3. **Existing rules hold unchanged.** Changed entities (§4.6, positions of a channel), N35 reopening
   (§10), section digests (§9.3) and the heterogeneity refusal all read unit lists today, and keep
   reading them.
4. **The redundancy is checked, not trusted.** A materialised list that differs from the experiment
   list is refused (`E_FAST_LAYOUT_MISMATCH`), so the copy can never drift silently.

Rejected: (a) **one list referenced by units** (a unit without `channels` that points at the table):
every reader changes, and an omitted list could no longer be told from a missing field; (b) **the
table alone, no per-unit marker**: an auditor could not tell a unit the user tagged on its own from
one accepted under the statement when both lists are equal (`v41` DrugA/rep2); (c) **the marker only
on exceptions** (absent in a fast-mode file meaning `experiment`): the same absent key would mean two
things in two files.

### Refusal: `R_FAST_LAYOUT_CONTRADICTION`

Preprocessing compares every included image of every unit with `channels_from = "experiment"` with
`channel_layout`, from **header metadata only** (the channel count and the channel names the format
states, its colour interpretation and samples per pixel), before any pixel of any image is read and
before anything is processed or published. Each image is checked for **every** kind below that can
be checked on it, and all that apply are reported for that image (not only the first):

| Kind | When |
|---|---|
| `image_type` | The image's type, the effective type after a valid RH1 override of its unit (§4.4b), contradicts `channel_layout.image_type` in either direction (the test of `R_IMAGE_TYPE_CONTRADICTS_HEADER`); a format that states no colour interpretation cannot contradict |
| `channel_count` | Its channel count differs from the list's length |
| `header_order` | Some non-empty header name at C*i* is not in `header_names` of the list's channel at *i* (the §4.3 rule: NFC of both sides, code points, no trimming), and every such name is in `header_names` of another channel of the list |
| `header_names` | Some non-empty header name at C*i* is in `header_names` of no channel of the list |

`image_type` and `channel_count` are checked on every image. The two header-name kinds exclude each
other (an image has `header_names` when any failing name is evidence for no channel of the list,
else `header_order`) and are checked at every index C*i* that both the image and the list have, so a
channel count that differs does not hide them. One image can thus carry up to three kinds, for
example an RGB header, three channels against a list of two, and a name that is evidence for no
channel. The order of the kinds in an image's entry is the order of the table.

An image without header names, or with an empty name at C*i*, needs no evidence there (§4.3): it is
accepted under the statement (FC3, "the one tagged unit's order"), and its count and type are still
checked.

**Verification status, recorded per image.** The run manifest's record of each unit with
`channels_from = "experiment"` holds `fast_layout_images`, one entry per included image of the unit,
sorted by path:

```json
{"path": "CTRL/rep1/acquisition_1/FOV001.ome.tif", "fov_key": "<FOV key>", "header_verified": false,
 "channels": [{"c": 0, "channel": "DNA", "header_name": "DAPI", "evidence": "header"},
              {"c": 1, "channel": "ACTIN", "header_name": null, "evidence": "statement"}]}
```

`channels` has one entry per index of the list, in order: `header_name` is the name as read (no
normalisation; `""` when the stated name is empty, `null` when the format states none) and `evidence` is `header`
(the name is in the channel's `header_names` under the §4.3 rule) or `statement` (no name: accepted
under FC2/FC3). `header_verified` is `true` exactly when every entry is `header`. A partly named
image (C0 named, C1 blank) is therefore recorded as not header-verified, with C0's evidence kept
(P37 (h)). A unit with `channels_from = "unit"` has no `fast_layout_images` (strict records apply).
The image-type check is recorded as for any unit (`image_type_header_verified`, §4.4b).

All contradictions over all fast units are reported together as **one** `R_FAST_LAYOUT_CONTRADICTION`
whose detail lists **every** contradicting image, and for each image **every** contradiction found in
it: the FOV key and the path once, then per contradiction the kind, the C index or indices, and the
expected and found values (for example `C0: expected DNA (DAPI, Hoechst 33342),
found "Phalloidin-488"`; `3 channels, the list has 2`). The message names the fix: *tag the units of
these images on their own (`channels_from = "unit"`, confirmed per unit), then re-run.* Nothing is
reordered, dropped, split per FOV or guessed, and no per-FOV exception is created (§10).

**Relation to the existing codes.**

- In a unit with `channels_from = "experiment"`, `R_FAST_LAYOUT_CONTRADICTION` is the **only** code
  for channel count, header names and image type. It replaces `R_CHANNEL_COUNT_MISMATCH`,
  `R_HEADER_CONTRADICTION`, `R_IMAGE_TYPE_CONTRADICTS_HEADER` and those three parts of
  `R_UNIT_NOT_HOMOGENEOUS`: every image is compared with one list, so a difference between two
  images of the unit in count or type, or a header name that is evidence for no channel at its
  index, is a contradiction of at least one of them, and that image is named. One code keeps the
  one fix and the one complete list FC4 asks for.
- `R_UNIT_NOT_HOMOGENEOUS` stays, in a fast unit, for **interpreted axes** only (not part of the
  channel statement).
- `R_RGB_OVERRIDE_NOT_THREE_SAMPLES` keeps its priority on a unit that declares
  `rgb_header_override = true` (owner answer of 14 November 2026): it names the image that breaks the
  override's condition, and that image is not also listed as a fast contradiction.
- A unit with `channels_from = "unit"` is checked exactly as in a strict file: its own codes and
  precedence, unchanged.
- A publication or a run reports `R_FAST_LAYOUT_CONTRADICTION` beside every other applicable `R_*`
  code (AQ2); one publication carries it at most once, with all images.

### Interactions

**RGB units and RH1.** An RGB experiment in fast mode has `channel_layout.image_type = "rgb"` and
`channels = ["R", "G", "B"]` (`v43`); RGB channels have no aliases (§4.4b), so its units are accepted
under the statement and checked on count and colour interpretation. `rgb_header_override` stays a
**per-unit** declaration (RH1): never a field of `channel_layout` (`i148`), never inferred, never
copied from one unit to another. Homogeneity and the fast-mode type test use the unit's effective
type, so a CTRL unit with a valid override and a DrugA unit whose header says RGB are both `rgb`. An
image whose header contradicts `rgb` in a unit without the override is an `image_type` contradiction;
when that image has three interleaved samples, the message also names `rgb_header_override` for its
unit, as `R_IMAGE_TYPE_CONTRADICTS_HEADER` does today (§8). Declaring the key is itself a per-unit
user action.

**Heterogeneous layouts (Stage 3).** The units that follow the experiment list share one layout.
A unit tagged on its own with another list or image type makes the description heterogeneous
(`v42`), and is then processed or refused exactly as a strict file with the same lists:
`R_HETEROGENEOUS_LAYOUT_NOT_ENABLED` where it applies. Fast mode lifts nothing and adds nothing to
Stage 3. Different channel sets across units, partial channel presence and the normalization opt-in
`partial_channels = "planes_with_channel"` (CellPatcher and preprocessing; `A_SCOPE_INCOMPLETE`
otherwise, SI1) are untouched: an extra channel in some acquisitions is a unit tagged on its own,
which fast mode never pads, drops or reorders.

**Reopen and append (P15).** New FOVs in an existing fast unit are checked against
`channel_layout` at every reconciliation and run. Those that satisfy it are reported and recorded
and reopen nothing (D6, P15); any that contradict it refuse publication and the run with
`R_FAST_LAYOUT_CONTRADICTION` naming them. A new unit discovered under a fast-mode file is drafted
with `channels_from = "experiment"` and the materialised list; it is pending like any new unit (its
grouping is confirmed by the user and its repeat's N35 confirmation reopens, §10), and its images
are checked the same way (`t19`). The draft never sets `unit` on its own: switching is the user's.

**Aliases.** `header_names` stay on the channel, so an alias saved for one unit is evidence for that
channel in every unit, fast or tagged (FC3, "or a saved alias"). When the user tags the one unit
whose order becomes the experiment list, its header names are confirmed as `header_names` entries.
Saving an alias is adding (not a changed entity, §4.6) and reopens nothing. Two images of one fast
unit whose names at C*i* are different confirmed aliases of the same channel (`DAPI` and
`Hoechst 33342`) are accepted: each carries evidence for that channel, and each name is recorded as
read (see open question O1).

**Switching modes.** Adopting fast mode on a published strict file (`t16`), giving it up, and
moving one unit between `experiment` and `unit` are user actions published as a new file; no reader
and no reconciliation switches on its own, and a strict file is never converted. `channels_from`
records how a list was confirmed, not what it is, so a switch alone reopens no N35 confirmation
(`t16`; a re-dated repeat is `R_CONFIRMED_ON_CHANGED`, `t17`) and changes no section digest. A change
of `channel_layout.channels` or `image_type` changes the list of every unit that follows it: those
repeats reopen, and positions that move are a changed entity (`R_CONFIRMED_ID_CHANGED` without the
recorded confirmation, `t20`). `channel_layout.confirmed_on` is kept byte-identical unless the
table's list or type changes (`R_CONFIRMED_ON_CHANGED`, `t18`).

### Versioning and the no-backward-compatibility rule (ADR 0002 AR10)

An **amendment of v1**, as PL1 and RH1 were, not `schema_version` 2:

- Every file valid before stays valid with the same meaning: the table is absent there, which
  means strict per-unit, exactly what those files were.
- A reader pinned to an earlier Spec commit refuses `channel_layout` and `channels_from` as
  `E_UNKNOWN_FIELD`; it never misreads a fast-mode file as strict.
- FC1's default is a **writer** default (notebook, CLI) for new descriptions. It does not change what
  any existing field means, so it needs no version.
- AR10 removes compatibility code and refuses old versions instead of converting them. Nothing here
  is compatibility: strict per-unit is a mode the owner kept (FC1), and the absent table is its one
  spelling. No conversion is written: a published strict file stays strict until the user adopts
  fast mode.
- Rejected: `schema_version` 2. With no migration (AR10 (7)), every published v1 file would be
  refused, for no change of meaning. Also rejected: making the table required, with an explicit
  strict value: every published file would become invalid, and the same "all units confirmed per
  unit" would gain a second spelling.

Consequence for implementation order: preprocessing can neither write nor read a fast-mode file
until it pins a Spec commit with this amendment. FC1's default switches together with that pin.

### Digests

`channel_layout` is not a section and is in no section digest (like `used_ids`); `channels_from`
is omitted from every digest. What products depend on is each unit's list, which is in the
`repeats` digest as before; how it was confirmed changes no pixel-to-channel mapping. A changed
experiment list changes the materialised unit lists, and so the `repeats` digest. `t16` has the
four digests of `v01` (checked by `refval.py fixtures`).

## Fixtures and validator

| Fixture | Expected | Shows |
|---|---|---|
| `v41` | pass | Fast mode, every unit materialised; one unit tagged on its own with the same list |
| `v42` | pass, heterogeneous | A unit tagged on its own with another order (FC4's fix) |
| `v43` | pass | RGB fast mode; RH1 override per unit |
| `i142` | `E_FAST_LAYOUT_MISMATCH` | A unit marked `experiment` with another order |
| `i143` | `E_FAST_LAYOUT_MISMATCH`, `E_RGB_TOKEN_MISUSE` | A unit marked `experiment` without the list's `image_type` |
| `i144` | `E_MISSING_FIELD` | A unit of a fast-mode file without `channels_from` |
| `i145` | `E_FAST_MARKER_WITHOUT_LAYOUT` | `channels_from` in a strict file |
| `i146` | `E_ENUM` | `channels_from = "Experiment"` |
| `i147` | `E_UNKNOWN_CHANNEL` | The experiment list names an undeclared channel |
| `i148` | `E_UNKNOWN_FIELD` | `rgb_header_override` in `channel_layout` |
| `i149` | `E_EMPTY` | An empty experiment list |
| `i150` | `E_MISSING_FIELD` | `channel_layout` without `confirmed_on` |
| `i151` | `E_ID_NOT_NFC` | A decomposed entry in the experiment list (phase 4) |
| `t16` | accepted (vs `v01`) | Adopting fast mode reopens nothing; digests unchanged |
| `t17` | `R_CONFIRMED_ON_CHANGED` (vs `v01`) | Adopting fast mode is not a reopening |
| `t18` | `R_CONFIRMED_ON_CHANGED` (vs `v41`) | The statement's date is a user fact |
| `t19` | accepted (vs `v41`) | Appending a repeat whose units follow the list |
| `t20` | `R_CONFIRMED_ID_CHANGED` (vs `v41`) | Restating the list in another order moves positions |

`tools/audit/refval.py` implements the table and the key (phases 3-5), the writer order, the digest
omission, the two-file `confirmed_on` check of the table, and the `t16` digest check. **A writer
validates the whole candidate model before it writes** (experiment-v1 §9.1): the reference
`write()` refuses the model of `i142` with `E_FAST_LAYOUT_MISMATCH` and writes nothing
(`tools/test_spec_consistency.py`). The fixture oracle checks the exact error paths of
`i142`-`i151` (their `# Paths:` header line), not only the set of codes. The image
checks need images: scenarios P37-P40 of the conformance plan.

## Modelling choices for the owner's review

Not owner decisions; each may be amended.

1. **Names:** `channel_layout` (table), `channels_from` with `experiment` and `unit`,
   `R_FAST_LAYOUT_CONTRADICTION`, `E_FAST_LAYOUT_MISMATCH`, `E_FAST_MARKER_WITHOUT_LAYOUT`. The table
   is not named `experiment_*` (`experiment` is a forbidden name, §4.7) or `shared_*` (`shared` is the
   mask-axes field of §4.7).
2. **`confirmed_on` in the table.** FC2 records a user statement; the date makes "when" auditable and
   follows the §4.4a rules. Without it, a reader could not tell from the file when the statement was
   made.
3. **`channels_from` on every unit of a fast-mode file** (no default inside the file), and not
   allowed in a strict file.
4. **The tagged unit is not named in the file.** The list is its order; which unit the user tagged
   is recorded in the run manifest with the preview, not in the description (a unit path field would
   be a per-unit reference no reader uses).
5. **`channels_from` is confirmation provenance:** omitted from digests and from the layout compared
   for N35 reopening.
6. **Reuse of existing codes** for the experiment list's own rules (`E_UNKNOWN_CHANNEL`,
   `E_DUPLICATE_CHANNEL_IN_UNIT`, `E_ID_NOT_NFC`, `E_RGB_UNIT_CHANNELS`, `E_RGB_TOKEN_MISUSE`),
   extended in meaning, instead of new codes per rule.
7. **One fast-mode code** that replaces the per-unit count, header and type codes in fast units
   (above), with the kind as message detail, not as separate codes. An image's entry lists every
   kind found in it (revised after the external review of 18 November 2026; the first draft kept
   only the first kind per image).

## Open questions

- **O1. Different confirmed aliases inside one fast unit.** Recommendation: accept (each image has
  evidence for the channel at its index; FC3 is a per-image rule) and record each name as read.
  Alternative: keep strict's rule that header names at one C index are equal across a unit's FOVs,
  reported as a fast contradiction.
- **O2. The `rgb_header_override` hint.** Recommendation: the fast-mode message names the RH1 key for
  an image with three interleaved samples whose header contradicts `rgb`, beside the per-unit fix,
  as `R_IMAGE_TYPE_CONTRADICTS_HEADER` does today. Alternative: name only FC4's fix.
- **O3. Spec §8 is behind preprocessing on heterogeneity.** At preprocessing `9115f39`,
  `src/morphobricks_preprocessing/description_layouts.py:1-12` refuses only units of different image
  types (owner decision of 11 November 2026, S3.3); different channel lists of one image type are
  processed. experiment-v1 §8 still says "Stage 1-2 only: the units do not all have the same ordered
  list". This ADR does not change that row; recommendation: record the 11 November decision in its
  own Spec PR.
