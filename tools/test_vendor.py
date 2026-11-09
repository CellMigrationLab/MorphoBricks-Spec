"""Self-tests of ``tools/vendor.py``.

Run with ``python -I -m pytest tools`` or, without pytest, ``python -I -m unittest discover -s
tools``. Every test builds its own throwaway Spec repository with git; none reads the network.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import vendor  # noqa: E402

#: Awkward bytes a copy must keep exactly: CRLF, lone CR, no final newline, BOM, bad UTF-8.
AWKWARD = {
    "fixtures/valid/v01_a.toml": b"# Fixture v01\nkey = 1\n",
    "fixtures/valid/v02_crlf.toml": b"a = 1\r\nb = 2\r\n",
    "fixtures/valid/v03_cr.toml": b"a = 1\rb = 2\r",
    "fixtures/invalid/i01_bom.toml": b"\xef\xbb\xbfa = 1\n",
    "fixtures/invalid/i02_bad_utf8.toml": b"a = \xff\xfe\n",
    "fixtures/records/r1.jsonl": b'{"a": 1}\n{"a": 2}',
    "fixtures/README.md": b"# Fixtures\n",
    # Names that sort differently as a tree entry (folder = name + "/") than as plain names.
    "fixtures/a.b": b"y",
    "fixtures/a-b": b"z",
    "fixtures/a/f": b"w",
    "docs/experiment-v1.md": b"# Experiment v1\r\ntext\r\n",
    "tools/audit/refval.py": b"print('refval')\n",
    "tools/audit/refrecords.py": b"print('refrecords')",
}


def git(repo: Path, *args: str) -> str:
    """Run git in ``repo`` and return stdout as text."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=True, text=True
    )
    return done.stdout.strip()


def make_spec(root: Path, files: dict[str, bytes] | None = None) -> Path:
    """Create a Spec repository holding ``files`` (binary writes) with vendor.py in tools/."""
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.org")
    git(root, "config", "user.name", "T")
    for relative, data in (files or AWKWARD).items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    shutil.copy(TOOLS / "vendor.py", root / "tools" / "vendor.py")
    git(root, "add", "--", *(files or AWKWARD))
    git(root, "commit", "-q", "-m", "spec")
    # Set only after the commit (the blobs keep their CRLF): reading must not rewrite either.
    git(root, "config", "core.autocrlf", "true")
    return root


