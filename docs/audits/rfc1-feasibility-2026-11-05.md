# Feasibility of MorphoBricks-Spec RFC #1 (`morphobricks.yaml`, experiment schema v1)

Date: 2026-11-05. RFC: https://github.com/CellMigrationLab/MorphoBricks-Spec/issues/1 (no comments yet;
the Spec repo has no commits). This is an assessment only: no code changed and nothing posted.

## Executive summary

1. **Recommendation: implement a reduced version, after the release. Nothing in the RFC is a release blocker, and no tag should move.** Today the code refuses heterogeneous channel layouts (`different_channel_counts`, `channel_names_differ`). That is a safe refusal, not a science defect.
2. **Real gaps it fills:**
   - **Semantic channel identity is confirmed once.** Today MorphoFeature, MorphoRelate and fiberfeatures each ask for it again, or read it from OME names that most TIFFs lack.
   - **Repeat-group pairing reaches MorphoCoverage.** Today MorphoCoverage pairs repeats by the raw `biological_repeat` label.
   - **Condition → reference edges** replace a boolean `control` that no brick consumes.
3. **Duplicated:** repeat-group pairing, confirmation and reconciliation already exist in `experiment_design.csv` (`design.py:375-427`). Mask inventory and mask kinds already exist in the manifest and `mask_relationships.json`.
4. **The expensive part is variable channel counts and orders (M5 + M6 + M7).** It is not a schema problem. Every MorphoBricks table names channels by index (`_C<i>`, normalization plan N41/N42, decided 27 Oct 2026). Normalization pools by index. CellPatcher selects by index. Rough cost: 20–25 PRs in 6 repos, with a breaking normalization schema.
5. **Contradictions to fix before M0:**
   - The masks' `axes`/`plane_scope: shared` conflict with the 2-D-only decision (PR #173).
   - `experiment` means three different things across the bricks, and as a condition field it defines MorphoCoverage's FDR families.
   - Header names are compared with IDs; the RFC's own `DNA`/"DAPI" example would be refused by MorphoFeature today (`channels.py:93-117`).
   - `R001` IDs depend on processing history.
   - The per-group comparability confirmation (N35) is silently lost.
   - Calibration has no place in the schema.
6. **YAML is the wrong format:** I reproduced it with PyYAML 6.0.1 `safe_load`. `012` → `10`, `NO` → `False`, `2026-01-01` → `date`, and a duplicate condition key is silently overwritten (even `BaseLoader` does that). TOML (stdlib `tomllib`, already used by MorphoRelate) or strict JSON avoids all four.
7. **Sequence:**
   - **Stage 0:** owner decisions, then M0 as docs + schema + fixtures only.
   - **Stage 1:** preprocessing v0.5 (additive). The experiment file still requires one ordered channel list for the whole experiment. Preprocessing keeps writing `experiment_design.csv` derived from the file, and adds a semantic channel API to `RunInputs`. Bricks adopt it at their own pace.
   - **Stage 2:** heterogeneous layouts, gated on real datasets and a normalization table v5 design. I recommend semantic wide columns over long format.
   - Drop M10–M12 from this roadmap.

---

## 0. Evidence base

| Repo | Commit read |
|---|---|
| morphobricks-preprocessing | `origin/main` `56501ac`; PR #173 head `e87a2fc` (`claude/2d-planes-only`), treated as the intended v1 state. Line numbers below are from `e87a2fc` unless marked |
| morphobricks-normalization | `b3999de` |
| CellPatcher | `828379b` |
| MorphoFeature | `475216e` |
| MorphoCoverage | `64ff307` |
| fiberfeatures | `ddb68dc` |
| MorphoRelate | `2042693` |
| MorphoObjects / MorphoEmbed | `ba3f6d7` / `422cc01` |

LabChronicle is not in this session, so I did not verify the RFC's claims about it (A2, M10).

---

## 1. Problem fit

### 1.1 What exists today

| RFC element | Today | Where |
|---|---|---|
| Repeat groups, folder pairing across conditions | `experiment_design.csv` `repeat_group`; default is the folder name; the user moves folders between groups; at most one folder per condition | contract §12 (`docs/contract.md:384-420`); `design.py:47-57`, `with_group` `design.py:233` |
| Comparability confirmation per group (normalization plan N35) | `confirmed`, `confirmed_on`; a new folder reopens its group | `design.py:253`, `reconcile_design` `design.py:375-427` |
| Reconciliation on rerun | Implemented. Known folders keep their group, control mark and confirmation. A new folder joins the group named after it, inherits its condition's control mark and reopens the group. A missing folder is **dropped without asking** | `design.py:375-427` (drop at `:425`); contract `:408` |
| Controls | Boolean `control` per condition. **"Recorded only"**: no brick uses it scientifically. MorphoFeature's notebook only displays it (`notebook_steps.py:158-168`); MorphoCoverage ignores it and guesses controls from names, then asks (`_guided_controls.py:40-60`) | contract `:407` |
| Channel names | Read **only** from OME-XML `Channel@Name` (`metadata.py:514-535`) and OME-Zarr `omero` labels (`zarr_input.py:53`); ImageJ hyperstacks give none. Recorded per file in the manifest; compared across the whole experiment by index (`channel_names_differ`, `metadata.py:584-622`) | contract `:61` |
| Channel count | One count for the whole experiment: `different_channel_counts` (`size_checks.py:86-121`), because a table row holds every channel (N43) | contract `:65`, §11 |
| Calibration | `calibration.csv` in the output folder: statements scoped to path (`.`, folder, **single image**). The run never writes it. Pinned by `calibration_sha256`, which `RunInputs` checks | `calibration.py:1-27`, contract §9.3 |
| Masks | Inventory, pairing, axes and shape in the manifest. Kinds (`instances`/`grouped`/`one_value`) are suggested by the mask step (`mask_relationships.json`), with no stored confirmation yet | contract §15, §15.1 |
| Brick access | `RunInputs.fovs()` gives `Fov.channel_names` and `c_count` (`run_inputs.py:101-138`); `design()` returns the strict design (`:358-380`) | contract §9.1 |

