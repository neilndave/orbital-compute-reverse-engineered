"""t454 item 2: per-column pump + reverse-return column manifold, NVIDIA Warp ladder network (warp.optim.linear.cg nodal solve, Picard on turbulent K).  ESTIMATE; hose ID, hinge K, corrugation factor, pump efficiency/mass ASSUMED."""
import sys, json, math, time, numpy as np, warp as wp
wp.config.quiet = True
sys.path.insert(0, "/tmp/gtcfc_root/inputs/ai1_replica"); sys.path.insert(0, "/tmp/gtcfc_root/inputs/ai1_replica/checks_t444")
import coolant_t423d as CT
from warp.optim.linear import cg, aslinearoperator
RHO, MU = 978.0, 4.0e-4
LS = 2.9446 + 0.004
def panel_dp(Q, a_mm, w_mm, n_tubes=4):
    b = (a_mm - 2 * w_mm) * 1e-3; u = Q / (n_tubes * b * b); return 28.45 * MU * u * 2.9446 / b ** 2, u, b
def ladder(Qcol, n, Rp, d, Kh, corr, reverse=True, Khdr=1.5, ko=0.0, Atube=1.0, use_warp=True):
    """supply nodes S0..Sn (S0 root inject), return nodes R1..Rn; panel k between S_k and R_k.  reverse=True: return header flows toward far end, outlet at R_n (P=0).
    reverse=False: return flows back toward root, outlet R_0 (P=0).  Segment dp = corr*(f Ls/d + Kh)*rho u^2/2 per hinge segment (+Khdr at panel tee)."""
    A = math.pi * d * d / 4; q = np.full(n, Qcol / n)
    def seg(qs):
        u = np.abs(qs) / A; Re = RHO * u * d / MU + 1e-9; f = np.where(Re > 4000, 0.316 * Re ** -0.25, 64 / Re)
        R = corr * (f * LS / d + Kh) * RHO * u / 2 / A + 1e-12; return R    # dp = R*|Q|*Q -> conductance in nodal form linearised: g = 1/(R*|Q|)
    for it in range(300):
        qs_sup = np.array([q[k:].sum() for k in range(n)])                     # supply seg k (S_k -> S_{k+1}): flow to panels k+1..n  (index k=0..n-1)
        if reverse: qs_ret = np.array([q[:k + 1].sum() for k in range(n - 1)])   # return seg between R_{k+1} and R_{k+2}: flow of panels 1..k+1
        else: qs_ret = np.array([q[k:].sum() for k in range(n)])                  # return seg between R_k and R_{k+1} toward root ... flow of panels k+1..n
        g_sup = 1.0 / seg(qs_sup); g_ret = 1.0 / seg(qs_ret)
        N = 2 * n + 2; idxS = lambda k: k; idxR = lambda k: n + 1 + k            # R index 0..n ; R_0 exists (root side)
        G = np.zeros((N, N))
        def st(i, j, g): G[i, i] += g; G[j, j] += g; G[i, j] -= g; G[j, i] -= g
        for k in range(n): st(idxS(k), idxS(k + 1), g_sup[k])
        if reverse:
            for k in range(n - 1): st(idxR(k + 1), idxR(k + 2), g_ret[k])
            ground = idxR(n); dead = [idxR(0)]
        else:
            for k in range(n): st(idxR(k), idxR(k + 1), g_ret[k])
            ground = idxR(0); dead = []
        for k in range(1, n + 1): st(idxS(k), idxR(k), 1.0 / (Rp[k - 1] + (Khdr * RHO / A ** 2 + ko * RHO / Atube ** 2) * q[k - 1] / 2 + 1e-12))
        keep = [i for i in range(N) if i != ground and i not in dead]; b = np.zeros(N); b[0] = Qcol
        K = G[np.ix_(keep, keep)]; xs = np.zeros(N)
        if use_warp:
            x = wp.zeros(len(keep), dtype=wp.float64); op = aslinearoperator(wp.array(K, dtype=wp.float64))
            cg(op, wp.array(b[keep], dtype=wp.float64), x, tol=1e-14, maxiter=40 * len(keep)); xs[keep] = x.numpy()
        else: xs[keep] = np.linalg.solve(K, b[keep])
        qn = np.array([(xs[idxS(k)] - xs[idxR(k)]) / (Rp[k - 1] + (Khdr * RHO / A ** 2 + ko * RHO / Atube ** 2) * q[k - 1] / 2 + 1e-12) for k in range(1, n + 1)])
        qn *= Qcol / qn.sum()
        if np.max(np.abs(qn - q)) < 1e-8 * Qcol: break
        q = 0.5 * q + 0.5 * qn
    return dict(dp_root=float(xs[0] - xs[ground]), q=qn, it=it, maldist=float(qn.max() / qn.mean()), minr=float(qn.min() / qn.mean()))
if __name__ == "__main__":
    t0 = time.time(); out = dict(label="ESTIMATE; ASSUMED hinge K 2 x corrugation 2 central; panel tube geometry a=6.805/1.5686 (repo P6) and 6.094/1.57 (MMOD set)", cases=[])
    Jun = ("Jun", 150.0, 81.62815837399465, [10, 10, 10, 10, 10, 9, 9, 9]); Aug = ("Aug", 250.0, 136.0469306233244, [10] * 11 + [9, 9])
    for (b, P, A, cols) in (Jun, Aug):
        c = CT.cool(P, A, pump=0.10, dT=20.0, panel_fluid=False, run_scale=0.5, spares=2); Vdot = c["diag"]["Vdot_L_s"] * 1e-3; npan = sum(cols)
        for tube, (a, w) in (("a6.805", (6.805, 1.5686)), ("a6.094", (6.094, 1.57))):
            Qp = Vdot / npan; dpp, up, bore = panel_dp(Qp, a, w); Rp0 = dpp / Qp
            for ncol in (10, 9):
                Qc = Vdot * ncol / npan
                for rev in (True, False):
                    for dmm in (8, 10, 12, 14, 16, 20, 25):
                        for (Kh, corr) in ((2.0, 2.0), (0.0, 1.0), (4.0, 3.0)):
                            s = ladder(Qc, ncol, np.full(ncol, Rp0), dmm * 1e-3, Kh, corr, reverse=rev)
                            out["cases"].append(dict(build=b, tube=tube, ncol=ncol, reverse=rev, d_mm=dmm, Kh=Kh, corr=corr, Qcol_L_s=Qc * 1e3, panel_dp_kPa=dpp / 1e3, dp_root_kPa=s["dp_root"] / 1e3, maldist=s["maldist"], minr=s["minr"], it=s["it"]))
    out["_s"] = time.time() - t0; json.dump(out, open("c10_coolant.json", "w"), indent=0)
    for r in out["cases"]:
        if r["tube"] == "a6.805" and r["build"] == "Jun" and r["ncol"] == 10 and (r["Kh"], r["corr"]) == (2.0, 2.0): print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    print("secs", out["_s"])
