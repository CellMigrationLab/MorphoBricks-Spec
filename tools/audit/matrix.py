"""AUDIT TOOL ONLY: the case matrix of the experiment-description v1 matrix audit.

Generates every case of docs/audits/matrix-audit-2026-11-07.md: a tiny synthetic dataset (TIFF
images and masks), the user's confirmed answers, the `morphobricks.toml` those answers give under
docs/experiment-v1.md (written with refval's canonical writer) and the spec's expected outcome
(E_/W_ codes from refval; R_ and A_ codes from the physical oracle below, which implements the
rules of experiment-v1 sections 4.3, 4.4b, 4.5a, 4.5c and 8 that need images).

Pruning rule (documented in the audit): every level of every dimension once, varied from one base
case (one-factor-at-a-time, OFAT), plus a greedy all-pairs covering array over five interacting
factors of three levels each (pairing, channel layout, control design, masks, header names).
Cases whose files differ from an earlier case only in `morphobricks.toml` (no dataset change) are
spec-only and point to the case whose brick runs they share.

Not a runtime package; nothing in MorphoBricks may import it.
"""

from __future__ import annotations

import itertools
import os
import tomllib
import unicodedata
from dataclasses import dataclass, field, replace
from pathlib import Path

import refval

LEVEL = {"DAPI": 1000, "DNA": 1000, "ACTIN": 2000, "PAX": 3000, "PHASE": 4000, "Tub": 2600,
         "R": 60, "G": 120, "B": 180}
CONFIRMED_ON = "2026-11-06"


@dataclass(frozen=True)
class Img:
    cond: str | None          # condition folder (None: the experiment root is the leaf)
    rep: str | None           # biological-repeat folder
    tech: str | None          # technical-repeat folder
    pos: str
    chans: tuple[str, ...]    # canonical channel ID at each C index (the truth)
    hdr: tuple[str, ...] | None  # header channel names, None when the file names none
    axes: str = "CYX"         # CYX, YX, TCYX, ZCYX, YXS (RGB)
    phys: tuple[float, float] | None = (0.5, 0.5)  # (x, y) micrometres, None: no calibration
    mask: str = "instances"   # instances, binary, bool, grouped, many_binary, none
    mask_axes: str = "YX"     # YX or TYX

    def folders(self) -> tuple[str, ...]:
        return tuple(x for x in (self.cond, self.rep, self.tech) if x is not None)

    def unit(self) -> tuple[str, str, str]:
        return (self.cond or "single", self.rep or "single", self.tech or "single")


@dataclass
class Case:
    cid: str
    title: str
    dims: dict
    images: list[Img]
    extra: list[str] = field(default_factory=list)       # stray image paths (relative)
    empty_dirs: list[str] = field(default_factory=list)
    cond_ids: dict = field(default_factory=dict)          # folder -> condition ID
    groups: dict = field(default_factory=dict)            # (cond folder, rep folder) -> repeat ID
    tech_ids: dict = field(default_factory=dict)          # tech folder -> technical repeat ID
    channel_ids: dict = field(default_factory=dict)       # header-free override (unused)
    references: dict = field(default_factory=dict)        # condition ID -> reference ID
    targets: dict = field(default_factory=dict)           # condition ID -> target text
    mask_decl: str | None = None                          # representation the user declares
    unconfirmed_aliases: set = field(default_factory=set)  # header names not in header_names
    discovery: str | None = None   # discovery refusal the spec leaves to preprocessing
    spec_note: str = ""            # where the spec is silent or wrong (MISMATCH-SPEC candidates)
    shares_runs: str | None = None  # spec-only case: brick runs are those of this case
    cp_binary_policy: bool = False  # CellPatcher cell mode with binary_mask_policy (section 4.5c)
    model_patch: object = None      # callable(doc) editing the model (spec-only variants)


# ------------------------------------------------------------------ base and helpers
def grid(conds=("CTRL", "DrugA"), reps=("rep1", "rep2"), techs=(None,), n=2, chans=("DAPI", "ACTIN"),
         hdr="same", **kw) -> list[Img]:
    out = []
    for c in conds:
        for r in reps:
            for t in techs:
                for i in range(n):
                    h = tuple(chans) if hdr == "same" else None
                    out.append(Img(c, r, t, f"f{i + 1}", tuple(chans), h, **kw))
    return out


def edit(imgs, pred, **changes):
    return [replace(i, **changes) if pred(i) else i for i in imgs]