### 1.2 Each part judged

| Part | Verdict | Why |
|---|---|---|
| **Semantic channel IDs confirmed once** | **Real gap, highest value** | Each brick asks for channel names on its own:<br>• MorphoFeature takes one global `channels:` list from its YAML run file, or the recorded OME names when every channel is named (`run_config.py:327-349`).<br>• MorphoRelate `init` writes `ch0, ch1…` or the user's names and refuses different counts (`project_config.py:101-127`).<br>• fiberfeatures selects by recorded OME names only (`run_reading.py:108-142`).<br>• CellPatcher selects by index (`config.py:243-261`).<br>Without OME names, **nothing** detects two repeats exported with swapped channel order: normalization pools `C0` with `C0`. A confirmed per-member declaration, checked against headers where they exist, closes this. |
| **Variable channel order or count between members** | Real but **unquantified** need; the most expensive part (§2) | Today's remedy is to "split into a separate experiment" (`size_checks.py:117-119`). Ask how many real datasets need this before paying for M6. |
| **Repeat groups (`repeats.R00x.members`)** | **Duplicates** `experiment_design.csv` | The pairing model is identical. What is new is the opaque ID; what is lost is the confirmation (§3.6). Moving it into the file is fine; its value lies in having one file, not in new behaviour. |
| **Repeat groups reaching MorphoCoverage** | **Real gap** | MorphoCoverage compares "biological repeat by biological repeat" on the `biological_repeat` column (`_control.py:1-15`). MorphoFeature's coverage export carries raw folder labels and no `repeat_group` (no match in `coverage_export.py`). Repeats paired across differently named folders (`rep2` ↔ `experiment_23`) are therefore **not** paired in MorphoCoverage. |
| **`reference` edges** | **Real gap**, but a single `reference` is weaker than MorphoCoverage | MorphoCoverage's `comparisons` allow one condition in several comparisons (`THBS5_SiCol6a1` vs `THBS5_SiNC` **and** vs `VEC_SiCol6a1`, `_control.py:5-10`). A tree of matched controls is defensible as experiment truth, but the RFC must say that extra contrasts remain MorphoCoverage configuration. |
| **`treatment_key`** | Fits | MorphoCoverage defines it per (control, member) edge (`_guided_controls.py:68`). With one reference per condition, a field on the condition is equivalent. |
| **`target`, `roles`** | No consumer found | YAGNI for v1. |
| **`experiment` (condition field)** | **Harmful as specified** | See §3.4. |
| **Masks section** | Mostly duplicates; partly contradicts the 2-D-only decision | Inventory, axes and shape are in the manifest. `kind` overlaps the mask step's kinds. Only `display_name` and `source_channels` are new. |
| **Reconciliation workflow** | Exists for the design; needs extending to channels and masks | The RFC improves on "removed is dropped silently" (`design.py:425`) by classifying removals. That is a real improvement. |
| **Semantic `RunInputs` API (M5)** | Right direction; can be **additive** | A new `Fov.channel_ids` plus helper methods break nobody. |
| **Histogram schema change (M6)** | Needed **only** for heterogeneous layouts | It also reverses N41 (§2.2). |

---

## 2. Technical feasibility per milestone

The PR counts are rough. "Tagged" means a repo that tags in the coming release (normalization v0.3.4, preprocessing v0.4.0, CellPatcher v0.2.0, then the bricks).

