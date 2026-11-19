"""Golden cases of ADR 0002 AR12 (resolver contract version 4): the recorded FOV subset.

Run with ``python -I -m pytest tools``. morphobricks-preprocessing's ``Request.fov_subset`` check,
its ``A_FOV_NOT_IN_RUN`` refusal and ``Provenance.fov_scope`` reproduce these values exactly (the
record key for key, the message and the digests character for character). The run is the
MorphoFeature G4 tree ``s07_missing_optional`` reduced to its keys: PAXILLIN in every image of
R001 and in no image of R002. The keys are those of the tree that MorphoFeature's
``adversarial/generate.py`` writes at commit ``952c4be`` (draft PR #240; ``img{index}.tif``, two
images per unit, units without a technical-repeat folder), read with ``RunInputs.fovs()`` of
preprocessing v0.7.0 on 19 November 2026. If #240 changes the tree's keys, this run, its digests
and ADR 0002's example record change with it in one Spec PR.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "fov_scope_spec", Path(__file__).resolve().parent / "fov_scope_spec.py"
)
f = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(f)

RUN = tuple(
    ((condition, source, "single", f"img{i}"), group)
    for group, source in (("R001", "rep1"), ("R002", "rep2"))
    for condition in ("CTRL", "DrugA")
    for i in (0, 1)
)
R001 = tuple(key for key, group in RUN if group == "R001")
R002 = tuple(key for key, group in RUN if group == "R002")

DIGEST_ALL = "f02bffc83abcc361b71256099ca8836211e4254f86d643839a4c00de52d3d011"
DIGEST_R001 = "df6472408c96f35ba7fc4ebe0aff8925a5901716099470376a5cc3100635c69d"
DIGEST_EVERY_KEY_EXPLICIT = "f0ddfd701846c4526aae4341b759d840a0aa78ca383f80c4b6689fc6231b6815"


class Record(unittest.TestCase):
    def test_absent_subset_is_all_and_recorded_explicitly(self) -> None:
        record = f.fov_scope(RUN, None)
        self.assertEqual(tuple(record), f.RECORD_KEYS)
        self.assertEqual(record["fov_subset"], "all")
        self.assertEqual((record["selected"], record["run_images"]), (8, 8))
        self.assertEqual(record["fovs"], sorted(list(k) for k, _ in RUN))
        self.assertEqual(record["excluded"], [])
        self.assertEqual(
            record["repeats"],
            [
                {"repeat_group": "R001", "selected": 4, "run_images": 4},
                {"repeat_group": "R002", "selected": 4, "run_images": 4},
            ],
        )
        self.assertEqual(record["selected_biological_repeats"], 2)
        self.assertEqual(record["scope_digest"], DIGEST_ALL)

    def test_explicit_subset_records_included_excluded_and_biological_n(self) -> None:
        record = f.fov_scope(RUN, R001)
        self.assertEqual(record["fov_subset"], "explicit")
        self.assertEqual((record["selected"], record["run_images"]), (4, 8))
        self.assertEqual(record["fovs"], [list(k) for k in sorted(R001)])
        self.assertEqual(record["excluded"], [list(k) for k in sorted(R002)])
        self.assertEqual(
            record["repeats"],
            [
                {"repeat_group": "R001", "selected": 4, "run_images": 4},
                {"repeat_group": "R002", "selected": 0, "run_images": 4},
            ],
        )
        self.assertEqual(record["selected_biological_repeats"], 1)
        self.assertEqual(record["scope_digest"], DIGEST_R001)

    def test_selected_repeats_is_not_a_comparison_n(self) -> None:
        """One image of each condition in R001 and only CTRL in R002: both repeats have a chosen
        image (2), but a CTRL-DrugA comparison has one repeat with both conditions (ADR 0002 AR12,
        "Biological N"); the record never states that N."""
        subset = (("CTRL", "rep1", "single", "img0"), ("DrugA", "rep1", "single", "img0"),
                  ("CTRL", "rep2", "single", "img0"))
        record = f.fov_scope(RUN, subset)
        self.assertEqual(record["selected_biological_repeats"], 2)
        self.assertNotIn("biological_n", record)

    def test_digest_is_the_canonical_json_hash_and_ignores_request_order(self) -> None:
        text = (
            '{"fov_subset":"explicit","fovs":[["CTRL","rep1","single","img0"],'
            '["CTRL","rep1","single","img1"],["DrugA","rep1","single","img0"],'
            '["DrugA","rep1","single","img1"]]}'
        )
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), DIGEST_R001)
        self.assertEqual(f.fov_scope(RUN, tuple(reversed(R001)))["scope_digest"], DIGEST_R001)

    def test_every_key_named_is_not_the_same_identity_as_all(self) -> None:
        record = f.fov_scope(RUN, tuple(k for k, _ in RUN))
        self.assertEqual(record["fovs"], f.fov_scope(RUN, None)["fovs"])
        self.assertEqual(record["scope_digest"], DIGEST_EVERY_KEY_EXPLICIT)
        self.assertNotEqual(DIGEST_EVERY_KEY_EXPLICIT, DIGEST_ALL)


class Malformed(unittest.TestCase):
    def test_shapes_refused_as_value_error(self) -> None:
        for subset in (
            (),  # empty
            (0, 1),  # positions
            ("CTRL/rep1/single/img0.tif",),  # a path
            [R001[0]],  # a list
            (R001[0][:3],),  # a key of three parts
            ((1, "rep1", "single", "img0"),),  # a part that is not str
            (R001[0], R001[0]),  # twice
        ):
            with self.subTest(subset=subset), self.assertRaises(ValueError):
                f.fov_scope(RUN, subset)

    def test_empty_message(self) -> None:
        with self.assertRaises(ValueError) as raised:
            f.check_subset(())
        self.assertEqual(
            str(raised.exception),
            "fov_subset is empty; name at least one FOV by its key, or leave it unset (None) to "
            "use every image of the run",
        )


class NotInRun(unittest.TestCase):
    def test_unknown_key_refused_with_code_and_fix(self) -> None:
        wrong_case = ("ctrl", "rep1", "single", "img0")  # never case-folded
        with self.assertRaises(f.FovNotInRun) as raised:
            f.fov_scope(RUN, (R001[0], wrong_case))
        self.assertEqual(raised.exception.code, "A_FOV_NOT_IN_RUN")
        self.assertEqual(raised.exception.unknown, (wrong_case,))
        self.assertEqual(
            str(raised.exception),
            "The requested FOV subset names 1 FOV(s) that this run does not have:\n"
            "  - ('ctrl', 'rep1', 'single', 'img0')\n"
            "Nothing was selected or read. Name each FOV by its key (condition, "
            "biological_repeat, technical_repeat, position_id) exactly as RunInputs.fovs() lists "
            "it, or leave fov_subset unset to use all 8 images of the run (A_FOV_NOT_IN_RUN).",
        )

    def test_more_than_ten_unknown_are_counted(self) -> None:
        unknown = tuple(("CTRL", "rep9", "single", f"img{i:02d}") for i in range(12))
        message = f.refusal_message(unknown, 8)
        self.assertEqual(
            message,
            "The requested FOV subset names 12 FOV(s) that this run does not have:\n"
            + "".join(f"  - ('CTRL', 'rep9', 'single', 'img{i:02d}')\n" for i in range(10))
            + "  ... and 2 more\n"
            "Nothing was selected or read. Name each FOV by its key (condition, "
            "biological_repeat, technical_repeat, position_id) exactly as RunInputs.fovs() lists "
            "it, or leave fov_subset unset to use all 8 images of the run (A_FOV_NOT_IN_RUN).",
        )


class AdrText(unittest.TestCase):
    """The normative text of ADR 0002 AR12 states what the reference rules compute."""

    ADR = (Path(__file__).resolve().parent.parent / "docs" / "adr" / "0002-shared-request-resolver.md")

    def setUp(self) -> None:
        text = self.ADR.read_text(encoding="utf-8")
        start = text.index("### Resolver contract version 4")
        self.section = text[start : text.index("\n### ", start + 1)]

    def test_version_and_code(self) -> None:
        self.assertIn(f"`RESOLVER_VERSION = {f.RESOLVER_VERSION}`", self.section)
        self.assertIn(f.CODE, self.section)

    def test_record_keys_in_order(self) -> None:
        rows = re.findall(r"^\| `([a-z_]+)` \|", self.section, re.M)
        self.assertEqual(tuple(rows), f.RECORD_KEYS)

    def test_example_record_is_the_golden(self) -> None:
        example = re.search(r"```json\n(.*?)\n```", self.section, re.S).group(1)
        self.assertEqual(json.loads(example), f.fov_scope(RUN, R001))

    def test_messages_are_stated_verbatim(self) -> None:
        flat = " ".join(self.section.split())
        tail = f.refusal_message((("x", "x", "x", "x"),), 8).split("\n")[-1]
        self.assertIn(" ".join(tail.replace("all 8 images", "all {n} images").split()), flat)
        with self.assertRaises(ValueError) as raised:
            f.check_subset(())
        self.assertIn(str(raised.exception), flat)


if __name__ == "__main__":
    unittest.main()
