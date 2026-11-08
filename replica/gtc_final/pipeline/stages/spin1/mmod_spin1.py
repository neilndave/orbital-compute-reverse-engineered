"""SPIN1 item 3: header/trunk MMOD protection screen on the GTC scoped baseline (no render change). Box CPU.
Flux: inherited repo rack_two_skies.mmod_env (NASA90 debris + Gruen 1985 meteoroids, SPENVIS forms; repo itself labels NASA90 OUTDATED, ORDEM/MASTER not run),
same orbit/epoch convention as c21_bumper.py (600 km, i 97.6 deg, year 2030, F10.7 index 1.5 -> S=150 in NASA90 convention as used by the repo, 5 yr),
debris 2.8 g/cc at 10 km/s, meteoroids at 20 km/s with Gruen density iteration, normal incidence.
Exposure convention (repo, conservative): impacts = flux x total exposed surface area (pi*d_out*L for tubes).
BLEs: Whipple = Christiansen NNO hypervelocity form (NASA JSC 'Whipple shield sizing equations', NTRS 19920010826; Christiansen NASA/TP-2003-210788):
   d_c = 3.918 t_w^(2/3) S^(1/3) rho_p^(-1/3) rho_b^(-1/9) (V cos th)^(-2/3) (sigma/70)^(1/3)   [cm, g/cc, km/s, ksi]
   bumper sizing t_b = c_b d_c rho_p/rho_b, c_b = 0.25 (S/d < 30) -> applied at the debris design d_c, floor 0.5 mm (repo min gauge, ASSUMED)
 Single wall (unprotected / thick-wall armour): repo Cour-Palais thin-plate d_lim_cm (K1 0.44).
Geometry: inherited c13 header model used for the baseline coolant mass: supply taper 20->10 mm (10 segments), return (9 segments), segment = LS 2.9486 m per panel, wall 0.8 mm Al;
 central trunks: 4 lines x 2.05 m (CT.cool run_scale 0.5), bore from CT.cool diag; root flex hoses: ASSUMED 2 x 1.0 m per column at 20 mm bore.
 Header routing in the render is NOT verified; a short-edge routing sensitivity (0.7264 m header per panel = 2 x panel width) is reported."""
import sys, os, json, math, numpy as np
sys.path.insert(0, "/tmp/gtcfc_root/inputs/repo/src")
from rack_two_skies.mmod_env import nasa90, gruen, earth_factor, rho_met, d_lim_cm
H, INC, YR, S10, LIFE = 600.0, 97.6, 2030, 1.5, 5.0
RHO_AL = 2.7; SIG_KSI = 241.0 / 6.895; WALL_CM = 0.08
LS = 2.9446 + 0.004; PW = 0.3634175776637853
def taper(droot, n, dmin):
    s = [max(dmin, droot * math.sqrt((n - k) / n)) for k in range(n)]; r = [max(dmin, droot * math.sqrt((k + 1) / n)) for k in range(n - 1)]; return s, r
def dc_whipple(tw_cm, S_cm, rho_p, V, sig=SIG_KSI):
    return 3.918 * tw_cm ** (2 / 3) * S_cm ** (1 / 3) * rho_p ** (-1 / 3) * RHO_AL ** (-1 / 9) * V ** (-2 / 3) * (sig / 70.0) ** (1 / 3)
def flux_total(dfun, flux_mult=1.0):
    d = dfun(2.8, 10.0); fd = nasa90(d, H, INC, YR, S10) * flux_mult; rho = 1.0
    for _ in range(30):
        dm = dfun(rho, 20.0); m = rho * math.pi / 6 * dm ** 3; rho = rho_met(m)
    fm = gruen(m) * earth_factor(H); return fd + fm, d, dm, fd, fm
def tubes(case):
    """list of (outer diameter m, length m) per spacecraft"""
    npan, ncol, trunk_bore = case["npan"], case["ncol"], case["trunk_bore_m"]; out = []
    s, r = taper(20e-3, 10, 10e-3)
    if case.get("routing", "ledger") == "ledger":
        for d in s + r: out.append((d + 2 * WALL_CM / 100, LS * npan / 10))
    else:
        for d in s + r: out.append((d + 2 * WALL_CM / 100, 2 * PW * npan / 19))
    out.append((trunk_bore + 2 * WALL_CM / 100, 4 * 2.05)); out.append((20e-3 + 2 * WALL_CM / 100, 2 * 1.0 * ncol))
    return out
def area(tb): return sum(math.pi * d * L for d, L in tb)
def unprotected(case, fm=1.0):
    tb = tubes(case); N, d, dm, fd, fme = flux_total(lambda rp, V: d_lim_cm(WALL_CM, rp, V), fm); A = area(tb); n = N * A * LIFE
    return dict(A_exposed_m2=A, d_crit_debris_mm=d * 10, d_crit_met_mm=dm * 10, N_5yr=n, PNP_5yr=math.exp(-n))
