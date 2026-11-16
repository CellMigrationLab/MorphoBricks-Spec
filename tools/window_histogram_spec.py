"""Reference rules of ADR 0004 EW11 (window histograms): canonical JSON, the conversion identity,
the derived-image histogram spec and the duplicate-report comparison.

Pure Python (no NumPy), one function per rule of ``docs/adr/0004-execution-windows.md``; the
normalization brick and MorphoFeature implement their own and reproduce the golden cases of
``tools/test_window_histogram_spec.py``. Nothing here reads pixels or imports a brick.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Mapping, Sequence
from typing import Any

CONVERSION_ID_VERSION = 1
SPEC_VERSION = 1
BIN_COUNT = 1024
WHITE_DEFAULT = (255.0, 255.0, 255.0)
WHITE_RESCALE = "clip(rint(I * 255 / white), 0, 255) as uint8, rint half to even"
"""``stain.WHITE_RESCALE`` of morphobricks-normalization b8aa65b (v0.6.1) and c6a9f9d (v0.7.0)."""
OD_DEFINITION = "-log10(max(I, 1) / white)"
CONVERSION_ID_KEYS = (
    "conversion_id_version", "preset", "preset_version", "method", "matrix", "target_component",
    "exclusion_component", "inverted", "colour_space", "white", "white_rescale", "stain_names",
    "stain_matrix", "residual_completed", "od_definition", "polarizer", "skimage_version",
)
WHITE_MODES = ("optional", "required", "none")
"""How a preset takes ``white``: in ``accepts`` (optional), in ``needs`` (required) or neither."""


# --- canonical JSON -------------------------------------------------------------------------------

def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"canonical JSON refuses a non-finite float: {value!r}")
        return 0.0 if value == 0.0 else float(value)  # -0.0 -> 0.0
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("canonical JSON refuses a mapping key that is not a str")
        return {key: _canonical_value(item) for key, item in value.items()}
    raise ValueError(f"canonical JSON refuses the type {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """The canonical text of EW11 (sorted keys, ``,`` and ``:``, ASCII, float ``repr``)."""
    return json.dumps(
        _canonical_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


# --- white (B1B) ----------------------------------------------------------------------------------

def _three_floats(white: object) -> tuple[float, float, float]:
    values = tuple(float(v) for v in white)  # type: ignore[union-attr]
    if len(values) != 3 or not all(math.isfinite(v) and 0.0 < v <= 255.0 for v in values):
        raise ValueError(f"white must be three finite values in (0, 255]; got {white!r}")
    return values  # type: ignore[return-value]


def resolved_white_from_options(mode: str, white: object) -> tuple[tuple[float, ...] | None, str | None]:
    """``(white, white_rescale)`` of the conversion identity, from the request's option."""
    if mode == "optional":
        return (WHITE_DEFAULT if white is None else _three_floats(white)), WHITE_RESCALE
    if mode == "required":
        if white is None:
            raise ValueError("this preset needs white")
        return _three_floats(white), None
    if mode == "none":
        if white is not None:
            raise ValueError("this preset does not use white")
        return None, None
    raise ValueError(f"unknown white mode {mode!r}")


def resolved_white_from_provenance(mode: str, provenance: Mapping[str, Any]) -> tuple[tuple[float, ...] | None, str | None]:
    """``(white, white_rescale)`` of the conversion identity, rebuilt from a ``ScalarResult.provenance``."""
    white = provenance.get("white")
    if mode == "optional":
        applied, rescale = provenance.get("white_applied"), provenance.get("white_rescale")
        if applied is False and white is None and rescale is None:
            return WHITE_DEFAULT, WHITE_RESCALE
        if applied is True and white is not None and rescale == WHITE_RESCALE:
            return _three_floats(white), WHITE_RESCALE
        raise ValueError("inconsistent white provenance (white, white_applied, white_rescale)")
    if mode in ("required", "none") and "white_applied" in provenance:
        raise ValueError("only a preset with an optional white records white_applied")
    if mode == "required":
        if white is None or provenance.get("white_rescale") is not None:
            raise ValueError("a custom_od provenance records its white and no rescale")
        return _three_floats(white), None
    if mode == "none":
        if white is not None or provenance.get("white_rescale") is not None:
            raise ValueError("this preset records no white")
        return None, None
    raise ValueError(f"unknown white mode {mode!r}")


def conversion_id(keys: Mapping[str, Any]) -> str:
    """SHA-256 of the canonical JSON of exactly :data:`CONVERSION_ID_KEYS`."""
    if set(keys) != set(CONVERSION_ID_KEYS):
        missing, extra = set(CONVERSION_ID_KEYS) - set(keys), set(keys) - set(CONVERSION_ID_KEYS)
        raise ValueError(f"conversion_id keys: missing {sorted(missing)}, extra {sorted(extra)}")
    if keys["conversion_id_version"] != CONVERSION_ID_VERSION:
        raise ValueError("conversion_id_version must be 1")
    return sha256_hex(dict(keys))


# --- float32 helpers (F1 rounding policy) ---------------------------------------------------------

