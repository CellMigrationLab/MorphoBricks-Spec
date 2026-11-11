"""Consistency checks between the normative text, the fixtures and the audit validator.

Run with ``python -I -m pytest tools`` or ``python -I -m unittest discover -s tools``. Each check
reads files of this repository only.
"""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs" / "experiment-v1.md"

#: Fixture numbers that were retired and must never be reused (their file moved elsewhere).
RETIRED_FIXTURES = {
    "invalid": ("i111",),  # owner decision PL1: now valid/v38
    "records": ("rv07", "rv08"),  # owner decisions RF1-RF6: now ri25, ri26
}

#: `A_*` codes that were proposed or removed and may be named only as history, in these files.
RETIRED_CODES: dict[str, tuple[str, ...]] = {}

#: Resolver-contract codes (ADR 0002), not experiment-v1 section 8 codes.
RESOLVER_CODES = ("A_VOLUME_NOT_SUPPORTED", "A_DESCRIPTION_REQUIRED")

A_CODE = re.compile(r"\bA_[A-Z_]*[A-Z]\b")


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end < 0 else text[start:end]


def _refval():
    spec = importlib.util.spec_from_file_location("refval", ROOT / "tools" / "audit" / "refval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normative_files() -> list[Path]:
    files = [ROOT / "README.md", ROOT / "fixtures" / "README.md", ROOT / "tools" / "audit" / "README.md"]
    files += sorted((ROOT / "docs").glob("*.md")) + sorted((ROOT / "docs" / "adr").glob("*.md"))
    files += sorted((ROOT / "fixtures").glob("*/*.toml"))
    return files


class RepresentationEnum(unittest.TestCase):
    def test_spec_table_equals_validator(self) -> None:
        row = next(line for line in _read("docs/experiment-v1.md").splitlines()
                   if line.startswith("| `representation` |"))
        rule = row.split("|")[4]
        values = re.findall(r"`([a-z_]+)`", rule.split("(`E_ENUM`")[0])
        self.assertEqual(tuple(values), _refval().REPRESENTATIONS)

    def test_every_value_has_a_valid_fixture(self) -> None:
        used = set()
        for f in (ROOT / "fixtures" / "valid").glob("*.toml"):
            used |= set(re.findall(r'^representation = "([^"]+)"', f.read_bytes().decode("utf-8", "replace"), re.M))
        self.assertEqual(used, set(_refval().REPRESENTATIONS))


class AnalysisCodes(unittest.TestCase):
    def test_every_a_code_is_defined(self) -> None:
        defined = set(A_CODE.findall(_section(SPEC.read_text(encoding="utf-8"), "## 8.")))
        defined |= set(RESOLVER_CODES)
        for retired in RETIRED_CODES:
            self.assertNotIn(retired, defined, f"{retired} is retired but defined in section 8")
        for path in _normative_files():
            rel = path.relative_to(ROOT).as_posix()
            for code in sorted(set(A_CODE.findall(path.read_bytes().decode("utf-8", "replace")))):
                if code in RETIRED_CODES:
                    self.assertIn(rel, RETIRED_CODES[code], f"{rel} names the retired {code}")
                else:
                    self.assertIn(code, defined, f"{rel} names {code}, defined nowhere")


class FixtureCatalogue(unittest.TestCase):
    def _count(self, sub: str, suffix: str) -> int:
        return len(list((ROOT / "fixtures" / sub).glob(f"*{suffix}")))

    def test_retired_numbers_not_reused(self) -> None:
        for sub, numbers in RETIRED_FIXTURES.items():
            names = [p.name for p in (ROOT / "fixtures" / sub).iterdir()]
            for number in numbers:
                self.assertFalse([n for n in names if n.startswith(number + "_")],
                                 f"retired fixture number {number} reused in {sub}/")

    def test_counts_stated_everywhere(self) -> None:
        valid = self._count("valid", ".toml")
        invalid = self._count("invalid", ".toml")
        transitions = self._count("transitions", ".toml")
        records = self._count("records", ".jsonl")
        catalogue = _read("fixtures/README.md")
        self.assertIn(f"## Valid fixtures ({valid})", catalogue)
        self.assertIn(f"## Invalid fixtures ({invalid})", catalogue)
        self.assertIn(f"## Transition fixtures ({transitions})", catalogue)
        self.assertIn(f"## Records fixtures ({records})", catalogue)
        flat = " ".join(catalogue.split())
        self.assertIn(f"accepts {valid} of {valid} valid files", flat)
        self.assertIn(f"refuses {invalid} of {invalid} invalid files", flat)
        self.assertIn(f"for {transitions} of {transitions} transitions", flat)
        readme = " ".join(_read("README.md").split())
        self.assertIn(f"{valid + invalid + transitions} fixtures", readme)
        self.assertIn(f"holds {valid} valid files, {invalid} invalid ones", readme)
        self.assertIn(f"{transitions} transitions", readme)
        self.assertIn(f"# {valid}/{valid}, {invalid}/{invalid}, {transitions}/{transitions},",
                      _read("tools/audit/README.md"))


if __name__ == "__main__":
    unittest.main()