def base(cid, title, dims, **kw) -> Case:
    return Case(cid, title, dims, grid(), references={"DrugA": "CTRL"}, **kw)


# ------------------------------------------------------------------ the v1 model of a case
def model(case: Case) -> dict:
    conds, members, chans = {}, {}, {}
    order = []
    for im in case.images:
        cf = im.cond or "single"
        cid = case.cond_ids.get(cf, cf)
        conds.setdefault(cid, {"source_folder": cf})
        rf = im.rep or "single"
        rid = case.groups.get((cf, rf), rf)
        tf = im.tech or "single"
        tid = case.tech_ids.get(tf, tf)
        m = members.setdefault((rid, cid), {"source_repeat": rf, "images": [], "units": {}})
        m["images"].append(im)
        u = m["units"].setdefault(tid, {"source_folder": tf, "first": im})
        for i, ch in enumerate(im.chans):
            if ch not in chans:
                chans[ch] = set()
                order.append(ch)
            if im.hdr is not None and i < len(im.hdr) and im.hdr[i] not in case.unconfirmed_aliases:
                if ch not in ("R", "G", "B"):
                    chans[ch].add(im.hdr[i])
    doc = {"schema": "morphobricks-experiment", "schema_version": 1, "conditions": {},
           "channels": {}, "repeats": {}}
    for cid, c in conds.items():
        doc["conditions"][cid] = dict(c)
        if cid in case.references:
            doc["conditions"][cid]["reference"] = case.references[cid]
        if cid in case.targets:
            doc["conditions"][cid]["target"] = case.targets[cid]
    for ch in order:
        doc["channels"][ch] = {"header_names": sorted(chans[ch])} if chans[ch] else {}
    for (rid, cid), m in members.items():
        rep = doc["repeats"].setdefault(rid, {"confirmed": True, "confirmed_on": CONFIRMED_ON,
                                              "members": {}})
        units = {}
        for tid, u in m["units"].items():
            units[tid] = {"source_folder": u["source_folder"], "channels": list(u["first"].chans)}
            if u["first"].axes == "YXS":
                units[tid]["image_type"] = "rgb"
        rep["members"][cid] = {"source_repeat": m["source_repeat"], "image_count": len(m["images"]),
                               "technical_repeats": units}
    kinds = {im.mask for im in case.images if im.mask != "none"}
    if kinds:
        truth = "binary" if kinds & {"binary", "bool"} else "instances"
        doc["masks"] = {"Cells": {"source_type": "Cells",
                                  "representation": case.mask_decl or truth}}
    doc["used_ids"] = {
        "conditions": sorted(doc["conditions"]), "channels": sorted(doc["channels"]),
        "repeats": sorted(doc["repeats"]),
        "technical_repeats": sorted({t for r in doc["repeats"].values()
                                     for m in r["members"].values()
                                     for t in m["technical_repeats"]}),
    }
    if case.model_patch:
        case.model_patch(doc)
    return doc


