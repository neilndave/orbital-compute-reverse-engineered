# t434: C1-to-C2 region (rack kg/kW vs wing W/kg) + 6 replica design points (C1, MID, C2 x Jun8/Aug4).  Box only. ESTIMATE unless tagged.
# Reuses t423g.build()/solve() unchanged (exec of t423g.py up to its OUT = {} line).  Writes results/t434_region.json and gtc_params/point_*.json
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
src = open(os.path.join(HERE, "t423g.py")).read().split("OUT = {}; ")[0]
ns = {"__file__": os.path.join(HERE, "t423g.py")}; exec(src, ns)
build, solve, CAND, wing, O = [ns[k] for k in ("build", "solve", "CAND", "wing", "O")]
c1 = {k: v for k, v in CAND["C1_margin_forward"].items() if k != "desc"}; c2 = {k: v for k, v in CAND["C2_compute_limited"].items() if k != "desc"}
# MID = arithmetic mean of C1 and C2 knob values (pump_spares 1.5 -> 2, ASSUMED rounding up = conservative)
mid = dict(n=(c1["n"] + c2["n"]) / 2, f_struct=(c1["f_struct"] + c2["f_struct"]) / 2, pcdu=(c1["pcdu"] + c2["pcdu"]) / 2, pump_spares=2,
           rack_spare=(c1["rack_spare"] + c2["rack_spare"]) / 2, growth=(c1["growth"] + c2["growth"]) / 2)
SETS = {"C1": c1, "MID": mid, "C2": c2}
NS = [0.25, 0.30, 0.35, 0.425, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.6, 2.2, 3.0]
res = {"sets": SETS, "iso": {}, "points": {}}
for b in ("Jun8", "Aug4"):
    for nm, kn in SETS.items():
        pts = []
        for n in NS:
            kw = {**kn, "n": n}; k = solve(b, **kw)
            if k is not None: pts.append((wing(n), k, n))
        res["iso"][f"{b}|{nm}"] = pts
        kw = dict(kn); k = solve(b, **kw); r = build(b, k_rack=k, **kw)
        r["lines"] = {a: round(v, 2) for a, v in r["lines"].items()}; r = {a: v for a, v in r.items() if a != "o"}
        r["knobs"] = kw; r["k_rack_solved"] = k; res["points"][f"{b}|{nm}"] = r
        print(b, nm, "k_rack", round(k, 3), "wing", round(r["wing"], 1), "M", round(r["M"], 1), "kwt", round(r["kwt"], 2), "N98", r["N98"], "A_rad", round(r["A_rad"], 2), "A_arr", round(r["A_arr"], 1), r["fcc"], flush=True)
json.dump(res, open(os.path.join(HERE, "results/t434_region.json"), "w"), indent=1, default=float)
