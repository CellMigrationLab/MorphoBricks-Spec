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
RETIRED_CODES = {
    # First draft of PL1, dropped by the owner's answer of 11 November 2026 (no role applies).
    "A_MASK_PARENT_LABELS_NOT_SUPPORTED": ("docs/adr/0001-experiment-description-v1.md",),
}

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


class FastLayout(unittest.TestCase):
    """ADR 0006: the field tables of experiment-v1 and the audit validator agree."""

    @staticmethod
    def _table_keys(heading: str) -> tuple[str, ...]:
        text = _read("docs/experiment-v1.md")
        start = text.index(heading)
        table = text[text.index("| Key |", start):].split("\n\n", 1)[0]
        return tuple(re.match(r"\| `([a-z_]+)` \|", line)[1]
                     for line in table.splitlines()[2:])

    def test_channel_layout_fields_equal_validator(self) -> None:
        self.assertEqual(self._table_keys("### 4.3a `channel_layout`"), _refval().LAYOUT)

    def test_unit_fields_equal_validator(self) -> None:
        text = _read("docs/experiment-v1.md")
        anchor = "`repeats.<R>.members.<C>.technical_repeats.<technical repeat ID>`"
        table = text[text.index("| Key |", text.index(anchor)):].split("\n\n", 1)[0]
        keys = tuple(re.match(r"\| `([a-z_]+)` \|", line)[1] for line in table.splitlines()[2:])
        self.assertEqual(keys, _refval().UNIT)

    def test_new_codes_are_catalogued(self) -> None:
        text = _read("docs/experiment-v1.md")
        for code in ("E_FAST_LAYOUT_MISMATCH", "E_FAST_MARKER_WITHOUT_LAYOUT"):
            self.assertIn(f"| 5 | `{code}` |", _section(text, "## 6."))
        self.assertIn("| `R_FAST_LAYOUT_CONTRADICTION` |", _section(text, "## 8."))


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