def run(spec: Path, *args: str) -> subprocess.CompletedProcess:
    """Run the Spec repository's own copy of vendor.py as a program."""
    return subprocess.run(
        [sys.executable, "-I", str(spec / "tools" / "vendor.py"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class VendorTest(unittest.TestCase):
    """Tests that need a Spec repository and a brick folder."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.spec = make_spec(base / "spec")
        self.brick = base / "brick"
        self.brick.mkdir()
        self.dest = self.brick / "tests" / "spec_fixtures"
        self.head = git(self.spec, "rev-parse", "HEAD")

    def vendor(self, *extra: str) -> subprocess.CompletedProcess:
        return run(self.spec, "--into", str(self.brick), *extra)

    def check(self) -> subprocess.CompletedProcess:
        return run(self.spec, "--into", str(self.brick), "--check")

    def test_copy_is_byte_exact_whatever_the_line_endings(self):
        done = self.vendor()
        self.assertEqual(done.returncode, 0, done.stderr)
        for relative, data in AWKWARD.items():
            self.assertEqual((self.dest / relative).read_bytes(), data, relative)

    def test_pin_toml_is_written_in_the_preprocessing_format(self):
        self.vendor()
        tree = git(self.spec, "rev-parse", "HEAD:fixtures")
        blobs = {p: git(self.spec, "rev-parse", f"HEAD:{p}") for p in vendor.FILES}
        expected = (
            "# The MorphoBricks-Spec commit these files are copied from (conformance plan section 1).\n"
            "# Updating the pin is a reviewed change: see README.md in this folder.\n"
            'repository = "https://github.com/CellMigrationLab/MorphoBricks-Spec"\n'
            f'commit = "{self.head}"\n'
            "\n"
            "# `git rev-parse <commit>:fixtures`, the git tree-object ID of the fixtures/ folder. The\n"
            "# vendored folder must hash to it, so one changed, added or missing byte fails a test.\n"
            f'fixtures_tree = "{tree}"\n'
            "\n"
            "# `git rev-parse <commit>:<path>`, the git blob ID of each other vendored file.\n"
            "[files]\n"
            f'"docs/experiment-v1.md" = "{blobs["docs/experiment-v1.md"]}"\n'
            f'"tools/audit/refval.py" = "{blobs["tools/audit/refval.py"]}"\n'
            f'"tools/audit/refrecords.py" = "{blobs["tools/audit/refrecords.py"]}"\n'
        )
        self.assertEqual((self.dest / "PIN.toml").read_bytes(), expected.encode())

    def test_readme_and_gitattributes_are_written(self):
        self.vendor()
        readme = (self.dest / "README.md").read_text(encoding="utf-8")
        self.assertIn("Do not edit", readme)
        self.assertIn("vendor.py", readme)
        self.assertEqual((self.dest / ".gitattributes").read_bytes(), vendor.GITATTRIBUTES.encode())
        self.assertTrue(vendor.GITATTRIBUTES.endswith("* -text\n"))

    def test_working_tree_state_never_leaks(self):
        (self.spec / "fixtures" / "valid" / "v01_a.toml").write_bytes(b"EDITED\n")
        (self.spec / "fixtures" / "valid" / "v99_untracked.toml").write_bytes(b"new\n")
        (self.spec / "docs" / "experiment-v1.md").unlink()
        self.assertEqual(self.vendor().returncode, 0)
        self.assertEqual((self.dest / "fixtures/valid/v01_a.toml").read_bytes(), AWKWARD["fixtures/valid/v01_a.toml"])
        self.assertFalse((self.dest / "fixtures/valid/v99_untracked.toml").exists())
        self.assertEqual((self.dest / "docs/experiment-v1.md").read_bytes(), AWKWARD["docs/experiment-v1.md"])

    def test_default_is_head_and_commit_selects_an_older_state(self):
        (self.spec / "fixtures" / "valid" / "v01_a.toml").write_bytes(b"second\n")
        git(self.spec, "commit", "-q", "-am", "second")
        self.assertEqual(self.vendor().returncode, 0)
        self.assertEqual((self.dest / "fixtures/valid/v01_a.toml").read_bytes(), b"second\n")
        self.assertEqual(self.vendor("--commit", self.head).returncode, 0)
        self.assertEqual((self.dest / "fixtures/valid/v01_a.toml").read_bytes(), AWKWARD["fixtures/valid/v01_a.toml"])
        self.assertIn(self.head, (self.dest / "PIN.toml").read_text(encoding="utf-8"))

    def test_a_short_sha_or_branch_is_pinned_as_the_full_sha(self):
        self.assertEqual(self.vendor("--commit", "main").returncode, 0)
        top, _ = vendor.parse_pin((self.dest / "PIN.toml").read_text(encoding="utf-8"))
        self.assertEqual(top["commit"], self.head)
        self.assertEqual(self.vendor("--commit", self.head[:7]).returncode, 0)
        top, _ = vendor.parse_pin((self.dest / "PIN.toml").read_text(encoding="utf-8"))
        self.assertEqual(top["commit"], self.head)

    def test_unknown_commit_is_a_usage_error_and_writes_nothing(self):
        done = self.vendor("--commit", "0" * 40)
        self.assertEqual(done.returncode, 2)
        self.assertFalse(self.dest.exists())

    def test_revendoring_replaces_the_previous_copy_and_drops_removed_files(self):
        self.vendor()
        git(self.spec, "rm", "-q", "fixtures/valid/v03_cr.toml")
        git(self.spec, "commit", "-q", "-m", "drop")
        self.assertEqual(self.vendor().returncode, 0)
        self.assertFalse((self.dest / "fixtures/valid/v03_cr.toml").exists())
        self.assertEqual(self.check().returncode, 0)

    def test_files_the_tool_does_not_manage_are_refused_and_kept(self):
        self.dest.mkdir(parents=True)
        (self.dest / "notes.txt").write_bytes(b"mine")
        done = self.vendor()
        self.assertEqual(done.returncode, 2)
        self.assertIn("notes.txt", done.stderr)
        self.assertEqual((self.dest / "notes.txt").read_bytes(), b"mine")

    def test_dest_must_stay_inside_the_brick(self):
        done = self.vendor("--dest", "../outside")
        self.assertEqual(done.returncode, 2)
        self.assertFalse((self.brick.parent / "outside").exists())

    def test_custom_dest(self):
        self.assertEqual(self.vendor("--dest", "vendor/spec").returncode, 0)
        self.assertTrue((self.brick / "vendor/spec/PIN.toml").is_file())
        done = run(self.spec, "--into", str(self.brick), "--dest", "vendor/spec", "--check")
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_executable_files_are_refused(self):
        git(self.spec, "update-index", "--chmod=+x", "tools/audit/refval.py")
        git(self.spec, "commit", "-q", "-m", "exec")
        done = self.vendor()
        self.assertEqual(done.returncode, 2)
        self.assertIn("refval.py", done.stderr)

    def test_a_missing_pinned_file_in_the_spec_is_refused(self):
        git(self.spec, "rm", "-q", "docs/experiment-v1.md")
        git(self.spec, "commit", "-q", "-m", "drop doc")
        done = self.vendor()
        self.assertEqual(done.returncode, 2)
        self.assertIn("experiment-v1.md", done.stderr)

    # --- --check ---

    def test_check_passes_on_a_fresh_copy_and_changes_nothing(self):
        self.vendor()
        before = {p: p.read_bytes() for p in self.dest.rglob("*") if p.is_file()}
        done = self.check()
        self.assertEqual(done.returncode, 0, done.stdout)
        after = {p: p.read_bytes() for p in self.dest.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_check_names_every_differing_file(self):
        self.vendor()
        (self.dest / "fixtures/valid/v01_a.toml").write_bytes(b"# Fixture v01\nkey = 2\n")
        (self.dest / "fixtures/valid/v02_crlf.toml").write_bytes(b"a = 1\nb = 2\n")  # CRLF lost
        (self.dest / "tools/audit/refval.py").unlink()
        (self.dest / "fixtures/valid/extra.toml").write_bytes(b"x")
        (self.dest / "docs/experiment-v1.md").write_bytes(b"# changed\n")
        done = self.check()
        self.assertEqual(done.returncode, 1)
        for name in (
            "fixtures/valid/v01_a.toml: differs",
            "fixtures/valid/v02_crlf.toml: differs",
            "tools/audit/refval.py: missing",
            "fixtures/valid/extra.toml: not in the Spec",
            "docs/experiment-v1.md: differs",
        ):
            self.assertIn(name, done.stdout)

    def test_check_fails_when_pin_toml_was_edited(self):
        self.vendor()
        pin = self.dest / "PIN.toml"
        text = pin.read_text(encoding="utf-8")
        tree = re.search(r'fixtures_tree = "([0-9a-f]{40})"', text).group(1)
        pin.write_bytes(text.replace(tree, "0" * 40).encode())
        done = self.check()
        self.assertEqual(done.returncode, 1)
        self.assertIn("fixtures_tree", done.stdout)

    def test_check_fails_when_the_pinned_commit_is_unknown(self):
        self.vendor()
        pin = self.dest / "PIN.toml"
        pin.write_bytes(pin.read_text(encoding="utf-8").replace(self.head, "1" * 40).encode())
        done = self.check()
        self.assertEqual(done.returncode, 1)
        self.assertIn("not in the Spec repository", done.stdout)

    def test_check_fails_when_pin_is_not_a_full_sha(self):
        self.vendor()
        pin = self.dest / "PIN.toml"
        pin.write_bytes(pin.read_text(encoding="utf-8").replace(self.head, "main").encode())
        done = self.check()
        self.assertEqual(done.returncode, 1)
        self.assertIn("40-digit", done.stdout)

    def test_check_fails_without_a_copy(self):
        done = self.check()
        self.assertEqual(done.returncode, 1)
        self.assertIn("PIN.toml: missing", done.stdout)

    def test_check_compares_with_the_pin_not_with_spec_head(self):
        self.vendor()
        (self.spec / "fixtures" / "valid" / "v01_a.toml").write_bytes(b"newer\n")
        git(self.spec, "commit", "-q", "-am", "newer")
        self.assertEqual(self.check().returncode, 0)

    def test_check_rejects_commit_argument(self):
        done = run(self.spec, "--into", str(self.brick), "--check", "--commit", self.head)
        self.assertEqual(done.returncode, 2)

    # --- the real Spec repository ---

    def test_the_real_spec_head_vendors_and_checks_clean(self):
        real = TOOLS.parent
        head = git(real, "rev-parse", "HEAD")
        brick = Path(self._tmp.name) / "real"
        brick.mkdir()
        done = subprocess.run(
            [sys.executable, "-I", str(real / "tools" / "vendor.py"), "--into", str(brick),
             "--commit", head],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        listed = git(real, "ls-tree", "-r", "--name-only", head, "--", "fixtures").splitlines()
        copied = [p.relative_to(brick / "tests/spec_fixtures").as_posix()
                  for p in (brick / "tests/spec_fixtures/fixtures").rglob("*") if p.is_file()]
        self.assertEqual(sorted(f"fixtures/{c[len('fixtures/'):]}" if c.startswith("fixtures/") else c for c in copied), sorted(listed))
        again = subprocess.run(
            [sys.executable, "-I", str(real / "tools" / "vendor.py"), "--into", str(brick), "--check"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(again.returncode, 0, again.stdout)


class PureTest(unittest.TestCase):
    """Tests of the hashing and parsing helpers."""

    def test_blob_id_is_gits(self):
        self.assertEqual(vendor.git_blob_id(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")
        self.assertEqual(vendor.git_blob_id(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

    def test_tree_id_matches_git_for_names_that_sort_around_a_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = make_spec(Path(tmp) / "s")
            files = {p[len("fixtures/"):]: d for p, d in AWKWARD.items() if p.startswith("fixtures/")}
            self.assertEqual(vendor.tree_id_from_blobs(files), git(spec, "rev-parse", "HEAD:fixtures"))

    def test_tree_id_known_answer_shared_with_the_brick_template(self):
        files = {"a.txt": b"hello\n", "b/c": b"x", "a.b": b"y", "a-b": b"z", "a/f": b"w"}
        self.assertEqual(vendor.tree_id_from_blobs(files), "fec6a54403e1c2a94724c1aab9f127c686f6dbb0")

    def test_parse_pin_round_trips_render_pin(self):
        blobs = {p: str(i) * 40 for i, p in enumerate(vendor.FILES)}
        text = vendor.render_pin(vendor.SPEC_REPOSITORY, "a" * 40, "b" * 40, blobs)
        top, files = vendor.parse_pin(text)
        self.assertEqual(top["commit"], "a" * 40)
        self.assertEqual(top["fixtures_tree"], "b" * 40)
        self.assertEqual(files, blobs)

    def test_parse_pin_refuses_what_it_does_not_understand(self):
        with self.assertRaises(vendor.VendorError):
            vendor.parse_pin("commit = main\n")
        with self.assertRaises(vendor.VendorError):
            vendor.parse_pin('commit = "a"\ncommit = "b"\n')

    def test_vendor_writes_only_in_binary_mode(self):
        source = (TOOLS / "vendor.py").read_text(encoding="utf-8")
        self.assertNotIn(".write_text(", source)
        self.assertNotIn("newline=", source)
        for call in re.findall(r"\bopen\(([^)]*)\)", source):
            self.assertIn('"wb"', call, call)
        self.assertNotIn("text=True", source)
        self.assertNotIn("universal_newlines", source)

    def test_no_third_party_imports(self):
        source = (TOOLS / "vendor.py").read_text(encoding="utf-8")
        imports = set(re.findall(r"^(?:from|import) (\w+)", source, re.M))
        self.assertLessEqual(imports, set(sys.stdlib_module_names) | {"__future__"})

    def test_hashing_helpers_work_on_a_python_without_newline_translation_surprises(self):
        # A file written by write_bytes keeps \r\n on every platform; the hash is of the bytes.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f"
            path.write_bytes(b"a\r\nb\r\n")
            self.assertEqual(vendor.git_blob_id(path.read_bytes()), vendor.git_blob_id(b"a\r\nb\r\n"))
            self.assertEqual(os.path.getsize(path), 6)


if __name__ == "__main__":
    unittest.main()
