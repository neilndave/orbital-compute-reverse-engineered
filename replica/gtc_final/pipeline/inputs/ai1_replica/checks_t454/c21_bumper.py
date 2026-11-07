"""t456 bumper: (a) repo Whipple at 1 mm S resolution for P>=0.90 (exact exp(-N), checked vs Warp Poisson MC); (b) NASA Nextel/Kevlar stuffed-Whipple BLE (Christiansen NASA/TP-2003-210788 HV eq 4-19; design eqs c_b=0.15, c_NK=0.23) in the same flux model; shield sized
by the design equations at the BLE critical diameter, strip geometry as repo (strip width = tube + 2 S tan30; stuffing strip at S/2).  Standoff hardware: ASSUMED placeholder, reported separately.  ESTIMATE."""
import sys, json, math, numpy as np
sys.path.insert(0, "/tmp/gtcfc_root/inputs/repo/src")
import rack_two_skies.mmod_env as M
from rack_two_skies.mmod_env import nasa90, gruen, earth_factor, rho_met, d_lim_whipple_cm
LM = 2.944557955166043; TW = 6.094e-3; PW = 0.3634176; NT = 4; H, INC, YR, S10 = 600.0, 97.6, 2030, 1.5
import os
WORST = os.environ.get('WORST','0') == '1'
SIG = M.SIGMA_BACK_MPA; sigp = (SIG / 6.895) / 40.0     # rear-wall yield, normalised to 40 ksi (ASSUMED: same back-wall yield the repo uses)
RHO_W, T_W = 2.7, 0.157                                    # g/cm3, cm (tube wall 1.57 mm, repo)
def d_sw(rho_p, V, S_cm):   # HV stuffed Whipple, normal incidence (V>=6.5 km/s holds for both debris 10 and meteoroid 20)
    return 0.6 * (T_W * RHO_W) ** (1 / 3) * rho_p ** (-1 / 3) * V ** (-1 / 3) * S_cm ** (2 / 3) * sigp ** (1 / 6)
def flux_N(dfun, npan, S_mm):
    A = NT * TW * LM * npan * 2
    d = dfun(2.8, 10.0); fd = nasa90(d, H, INC, YR, S10); best = None
    for rho0 in ((1.0, 0.5) if WORST else (1.0,)):
        rho = rho0
        for _ in range(20):
            dm = dfun(rho, 20.0); m = rho * math.pi / 6 * dm ** 3; rho = rho_met(m)
        fm = gruen(m) * earth_factor(H); N = (fd + fm) * A * 5.0
        if best is None or N > best[0]: best = (N, d, dm, rho)
    return best
def strip(S_mm, frac=1.0): return min(TW + 2 * frac * S_mm * 1e-3 * math.tan(math.radians(30.0)), PW / 4)
def run(npan):
    out = dict(whipple=[], stuffed=[])
    for S in np.arange(20, 121, 1.0):
        N, d, dm, _ = flux_N(lambda rp, V: d_lim_whipple_cm(0.157, S / 10, rp, V) * 0 + d_lim_whipple_cm(0.157, S / 10, rp, V), npan, S)
        # repo call signature: d_lim_whipple_cm(t_b_cm, S_cm, rho_p, v) with t_b = tube wall; 0.157 cm
        area = npan * NT * LM * 2 * strip(S); out["whipple"].append(dict(S=float(S), P=math.exp(-N), d_deb_mm=d * 10, d_met_mm=dm * 10, mass_kg=area * 0.5e-3 * 2700.0))
        N2, d2, dm2, rho_m = flux_N(lambda rp, V: d_sw(rp, V, S / 10), npan, S)
        # design equations at the larger critical particle (debris 2.8 g/cc vs meteoroid): t_b = c_b d rho_p/rho_b ; AD_stuff = c_NK d rho_p
        tb = max(0.15 * d2 * 2.8 / 2.7, 0.15 * dm2 * rho_m / 2.7) * 10.0; tb = max(tb, 0.5)       # mm; never below the repo 0.5 mm min gauge
        ad = max(0.23 * d2 * 2.8, 0.23 * dm2 * rho_m) * 10.0                                         # kg/m2 (g/cm2 x 10)
        a_b = npan * NT * LM * 2 * strip(S); a_s = npan * NT * LM * 2 * strip(S, 0.5)
        out["stuffed"].append(dict(S=float(S), P=math.exp(-N2), d_deb_mm=d2 * 10, d_met_mm=dm2 * 10, t_b_mm=tb, AD_stuff_kg_m2=ad, mass_bump=a_b * tb * 1e-3 * 2700.0, mass_stuff=a_s * ad, mass_kg=a_b * tb * 1e-3 * 2700.0 + a_s * ad, rho_met=rho_m))
    return out
res = {}
for b, npan in (("Jun", 77), ("Aug", 128)):
    r = run(npan)
    for k in ("whipple", "stuffed"):
        ok = [x for x in r[k] if x["P"] >= 0.90]; r[k + "_best"] = min(ok, key=lambda x: x["mass_kg"]); print(b, k, {a: round(v, 3) for a, v in r[k + "_best"].items()})
    res[b] = r
json.dump(res, open("c21_bumper_worst.json" if WORST else "c21_bumper.json", "w"), indent=1)
