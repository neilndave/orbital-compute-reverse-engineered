#!/usr/bin/env python3
"""Reads the derisk result JSONs and prints PASS/FAIL per gate item.  usage: check_gate.py <WORK dir with newton_array results>   (box-done items are read from ./derisk)"""
import json, glob, pathlib, sys
H = pathlib.Path(__file__).resolve().parent; W = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else H / "work"
def j(p): return json.load(open(p))
print("(b) panel FEA :", end=" "); f = j(H / "derisk/fea_panel_disp.json"); print("max_axial", f["max_axial"], "clearance_mm", f["clearance_mm"])
print("(c) stack f1  : derisk/stack_stiffness.json (t440). Untied 6.9/3.3 Hz (Jun), 7.0/3.4 Hz (Aug). With bay-wall ties every 3 levels: Jun 25.4/>58 Hz (rigid wall; 24.8 at 10x compliance, 23.4 at 3x), Aug 33.3 Hz. vs Falcon guide 25/10 Hz (STATEMENT) applied to Starship (ASSUMED). Needs tie anchors on the bay wall (ASSUMED free).")
bl = j(H / "derisk/blanket_check.json"); print("(a2) blanket strain check (box):", {k: bl[k] for k in ("pitch_6.0mm", "verdict_rule")})
ok = True; nfound = 0
for B, n in (("Jun", 5), ("Aug", 6)):
    for p in sorted(glob.glob(str(W / f"**/wfold_n{n}_w*.json"), recursive=True)):
        nfound += 1; r = j(p); keys = ("t_all_latched", "peak_latch_torque", "sync_err", "bus_rate", "bus_yaw")
        print(f"(a) {B} n={n} {pathlib.Path(p).name}:", {k: r.get(k) for k in keys if k in r} or list(r)[:8])
        if r.get("t_all_latched") is None: ok = False
print("(a) Newton fold chain:", "latched in all runs found" if (ok and nfound >= 6) else "MISSING or NOT latched -> FAIL")
