"""Check 8 (t444) part 2: convert the Warp ray-trace array/bus blockage into the radiator thermal result.  Uses the repo thermal model (gb10_gtc/thermal/ai1_model.host_treq_det logic, copied with one extra term).
All values ESTIMATE; F1 fin table; peak/avg loads and replica areas from the t434 replica builds."""
import sys, json, math, numpy as np
sys.path.insert(0, "replica/gb10_gtc/thermal")
import ai1_specs as S
import ai1_model as M
from scipy.optimize import brentq
from scipy.interpolate import RegularGridInterpolator
HERE = "replica/gb10_gtc/thermal"
tbl = json.load(open("replica/gb10_run_t410/results/table_F1_L60_t0p8.json"))
e = json.load(open(f"{HERE}/data/env_table.json")); gt = json.load(open(f"{HERE}/data/g_table.json"))
BASE = dict(sigma_pt=0.0, fg=0.0, dT0=20.0, pairing=0.0, leak=False, blk=0.0092)
eta = np.array(tbl["eta"]).reshape(tbl["ntb"], tbl["nee"], tbl["nts"])
tb = tbl["tb0"] + tbl["dtb"] * np.arange(tbl["ntb"]); ea = tbl["ee0"] + tbl["dee"] * np.arange(tbl["nee"]); ta = tbl["ts0"] + tbl["dts"] * np.arange(tbl["nts"])
RGI = RegularGridInterpolator((tb, ea, ta), eta, bounds_error=False, fill_value=None)
tab = lambda Tb, e_, Ts_: float(RGI([[min(max(Tb, tb[0]), tb[-1]), min(max(e_, ea[0]), ea[-1]), min(max(Ts_, ta[0]), ta[-1])]])[0])
def treq(case, fb=0.0, Ta=330.0, ea_=0.8, A=None):
    """as host_treq_det (u=0.25), plus: a fraction fb of the radiator's view is a grey surface (array/bus) at Ta, emissivity ea_, replacing deep space for that fraction."""
    u = 0.25; dec = math.radians(23.44) * math.sin(2 * math.pi * u); inc = math.radians(97.57)
    beta = abs(math.degrees(math.asin(math.sin(dec) * math.cos(inc) + math.cos(dec) * math.sin(inc))))
    doy = 79.0 + u * 365.25 + case["pairing"] * 182.625; Sun = 1367.0 * (1 + 0.0334 * math.cos(2 * math.pi * (doy - 3.0) / 365.25))
    Fb = np.interp(beta, e["beta"], e["F_earth"]); Ab = np.interp(beta, e["beta"], e["albedo_geom"])
    alpha = 0.2; eps = case["eps0"]; q = eps * 239.0 * Fb + alpha * 0.30 * Sun * Ab + 0.0 + case["fg"] * alpha * Sun * np.interp(beta, gt["beta"], gt["g"])
    ee = eps * case["F0"] * (1 - min(0.15, case["blk"] * math.exp(-0.045)))
    Ts = (q / (ee * S.SIG)) ** 0.25; dT = case["dT0"]; A = A or case["A"]
    def bal(T):
        gs = 0.0
        for m, w in ((0, 1.0), (1, 4.0), (2, 1.0)):
            Tm = T + dT * 0.5 * m; et = tab(Tm, ee, Ts); gs += w * 2 * ee * S.SIG * (Tm**4 - Ts**4) * et
            if fb > 0:   # grey-wall exchange for the blocked fraction (per unit of the same face area), same fin efficiency
                gs += w * 2 * fb * (S.SIG * (Tm**4 - Ta**4) / (1 / eps + 1 / ea_ - 1)) * et
        return A * gs / 6.0 - case["P0"]
    return brentq(bal, 250.0, 450.0, xtol=1e-9)
BUILDS = {"J8": dict(peak=150e3, avg=120e3, A=81.62815837399465), "A4": dict(peak=250e3, avg=175e3, A=136.0469306233244)}
OPT = {"e95F100": (0.95, 1.00), "e92F99": (0.92, 0.99), "e92F95": (0.92, 0.95), "e90F85": (0.90, 0.85)}
vf = json.load(open("c8_viewfactor.json"))
SC = {"render_yoke4.137_W14": "S0_render_yoke4.137_W14", "stage1_yoke1.968_W14": "S1_stage1_yoke1.968_W14", "repo_root0.25_W14": "S2_repo_root0.25_W14"}
out = dict(label="ESTIMATE (F1 fin table; flat-strip model; u=0.25 deterministic draw; MC-median offset not applied, see mc_median)", rows=[])
# MC median of required supply temperature for F1 e92F99 peak, from RESULTS_t422 / check 6 (STATEMENT of earlier run): J8 376.7 K (case), A4: read from the replica run
for bname, bd in BUILDS.items():
    key = "Jun" if bname == "J8" else "Aug"
    for opt, (eps0, F0) in OPT.items():
        if opt not in ("e92F99", "e95F100"): continue
        for load in ("peak", "avg"):
            c = dict(BASE); c.update(P0=bd[load], A=bd["A"], eps0=eps0, F0=F0)
            T0 = treq(c)
            for sname, sk in SC.items():
                r = vf[f"{key}/{sk}"]; fa, fbus = r["f_array_exact_mean"], r["f_bus_mc_mean"]
                Fe = 1.0 - fa - fbus; c2 = dict(c); c2["F0"] = Fe * (F0 / 0.99 if False else 1.0)
                T1 = treq(c2); T2 = treq(c, fb=fa + fbus) if False else treq(dict(c, F0=Fe), fb=fa + fbus, Ta=330.0, ea_=0.8)
                # area ratio needed to restore the supply cap 370.15 K (bisection on A)
                def need(case, **kw):
                    lo, hi = 0.5, 3.0
                    for _ in range(40):
                        m = 0.5 * (lo + hi)
                        if treq(case, A=bd["A"] * m, **kw) > 370.15: lo = m
                        else: hi = m
                    return hi
                out["rows"].append(dict(build=bname, optics=opt, load=load, scenario=sname, f_array=fa, f_bus=fbus, F_eff=Fe, F0_model=F0, T_det_model_K=T0, T_det_geometry_K=T1, dT_K=T1 - T0,
                    T_det_grey_array_K=T2, dT_grey_K=T2 - T0, area_scale_for_370K_model=need(c), area_scale_for_370K_geometry=need(dict(c, F0=Fe)), area_scale_for_370K_grey=need(dict(c, F0=Fe), fb=fa + fbus)))
json.dump(out, open("c8_thermal.json", "w"), indent=1)
for r in out["rows"]:
    if r["optics"] == "e92F99" and r["scenario"] in ("render_yoke4.137_W14", "repo_root0.25_W14"):
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