| M | Repos | PRs | Breaking? | Notes |
|---|---|---|---|---|
| M0 | Spec | 1–2 | No | Docs, JSON Schema, fixtures, but only after the owner decisions in §4.3 |
| M1 | Spec **or** preprocessing | 1–2 | No | I recommend **no** separate runtime package (§5.1): it would add a 6th core repo to the tag order and a new dependency for every brick through preprocessing |
| M2 | preprocessing | 2–3 | Additive | Draft model from `Preflight` (`run/preflight.py:45`); reconciliation; atomic publish; manifest key; `RunInputs` SHA check (calibration model) |
| M3 | preprocessing (notebook) | 3–5 | No | The montage renderer is new. Today's preview is the axis step's preview plane (`notebook_axis_preview.py`). Pairing and control UI exist in `notebook_design.py` and must be reworked |
| M4 | preprocessing (+ CellPatcher, MorphoFeature if the CSV goes) | 2 (+2) | **Yes, if `experiment_design.csv` stops being written** | CellPatcher (`normalization.py:133-160`) and MorphoFeature (`experiment_design.py:58-82`) call `read_confirmed_design(path)` directly. Keep writing the CSV, derived from the file, so they are not touched |
| M5 | preprocessing 1–2; MorphoFeature 1–2; fiberfeatures 1; MorphoRelate 2; CellPatcher 2–3; MorphoObjects/MorphoEmbed 0–1 (through MorphoFeature) | **8–12** | Additive in preprocessing; behaviour change in each brick | See §2.3 |
| M6 | normalization 3–5; preprocessing 1–2; CellPatcher 2–3; MorphoFeature 1 | **8–11** | **Yes**: normalization schema v5, `PlaneRecord`, the pooling API and parameter columns | See §2.2 |
| M7 | preprocessing 2 | 2 | Changes refusals into per-member checks | Must also replace `channel_names_differ` (`metadata.py:584-622`), not only `different_channel_counts`; RGB (exactly 3 channels) per member |
| M8 | preprocessing 2–3 | 2–3 | Additive | Most of it exists (contract §15); add the stored confirmation of mask semantics |
| M9 | MorphoFeature 1 (export columns) + MorphoCoverage 1–2 | 2–3 | Additive | MorphoCoverage does not depend on preprocessing (its `pyproject.toml` lists none), so the data must come through MorphoFeature's export |
| M10–M12 | LabChronicle, preprocessing | ? | — | Out of scope (§5.2) |

**Total: about 35–50 PRs across 8 repos**, roughly another release cycle. Without M6/M7 (Stage 1 only, §4.4) it is **about 15–20 PRs, with no breaking change in a tagged repo**.

### 2.1 M7: removing the global `different_channel_counts`

- The refusal exists because the table cannot hold rows with different channel counts. The writer refuses at `csv_io.py:127-133`, the reader at `:205-206`, the summaries at `summaries.py:170`.
- Removing the preprocessing check without M6 would only move the refusal into the normalization writer. **M7 cannot come before M6.**
- `channel_names_differ` must become per-member too. Otherwise CTRL `[DNA, ACTIN]` and DrugA `[ACTIN, DNA]`, both OME-named, still fail the global check.
- The intensity checks (`checks.py:226-344`) compare images and repeats by channel index within a condition. Across repeats of one condition, layouts may differ, so these comparisons must also go by channel ID.

### 2.2 M6: histogram schema v5, and the risk of counting channels as FOVs

**N41 is a cross-brick rule decided 9 days ago.** Normalization plan N41 (`docs/plan.md:385`) says channels go across columns in **every** MorphoBricks table, never in rows. N42 (`:389`) says the channel token is the zero-based index. Schema versions 1–2 *were* long format with a `c` column, and were replaced on 27 Oct 2026 (`csv_io.py:35-36`). The RFC's "leading candidate" (long format) reverses this without mentioning it.

**Where long format would count channels as FOVs or planes** (concrete code paths):

| Code path | What happens with long format |
|---|---|
| `duplicate_planes` (`records.py:151`) | Refuses two rows with one `plane_id`. The key would have to become `(plane_id, channel)`; any consumer still keyed on `plane_id` either fails or keeps one channel |
| `scope_groups` and group keys (`scopes.py:33-133`) | Group rows by repeat group or image. Every channel row would fall in the same group. CellPatcher's per-group table reports `"planes": len(records)` (`normalization.py:411-412`), which would triple for 3 channels |
| `PooledHistogram` / `pooled_statistics(channel=)` (`pooling.py:348-393`) | Pools whatever rows it is given. Without a mandatory channel filter, DNA and ACTIN rows of one group are pooled into one histogram. That is silent and catastrophic |
| `IntensityCheckSettings.min_images` (5) and `unbalanced_images` | Count images. A naive count of rows would see 3× the images |
| MorphoCoverage observation counting | Already sensitive to this: "MorphoCoverage counts a field's planes as one observation" (`coverage_export.py:21-25`) |

**Alternatives the RFC does not consider:**

| Option | Shape | Pros | Cons |
|---|---|---|---|
| (a) Ragged index-wide | v4 plus per-row `channel_count` (it already exists as a column); cells beyond a row's count must be empty, and the reader refuses any value there | Smallest change; one row per plane is kept | Semantics stay outside the table: `C0` means different stains in different rows. Every consumer must join the per-member mapping, and an offline reader that does not gets mixed stains silently. **Reject.** |
| (b) **Semantic-wide (recommended)** | One row per plane (N41 kept); columns by **channel ID** (`Histogram_Count_ACTIN_00042`); a channel a member lacks is **empty, with a per-row `channels` list** stating which are present; the reader refuses a value outside that list and an empty cell inside it | Self-describing; the sampling unit is unchanged; consumers stop mapping indices; absence is explicit, never zero | Replaces N42 (token = index) for this table; columns depend on the experiment's IDs, so renaming an ID rewrites the table (correctly). The relabel must reuse staged histograms, not reread pixels (A8) |
| (c) Long | `(plane, channel)` rows | Natural for heterogeneity | Reverses N41; all the risks above; a channel ID such as `NA` or `None` passes the token rule but pandas reads it as missing (§3.8) |

