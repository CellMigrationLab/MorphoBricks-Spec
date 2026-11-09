#!/usr/bin/env python3
"""Copy the Spec's test material into a brick repository as a pinned, byte-exact copy.

Usage::

    python tools/vendor.py --into <brick repo root> [--commit <sha>] [--dest tests/spec_fixtures]
    python tools/vendor.py --into <brick repo root> [--commit <sha>] [--dest ...] --check

The copy is a test fixture, never a runtime dependency (owner decisions of 2026-11-09). It
holds the standard file set (``fixtures/``, ``docs/experiment-v1.md``,
``tools/audit/refval.py``, ``tools/audit/refrecords.py``) laid out as in the Spec, plus
``PIN.toml`` (the commit and the git hashes of each pinned path), ``README.md`` and
``.gitattributes``. See ``docs/vendoring.md``.

Rules that make the copy trustworthy:

- Content is read from git objects of the given commit (``git ls-tree`` and ``git show``),
  never from the working tree, so uncommitted edits cannot leak in. The default commit is
  ``HEAD``; the pin always records the full 40-digit SHA.
- Every file is written in binary mode. No newline translation happens, on any platform.
- Hashes are git's: ``git rev-parse <commit>:<path>``. They are recomputed from the bytes
  written (blob = sha1 of ``blob <len>\\0`` + bytes; tree as ``git write-tree`` gives it) and a
  mismatch aborts the run.
- ``--check`` changes nothing. It compares the copy with its ``PIN.toml`` and with the Spec
  at the pinned commit, names every differing file and exits 1 on any difference.

Exit codes: 0 success, 1 the copy differs (``--check``), 2 usage or environment error.
Standard library only, Python 3.10 or newer.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SPEC_REPOSITORY = "https://github.com/CellMigrationLab/MorphoBricks-Spec"
DEFAULT_DEST = "tests/spec_fixtures"

#: The Spec folder copied whole and pinned by its git tree-object ID.
TREE = "fixtures"
#: The Spec files copied one by one and pinned by their git blob-object IDs.
FILES = (
    "docs/experiment-v1.md",
    "tools/audit/refval.py",
    "tools/audit/refrecords.py",
)

GITATTRIBUTES = (
    "# The vendored Spec files are byte-exact copies. Git must not touch line endings\n"
    "# (the pin is a hash of the bytes; a CRLF checkout would break it).\n"
    "* -text\n"
)

README = """\
# Vendored MorphoBricks-Spec files

**Do not edit anything in this folder.** It is a byte-exact, pinned copy of
[MorphoBricks-Spec]({repository}) made by the Spec's shared sync tool. Regenerate it with
`vendor.py`, never by hand:

    python <Spec checkout>/tools/vendor.py --into <this repository's root> --commit <full sha>

`PIN.toml` names the Spec commit and the git hash of each pinned path. The pin test hashes
this folder against it offline, and a changed, added or missing byte fails it. The copy is a
test fixture, not a runtime dependency. A fixture that a test fails is a finding for the Spec
repository, not something to change here. How to re-pin: `docs/vendoring.md` in the Spec.

| Here | In the Spec |
|---|---|
| `fixtures/` | `fixtures/` |
| `docs/experiment-v1.md` | `docs/experiment-v1.md` |
| `tools/audit/refval.py` | `tools/audit/refval.py` |
| `tools/audit/refrecords.py` | `tools/audit/refrecords.py` |
"""

PIN_HEAD = (
    "# The MorphoBricks-Spec commit these files are copied from (conformance plan section 1).\n"
    "# Updating the pin is a reviewed change: see README.md in this folder.\n"
)

FULL_SHA = re.compile(r"[0-9a-f]{40}")


class VendorError(Exception):
    """A usage or environment problem (exit code 2)."""


# --- git hashing, as git does it ---------------------------------------------------------


def git_blob_id(data: bytes) -> str:
    """Return the git blob-object ID of ``data`` (``git hash-object``)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def tree_id_from_blobs(files: dict[str, bytes]) -> str:
    """Return the git tree-object ID of a folder given as ``{relative posix path: bytes}``.

    Every file counts as mode 100644. Entries sort by name, a folder as its name plus ``/``.
    """
    root: dict = {}
    for relative, data in files.items():
        node = root
        *folders, name = relative.split("/")
        for part in folders:
            node = node.setdefault(part, {})
        node[name] = data

    def tree(node: dict) -> str:
        entries = []
        for name, child in node.items():
            raw = name.encode("utf-8")
            if isinstance(child, dict):
                entries.append((raw + b"/", b"40000", raw, bytes.fromhex(tree(child))))
            else:
                entries.append((raw, b"100644", raw, bytes.fromhex(git_blob_id(child))))
        body = b"".join(mode + b" " + name + b"\0" + sha for _, mode, name, sha in sorted(entries))
        return hashlib.sha1(b"tree %d\0" % len(body) + body).hexdigest()

    return tree(root)


