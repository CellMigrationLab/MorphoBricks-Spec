"""Reference conversions of ADR 0004 (execution windows, typed coordinates), proposed.

Pure functions, one per formula of ``docs/adr/0004-execution-windows.md``; bricks implement their own
and test them against ``tools/test_execution_frames.py``'s cases. Every coordinate is per axis; a
rectangle is ``(y0, y1, x0, x1)``, half-open ``pixel_edge`` in the plane's frame.
"""

from __future__ import annotations

from numbers import Integral, Real


def _integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer, got {value!r}")
    return int(value)


def local_to_plane(origin: int, local: Real) -> Real:
    """A ``local`` coordinate (either type) relative to a window origin -> the plane's coordinate."""
    return _integer("origin", origin) + local


def edge_to_full_res(edge: Real, offset: int, downsample: int) -> Real:
    """A plane ``pixel_edge`` coordinate -> ``full_res`` (``c = x0 + e * d``)."""
    return offset + edge * downsample


def index_to_full_res(index: Real, offset: int, downsample: int) -> Real:
    """A plane ``pixel_index`` coordinate -> ``full_res`` (``c = x0 + (i + 0.5) * d``)."""
    return offset + (index + 0.5) * downsample


def edge_to_labconstrictor(edge: Real) -> Real:
    """A plane ``pixel_edge`` coordinate -> a LabConstrictor result coordinate (``x = e - 0.5``)."""
    return edge - 0.5


def index_to_labconstrictor(index: Real) -> Real:
    """A plane ``pixel_index`` coordinate -> a LabConstrictor result coordinate (``x = i``)."""
    return index


def labconstrictor_to_full_res(x: Real, offset: int, downsample: int) -> Real:
    """The bridge's placement formula (LabConstrictor SPEC_WRONG_SCIENCE 1.1.3)."""
    return offset + (x + 0.5) * downsample


def context_bounds(
    bounds: tuple[int, int, int, int], margin: tuple[int, int], shape: tuple[int, int]
) -> dict[str, tuple[int, ...]]:
    """The window record of ADR 0004 for one patch: context bounds, origin, margins, local interior."""
    y0, y1, x0, x1 = (_integer("bounds", v) for v in bounds)
    my, mx = (_integer("margin", v) for v in margin)
    height, width = (_integer("shape", v) for v in shape)
    if my < 0 or mx < 0:
        raise ValueError(f"a margin is never negative, got {margin!r}")
    if not (0 <= y0 < y1 <= height and 0 <= x0 < x1 <= width):
        raise ValueError(f"bounds {bounds!r} are not a non-empty rectangle inside the plane {shape!r}")
    cb = (max(0, y0 - my), min(height, y1 + my), max(0, x0 - mx), min(width, x1 + mx))
    origin = (cb[0], cb[2])
    return {
        "context_bounds": cb,
        "origin": origin,
        "margin_requested": (my, my, mx, mx),
        "margin_clipped": (y0 - cb[0], cb[1] - y1, x0 - cb[2], cb[3] - x1),
        "local_interior": (y0 - origin[0], y1 - origin[0], x0 - origin[1], x1 - origin[1]),
    }
