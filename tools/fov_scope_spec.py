"""Reference rules of ADR 0002 AR12 (resolver contract version 4): the recorded FOV subset.

Pure Python, one function per rule of ``docs/adr/0002-shared-request-resolver.md`` ("Resolver
contract version 4"): the shape check of ``Request.fov_subset``, the refusal of a FOV the run does
not have (``A_FOV_NOT_IN_RUN``) and the ``fov_scope`` record with its ``scope_digest``.
morphobricks-preprocessing implements its own and reproduces the golden cases of
``tools/test_fov_scope_spec.py``. Nothing here reads a file or imports a brick.
"""

from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Sequence
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "window_histogram_spec", Path(__file__).resolve().parent / "window_histogram_spec.py"
)
_w = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_w)
canonical_json = _w.canonical_json  # the one canonical form (ADR 0004 EW11)

RESOLVER_VERSION = 4
ALL = "all"
EXPLICIT = "explicit"
CODE = "A_FOV_NOT_IN_RUN"
RECORD_KEYS = ("fov_subset", "selected", "run_images", "repeats", "fovs", "excluded", "scope_digest")
LISTED = 10
"""Unknown FOVs named one per line in the refusal before ``... and {m} more``."""

FovKey = tuple[str, str, str, str]


class FovNotInRun(Exception):
    """``A_FOV_NOT_IN_RUN``: the subset names a FOV key the run does not have."""

    code = CODE

    def __init__(self, unknown: Sequence[FovKey], run_images: int) -> None:
        self.unknown = tuple(sorted(unknown))
        super().__init__(refusal_message(self.unknown, run_images))


def check_subset(subset: object) -> None:
    """Refuse a malformed ``fov_subset`` (``ValueError``), before anything is classified.

    None is valid (every image of the run). Otherwise a non-empty tuple of FOV keys, each a tuple of
    exactly four ``str`` (condition, biological_repeat, technical_repeat, position_id), none twice.
    An index, a path, a list or a key of another length is malformed: a FOV is never named by
    position.
    """
    if subset is None:
        return
    if not isinstance(subset, tuple) or not all(
        isinstance(k, tuple) and len(k) == 4 and all(isinstance(p, str) for p in k) for k in subset
    ):
        raise ValueError(
            "fov_subset must be None or a tuple of FOV keys, each a tuple of four str "
            f"(condition, biological_repeat, technical_repeat, position_id), not {subset!r}"
        )
    if not subset:
        raise ValueError(
            "fov_subset is empty; name at least one FOV by its key, or leave it unset (None) to "
            "use every image of the run"
        )
    seen: set[FovKey] = set()
    for key in subset:
        if key in seen:
            raise ValueError(f"the FOV {key!r} is named twice in fov_subset")
        seen.add(key)


def refusal_message(unknown: Sequence[FovKey], run_images: int) -> str:
    """The exact ``A_FOV_NOT_IN_RUN`` message: unknown keys sorted, at most ten listed."""
    keys = tuple(sorted(unknown))
    shown = "\n".join(f"  - {key!r}" for key in keys[:LISTED])
    more = f"\n  ... and {len(keys) - LISTED} more" if len(keys) > LISTED else ""
    return (
        f"The requested FOV subset names {len(keys)} FOV(s) that this run does not have:\n"
        f"{shown}{more}\nNothing was selected or read. Name each FOV by its key (condition, "
        "biological_repeat, technical_repeat, position_id) exactly as RunInputs.fovs() lists it, "
        f"or leave fov_subset unset to use all {run_images} images of the run (A_FOV_NOT_IN_RUN)."
    )


def scope_digest(mode: str, fovs: Sequence[FovKey]) -> str:
    """SHA-256 of the canonical JSON of ``{"fov_subset": mode, "fovs": sorted keys}``."""
    text = canonical_json({"fov_subset": mode, "fovs": [list(k) for k in sorted(fovs)]})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fov_scope(run: Sequence[tuple[FovKey, str]], subset: tuple[FovKey, ...] | None) -> dict:
    """Return the ``fov_scope`` record of a request on a run.

    Parameters
    ----------
    run
        Every FOV of the run as ``(key, repeat_group)``.
    subset
        ``Request.fov_subset``: None (every image) or the explicit keys.

    Raises
    ------
    ValueError
        A malformed subset (:func:`check_subset`).
    FovNotInRun
        A key the run does not have; the request has no scope and no record.
    """
    check_subset(subset)
    keys = {key for key, _ in run}
    if subset is not None:
        unknown = [k for k in subset if k not in keys]
        if unknown:
            raise FovNotInRun(unknown, len(keys))
    chosen = keys if subset is None else set(subset)
    mode = ALL if subset is None else EXPLICIT
    fovs = sorted(chosen)
    repeats: dict[str, list[int]] = {}
    for key, group in run:
        counts = repeats.setdefault(group, [0, 0])
        counts[0] += key in chosen
        counts[1] += 1
    return {
        "fov_subset": mode,
        "selected": len(fovs),
        "run_images": len(keys),
        "repeats": [
            {"repeat_group": g, "selected": s, "run_images": n}
            for g, (s, n) in sorted(repeats.items())
        ],
        "fovs": [list(k) for k in fovs],
        "excluded": [list(k) for k in sorted(keys - chosen)],
        "scope_digest": scope_digest(mode, fovs),
    }