# --- reading the Spec from git objects ---------------------------------------------------


def _git(repo: Path, *args: str) -> bytes:
    """Run git in ``repo`` and return stdout as bytes (never decoded, never translated)."""
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, check=False
        )
    except FileNotFoundError as error:
        raise VendorError("git is not installed or not on PATH") from error
    if done.returncode != 0:
        message = done.stderr.decode("utf-8", "replace").strip()
        raise VendorError(f"git {' '.join(args)} failed: {message}")
    return done.stdout


def resolve_commit(repo: Path, commit: str) -> str:
    """Return the full SHA of ``commit`` in the Spec repository, or raise ``VendorError``."""
    out = _git(repo, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
    sha = out.decode("ascii").strip()
    if not FULL_SHA.fullmatch(sha):
        raise VendorError(f"{commit!r} does not resolve to a commit")
    return sha


def spec_files(repo: Path, commit: str) -> dict[str, bytes]:
    """Return the standard file set at ``commit`` as ``{path in the Spec: bytes}``.

    Raises ``VendorError`` for a missing path, a symbolic link, a submodule or any mode other
    than 100644 (the tree hash of the copy assumes plain files).
    """
    found: dict[str, bytes] = {}
    for path in (TREE, *FILES):
        listing = _git(repo, "ls-tree", "-r", "-z", "--full-tree", commit, "--", path)
        if not listing:
            raise VendorError(f"{path} does not exist in {commit}")
        for entry in listing.split(b"\0"):
            if not entry:
                continue
            meta, _, raw_name = entry.partition(b"\t")
            mode, kind, _sha = meta.decode("ascii").split()
            name = raw_name.decode("utf-8")
            if kind != "blob" or mode != "100644":
                raise VendorError(f"{name} in {commit} has mode {mode} ({kind}); only plain files")
            if name in found:
                continue
            found[name] = _git(repo, "show", f"{commit}:{name}")
    for path in FILES:
        if path not in found:
            raise VendorError(f"{path} does not exist in {commit} as a file")
    return found


def pinned_hashes(repo: Path, commit: str) -> tuple[str, dict[str, str]]:
    """Return ``(tree id of fixtures, {file: blob id})`` as ``git rev-parse`` gives them."""

    def rev(path: str) -> str:
        return _git(repo, "rev-parse", f"{commit}:{path}").decode("ascii").strip()

    return rev(TREE), {path: rev(path) for path in FILES}


# --- PIN.toml ----------------------------------------------------------------------------


def render_pin(repository: str, commit: str, tree: str, blobs: dict[str, str]) -> str:
    """Return the text of ``PIN.toml``, in the format the preprocessing brick established."""
    lines = [
        PIN_HEAD,
        f'repository = "{repository}"\n',
        f'commit = "{commit}"\n',
        "\n",
        "# `git rev-parse <commit>:fixtures`, the git tree-object ID of the fixtures/ folder. The\n",
        "# vendored folder must hash to it, so one changed, added or missing byte fails a test.\n",
        f'fixtures_tree = "{tree}"\n',
        "\n",
        "# `git rev-parse <commit>:<path>`, the git blob ID of each other vendored file.\n",
        "[files]\n",
    ]
    lines += [f'"{path}" = "{blobs[path]}"\n' for path in FILES]
    return "".join(lines)


_PIN_LINE = re.compile(r'^(?:"([^"]+)"|([A-Za-z_]+))\s*=\s*"([^"]*)"\s*$')


def parse_pin(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Parse ``PIN.toml`` into ``(top-level keys, [files] table)``.

    Reads exactly the format :func:`render_pin` writes (Python 3.10 has no ``tomllib``).
    Anything else raises ``VendorError``.
    """
    top: dict[str, str] = {}
    files: dict[str, str] = {}
    table = top
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "[files]":
            table = files
            continue
        match = _PIN_LINE.match(stripped)
        if not match:
            raise VendorError(f"PIN.toml line {number} is not understood: {line!r}")
        key = match.group(1) or match.group(2)
        if key in table:
            raise VendorError(f"PIN.toml line {number}: duplicate key {key!r}")
        table[key] = match.group(3)
    return top, files


# --- the copy ----------------------------------------------------------------------------


def destination_files(spec: dict[str, bytes], pin_text: str) -> dict[str, bytes]:
    """Return everything the destination holds, as ``{path relative to dest: bytes}``."""
    out = dict(spec)
    out["PIN.toml"] = pin_text.encode("utf-8")
    out["README.md"] = README.format(repository=SPEC_REPOSITORY).encode("utf-8")
    out[".gitattributes"] = GITATTRIBUTES.encode("utf-8")
    return out


def _existing(dest: Path) -> list[str]:
    """Return the files already in ``dest`` (posix paths), ignoring ``__pycache__``."""
    if not dest.exists():
        return []
    found = []
    for path in sorted(dest.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink() or path.is_file():
            found.append(path.relative_to(dest).as_posix())
    return found


def write_copy(dest: Path, files: dict[str, bytes]) -> None:
    """Replace the managed content of ``dest`` with ``files``, writing bytes untouched.

    The folder must hold nothing but files this tool manages (a previous copy); otherwise
    ``VendorError`` names the strangers and nothing is deleted.
    """
    managed = set(files) | {"PIN.toml", "README.md", ".gitattributes"}
    existing = _existing(dest)
    strangers = [p for p in existing if p not in managed and not _in_tree(p)]
    if strangers:
        raise VendorError(
            f"{dest} holds files this tool does not manage: {', '.join(strangers)}; "
            "move them away first"
        )
    for relative in existing:
        (dest / relative).unlink()
    for relative, data in files.items():
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as handle:  # binary: no newline translation, ever
            handle.write(data)
    _prune_empty(dest)


def _in_tree(relative: str) -> bool:
    """Return whether ``relative`` is under the replaced ``fixtures/`` folder."""
    return relative.startswith(TREE + "/")


def _prune_empty(dest: Path) -> None:
    """Remove folders left empty by the replacement, deepest first."""
    for folder in sorted((p for p in dest.rglob("*") if p.is_dir()), reverse=True):
        if not any(folder.iterdir()):
            folder.rmdir()


def verify_written(dest: Path, repo: Path, commit: str) -> None:
    """Re-read what was written and confirm it hashes to ``git rev-parse``; else abort."""
    tree, blobs = pinned_hashes(repo, commit)
    got = {
        p: (dest / p).read_bytes() for p in _existing(dest) if _in_tree(p)
    }
    local_tree = tree_id_from_blobs({p[len(TREE) + 1 :]: d for p, d in got.items()})
    if local_tree != tree:
        raise VendorError(f"written fixtures/ hashes to {local_tree}, git says {tree}")
    for path, blob in blobs.items():
        local = git_blob_id((dest / path).read_bytes())
        if local != blob:
            raise VendorError(f"written {path} hashes to {local}, git says {blob}")


# --- --check -----------------------------------------------------------------------------


def check_copy(dest: Path, repo: Path) -> list[str]:
    """Return one line per difference between the copy, its PIN.toml and the Spec at the pin.

    An empty list means the copy is exactly what ``vendor.py`` writes for the pinned commit
    (``README.md`` is not compared: it is documentation, not Spec content).
    """
    problems: list[str] = []
    pin_path = dest / "PIN.toml"
    if not pin_path.is_file():
        return [f"PIN.toml: missing in {dest}"]
    top, pinned_files = parse_pin(pin_path.read_bytes().decode("utf-8"))
    commit = top.get("commit", "")
    if not FULL_SHA.fullmatch(commit):
        return [f"PIN.toml: commit {commit!r} is not a full 40-digit SHA"]
    if top.get("repository") != SPEC_REPOSITORY:
        problems.append(f"PIN.toml: repository is {top.get('repository')!r}")
    try:
        resolved = resolve_commit(repo, commit)
    except VendorError as error:
        return problems + [f"PIN.toml: the pinned commit is not in the Spec repository: {error}"]
    if resolved != commit:
        return problems + [f"PIN.toml: commit {commit} resolves to {resolved}"]

    spec = spec_files(repo, commit)
    tree, blobs = pinned_hashes(repo, commit)
    if top.get("fixtures_tree") != tree:
        problems.append(
            f"PIN.toml: fixtures_tree is {top.get('fixtures_tree')}, the Spec at the pin has {tree}"
        )
    if set(pinned_files) != set(FILES):
        problems.append(f"PIN.toml: [files] names {sorted(pinned_files)}, expected {sorted(FILES)}")
    for path, blob in blobs.items():
        if pinned_files.get(path) != blob:
            problems.append(f"PIN.toml: {path} is {pinned_files.get(path)}, the Spec has {blob}")

    existing = {p for p in _existing(dest)}
    for path, data in sorted(spec.items()):
        relative = path
        if relative not in existing:
            problems.append(f"{relative}: missing from the copy")
        elif (dest / relative).read_bytes() != data:
            problems.append(f"{relative}: differs from the Spec at {commit[:7]}")
    managed = set(spec) | {"PIN.toml", "README.md", ".gitattributes"}
    for relative in sorted(existing - managed):
        problems.append(f"{relative}: not in the Spec at {commit[:7]} (extra file)")
    attributes = dest / ".gitattributes"
    if not attributes.is_file():
        problems.append(".gitattributes: missing")
    elif attributes.read_bytes() != GITATTRIBUTES.encode("utf-8"):
        problems.append(".gitattributes: differs from what vendor.py writes")
    if not (dest / "README.md").is_file():
        problems.append("README.md: missing")
    return problems


# --- command line ------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit code."""
    parser = argparse.ArgumentParser(
        description="Copy the Spec's test material into a brick as a pinned, byte-exact copy."
    )
    parser.add_argument("--into", required=True, type=Path, help="root of the brick repository")
    parser.add_argument("--commit", help="Spec commit to copy (default HEAD); --check uses the pin")
    parser.add_argument("--dest", default=DEFAULT_DEST, help=f"folder in the brick ({DEFAULT_DEST})")
    parser.add_argument("--check", action="store_true", help="verify an existing copy, write nothing")
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parent.parent
    try:
        brick = args.into.resolve()
        if not brick.is_dir():
            raise VendorError(f"--into {args.into} is not a folder")
        dest = (brick / args.dest).resolve()
        if brick != dest and brick not in dest.parents:
            raise VendorError("--dest must stay inside the brick repository")
        if args.check:
            if args.commit:
                raise VendorError("--check reads the commit from PIN.toml; do not pass --commit")
            problems = check_copy(dest, repo)
            for problem in problems:
                print(problem)
            if problems:
                print(f"{len(problems)} difference(s): the copy is not the Spec at its pin.")
                return 1
            print(f"{dest}: identical to the Spec at its pinned commit.")
            return 0
        commit = resolve_commit(repo, args.commit or "HEAD")
        spec = spec_files(repo, commit)
        tree, blobs = pinned_hashes(repo, commit)
        if tree != tree_id_from_blobs(
            {p[len(TREE) + 1 :]: d for p, d in spec.items() if p.startswith(TREE + "/")}
        ):
            raise VendorError("fixtures/ read from git does not hash to its git tree ID")
        pin = render_pin(SPEC_REPOSITORY, commit, tree, blobs)
        write_copy(dest, destination_files(spec, pin))
        verify_written(dest, repo, commit)
        print(f"Vendored the Spec at {commit} into {dest} ({len(spec)} files).")
        return 0
    except VendorError as error:
        print(f"vendor.py: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
