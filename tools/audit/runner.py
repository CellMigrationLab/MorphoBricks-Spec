"""AUDIT TOOL ONLY: run every matrix case through the released bricks and record the result.

    python runner.py VENV_PYTHON WORK_DIR RESULTS_JSON [CASE_ID ...]

For each case of matrix.py: write its dataset under WORK_DIR/<case>, write the expected
`morphobricks.toml` beside it, run the bricks as a user would (steps.py, in the bricks'
environment), record every observation, then delete the dataset. Results are merged into
RESULTS_JSON (one entry per case), so the run can be resumed. Not a runtime package.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import matrix

HERE = Path(__file__).resolve().parent


def step(py, name, cd, args, timeout=900):
    t = time.time()
    try:
        p = subprocess.run([py, str(HERE / "steps.py"), name, str(cd), json.dumps(args)],
                           capture_output=True, text=True, timeout=timeout)
        line = (p.stdout.strip().splitlines() or ["{}"])[-1]
        try:
            res = json.loads(line)
        except json.JSONDecodeError:
            res = {"crash": "no JSON", "stdout": p.stdout[-800:], "stderr": p.stderr[-800:]}
    except subprocess.TimeoutExpired:
        res = {"crash": "timeout"}
    res["seconds"] = round(time.time() - t, 1)
    return res


def run_case(py, work: Path, case: matrix.Case) -> dict:
    exp = matrix.expected(case)
    rec = {"title": case.title, "dims": case.dims, "expected": exp, "obs": {}}
    if case.shares_runs:
        rec["shares_runs"] = case.shares_runs
        return rec
    cd = work / case.cid
    if cd.exists():
        shutil.rmtree(cd)
    matrix.write_dataset(case, cd)
    if exp.get("toml"):
        (cd / "morphobricks.toml").write_text(exp["toml"], encoding="utf-8")
    obs = rec["obs"]
    obs["pp_check"] = step(py, "pp_check", cd, {})
    doc = matrix.model(case)
    folder_of = {cid: c["source_folder"] for cid, c in doc["conditions"].items()}
    groups = [f"{c}/{r}={g}" for (c, r), g in case.groups.items()]
    controls = sorted({folder_of.get(ref, ref) for ref in case.references.values()})
    obs["pp_design"] = step(py, "pp_design", cd, {"groups": groups, "controls": controls})
    rgb = any(i.axes == "YXS" for i in case.images)
    obs["pp_run"] = step(py, "pp_run", cd, {"axes": obs["pp_check"].get("axes"),
                                            "image_type": "rgb" if rgb else "fluorescence"})
    if obs["pp_run"].get("rc") != 0:
        shutil.rmtree(cd)
        return rec
    with_masks = any(i.mask != "none" for i in case.images)
    if with_masks:
        obs["pp_masks"] = step(py, "pp_masks", cd, {})
    t_all = any(i.axes in ("TCYX",) for i in case.images)
    for mode in ("grid", "random", "whole_fov") + (("cell",) if with_masks else ()):
        obs[f"cp_{mode}"] = step(py, "cp", cd, {"mode": mode, "t_all": t_all,
                                                "binary_policy": case.cp_binary_policy})
    first = case.images[0]
    canon = list(dict.fromkeys(first.chans))
    named = first.hdr is not None
    all_ch = list(doc["channels"])
    base_args = {"masks": with_masks, "channels": all_ch,
                 "channels_key": None if named else canon,
                 "calibrated": any(i.phys for i in case.images),
                 "nan_probe": any(i.mask == "tiny" for i in case.images)}
    provs = ["morphoobjects"] + (["morphorelate", "fiberfeatures", "morphoembed"] if with_masks else [])
    for prov in provs:
        r = step(py, "mf", cd, {**base_args, "provider": prov})
        obs[f"mf_{prov}"] = r
        recorded = None
        man = obs["pp_run"].get("manifest") or {}
        if man.get("files"):
            recorded = [n for n in (man["files"][0].get("channel_names") or []) if n]
        if r.get("rc") not in (0, None) and prov != "morphoembed" and recorded and \
                recorded != all_ch and "channel" in r.get("tail", "").lower():
            # what today's brick needs: the recorded header names as channel identities
            r2 = step(py, "mf", cd, {**base_args, "provider": prov, "channels": recorded})
            obs[f"mf_{prov}_with_header_names"] = r2
    if obs.get("mf_morphoobjects", {}).get("rc") == 0 and with_masks:
        comps = [[c, ref] for c, ref in case.references.items()]
        tmap = {folder_of.get(c, c): t for c, t in case.targets.items()}
        obs["mc"] = step(py, "mc", cd, {"comparisons": comps, "targets": tmap,
                                        "contrast_table": bool(comps)})
        if any(folder_of.get(c, c) != c for c in folder_of):
            comps_f = [[folder_of.get(c, c), folder_of.get(ref, ref)] for c, ref in case.references.items()]
            obs["mc_by_folder_label"] = step(py, "mc", cd, {"comparisons": comps_f, "targets": tmap})
    shutil.rmtree(cd)
    return rec


def main(argv):
    py, work, out = argv[0], Path(argv[1]), Path(argv[2])
    only = set(argv[3:])
    work.mkdir(parents=True, exist_ok=True)
    results = json.loads(out.read_text()) if out.exists() else {}
    for case in matrix.cases():
        if only and case.cid not in only:
            continue
        t = time.time()
        results[case.cid] = run_case(py, work, case)
        results[case.cid]["seconds"] = round(time.time() - t, 1)
        out.write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str))
        print(case.cid, results[case.cid]["seconds"], "s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
