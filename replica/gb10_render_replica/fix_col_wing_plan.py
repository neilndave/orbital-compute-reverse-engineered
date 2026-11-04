#!/usr/bin/env python3
"""[t441] col_wing fix: delay the staging moves of named bodies by fixed amounts (t0 and t1 both shift, duration kept), in every sat of a stage-plan JSON.  Default = the Aug fix:  col1_00 +1.0 s,  plates1 +0.37 s,  pod +0.40 s.
CAUSE (INFERENCE from 0.02 s scans of the clearance checker): the planner treats each wing array as a RIGID block, but fleet_kin width-folds it (tau 13-27 s) while the satellite is still being staged.  Two brief transients result (own-sat col_wing):
  (1) tau ~19.7-19.9 s, -61 mm (-48.7 mm at 0.1 s sampling): the half-open plate stack sweeps into col1_00 (moving 17.6->30.9 s);   fix: col1_00 +1.0 s (working range +0.5..+1.25).
  (2) tau ~18.42-18.46 s (0.04 s wide, -19.9 mm): col1_02 vs the wing-1 plates (plates1 starts 16.75 s);  fix: plates1 +0.37 s (>= ~0.33 clears it), which in turn needs pod +0.40 s (pod_own: plates1 later moves the plate stack into the pod at tau ~21 and ~28.8; pod window ~+0.35..+0.42).
All three shifts together pass the 0.02 s scan of tau 0-75 s with every category > 0 (margins in the t441 report).  The windows are NARROW (tens of ms): re-run the 0.02 s scan after ANY change to the planner, layout or width-fold timing.
usage: fix_col_wing_plan.py IN.json OUT.json [name=shift ...]   (IN is never modified; IN must be an ORIGINAL plan, the .bak_t441 file)"""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
sh = dict(a.split("=") for a in sys.argv[3:]) or {"col1_00": 1.0, "plates1": 0.37, "pod": 0.40}; sh = {k: float(v) for k, v in sh.items()}
d = json.load(open(src)); n = 0
for k, v in d.items():
    assert not v.get("info", {}).get("col_wing_shift_t441") and not v.get("info", {}).get("col1_00_shift_t441"), "already fixed: start from the .bak_t441 original"
    for b in v["bodies"]:
        if b["name"] in sh: b["t0"] += sh[b["name"]]; b["t1"] += sh[b["name"]]; n += 1
    v["t_ready"] = max(v["t_ready"], max(b["t1"] for b in v["bodies"]))
    v.setdefault("info", {})["col_wing_shift_t441"] = sh
json.dump(d, open(dst, "w")); print(f"shifted {sh}: {n} bodies in {len(d)} sat plans -> {dst}")
