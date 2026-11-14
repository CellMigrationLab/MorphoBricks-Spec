# MorphoBricks-Spec

The shared rulebook of MorphoBricks: the decisions and contracts that several bricks depend
on, written down once so that every tool reads an experiment the same way. Its main piece is
the **experiment description**, a small file called `morphobricks.toml` that says what your
imaging experiment is: which conditions you compared, which biological repeats belong together,
what each channel is, and what each mask means. This repository holds the text, the test files
and the audit tools. There is no package to install.

## The problem it solves

Every MorphoBricks tool needs the same facts about your experiment. Which folder is the
control? Is `rep1` under `CTRL` the same day's work as `experiment_23` under `DrugA`? Is
channel 2 the collagen stain in every image, or only in some? Is this mask a set of numbered
cells, or just "inside or outside"?

Before, those answers lived in several places: a design CSV, channel names typed into each
brick, mask kinds in a manifest. Each tool asked again, or guessed. A guess about a channel or
a repeat is the kind of mistake that is invisible in the output and wrong in the statistics.

The experiment description fixes this. You answer the questions once, in the preprocessing
notebook. The answers are saved as `morphobricks.toml` next to your results. Today the
preprocessing brick reads that file; the other bricks will read it too as they reach Stage 2
(see [Status and roadmap](#status-and-roadmap)). Nothing is inferred from file names, pixel
values or header spelling: what the file does not say, no tool assumes.

## Who it is for

- **Biologists and image analysts** who run the MorphoBricks notebooks. You will meet the
  file as a set of questions in the preprocessing notebook, and you rarely need to open it.
- **Collaborators** who want to know what a MorphoBricks result was computed from. The file is
  short and readable; the example below shows all of it.
- **Developers of a brick**, who need the exact rules. Those are in the normative documents
  linked further down.

## What you actually touch

The preprocessing notebook ([morphobricks-preprocessing](https://github.com/CellMigrationLab/morphobricks-preprocessing))
checks your experiment folder, shows a picture of each image folder, and asks:

1. what each folder is (condition, biological repeat, technical repeat), with short names
   that never change once saved;
2. which condition each treatment is compared against;
3. what was imaged in each channel, tagged per acquisition with the header name as evidence;
4. whether each mask is a set of separate numbered objects, a region, or groups such as the
   mitochondria of each cell;
5. whether the folders of one biological repeat were prepared and imaged the same way.

*Check and save* restates your answers in sentences and writes `morphobricks.toml` to the
output folder. From then on, the run and every later brick read that file. When you add images
or a new repeat, the notebook compares the folder with the saved file and asks only about what
changed. Nothing is renamed, renumbered or paired on your behalf.

## An example

A two-condition experiment, one biological repeat, two channels, one mask. This is the whole
file.

```toml
schema = "morphobricks-experiment"
schema_version = 1

[conditions.CTRL]
source_folder = "CTRL"
display_name = "Control"

[conditions.TGFb]
source_folder = "TGFb"
display_name = "TGF-beta"
reference = "CTRL"

[channels.DNA]
display_name = "DAPI"
header_names = ["DAPI"]

[channels.COL1]
display_name = "Collagen I (CNA35)"
header_names = ["CNA35"]

[repeats.Day1]
confirmed = true
confirmed_on = "2026-11-06"

[repeats.Day1.members.CTRL]
source_repeat = "rep1"
image_count = 12

[repeats.Day1.members.CTRL.technical_repeats.single]
source_folder = "single"
channels = ["DNA", "COL1"]

[repeats.Day1.members.TGFb]
source_repeat = "experiment_23"
image_count = 11

[repeats.Day1.members.TGFb.technical_repeats.single]
source_folder = "single"
channels = ["DNA", "COL1"]

[masks.Cells]
source_type = "cells"
representation = "instances"
source_channels = ["DNA"]

[used_ids]
conditions = ["CTRL", "TGFb"]
channels = ["COL1", "DNA"]
repeats = ["Day1"]
technical_repeats = ["single"]
```

What each block says:

- **`schema`, `schema_version`.** Which rules the file follows. A reader that does not know
  version 1 refuses the file instead of guessing.
- **`[conditions.CTRL]`, `[conditions.TGFb]`.** Two conditions. The key (`CTRL`) is the short
  name every tool uses; `source_folder` is the folder on disk; `display_name` is what plots and
  reports show. `reference = "CTRL"` says TGF-beta is compared against the control. That is
  the only statistical statement in the file; which tests to run is decided later, in
  MorphoCoverage.
- **`[channels.DNA]`, `[channels.COL1]`.** The two stains, with the name each has in the image
  headers. A header name is evidence that you confirmed, never a match made by the software:
  `cna35` would not match `CNA35`.
- **`[repeats.Day1]`.** One biological repeat. `confirmed_on` is the day you answered "yes,
  these were prepared and imaged the same way"; it is your date, never the clock's.
- **`members.CTRL`, `members.TGFb`.** Which folder of each condition belongs to Day1. Here the
  control folder is `rep1` and the treated folder is `experiment_23`: different names, same
  biological repeat, paired by you. `image_count` records how many images you confirmed.
- **`technical_repeats.single`.** Each member has one acquisition. `single` means "no
  technical-repeat folder level". `channels = ["DNA", "COL1"]` says, in order, what channel 0
  and channel 1 of those images are. An acquisition with another order gets its own list.
- **`[masks.Cells]`.** One mask type, found in the folder `cells`. `instances` means each cell
  has its own number, so it can be used as an object set; a `binary` mask is a region and
  cannot. A third kind, `parent_labels`, gives each group one number whose pixels can be in
  several pieces (the mitochondria of one cell); a brick that declares support for it reads the
  groups, any other brick uses it as a plain area and says so. `source_channels` records that it
  was segmented from the DNA channel.
- **`[used_ids]`.** Every short name ever saved. A name that is removed stays here and is never
  given to something else, so old results can never be confused with new ones.

Once the bricks read this file (Stage 2, below), fiberfeatures measures collagen organization
in the `COL1` channel inside the `Cells` objects, and MorphoCoverage compares `TGFb` with `CTRL`
across the repeats you paired. Neither tool has to be told again which channel or which folder
is which.

The example is checked by the reference validator
(`python -I tools/audit/refval.py check morphobricks.toml`, no errors, no warnings) and
follows the fixtures [`v03`](fixtures/valid/v03_paired_different_folder_names.toml) and
[`v07`](fixtures/valid/v07_instance_masks.toml).

## Where it fits among the bricks

MorphoBricks is a set of small tools, each with one job. The experiment description is written
by the first one and read by the others.

| Brick | What it does | Relation to the description |
|---|---|---|
| [morphobricks-preprocessing](https://github.com/CellMigrationLab/morphobricks-preprocessing) | Reads the experiment folder, checks headers and axes, computes per-plane histograms, writes the run folder that every other brick reads | Asks the questions and writes `morphobricks.toml`; the only program that parses it |
| [morphobricks-normalization](https://github.com/CellMigrationLab/morphobricks-normalization) | The normalization methods and the histogram table format, as a library | Pools statistics by biological repeat |
| [CellPatcher](https://github.com/CellMigrationLab/CellPatcher) | Cell, random, grid and whole-field patches from a preprocessing run | Selects channels and masks by name |
| [MorphoFeature](https://github.com/CellMigrationLab/MorphoFeature) | Runs several feature bricks over one run and writes standard feature tables | Resolves channel and mask names per image, refuses what the description does not cover |
| [MorphoObjects](https://github.com/CellMigrationLab/MorphoObjects) | Per-object shape and single-channel intensity features | Receives named channels and object sets through MorphoFeature |
| [MorphoRelate](https://github.com/CellMigrationLab/MorphoRelate) | Relationships between channels, compartments and segmented structures | Receives named channels and mask roles |
| [MorphoEmbed](https://github.com/CellMigrationLab/MorphoEmbed) | Learned embeddings of object crops with pinned encoders | Fits its normalization per biological repeat, never per technical repeat |
| [fiberfeatures](https://github.com/CellMigrationLab/fiberfeatures) | Fiber and ECM organization at several scales | Measures channels by name, grouped by repeat |
| [MorphoCoverage](https://github.com/CellMigrationLab/MorphoCoverage) | Did you image enough fields, and do the conditions differ | Takes conditions, references and repeat pairing from the description |

Today the bricks read channel names and repeat labels from a v0.4 preprocessing run. The
third column describes what each brick takes from the description once Stage 2 (below) is
done; the roles themselves are from each brick's own README.

The file deliberately leaves things out: pixel sizes stay in `calibration.csv`, the list of
image files and their fingerprints stay in the run manifest, and which features to compute or
which statistics to run belong to the brick you ask. See
[experiment-v1 §1](docs/experiment-v1.md#1-scope).

## Status and roadmap

The work is staged; each stage has a gate that is declared only after the tests exist and run.

| Stage | What | Where it stands |
|---|---|---|
| 0: Specification | Decisions ([ADR 0001](docs/adr/0001-experiment-description-v1.md)), the normative text, 195 fixtures, a reference validator, a conformance plan | **Done** (6 to 9 November 2026). Validator: 0 mismatches |
| 1: Preprocessing writes and reads the file | Notebook questions, `describe` command, strict reader, reconciliation when folders change, `RunInputs` with canonical IDs, the derived `experiment_design.csv` | Implemented on the preprocessing `main` branch; ships as **v0.5.0**. Gate G1 is declared once every fixture and scenario of the [conformance plan](docs/conformance-plan.md) runs on the release candidate |
| 2: The bricks | MorphoFeature, MorphoRelate, fiberfeatures, MorphoObjects, MorphoEmbed, MorphoCoverage and CellPatcher take channel, mask and repeat identities from `RunInputs` instead of raw labels | Design decisions recorded (ADR 0001, 8 November 2026); the architecture decided on 10 November 2026 ([ADR 0002](docs/adr/0002-shared-request-resolver.md): one shared request resolver in preprocessing, both routes kept); a draft resolver in preprocessing; not implemented in the bricks |
| 3: Mixed layouts | Acquisitions with different channel sets or orders processed in one experiment | Not started. Until then a described run with mixed layouts is refused (`R_HETEROGENEOUS_LAYOUT_NOT_ENABLED`) |
| 4: Masks and regression | Progressive segmentation, end-to-end tests across all bricks, migration guide | Not started |

The detailed plan, with gates and acceptance tests, is [docs/roadmap.md](docs/roadmap.md);
how it is sequenced against everything else in MorphoBricks is
[docs/master-roadmap.md](docs/master-roadmap.md). The architectural discussion is
[RFC #1](https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1).

## For developers

Everything below is the normative material. Read it when you write or change a reader, a
writer or a brick that consumes the description.

### Documents

- [Experiment description v1](docs/experiment-v1.md): the schema, every field and type, the
  identity rules, the error catalogue (`E_*` for the file, `R_*` for preprocessing, `A_*` for
  the analysis layer), canonical serialization, reconciliation and the derived CSV.
- [ADR 0001](docs/adr/0001-experiment-description-v1.md): the owner's decisions, recorded
  verbatim, with the alternatives that were rejected and why.
- [Conformance plan](docs/conformance-plan.md): how preprocessing turns the fixtures into
  executable tests, the physical scenarios P01 to P35, and the exit criteria of gate G1.
- [Roadmap](docs/roadmap.md) and [master roadmap](docs/master-roadmap.md).
- [One route for every image size and type](docs/design/one-route.md): **proposed, not
  normative**. The whole-slide, multithreaded, bridge-compatible design (umbrella #2), with its
  acceptance gates.
- [ADR 0004](docs/adr/0004-execution-windows.md) (**accepted**, 14 November 2026): execution windows,
  typed coordinates and the patch catalogue, the first slice of the one-route design; reference
  conversions in `tools/execution_frames.py`.

### Fixtures and goldens

[`fixtures/`](fixtures/README.md) holds 40 valid files, 140 invalid ones (each with the exact
set of error codes a reader must report), 15 transitions (a valid file checked against the
published file it replaces), golden `experiment_design.csv` outputs and 37 goldens for the
records file. A reader pins this repository by commit SHA and must accept or refuse every file
exactly as listed. Fixtures change first: a normative change lands here as text plus fixtures
(plus a new `schema_version` when the meaning of a field changes), then preprocessing updates
its pin.

### Reference validator

```bash
python -I tools/audit/refval.py fixtures .          # the whole catalogue
python -I tools/audit/refval.py check FILE [--json]  # one file
python -I tools/audit/refval.py transition OLD NEW   # one publication step
```

The first command prints `mismatches: 0` on a clean tree. [`tools/audit/`](tools/audit/README.md)
also holds the matrix audit (synthetic datasets run through every brick) and its recorded
results. These are audit tools: no brick may import them, and the one reference reader is
preprocessing.

### Proposing a change

Open an issue or a pull request that changes the normative text **and** the fixtures together,
and record the decision in an ADR ([ADR 0001](docs/adr/0001-experiment-description-v1.md) is
the model) with the rejected alternative and the fixtures that show it. A change that alters what an
existing field means needs a new `schema_version`; readers refuse versions they do not know.
Run `python -I tools/audit/refval.py fixtures .` before you push.

### Audits

Dated evidence, not current status: the [feasibility audit](docs/audits/rfc1-feasibility-2026-11-05.md)
(its addendum wins where they differ), the [consumer audit](docs/audits/s01-consumer-audit-2026-11-06.md),
the [LabChronicle lessons](docs/audits/labchronicle-lessons-2026-11-06.md) and the
[matrix audit](docs/audits/matrix-audit-2026-11-07.md), reproducible with the audit tools.
