#!/usr/bin/env python3
"""Merge per-class stage plans into stage_plan_Aug30.json.  Satellites with identical pack signature (same column/array/pod pack poses and stowed rotation) share one plan:
Aug classes (checked on the box with fleet_kin): {0-19}, {20,21}, {22,23}, {24,25,26}, {27,28}, {29}.  usage: merge_stage_plans.py out.json plan_c0.json plan_c20.json ..."""
import json, sys, copy
CL = {0: range(0, 20), 20: (20, 21), 22: (22, 23), 24: (24, 25, 26), 27: (27, 28), 29: (29,)}
out = {}
for p in sys.argv[2:]:
    d = json.load(open(p))
    for k, v in d.items():
        for m in CL[int(k)]:
            w = copy.deepcopy(v); w["sat"] = m; out[str(m)] = w
assert sorted(map(int, out)) == list(range(30)), sorted(map(int, out))
json.dump(out, open(sys.argv[1], "w"))
print("merged", len(out), "satellites; t_ready max", max(v["t_ready"] for v in out.values()))
