# ADR 0009: consumer manifest (early dimension checks in preprocessing)

- **Status:** **Proposed** (owner decisions of 24 November 2026, CM1-CM5 and the owner answers O1-O8
  below, final and not to be reopened by the review). Not implemented. What this ADR adds is their
  encoding: the file, its fields, how preprocessing finds it, where the check sits in the
  preprocessing flow, the refusal codes, the fixes offered, the record in the run manifest, and the
  interactions with RC1, ADR 0002 AR3, ADR 0005, ADR 0006 and morphobricks-preprocessing#438. The
  choices those decisions do not cover are listed under
  [modelling choices](#modelling-choices-for-the-owners-review), for the owner's review. No question
  is open: O1-O8 were answered on 24 November 2026. Tracking: Spec #54.
- **Absorbs** morphobricks-preprocessing#438 ("Move the Z-stack gate from the description step to
  the hand-off"): its owner decisions of 23 November 2026 are CM5 here, and this ADR states how a
  chosen consumer's manifest interacts with #438's mixed-run warning.
- **Amends, on acceptance:** the refusal table of experiment-v1 §8 (four `R_*` rows and their
  precedence, below). The file format itself is normative text of its own, in a new
  `docs/consumer-manifest-v1.md`, written on acceptance from the
  [file section](#the-file-morphobricks_consumertoml); it is not a section of experiment-v1 (owner
  answer O8). Nothing of
  `morphobricks.toml` changes: no field is added, and the consumer is never written into the
  description (experiment-v1 §1 excludes brick names and routing; ADR 0001 decision 10, "no brick
  routing"). No fixture, golden or validator changes in this PR; the fixtures and conformance rows
  below are proposed.
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
  ADR 0002 AR3, ADR 0005 BM5);
- MorphoFeature's own provider checks, after the run (`morphofeature/provider_lookup.py`
  `declared_rgb_support`; `providers.py`, the static provider manifest `morphofeature_provider.json`).

By then the user has confirmed axes, tagged every channel, built the design, saved the description
and run preprocessing. A tool that takes one channel only, or no time-lapse, or that needs Z-stacks,
has no way to say so before that work is done. The owner decided on 24 November 2026 that the next
app (the **consumer**: MorphoFeature, OpticalFlow3D and others) declares what it allows in an
external **consumer manifest**, and that preprocessing checks it early. With no manifest, everything
is allowed, as today.

The rules this must keep: nothing guessed (axes are user-confirmed roles, the image type is a
user-confirmed declaration, ADR 0001 AQ6); no silent drop, slice, projection or conversion; every
refusal names what is wrong and how to fix it; core discovery stays inert (no consumer module is
imported to find its manifest); the consumer's own runtime refusal stays (a manifest is an early
error, never the only guard).

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

### The principle: a manifest narrows, it never widens

