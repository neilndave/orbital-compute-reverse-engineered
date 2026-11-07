"""t454 item 2c: tapered (constant-velocity) supply/return headers + per-panel orifice balance, NVIDIA Warp CG nodal solve (final points) / NumPy solve inside the bisection.  ESTIMATE; ASSUMED hinge K (2), corrugation factor (2), d_min."""
import sys, json, math, numpy as np, warp as wp
wp.config.quiet = True
sys.argv = sys.argv[:1]
from c10_coolant import RHO, MU, LS, panel_dp, aslinearoperator, cg
def ladder_t(Qcol, n, Rp, dsup, dret, Kh, corr, ko, Atube, Khdr=1.5, use_warp=False):
    """reverse-return; dsup[k] (k=0..n-1) supply seg S_k->S_k+1 ; dret[k] (k=0..n-2) return seg R_k+1->R_k+2 ; tee uses dsup[k-1]."""
    q = np.full(n, Qcol / n)
    def R_of(qs, d):
        A = math.pi * d * d / 4; u = np.abs(qs) / A; Re = RHO * u * d / MU + 1e-9; f = np.where(Re > 4000, 0.316 * Re ** -0.25, 64 / Re)
        return corr * (f * LS / d + Kh) * RHO * u / 2 / A + 1e-12
    Atee = math.pi * np.asarray(dsup) ** 2 / 4
    for it in range(400):
        qs_sup = np.array([q[k:].sum() for k in range(n)]); qs_ret = np.array([q[:k + 1].sum() for k in range(n - 1)])
        g_sup = 1.0 / R_of(qs_sup, np.asarray(dsup)); g_ret = 1.0 / R_of(qs_ret, np.asarray(dret))
        N = 2 * n + 2; S = lambda k: k; Rr = lambda k: n + 1 + k; G = np.zeros((N, N))
        def st(i, j, g): G[i, i] += g; G[j, j] += g; G[i, j] -= g; G[j, i] -= g
        for k in range(n): st(S(k), S(k + 1), g_sup[k])
        for k in range(n - 1): st(Rr(k + 1), Rr(k + 2), g_ret[k])
        ground = Rr(n)
        gp = lambda k: 1.0 / (Rp[k - 1] + (Khdr * RHO / Atee[k - 1] ** 2 + ko * RHO / Atube ** 2) * q[k - 1] / 2 + 1e-12)
        for k in range(1, n + 1): st(S(k), Rr(k), gp(k))
        keep = [i for i in range(N) if i != ground and i != Rr(0)]; b = np.zeros(N); b[0] = Qcol; K = G[np.ix_(keep, keep)]; xs = np.zeros(N)
        if use_warp:
            x = wp.zeros(len(keep), dtype=wp.float64); cg(aslinearoperator(wp.array(K, dtype=wp.float64)), wp.array(b[keep], dtype=wp.float64), x, tol=1e-14, maxiter=40 * len(keep)); xs[keep] = x.numpy()
        else: xs[keep] = np.linalg.solve(K, b[keep])
        qn = np.array([(xs[S(k)] - xs[Rr(k)]) * gp(k) for k in range(1, n + 1)]); qn *= Qcol / qn.sum()
        if np.max(np.abs(qn - q)) < 1e-8 * Qcol: break
        q = 0.5 * q + 0.5 * qn
    return dict(dp_root=float(xs[0] - xs[ground]), q=qn, maldist=float(qn.max() / qn.mean()), minr=float(qn.min() / qn.mean()))
def taper(droot, n, dmin):
    frac_s = np.array([(n - k) / n for k in range(n)]); frac_r = np.array([(k + 1) / n for k in range(n - 1)])
    return np.maximum(dmin, droot * np.sqrt(frac_s)), np.maximum(dmin, droot * np.sqrt(frac_r))
def fluid_kg(dsup, dret, n_hose_root=0.0):
    return float(RHO * sum(math.pi * d * d / 4 * LS for d in list(dsup) + list(dret)))
if __name__ == "__main__":
    a, w = 6.094, 1.57; b = (a - 2 * w) * 1e-3; Atube = 4 * b * b; n = 10; Qc = 0.2383e-3
    dpp, up, _ = panel_dp(Qc / n, a, w); Rp = np.full(n, dpp / (Qc / n)); res = []
    for droot in (12, 14, 16, 18, 20, 24):
        for dmin in (6, 8, 10):
            ds, dr = taper(droot * 1e-3, n, dmin * 1e-3)
            def mal(ko, uw=False): return ladder_t(Qc, n, Rp, ds, dr, 2.0, 2.0, ko, Atube, use_warp=uw)
            ok = lambda s: s["maldist"] <= 1.15 and s["minr"] >= 0.85
            if ok(mal(0.0)): ko = 0.0
            else:
                lo, hi = 0.0, 1.0
                while not ok(mal(hi)): hi *= 2
                for _ in range(14):
                    mid = (lo + hi) / 2
                    if ok(mal(mid)): hi = mid
                    else: lo = mid
                ko = hi
            s = mal(ko, True)
            res.append(dict(droot_mm=droot, dmin_mm=dmin, ko=ko, dp_orifice_kPa=ko * RHO * up ** 2 / 2e3, dp_root_kPa=s["dp_root"] / 1e3, maldist=s["maldist"], minr=s["minr"], fluid_hdr_kg_per_col=fluid_kg(ds, dr), panel_dp_kPa=dpp / 1e3))
            print({k: round(v, 3) for k, v in res[-1].items()}, flush=True)
    # untapered references for mass
    for d in (12, 14, 16, 20):
        print("untapered", d, "fluid_kg_per_col", round(fluid_kg([d * 1e-3] * n, [d * 1e-3] * (n - 1)), 2))
    json.dump(res, open("c10c_taper.json", "w"), indent=0)