**M6 acceptance criteria to add to the RFC's list:**

- On a homogeneous experiment, v5 gives **bit-identical** parameters, summaries and intensity warnings to v4.
- Pooling APIs take a channel ID and refuse to pool without one.
- Image and plane counts in every summary are unchanged by the number of channels.
- No API anywhere accepts mixed channels.

### 2.3 M5: what each brick must change

| Brick | Today | Change |
|---|---|---|
| preprocessing | `Fov.channel_names`, `c_count` (`run_inputs.py:101-138`) | Add `Fov.channel_ids` (ordered, per member); `channel_index(fov, id)`; `read_channel(fov, id, t=)`. A `t` argument is required, since T>1 is still allowed (`read_plane` takes `z, t`). Additive |
| MorphoFeature | `ChannelCatalogue` is already per FOV (`channels.py:57-146`), but `_catalogue` fills it from **one global list** (`run_config.py:327-349`) | Fill it from `Fov.channel_ids`; make run-file `channels` a cross-check or remove it. `check_metadata_names` (`channels.py:93-117`) must compare against the confirmed header aliases (§3.9), not against the ID. `require_same_channels` (`:149`) and the scaling fits (`fits.py:175-182`, `catalogue.resolve`) already work by name. **1–2 PRs, low risk** |
| fiberfeatures | Selects by recorded OME names, never by position (`run_reading.py:108-142`); its metadata table is already long (`c`, `channel` columns), grouped by FOV key (`fov_blocks.py`) | Select by channel ID; keep `c` as provenance. 1 PR |
| MorphoRelate | `init` writes one global name → index map and refuses different counts (`project_config.py:101-127`); `InputConfig.channels: Mapping[str, int]` is global (`io/run_source.py:142`) | Global → per-FOV mapping is a real refactor of its config model. 2 PRs |
| CellPatcher | Index-based `split_channels`/selection (`config.py:243-261`); `Normalization_Offset_C<i>` columns (`export.py:70`); pooling by index (`normalization.py:411`) | Select by ID; parameter columns by ID; patches from members with different orders must be stored in one declared channel order, or labelled per row. 2–3 PRs, **plus** the M6 adaptation |
| MorphoObjects, MorphoEmbed | Receive channels through MorphoFeature; MorphoObjects uses `RunInputs` for calibration only | Nothing beyond MorphoFeature |

---

## 3. Design flaws and contradictions

### 3.1 The masks contradict the 2-D-only decision (row 36, PR #173)

- PR #173 removes the stated shared 2-D mask: a `YX` statement is the error `shared_mask_not_supported` (`masks/stated.py:25`), and `RunInputs.open` refuses any record with `shared: true`. Z>1 is refused (`size_checks.py:49`).
- The RFC's own example declares `axes: YX` and `plane_scope: shared` for every mask. Under v1 these are refused.
- In v1 a mask's axes are **determined**: the image's T (if any) + `YX`. `plane_scope` has one legal value.
- **Remove both fields from v1.** A mask's axes stay manifest facts.
- The one header-repair statement that survives (`--mask-axes Cells=TYX` for a plain stack) is file interpretation and stays in the recorded inputs, not in the schema.

### 3.2 Calibration has no place

- The RFC lists calibration in discovery (step 1) but has no section for it.
- `calibration.csv` statements can target **one image** (`calibration.py:11-14`), which the RFC forbids in the file ("no per-FOV overrides").
- **Decision needed, and my recommendation:** calibration stays in `calibration.csv`, which already has strict reading, its own SHA in the manifest and the `RunInputs` check. The spec must say so explicitly, so nobody adds a `pixel_size` field to members later.
- The same applies to `image_type`, which is recorded in the manifest (contract §13). Say where it lives.

### 3.3 Migrating the boolean `control` to `reference`

Migration is deterministic only in two cases:

| Controls marked in `experiment_design.csv` | Migration |
|---|---|
| 0 | No references |
| exactly 1 (C) | Every other condition → `reference: C`; C has none |
| ≥2 | **Not deterministic.** Which DrugA → which control? MorphoCoverage's answer is a name-stem heuristic (`_guided_controls.py:40-66`), which is a guess. The migration must write a **draft** with unresolved references and refuse to publish until the user answers |

Further points:

- The boolean also cannot express chains (`VEC_SiNC` is both a control and has a reference, `VEC`).
- After migration, "is a control" is derivable (some condition references it), so **drop the boolean** rather than keep two truths.
- Use the **strict** reader for migration. The lenient `read_experiment_design` accepts `yes/no/1/0` and reads an **empty `control` as false** (`design_values.py:19-20`). That is a silent coercion, which a migration must not carry into the new file.

