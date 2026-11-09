# Vendoring the Spec's test material into a brick

Owner decisions (2026-11-09):

- A brick gets the Spec's test material as a **pinned copy** made by one shared tool,
  [`tools/vendor.py`](../tools/vendor.py). The copy is a test fixture, not a runtime dependency.
- CI **fails** if a brick's copy differs from the Spec at its pinned commit.
- A weekly job **opens an issue** (it never blocks) when the pin is behind Spec main on files
  that matter.
- The Spec keeps the table of which brick pins which commit: [pins.md](pins.md).

The reference implementation is `tests/spec_fixtures/` of morphobricks-preprocessing; the tool
reproduces its `PIN.toml` format and hashing exactly. Principles: [conformance plan](conformance-plan.md) section 1.

## What is copied

`vendor.py` copies this standard set, laid out as in the Spec, into `tests/spec_fixtures/`:

| Spec path | Pinned by |
|---|---|
| `fixtures/` | git tree ID (`git rev-parse <commit>:fixtures`) |
| `docs/experiment-v1.md`, `tools/audit/refval.py`, `tools/audit/refrecords.py` | git blob IDs (`git rev-parse <commit>:<path>`) |

It also writes `PIN.toml` (the full commit SHA and those hashes), a `README.md` ("do not edit;
regenerate with vendor.py") and `.gitattributes` (`* -text`, so git never rewrites line endings).
`vendor.py` manages the **whole destination folder**, `README.md` included: it writes the same
generic README for every brick and `--check` compares it byte for byte, like `PIN.toml` and
`.gitattributes`. morphobricks-preprocessing's `README.md` is still brick-specific (it also
documents its skipped-test gate). Preprocessing adopts the generic README in a later PR, after its
v0.5.0 tag; until then its folder differs from `vendor.py`'s output in that one file, so it must
not run `--check` (or re-run `vendor.py`, which replaces the README) before that PR. Everything
else in its folder is identical to what the tool writes for its pinned commit `1bed024`.
Content comes from git objects of the commit (never the working tree) and is written in binary
mode: copies are byte-exact on every platform.

## Re-pinning a brick

1. In a Spec checkout at the commit you want, run
   `python tools/vendor.py --into <brick root> [--commit <full sha>] [--dest tests/spec_fixtures]`
   (default commit: `HEAD`). The tool replaces the previous copy; files it does not manage in
   the destination make it stop.
2. Run the brick's tests. When the Spec changed text or fixtures, the brick's code and tests
   change in the same pull request.
3. Open a **reviewed** pull request in the brick. Never edit the copy by hand.
4. Update the row in [pins.md](pins.md) (commit, date, PR link).

## The hard check (CI fails)

Two layers:

- **Offline pin test.** Copy [`tools/brick_templates/test_spec_pin.py`](../tools/brick_templates/test_spec_pin.py)
  to `tests/test_spec_pin.py`. It hashes the copy like git (blob = sha1 of `blob <len>\0` + bytes,
  `fixtures/` as a git tree) and fails on one changed, added or missing byte. A skipped pin test must be
  treated as a failure by the brick's gate.
- **Against the Spec.** The offline test trusts `PIN.toml`. To also prove `PIN.toml` is what the Spec says at
  that commit, run `vendor.py --check` in CI. It changes nothing, exits 1 and names each difference:
an edited, missing or extra file, a symbolic link, a `PIN.toml`, `README.md` or `.gitattributes`
that is not byte for byte what `vendor.py` writes, and a pinned commit that is not in the Spec
checkout (fetch the full history, as below):

```yaml
- uses: actions/checkout@v4
  with: { repository: CellMigrationLab/MorphoBricks-Spec, path: spec, fetch-depth: 0 }
- run: python spec/tools/vendor.py --into . --check   # add --dest if not tests/spec_fixtures
```

## The weekly warning (never blocks)

Copy [`tools/brick_templates/spec-freshness.yml`](../tools/brick_templates/spec-freshness.yml) to
`.github/workflows/`. Each Monday (and on demand) it compares, for every path named in `PIN.toml`,
the git hash at the pin with the hash at Spec main. If any differ it opens or updates one issue,
**"Spec pin is behind MorphoBricks-Spec main"**, listing the changed paths and commits. Docs-only
Spec changes outside the pinned paths do not trigger it. The step uses `continue-on-error` and
only needs `issues: write`. It does not close the issue; close it after re-pinning (a closed issue
is not reused: the next run that finds the pin behind opens a new one).

**Private Spec.** The Spec is public today (checked 2026-11-09 without credentials), so the
default `GITHUB_TOKEN` can check it out. The workflow token only reads the brick's own repository
for a private Spec. In that case add a read-only token for the Spec as the brick's repository
secret `SPEC_READ_TOKEN`; the workflow uses it when it exists. The same applies to the
`--check` snippet above (`token: ${{ secrets.SPEC_READ_TOKEN }}`). Without it the weekly job's
checkout fails, the compare step is skipped, and the run shows a `spec-freshness` warning
annotation; the job stays green and blocks nothing. `--check` in the brick's regular CI fails then,
by design: it cannot prove the copy.

## Tests of the tooling

`python -I -m pytest tools` (or `python -I -m unittest discover -s tools`) runs
[`tools/test_vendor.py`](../tools/test_vendor.py).
