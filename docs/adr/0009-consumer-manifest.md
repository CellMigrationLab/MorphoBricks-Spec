# ADR 0009: consumer manifest (early dimension checks in preprocessing)

- **Status:** **Proposed** (owner decisions of 24 November 2026, CM1-CM5 and the owner answers O1-O8
  below, final and not to be reopened by the review). Not implemented. What this ADR adds is their
  encoding: the file, its fields, how preprocessing finds it, where the check sits in the
  preprocessing flow, the refusal codes, the fixes offered, the record in the run manifest, and the
  interactions with RC1, ADR 0002 AR3, ADR 0005, ADR 0006, ADR 0007 and
  morphobricks-preprocessing#438. The choices those decisions do not cover are listed under
  [modelling choices](#modelling-choices-for-the-owners-review), for the owner's review. No question
  is open: O1-O8 were answered on 24 November 2026. Tracking: Spec #54. **Revised** after review
  *at* (24 November 2026, verdict "do not accept", blockers B1-B10, file items F1-F4): every finding
  was checked against the cited sources and holds; the encoding is repaired, no owner decision is
  reopened ([responses](#review-at--responses)).
- **Absorbs** morphobricks-preprocessing#438 ("Move the Z-stack gate from the description step to
  the hand-off"): its owner decisions of 23 November 2026 are CM5 here, and this ADR states how a
  chosen consumer's manifest interacts with #438's mixed-run warning. It does **not** write #438's
  own normative change of experiment-v1 §1; that is a separate prerequisite
  ([prerequisites](#prerequisites-of-the-volume-rules)).
- **Amends, on acceptance:** the refusal table of experiment-v1 §8 (four `R_*` rows and their
  precedence, below). The file format itself is normative text of its own, in a new
  `docs/consumer-manifest-v1.md`, written on acceptance from the
  [file section](#the-file-morphobricks_consumertoml); it is not a section of experiment-v1 (owner
  answer O8). Nothing of `morphobricks.toml` changes: no field is added, and the consumer is never
  written into the description (experiment-v1 §1 excludes brick names and routing; ADR 0001
  decision 10, "no brick routing"). It changes no other experiment-v1 rule: in particular §1's
  "v1 analyses 2-D planes only" stays until the separate #438 amendment (prerequisite P-1) is
  accepted. It amends **no** rule of ADR 0007: the reuse consequence of the new run-manifest field is
  stated under [the record](#the-record-where-it-lives). No fixture, golden or validator changes in
  this PR; the fixtures and conformance rows below are proposed.
- **Base:** MorphoBricks-Spec `main` `232fb38880cc487510532d99dc71d46a27005f23`. Evidence read at
  morphobricks-preprocessing `main` `abacc4007cb13ec08728da8befd79e0111971a63` and MorphoFeature
  `main` `58aa19b849946426961e5c9be495b4ab41a366e2`.
- **Why a new ADR file.** Like ADR 0006 and ADR 0007: a new policy with its own decision set, its own
  file format, refusal codes and a place in the preprocessing workflow. It changes no rule of
  ADR 0001 or ADR 0002.

## Context

Today a run whose images the next app cannot take is refused late. Preprocessing refuses one thing
early, for everyone: an image with more than one depth slice (`z_stack_not_supported`,
`metadata.check_metadata(files, allow_z=False)`, preprocessing `metadata.py:391-431`, with the
projection card of `notebook_projection.py` as the fix). Everything else that depends on the next
app is refused only when that app opens `RunInputs` or later:

- `A_RGB_NOT_SUPPORTED` for a consumer whose `Capabilities.rgb_support` is false, and
  `A_VOLUME_NOT_SUPPORTED` for a `volume` request without `Capabilities.volume_support`
  (preprocessing `run_inputs_request.py:120-140`, `volume_refusals` at `:557-598`; ADR 0001 RC1,
  ADR 0002 AR3, ADR 0005 BM5). AR3's flag guards a **requested Z-volume selection** only: a `plane`
  request (the default, `run_inputs_request.py:169-193`) on Z-stacks is not refused for lack of
  `volume_support`;
- MorphoFeature's own provider checks, after the run (`morphofeature/provider_lookup.py`
  `declared_rgb_support`; `providers.py`, the static provider manifest `morphofeature_provider.json`).
  MorphoFeature today expands every Z slice of an image into a 2-D plane
  (`run_config._planes`, `:440-445`): it has no Z refusal of its own.

By then the user has confirmed axes, tagged every channel, built the design, saved the description
and run preprocessing. A tool that takes one channel only, or no time-lapse, or that needs Z-stacks,
has no way to say so before that work is done. The owner decided on 24 November 2026 that the next
app (the **consumer**: MorphoFeature, OpticalFlow3D and others) declares what it allows in an
external **consumer manifest**, and that preprocessing checks it early. With no manifest, everything
is allowed, as today.

The rules this must keep: nothing guessed (axes are user-confirmed roles, the image type is a
user-confirmed declaration, ADR 0001 AQ6); no silent drop, slice, projection or conversion; every
refusal names what is wrong and how to fix it; core discovery stays inert (no consumer module is
imported, and no import machinery runs, to find its manifest); the consumer's own runtime refusal
stays, and must exist for every restriction it declares (a manifest is an early error, never the
only guard).

## Decisions

### Owner decisions of 24 November 2026 (recorded, accepted; not reopened by this ADR)

**Purpose.** An external manifest that declares what the next app (the consumer, for example
MorphoFeature or OpticalFlow3D) allows, so that preprocessing errors early, before MorphoFeature or
the bricks. With **no** manifest, everything is allowed (today's behaviour).

**Intended preprocessing flow.** (1) Scan headers and folder layout; (2) validate axes; (3) check the
manifest, if any: problems must be resolved; (4) tag channels; (5) 2-D images get histograms and QC,
3-D images skip them for now; (6) match images to mask classes.

| # | Decision |
|---|---|
| CM1 | **Source.** A manifest is shipped by the consumer package (discoverable when the package is installed) **and** may be bundled by LabConstrictor apps |
| CM2 | **Several consumers available.** The user picks one; that one is checked and recorded |
| CM3 | **Mismatch.** The run is blocked, and preprocessing offers the fixes it has: exclude the offending images, choose another consumer; Z projection only where preprocessing actually has it |
| CM4 | **v1 rules: dimensions only.** Which axes may be present: multichannel, multi-Z, multi-T, RGB; channel count limits; mixed 2-D/3-D within one run. Pixel types, calibration, channel IDs and masks are **out of v1** |
| CM5 | **Earlier 3-D decisions folded in** (preprocessing#438, owner comments of 23 November 2026): histograms, normalization and QC metrics are **disabled** for volumes at first (recorded as not computed, never empty or zero); a Z run goes only to volume-capable bricks (`volume_support`); a run mixing 2-D and 3-D images is refused by MorphoFeature and only **warned** about in preprocessing, the warning recorded in the run's checks |

### Owner answers of 24 November 2026 (O1-O8; recorded, accepted; not reopened by this ADR)

These answer the eight questions this draft put to the owner. Each is encoded where it applies below
and is marked there by its ID.

| # | Question | Owner answer |
|---|---|---|
| O1 | No pick while consumers are installed (CLI, scripts) | The check is skipped; the run records the available consumers. No refusal for omission |
| O2 | The same consumer from a package and from a LabConstrictor bundle | The two copies must be byte-identical (same SHA-256), else refused (`R_CONSUMER_MANIFEST_CONFLICT`). The bundled file never wins |
| O3 | One available consumer | Never preselected, even with one consumer: the user still clicks. *No consumer check* stays an explicit entry |
| O4 | MorphoFeature's `rgb_support` | `true` if **any** installed provider declares it; each provider still refuses at run time |
| O5 | Should consumers read `consumer_check`? | Not in v1: it is provenance only |
| O6 | Mask matching order | Keep today's notebook order: masks are paired before the run |
| O7 | `describe` and publication | The check also blocks `describe --consumer` publishing; *No consumer check* can still publish |
| O8 | Where the normative text lives on acceptance | A new `docs/consumer-manifest-v1.md` plus four rows in the refusal table; not a section of experiment-v1 |

### Prerequisites of the volume rules

The `volume` and `mixed_volumes` rules are specified now so that manifests are written once, but they
take effect only when **both** prerequisites below are accepted and implemented (review *at* B1, B2).
Until then preprocessing refuses every Z-stack for everyone (`z_stack_not_supported`), so neither
kind can occur, and preprocessing's #438 step that lifts that refusal MUST NOT land before them.

- **P-1, the #438 normative amendment of experiment-v1 §1 (separate, not written here).**
  experiment-v1 §1 says "v1 analyses 2-D planes only. A Z stack is projected by a recorded
  preprocessing step before it is described". Accepting unprojected volumes (CM5) changes that
  sentence, and it is #438's change, in its own reviewed Spec amendment: which volumes may be
  described, how §8's homogeneity reads `Z`, and that histograms, normalization and QC are recorded
  as not computed for them. This ADR does not write it, adds no Z, axes or shared-plane field to
  `morphobricks.toml`, and does not put the consumer format into experiment-v1 (O8).
- **P-2, MorphoFeature's Z and mixed runtime guard (#438's MorphoFeature step).** MorphoFeature
  refuses, on every route it opens a run (notebook, command line, run file), a run with any image
  whose `Z` > 1 while none of the run's providers takes volumes, and a run mixing `Z` > 1 and
  `Z` = 1 images (CM5), from the `Fov` sizes `RunInputs` gives, before any provider runs and
  whatever `consumer_check` says (O5). Today it expands the slices into planes
  (`run_config._planes`, `:440-445`), which this guard replaces for such runs. P49 below is valid
  only once P-2 is implemented.

### The principle: a manifest narrows, it never widens

A consumer manifest can only **add** refusals to what preprocessing already refuses for everyone. It
never lifts one: a manifest with `volume_support = true` does not make preprocessing accept a Z-stack
while `z_stack_not_supported` is still in force, and a manifest that allows something preprocessing
cannot record (a pixel type, an axis role outside `X Y Z C T`, `axes.py:39`) changes nothing. And it
never replaces the consumer's runtime refusal
([Interactions](#the-consumers-own-runtime-guards-every-declared-restriction-every-route)).

### The file `morphobricks_consumer.toml`

A small TOML file with a schema identifier and a version, parsed with the strict rules of
experiment-v1 §2 items 2-4 (UTF-8 without BOM, TOML 1.0, duplicate keys refused, no type conversion,
closed field sets, no extension namespace). Example: a single-channel time-lapse tool that takes
Z-stacks.

```toml
schema = "morphobricks-consumer"
schema_version = 1
consumer = "opticalflow3d"
display_name = "OpticalFlow3D Profiler"

[dimensions]
multichannel_support = false
rgb_support = false
time_support = true
volume_support = true
mixed_volume_support = false
```

| Key | Type | Required | Meaning |
|---|---|---|---|
| `schema` | text | yes | Exactly `morphobricks-consumer` |
| `schema_version` | integer | yes | `1`. A reader refuses a version it does not know |
| `consumer` | text, a Token (experiment-v1 §3.2) | yes | The consumer's ID: what the user picks, what the run records, what the discovery entry point (or the bundle declaration) is named |
| `display_name` | text, non-empty | yes | What the picker shows |
| `dimensions` | table | yes | The v1 rules below; closed field set |
| `snapshot` | table | no | The installed plug-ins a derived rule was computed from ([below](#derived-rules-the-snapshot-table)); closed field set |

**Consumer IDs (F3).** IDs are compared exactly (NFC, case-sensitive). Two discovered IDs that differ
but whose `str.casefold()` forms are equal are a collision (`E_ID_CASE_COLLISION`, experiment-v1
§3.3's rule applied to the scope "consumer IDs of one environment and its bundles"): both are
refused as `R_CONSUMER_MANIFEST_CONFLICT`. `--consumer` matches exactly; a request that matches a
discovered ID only after case folding is `R_CONSUMER_NOT_FOUND`, naming the near match.

`[dimensions]`, every rule decided from **confirmed** axis roles and the **confirmed** image type of
each included image, never from pixels and never from header letters alone:

| Key | Type | Required | An included image is refused for this consumer when |
|---|---|---|---|
| `multichannel_support` | boolean | yes | `false` and the image is a channel image whose confirmed `C` role has size > 1 |
| `rgb_support` | boolean | yes | `false` and the image belongs to a unit whose confirmed image type is `rgb` (ADR 0001 AQ6; the meaning of RC1's provider key) |
| `time_support` | boolean | yes | `false` and the image's confirmed `T` role has size > 1 |
| `volume_support` | boolean | yes | `false` and the image's confirmed `Z` role has size > 1 (a one-slice `Z` is a plane). Stronger than AR3: see *Vocabulary* |
| `mixed_volume_support` | boolean | yes | `false`, `volume_support` is `true`, and the included images are not all of one kind: some have `Z` > 1 and some do not (a run-level rule, CM5) |
| `min_channels` | integer ≥ 1 | no | The image is a channel image with fewer channels (absent: no lower limit beyond 1) |
| `max_channels` | integer ≥ 1 | no | The image is a channel image with more channels (absent: no upper limit) |

- A channel image without a `C` role has one channel; so has one whose `C` has size 1. An RGB image
  is governed by `rgb_support` alone: its three samples are not stains, and the channel rules do not
  count them (an RGB image never fails `max_channels = 1` or `multichannel_support = false`).
- A singleton `T` or `Z` (size 1) is no time-lapse and no volume.
- **Contradictions are only unsatisfiable rule sets (B4)** (`E_CONSUMER_RULE_CONTRADICTION`):
  `mixed_volume_support = true` with `volume_support = false` (a mix needs volumes);
  `min_channels > max_channels`; and `multichannel_support = false` with `min_channels > 1` (no
  channel image could pass). `multichannel_support = false` with `max_channels` above 1 is **valid**:
  a one-channel image satisfies both, and the effective upper limit is 1.
- A non-boolean value is `E_TYPE`, never read as `true` or `false` (the RC1 modelling rule).
- Pixel types, calibration, channel IDs and masks (CM4) are not fields: a `pixel_types`,
  `calibration`, `channels` or `masks` key is `E_UNKNOWN_FIELD`.

**Vocabulary.** `rgb_support` keeps RC1's meaning. `volume_support` keeps the **word** of AR3 and of
provider manifests, with a stronger early meaning stated here: in a consumer manifest, `false` says
the consumer takes **no image with `Z` > 1 in any form** (as planes or as a volume); AR3's
`Capabilities.volume_support = false` refuses only a requested `volume` selection. The two are not
claimed equivalent at run time: the consumer's guard for the stronger rule is its own (P-2 for
MorphoFeature; [Interactions](#the-consumers-own-runtime-guards-every-declared-restriction-every-route)).
The new keys follow the same `<axis>_support` pattern. In a provider manifest an absent capability
means `false` (RC1); in a consumer manifest every boolean rule is **required**: a consumer manifest
exists only to state the rules, and an absent rule would otherwise be a silent refusal (or a silent
permission) that the author never wrote.

#### Derived rules: the `[snapshot]` table

A consumer whose rule depends on the plug-ins installed beside it (MorphoFeature's `rgb_support`, O4:
true if **any** installed provider declares it) states that dependency, so that preprocessing can
verify the value is current without importing or interpreting the plug-ins (B3):

```toml
[snapshot]
entry_point_group = "morphofeature.providers"
member_file = "morphofeature_provider.json"
derives = ["rgb_support"]

[[snapshot.members]]
name = "morphoobjects"
distribution = "morphoobjects"
version = "0.9.1"
file_sha256 = "<SHA-256 of that distribution's member_file bytes>"
```

| Key | Type | Required | Meaning |
|---|---|---|---|
| `entry_point_group` | text, non-empty | yes | The entry-point group whose members the derived rules were computed from |
| `member_file` | text, a file name without a path separator | yes | The file each member ships beside its top-level package |
| `derives` | array of the boolean `[dimensions]` keys, non-empty, no duplicates | yes | The rules computed from the members; the others are fixed |
| `members` | array of tables `name`, `distribution`, `version`, `file_sha256`, sorted by `name`; may be empty | yes | Every member installed when the file was written |

The consumer's own tool writes it (MorphoFeature: [below](#morphofeatures-manifest)); preprocessing
**verifies** it, every time the consumer is discovered: it lists the group's installed entry points
from distribution metadata only, locates each member's `member_file` by the safe package rule of
[discovery](#discovery-cm1) (the entry point's value as the top-level package), hashes the bytes and
compares the set of `(name, normalized distribution, version, file_sha256)` with `members`, both
ways. Any difference, or a member file that cannot be located safely, is `E_CONSUMER_SNAPSHOT_STALE`
naming every added, removed and changed member; the consumer is then unavailable from that source
(`R_CONSUMER_MANIFEST_INVALID`). Preprocessing never parses a member file and never recomputes a
derived value: it proves only that the inputs are the ones the consumer derived from. A stale file
is never read as if its value were current.

### Discovery (CM1)

Both sources yield **candidates**: a source, the ID it is declared for, its bytes (read once), their
SHA-256 and the validation result of **those** bytes. No candidate is found by executing code: no
`EntryPoint.load`, no `import`, no `importlib.util.find_spec` (it consults `sys.meta_path` finders and
path hooks, which may run code), no `.pth` evaluation beyond what the interpreter already did.

**Shipped by the consumer package (B6).** A distribution declares an entry point in the group
`morphobricks.consumers`, named by its consumer ID, whose value is its top-level package (for
MorphoFeature: `morphofeature = "morphofeature"`). Preprocessing reads the group from each
installed distribution's metadata (`importlib.metadata.distributions()`, then that distribution's
`entry_points`), so every entry point is attributed to its **declaring distribution**, and then:

1. The name must be a Token (`E_ID_SYNTAX`); the value must be one top-level package name, an
   identifier without `.`, `:`, `[extras]` or spaces (`E_CONSUMER_ENTRY_POINT`).
2. The file is located through the **declaring distribution's installed-file inventory**
   (`Distribution.files`, its `RECORD`): it must list exactly `<value>/morphobricks_consumer.toml`
   and `<value>/__init__.py` (a regular package: a namespace or multi-location package is refused),
   and the path is `Distribution.locate_file` of that entry. A distribution without an inventory
   (some editable installs), an entry not listed, or the same relative path listed by another
   installed distribution is `E_CONSUMER_SOURCE_UNSAFE`. A consumer in development is given as a
   bundle (below).
3. The file must be contained and plain: its resolved path lies under the distribution's install
   root and under `<value>/`; no component from that root down is a symbolic link (`lstat`); the
   file is a regular file; and when the inventory records a hash for it, the bytes match it. Each
   failure is `E_CONSUMER_SOURCE_UNSAFE`, naming the path and the reason.
4. The entry point's name must equal the file's `consumer` (`E_CONSUMER_ID_MISMATCH`).

MorphoFeature's provider discovery (`providers.py:266-277`, `find_spec` and `is_file`, which follows
symbolic links) is **not** the model for this: it was the draft's model and is not safe enough (B6).

**Bundled by a LabConstrictor app.** The app names each manifest **with the ID it is for**: the
notebook API takes `consumer_manifests={"<ID>": path, ...}`, which an app sets in the notebook's
hidden setup cell (where LabConstrictor already reads `current_version` and `notebook_name`,
preprocessing `README.md:122`), and the CLI takes `--consumer-manifest ID=PATH` (repeatable). No
folder is scanned. The declared ID must be a Token and equal the file's `consumer`
(`E_CONSUMER_ID_MISMATCH`), so a bundle that does not parse is still attributed to an ID (B5). The
path's last component must not be a symbolic link and must be a regular file (opened without
following a link where the platform allows), as `morphobricks.toml` is (`R_FILE_SYMLINK`'s rule,
reported as `E_CONSUMER_SOURCE_UNSAFE`).

**Classifying one ID (B5, F1, O2).** For each ID, over **all** its candidates, valid or not, in this
order; the three outcomes are mutually exclusive:

1. **Conflict** (`R_CONSUMER_MANIFEST_CONFLICT`): the ID collides by case with another (F3); or it is
   declared by two distributions (MorphoFeature's provider rule, `providers.py:549-552`); or its
   candidates hold two or more different SHA-256 (package versus bundle, O2: the bundled file never
   wins; two bundles, F1; an invalid copy counts with its bytes). Every candidate is named with its
   source, SHA-256 and, if any, its own `E_*` reasons.
2. **Invalid** (`R_CONSUMER_MANIFEST_INVALID`): not a conflict, and the one byte content, or any of its
   sources, fails a rule (file rules, `E_CONSUMER_SOURCE_UNSAFE`, `E_CONSUMER_ENTRY_POINT`,
   `E_CONSUMER_SNAPSHOT_STALE`). Every reason of every candidate is listed. A valid copy from another
   source does not hide an invalid one.
3. **Available:** one byte content, valid, every source sound. Identical copies (package and bundle,
   or two bundles) are **one** consumer whose record lists every source.

An ID with no candidate at all is **not found** (`R_CONSUMER_NOT_FOUND`) and only then. Nothing is
chosen by source or enumeration order: candidates are listed sorted by source kind (`package` before
`bundled`), then normalized distribution name or path, in code-point order. An unavailable consumer
blocks nothing unless the user, or the CLI, names it.

### The choice (CM2)

- The notebook shows one picker, *Next app (consumer)*, listing every available consumer by
  `display_name` with its ID and sources, then every unavailable one with its refusal and reasons,
  and the entry *No consumer check*. Available entries are sorted by `display_name` after NFC and
  case folding, then by ID, independent of entry-point enumeration (F3); unavailable ones by ID.
  Nothing is preselected, also when one consumer is available: picking is the user's answer (owner
  answer O3). With no manifest found, the picker says so in one line and the run behaves as today.
- The CLI takes `--consumer ID` or `--no-consumer`. Without either, no consumer is checked and the
  run's report lists the consumers that were available (owner answer O1); omission is never a
  refusal, so existing scripts behave as today. `describe` takes the same two options
  (`describe --consumer ID`, owner answer O7). An ID with no candidate is `R_CONSUMER_NOT_FOUND`,
  naming the available IDs and the unavailable ones with their refusal; an ID that has candidates is
  refused with its own class (conflict or invalid), never as not found.
- The notebook keeps the pick (ID and pinned SHA-256) with its other run settings, as it keeps the
  exclusions and the histogram settings for a reopened experiment (`notebook_prefill.py`); it is
  never written into `morphobricks.toml`. A reopened experiment whose saved pick has no candidate any
  more is `R_CONSUMER_NOT_FOUND`; one whose saved pick now has other bytes is refused as below
  (`E_CONSUMER_CHANGED_SINCE_CHECK`) until the user checks again. Neither falls back to *No consumer
  check* or to another consumer.

### Where the check sits in the flow

Mapped on the shipped notebook's seven steps (`notebook_steps.py:1-22`, `:149-178`):

| Owner flow | Notebook today | With this ADR |
|---|---|---|
| (1) Scan headers and folder layout | Step 1 *Images* (quick scan, then every header on a click; `run/preflight.py:169-260`) | Unchanged. The consumer can be picked here already |
| (2) Validate axes | Step 2 *Axes* (roles, pixel size; projection card) | Unchanged |
| (3) Check the manifest | (none) | **New.** The `Z`, `T`, `C` and mixed rules are checked as soon as the axis roles are confirmed; the `rgb` rule as soon as the image type is confirmed |
| (4) Tag channels | Step 3 *Channels*: confirm the image type, then name the stains and tag | Naming and tagging open only when the check passed for the current state (or no consumer is checked) |
| (5) Histograms and QC for 2-D; skipped for 3-D | Step 7 *Run* | Unchanged by this ADR; volumes skip them under #438 (CM5) |
| (6) Match images to mask classes | Step 4 *Masks* pairs masks before the run; the mask step reads them after it | Unchanged: today's order is kept (owner answer O6) |

**One refinement of the owner's step order, with its evidence.** The owner placed the check after the
axes and before channel tagging. All rules but one can be decided there. `rgb` cannot: the image type
is a user-confirmed declaration that the notebook proposes at the quick scan and confirms at the start
of step 3, *before* the stains are named and tagged (`notebook_steps.py:7-11`, `CHANNELS_INTRO`), and a
header saying RGB is evidence, never the type (ADR 0001 AQ6, RH1). So the check completes in two
moments, both before tagging: the axis rules at axis confirmation, the `rgb` rule at image-type
confirmation. Tagging opens only after both. Checking RGB from the header at axis time was rejected:
it would decide a user declaration from a header (an RH1 override unit says the opposite of its
header).

**What a check is bound to (B8).** A check result is valid for one exact state, never for "the
consumer" in general:

- **Pinned bytes.** Picking a consumer discovers it (all candidates, classified as above), reads its
  bytes once, parses and validates **those** bytes and pins their SHA-256 and source list. The rules
  applied are always the rules of the pinned bytes; a file is never re-read to apply them.
- **Candidate-state fingerprint.** The SHA-256 of the canonical JSON (experiment-v1 §9 form) of:
  the pinned SHA-256 and sources; the snapshot verification result (the verified `members`, or
  none); every included image (FOV key, relative path, the header fingerprint the scan bound, its
  confirmed roles and their sizes); the exclusion list; and every unit's confirmed image type
  (RH1 override included). The check records the fingerprint with its outcome.
- **Invalidation.** Any change to an input of the fingerprint (another pick, a reopened saved pick,
  the axis roles, the image type, an exclusion, a rescan, an added or removed image, the app's bundle
  list) voids the result: tagging and publication close again until the check passes for the new
  fingerprint. Tags already entered are kept, not re-confirmed by the check.
- **Pinned re-check at both commit boundaries.** Immediately before `describe` (or the notebook's
  description step) publishes a description, and immediately before `run` (notebook step 7, CLI
  `run`) reads any pixel and again before it publishes the run manifest, preprocessing re-discovers
  the ID, re-reads its bytes once and recomputes the fingerprint from the state it is about to
  commit. It publishes only when the SHA-256 and sources equal the pinned ones, the fingerprint
  equals the checked one, and the rules of those bytes pass; the record then names those bytes. Any
  difference is `R_CONSUMER_MANIFEST_INVALID` with `E_CONSUMER_CHANGED_SINCE_CHECK` (naming the
  pinned and the current SHA-256, or the inputs of the fingerprint that changed); nothing is
  published; the fix is to check again, which in the notebook is a visible step the user confirms.
  A changed file is never silently adopted and the record never names bytes that were not checked.

The check reads no pixel: confirmed roles, the sizes the headers give for them (`TiffMetadata`), and
the confirmed image type.

### Refusal codes

New `R_*` codes (preprocessing layer, experiment-v1 §8), proposed for §8 on acceptance. They are
four (O8); every other distinction is an `E_*` reason or a message detail.

| Code | Meaning |
|---|---|
| `R_CONSUMER_MANIFEST_INVALID` | The named consumer has candidates, is not a conflict, and its bytes or a source fail. Reasons: the experiment-v1 §2/§6 codes reused with their meaning (`E_FILE_ENCODING`, `E_TOML_SYNTAX`, `E_DUPLICATE_KEY`, `E_TYPE`, `E_UNKNOWN_FIELD`, `E_MISSING_FIELD`, `E_SCHEMA_ID`, `E_SCHEMA_VERSION_MISSING`, `E_SCHEMA_VERSION_UNSUPPORTED`, `E_ID_SYNTAX`, `E_TEXT_EMPTY`, `E_VALUE_RANGE`) and new ones: `E_CONSUMER_ID_MISMATCH` (the entry point's or the bundle declaration's ID is not the file's `consumer`), `E_CONSUMER_RULE_CONTRADICTION` (an unsatisfiable rule set), `E_CONSUMER_ENTRY_POINT` (an entry-point value that is not one top-level package name), `E_CONSUMER_SOURCE_UNSAFE` (not in the declaring distribution's inventory, outside its package, a symbolic link on the way, not a regular file, a hash differing from the inventory, a namespace or ambiguous package), `E_CONSUMER_SNAPSHOT_STALE` (the `[snapshot]` does not match the installed members), `E_CONSUMER_CHANGED_SINCE_CHECK` (the bytes, sources or candidate state differ from what was checked). Makes that consumer unavailable; blocks only when it is named |
| `R_CONSUMER_MANIFEST_CONFLICT` | The named ID collides by case with another, is declared by two distributions, or its candidates hold more than one SHA-256 (package and bundle, O2; two bundles). Names every candidate with source, SHA-256 and its own reasons |
| `R_CONSUMER_NOT_FOUND` | The consumer named (`--consumer`, or a reopened experiment's saved pick) has **no** candidate; names the available IDs, any case-folded near match, and the unavailable ones with their refusal |
| `R_CONSUMER_DIMENSIONS_NOT_ALLOWED` | Included images break the chosen consumer's `[dimensions]`. **One** refusal lists **every** offending image (FOV key, path) with **every** per-image kind found in it (`multichannel`, `channel_count`, `rgb`, `time`, `volume`; expected and found, for example `T = 40, consumer allows T = 1`); then, for the run-level kind `mixed_volumes`, **both groups in full**: every included image with `Z` > 1 (FOV key, path, `Z` size) and every included image with `Z` = 1 or no `Z` (FOV key, path), then the two counts (B7). Lists are sorted by FOV key, then path, in code-point order. It names the consumer, the manifest's SHA-256 and the fixes below. Nothing is dropped, sliced, projected or converted |

The kinds are message detail, not separate codes, as in `R_FAST_LAYOUT_CONTRADICTION` (ADR 0006,
modelling choice 7): one code, one complete list, one set of fixes.

**Precedence.** Preprocessing's own refusals come first: the check needs confirmed axes, so
`z_stack_not_supported` and the axis errors are resolved before it runs. For the named consumer,
exactly one of `R_CONSUMER_MANIFEST_CONFLICT`, `R_CONSUMER_MANIFEST_INVALID` and
`R_CONSUMER_NOT_FOUND` applies, decided by the classification above (conflict, then invalid; not
found only with no candidate); `R_CONSUMER_DIMENSIONS_NOT_ALLOWED` is computed only for an available
consumer. In the notebook, the consumer refusals are reported before any channel-tagging code (they
are decided before tagging opens). At a publication or a run they are reported beside every other
applicable `R_*` code (ADR 0001 AQ2); one run carries each at most once.

### Fixes offered (CM3)

What preprocessing has today (checked, not invented):

| Kind | Fixes |
|---|---|
| every kind | **Exclude the offending images.** The exclusion list exists in the notebook (the *exclude* field and the *exclude the blocking images* action, `notebook_folder.py:483-489`, `EXCLUDABLE_CODES` in `notebook_options.py:35`) and the CLI (`--exclude PATH`, `cli.py:189-195`); the action gains this code. Exclusion is the user's click and is recorded as every exclusion is |
| every kind | **Choose another consumer**, or *No consumer check* |
| `volume`, `mixed_volumes` | **Project the stacks**, offered **only after preprocessing's existing planner has accepted it for the actual input** (B10): `conversion_plan` with a projection (`_plan_projected`, `:251-285`), which calls `projection_plan.plan_projection` (`:40-128`), is run as a plan (nothing written) on the current included images, mapping, masks folder and the projection settings shown. It refuses OME-Zarr inputs, masks with a Z axis, a slice range that does not fit every stack, a pixel type or sum it cannot project exactly, and a projection over the memory limit. When it returns any refusal, the fix is **not** offered: the message says it is unavailable and quotes each planner refusal with the images it names, and only exclusion and another consumer remain. When it is offered, it is the recorded projection copy (`notebook_projection.py`, `conversion.convert_experiment`; methods `max`, `mean`, `sum` and a slice range, `projection.py:39`), the originals kept. For `mixed_volumes` the copy covers **every** included image, the one-plane ones included, each as an explicit entry of the recorded conversion (`_planned` for every header, `projection_plan.py:84-87`); the message says so. Nothing is silently dropped. Instead the user may exclude all volumes or all planes (two explicit actions; neither is preselected) |
| `time`, `channel_count`, `multichannel`, `rgb` | None beyond exclusion and another consumer. Preprocessing has no time-point selection or projection, no channel subset copy and no RGB-to-grey conversion (ADR 0001 RC1 forbids a silent one; ADR 0006 forbids dropping channels). The message says so instead of suggesting a tool that does not exist |

### The record (where it lives)

The run manifest (`run_manifest.json`) records the check under `consumer_check`:

```json
"consumer_check": {
  "consumer": "morphofeature",
  "display_name": "MorphoFeature",
  "schema_version": 1,
  "manifest_sha256": "<SHA-256 of the exact bytes checked>",
  "sources": [{"kind": "package", "distribution": "morphofeature", "version": "<installed version>"},
              {"kind": "bundled", "path": "<path as given>"}],
  "dimensions": {"multichannel_support": true, "rgb_support": false, "time_support": true,
                 "volume_support": false, "mixed_volume_support": false},
  "snapshot_members_sha256": "<SHA-256 of the canonical JSON of the verified members, or null>",
  "state_sha256": "<the candidate-state fingerprint checked>",
  "outcome": "passed"
}
```

With no consumer checked: `{"consumer": null, "available": ["<ID>", ...]}` (`[]` when none was
found; sorted by ID; available ones only, as O1 says). A run is published only with
`outcome = "passed"` or no consumer; a refused check publishes nothing. The same holds for
`describe --consumer ID` (the check also blocks publishing a description; owner answer O7); a
description or run published with *No consumer check* is not blocked. The record is provenance only:
no consumer reads it in v1 (owner answer O5). It is **not** in `morphobricks.toml` (experiment-v1 §1:
no brick names or routing; ADR 0001 decision 10).

**Run-manifest version and reader (B9).** Adding the key is a new run-manifest version:
**the next integer after the version current when it lands** (`MANIFEST_VERSION = "5"` at the
evidence commit, `manifest_versions.py:27`; ADR 0008 also takes a new version, and whichever lands
second takes the following number; the implementing PR states the number). Under preprocessing's
one-version rule (`READ_VERSIONS`, ADR 0002 AR11 (7)) the new reader reads that version only and
refuses every other one, so a version-5 reader never meets the field, and a version-5 manifest is
refused by the new reader with today's message (run preprocessing again). In the new version
`consumer_check` is **required** and read strictly: a closed field set per form (the checked form
above, or the `{"consumer": null, "available": [...]}` form), every field typed, an unknown or
missing field refused (`ManifestFormatError`), never dropped. Today's `RunManifest.from_dict` ignores
keys it does not know (`manifest.py:287-342`); the new field is parsed by it, not passed through.

**Reuse identity (B9; ADR 0007 not amended).** ADR 0007 puts the SHA-256 of the whole
`run_manifest.json` into an entry's `run_folder` identity (`0007:337-355`). So a changed
`consumer_check` **does** change the identity of every downstream output computed from that run
folder: a brick entry finds `ENTRY_OUTPUT_EXISTS` and computes nothing silently. This ADR keeps
that, and corrects the draft's claim that the record is "in no reuse key". Chosen: **the full
manifest SHA-256 stays in the identity** (option a of the review), rejected: a second, "scientific"
manifest digest that excludes `consumer_check` (option b). Reasons: it changes no accepted ADR and no
implemented key; it fails closed (a re-run with another pick never reuses an output silently); a
re-checked run is a re-run of preprocessing, which already rewrites `written_at` and so already
changes the SHA-256, so option b would gain no reuse in practice while adding a second digest
definition that every reader must implement identically. Listed as modelling choice 10.

### Interactions

#### The consumer's own runtime guards: every declared restriction, every route

A consumer still declares its `Capabilities` when it opens `RunInputs`, and is refused there as today
(`A_RGB_NOT_SUPPORTED`, `A_VOLUME_NOT_SUPPORTED`; MorphoFeature's provider checks). It does not read
`consumer_check` in v1, to skip a check or for any other purpose (owner answer O5). That alone does
**not** guard every manifest rule (B2): AR3 refuses a requested volume, not a `plane` request on
Z-stacks, and no resolver code exists for `T`, `C` counts or a mix. So, normatively:

- A consumer that publishes a manifest with a restriction (a boolean rule `false`, or a channel
  limit) MUST refuse, itself, a run that breaks it, on **every** route it opens a run, from the
  confirmed roles, sizes and image type `RunInputs` gives, before any computation, whatever
  `consumer_check` says or whether it is present (O1, O5). The refusal code is its own (the resolver
  codes where they apply).
- A restriction declared without that guard is a defect of the consumer, found by its conformance
  row: for each restricted dimension, a run made with *No consumer check* is refused by the consumer.
- For MorphoFeature: `rgb_support` is guarded per provider (MF-6, `mask_selection.py:335-336`);
  `volume_support = false` and `mixed_volume_support = false` are guarded only once P-2 exists.
  MorphoFeature restricts neither `T` nor `C`.

The manifest is an early error, not a contract that consumers trust. Conformance proves both: the
same run is refused early by the manifest and, with the manifest check skipped, by the consumer.

#### ADR 0001 RC1 and ADR 0002 AR3

`rgb_support` means the same thing in the three places; `volume_support` shares the word, with the
stronger early meaning of *Vocabulary* above. The consumer manifest is not a provider manifest:
MorphoFeature keeps reading `rgb_support` per provider from `morphofeature_provider.json` and passing
it as `Capabilities` (ADR 0002 AR7: MorphoFeature decides provider capability). The consumer
manifest describes the app as a whole for preprocessing's early check only.

#### #438 and ADR 0005 (volumes)

- Until prerequisites P-1 and P-2 are accepted and implemented, and #438's first step lands after
  them, preprocessing refuses every Z-stack for everyone (`z_stack_not_supported`), so the `volume`
  and `mixed_volumes` kinds cannot occur.
- After it, a Z-stack passes preprocessing's own checks; `volume_support = false` in the chosen
  manifest refuses it at step 3, with projection named as a fix only where the planner accepts it.
- **The mixed-run warning (CM5).** Preprocessing warns, for every run, when some included images have
  `Z` > 1 and others do not, and records the warning in the run's checks (#438, owner comment of
  23 November 2026). With a chosen consumer: `volume_support = false` refuses each volume as `volume`
  (the mix is not reported again); `volume_support = true` and `mixed_volume_support = false` turns
  the mix into the blocking kind `mixed_volumes`, listing both groups, and the recorded warning
  stays; `mixed_volume_support = true` leaves only the warning. With no consumer the warning is all,
  as #438 decided, and MorphoFeature's P-2 guard still refuses a mixed run. The manifest never makes
  the warning disappear.
- Histograms, normalization and QC for volumes (step 5) are #438's rule and are untouched here. A
  `volume` run never reaches `binary_mask_policy` (ADR 0005 BM5) through this check: that refusal
  stays at `RunInputs`; the early manifest does not replace it.

#### ADR 0006 (fast-mode channel layout)

The check runs before tagging, so before `R_FAST_LAYOUT_CONTRADICTION` can be computed. The two
never report the same thing: the manifest counts channels against the consumer's limits; fast mode
compares each image with the experiment's list.

#### ADR 0007 (run-folder entry)

A brick started on a validated run folder (`<brick>.run_folder`) is otherwise unaffected. A brick's
entry does not name the consumer a run was checked for and does not read `consumer_check` (owner
answer O5); the field changes its run-folder identity only through the manifest SHA-256 (above).

### MorphoFeature's manifest

From the code read: MorphoFeature runs time series (`run_config._planes`, `:440-445`, iterates `T`;
`attach_tracks`), takes several channels, expands every `Z` slice into a separate 2-D FOV today
(P-2 replaces that with a refusal), and requires `rgb_support` from every provider of a run (MF-6,
`mask_selection.py:335-336`). Its own distribution declares **no** provider: providers are other
distributions in the `morphofeature.providers` group (MorphoFeature `pyproject.toml` at the evidence
commit). So the draft's "the providers the release itself ships" is the empty set, and a fixed
`rgb_support` would contradict O4 in any real installation (B3).

The encoding of O4 (recommended):

- MorphoFeature ships `src/morphofeature/morphobricks_consumer.toml` with the entry point
  `[project.entry-points."morphobricks.consumers"] morphofeature = "morphofeature"`:
  `multichannel_support = true`, `time_support = true`, `volume_support = false`,
  `mixed_volume_support = false`, no channel limits, and `rgb_support` with a `[snapshot]`
  (`entry_point_group = "morphofeature.providers"`, `member_file = "morphofeature_provider.json"`,
  `derives = ["rgb_support"]`).
- The file is written by MorphoFeature's own command (for example
  `morphofeature consumer-manifest --write PATH`), which uses MorphoFeature's inert provider discovery
  (no provider import) to list the installed providers, applies O4 (`true` if any declares
  `rgb_support`) and writes the members with their SHA-256. The release writes the shipped file
  for the provider set it is released with (its documented install set).
- Preprocessing verifies the snapshot at every discovery. In an environment whose installed providers
  differ (an add-on installed, one removed or upgraded), MorphoFeature is **unavailable** as a
  consumer (`E_CONSUMER_SNAPSHOT_STALE`, naming each difference), never checked against a value that
  may be wrong. The user's fixes: install the release's provider set, or *No consumer check* (the
  runtime guards still apply). A bundled regenerated copy does **not** override a stale package copy
  (O2: the bundled file never wins; differing bytes are a conflict).

Consequence for the owner's review (modelling choice 14): with this encoding MorphoFeature is
checkable only in environments matching its release's provider set. The alternative that would
follow every installation, MorphoFeature shipping no package manifest and LabConstrictor apps
bundling a generated one, reads CM1 as permitting a consumer to use the bundle source alone; it is
not chosen here because CM1 says the consumer package ships the manifest.

## Rejected alternatives

- **Fields in `morphobricks.toml`.** The description says what the experiment is; which app runs next
  is routing (experiment-v1 §1, ADR 0001 decision 10), and one experiment can feed several consumers.
- **Reading the provider manifests directly.** Preprocessing would interpret MorphoFeature's
  provider format, and a non-MorphoFeature consumer (OpticalFlow3D) has none. The `[snapshot]` hashes
  member files without parsing them.
- **A Python hook in the consumer package** (`check(dimensions) -> refusals`). Discovery would import
  consumer code; a declarative file can be hashed, recorded and audited.
- **`find_spec` and `is_file` to locate the package file** (the draft, after MorphoFeature's provider
  discovery). `find_spec` runs import finders; `is_file` follows symbolic links; neither binds the
  file to the declaring distribution (B6).
- **Checking at the header scan (step 1).** Header letters are not confirmed roles; a plain stack's
  axes are open (`axis_names.py`), so the check would guess.
- **Replacing the consumer's runtime refusal.** A stale or wrong manifest would then let a run through.
- **Re-checking a changed manifest at the run and recording the new bytes** (the draft's P48). The
  user confirmed one manifest; a run under other bytes would be checked against rules nobody saw
  (B8).
- **Absent boolean rules defaulting to `false` (RC1's provider rule).** See *Vocabulary* above.

## Proposed fixtures and conformance

Fixtures (proposed, not created): a new tree `fixtures/consumer/`, checked by a reference validator
`tools/audit/refconsumer.py` on acceptance.

| Fixture | Expected | Shows |
|---|---|---|
| `cv01_morphofeature_like` | pass | All five booleans, no channel limits |
| `cv02_single_channel_volume_timelapse` | pass | The OpticalFlow3D-like example above |
| `cv03_channel_limits` | pass | `min_channels = 2`, `max_channels = 4` |
| `cv04_single_channel_with_max_3` | pass | `multichannel_support = false`, `max_channels = 3`: satisfiable by one channel (was `ci07`, B4) |
| `cv05_only_max_channels` | pass | `max_channels = 2`, `min_channels` omitted (F4) |
| `cv06_snapshot` | pass | A `[snapshot]` with two members, `derives = ["rgb_support"]` |
| `cv07_snapshot_no_members` | pass | A `[snapshot]` with `members = []` |
| `ci01_missing_volume_support` | `E_MISSING_FIELD` | Every boolean rule is required |
| `ci02_rgb_support_string` | `E_TYPE` | `"true"` is not support |
| `ci03_pixel_types_field` | `E_UNKNOWN_FIELD` | CM4: pixel types are out of v1 |
| `ci04_schema_version_2` | `E_SCHEMA_VERSION_UNSUPPORTED` | Unknown versions refused |
| `ci05_mixed_without_volume` | `E_CONSUMER_RULE_CONTRADICTION` | `mixed_volume_support` without `volume_support` |
| `ci06_min_above_max` | `E_CONSUMER_RULE_CONTRADICTION` | Channel limits |
| `ci07` | retired, never reused | Was a wrong contradiction; now `cv04` |
| `ci08_max_channels_zero` | `E_VALUE_RANGE` | Limits are ≥ 1 |
| `ci09_consumer_not_token` | `E_ID_SYNTAX` | The ID follows the Token rule |
| `ci10_bom` | `E_FILE_ENCODING` | §2 item 2 |
| `ci11_duplicate_key` | `E_DUPLICATE_KEY` | §2 item 2 |
| `ci12_schema_wrong` | `E_SCHEMA_ID` | `schema = "morphobricks-experiment"` |
| `ci13_single_channel_min_2` | `E_CONSUMER_RULE_CONTRADICTION` | `multichannel_support = false`, `min_channels = 2`: no image can pass (B4) |
| `ci14_snapshot_derives_unknown_key` | `E_VALUE_RANGE` | `derives = ["min_channels"]`: only boolean rules derive |
| `ci15_snapshot_member_file_with_path` | `E_VALUE_RANGE` | `member_file = "../x.json"` |

Rule cases (F4), checked with `cv01`/`cv03`/`cv04` against described inputs: an image without `C`
passes `max_channels = 1` and `multichannel_support = false`; `C` of size 1 likewise; `Z` = 1 and
`T` = 1 pass `volume_support = false` and `time_support = false`; an RGB unit of three samples passes
`max_channels = 1` and is refused only by `rgb_support = false`; `cv03` refuses a one-channel image
as `channel_count` (`found 1, required ≥ 2`).

Conformance plan, proposed rows on acceptance: a §2 row *Consumer manifest* (preprocessing runs every
`cv*`/`ci*` fixture with the exact reasons) and physical scenarios P41-P58 in §3 (they do not collide
with P1-P40):

| # | Setup | Required outcome |
|---|---|---|
| P41 | No manifest installed or bundled | Run as today; `consumer_check = {"consumer": null, "available": []}` |
| P42 | A T = 5 time-lapse; consumer with `time_support = false` | `R_CONSUMER_DIMENSIONS_NOT_ALLOWED` at axis confirmation, every image listed with kind `time`; tagging does not open; excluding them or picking another consumer passes; no projection offered |
| P43 | A unit confirmed `rgb`; consumer with `rgb_support = false` | Refused at image-type confirmation, before tagging, kind `rgb`; an RH1 override unit is judged by its confirmed type, not its header |
| P44 | Three-channel images; `max_channels = 2` | Kind `channel_count`, `found 3, allowed ≤ 2`; nothing dropped |
| P45 | (after P-1, P-2, #438) Z-stacks; `volume_support = false` | (a) TIFF stacks the planner accepts: kind `volume`, projection offered; after the projection copy the check passes and the record holds the manifest SHA-256; (b) OME-Zarr stacks, or masks with Z: projection **not** offered, the planner's refusal quoted, exclusion and another consumer only |
| P46 | (after P-1, P-2, #438) Mixed Z and 2-D images | `mixed_volume_support = false` (with `volume_support = true`): `mixed_volumes`, the refusal lists every volume (FOV key, path, Z) and every plane (FOV key, path) in order, then both counts; both exclusion actions offered, neither preselected; the projection, when offered, names every included image; #438's warning still recorded. `mixed_volume_support = true`: warning only. No consumer: warning only |
| P47 | One consumer ID from several sources | Package and bundle, equal SHA-256: one entry, both sources recorded; different (also CRLF-only): `R_CONSUMER_MANIFEST_CONFLICT` naming both, other consumers still selectable; two bundles, equal: one entry; different: conflict (F1); two distributions with one ID: conflict for both; IDs `MF` and `mf`: conflict for both (F3) |
| P48 | Manifest bytes changed between the check and `describe` or `run` (and, separately, between the run's first re-check and its publication) | `R_CONSUMER_MANIFEST_INVALID` with `E_CONSUMER_CHANGED_SINCE_CHECK` naming both SHA-256; nothing published; checking again and confirming passes and records the new SHA-256 |
| P49 | (after P-2) A manifest claims `volume_support = true` for a consumer without volume providers; run made with *No consumer check* | Preprocessing passes the Z run; MorphoFeature refuses it by its P-2 guard before any provider runs: the runtime guard stands. Before P-2 this scenario is not valid and is not run |
| P50 | Skipped early check against each restricted dimension: for each consumer and each restriction its manifest declares, a run with *No consumer check* | The consumer refuses it on every route it offers (B2); MorphoFeature: `rgb` by MF-6, and (after P-2) Z and mixed |
| P51 | CLI: no `--consumer` while two consumers are installed and one is invalid (O1) | No check, no refusal; `available` lists the valid ID only; `--consumer unknown` is `R_CONSUMER_NOT_FOUND` naming the available and unavailable ones |
| P52 | Notebook with exactly one available consumer (O3) | Nothing preselected; tagging stays closed until the user clicks the consumer or *No consumer check* |
| P53 | `describe --consumer ID` on images the consumer refuses; then `describe --no-consumer` (O7) | The first publishes nothing (`R_CONSUMER_DIMENSIONS_NOT_ALLOWED`); the second publishes |
| P54 | MorphoFeature's snapshot (B3, O4): (a) the release provider set; (b) an RGB-capable add-on provider installed; (c) a provider removed; (d) a regenerated bundle beside the stale package copy | (a) available, `rgb_support` as written; (b), (c) `R_CONSUMER_MANIFEST_INVALID`, `E_CONSUMER_SNAPSHOT_STALE` naming the member; (d) `R_CONSUMER_MANIFEST_CONFLICT`; no provider module imported in any case |
| P55 | Hostile discovery (B6): (a) an entry-point value `os:system` or `pkg.sub`; (b) the package's manifest a symbolic link to a file outside the package; (c) the top-level name a namespace package spread over two paths; (d) an import trap: a `sys.meta_path` finder and a package `__init__.py` that record any call; (e) a distribution listing another distribution's package file | (a) `E_CONSUMER_ENTRY_POINT`; (b), (c), (e) `E_CONSUMER_SOURCE_UNSAFE`; (d) the trap records nothing and no consumer module enters `sys.modules`; each consumer refused alone, the others still listed |
| P56 | Refusal classes (B5): (a) a named ID whose only copy has a TOML error; (b) a named ID with a valid package copy and an invalid bundled copy; (c) a named ID with no candidate but an unrelated invalid file | (a) `R_CONSUMER_MANIFEST_INVALID` only; (b) `R_CONSUMER_MANIFEST_CONFLICT` only, listing the bundle's reasons; (c) `R_CONSUMER_NOT_FOUND` only |
| P57 | Invalidation (B8): after a passed check, the user changes the axis roles, an exclusion, the image type or the pick, or reopens an experiment whose saved pick is gone | Tagging and publication close until the check passes again; the gone pick is `R_CONSUMER_NOT_FOUND`, never *No consumer check* |
| P58 | Run-manifest version (B9): (a) a new-version manifest without `consumer_check` or with an unknown field in it; (b) a version-5 manifest; (c) a brick output reused after the same run folder is re-run with another pick | (a) refused by the reader; (b) refused with "run preprocessing again"; (c) `ENTRY_OUTPUT_EXISTS` (ADR 0007), never a silent reuse |

The §2 row also checks that discovery imports no consumer module (a `sys.modules` scan **and** the
P55 (d) trap, since a module scan alone does not prove that no finder ran).

## Modelling choices for the owner's review

Not owner decisions, except where marked "now owner answer": choices 6, 11 and 12 are the encoding
of O2, O3 and O1 and stay listed so the list is complete. The others are not covered by the owner's
answers; each may be amended. **Changed after review *at*** marks a choice revised by this revision,
with the finding.

1. **Names:** the file `morphobricks_consumer.toml` (underscore, like MorphoFeature's
   `morphofeature_provider.json`); `schema = "morphobricks-consumer"`; the keys `consumer`,
   `display_name`, `[dimensions]`, `multichannel_support`, `rgb_support`, `time_support`,
   `volume_support`, `mixed_volume_support`, `min_channels`, `max_channels`, `[snapshot]`.
   **Changed after review *at*** (F3): IDs compared exactly; a case-fold collision is a conflict;
   picker order by folded `display_name`, then ID. (B3): the `[snapshot]` table is added.
2. **Format:** TOML with experiment-v1 §2's strict parsing rules (not JSON like the provider
   manifests), so one parser and one set of reasons serve both MorphoBricks TOML files.
3. **Reuse of `rgb_support` and `volume_support`**, new keys in the same `<axis>_support` pattern;
   every boolean rule **required**. **Changed after review *at*** (B2): `volume_support` keeps the
   word, with a stated stronger early meaning (no image with `Z` > 1 in any form), not claimed
   equivalent to AR3 at run time.
4. **Channel limits optional**, absent meaning no limit; RGB samples are not counted as channels.
   **Changed after review *at*** (B4): only unsatisfiable sets are contradictions
   (`min_channels > 1` with `multichannel_support = false`; `min > max`; mixed without volume).
5. **Discovery:** entry-point group `morphobricks.consumers`, named by consumer ID, value the
   top-level package. **Changed after review *at*** (B6): the file is bound to the declaring
   distribution's installed-file inventory, contained, regular and link-free; no `find_spec`, no
   `EntryPoint.load`; namespace and ambiguous packages refused. (B5, F1): bundled files are declared
   with their ID (`consumer_manifests={ID: path}`, `--consumer-manifest ID=PATH`), no folder scan.
6. **Precedence:** identical SHA-256 or refuse (`R_CONSUMER_MANIFEST_CONFLICT`); duplicate IDs across
   distributions refused for both. (Package versus bundle: now owner answer O2.) **Changed after
   review *at*** (B5, F1): the same rule covers two bundles and invalid copies; conflict, invalid and
   not found are mutually exclusive, in that order.
7. **The check in two moments**, axis rules at axis confirmation and `rgb` at image-type
   confirmation, both before tagging. **Changed after review *at*** (B8): bound to pinned bytes and a
   candidate-state fingerprint, voided by any edit, re-checked pinned at the describe and run commit
   boundaries; a changed manifest is refused, never silently adopted.
8. **Codes:** four `R_CONSUMER_*` codes (O8); the §2/§6 `E_*` codes reused as reasons, plus
   `E_CONSUMER_ID_MISMATCH` and `E_CONSUMER_RULE_CONTRADICTION`; one dimensions refusal with kinds as
   detail. **Changed after review *at*** (B5-B8, B3): new reasons `E_CONSUMER_ENTRY_POINT`,
   `E_CONSUMER_SOURCE_UNSAFE`, `E_CONSUMER_SNAPSHOT_STALE`, `E_CONSUMER_CHANGED_SINCE_CHECK`;
   `mixed_volumes` lists both groups in full (B7).
9. **The mixed rule is required** and only meaningful with `volume_support = true` (a contradiction
   otherwise); the #438 warning is kept and recorded in every case. **Changed after review *at***
   (B1, B2): the volume rules take effect only after prerequisites P-1 (the #438 experiment-v1 §1
   amendment) and P-2 (MorphoFeature's Z and mixed guard).
10. **The record:** `consumer_check` in `run_manifest.json`, `{"consumer": null, "available": [...]}`
    when none; never in the description. **Changed after review *at*** (B9): a new run-manifest
    version with a strict reader and the field required; the record adds `snapshot_members_sha256`
    and `state_sha256`; the draft's "in no reuse key" was wrong: through ADR 0007's full-manifest
    SHA-256 a changed record changes downstream identity, and this ADR **keeps** that (option a),
    rather than a second digest excluding the field (option b).
11. **No preselection** in the picker, even with one consumer; *No consumer check* is an explicit
    entry. (Now owner answer O3.)
12. **CLI default without `--consumer`:** no check, the available consumers listed in the report.
    (Now owner answer O1.)
13. **The fixes:** exclusion (existing list, a new action for this code), another consumer, and
    projection for the volume kinds only; nothing invented for T, channels or RGB. **Changed after
    review *at*** (B10): projection is offered only after the existing planner accepted it for the
    actual input, otherwise its refusals are quoted; a mixed-run projection covers every included
    image explicitly.
14. **New after review *at*** (B3): MorphoFeature's O4 value is carried by a verified `[snapshot]` in
    its package file; an environment with another provider set makes MorphoFeature unavailable
    (`E_CONSUMER_SNAPSHOT_STALE`) rather than checked against a possibly wrong value. The
    bundle-only alternative is described under [MorphoFeature's manifest](#morphofeatures-manifest).
15. **New after review *at*** (B2): every consumer that declares a restriction guards it itself on
    every route, independent of `consumer_check`; tested by P50.

## Review *at* — responses

Review *at* (24 November 2026) read this ADR at `80c7dd8b9ce575b00506e7e89a09f6984bcc8c78`. Each
finding was checked against the cited sources at the stated commits before any change; all hold.

| Finding | Checked | Change |
|---|---|---|
| B1 | experiment-v1 §1 (`:49-50`) does say "2-D planes only"; the draft's "no other rule changes" was false | Prerequisite P-1, a separate #438 amendment; not written here (O8 kept) |
| B2 | `Request.planes` defaults to `plane` (`run_inputs_request.py:169-193`); `volume_refusals` refuses only a `volume` request or a BM5 conversion (`:557-599`); MorphoFeature's `_planes` expands Z | Consumer-side guards required for every declared restriction (P50); MorphoFeature's guard is prerequisite P-2; P49 is a future scenario |
| B3 | MorphoFeature's `pyproject.toml` declares no provider entry point: "providers the release ships" is empty | Verified `[snapshot]`; stale refused (choice 14) |
| B4 | `multichannel_support = false`, `max_channels = 3` is satisfied by one channel | Contradictions are unsatisfiable sets only; `ci07` retired to `cv04`; `ci13` added |
| B5 | An unavailable named ID met INVALID, CONFLICT and NOT_FOUND; a bundle without a readable `consumer` had no ID | Bundles declared with their ID; mutually exclusive classes in fixed order (P56) |
| B6 | `providers.py:266-277` uses `find_spec` and `is_file` (follows links); no distribution binding | Inventory binding, containment, link-free, no finders (P55) |
| B7 | Counts alone do not name the files to exclude | Both groups listed in full, then counts (P46) |
| B8 | Only `run` re-read; the draft adopted changed bytes | Pinned bytes, fingerprint, invalidation, pinned re-check at describe and run (P48, P57) |
| B9 | `manifest_versions.py` reads `"5"` only; `from_dict` ignores unknown keys; ADR 0007 puts the full manifest SHA-256 in identity | New version, strict required field; option a chosen (choice 10, P58) |
| B10 | `plan_projection` refuses Zarr, Z masks, ranges, pixel types and memory; `_planned` covers every header | Offered only after a planner pass; mixed copy covers every image |
| F1-F4 | Hold | Two-bundle rule; P51-P54 and fixtures; case-fold and order; `cv04`-`cv07` and rule cases |