### 3.4 `experiment`: a condition field versus an identity level

`experiment` already has three meanings:

1. **fiberfeatures:** an optional identity level *above* `biological_repeat`, part of the FOV key (`fov_blocks.py:27`, `:52`).
2. **MorphoCoverage:** each condition's declared experiment = the **multiple-testing correction family** (`sampling_unit/discovery.py:287-289`, `:513` "`families`, each condition's declared experiment").
3. **preprocessing:** none. One experiment root is one experiment; `FOV_KEY` has no such level (`discovery.py:55`). fiberfeatures repeats it: "One run is one experiment" (`run_reading.py:13`).

As a condition field, `experiment` **is** an FDR-family declaration. That contradicts the RFC's own exclusion ("Do not put … FDR families … in the experiment schema"). If it were instead an identity level, it would change pairing: conditions of two sub-experiments sharing folder names would default into one repeat group.

**Drop it from v1.** One file describes one preprocessing experiment, and sub-experiment families stay MorphoCoverage configuration.

### 3.5 Technical repeats: absent from the schema, present everywhere else

- `technical_repeat` stays in `FOV_KEY`, in every table row, in the manifest and in fiberfeatures blocks. Keeping it out of the schema is fine.
- **The RFC's suggested remedy is a science error.** It says a technical repeat with a different layout should be split "into a separate biological-repeat". Moving data into a new biological-repeat folder **fabricates a biological replicate**, inflating n in every repeat-level statistic. The remedies must be:
  - exclude the technical repeat;
  - re-export it with the member's layout;
  - wait for a later per-technical-repeat extension.
- The RFC drops `image_count`/`technical_repeat_count` "at the time of confirmation" (A7). Today they record what the user confirmed as comparable (contract §12). Without them, reconciliation cannot tell that a confirmed member has gained technical repeats since confirmation. Keep that evidence in provenance (manifest or report), not nowhere.

### 3.6 The comparability confirmation (N35) silently disappears

- Today every repeat group must be confirmed with "Were these images prepared and acquired under the same circumstances…?" (contract §12, `design.py:253`). Normalization, CellPatcher and MorphoFeature refuse unconfirmed designs (`read_confirmed_design`).
- The RFC has no such flag. Either "published file" must be defined to mean every group was confirmed, with new members reopening their group before the next publish, or the confirmation must be kept explicitly.
- As written, M4 deletes a scientific gate.

### 3.7 `R001` IDs: stability and reconciliation

- "Deterministic and stable across reloads; do not renumber when an earlier-sorting repeat appears" (A3) makes IDs depend on **processing history**, not on the data. Two people who process the same folder in different increments get different IDs.
- Removal semantics are undefined:
  - If a group whose members all disappeared is deleted, its number can be reused. The same ID then names different data across runs, and downstream outputs (normalization `normalization_group`, MorphoFeature fit records) conflate them.
  - If it is kept, the file needs tombstones or a stored counter, which is state outside the four sections.
- Rename: identities are never parsed, so a renamed folder is "removed + new". That is acceptable only if the new member is **unpaired and pending**, never auto-paired to the removed one's group. The RFC should state this.
- Today's default label is the folder name (`rep1`). It is data-derived, human-readable and already flows into normalization group names and CellPatcher outputs. Switching to `R001` changes those strings in every downstream output for no scientific gain.
- **Recommendation:** keep "group label defaults to the biological-repeat folder name, editable, identity-checked", as today.

### 3.8 Channel-token rules

- MorphoFeature's token rule (`naming.py:19`) accepts `NA`, `nan`, `None`, `null`. Preprocessing's identity rule refuses those (`MISSING_TEXT`, `discovery.py:60`) because table readers turn them into missing values.
- The token rule is case-sensitive, but `check_identity_case` (`discovery.py:146`) refuses names that differ only in case.
- The spec must require **both** rules for channel IDs and mask IDs:
  - token rule, plus `check_identity_text`, plus uniqueness ignoring case;
  - for mask IDs, MorphoFeature's object-set rule (no reserved compartments such as `cell`/`nucleus`, case-insensitive; `identity.py` `check_object_set_name`, `naming.py:18`).
- Otherwise the spec validates names that a brick refuses later.
- I also recommend refusing channel IDs equal to MorphoRelate compartment tokens, since those tokens appear in the same column positions.

### 3.9 "Header names are evidence": what preprocessing reads from headers

- Names come only from OME-TIFF `Channel@Name` and OME-Zarr `omero` labels (`metadata.py:514-535`, `zarr_input.py:53`). ImageJ TIFFs, the common Fiji export, give **no** names. Emission wavelengths and fluorophores are not read.
- In practice, step 2's "same header channel order/names where known" will usually be "unknown", and the guard is the user's confirmation.
- Header names are display strings (`DAPI`, `Alexa Fluor 488`), while IDs are semantic tokens (`DNA`). "Contradiction" is undefined:
  - The RFC's own example (`DNA`, display "DAPI") would be **refused today** by MorphoFeature: `check_metadata_names` requires the declared name to equal the OME name (`channels.py:109-117`).