def whipple_case(case, Pt, S_mm, fm=1.0):
    tb = tubes(case); S = S_mm / 10.0
    N, d, dm, fd, fme = flux_total(lambda rp, V: dc_whipple(WALL_CM, S, rp, V), fm); A = area(tb); n = N * A * LIFE
    t_b_mm = max(0.5, 0.25 * d * 2.8 / RHO_AL * 10.0)
    A_b = sum(math.pi * (dd + 2 * S_mm / 1000.0) * L for dd, L in tb); mass = A_b * t_b_mm / 1000.0 * 2700.0
    sup = 0.10 * mass   # standoff ribs/clips: ASSUMED 10 % of bumper sheet mass
    return dict(S_mm=S_mm, t_b_mm=t_b_mm, d_c_debris_mm=d * 10, d_c_met_mm=dm * 10, N_5yr=n, PNP_5yr=math.exp(-n), bumper_area_m2=A_b, bumper_sheet_kg=mass, supports_kg=sup, total_kg=mass + sup, meets=math.exp(-n) >= Pt)
def armour_case(case, Pt, fm=1.0):
    """increase header/trunk wall (Al) until single-wall PNP >= Pt; mass = added wall only."""
    tb = tubes(case); A = area(tb)
    for t_mm in np.arange(0.8, 12.01, 0.05):
        N, d, dm, fd, fme = flux_total(lambda rp, V, t=t_mm / 10: d_lim_cm(t, rp, V), fm); n = N * A * LIFE
        if math.exp(-n) >= Pt:
            add = sum(math.pi * (dd + (t_mm - 0.8) / 1000.0) * L * (t_mm - 0.8) / 1000.0 * 2700.0 for dd, L in tb)
            return dict(wall_mm=float(t_mm), PNP_5yr=math.exp(-n), added_kg=add, d_crit_debris_mm=d * 10)
    return dict(wall_mm=None, PNP_5yr=None, added_kg=float("inf"))
def block_fraction(h_m, W=PW, edges=2):
    """fraction of one fin face's hemispherical view blocked by a ridge of height h at each long edge of a strip of width W (2-D, exact for an
    infinitely long ridge): per edge  F = [W + h - sqrt(W^2+h^2)] / (2W)."""
    return edges * (W + h_m - math.sqrt(W * W + h_m * h_m)) / (2 * W)
def optimise(case, Pt, fm=1.0):
    best = None; rows = []
    for S_mm in np.arange(5.0, 100.01, 1.0):
        r = whipple_case(case, Pt, float(S_mm), fm); rows.append(r)
        if r["meets"] and (best is None or r["total_kg"] < best["total_kg"]): best = r
    return best, rows
if __name__ == "__main__":
    base = json.load(open("/tmp/gtcfc_root/stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"))
    CASES = {"June": dict(npan=77, ncol=8, trunk_bore_m=24.1656e-3), "August": dict(npan=128, ncol=13, trunk_bore_m=31.1977e-3)}
    out = dict(method=__doc__, cases={})
    for nm, c in CASES.items():
        R = {}
        for routing in ("ledger", "short_edge"):
            cc = dict(c, routing=routing); RR = dict(tubes=[(round(d, 5), round(L, 3)) for d, L in tubes(cc)], unprotected=unprotected(cc), unprotected_flux_x3=unprotected(cc, 3.0))
            for Pt in (0.90, 0.95, 0.99):
                for fm in (1.0, 3.0):
                    b, rows = optimise(cc, Pt, fm); RR[f"whipple_opt_P{Pt}_flux{fm:g}"] = b
                    RR[f"armour_P{Pt}_flux{fm:g}"] = armour_case(cc, Pt, fm)
            for S_mm in (10.0, 15.0, 20.0):
                RR[f"whipple_S{S_mm:g}_P0.95"] = whipple_case(cc, 0.95, S_mm)
            R[routing] = RR
        out["cases"][nm] = R
    # header ridge view blockage for the ledger routing (header along both long edges of each 0.3634 m strip; mean header OD)
    s, r = taper(20e-3, 10, 10e-3); dmean = np.mean([d + 1.6e-3 for d in s + r])
    out["header_mean_OD_m"] = float(dmean)
    out["blockage_examples"] = {f"h_{h*1000:.0f}mm": block_fraction(h) for h in (dmean / 2, dmean / 2 + 0.005, dmean / 2 + 0.010, dmean / 2 + 0.020, dmean / 2 + 0.040)}
    json.dump(out, open("MMOD_SPIN1.json", "w"), indent=1, default=float)
    for nm in out["cases"]:
        for rt in ("ledger", "short_edge"):
            R = out["cases"][nm][rt]; print(nm, rt, "unprot", {k: round(v, 4) for k, v in R["unprotected"].items()})
            for k in R:
                if k.startswith(("whipple_opt", "armour", "whipple_S")): print("  ", k, {a: (round(v, 4) if isinstance(v, float) else v) for a, v in (R[k] or {}).items()})
    print("dmean", dmean, out["blockage_examples"])