def _f32_bits(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _f32_from_bits(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def _f32_nearest(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def _f32_next_up(f: float) -> float:
    if f == 0.0:
        return _f32_from_bits(1)
    bits = _f32_bits(f)
    return _f32_from_bits(bits + 1 if f > 0 else bits - 1)


def _f32_next_down(f: float) -> float:
    return -_f32_next_up(-f)


def f32_floor(x: float) -> float:
    """The largest float32 that is ``<= x``, as a Python float."""
    f = _f32_nearest(x)
    return _f32_next_down(f) if f > x else f


def f32_ceil(x: float) -> float:
    """The smallest float32 that is ``>= x``, as a Python float."""
    f = _f32_nearest(x)
    return _f32_next_up(f) if f < x else f


def f32_spacing(m: float) -> float:
    """``float(numpy.spacing(numpy.float32(m)))`` for a float32-representable ``m >= 0``."""
    if m < 0 or _f32_nearest(m) != m:
        raise ValueError("m must be a non-negative float32 value")
    return _f32_next_up(m) - m


# --- analytic bounds and the spec (F1) ------------------------------------------------------------

def custom_od_bounds(white: Sequence[float], stain_matrix: Sequence[Sequence[float]]) -> tuple[float, float]:
    """Exact-order float64 bounds of the target concentration of a ``custom_od`` preset.

    ``a`` is column 0 of ``inv(M)`` (``concentrations = OD @ inv(M)``, target first), by the
    adjugate: ``a_j = C_0j / det`` with the cofactors of row 0 and ``det = M00*C00 + M01*C01 +
    M02*C02``; per channel ``lo_j = -log10(255 / white_j)``, ``hi_j = -log10(1 / white_j)``; then
    ``sum_j min(a_j*lo_j, a_j*hi_j)`` and ``sum_j max(...)``, added left to right (j = 0, 1, 2).
    """
    m = [[float(v) for v in row] for row in stain_matrix]
    c0 = (
        m[1][1] * m[2][2] - m[1][2] * m[2][1],
        -(m[1][0] * m[2][2] - m[1][2] * m[2][0]),
        m[1][0] * m[2][1] - m[1][1] * m[2][0],
    )
    det = m[0][0] * c0[0] + m[0][1] * c0[1] + m[0][2] * c0[2]
    a = [c / det for c in c0]
    w = _three_floats(white)
    lo = [-math.log10(255.0 / w_j) for w_j in w]
    hi = [-math.log10(1.0 / w_j) for w_j in w]
    low = high = 0.0
    for j in range(3):
        low += min(a[j] * lo[j], a[j] * hi[j])
        high += max(a[j] * lo[j], a[j] * hi[j])
    return low, high


def output_histogram_spec(preset: str, preset_version: int, conversion: str, low: float, high: float) -> dict[str, Any]:
    """The ``OutputHistogramSpec`` of a bounded preset from its float64 analytic bounds."""
    analytic_min, analytic_max = f32_floor(low), f32_ceil(high)
    tolerance = 4.0 * f32_spacing(max(abs(analytic_min), abs(analytic_max)))
    return {
        "spec_version": SPEC_VERSION,
        "preset": preset,
        "preset_version": preset_version,
        "conversion_id": conversion,
        "bin_count": BIN_COUNT,
        "analytic_min": analytic_min,
        "analytic_max": analytic_max,
        "tolerance": tolerance,
        "binning_min": analytic_min - tolerance,
        "binning_max": analytic_max + tolerance,
    }


def spec_sha256(spec: Mapping[str, Any]) -> str:
    return sha256_hex(dict(spec))


# --- duplicate reports (B4) -----------------------------------------------------------------------

def comparable(value: Any) -> Any:
    """A field value as compared between two reports: floats by IEEE-754 binary64 bits.

    ``-0.0`` compares as ``0.0``; NaN is refused (no compared float may be NaN: it breaks the
    invariants and is a provider output error before any comparison); blank (``None``) equals
    only blank; ``counts`` is compared as its full sequence of integers.
    """
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return (type(value).__name__, value)
    if isinstance(value, float):
        if math.isnan(value):
            raise ValueError("a NaN in a compared field is a provider output error")
        return ("float", struct.pack(">d", 0.0 if value == 0.0 else value))
    if isinstance(value, (list, tuple)):
        return ("seq", tuple(comparable(item) for item in value))
    raise ValueError(f"uncomparable type {type(value).__name__}")


def first_difference(entries: Mapping[str, Mapping[str, Any]], fields: Sequence[str]) -> tuple[str, str, str] | None:
    """``(first_provider, other_provider, field)`` of the first difference, or ``None``.

    Providers in Python string order; each other provider is compared with the first, in that
    order; fields in ``fields`` order; ``counts`` is named ``counts[i]`` at its first differing bin.
    """
    providers = sorted(entries)
    base = entries[providers[0]]
    for other in providers[1:]:
        for field in fields:
            left, right = base[field], entries[other][field]
            if field == "counts" and left is not None and right is not None and len(left) == len(right):
                for i, (x, y) in enumerate(zip(left, right)):
                    if comparable(x) != comparable(y):
                        return providers[0], other, f"counts[{i}]"
                continue
            if comparable(left) != comparable(right):
                return providers[0], other, field
    return None