- **Required:** a per-channel `header_names` list of exact (trimmed) strings that the user confirmed as evidence for that channel. A header name outside the confirmed channel's list is a refusal. MorphoFeature's check must change to use that list.

### 3.10 Location and provenance of the file

The output folder is the only sensible place, next to `experiment_design.csv` and `calibration.csv` (the default output is a sibling of the experiment, `discovery.py:214-220`). Consequences the RFC does not state:

- "One output folder belongs to one experiment", but one experiment can have several output folders (different exclusions). The "experiment truth" is therefore per output folder and can diverge. State it, or forbid it.
- **Writer model.** Choose the `calibration.csv` model: written by the notebook or CLI under the output folder's lock; never written, replaced or removed by `run`; pinned by SHA in the manifest; `RunInputs` refuses a changed file.
  - Do not use the `experiment_design.csv` model, in which the run publishes it as part of the generation.
  - The draft/staging file of RFC step 8 then needs a name and a lock rule too.
- **Symlinks:** refuse a symlinked file (owner decision); open it without following links.
- **SHA:** over the exact bytes parsed, as `read_confirmed_design` does. Deterministic serialisation is needed (the same content gives the same bytes, as contract §12 requires for the CSV).

### 3.11 Cache-key consequences (A8)

- In preprocessing, A8 already holds: design and calibration changes recompute no row (row key, contract §9). A `restart` after editing a reference reuses every row; only the manifest changes.
- The brick cache (`brick_cache.entry_key`) keys on pixel digests, channels, masks and requests, not on the preprocessing manifest. It is unaffected.
- **Exception:** MorphoFeature's fits from saved histograms identify an image by `(run.manifest_sha256, image, fingerprint)` (`fov_files.py:211`, used at `fits.py:175`). Every metadata-only edit plus restart gives a new manifest SHA, so those trial fits are recomputed (they read no pixels, so the cost is modest). "Full SHA is provenance, not a cache key" needs a mechanism:
  - record per-section digests (`channels`, `repeats`, `conditions`, `masks`, each the SHA of a canonical serialisation) in the manifest;
  - let consumers key on the section they use (scaling fits on `repeats` + `channels`, never `conditions`).

### 3.12 YAML, and the strict unknown-field policy

The rule against parsing identities is about not *deriving* identity from strings. Reading declared text exactly is fine, but YAML 1.1 typing does derive. Reproduced with PyYAML 6.0.1 `safe_load` (MorphoFeature already reads its run files this way, `run_config.py:321`):

```text
NO:                 -> key False
CTRL twice          -> second silently wins (also with BaseLoader)
biological_repeat: 2026-01-01  -> datetime.date(2026, 1, 1)
biological_repeat: 012         -> 10   (octal)
biological_repeat: 1.0 / 1_000 -> 1.0 / 1000
biological_repeat: ~ / off     -> None / False
```

- `BaseLoader` fixes typing (every scalar becomes text) but **not** duplicate keys, and it needs anchors and aliases refused.
- Preprocessing has no YAML dependency today (`pyproject.toml` lists numpy, tifffile, scipy and normalization). Adding PyYAML would add it to every brick.
- **TOML:**
  - `tomllib` is stdlib on the required Python ≥3.11.
  - Duplicates are an error by specification (verified: "Cannot declare ('conditions','CTRL') twice").
  - Unquoted text is a syntax error, so `rep1` must be `"rep1"`; nothing is typed implicitly.
  - Bare keys are text.
  - MorphoRelate already reads TOML and writes it with its own `toml_value` (`project_config.py:295`).
- **Strict JSON** (with an `object_pairs_hook` that refuses duplicates) matches the manifest and JSON Schema natively, but is less pleasant to read.
- **Recommendation:** TOML, or JSON if hand editing is truly secondary. The file name should then not be `.yaml`.

**Unknown fields:** strict refusal is consistent with existing practice. Readers refuse a manifest version they do not know (contract §9), and any change to the contract requires a new `schema_version` (contract line 3). Rules:

- any new field bumps `schema_version`;
- readers refuse newer versions with an actionable message;
- no `x-` extension namespace, which would be a back door for unvalidated semantics.

Only preprocessing reads the file (bricks go through `RunInputs`), so the coupling cost is small.

### 3.13 Other issues

- **RGB:** `image_type: rgb` treats C0–C2 jointly (contract §13). Per-channel semantic IDs make no sense for H&E. Define a rule (one joint channel ID, or a refusal).
- **Mask IDs:** "semantic mask name" in step 7 implies renaming discovered mask types, but the file stores no mapping from type to ID, and identities are never parsed. In v1 the mask ID must equal the discovered type name; `display_name` is enough for the UI.
- **`source_channels` versus the 2-D rule:** a mask derived from DNA in a member where DNA is absent should be a validation error (or warning). State which.
- **Unused declared channels and members without masks:** define warning versus error.
- **A condition and its reference with no shared repeat group** cannot be paired by MorphoCoverage. Warn at publish.
- **"The user must not create this file before preprocessing" (A-goal) versus M10**, where LabChronicle prefills it: reconcile the two (an import produces a draft, never a published file).
- **A10, no defaults:** agreed.
- **A4, list order only for channels:** agreed. With TOML arrays of tables, the order of members must also be declared non-semantic.