# ------------------------------------------------------------------ the physical oracle
def physical(case: Case, doc: dict) -> dict:
    """R_ and A_ codes of experiment-v1 sections 4.3, 4.4b, 4.5, 8 that need the images."""
    r_codes, a_codes, notes = set(), {}, []
    if case.discovery:
        return {"R": ["discovery:" + case.discovery], "A": {}, "notes": notes}
    for im in case.images:
        for f in im.folders():
            if unicodedata.normalize("NFC", f) != f:
                r_codes.add("R_FOLDER_NOT_NFC")
    units: dict = {}
    for im in case.images:
        units.setdefault(im.unit(), []).append(im)
    lists = set()
    for key, ims in units.items():
        sig = {(len(i.chans), i.axes == "YXS", i.axes, i.hdr) for i in ims}
        if len(sig) > 1:
            r_codes.add("R_UNIT_NOT_HOMOGENEOUS")
            continue
        first = ims[0]
        lists.add(first.chans)
        if first.hdr:
            for i, h in enumerate(first.hdr):
                hn = doc["channels"].get(first.chans[i], {}).get("header_names", [])
                if first.chans[i] not in ("R", "G", "B") and \
                        unicodedata.normalize("NFC", h) not in [unicodedata.normalize("NFC", x) for x in hn]:
                    r_codes.add("R_HEADER_CONTRADICTION")
    if any(i.mask in ("grouped", "many_binary", "instances") for i in case.images) and \
            doc.get("masks", {}).get("Cells", {}).get("representation") == "binary":
        if any(i.mask in ("grouped", "many_binary", "instances") for i in case.images):
            r_codes.add("R_MASK_CONTRADICTS_REPRESENTATION")
    stage12 = set()
    if len(lists) > 1:
        stage12.add("R_HETEROGENEOUS_LAYOUT_NOT_ENABLED")
    # analysis requests of the standard request set (runner.REQUESTS)
    rep = doc.get("masks", {}).get("Cells", {}).get("representation")
    with_mask = [i for i in case.images if i.mask != "none"]
    all_ch = list(doc["channels"])
    unit_lists = [ims[0].chans for ims in units.values()]
    for brick in ("morphoobjects", "morphorelate", "fiberfeatures", "morphoembed", "cellpatcher_cell"):
        codes = set()
        if with_mask and rep == "binary" and not (brick == "cellpatcher_cell" and case.cp_binary_policy):
            codes.add("A_MASK_NOT_INSTANCES")
        if with_mask and len(with_mask) < len(case.images):
            codes.add("A_SCOPE_INCOMPLETE")
        if not with_mask:
            codes.add("no object set (no masks)")
        if brick != "cellpatcher_cell" and any(any(c not in ul for ul in unit_lists) for c in all_ch):
            codes.add("A_SCOPE_INCOMPLETE")
        if any(i.axes == "YXS" for i in case.images):
            codes.add("A_RGB_NOT_SUPPORTED")
        a_codes[brick] = sorted(codes)
    for brick in ("cellpatcher_grid", "cellpatcher_random", "cellpatcher_whole_fov"):
        a_codes[brick] = ["A_RGB_NOT_SUPPORTED"] if any(i.axes == "YXS" for i in case.images) else []
    return {"R": sorted(r_codes), "R_stage12": sorted(stage12), "A": a_codes, "notes": notes}


def expected(case: Case) -> dict:
    doc = model(case)
    data = refval.write(doc) if _writable(doc) else None
    if data is None:
        return {"toml": None, "E": ["(model not writable)"], "W": [], "phase": None}
    r, _ = refval.validate(data)
    out = {"toml": data.decode("utf-8"), "phase": r.phase, "E": sorted(r.codes),
           "W": sorted(r.warning_codes), "errors": [list(map(str, e)) for e in r.errors][:12]}
    out.update(physical(case, doc))
    if out["E"]:
        out["verdict"] = "refused: " + ", ".join(out["E"])
    elif out["R"]:
        out["verdict"] = "refused: " + ", ".join(out["R"])
    else:
        out["verdict"] = "accepted" + (" (Stage 1-2: " + ", ".join(out["R_stage12"]) + ")"
                                       if out["R_stage12"] else "")
    return out


def _writable(doc):
    try:
        refval.write(doc)
        return True
    except Exception:  # noqa: BLE001 - audit tool
        return False


