"""Check 9B (t444): MMOD for the replica radiators. Analytic: repo mmod_env.whipple (Gruen + NASA90, idealized/outdated; ORDEM/MASTER NOT run; normal incidence; no obliquity model).
Monte Carlo: Warp (wp.poisson per panel per trial) for the distribution of punctured panels, converted to radiator area loss and supply-temperature delta via the check-6 thermal model.  ESTIMATE."""
import sys, json, math, time, numpy as np, warp as wp, io, contextlib
wp.config.quiet = True
sys.path.insert(0, "vendor/same_rack/src"); sys.path.insert(0, "replica/checks_t444")
from rack_two_skies.mmod_env import whipple
SC = "replica"
with contextlib.redirect_stdout(io.StringIO()):
    import c8_thermal as T
dev = "cpu"
@wp.kernel
def mc(lam: float, npan: int, seed: int, hit: wp.array(dtype=int)):
    t = wp.tid(); st = wp.rand_init(seed, t); n = int(0)
    for i in range(npan): n += int(wp.poisson(st, lam) > 0)
    hit[t] = n
def run(N_total, npan, trials=200000, seed=7):
    hit = wp.zeros(trials, dtype=int, device=dev); wp.launch(mc, trials, [N_total / npan, npan, seed, hit], device=dev); h = hit.numpy(); return h
out = dict(note="ESTIMATE; ASSUMED tube geometry 4 tubes/panel, 6.094 mm width, wall 1.57 mm, bumper 0.5 mm; 600 km, inc 97.6, epoch 2030 as repo mmod_hand; Whipple normal incidence; tumbling-plate flux both faces")
tt = {}; t00 = time.time()
# validation: repo T45 geometry, S=20 mm, T=5
g45 = dict(n_tubes_per_panel=4, tube_width_m=6.094e-3, panel_L_m=2.7976, n_panels=266)
w = whipple(550.0, 97.6, 2030, 20, 1.57, 0.5, g45, T_yr=5); out["validation_T45_S20"] = dict(N_5yr=w["N_5yr"], repo_value=1.3925877986177109, A_tube=w["A_tube_m2"])
for b, npan, A_rad in (("Jun", 77, 81.62815837399465), ("Aug", 128, 136.0469306233244)):
    lay = json.load(open(f"{SC}/{b}/fleet_layout_replica_{b}.json")) if False else None
    import glob
    Lm = json.load(open(glob.glob(f"replica/**/fleet_layout_replica_{b}.json", recursive=True)[0]))["panel_L_mm"] / 1000
    g = dict(n_tubes_per_panel=4, tube_width_m=6.094e-3, panel_L_m=Lm, n_panels=npan)
    base = dict(build=b, panel_L_m=Lm, n_panels=npan, rows=[])
    for S in (10, 20, 50):
        for Ty in (3, 5):
            w = whipple(600.0, 97.6, 2030, S, 1.57, 0.5, g, T_yr=Ty)
            for mult in (0.1, 1, 3):
                N = w["N_5yr"] * mult
                ts = time.time(); h = run(N, npan); dt = time.time() - ts
                r = dict(S_mm=S, T_yr=Ty, flux_mult=mult, N=N, P_no_puncture_analytic=math.exp(-N), P_no_puncture_mc=float(np.mean(h == 0)), mean_panels_hit=float(h.mean()), P_ge2=float(np.mean(h >= 2)), P_ge4=float(np.mean(h >= 4)), p95_panels=int(np.percentile(h, 95)),
                         bumper_mass_kg=w["bumper_mass_kg"], mc_s=dt)
                # supply temp if k panels isolated/lost (ASSUMED isolable): peak 150/250 kW, e92F99 model
                bd = T.BUILDS["J8" if b == "Jun" else "A4"]; c = dict(T.BASE); c.update(P0=bd["peak"], A=bd["A"], eps0=0.92, F0=0.99)
                for k in (1, 2, 4):
                    cc = dict(c); cc["A"] = bd["A"] * (1 - k / npan); r[f"T_peak_K_lose{k}"] = T.treq(cc)
                base["rows"].append(r)
    base["T_peak_K_nominal"] = T.treq(dict(c, A=bd["A"])); base["replica_bumper_line_kg"] = 0.8437 * 2 * A_rad
    out[b] = base
out["_s"] = time.time() - t00; json.dump(out, open("c9_mmod.json", "w"), indent=1)
print(json.dumps(out["validation_T45_S20"]))
for b in ("Jun", "Aug"):
    print(b, out[b]["T_peak_K_nominal"], out[b]["replica_bumper_line_kg"])
    for r in out[b]["rows"]:
        if r["flux_mult"] in (1,) or r["S_mm"] == 20: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k in ("S_mm", "T_yr", "flux_mult", "N", "P_no_puncture_analytic", "P_no_puncture_mc", "mean_panels_hit", "P_ge2", "p95_panels", "bumper_mass_kg", "T_peak_K_lose1")})