---

## 4. Should it be implemented?

### 4.1 Before or after the first release?

**After.** Nothing in the RFC fixes a defect in the code being tagged:

- Heterogeneous layouts are refused, not mishandled.
- `experiment_design.csv` works and is strictly read.
- The one silent risk, swapped channel order in experiments whose headers name no channels, is a documented limitation ("channels are matched by their number", contract §2).

Changing any of this now would move normalization v0.3.4 (M6), preprocessing v0.4.0 (M2–M7) and CellPatcher v0.2.0 (M4–M6), and it would invalidate the pending ChatGPT blocker batch 8. **Pre-release action:** one sentence in the release notes and the user guide stating the channel-order limitation for unnamed headers.

### 4.2 All of it, or a subset?

**A subset, in two stages.** The schema shape (per-member channel lists) can be fixed now, so that Stage 2 only relaxes a validator and does not change the file format.

### 4.3 What must be decided first (owner)

1. **Is heterogeneous channel count or order a real v1 need?** How many current datasets? This gates M6 and M7.
2. **File format:** TOML (recommended), strict JSON, or YAML with a custom loader (text-only scalars, duplicate refusal, no aliases).
3. **Writer model and location:** output folder, calibration model (§3.10); whether several output folders per experiment are allowed.
4. **Repeat-group labels:** folder-name default (recommended) or `R001`; removal and reuse rules.
5. **Reference model:** a single matched control (tree), with extra contrasts left to MorphoCoverage; drop the boolean; behaviour of the migration with ≥2 controls.
6. **Drop `experiment`, `target`, `roles`, mask `axes`/`plane_scope`/`kind` from v1?** (Recommended: yes; keep `treatment_key` optional.)
7. **Header evidence:** a per-channel `header_names` list and the definition of a contradiction.
8. **The comparability confirmation (N35):** implied by publishing, or an explicit flag.
9. **Table v5 shape** (Stage 2 only): semantic-wide (recommended) versus long. This is an amendment of N41/N42.
10. **Spec packaging:** docs + schema + fixtures only, with preprocessing as the sole validator (recommended), or a runtime package.

### 4.4 Recommended sequence (minimal churn in tagged repos)

| Stage | When | Content | Tagged repos touched |
|---|---|---|---|
| **0** | Now, in parallel with the release (docs only) | Owner decisions (§4.3) → M0 | none |
| **1** | After the brick tags | **preprocessing v0.5.0 (additive):**<br>• the experiment file with `conditions` (`reference`, `treatment_key`), `channels` (`display_name`, `header_names`), `repeats` (members with ordered `channels`) and `masks` (`display_name`, `source_channels`);<br>• the validator **requires every member's list to be identical** (today's invariant, now named and confirmed);<br>• draft, reconciliation, publish, manifest `experiment_sha256` + section digests;<br>• `RunInputs` gains `channel_ids` and readers by ID;<br>• `experiment_design.csv` is **still written, derived** from the file, in the same schema-v1 bytes;<br>• migration from the existing CSV. | preprocessing only; consumers unchanged |
| **1b** | As each brick wants | MorphoFeature: catalogue from `RunInputs`, header aliases; fiberfeatures: select by ID; MorphoRelate: names from the run; MorphoFeature export: `repeat_group`/`reference` columns → MorphoCoverage prefill (M9) | one minor release per brick |
| **2** | Only if decision 1 says yes | Normalization v0.4.0 with table v5 (semantic-wide) and ID-based pooling, summaries and checks; preprocessing v0.6 relaxes the equal-lists rule to per-member checks (M7); CellPatcher v0.3 by ID | normalization, preprocessing, CellPatcher (breaking, coordinated) |
| **3** | Later | Mask-semantics confirmation in the notebook (M8 remainder); the `experiment_design.csv` compatibility output retired after a deprecation cycle | preprocessing |

Why Stage 1 must keep identical lists: if members could differ only in order, the v4 table's `C0` would mean different stains in different rows, and CellPatcher's repeat-group pooling by index (`normalization.py:411`) would mix them silently. Order differences therefore need Stage 2 too.

---

## 5. How

### 5.1 Merge, split or drop

| Milestone | Action |
|---|---|
| M0 | Keep; contents in §5.3 |
| M1 | **Merge into M2** (preprocessing is the only reader). The Spec repo ships fixtures, which preprocessing tests pin by commit |
| M2 + M4 | **Merge** (the file replaces the design in the same release, with the derived CSV kept) |
| M3 | Split: (a) channel naming and pairing cards; (b) montages. The montage is UX, not a correctness gate |
| M5 | Split: preprocessing API (Stage 1) / each brick's adoption (Stage 1b) |
| M6 + M7 | **Merge into Stage 2**; gated |
| M8 | Reduce to the stored mask confirmation; the rest exists |
| M9 | Keep; it goes through the MorphoFeature export, since MorphoCoverage has no preprocessing dependency |
| M10, M11, M12 | **Drop from this roadmap** (separate issues if wanted). M11 (pixel embeddings for channel QC) is the kind of model-based inference the refusal rules make advisory-only anyway |