# ------------------------------------------------------------------ the cases
def ofat() -> list[Case]:
    C = []
    add = C.append
    b = base
    # 1. folder structures
    add(Case("F01", "single flat folder (root is the leaf)", {"F": "flat"},
             [Img(None, None, None, f"f{i}", ("DAPI", "ACTIN"), ("DAPI", "ACTIN")) for i in (1, 2)],
             spec_note="No condition folder: preprocessing labels the condition `single`; v1 gives "
                       "`single` rules for repeats and technical repeats only (3.2), and 4.2 "
                       "`source_folder` is 'the condition folder label as read from disk', which "
                       "does not exist here."))
    add(Case("F02", "one condition, two repeats", {"F": "one-condition"},
             grid(conds=("CTRL",))))
    add(Case("F03", "three conditions, same repeat names", {"F": "several-conditions"},
             grid(conds=("CTRL", "DrugA", "DrugB")), references={"DrugA": "CTRL", "DrugB": "CTRL"}))
    add(Case("F04", "one biological repeat", {"F": "one-repeat"}, grid(reps=("rep1",)),
             references={"DrugA": "CTRL"}))
    add(Case("F05", "repeats paired with different folder names (v03)", {"F": "paired-different"},
             grid(conds=("CTRL",)) + [replace(i, cond="DrugA", rep={"rep1": "exp23", "rep2": "exp24"}[i.rep])
                                      for i in grid(conds=("CTRL",))],
             groups={("CTRL", "rep1"): "Day1", ("DrugA", "exp23"): "Day1",
                     ("CTRL", "rep2"): "Day2", ("DrugA", "exp24"): "Day2"},
             references={"DrugA": "CTRL"}))
    add(Case("F06", "a repeat missing in one condition", {"F": "repeat-missing"},
             [i for i in grid() if not (i.cond == "DrugA" and i.rep == "rep2")],
             references={"DrugA": "CTRL"}))
    add(Case("F07", "same source label in different repeats (v30)", {"F": "same-label-two-repeats"},
             grid(), groups={("CTRL", "rep1"): "Day1", ("DrugA", "rep2"): "Day1",
                             ("CTRL", "rep2"): "Day2", ("DrugA", "rep1"): "Day2"},
             references={"DrugA": "CTRL"}))
    add(Case("F08", "swapped labels: rep1 paired with the other condition's rep2", {"F": "swapped-labels"},
             grid(), groups={("CTRL", "rep1"): "rep1", ("DrugA", "rep2"): "rep1",
                             ("CTRL", "rep2"): "rep2", ("DrugA", "rep1"): "rep2"},
             references={"DrugA": "CTRL"}))
    add(Case("F09", "one technical-repeat folder", {"F": "tech-one"}, grid(techs=("acq1",)),
             references={"DrugA": "CTRL"}))
    add(Case("F10", "several technical repeats, same layout", {"F": "tech-several-same"},
             grid(techs=("acq1", "acq2")), references={"DrugA": "CTRL"}))
    add(Case("F11", "several technical repeats, different layouts (named)", {"F": "tech-several-different"},
             edit(grid(techs=("acq1", "acq2")), lambda i: i.tech == "acq2" and i.cond == "CTRL",
                  chans=("ACTIN", "DAPI"), hdr=("ACTIN", "DAPI")), references={"DrugA": "CTRL"}))
    add(Case("F12", "images beside sub-folders", {"F": "images-beside-folders"}, grid(),
             extra=["CTRL/stray.ome.tif"], references={"DrugA": "CTRL"}, discovery="tiff_outside_leaf"))
    add(Case("F13", "one image per folder", {"F": "one-image"}, grid(n=1), references={"DrugA": "CTRL"}))
    add(Case("F14", "many images per folder (6)", {"F": "many-images"}, grid(n=6),
             references={"DrugA": "CTRL"}))
    add(Case("F15", "empty folders (an empty condition and an empty repeat)", {"F": "empty-folders"},
             grid(), empty_dirs=["DrugB", "CTRL/rep3"], references={"DrugA": "CTRL"}))
    add(Case("F16", "reserved/forbidden folder names: condition `control`, repeat `z`, technical repeat `files`",
             {"F": "reserved-names"},
             [replace(i, cond={"CTRL": "control"}.get(i.cond, i.cond), rep={"rep1": "z"}.get(i.rep, i.rep))
              for i in grid(techs=("files",))],
             cond_ids={"control": "ctrl"}, tech_ids={"files": "acq1"}, references={"DrugA": "ctrl"},
             groups={("control", "z"): "R1", ("DrugA", "z"): "R1"},
             spec_note="4.6a gives the 'propose another ID' rule for condition and technical-repeat "
                       "folders only; a biological-repeat folder `z` defaults to the repeat ID `z` "
                       "(3.1), which is a forbidden ID key (4.7): the repeat proposal rule is silent."))
    add(Case("F17", "lower-case `single` folder as the only repeat folder", {"F": "single-folder"},
             grid(reps=("single",)), references={"DrugA": "CTRL"}))
    add(Case("F18", "`Single` folder (other case)", {"F": "Single-folder"},
             grid(reps=("Single",)), references={"DrugA": "CTRL"}, discovery="reserved_folder_name"))
    add(Case("F19", "repeat folders differing only in case (rep1 / Rep1)", {"F": "case-collision"},
             edit(grid(), lambda i: i.cond == "DrugA" and i.rep == "rep1", rep="Rep1"),
             references={"DrugA": "CTRL"}, discovery="case_conflict"))
    add(Case("F20", "folder label `NA`", {"F": "invalid-label"},
             edit(grid(), lambda i: i.rep == "rep2", rep="NA"), references={"DrugA": "CTRL"},
             discovery="invalid_name"))
    add(Case("F21", "non-NFC folder label (decomposed e-acute)", {"F": "non-nfc"},
             edit(grid(), lambda i: i.cond == "DrugA", cond="Café"),
             cond_ids={"Café": "Cafe"}, references={"Cafe": "CTRL"}))
    # 2. channels
    add(Case("C01", "one channel, YX", {"C": "1", "A": "YX"},
             grid(chans=("DAPI",), axes="YX"), references={"DrugA": "CTRL"}))
    add(Case("C03", "three channels", {"C": "3"}, grid(chans=("DAPI", "ACTIN", "PAX")),
             references={"DrugA": "CTRL"}))
    add(Case("C04", "four channels", {"C": "4+"}, grid(chans=("DAPI", "ACTIN", "PAX", "PHASE")),
             references={"DrugA": "CTRL"}))
    add(Case("C05", "same count, different order across conditions (named)", {"C": "order-conditions", "K": "control-other-layout"},
             edit(grid(), lambda i: i.cond == "DrugA", chans=("ACTIN", "DAPI"), hdr=("ACTIN", "DAPI")),
             references={"DrugA": "CTRL"}))
    add(Case("C06", "different order across repeats (named)", {"C": "order-repeats"},
             edit(grid(), lambda i: i.rep == "rep2", chans=("ACTIN", "DAPI"), hdr=("ACTIN", "DAPI")),
             references={"DrugA": "CTRL"}))
    add(Case("C07", "different order within one unit (named)", {"C": "order-within-unit"},
             edit(grid(), lambda i: i.cond == "DrugA" and i.rep == "rep1" and i.pos == "f2",
                  chans=("ACTIN", "DAPI"), hdr=("ACTIN", "DAPI")), references={"DrugA": "CTRL"}))
    add(Case("C08", "an extra channel in some images of one unit", {"C": "extra-some-images"},
             edit(grid(), lambda i: i.cond == "DrugA" and i.rep == "rep1" and i.pos == "f2",
                  chans=("DAPI", "ACTIN", "PAX"), hdr=("DAPI", "ACTIN", "PAX")),
             references={"DrugA": "CTRL"}))
    add(Case("C09", "an extra channel in a whole technical repeat", {"C": "extra-unit"},
             edit(grid(techs=("acq1", "acq2")), lambda i: i.tech == "acq2",
                  chans=("DAPI", "ACTIN", "PAX"), hdr=("DAPI", "ACTIN", "PAX")),
             references={"DrugA": "CTRL"}))
    add(Case("C10", "a missing channel in one condition", {"C": "missing-channel"},
             edit(grid(), lambda i: i.cond == "DrugA", chans=("DAPI",), hdr=("DAPI",)),
             references={"DrugA": "CTRL"}))
    add(Case("C11", "header names missing (unnamed channels)", {"C": "unnamed"},
             grid(hdr=None), references={"DrugA": "CTRL"}))
    alias = edit(grid(chans=("DNA", "ACTIN")), lambda i: True, hdr=("DAPI", "ACTIN"))
    alias = edit(alias, lambda i: i.cond == "DrugA", hdr=("Hoechst", "ACTIN"))
    add(Case("C12", "header alias: DNA confirmed by DAPI and by Hoechst", {"C": "alias"}, alias,
             references={"DrugA": "CTRL"}))
    add(Case("C12b", "header alias not confirmed (Hoechst not in header_names)", {"C": "alias-unconfirmed"},
             alias, references={"DrugA": "CTRL"}, unconfirmed_aliases={"Hoechst"}, shares_runs="C12"))
    add(Case("C13", "header names differing in case (DAPI / dapi)", {"C": "case"},
             edit(grid(), lambda i: i.cond == "DrugA", hdr=("dapi", "ACTIN")),
             references={"DrugA": "CTRL"}))
    add(Case("C14", "header name with outer whitespace ('DAPI ' / 'DAPI')", {"C": "whitespace"},
             edit(grid(), lambda i: i.cond == "DrugA", hdr=("DAPI ", "ACTIN")),
             references={"DrugA": "CTRL"}))
    add(Case("C15", "header name `t` (reserved as a channel ID; channel confirmed as `Tub`)", {"C": "reserved-header"},
             edit(grid(chans=("DAPI", "Tub")), lambda i: True, hdr=("DAPI", "t")),
             references={"DrugA": "CTRL"}))
    add(Case("C16", "RGB images", {"C": "rgb"},
             grid(chans=("R", "G", "B"), axes="YXS", hdr=None), references={"DrugA": "CTRL"}))
    add(Case("C17", "unnamed channels, order swapped across conditions", {"C": "unnamed-swapped"},
             edit(grid(hdr=None), lambda i: i.cond == "DrugA", chans=("ACTIN", "DAPI")),
             references={"DrugA": "CTRL"},
             spec_note="Undetectable by any layer (experiment-v1 8); v1 lets the user declare the "
                       "per-unit order, the bricks give no way to state it."))
    # 3. control / experiment designs
    add(Case("K01", "no control", {"K": "none"}, grid()))
    add(Case("K03", "several controls for different treatments", {"K": "several-controls"},
             grid(conds=("DMSO", "DrugA", "WT", "KO")), references={"DrugA": "DMSO", "KO": "WT"}))
    add(Case("K04", "per-treatment matched controls (siNC per background)", {"K": "matched-controls"},
             grid(conds=("VEC_SiNC", "VEC_SiCol", "THBS5_SiNC", "THBS5_SiCol")),
             references={"VEC_SiCol": "VEC_SiNC", "THBS5_SiCol": "THBS5_SiNC", "THBS5_SiNC": "VEC_SiNC"}))
    add(Case("K05", "reference chain B -> A -> CTRL", {"K": "chain"},
             grid(conds=("CTRL", "DrugA", "DrugB")), references={"DrugA": "CTRL", "DrugB": "DrugA"}))
    add(Case("K06", "reference cycle A -> B -> A (refused)", {"K": "cycle"},
             grid(conds=("DrugA", "DrugB")), references={"DrugA": "DrugB", "DrugB": "DrugA"}))
    add(Case("K07", "several reagents per target (si1, si2 -> SRC)", {"K": "reagents-per-target"},
             grid(conds=("CTRL", "si1", "si2")), references={"si1": "CTRL", "si2": "CTRL"},
             targets={"si1": "SRC", "si2": "SRC"}))
    add(Case("K08", "control missing in one repeat", {"K": "control-missing-repeat"},
             [i for i in grid() if not (i.cond == "CTRL" and i.rep == "rep2")],
             references={"DrugA": "CTRL"}))
    add(Case("K09", "control and condition share no repeat", {"K": "unpaired"},
             grid(conds=("CTRL",), reps=("rep3",)) + grid(conds=("DrugA",)),
             references={"DrugA": "CTRL"}))
    add(Case("K10", "control present only in some technical repeats", {"K": "control-some-tech"},
             [i for i in grid(techs=("acq1", "acq2")) if not (i.cond == "CTRL" and i.tech == "acq2")],
             references={"DrugA": "CTRL"}))
    add(Case("K11", "reference names a display name / self reference (spec only)", {"K": "bad-reference"},
             grid(), references={"DrugA": "Control"}, shares_runs="A02",
             model_patch=lambda d: d["conditions"]["CTRL"].update(display_name="Control")))
    add(Case("K12", "self reference (spec only)", {"K": "self"}, grid(),
             references={"DrugA": "DrugA"}, shares_runs="A02"))
    # 4. axes, calibration, masks
    add(base("A02", "base: CTRL/DrugA x rep1/rep2, CYX, 2 named channels, instance masks", {"A": "CYX"}))
    add(Case("A03", "TCYX with T=2, Z=1 (masks TYX)", {"A": "TCYX"},
             grid(axes="TCYX", mask_axes="TYX"), references={"DrugA": "CTRL"},
             spec_note="v1 is silent on time-lapses: 2-D planes only (1), no T rule; the "
                       "MorphoCoverage export of a multi-plane set is refused."))
    add(Case("A04", "Z>1 (ZCYX, Z=3)", {"A": "Z>1"}, grid(axes="ZCYX"), references={"DrugA": "CTRL"},
             discovery="z_stack_not_supported"))
    add(Case("A05", "non-square pixels (0.5 x 0.25 um)", {"A": "non-square"},
             grid(phys=(0.5, 0.25)), references={"DrugA": "CTRL"}))
    add(Case("A06", "missing calibration", {"A": "no-calibration"}, grid(phys=None),
             references={"DrugA": "CTRL"}))
    add(Case("A07", "calibration missing in some images", {"A": "partial-calibration"},
             edit(grid(), lambda i: i.cond == "DrugA", phys=None), references={"DrugA": "CTRL"}))
    add(Case("A08", "binary masks (0/1, two blobs), declared binary", {"A": "mask-binary"},
             grid(mask="binary"), references={"DrugA": "CTRL"}))
    add(Case("A08b", "binary masks, CellPatcher binary_mask_policy=connected_components", {"A": "mask-binary-converted"},
             grid(mask="bool"), references={"DrugA": "CTRL"}, cp_binary_policy=True))
    add(Case("A09", "binary masks stored as booleans", {"A": "mask-bool"}, grid(mask="bool"),
             references={"DrugA": "CTRL"}))
    add(Case("A10", "masks missing (no masks folder)", {"A": "mask-missing"}, grid(mask="none"),
             references={"DrugA": "CTRL"}))
    add(Case("A11", "masks partial (DrugA not segmented yet)", {"A": "mask-partial"},
             edit(grid(), lambda i: i.cond == "DrugA", mask="none"), references={"DrugA": "CTRL"}))
    add(Case("A12", "shared 2-D mask for a time-lapse (YX mask, T=2)", {"A": "mask-shared"},
             grid(axes="TCYX", mask_axes="YX"), references={"DrugA": "CTRL"},
             discovery="mask_planes_mismatch"))
    add(Case("A13", "mask declared binary holding instance labels (>2 values)", {"A": "mask-contradiction"},
             grid(), references={"DrugA": "CTRL"}, mask_decl="binary"))
    add(Case("A14", "grouped (parent_labels) mask declared instances", {"A": "mask-grouped"},
             grid(mask="grouped"), references={"DrugA": "CTRL"},
             spec_note="v1 cannot describe a grouped mask (4.5b); declaring it `instances` is "
                       "not detectable from the file and pixels cannot prove instances (4.5a)."))
    return C


