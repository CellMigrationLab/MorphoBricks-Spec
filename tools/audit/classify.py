"""AUDIT TOOL ONLY: classify each (case, brick) cell of the matrix audit and print the table.

    python classify.py RESULTS_JSON > table.md

Verdicts: MATCH; MISMATCH-SPEC (spec wrong or silent); MISMATCH-BRICK (brick differs from v1:
a Stage 1-3 item); BUG (wrong today regardless of the spec); N/A (not reached: an earlier brick
refused); SKIP (not runnable here). The automatic rules are in `cell()`; every exception decided
by reading the observation is in OVERRIDES with its reason. Not a runtime package.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

LEVEL = {"DAPI": 1000, "DNA": 1000, "ACTIN": 2000, "PAX": 3000, "PHASE": 4000, "Tub": 2600,
         "R": 60, "G": 120, "B": 180}
COLS = ("PP", "NORM", "CP", "MO", "MR", "FF", "ME", "MC")
SHORT = {"MATCH": "M", "MISMATCH-SPEC": "MS", "MISMATCH-BRICK": "MB", "BUG": "B", "N/A": "-",
         "SKIP": "skip"}

# (case, column) -> (verdict, reason). Decided by reading the observation in the results JSON.
OVERRIDES = {
    ("F01", "PP"): ("MISMATCH-SPEC", "pp labels the missing condition level `single`; v1 has no "
                    "rule for a condition without a folder (4.2 source_folder 'as read from disk')"),
    ("F16", "PP"): ("MISMATCH-SPEC", "pp keeps folder labels (v1 agrees); v1 has no 'propose another ID' "
                    "rule for a biological-repeat folder whose label is a forbidden ID (`z`), 4.6a covers "
                    "conditions and technical repeats only"),
    ("F07", "MC"): ("MISMATCH-BRICK", "silently pairs CTRL/rep1 with DrugA/rep1 by folder label; the "
                    "confirmed design pairs CTRL/rep1 with DrugA/rep2 (Day1): wrong pairing, no warning"),
    ("F08", "MC"): ("MISMATCH-BRICK", "pairs by folder label against the confirmed design (which v1 "
                    "refuses anyway, E_REPEAT_ID_SHADOWS_SOURCE)"),
    ("F05", "MC"): ("MISMATCH-BRICK", "user's pairing Day1/Day2 lost: 'Not compared (no biological repeat "
                    "holds both)'; the export has no repeat_group"),
    ("F16", "MC"): ("MISMATCH-BRICK", "comparison by canonical condition ID `ctrl` refused (export carries "
                    "the folder label `control`, no condition_id); by folder label it runs"),
    ("F21", "MC"): ("MISMATCH-BRICK", "comparison by canonical condition ID refused (folder label only)"),
    ("K06", "MC"): ("MATCH", "MorphoCoverage accepts mutual own_control rows A<->B (its own contrast "
                    "config); the v1 cycle is refused in the file before it could reach it"),
    ("K07", "MC"): ("MATCH", "reagent agreement from a target column the user supplies to "
                    "MorphoCoverage (its own input, AQ3); the export carries no target"),
    ("A06", "FF"): ("SKIP", "harness artefact: fiberfeatures' pixel defaults need a larger image than "
                    "32x32 (Gaussian kernel radius too large); not a v1 question"),
    ("A07", "MO"): ("MATCH", "mixed calibration refused explicitly (calibration is outside v1)"),
    ("A07", "MR"): ("MATCH", "mixed calibration refused explicitly"),
    ("A07", "FF"): ("MATCH", "mixed calibration refused explicitly"),
    ("A05", "FF"): ("MATCH", "fiberfeatures refuses features not exact on non-square pixels"),
    ("A03", "MC"): ("MISMATCH-SPEC", "export not written for several planes per FOV "
                    "(MorphoCoverage#604); v1 is silent on T>1"),
    ("A10", "MO"): ("MATCH", "no masks: object requests impossible, the patch set runs"),
    ("C15", "MO"): ("MISMATCH-BRICK", "canonical ID `Tub` refused (header names are the IDs); with the "
                    "header name `t` every FOV FAILS at provider time (reserved column), not refused at "
                    "planning"),
    ("C15", "MR"): ("MISMATCH-BRICK", "as MO: `Tub` refused; `t` fails every FOV at provider time"),
    ("C15", "FF"): ("BUG", "`Tub` refused (MB); with the header name, fiberfeatures ACCEPTS the reserved name `t` "
                    "(output column t__Cells__fa_mean) where MorphoObjects/MorphoRelate refuse it"),
    ("C14", "PP"): ("MISMATCH-BRICK", "header `DAPI ` trimmed and matched to `DAPI` (channel_names_trimmed); "
                    "v1 4.3 compares untrimmed (here both spellings confirmed, so the outcome agrees, the "
                    "rule does not)"),
    ("C16", "CP"): ("MATCH", "CellPatcher declares RGB support; grid normalization refuses until "
                    "normalization.image_type='rgb' is stated (explicit)"),
    ("C12b", "PP"): ("MATCH", "refused (channel_names_differ) ~ spec R_HEADER_CONTRADICTION"),
    ("A14", "PP"): ("MISMATCH-SPEC", "v1 cannot describe a grouped mask (4.5b); declared `instances` it is "
                    "measured as wrong objects and nothing can detect it; preprocessing's kind heuristic "
                    "(median pieces per label > 2) reports this mask `instances`"),
    ("C17", "NORM"): ("MISMATCH-BRICK", "SILENT: normalization pools C0 over DAPI (CTRL) and ACTIN (DrugA); "
                      "per-unit channel lists cannot be declared"),
    ("P06", "NORM"): ("MISMATCH-BRICK", "SILENT: C0/C1 pooled across technical repeats whose orders differ"),
    ("P02", "NORM"): ("MISMATCH-BRICK", "SILENT: C0/C1 pooled across conditions whose orders differ"),
    ("C17", "CP"): ("MISMATCH-BRICK", "patches carry C indices only; C0 is DAPI in CTRL and ACTIN in DrugA"),
    ("P06", "CP"): ("MISMATCH-BRICK", "patches by C index; technical repeats differ in order"),
    ("C17", "FF"): ("MISMATCH-BRICK", "SILENT: `ACTIN` resolves to C1 everywhere; in DrugA C1 is DAPI"),
    ("P06", "FF"): ("MISMATCH-BRICK", "SILENT: one global name->index list for units of different order"),
    ("C16", "NORM"): ("MATCH", "refused until the RGB normalization type is stated (explicit, no default)"),
}


def paired_expected(doc):
    out = {}
    for c, cond in doc["conditions"].items():
        ref = cond.get("reference")
        if ref:
            n = sum(1 for r in doc["repeats"].values() if c in r["members"] and ref in r["members"])
            out[f"{c} vs {ref}"] = n
    return out


def chan_bad(v):
    bad = []
    for col, g in (v.get("intensity") or {}).items():
        ch = col.split(":")[1].split("__")[0]
        for grp, val in g.items():
            if ch in LEVEL and abs(val - LEVEL[ch]) > 60:
                bad.append(f"{ch}@{grp}={val:g}")
    return bad


def cell(cid, rec, col):
    if (cid, col) in OVERRIDES:
        return OVERRIDES[(cid, col)]
    e, o = rec["expected"], rec["obs"]
    spec_refuses = bool(e["E"]) or bool(e["R"])
    pp_ok = o.get("pp_run", {}).get("rc") == 0
    if col == "PP":
        issues = sorted(set((o.get("pp_check", {}).get("issues") or []) +
                            (o.get("pp_run", {}).get("issues") or [])))
        errs = [i.split(":", 1)[1] for i in issues if i.startswith("error:")]
        if spec_refuses:
            if not pp_ok:
                return "MATCH", f"refused ({', '.join(errs)}) ~ spec {', '.join(e['E'] + e['R'])}"
            return "MISMATCH-BRICK", f"accepted; v1 refuses ({', '.join(e['E'] + e['R'])}): Stage 1 reader"
        if e.get("R_stage12"):
            if not pp_ok:
                return "MATCH", (f"refused ({', '.join(errs)}) = Stage 1-2 "
                                 "R_HETEROGENEOUS_LAYOUT_NOT_ENABLED; v1 accepts at Stage 3")
            return "MISMATCH-BRICK", ("accepted silently: unnamed units with different channel "
                                      "orders cannot be declared, so channels are pooled by C index")
        if not pp_ok:
            return "MISMATCH-BRICK", f"refused ({', '.join(errs)}); v1 accepts (confirmed aliases)"
        warn = [i.split(":", 1)[1] for i in issues if i.startswith("warning:")]
        return "MATCH", "accepted" + (f" (warnings {', '.join(warn)})" if warn else "")
    if not pp_ok:
        return "N/A", ""
    if col == "NORM":
        g = o.get("cp_grid", {})
        if not g.get("ok"):
            return "MATCH", "refused explicitly: " + g.get("error", "")[:120]
        doc = tomllib.loads(e["toml"]) if e.get("toml") else None
        want = {}
        for rid, r in (doc or {}).get("repeats", {}).items():
            for c, m in r["members"].items():
                want[f"{doc['conditions'][c]['source_folder']}/{m['source_repeat']}"] = rid
        got = {k: v[0] for k, v in g.get("normalization_group", {}).items()}
        bad = {k: (got.get(k), want[k]) for k in want if got.get(k) != want[k]}
        if bad:
            return "MISMATCH-BRICK", f"normalization group differs from the v1 repeat ID: {bad}"
        return "MATCH", "pooled by the confirmed repeat group (= v1 repeat ID)"
    if col == "CP":
        notes, verdict = [], "MATCH"
        exp_cell = e["A"].get("cellpatcher_cell", [])
        for mode in ("grid", "random", "whole_fov", "cell"):
            v = o.get(f"cp_{mode}")
            if v is None:
                continue
            if mode == "cell":
                if "A_MASK_NOT_INSTANCES" in exp_cell and v.get("ok"):
                    verdict = "MISMATCH-BRICK"
                    notes.append("cell mode ran on a mask v1 declares binary (no representation "
                                 "known; a 0/1 mask is one object per FOV); v1 A_MASK_NOT_INSTANCES")
                elif "A_SCOPE_INCOMPLETE" in exp_cell and not v.get("ok"):
                    notes.append("cell mode refuses the partial masks")
                elif not v.get("ok"):
                    notes.append(f"cell: {v.get('error', '')[:100]}")
            elif not v.get("ok") and mode != "grid":
                verdict = "MISMATCH-BRICK"
                notes.append(f"{mode}: {v.get('error', '')[:100]}")
        return verdict, "; ".join(notes) or "grid/random/whole_fov/cell ran; FOV key = folder labels"
    if col in ("MO", "MR", "FF"):
        prov = {"MO": "morphoobjects", "MR": "morphorelate", "FF": "fiberfeatures"}[col]
        v = o.get(f"mf_{prov}")
        if v is None:
            return "N/A", "no object set (no masks)"
        exp = [a for a in e["A"].get(prov, []) if a.startswith("A_")]
        ok = v.get("rc") == 0 and not v.get("fov_failures")
        if exp:
            if ok:
                return "MISMATCH-BRICK", f"accepted silently; v1 refuses {', '.join(exp)}" + (
                    f" (objects per FOV {v.get('objects_per_fov')})" if v.get("objects_per_fov") else "")
            return "MATCH", f"refused ~ {', '.join(exp)}: {v.get('tail', '')[:110]}"
        if not ok:
            return "MISMATCH-BRICK", f"refused: {v.get('tail', '')[:140]}"
        bad = chan_bad(v)
        if bad:
            return "MISMATCH-BRICK", "SILENT CHANNEL MIX-UP (canonical channel measured from another "\
                "fluorophore): " + ", ".join(bad[:4])
        nan = v.get("nan", {})
        if nan.get("total", 0) != nan.get("with_applicability_row", 0):
            return "BUG", f"unexplained NaN: {nan}"
        return "MATCH", f"measured; NaN {nan.get('total', 0)} all with applicability rows"
    if col == "ME":
        v = o.get("mf_morphoembed")
        if v is None:
            return "N/A", "no object set"
        t = v.get("tail", "")
        if "does not exist" in t:
            return "SKIP", "weights absent: refused at the checkpoint (planning passed)"
        if "rename one repeat" in t:
            return "MISMATCH-BRICK", "fitted scaling keyed by source repeat label: 'rename one repeat'"
        if "MissingMasksError" in t or "mixed calibration" in t:
            return "MATCH", "refused before the weights: " + t[:90]
        if "names the channel" in t:
            return "MISMATCH-BRICK", "canonical channel ID refused (header names are the IDs)"
        return "SKIP", t[:120]
    if col == "MC":
        v = o.get("mc")
        if v is None:
            return "N/A", "no coverage export (MorphoObjects run refused or no masks)"
        if not v.get("ok"):
            return "MISMATCH-BRICK", v.get("error", "")[:150]
        if v.get("contrast"):
            return "MATCH", "no reference: nothing compared"
        doc = tomllib.loads(e["toml"])
        want = paired_expected(doc)
        got = v.get("paired_repeats", {})
        diffs = {k: (got.get(k, "<2"), n) for k, n in want.items()
                 if (n >= 2 and got.get(k) != n) or (n < 2 and k in got)}
        if diffs:
            return "MISMATCH-BRICK", f"paired repeats (MorphoCoverage, v1): {diffs}"
        return "MATCH", (f"paired repeats as v1 ({want}); unit {v.get('unit')}; repeat_group column "
                         f"absent from the export")
    raise ValueError(col)


def main(path):
    res = json.load(open(path))
    cases = Path(path).parent / "cases"
    for cid, rec in res.items():  # the compact results keep each case's TOML in cases/
        if "toml" not in rec["expected"] and (cases / f"{cid}.toml").exists():
            rec["expected"]["toml"] = (cases / f"{cid}.toml").read_text(encoding="utf-8")
    rows, counts = [], {}
    for cid, rec in res.items():
        src = res[rec["shares_runs"]] if rec.get("shares_runs") else rec
        cells = {}
        for col in COLS:
            if (cid, col) in OVERRIDES:
                v, why = OVERRIDES[(cid, col)]
            elif rec.get("shares_runs"):
                v, why = cell(rec["shares_runs"], src, col)
                if col == "PP":
                    v, why = ("MISMATCH-BRICK", "accepted (no reader of the file today); v1 refuses "
                              + ", ".join(rec["expected"]["E"] + rec["expected"]["R"]))
                else:
                    why = f"as {rec['shares_runs']} (bricks read no description)"
            else:
                v, why = cell(cid, rec, col)
            cells[col] = (v, why)
            counts[v] = counts.get(v, 0) + 1
        rows.append((cid, rec, cells))
    print("| Case | What | Spec v1 expects | " + " | ".join(COLS) + " |")
    print("|---|---|---|" + "---|" * len(COLS))
    for cid, rec, cells in rows:
        e = rec["expected"]
        exp = e["verdict"] + (f"; {', '.join(e['W'])}" if e["W"] else "")
        a = sorted({x for v in e["A"].values() for x in v if x.startswith("A_")})
        if a:
            exp += f"; requests: {', '.join(a)}"
        print(f"| {cid} | {rec['title']} | {exp} | " +
              " | ".join(SHORT[cells[c][0]] for c in COLS) + " |")
    print("\nCounts:", json.dumps(counts))
    print("\n## Cell notes\n")
    for cid, rec, cells in rows:
        notes = [f"{c} {SHORT[v]}: {why}" for c, (v, why) in cells.items()
                 if v not in ("N/A",) and why and (v != "MATCH" or c in ("PP",))
                 and not (v == "SKIP" and why.startswith("weights absent"))]
        if notes:
            print(f"- **{cid}** " + "; ".join(n.replace("|", "/") for n in notes))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
