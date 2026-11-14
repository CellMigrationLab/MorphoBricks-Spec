"""Cases of ADR 0004 (proposed): typed coordinate conversions and the window record.

Run with ``python -I -m pytest tools``. The cases are the normative examples; a brick that implements
the conversions reproduces them.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "execution_frames", Path(__file__).resolve().parent / "execution_frames.py"
)
frames = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(frames)


class Conversions(unittest.TestCase):
    def test_the_adr_examples(self) -> None:
        # Patch [0, 256) of a whole source: vertices 0 and 256 in full_res; -0.5 and 255.5 for the bridge.
        self.assertEqual(frames.edge_to_full_res(0, 0, 1), 0)
        self.assertEqual(frames.edge_to_full_res(256, 0, 1), 256)
        self.assertEqual(frames.edge_to_labconstrictor(0), -0.5)
        self.assertEqual(frames.edge_to_labconstrictor(256), 255.5)
        # A centroid at index 12: 12.5 in full_res, 12 for the bridge.
        self.assertEqual(frames.index_to_full_res(12, 0, 1), 12.5)
        self.assertEqual(frames.index_to_labconstrictor(12), 12)

    def test_the_bridge_places_both_types_where_full_res_says(self) -> None:
        for offset in (0, 1000):
            for downsample in (1, 2, 4):
                for value in (0, 7, 256):
                    self.assertEqual(
                        frames.labconstrictor_to_full_res(frames.edge_to_labconstrictor(value), offset, downsample),
                        frames.edge_to_full_res(value, offset, downsample),
                    )
                    self.assertEqual(
                        frames.labconstrictor_to_full_res(frames.index_to_labconstrictor(value), offset, downsample),
                        frames.index_to_full_res(value, offset, downsample),
                    )

    def test_a_crop_offset_and_a_downsample(self) -> None:
        # A viewer crop at full-resolution x0 = 1000, exported at downsample 2.
        self.assertEqual(frames.edge_to_full_res(10, 1000, 2), 1020)
        self.assertEqual(frames.index_to_full_res(10, 1000, 2), 1021)

    def test_local_to_plane(self) -> None:
        self.assertEqual(frames.local_to_plane(192, 64), 256)
        with self.assertRaises(TypeError):
            frames.local_to_plane(1.5, 0)


class WindowRecord(unittest.TestCase):
    def test_an_interior_patch_keeps_its_whole_margin(self) -> None:
        record = frames.context_bounds((256, 512, 256, 512), (67, 67), (1024, 1024))
        self.assertEqual(record["context_bounds"], (189, 579, 189, 579))
        self.assertEqual(record["origin"], (189, 189))
        self.assertEqual(record["margin_requested"], (67, 67, 67, 67))
        self.assertEqual(record["margin_clipped"], (67, 67, 67, 67))
        self.assertEqual(record["local_interior"], (67, 323, 67, 323))

    def test_the_plane_edge_clips_and_records(self) -> None:
        record = frames.context_bounds((0, 256, 900, 1000), (67, 30), (300, 1000))
        self.assertEqual(record["context_bounds"], (0, 300, 870, 1000))
        self.assertEqual(record["margin_clipped"], (0, 44, 30, 0))
        self.assertEqual(record["local_interior"], (0, 256, 30, 130))

    def test_zero_margin_is_the_patch(self) -> None:
        record = frames.context_bounds((10, 20, 30, 40), (0, 0), (100, 100))
        self.assertEqual(record["context_bounds"], (10, 20, 30, 40))
        self.assertEqual(record["local_interior"], (0, 10, 0, 10))

    def test_refusals(self) -> None:
        with self.assertRaises(ValueError):
            frames.context_bounds((0, 10, 0, 10), (-1, 0), (100, 100))
        with self.assertRaises(TypeError):
            frames.context_bounds((0, 10, 0, 10), (1.5, 0), (100, 100))
        with self.assertRaises(TypeError):
            frames.context_bounds((0, 10, 0, 10), (True, 0), (100, 100))
        with self.assertRaises(ValueError):
            frames.context_bounds((0, 0, 0, 10), (1, 1), (100, 100))
        with self.assertRaises(ValueError):
            frames.context_bounds((0, 10, 0, 110), (1, 1), (100, 100))


if __name__ == "__main__":
    unittest.main()
