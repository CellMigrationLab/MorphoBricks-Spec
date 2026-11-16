"""Golden cases of ADR 0004 EW11: canonical JSON, conversion identity, histogram spec, duplicates.

Run with ``python -I -m pytest tools``. The normalization brick's ``canonical_json``,
``conversion_id`` and ``output_histogram_spec`` and MorphoFeature's duplicate rule reproduce these
values exactly (the hashes and every float bit for bit). The stain-matrix rows are inputs here: they
are what ``optical_density.stain_matrix`` returns at morphobricks-normalization c6a9f9d (v0.7.0)
for the vectors named in each case, and the brick's own test checks that.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "window_histogram_spec", Path(__file__).resolve().parent / "window_histogram_spec.py"
)
w = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(w)

HE_DEFAULT_ROWS = (  # he_custom default vectors (HE_DEFAULT_VECTORS), residual completed
    (0.0701017212973667, 0.9914386297770432, 0.1101598477530048),
    (0.6511078257574492, 0.7011930431234068, 0.29049426072255424),
    (0.3321168641376976, 0.08093471415445082, -0.9397595227504105),
)
HE_USER_ROWS = (  # {"eosin": (0.10, 0.95, 0.20), "hematoxylin": (0.60, 0.75, 0.30)}, residual completed
    (0.102463103915712, 0.973399487199264, 0.204926207831424),
    (0.5962847939999439, 0.7453559924999299, 0.29814239699997197),
    (0.259160527674408, 0.17277368511627203, -0.950255268139496),
)
PSR_USER_ROWS = (  # {"psr": (0.15, 0.85, 0.50), "counterstain": (0.70, 0.40, 0.55), "residual": (0.30, 0.20, 0.90)}
    (0.15037641213512565, 0.8521330020990454, 0.5012547071170855),
    (0.7172417274099839, 0.409852415662848, 0.563547071536416),
    (0.309426373877638, 0.20628424925175867, 0.928279121632914),
)


def _keys(**given: object) -> dict[str, object]:
    keys: dict[str, object] = {
        "conversion_id_version": 1, "matrix": None, "target_component": None,
        "exclusion_component": None, "inverted": False, "colour_space": "srgb", "white": None,
        "white_rescale": None, "stain_names": None, "stain_matrix": None,
        "residual_completed": None, "od_definition": None, "polarizer": None,
        "skimage_version": None,
    }
    keys.update(given)
    return keys


def _luminance_keys(white_option: object) -> dict[str, object]:
    white, rescale = w.resolved_white_from_options("optional", white_option)
    return _keys(
        preset="luminance_inverted", preset_version=1, method="luminance", inverted=True,
        white=white, white_rescale=rescale, skimage_version="0.26.0",
    )


def _custom_keys(preset: str, white: tuple[float, ...], names: list[str], rows: tuple, completed: bool) -> dict[str, object]:
    resolved, rescale = w.resolved_white_from_options("required", white)
    return _keys(
        preset=preset, preset_version=1, method="custom_od", white=resolved, white_rescale=rescale,
        stain_names=names, stain_matrix=rows, residual_completed=completed,
        od_definition=w.OD_DEFINITION,
    )


# (case, keys, float64 analytic bounds or None for the stated constants, expected)
GOLDEN = {
    "G1 luminance_inverted, white unset": (
        _luminance_keys(None), (0.0, 1.0),
        {
            "conversion_id": "ce13f97f2d55b509f3d0ca2e435dde305c41f7a34a9e41045084f6367cc39ac7",
            "analytic_min": 0.0, "analytic_max": 1.0, "tolerance": 4.76837158203125e-07,
            "binning_min": -4.76837158203125e-07, "binning_max": 1.0000004768371582,
            "spec_sha256": "a25dd0952d26d8f8d92a8a7026146726264decbe2997fd4934c8009bff457f59",
        },
    ),
    "G2 luminance_inverted, white (255, 255, 255)": (
        _luminance_keys((255, 255, 255)), (0.0, 1.0),
        {
            "conversion_id": "ce13f97f2d55b509f3d0ca2e435dde305c41f7a34a9e41045084f6367cc39ac7",
            "analytic_min": 0.0, "analytic_max": 1.0, "tolerance": 4.76837158203125e-07,
            "binning_min": -4.76837158203125e-07, "binning_max": 1.0000004768371582,
            "spec_sha256": "a25dd0952d26d8f8d92a8a7026146726264decbe2997fd4934c8009bff457f59",
        },
    ),
    "G3 he_custom, default vectors": (
        _custom_keys("he_custom", (230.0, 225.0, 240.0), ["eosin", "hematoxylin", "residual"], HE_DEFAULT_ROWS, True),
        None,
        {
            "float64_bounds": (-3.2763034686588015, 2.6812241264838463),
            "conversion_id": "d29672aa039c56940e6d2cbce6b19e524f17e81d6dc554a0d31b964ce38b9937",
            "analytic_min": -3.27630352973938, "analytic_max": 2.6812243461608887,
            "tolerance": 9.5367431640625e-07,
            "binning_min": -3.2763044834136963, "binning_max": 2.681225299835205,
            "spec_sha256": "5d4f141a41cba08bd6fca1c13659a914d38550cd75f71ada7a9272196ebf2b0b",
        },
    ),
    "G4 he_custom, user vectors": (
        _custom_keys("he_custom", (230.0, 225.0, 240.0), ["eosin", "hematoxylin", "residual"], HE_USER_ROWS, True),
        None,
        {
            "float64_bounds": (-3.853378432531873, 2.9239346015209104),
            "conversion_id": "05354c067033bc5da7e1cbcd33f476dba3632bf57f22e1cbb4001ca42513234f",
            "analytic_min": -3.8533785343170166, "analytic_max": 2.9239346981048584,
            "tolerance": 9.5367431640625e-07,
            "binning_min": -3.853379487991333, "binning_max": 2.923935651779175,
            "spec_sha256": "9d87fcd655d5e9dd3e72b460ae24f6293f878da5399ce64f4e62cc9d5337ffce",
        },
    ),
    "G5 psr_brightfield, user vectors with residual": (
        _custom_keys("psr_brightfield", (250.0, 248.0, 252.0), ["psr", "counterstain", "residual"], PSR_USER_ROWS, False),
        None,
        {
            "float64_bounds": (-1.8734702623295671, 3.2002305964865143),
            "conversion_id": "acd54b73791cd9bd5158134e463a92f6c94c42d34d0ee347656bb47f500dd784",
            "analytic_min": -1.8734703063964844, "analytic_max": 3.200230598449707,
            "tolerance": 9.5367431640625e-07,
            "binning_min": -1.8734712600708008, "binning_max": 3.2002315521240234,
            "spec_sha256": "3c3fddfc661b16387e61f513b4b241d720da5e6af21c596b6a34fb3edd25240b",
        },
    ),
}


class OutputHistogramSpecGoldens(unittest.TestCase):
    def test_goldens(self) -> None:
        for case, (keys, bounds, expected) in GOLDEN.items():
            with self.subTest(case):
                conversion = w.conversion_id(keys)
                self.assertEqual(conversion, expected["conversion_id"])
                if bounds is None:
                    bounds = w.custom_od_bounds(keys["white"], keys["stain_matrix"])
                    self.assertEqual(bounds, expected["float64_bounds"])
                spec = w.output_histogram_spec(keys["preset"], 1, conversion, *bounds)
                for field in ("analytic_min", "analytic_max", "tolerance", "binning_min", "binning_max"):
                    self.assertEqual(spec[field].hex(), float(expected[field]).hex(), field)
                self.assertEqual(spec["bin_count"], 1024)
                self.assertEqual(w.spec_sha256(spec), expected["spec_sha256"])

    def test_bounds_are_float32_and_outward(self) -> None:
        low, high = GOLDEN["G3 he_custom, default vectors"][2]["float64_bounds"]
        self.assertLessEqual(w.f32_floor(low), low)
        self.assertGreaterEqual(w.f32_ceil(high), high)
        self.assertEqual(w.f32_floor(1.0), 1.0)
        self.assertEqual(w.f32_spacing(1.0), 2.0**-23)


class WhiteIdentity(unittest.TestCase):
    def test_unset_and_default_white_share_the_id(self) -> None:
        self.assertEqual(w.conversion_id(_luminance_keys(None)), w.conversion_id(_luminance_keys((255.0, 255.0, 255.0))))
        self.assertNotEqual(w.conversion_id(_luminance_keys(None)), w.conversion_id(_luminance_keys((250.0, 255.0, 255.0))))

    def test_rebuilt_from_provenance(self) -> None:
        unset = {"white": None, "white_applied": False, "white_rescale": None}
        explicit = {"white": (255.0, 255.0, 255.0), "white_applied": True, "white_rescale": w.WHITE_RESCALE}
        self.assertEqual(w.resolved_white_from_provenance("optional", unset), (w.WHITE_DEFAULT, w.WHITE_RESCALE))
        self.assertEqual(w.resolved_white_from_provenance("optional", explicit), (w.WHITE_DEFAULT, w.WHITE_RESCALE))
        for broken in (
            {"white": None, "white_applied": True, "white_rescale": w.WHITE_RESCALE},
            {"white": (255.0, 255.0, 255.0), "white_applied": True, "white_rescale": "other"},
            {"white": None, "white_applied": False, "white_rescale": w.WHITE_RESCALE},
        ):
            with self.assertRaises(ValueError):
                w.resolved_white_from_provenance("optional", broken)
        # custom_od records its white and no rescale key; fixed_deconvolution records neither.
        self.assertEqual(w.resolved_white_from_provenance("required", {"white": (230.0, 225.0, 240.0)}), ((230.0, 225.0, 240.0), None))
        self.assertEqual(w.resolved_white_from_provenance("none", {}), (None, None))

    def test_white_scope(self) -> None:
        with self.assertRaises(ValueError):
            w.resolved_white_from_options("required", None)  # custom_od: no default white
        with self.assertRaises(ValueError):
            w.resolved_white_from_options("none", (255, 255, 255))  # fixed_deconvolution: refused


class CanonicalJson(unittest.TestCase):
    def test_rules(self) -> None:
        self.assertEqual(w.canonical_json({"b": 1, "a": [1.0, -0.0, None, True]}), '{"a":[1.0,0.0,null,true],"b":1}')
        with self.assertRaises(ValueError):
            w.canonical_json(float("nan"))
        with self.assertRaises(ValueError):
            w.canonical_json({1: 2})


class DuplicateComparison(unittest.TestCase):
    FIELDS = ("pixel_min", "underflow_mean", "counts", "zero_count")

    def test_bits_zero_and_nan(self) -> None:
        base = {"pixel_min": 0.0, "underflow_mean": 0.1, "counts": [3, 0, 2], "zero_count": None}
        self.assertIsNone(w.first_difference({"a": base, "b": dict(base, pixel_min=-0.0)}, self.FIELDS))
        nearby = dict(base, underflow_mean=0.1 + 2.0**-56)  # the next float64 above 0.1
        self.assertNotEqual(nearby["underflow_mean"], 0.1)
        self.assertEqual(w.first_difference({"b": nearby, "a": base}, self.FIELDS), ("a", "b", "underflow_mean"))
        self.assertEqual(w.first_difference({"a": base, "b": dict(base, counts=[3, 1, 1])}, self.FIELDS), ("a", "b", "counts[1]"))
        self.assertEqual(w.first_difference({"a": base, "b": dict(base, zero_count=0)}, self.FIELDS), ("a", "b", "zero_count"))
        with self.assertRaises(ValueError):
            w.first_difference({"a": base, "b": dict(base, underflow_mean=float("nan"))}, self.FIELDS)

    def test_order(self) -> None:
        base = {"pixel_min": 1.0, "underflow_mean": 0.0, "counts": [1], "zero_count": 0}
        entries = {"c": dict(base, pixel_min=2.0), "a": base, "b": dict(base, zero_count=5)}
        self.assertEqual(w.first_difference(entries, self.FIELDS), ("a", "b", "zero_count"))


if __name__ == "__main__":
    unittest.main()