FACTORS = {
    "P": ("same", "different", "missing"),
    "L": ("homogeneous", "swapped-conditions", "tech-different"),
    "K": ("one", "chain", "none"),
    "M": ("instances", "binary", "partial"),
    "H": ("named", "unnamed", "alias"),
}


def allpairs(factors: dict) -> list[dict]:
    """Greedy all-pairs covering array (deterministic)."""
    names = list(factors)
    need = {((a, x), (b, y)) for a, b in itertools.combinations(names, 2)
            for x in factors[a] for y in factors[b]}
    rows = []
    every = [dict(zip(names, v)) for v in itertools.product(*factors.values())]
    while need:
        best = max(every, key=lambda r: sum(((a, r[a]), (b, r[b])) in need
                                            for a, b in itertools.combinations(names, 2)))
        rows.append(best)
        need -= {((a, best[a]), (b, best[b])) for a, b in itertools.combinations(names, 2)}
    return rows


def pairwise_case(n: int, f: dict) -> Case:
    conds = ("CTRL", "DrugA", "DrugB") if f["K"] == "chain" else ("CTRL", "DrugA")
    techs = ("acq1", "acq2") if f["L"] == "tech-different" else (None,)
    chans = ("DNA", "ACTIN") if f["H"] == "alias" else ("DAPI", "ACTIN")
    imgs = grid(conds=conds, techs=techs, chans=chans, hdr=None if f["H"] == "unnamed" else "same")
    if f["H"] == "alias":
        imgs = edit(imgs, lambda i: True, hdr=("DAPI", "ACTIN"))
        imgs = edit(imgs, lambda i: i.cond == "DrugA", hdr=("Hoechst", "ACTIN"))
    groups = {}
    if f["P"] == "different":
        imgs = [replace(i, rep={"rep1": "exp23", "rep2": "exp24"}[i.rep]) if i.cond == "DrugA" else i
                for i in imgs]
        groups = {("DrugA", "exp23"): "rep1", ("DrugA", "exp24"): "rep2"}
    elif f["P"] == "missing":
        imgs = [i for i in imgs if not (i.cond == "DrugA" and i.rep == "rep2")]
    sw = (chans[1], chans[0])

    def swap(i):
        h = None if i.hdr is None else (i.hdr[1], i.hdr[0])
        return replace(i, chans=sw, hdr=h)
    if f["L"] == "swapped-conditions":
        imgs = [swap(i) if i.cond == "DrugA" else i for i in imgs]
    elif f["L"] == "tech-different":
        imgs = [swap(i) if i.tech == "acq2" and i.cond == "CTRL" else i for i in imgs]
    if f["M"] == "binary":
        imgs = edit(imgs, lambda i: True, mask="binary")
    elif f["M"] == "partial":
        imgs = edit(imgs, lambda i: i.cond == "DrugA", mask="none")
    refs = {"one": {"DrugA": "CTRL"}, "chain": {"DrugA": "CTRL", "DrugB": "DrugA"}, "none": {}}[f["K"]]
    title = ", ".join(f"{k}={v}" for k, v in f.items())
    return Case(f"P{n:02d}", title, dict(f), imgs, groups=groups, references=refs)


