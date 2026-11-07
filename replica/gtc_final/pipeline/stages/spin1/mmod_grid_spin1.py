"""SPIN1 item 3b: header wall x Whipple standoff grid (same flux/BLE/geometry as mmod_spin1.py) + single-point-failure trunk Whipple.
Header wall growth mass = added Al wall; bumper = full wrap pi(d_out+2S)L x t_b, t_b = max(0.5 mm, 0.25 d_c rho_p/rho_b); supports +10 % (ASSUMED).
View blockage: ridge height h = d_out/2 + S (+ t_b) on BOTH long edges of each 0.3634 m strip for ledger routing; for short-edge routing ridge on both
short ends of the 2.9446 m panel (strip width 2.9446 m). Incremental blockage = blockage(h) - blockage(d_out/2) (bare header already modelled? NO -> the baseline view model
ignores headers; we report incremental vs bare header and treat the bare-header ridge as an existing unmodelled effect)."""
import json, math, numpy as np
import mmod_spin1 as MM
from rack_two_skies.mmod_env import d_lim_cm
def hdr_tubes(c): return MM.tubes(c)[:-2]
def trunk_tubes(c): return [MM.tubes(c)[-2]]
def evalc(tb, tw_mm, S_mm, fm=1.0):
    tw = tw_mm / 10.0
    if S_mm <= 0:
        N, d, dm, fd, fme = MM.flux_total(lambda rp, V: d_lim_cm(tw, rp, V), fm); tb_mm = 0.0; dc = d
    else:
        N, d, dm, fd, fme = MM.flux_total(lambda rp, V: MM.dc_whipple(tw, S_mm / 10.0, rp, V), fm); tb_mm = max(0.5, 0.25 * d * 2.8 / MM.RHO_AL * 10.0); dc = d
    A = sum(math.pi * (dd + 2 * (tw_mm - 0.8) / 1000) * L for dd, L in tb); n = N * A * MM.LIFE
    wall_add = sum(math.pi * (dd + (tw_mm - 0.8) / 1000) * L * (tw_mm - 0.8) / 1000 * 2700 for dd, L in tb)
    bump = sum(math.pi * (dd + 2 * (tw_mm - 0.8) / 1000 + 2 * S_mm / 1000) * L for dd, L in tb) * tb_mm / 1000 * 2700 * 1.10 if S_mm > 0 else 0.0
    return dict(tw_mm=tw_mm, S_mm=S_mm, t_b_mm=tb_mm, d_c_debris_mm=dc * 10, N_5yr=n, PNP=math.exp(-n), wall_add_kg=wall_add, bumper_kg=bump, total_kg=wall_add + bump)
def blk(h, W): return 2 * (W + h - math.sqrt(W * W + h * h)) / (2 * W)
if __name__ == "__main__":
    CASES = {"June": dict(npan=77, ncol=8, trunk_bore_m=24.1656e-3), "August": dict(npan=128, ncol=13, trunk_bore_m=31.1977e-3)}
    s, r = MM.taper(20e-3, 10, 10e-3); dmean = float(np.mean([d + 1.6e-3 for d in s + r])); out = dict(doc=__doc__, header_mean_OD_m=dmean, cases={})
    for nm, c in CASES.items():
        R = {}
        for rt, W in (("ledger", MM.PW), ("short_edge", 2.9446)):
            cc = dict(c, routing=rt); tb = hdr_tubes(cc); rows = []
            for tw in (0.8, 1.2, 1.6, 2.0, 2.5, 3.0, 4.0):
                for S in (0, 5, 10, 15, 20, 30, 40, 60):
                    e = evalc(tb, tw, S); h0 = dmean / 2; h = dmean / 2 + (tw - 0.8) / 1000 + (S + e["t_b_mm"]) / 1000 if S > 0 else dmean / 2 + (tw - 0.8) / 1000
                    e["blockage_incremental_frac"] = blk(h, W) - blk(h0, W); e["blockage_bare_header_frac_unmodelled"] = blk(h0, W); rows.append(e)
            R[rt] = dict(grid=rows)
            for Nt in (1.0, 0.5, 0.1):
                ok = [x for x in rows if x["N_5yr"] <= Nt]; R[rt][f"min_mass_N<={Nt}"] = min(ok, key=lambda x: x["total_kg"]) if ok else None
                ok2 = [x for x in ok if x["blockage_incremental_frac"] <= 0.005]; R[rt][f"min_mass_N<={Nt}_blk<=0.5%"] = min(ok2, key=lambda x: x["total_kg"]) if ok2 else None
        # single-point-failure trunks (bus side, no fin view): Whipple, wall 0.8 mm, sweep S
        tt = trunk_tubes(dict(c, routing="ledger")); trows = [evalc(tt, 0.8, S) for S in range(0, 151, 5)]
        R["trunk_SPF"] = dict(tubes=tt, rows=trows)
        for Pt in (0.95, 0.99):
            ok = [x for x in trows if x["PNP"] >= Pt]; R["trunk_SPF"][f"min_mass_P{Pt}"] = min(ok, key=lambda x: x["total_kg"]) if ok else None
            ok3 = [x for x in trows if (x["S_mm"] > 0 and evalc(tt, 0.8, x["S_mm"], 3.0)["PNP"] >= Pt)]; R["trunk_SPF"][f"min_mass_P{Pt}_flux_x3"] = min(ok3, key=lambda x: x["total_kg"]) if ok3 else None
        out["cases"][nm] = R
    json.dump(out, open("MMOD_GRID_SPIN1.json", "w"), indent=1, default=float)
    for nm, R in out["cases"].items():
        for rt in ("ledger", "short_edge"):
            for k, v in R[rt].items():
                if k.startswith("min"): print(nm, rt, k, None if v is None else {a: round(b, 4) for a, b in v.items()})
        for k, v in R["trunk_SPF"].items():
            if k.startswith("min"): print(nm, "trunk", k, None if v is None else {a: round(b, 4) for a, b in v.items()})
