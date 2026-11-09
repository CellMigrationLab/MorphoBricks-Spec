# Audit tools (not a runtime package)

These scripts reproduce the executable matrix audit of the experiment description v1
([`docs/audits/matrix-audit-2026-11-07.md`](../../docs/audits/matrix-audit-2026-11-07.md)). They are
**audit tools only**: no brick may import them, and the single reference reader of v1 stays
preprocessing ([conformance plan](../../docs/conformance-plan.md)). They read the normative text and
fixtures of this repository; nothing here is a rule.

| File | What it does |
|---|---|
| `refval.py` | Throwaway reference validator of `docs/experiment-v1.md`: phases 1-5 and warnings (section 6), canonical writer (9.1), section digests (9.3), the two-file predecessor checks (4.4a, 4.6, 4.9). `python -I refval.py fixtures <spec root>` runs the whole fixture catalogue; `check FILE [--json]` one file; `transition OLD NEW` one transition. Choices where the text is ambiguous are marked `AMBIGUITY` in the code. |
| `refrecords.py` | Throwaway reference validator and canonical encoder of `morphobricks.records.jsonl` (experiment-v1 section 4.6: the three typed record forms, RR1-RR3, and the byte rules). `python -I refrecords.py check FILE [--json]` checks one file; `refval.py fixtures` checks the 37 goldens of `fixtures/records/`. A refused file is `R_RECORDS_FILE_INVALID`; its `E_RECORDS_*` names are the reasons (owner decisions RF1-RF6). |
| `matrix.py` | The case matrix: one base case varied one factor at a time over every level of the four dimensions, plus a greedy all-pairs array over five interacting factors. For each case: the synthetic dataset (32x32 TIFF images and masks), the user's confirmed answers, the `morphobricks.toml` they give (canonical bytes from `refval.write`) and the spec's expected outcome (`E_`/`W_` from `refval`, `R_`/`A_` from the physical oracle `physical()`). `python -I matrix.py` prints the expected outcome of every case. |
| `steps.py` | One brick step as a user runs it, executed in the bricks' environment: preprocessing `check`, `design`, `run`, `masks` (CLI); CellPatcher `grid`/`random`/`whole_fov`/`cell` on the preprocessing run (grid with normalization by biological repeat); a MorphoFeature run file per provider (MorphoObjects with a CellPatcher patch set, MorphoRelate, fiberfeatures; MorphoEmbed `check` only); MorphoCoverage `condition_contrast` on MorphoFeature's coverage export. Prints one JSON observation. |
| `runner.py` | Runs every case (or the named ones): writes the dataset, runs the steps in order (a refusal stops the steps that need its output), records the observations, deletes the dataset. Results are merged into one JSON file so a run can resume. |
| `classify.py` | Gives every (case, brick) cell a verdict (MATCH, MISMATCH-SPEC, MISMATCH-BRICK, BUG, N/A, SKIP) by fixed rules, with every judgement made by reading an observation listed in `OVERRIDES` with its reason, and prints the case table. |
| `results/` | The recorded run of 7 November 2026: `matrix-results-2026-11-07.json` (compact observations; paths stripped) and `cases/<case>.toml` (read by `classify.py`; the expected `morphobricks.toml` of each case, headed by its expected outcome). |

## Reproduce

The tags below are the pins of 7 November 2026 and will age at the next release.

```bash
python -I tools/audit/refval.py fixtures .          # 37/37, 135/135, 13/13, 3 golden CSVs, 37 records goldens, round trip
uv venv venv-mx -p 3.13
uv pip install -p venv-mx/bin/python --extra-index-url https://download.pytorch.org/whl/cpu \
  --index-strategy unsafe-best-match \
  "morphobricks-preprocessing @ git+https://github.com/CellMigrationLab/morphobricks-preprocessing@v0.4.0" \
  "morphobricks-normalization @ git+https://github.com/CellMigrationLab/morphobricks-normalization.git@v0.3.4" \
  "cellpatcher @ git+https://github.com/CellMigrationLab/CellPatcher.git@v0.2.0" \
  "morphofeature[cli] @ git+https://github.com/CellMigrationLab/MorphoFeature@v0.1.0" \
  "morphoobjects @ git+https://github.com/CellMigrationLab/MorphoObjects@v0.1.0" \
  "morphorelate[yaml] @ git+https://github.com/CellMigrationLab/MorphoRelate@v0.1.1" \
  "morphoembed[provider] @ git+https://github.com/CellMigrationLab/MorphoEmbed@v0.1.0" \
  "fiberfeatures @ git+https://github.com/CellMigrationLab/fiberfeatures@v0.2.1" \
  "morphocoverage @ git+https://github.com/CellMigrationLab/MorphoCoverage@64ff307d90fe5eb62a72630f35b85bd7fe6040a4"
cd tools/audit
../../venv-mx/bin/python runner.py ../../venv-mx/bin/python /tmp/mx-data /tmp/mx-results.json   # about 20 min
python -I classify.py /tmp/mx-results.json > table.md
```

The runner needs about 1 MB of disk per case at a time (each dataset is deleted after its case).
MorphoEmbed weights are not downloaded: its request is planned with `morphofeature check` and the
refusal is recorded (planning passes up to the missing checkpoint).
