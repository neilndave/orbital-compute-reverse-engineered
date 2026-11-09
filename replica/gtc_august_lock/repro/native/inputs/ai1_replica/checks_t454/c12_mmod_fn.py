import os
import sys, math, numpy as np, warp as wp
wp.config.quiet = True
sys.path.insert(0, os.environ["GTCFC_ROOT"]+"/inputs/repo/src")
from rack_two_skies.mmod_env import whipple
@wp.kernel
def mc(lam: float, npan: int, seed: int, hit: wp.array(dtype=int)):
    t = wp.tid(); st = wp.rand_init(seed, t); n = int(0)
    for i in range(npan): n += int(wp.poisson(st, lam) > 0)
    hit[t] = n
PANEL_W = 0.3634176; RHO = 2700.0; Lm = 2.944557955166043
def sweep(npan, tgt=0.90, Smax=200, trials=200000, seed=11, t_s=0.5):
    g = dict(n_tubes_per_panel=4, tube_width_m=6.094e-3, panel_L_m=Lm, n_panels=npan); rows = []
    for S in range(10, Smax + 1, 5):
        w = whipple(600.0, 97.6, 2030, S, 1.57, 0.5, g, T_yr=5); N = w["N_5yr"]
        hit = wp.zeros(trials, dtype=int, device="cpu"); wp.launch(mc, trials, [N / npan, npan, seed, hit], device="cpu"); h = hit.numpy()
        sw = min(w["bumper_strip_width_mm"] / 1e3, PANEL_W / 4); area = npan * 4 * Lm * 2 * sw
        rows.append(dict(S_mm=S, P_mc=float(np.mean(h == 0)), N=N, area_m2=area, mass_A_kg=area * t_s * 1e-3 * RHO, d_lim_deb_mm=w["d_lim_debris_mm"]))
        if rows[-1]["P_mc"] >= tgt: break
    return rows