A consumer manifest can only **add** refusals to what preprocessing already refuses for everyone. It
never lifts one: a manifest with `volume_support = true` does not make preprocessing accept a Z-stack
while `z_stack_not_supported` is still in force (until #438's first step lands), and a manifest that
allows something preprocessing cannot record (a pixel type, an axis role outside `X Y Z C T`,
`axes.py:39`) changes nothing. And it never replaces the consumer's runtime refusal: the consumer
still opens `RunInputs` with its own `Capabilities` and is refused there exactly as today
([Interactions](#the-consumers-runtime-refusal-stays-the-final-guard)).

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
| `consumer` | text, a Token (experiment-v1 §3.2) | yes | The consumer's ID: what the user picks, what the run records, what the discovery entry point is named |
| `display_name` | text, non-empty | yes | What the picker shows |
| `dimensions` | table | yes | The v1 rules below; closed field set |

`[dimensions]`, every rule decided from **confirmed** axis roles and the **confirmed** image type of
each included image, never from pixels and never from header letters alone:

| Key | Type | Required | An included image is refused for this consumer when |
|---|---|---|---|
| `multichannel_support` | boolean | yes | `false` and the image is a channel image whose confirmed `C` role has size > 1 |
| `rgb_support` | boolean | yes | `false` and the image belongs to a unit whose confirmed image type is `rgb` (ADR 0001 AQ6; the meaning of RC1's provider key) |
| `time_support` | boolean | yes | `false` and the image's confirmed `T` role has size > 1 |
| `volume_support` | boolean | yes | `false` and the image's confirmed `Z` role has size > 1 (the meaning of `Capabilities.volume_support`, ADR 0002 AR3; a one-slice `Z` is a plane) |
| `mixed_volume_support` | boolean | yes | `false`, `volume_support` is `true`, and the included images are not all of one kind: some have `Z` > 1 and some do not (a run-level rule, CM5) |
| `min_channels` | integer ≥ 1 | no | The image is a channel image with fewer channels (absent: no lower limit beyond 1) |
| `max_channels` | integer ≥ 1 | no | The image is a channel image with more channels (absent: no upper limit) |

- A channel image without a `C` role has one channel. An RGB image is governed by `rgb_support`
  alone: its three samples are not stains, and the channel rules do not count them.
- `mixed_volume_support = true` with `volume_support = false`, `min_channels > max_channels`, and
  `multichannel_support = false` with `min_channels` or `max_channels` above 1 are contradictions
  (`E_CONSUMER_RULE_CONTRADICTION`): the file says two things.
- A non-boolean value is `E_TYPE`, never read as `true` or `false` (the RC1 modelling rule).
- Pixel types, calibration, channel IDs and masks (CM4) are not fields: a `pixel_types`,
  `calibration`, `channels` or `masks` key is `E_UNKNOWN_FIELD`.

**Vocabulary.** `rgb_support` and `volume_support` keep the meaning they have in provider manifests
and in `Capabilities` (`run_inputs_request.py:120-140`): one word, one meaning, across the provider
manifest, the resolver and the consumer manifest. The new keys follow the same `<axis>_support`
pattern. One difference is deliberate: in a provider manifest an absent capability means `false`
(RC1); in a consumer manifest every boolean rule is **required**. A provider manifest declares one
optional capability among many; a consumer manifest exists only to state the rules, and an absent
rule would otherwise be a silent refusal (or a silent permission) that the author never wrote.

### Discovery (CM1)

**Shipped by the consumer package.** The package declares an entry point in the group
`morphobricks.consumers`, named by its consumer ID, whose value is its top-level package (for
MorphoFeature: `morphofeature = "morphofeature"`). The file `morphobricks_consumer.toml` lies in that
package's directory (package data). Preprocessing finds it with `importlib.metadata.entry_points`
and `importlib.util.find_spec(<top-level>)`, which locates a package without executing it: the
consumer is never imported, so discovery stays inert. This is the mechanism MorphoFeature already
uses for its provider manifests (`providers.py:266-277` `_manifest_path`, `:526-564`
`discover_providers`). The entry point's name must equal the file's `consumer`
(`E_CONSUMER_ID_MISMATCH`). One consumer ID declared by two distributions is refused for both
(`R_CONSUMER_MANIFEST_CONFLICT`), never resolved by installation order (MorphoFeature's provider
rule, `providers.py:549-552`).

**Bundled by a LabConstrictor app.** The app names its manifest files explicitly: the notebook API
takes `consumer_manifests=[path, ...]`, which an app sets in the notebook's hidden setup cell (where
LabConstrictor already reads `current_version` and `notebook_name`, preprocessing `README.md:122`),
and the CLI takes `--consumer-manifest PATH` (repeatable). No folder is scanned. A bundled file must
be a regular file; a symlink is refused, as `morphobricks.toml` is (`R_FILE_SYMLINK`'s rule, reason
reported under `R_CONSUMER_MANIFEST_INVALID`).

**The same consumer from both sources (precedence).** When a package-shipped and a bundled manifest
name the same `consumer`: if their SHA-256 are equal, they are one consumer and the record lists both
sources; if they differ (owner answer O2: byte-identical or refused; the bundled file never wins), that consumer is refused (`R_CONSUMER_MANIFEST_CONFLICT`, naming both paths
and both SHA-256) and cannot be picked until one source is removed or they are made identical. Other
consumers stay available. Nothing is chosen by source order.

A manifest that fails to parse or validate makes **that** consumer unavailable: the picker lists it
as not available with the reason (`R_CONSUMER_MANIFEST_INVALID` and its `E_*` reasons). It blocks
nothing unless the user, or the CLI, names it.

### The choice (CM2)

- The notebook shows one picker, *Next app (consumer)*, listing every available consumer by
  `display_name` with its ID and source, every unavailable one with its reason, and the entry
  *No consumer check*. Nothing is preselected, also when one consumer is available: picking is the
  user's answer (owner answer O3). With no manifest found, the picker says so in one line and the run behaves as
  today.
- The CLI takes `--consumer ID` or `--no-consumer`. Without either, no consumer is checked and the
  run's report lists the consumers that were available (owner answer O1); omission is never a
  refusal, so existing scripts behave as today. `describe` takes the same two options
  (`describe --consumer ID`, owner answer O7).
  An ID that is not available is `R_CONSUMER_NOT_FOUND`, naming the available IDs.
- The notebook keeps the pick with its other run settings, as it keeps the exclusions and the
  histogram settings for a reopened experiment (`notebook_prefill.py`); it is never written into
  `morphobricks.toml`.

### Where the check sits in the flow

Mapped on the shipped notebook's seven steps (`notebook_steps.py:1-22`, `:149-178`):

| Owner flow | Notebook today | With this ADR |
|---|---|---|
| (1) Scan headers and folder layout | Step 1 *Images* (quick scan, then every header on a click; `run/preflight.py:169-260`) | Unchanged. The consumer can be picked here already |
| (2) Validate axes | Step 2 *Axes* (roles, pixel size; projection card) | Unchanged |
| (3) Check the manifest | (none) | **New.** The `Z`, `T`, `C` and mixed rules are checked as soon as the axis roles are confirmed; the `rgb` rule as soon as the image type is confirmed |
| (4) Tag channels | Step 3 *Channels*: confirm the image type, then name the stains and tag | Naming and tagging open only when the check passed (or no consumer is checked) |
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

**Again at the run.** `run` (notebook step 7, CLI `run`) re-reads the chosen manifest, recomputes
its SHA-256 and re-checks every included image before any pixel is read. A manifest whose bytes
changed since the step-3 check is checked again as it is now; the run records what it checked.

The check reads no pixel: confirmed roles, the sizes the headers give for them (`TiffMetadata`), and
the confirmed image type.

### Refusal codes

New `R_*` codes (preprocessing layer, experiment-v1 §8), proposed for §8 on acceptance:

| Code | Meaning |
|---|---|
| `R_CONSUMER_MANIFEST_INVALID` | A consumer manifest breaks the file rules. Reasons: the experiment-v1 §2/§6 codes reused with their meaning (`E_FILE_ENCODING`, `E_TOML_SYNTAX`, `E_DUPLICATE_KEY`, `E_TYPE`, `E_UNKNOWN_FIELD`, `E_MISSING_FIELD`, `E_SCHEMA_ID`, `E_SCHEMA_VERSION_MISSING`, `E_SCHEMA_VERSION_UNSUPPORTED`, `E_ID_SYNTAX`, `E_TEXT_EMPTY`, `E_VALUE_RANGE`) and two new ones, `E_CONSUMER_ID_MISMATCH` (the entry point's name is not the file's `consumer`) and `E_CONSUMER_RULE_CONTRADICTION` (the contradictions above); a symlinked bundled file. Makes that consumer unavailable; blocks only when it is named |
| `R_CONSUMER_MANIFEST_CONFLICT` | One consumer ID comes from two distributions, or from a package and a bundle with different SHA-256; names every source and SHA-256 |
| `R_CONSUMER_NOT_FOUND` | The consumer named (`--consumer`, or a reopened experiment's saved pick) is not available; names the available ones and the unavailable ones with their reason |
| `R_CONSUMER_DIMENSIONS_NOT_ALLOWED` | Included images break the chosen consumer's `[dimensions]`. **One** refusal lists **every** offending image (FOV key, path) with **every** kind found in it (`multichannel`, `channel_count`, `rgb`, `time`, `volume`; expected and found, for example `T = 40, consumer allows T = 1`), then the run-level kind `mixed_volumes` with the count of images of each kind; it names the consumer, the manifest's SHA-256 and the fixes below. Nothing is dropped, sliced, projected or converted |

The kinds are message detail, not separate codes, as in `R_FAST_LAYOUT_CONTRADICTION` (ADR 0006,
modelling choice 7): one code, one complete list, one set of fixes.

**Precedence.** Preprocessing's own refusals come first: the check needs confirmed axes, so
`z_stack_not_supported` and the axis errors are resolved before it runs. In the notebook,
`R_CONSUMER_DIMENSIONS_NOT_ALLOWED` is reported before any channel-tagging code (it is decided before
tagging opens). At a publication or a run it is reported beside every other applicable `R_*` code
(ADR 0001 AQ2); one run carries it at most once.

### Fixes offered (CM3)

What preprocessing has today (checked, not invented):

| Kind | Fixes |
|---|---|
| every kind | **Exclude the offending images.** The exclusion list exists in the notebook (the *exclude* field and the *exclude the blocking images* action, `notebook_folder.py:483-489`, `EXCLUDABLE_CODES` in `notebook_options.py:35`) and the CLI (`--exclude PATH`, `cli.py:189-195`); the action gains this code. Exclusion is the user's click and is recorded as every exclusion is |
| every kind | **Choose another consumer**, or *No consumer check* |
| `volume`, `mixed_volumes` | **Project the stacks**: the recorded projection copy (`notebook_projection.py`, `conversion.convert_experiment`; methods `max`, `mean`, `sum` and a slice range, `projection.py:39`), the originals kept. For `mixed_volumes` the user may instead exclude all volumes or all planes (two explicit actions; neither is preselected) |
| `time`, `channel_count`, `multichannel`, `rgb` | None beyond exclusion and another consumer. Preprocessing has no time-point selection or projection, no channel subset copy and no RGB-to-grey conversion (ADR 0001 RC1 forbids a silent one; ADR 0006 forbids dropping channels). The message says so instead of suggesting a tool that does not exist |

### The record (where it lives)

The run manifest (`run_manifest.json`) records the check under `consumer_check`:

```json
"consumer_check": {
  "consumer": "morphofeature",
  "display_name": "MorphoFeature",
  "schema_version": 1,
  "manifest_sha256": "<SHA-256 of the exact bytes read>",
  "sources": [{"kind": "package", "distribution": "morphofeature", "version": "<installed version>"},
              {"kind": "bundled", "path": "<path as given>"}],
  "dimensions": {"multichannel_support": true, "rgb_support": false, "time_support": true,
                 "volume_support": false, "mixed_volume_support": false},
  "outcome": "passed"
}
```

With no consumer checked: `{"consumer": null, "available": ["<ID>", ...]}` (`[]` when none was
found). A run is published only with `outcome = "passed"` or no consumer; a refused check publishes
nothing. The same holds for `describe --consumer ID` (the check also blocks publishing a description;
owner answer O7); a description or run published with *No consumer check* is not blocked. The record
is provenance only: no consumer reads it in v1 (owner answer O5). It is **not** in `morphobricks.toml` (experiment-v1 §1: no brick names or routing; ADR 0001
decision 10), and it is in no output's cache or reuse key: it changes no pixel, histogram or QC
value, only whether the run may proceed. A run that reuses outputs records the check it made itself.
Adding the key follows preprocessing's run-manifest versioning (`manifest_versions.py`,
`MANIFEST_VERSION = "5"` at the evidence commit).

### Interactions

#### The consumer's runtime refusal stays the final guard

A consumer still declares its `Capabilities` when it opens `RunInputs`, and is refused there as today
(`A_RGB_NOT_SUPPORTED`, `A_VOLUME_NOT_SUPPORTED`; MorphoFeature's provider checks). It does not read
`consumer_check` in v1, to skip a check or for any other purpose (owner answer O5): a run checked for another consumer, a manifest that disagrees with
the consumer's code, or a run made with *No consumer check* is caught there. The manifest is an early
error, not a contract that consumers trust. Conformance proves both: the same run is refused early by
the manifest and, with the manifest check skipped, by the consumer.

#### ADR 0001 RC1 and ADR 0002 AR3

`rgb_support` and `volume_support` mean the same thing in the three places. The consumer manifest is
not a provider manifest: MorphoFeature keeps reading `rgb_support` per provider from
`morphofeature_provider.json` and passing it as `Capabilities` (ADR 0002 AR7: MorphoFeature decides
provider capability). The consumer manifest describes the app as a whole for preprocessing's early
check only.

#### #438 and ADR 0005 (volumes)

- Until #438's first step lands, preprocessing refuses every Z-stack for everyone
  (`z_stack_not_supported`), so the `volume` and `mixed_volumes` kinds cannot occur; the rules are
  specified now so that manifests are written once.
- After it, a Z-stack passes preprocessing's own checks; `volume_support = false` in the chosen
  manifest refuses it at step 3 with projection named as a fix, instead of at `RunInputs`.
- **The mixed-run warning (CM5).** Preprocessing warns, for every run, when some included images have
  `Z` > 1 and others do not, and records the warning in the run's checks (#438, owner comment of
  23 November 2026). With a chosen consumer: `volume_support = false` refuses each volume as `volume`
  (the mix is not reported again); `volume_support = true` and `mixed_volume_support = false` turns
  the mix into the blocking kind `mixed_volumes`, and the recorded warning stays; `mixed_volume_support
  = true` leaves only the warning. With no consumer the warning is all, as #438 decided. The manifest
  never makes the warning disappear.
- Histograms, normalization and QC for volumes (step 5) are #438's rule and are untouched here. A
  `volume` run never reaches `binary_mask_policy` (ADR 0005 BM5) through this check: that refusal
  stays at `RunInputs`.

#### ADR 0006 (fast-mode channel layout)

The check runs before tagging, so before `R_FAST_LAYOUT_CONTRADICTION` can be computed. The two
never report the same thing: the manifest counts channels against the consumer's limits; fast mode
compares each image with the experiment's list.

#### ADR 0007 (run-folder entry)

A brick started on a validated run folder (`<brick>.run_folder`) is unaffected. A brick's
entry does not name the consumer a run was checked for and does not read `consumer_check` (owner
answer O5).

### MorphoFeature's manifest (the shipping option is still the owner's)

From the code read: MorphoFeature runs time series (`run_config._planes`, `:440-445`, iterates `T`;
`attach_tracks`), takes several channels, expands every `Z` slice into a separate 2-D FOV today
(`run_config._planes`; #438 asks it to refuse a Z run instead), and requires `rgb_support` from every
provider of a run (MF-6, `mask_selection.py:335-336`). Two ways to ship it:

1. **A static file** `src/morphofeature/morphobricks_consumer.toml` with the entry point
   `[project.entry-points."morphobricks.consumers"] morphofeature = "morphofeature"`:
   `multichannel_support = true`, `time_support = true`, `volume_support = false`,
   `mixed_volume_support = false`, no channel limits, and `rgb_support` by the owner's rule (O4): `true` if **any** installed provider declares it (the app
   can do something with RGB; each provider still refuses at run time, MF-6 for a run whose chosen
   providers do not all declare it). In a static file, "installed" can only mean the providers the
   MorphoFeature release itself ships, so the value is fixed when the release is made; option 2
   below follows the providers installed in a given app. Fixed bytes, one SHA-256 per release.
2. **Generated from the installed providers**, by a command such as
   `morphofeature consumer-manifest --write PATH`, for a LabConstrictor app to bundle at build time:
   `rgb_support` and, later, `volume_support` (#438, MorphoFeature#157: providers declaring a volume
   unit) derived from the provider manifests installed in that app. Generating it at preprocessing
   time was rejected: the file's SHA-256 would change with whatever happens to be installed, and
   preprocessing would have to import or interpret MorphoFeature's provider manifests.

Recommended: the static file first (option 1), the command when a LabConstrictor app needs a narrower
manifest.

## Rejected alternatives

- **Fields in `morphobricks.toml`.** The description says what the experiment is; which app runs next
  is routing (experiment-v1 §1, ADR 0001 decision 10), and one experiment can feed several consumers.
- **Reading the provider manifests directly.** Preprocessing would interpret MorphoFeature's
  provider format, and a non-MorphoFeature consumer (OpticalFlow3D) has none.
- **A Python hook in the consumer package** (`check(dimensions) -> refusals`). Discovery would import
  consumer code; a declarative file can be hashed, recorded and audited.
- **Checking at the header scan (step 1).** Header letters are not confirmed roles; a plain stack's
  axes are open (`axis_names.py`), so the check would guess.
- **Replacing the consumer's runtime refusal.** A stale or wrong manifest would then let a run through.
- **Absent boolean rules defaulting to `false` (RC1's provider rule).** See *Vocabulary* above.

## Proposed fixtures and conformance

Fixtures (proposed, not created): a new tree `fixtures/consumer/`, checked by a reference validator
`tools/audit/refconsumer.py` on acceptance.

| Fixture | Expected | Shows |
|---|---|---|
| `cv01_morphofeature_like` | pass | All five booleans, no channel limits |
| `cv02_single_channel_volume_timelapse` | pass | The OpticalFlow3D-like example above |
| `cv03_channel_limits` | pass | `min_channels = 2`, `max_channels = 4` |
| `ci01_missing_volume_support` | `E_MISSING_FIELD` | Every boolean rule is required |
| `ci02_rgb_support_string` | `E_TYPE` | `"true"` is not support |
| `ci03_pixel_types_field` | `E_UNKNOWN_FIELD` | CM4: pixel types are out of v1 |
| `ci04_schema_version_2` | `E_SCHEMA_VERSION_UNSUPPORTED` | Unknown versions refused |
| `ci05_mixed_without_volume` | `E_CONSUMER_RULE_CONTRADICTION` | `mixed_volume_support` without `volume_support` |
| `ci06_min_above_max` | `E_CONSUMER_RULE_CONTRADICTION` | Channel limits |
| `ci07_single_channel_with_max_3` | `E_CONSUMER_RULE_CONTRADICTION` | `multichannel_support = false`, `max_channels = 3` |
| `ci08_max_channels_zero` | `E_VALUE_RANGE` | Limits are ≥ 1 |
| `ci09_consumer_not_token` | `E_ID_SYNTAX` | The ID follows the Token rule |
| `ci10_bom` | `E_FILE_ENCODING` | §2 item 2 |
| `ci11_duplicate_key` | `E_DUPLICATE_KEY` | §2 item 2 |
| `ci12_schema_wrong` | `E_SCHEMA_ID` | `schema = "morphobricks-experiment"` |

Conformance plan, proposed rows on acceptance: a §2 row *Consumer manifest* (preprocessing runs every
`cv*`/`ci*` fixture with the exact reasons; discovery imports no consumer module, checked by a
`sys.modules` scan; the entry-point name mismatch is `E_CONSUMER_ID_MISMATCH`) and physical scenarios
P41-P49 in §3:

| # | Setup | Required outcome |
|---|---|---|
| P41 | No manifest installed or bundled | Run as today; `consumer_check = {"consumer": null, "available": []}` |
| P42 | A T = 5 time-lapse; consumer with `time_support = false` | `R_CONSUMER_DIMENSIONS_NOT_ALLOWED` at axis confirmation, every image listed with kind `time`; tagging does not open; excluding them or picking another consumer passes; no projection offered |
| P43 | A unit confirmed `rgb`; consumer with `rgb_support = false` | Refused at image-type confirmation, before tagging, kind `rgb`; an RH1 override unit is judged by its confirmed type, not its header |
| P44 | Three-channel images; `max_channels = 2` | Kind `channel_count`, `found 3, allowed ≤ 2`; nothing dropped |
| P45 | (after #438) Z-stacks; `volume_support = false` | Kind `volume`, projection named; after the projection copy the check passes and the record holds the manifest SHA-256 |
| P46 | (after #438) Mixed Z and 2-D images | `mixed_volume_support = false` (with `volume_support = true`): `mixed_volumes` with both counts, blocking, #438's warning still recorded; `mixed_volume_support = true`: warning only; no consumer: warning only |
| P47 | One consumer ID from a package and a bundle | Equal SHA-256: one entry, both sources recorded; different: `R_CONSUMER_MANIFEST_CONFLICT`, other consumers still selectable; two distributions with one ID: refused for both |
| P48 | Manifest bytes changed between step 3 and the run | The run re-checks and records the new SHA-256; a manifest that now refuses blocks the run |
| P49 | A manifest claims `volume_support = true` for a 2-D consumer | Preprocessing passes the Z run; the consumer is still refused at `RunInputs` (`A_VOLUME_NOT_SUPPORTED`): the runtime guard stands. CLI: `--consumer unknown` is `R_CONSUMER_NOT_FOUND`; no flag checks nothing and lists the available consumers |

## Modelling choices for the owner's review

Not owner decisions, except where marked "now owner answer": choices 6, 11 and 12 are the encoding
of O2, O3 and O1 and stay listed so the list is complete. The others are not covered by the owner's
answers; each may be amended.

1. **Names:** the file `morphobricks_consumer.toml` (underscore, like MorphoFeature's
   `morphofeature_provider.json`); `schema = "morphobricks-consumer"`; the keys `consumer`,
   `display_name`, `[dimensions]`, `multichannel_support`, `rgb_support`, `time_support`,
   `volume_support`, `mixed_volume_support`, `min_channels`, `max_channels`.
2. **Format:** TOML with experiment-v1 §2's strict parsing rules (not JSON like the provider
   manifests), so one parser and one set of reasons serve both MorphoBricks TOML files.
3. **Reuse of `rgb_support` and `volume_support`** with their RC1/AR3 meaning, new keys in the same
   `<axis>_support` pattern; but every boolean rule **required** (no default inside the file).
4. **Channel limits optional**, absent meaning no limit; RGB samples are not counted as channels.
5. **Discovery:** entry-point group `morphobricks.consumers`, named by consumer ID, value the
   top-level package; the file found with `find_spec`, never imported. Bundled files only by explicit
   path (`consumer_manifests=[...]`, `--consumer-manifest`), no folder scan; symlinks refused.
6. **Precedence:** identical SHA-256 or refuse (`R_CONSUMER_MANIFEST_CONFLICT`); duplicate IDs across
   distributions refused for both. (Package versus bundle: now owner answer O2; the duplicate-ID rule
   across distributions is this ADR's.)
7. **The check in two moments**, axis rules at axis confirmation and `rgb` at image-type
   confirmation, both before tagging; repeated at the run.
8. **Codes:** four `R_CONSUMER_*` codes; the §2/§6 `E_*` codes reused as reasons, plus
   `E_CONSUMER_ID_MISMATCH` and `E_CONSUMER_RULE_CONTRADICTION`; one dimensions refusal with kinds as
   detail (`multichannel`, `channel_count`, `rgb`, `time`, `volume`, `mixed_volumes`).
9. **The mixed rule is required** and only meaningful with `volume_support = true` (a contradiction
   otherwise); the #438 warning is kept and recorded in every case.
10. **The record:** `consumer_check` in `run_manifest.json` (consumer, display name, schema version,
    SHA-256, sources, the rules as read, outcome), `{"consumer": null, "available": [...]}` when
    none; never in the description; in no cache or reuse key.
11. **No preselection** in the picker, even with one consumer; *No consumer check* is an explicit
    entry. (Now owner answer O3.)
12. **CLI default without `--consumer`:** no check, the available consumers listed in the report.
    (Now owner answer O1.)
13. **The fixes:** exclusion (existing list, a new action for this code), another consumer, and
    projection for the volume kinds only; nothing invented for T, channels or RGB.