### 5.2 Fields for v1 (after the decisions)

- **Top level:** `schema`, `schema_version`.
- **`conditions.<ID>`:** `display_name`, `reference?`, `treatment_key?`.
- **`channels.<ID>`:** `display_name`, `header_names` (list, may be empty).
- **`repeats.<label>`:** `members` = list of {`condition`, `biological_repeat`, `channels`}.
- **`masks.<type>`:** `display_name`, `source_channels?`.

Removed: `experiment`, `target`, `roles`, mask `kind`/`axes`/`plane_scope`.

Out of scope, stated explicitly: calibration (`calibration.csv`), image type, exclusions and mask-axis statements (recorded inputs/manifest).

### 5.3 What M0 should contain

1. `README.md`: scope, non-goals, the owner decisions with dates, and the relation to `experiment_design.csv`, `calibration.csv`, `run_manifest.json` and `RunInputs`.
2. `docs/experiment-v1.md`, normative:
   - fields, identity rules (token + `check_identity_text` + case-uniqueness + reserved names);
   - reference rules (exists, not self, acyclic, one per condition);
   - member rules (unique (condition, biological_repeat); each in exactly one group; at most one member per condition per group);
   - channel rules (declared, unique per member, header evidence);
   - the confirmation semantics (N35);
   - reconciliation semantics (new / removed / renamed / conflicting, with what is reopened);
   - writer/lock/SHA model; versioning policy.
3. A table mapping today's files to the schema: `experiment_design.csv` columns, the migration algorithm (§3.3), and what goes where.
4. JSON Schema (2020-12) for structure, and a list of semantic rules with stable error codes (the schema cannot express acyclicity or cross-references).
5. Fixtures, each invalid one with its expected error code. Beyond the RFC's 9:
   - folder names `2026-01-01`, `012`, `NO`, `1.0`, `off`;
   - a duplicate condition key;
   - IDs differing only in case;
   - a channel ID `NA`;
   - a mask ID `Nucleus` (reserved);
   - a reference cycle, a self-reference, an unknown reference;
   - one member in two groups; two members of one condition in a group;
   - a channel twice in a member;
   - `source_channels` naming an undeclared channel;
   - a mask with `axes`/`plane_scope` (refused in v1);
   - an RGB experiment;
   - `single` labels;
   - an unknown field; `schema_version` 2;
   - a symlinked file;
   - a migration from 0, 1 and 2 controls.
6. A versioning policy: strict fields, a version bump for any addition, older readers refuse newer files.

### 5.4 Acceptance tests

**Stage 1 (preprocessing v0.5.0):**

- **Parser:** every typing fixture round-trips as exact text; duplicates, aliases, BOM, a symlink, and non-text scalars where text is required are each refused with their code.
- **Determinism:** the same content gives the same bytes and SHA; a reorder of members or conditions changes nothing semantic.
- **Reconciliation:**
  - a new folder → a pending member, its group reopened, nothing published until confirmed;
  - a renamed folder → removed + new, **never auto-paired**;
  - a group emptied → reported, and its label not reused for different data;
  - a new earlier-sorting folder → no relabelling.
- **Header evidence:**
  - an OME name outside the channel's `header_names` → refusal naming the image, index and both names;
  - ImageJ without names → the confirmation suffices.
- **Equal-lists rule:** members with different orders or counts → refusal in Stage 1, naming the members (the message says Stage 2 will allow it).
- **Migration:**
  - 1 control → deterministic references;
  - ≥2 controls → a draft with unresolved references, publish refused;
  - a lenient value (`yes`, empty) → refused, not coerced;
  - the derived `experiment_design.csv` is byte-identical to the one today's code writes for the same answers.
- **A8:** editing a reference + `restart` → every row reused and the CSV SHA unchanged; the manifest section digests for `channels`/`repeats` are unchanged.
- **`RunInputs`:** a file changed or removed since the run is refused; `channel_ids` equal the confirmed list for every FOV.
- **2-D:** together with PR #173, no field allows sharing a mask across planes.

**Stage 1b (MorphoFeature):**

- A run without run-file `channels` gets per-FOV catalogues from `RunInputs`.
- `DNA` with header "DAPI" listed in `header_names` passes; it is refused when not listed.
- The coverage export carries `repeat_group`; MorphoCoverage pairs `rep2` with `experiment_23`.

**Stage 2 (normalization v5 + preprocessing + CellPatcher):**

- The RFC's M6 list.
- Bit-identical v4/v5 results on homogeneous data.
- Image and plane counts independent of the number of channels.
- No API can pool without a channel ID.
- An absent channel is never zero or blank-as-value: an empty cell outside the row's `channels` list, and a refusal for any value there.
- CellPatcher patches from members with different orders end up in one declared channel order (or are labelled per row).
- Serial and parallel runs, and a resumed run, are byte-identical.
