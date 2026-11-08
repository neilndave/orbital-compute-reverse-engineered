"""SPIN1 item 3c (reconstructed generator for MMOD_TRUNK_ALLOC_SPIN1.json): trunk SPF wall x standoff grid at PNP 0.95/0.99, flux x1/x3,
and best header N within (allocation - trunk P0.95_flux1)."""
import json, sys
sys.path.insert(0, "/tmp/gtcfc_root/inputs/repo/src")
import mmod_spin1 as MM, mmod_grid_spin1 as G
ALLOC = {"June": 80.0, "August": 140.0}
CASES = {"June": dict(npan=77, ncol=8, trunk_bore_m=24.1656e-3), "August": dict(npan=128, ncol=13, trunk_bore_m=31.1977e-3)}
TW = (0.8, 1.2, 1.6, 2.0, 2.5, 3.0)            # trunk wall grid (as used in spin1)
TWH = (0.8, 1.2, 1.6, 2.0, 2.5, 3.0, 4.0)      # header grid = mmod_grid_spin1
out = {}
for nm, c in CASES.items():
    cc = dict(c, routing="ledger"); tt = G.trunk_tubes(cc); R = {}
    for Pt in (0.95, 0.99):
        for fm in (1.0, 3.0):
            rows = [G.evalc(tt, tw, S, fm) for tw in TW for S in range(0, 151, 5)]
            ok = [x for x in rows if x["PNP"] >= Pt]; R[f"P{Pt}_flux{fm:g}"] = min(ok, key=lambda x: x["total_kg"]) if ok else None
    budget = ALLOC[nm] - R["P0.95_flux1"]["total_kg"]
    grid = [G.evalc(G.hdr_tubes(cc), tw, S) for tw in TWH for S in (0, 5, 10, 15, 20, 30, 40, 60)]
    ok = [x for x in grid if x["total_kg"] <= budget]; best = min(ok, key=lambda x: x["N_5yr"]); best = dict(best, budget_kg=budget)
    R["header_best_N_within_allocation"] = best; out[nm] = R
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "MMOD_TRUNK_ALLOC_SPIN1.json", "w"), indent=1, default=float)
