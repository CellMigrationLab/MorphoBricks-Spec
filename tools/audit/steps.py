"""AUDIT TOOL ONLY: one brick step of the matrix audit, run in the bricks' virtual environment.

    python steps.py STEP CASE_DIR ARGS_JSON

prints one JSON line (the observation) as its last line. Each step does what a user does with
the released brick: the preprocessing CLI (check, design, run, masks), CellPatcher's Python API
on the preprocessing run, a MorphoFeature run file with one provider, and MorphoCoverage's
condition_contrast on MorphoFeature's coverage export. Nothing here repairs or completes an
input: a refusal is recorded as it is.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

BIN = Path(sys.executable).parent
PP = str(BIN / "morphobricks-preprocessing")
MF = str(BIN / "morphofeature")
LEVEL = {"DAPI": 1000, "DNA": 1000, "ACTIN": 2000, "PAX": 3000, "PHASE": 4000, "Tub": 2600,
         "R": 60, "G": 120, "B": 180}


def sh(cmd, cwd, timeout=600):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def tail(s, n=1500):
    s = s.strip()
    return s[-n:]


def report_issues(out: Path):
    f = out / "discovery_report.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    res = []
    for i in d.get("issues", []):
        res.append(f"{i.get('severity', '?')}:{i.get('code', i.get('kind', '?'))}")
    return sorted(set(res))


def has_masks(cd: Path) -> bool:
    m = cd / "masks"
    return m.exists() and any(m.iterdir())


# ------------------------------------------------------------------ preprocessing
def pp_check(cd, a):
    cmd = [PP, "check", "exp", "--output", "out"] + (["--masks", "masks"] if has_masks(cd) else [])
    rc, o, e = sh(cmd, cd)
    m = re.search(r"--axes (\S+)", o)
    return {"rc": rc, "issues": report_issues(cd / "out"), "axes": m.group(1) if m else None,
            "type": re.search(r"Suggested image type: (\w+)", o).group(1)
            if re.search(r"Suggested image type: (\w+)", o) else None,
            "tail": tail(o + e, 900)}


def pp_design(cd, a):
    cmd = [PP, "design", "--output", "out"]
    for g in a.get("groups", []):
        cmd += ["--repeat-group", g]
    for c in a.get("controls", []):
        cmd += ["--control", c]
    cmd += ["--confirm-all"]
    rc, o, e = sh(cmd, cd)
    f = cd / "out" / "experiment_design.csv"
    return {"rc": rc, "csv": f.read_text() if f.exists() else None, "tail": tail(o + e, 900)}


def pp_run(cd, a):
    cmd = [PP, "run", "exp", "--output", "out"]
    if a.get("axes"):
        cmd += ["--axes", a["axes"]]
    if a.get("image_type"):
        cmd += ["--image-type", a["image_type"]]
    if has_masks(cd):
        cmd += ["--masks", "masks"]
    rc, o, e = sh(cmd, cd)
    man = cd / "out" / "run_manifest.json"
    files = []
    if man.exists() and rc == 0:
        d = json.loads(man.read_text())
        for f in d["files"]:
            files.append({k: f.get(k) for k in ("relative_path", "condition", "biological_repeat",
                                                "technical_repeat", "position_id", "channel_names",
                                                "channel_names_trimmed", "axes")})
        files = {"files": files, "image_type": d.get("image_type"),
                 "design_sha": d.get("experiment_design_sha256")}
    return {"rc": rc, "issues": report_issues(cd / "out"), "manifest": files or None,
            "tail": tail(o + e, 1200)}


def pp_masks(cd, a):
    rc, o, e = sh([PP, "masks", "--output", "out"], cd)
    f = cd / "out" / "mask_relationships.json"
    kinds = None
    if f.exists():
        kinds = {k: v.get("kind") for k, v in json.loads(f.read_text()).get("masks", {}).items()}
    return {"rc": rc, "kinds": kinds, "tail": tail(o + e, 600)}


# ------------------------------------------------------------------ CellPatcher
def cp(cd, a):
    import warnings

    import pandas as pd
    from cellpatcher import CellPatcherConfig, NormalizationConfig, run_patching_condition_repeat_tree

    warnings.simplefilter("ignore")
    mode = a["mode"]
    c = CellPatcherConfig(mode=mode)
    c.common.preprocessing_run = "out"
    c.common.output_dir = f"cp_{mode}"
    c.export.enabled = True
    if a.get("z_all"):
        c.common.z_policy = "all"
    if mode == "grid":
        c.grid.tile_size = 16
        c.normalization = NormalizationConfig(enabled=True, scope="biological_repeat")
    if mode == "random":
        c.random.patch_size = 8
        c.random.n_patches = 2
    if mode == "cell":
        c.cell.patch_size = 16
        c.matching.mask_type = "Cells"
        if a.get("binary_policy"):
            c.cell.binary_mask_policy = "connected_components"
    try:
        import os
        os.chdir(cd)
        run_patching_condition_repeat_tree("exp", config=c, combine_metadata=True)
    except Exception as exc:  # noqa: BLE001 - recorded
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:700]}"}
    p = Path(cd) / f"cp_{mode}" / "patches.csv"
    if not p.exists():
        return {"ok": True, "rows": 0}
    df = pd.read_csv(p, keep_default_na=False, na_values=[""])
    out = {"ok": True, "rows": len(df),
           "per_fov": df.groupby(["condition", "biological_repeat", "technical_repeat", "position_id"])
           .size().astype(int).describe().to_dict() if len(df) else {}}
    if mode == "grid" and "normalization_group" in df:
        g = df.groupby(["condition", "biological_repeat"])["normalization_group"].agg(
            lambda s: sorted(set(map(str, s))))
        out["normalization_group"] = {f"{k[0]}/{k[1]}": v for k, v in g.items()}
    if mode == "cell":
        out["labels_per_fov"] = df.groupby(["condition", "biological_repeat", "technical_repeat",
                                            "position_id"]).size().astype(int).to_dict().__repr__()[:300]
    return out


# ------------------------------------------------------------------ MorphoFeature
def mf(cd, a):
    import yaml

    prov = a["provider"]
    run = {"preprocessing_run": "out", "masks": {"Cells": "Cells"} if a["masks"] else {},
           "requests": [], "output": f"mf_{prov}", "format": "csv", "workers": 0}
    if a["masks"]:
        run["observation_units"] = {"Cells": "cell"}
    if a.get("channels_key"):
        run["channels"] = a["channels_key"]
    chans = a["channels"]
    if prov == "morphoobjects":
        if a["masks"]:
            run["requests"] += [
                {"provider": "morphoobjects", "features": ["area"], "object_set": "Cells"},
                {"provider": "morphoobjects", "feature": "mean_intensity", "object_set": "Cells",
                 "for_each_channel": chans}]
        run["patch_sets"] = {"tiles": {"mode": "grid", "side": 16}}
        run["requests"].append({"patch_set": "tiles", "id": "tile_mean", "provider": "morphoobjects",
                                "feature": "mean_intensity", "channels": [chans[0]]})
    elif prov == "morphorelate":
        run["requests"].append({"provider": "morphorelate", "feature": "mean_intensity",
                                "object_set": "Cells", "compartment": "cell",
                                "masks": {"cell": "Cells"}, "for_each_channel": chans})
    elif prov == "fiberfeatures":
        if a.get("calibrated"):
            run["bricks"] = {"fiberfeatures": {"scales": [0.5, 1.0], "sigma_in": 0.5,
                                               "preprocess_denoise_sigma": 0.5}}
        run["requests"].append({"provider": "fiberfeatures", "features": ["fa_mean"],
                                "object_set": "Cells", "for_each_channel": [chans[-1]]})
    elif prov == "morphoembed":
        run["bricks"] = {"morphoembed": {"weights_dir": str(Path(cd) / "no_weights"), "device": "cpu"}}
        run["requests"].append({"provider": "morphoembed", "feature": "efficientnet_b0_ra_in1k",
                                "object_set": "Cells", "for_each_channel": chans})
    rf = Path(cd) / f"run_{prov}.yaml"
    rf.write_text(yaml.safe_dump(run, sort_keys=False))
    verb = "check" if prov == "morphoembed" else "run"
    rc, o, e = sh([MF, verb, rf.name], cd)
    res = {"rc": rc, "tail": tail(o + e, 1000), "channels_used": chans}
    if rc == 0 and verb == "run":
        res.update(inspect_mf(Path(cd) / f"mf_{prov}"))
    return res


def inspect_mf(folder: Path):
    import pandas as pd

    out = {}
    fovs = pd.read_csv(folder / "fovs.csv", keep_default_na=False, na_values=[""])
    if "status" in fovs:
        out["fov_status"] = fovs["status"].value_counts().to_dict()
    feats = {}
    nan_total, nan_explained = 0, 0
    app = pd.read_csv(folder / "applicability.csv", keep_default_na=False, na_values=[""])
    app_keys = set()
    for r in app.itertuples(index=False):
        app_keys.add((r.condition, r.biological_repeat, r.technical_repeat, str(r.position_id),
                      str(r.label_id), r.feature))
    for f in sorted((folder / "features").rglob("*.csv")):
        df = pd.read_csv(f, keep_default_na=False, na_values=[""])
        idc = [c for c in ("condition", "biological_repeat", "technical_repeat", "position_id",
                           "label_id") if c in df]
        cols = [c for c in df.columns if "__" in c]
        for c in cols:
            nan_rows = df[df[c].isna()]
            nan_total += len(nan_rows)
            for r in nan_rows.itertuples(index=False):
                d = r._asdict()
                key = (d.get("condition"), d.get("biological_repeat"), d.get("technical_repeat"),
                       str(d.get("position_id")), str(d.get("label_id")),
                       c.split("__")[-1])
                k2 = key[:5] + (c,)
                if key in app_keys or k2 in app_keys:
                    nan_explained += 1
            if "mean_intensity" in c and "condition" in df:
                g = df.groupby(["condition", "biological_repeat"])[c].mean().round(0)
                feats[f"{f.parent.name}/{f.stem}:{c}"] = {f"{k[0]}/{k[1]}": v for k, v in g.items()}
            if c.endswith("__area") and "condition" in df:
                n = df.groupby(["condition", "biological_repeat", "technical_repeat",
                                "position_id"]).size()
                out["objects_per_fov"] = sorted(set(n.tolist()))
    out["nan"] = {"total": nan_total, "with_applicability_row": nan_explained,
                  "applicability_rows": len(app)}
    out["intensity"] = feats
    cov = folder / "coverage"
    if cov.exists():
        out["coverage"] = {p.name: json.loads((p / "coverage.json").read_text()).get("exported", True)
                           for p in cov.iterdir() if (p / "coverage.json").exists()}
        rec = {p.name: json.loads((p / "coverage.json").read_text()).get("reason")
               for p in cov.iterdir() if (p / "coverage.json").exists()}
        out["coverage_reason"] = {k: v for k, v in rec.items() if v}
    man = json.loads((folder / "run_manifest.json").read_text())
    inputs = man.get("inputs", {})
    out["provenance"] = sorted(inputs.keys()) if isinstance(inputs, dict) else str(inputs)[:200]
    return out


# ------------------------------------------------------------------ MorphoCoverage
def mc(cd, a):
    import warnings

    import pandas as pd
    from morphocoverage.feature_tables import attach_feature_tables
    from morphocoverage.sampling_unit import condition_contrast
    from morphofeature.coverage_inputs import load_coverage_inputs

    warnings.simplefilter("ignore")
    folder = Path(cd) / "mf_morphoobjects"
    try:
        objects, fovs, tables, unit = load_coverage_inputs(folder, "Cells")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "load", "error": f"{type(exc).__name__}: {str(exc)[:500]}"}
    out = {"fov_columns": list(fovs.columns), "repeat_group_column": "repeat_group" in fovs.columns,
           "target_column": "target" in fovs.columns}
    try:
        ft = attach_feature_tables(objects, fovs, tables)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "attach", "error": f"{type(exc).__name__}: {str(exc)[:500]}", **out}
    obj = ft.objects
    feature = "Cells__area"
    comps = [tuple(x) for x in a["comparisons"]]
    if not comps:
        out["contrast"] = "no reference declared: nothing to compare"
        return {"ok": True, **out}
    kw = {}
    if a.get("targets"):
        fovs = fovs.assign(target=fovs["condition"].map(a["targets"]))
        kw["target_col"] = "target"
    try:
        r = condition_contrast(obj, fovs, feature=feature, comparisons=comps, n_permutations=50,
                               n_draws=10, cell_test=False, **kw)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stage": "contrast", "error": f"{type(exc).__name__}: {str(exc)[:600]}",
                **out}
    rep = r.repeats
    out["ok"] = True
    out["unit"] = r.settings.get("unit")
    out["unit_note"] = r.settings.get("unit_note")
    out["paired_repeats"] = ({str(k): int(v) for k, v in zip(rep["condition"], rep["repeats"])}
                             if len(rep) and "repeats" in rep else {})
    out["control_only_repeats"] = r.settings.get("control_only_repeats")
    out["reason"] = r.settings.get("reason")
    if a.get("targets"):
        out["targets_table"] = r.targets.to_dict("records") if len(r.targets) else []
    if a.get("contrast_table"):
        try:
            t = pd.DataFrame([{"kind": "own_control", "condition": c, "reference": ref}
                              for c, ref in comps])
            r2 = condition_contrast(obj, fovs, feature=feature, contrasts=t, n_permutations=50,
                                    n_draws=10, cell_test=False)
            out["own_control_table"] = "accepted: " + str(len(r2.repeats)) + " rows"
        except Exception as exc:  # noqa: BLE001
            out["own_control_table"] = f"refused: {type(exc).__name__}: {str(exc)[:300]}"
    return out


STEPS = {"pp_check": pp_check, "pp_design": pp_design, "pp_run": pp_run, "pp_masks": pp_masks,
         "cp": cp, "mf": mf, "mc": mc}

if __name__ == "__main__":
    step, cd, args = sys.argv[1], Path(sys.argv[2]), json.loads(sys.argv[3])
    try:
        res = STEPS[step](cd, args)
    except Exception as exc:  # noqa: BLE001 - an audit records every failure
        res = {"crash": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-1500:]}
    print(json.dumps(res, default=str, ensure_ascii=False))