def cases() -> list[Case]:
    return ofat() + [pairwise_case(n + 1, f) for n, f in enumerate(allpairs(FACTORS))]


# ------------------------------------------------------------------ dataset writer
def write_dataset(case: Case, root: Path) -> None:
    import numpy as np
    import tifffile

    rng = np.random.default_rng(abs(hash(case.cid)) % (2 ** 32))
    exp, masks = root / "exp", root / "masks"
    exp.mkdir(parents=True)
    for im in case.images:
        d = exp.joinpath(*im.folders())
        d.mkdir(parents=True, exist_ok=True)
        lab = label_image(im.mask if im.mask != "none" else "instances")
        obj = lab > 0
        if im.axes == "YXS":
            a = np.zeros((32, 32, 3), np.uint8)
            for k, ch in enumerate(im.chans):
                a[..., k] = np.where(obj, LEVEL[ch], LEVEL[ch] // 2) + rng.integers(0, 5, (32, 32))
            tifffile.imwrite(d / f"{im.pos}.tif", a, photometric="rgb")
        else:
            planes = []
            for ch in im.chans:
                lv = LEVEL.get(ch, 500)
                planes.append(np.where(obj, lv, lv // 2) + rng.integers(-20, 21, (32, 32)))
            a = np.stack(planes).astype(np.uint16)
            axes = im.axes
            if axes == "YX":
                a = a[0]
            elif axes == "TCYX":
                a = np.stack([a, a])
            elif axes == "ZCYX":
                a = np.stack([a, a, a])
            md = {"axes": axes}
            if im.hdr is not None:
                md["Channel"] = {"Name": list(im.hdr)}
            if im.phys:
                md["PhysicalSizeX"], md["PhysicalSizeY"] = im.phys
            if im.hdr is None and im.phys is None:
                tifffile.imwrite(d / f"{im.pos}.tif", a, imagej=True, metadata={"axes": axes})
            elif im.hdr is None:
                tifffile.imwrite(d / f"{im.pos}.ome.tif", a, ome=True,
                                 metadata={k: v for k, v in md.items()})
            else:
                tifffile.imwrite(d / f"{im.pos}.ome.tif", a, ome=True, metadata=md)
        if im.mask != "none":
            md_ = masks / "Cells" / Path(*im.folders())
            md_.mkdir(parents=True, exist_ok=True)
            m = lab
            if im.mask == "bool":
                m = lab > 0
            elif im.mask == "binary":
                m = (lab > 0).astype(np.uint8)
            if im.mask_axes == "TYX":
                m = np.stack([m, m])
            tifffile.imwrite(md_ / f"{im.pos}.ome.tif", m, ome=True, metadata={"axes": im.mask_axes})
    for e in case.extra:
        p = exp / e
        p.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imwrite(p, np.zeros((2, 32, 32), np.uint16), ome=True,
                         metadata={"axes": "CYX", "Channel": {"Name": ["DAPI", "ACTIN"]}})
    for e in case.empty_dirs:
        (exp / e).mkdir(parents=True, exist_ok=True)
    if not any(im.mask != "none" for im in case.images):
        masks.mkdir(exist_ok=True)


def label_image(kind: str):
    import numpy as np

    m = np.zeros((32, 32), np.uint16)
    m[2:12, 2:12] = 1
    m[16:28, 4:14] = 2
    m[5:15, 18:30] = 3
    if kind == "grouped":
        m[m == 3] = 1  # label 1 in two pieces, label 2 one piece
        m[22:30, 20:30] = 1
    return m


if __name__ == "__main__":
    import json
    import sys

    out = {}
    for c in cases():
        e = expected(c)
        out[c.cid] = {"title": c.title, "dims": c.dims, "verdict": e["verdict"], "E": e["E"],
                      "W": e["W"], "R": e["R"], "R_stage12": e.get("R_stage12", []), "A": e["A"]}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
