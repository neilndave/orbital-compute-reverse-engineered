"""Check 9C (t444): coolant capacity and pressure drop through the radiator panel-to-panel fold hinges (column of ~9-10 panels per stack, 4 mm hinge gap) for the replica builds.
Method: repo/replica coolant_t423d.cool for the loop; NVIDIA Warp ladder-network solve (Picard on turbulent hinge/manifold K, warp.optim.linear.cg on the nodal system) for
(P) parallel feed: manifold along each column with a flex link at every hinge, panels T-fed;  (S) series: panels of a column plumbed end to end through the hinge links.
Interpretation (INFERENCE): the array fold hinges carry no coolant; 'fold hinges' = radiator panel hinges.  Hose ID, bend K and corrugation factor are ASSUMED.  ESTIMATE."""
import sys, json, math, time, numpy as np, warp as wp
wp.config.quiet = True
sys.path.insert(0, "replica")
import coolant_t423d as CT
from warp.optim.linear import cg, aslinearoperator
RHO, MU = 978.0, 4.0e-4   # as repo G (water ~350 K)
def poiseuille_panel(Q, a_mm, w_mm, L_m, n_tubes=4, hdr_mm=14.0):
    b = (a_mm - 2 * w_mm) * 1e-3; u = Q / (n_tubes * b * b); dp = 28.45 * MU * u * L_m / b ** 2     # square duct fRe = 56.9
    return dp, u, b
def solve_ladder(Qcol, n, Rp, d, K_hinge, Khdr, corr):
    """parallel feed: supply manifold nodes 0..n, return nodes 0..n (node 0 = root).  panel k (1..n) between S_k and R_k.  Segment resistance = corr*(f L/d + K_hinge) rho u^2/2 per hinge segment.
    unknowns S_0..S_n,R_0..R_n relative pressure; R_0 = 0, flow imposed by scaling.  Picard on flow-dependent segment resistances."""
    Ls = 2.9446 + 0.004; A = math.pi * d * d / 4; q = np.full(n, Qcol / n) * 0 + Qcol * (np.arange(n, 0, -1) / n)  # flow in segment k (k=1..n): downstream demand
    q = Qcol * (n - np.arange(n)) / n
    for it in range(200):
        u = q / A; Re = RHO * u * d / MU; f = np.where(Re > 4000, 0.316 * np.maximum(Re, 1) ** -0.25, 64 / np.maximum(Re, 1))
        dpseg = corr * (f * Ls / d + K_hinge) * RHO * u * u / 2 + 1e-9; gseg = q / dpseg                 # conductance Q/dp
        N = 2 * (n + 1); G = np.zeros((N, N)); b = np.zeros(N)
        def stamp(i, j, g): G[i, i] += g; G[j, j] += g; G[i, j] -= g; G[j, i] -= g
        for k in range(1, n + 1):
            stamp(k - 1, k, gseg[k - 1]); stamp(n + 1 + k - 1, n + 1 + k, gseg[k - 1]); stamp(k, n + 1 + k, 1.0 / (Rp[k - 1] + 1e-9))   # panel k between S_k and R_k
        # R_0 = 0 (Dirichlet), inject +Qcol at S_0
        keep = [i for i in range(N) if i != n + 1]; b[0] = Qcol
        K = G[np.ix_(keep, keep)]; x = wp.zeros(len(keep), dtype=wp.float64); op = aslinearoperator(wp.array(K, dtype=wp.float64))
        cg(op, wp.array(b[keep], dtype=wp.float64), x, tol=1e-14, maxiter=20 * len(keep)); xs = np.zeros(N); xs[keep] = x.numpy()
        qn = np.array([gseg[k] * (xs[k] - xs[k + 1]) for k in range(n)])
        if np.max(np.abs(qn - q)) < 1e-7 * Qcol: break
        q = 0.5 * q + 0.5 * qn
    qp = np.array([(xs[k] - xs[n + 1 + k]) / (Rp[k - 1] + 1e-9) for k in range(1, n + 1)])
    return dict(dp_root=float(xs[0]), q_panel=qp, it=it, resid=float(np.max(np.abs(qn - q))))
out = dict(label="ESTIMATE; hose ID/K/corrugation factor ASSUMED; panel tube geometry 4 tubes a=6.094 mm w=1.57 mm (MMOD input set) and a=6.805 mm (repo P6 bus_model) bracketed", builds={}); t0 = time.time()
for b, P, A, cols in (("Jun", 150.0, 81.62815837399465, [10, 10, 10, 10, 10, 9, 9, 9]), ("Aug", 250.0, 136.0469306233244, [10] * 11 + [9, 9])):
    r = {}
    for dT in (20.0, 9.8):
        c = CT.cool(P, A, pump=0.10, dT=dT, panel_fluid=False, run_scale=0.5, spares=2); dg = c["diag"]
        r[f"loop_dT{dT}"] = dict(total_kg=c["total"], pumps=c["pumps"], fluid=c["fluid_total"], piping=c["piping"], mdot=dg["mdot"], Vdot_L_s=dg["Vdot_L_s"], trunk_d_mm=dg["d_mm"], dp_kPa_model=dg["dp_kPa"], P_hyd_W=dg["P_hyd_W"], n_active_by_power=dg["n_active"],
                                n_active_by_flow=math.ceil(dg["Vdot_L_s"] / 1.67 - 1e-9), module_flow_L_s=1.67)
    Vdot = r["loop_dT20.0"]["Vdot_L_s"] * 1e-3; npan = sum(cols)
    for tube, (a, w) in (("a6.094", (6.094, 1.57)), ("a6.805", (6.805, 1.5686))):
        Qp = Vdot / npan; dpp, up, bore = poiseuille_panel(Qp, a, w, 2.9446, hdr_mm=14.0)
        # series column
        ser = {}
        for ncol in (10, 9):
            Qc = Vdot * ncol / npan; dps = []
            for ks, label in ((1.0, "K1"),):
                dpt, ut, _ = poiseuille_panel(Qc, a, w, 2.9446); dpc = ncol * dpt + (ncol - 1) * 2 * 1.5 * RHO * ((Qc / (4 * bore ** 2)) ** 2) / 2   # + hinge/header K 1.5 x2 per hinge on the tube velocity
                ser[f"n{ncol}"] = dict(Qcol_L_s=Qc * 1e3, dp_kPa=dpc / 1e3, u_tube=ut)
        res = dict(panel_Q_mL_s=Qp * 1e6, panel_dp_kPa=dpp / 1e3, u_tube_m_s=up, bore_mm=bore * 1e3, Re_tube=RHO * up * bore / MU, series_column=ser)
        # parallel-feed ladders: hose ID from 2 m/s at column root, ASSUMED K per hinge 2.0 (two bends) x corrugation 2.0
        par = {}
        for ncol in (10, 9):
            Qc = Vdot * ncol / npan; d = math.sqrt(4 * Qc / (math.pi * 2.0)); Rp = np.full(ncol, dpp / Qp)
            for Kh, corr in ((2.0, 2.0), (4.0, 3.0), (0.0, 1.0)):
                s = solve_ladder(Qc, ncol, Rp, d, Kh, 1.5, corr); qp = s["q_panel"]
                par[f"n{ncol}_K{Kh}_corr{corr}"] = dict(hose_ID_mm=d * 1e3, dp_root_kPa=s["dp_root"] / 1e3, maldistribution_max_over_mean=float(qp.max() / qp.mean()), min_over_mean=float(qp.min() / qp.mean()), picard_iters=s["it"], resid=s["resid"])
        # design closure for parallel feed (ASSUMED K=2 per hinge, corrugation x2): (i) hose ID needed for max/mean <= 1.15 with no orifice; (ii) series panel-inlet orifice (Ro = ko * R_panel) at 12 mm-class hose
        close = {}
        for ncol in (10, 9):
            Qc = Vdot * ncol / npan; Rp0 = dpp / Qp; d0 = math.sqrt(4 * Qc / (math.pi * 2.0))
            lo, hi = d0, 0.12
            for _ in range(40):
                m = 0.5 * (lo + hi); s_ = solve_ladder(Qc, ncol, np.full(ncol, Rp0), m, 2.0, 1.5, 2.0); md = s_["q_panel"].max() / s_["q_panel"].mean()
                if md > 1.15: lo = m
                else: hi = m
            sd = solve_ladder(Qc, ncol, np.full(ncol, Rp0), hi, 2.0, 1.5, 2.0)
            lo, hi2 = 0.0, 1000.0
            for _ in range(50):
                ko = 0.5 * (lo + hi2); s_ = solve_ladder(Qc, ncol, np.full(ncol, Rp0 * (1 + ko)), d0, 2.0, 1.5, 2.0); md = s_["q_panel"].max() / s_["q_panel"].mean()
                if md > 1.15: lo = ko
                else: hi2 = ko
            so = solve_ladder(Qc, ncol, np.full(ncol, Rp0 * (1 + hi2)), d0, 2.0, 1.5, 2.0)
            close[f"n{ncol}"] = dict(hose_ID_for_maldist1p15_mm=hi * 1e3, dp_root_kPa_big_hose=sd["dp_root"] / 1e3, manifold_u_root_m_s=Qc / (math.pi * hi * hi / 4), fluid_kg_per_column_manifolds=2 * ncol * 2.9486 * math.pi * hi * hi / 4 * RHO,
                                      orifice_ko=hi2, dp_root_kPa_orifice=so["dp_root"] / 1e3, hose_ID_orifice_mm=d0 * 1e3, fluid_kg_per_column_manifolds_orifice=2 * ncol * 2.9486 * math.pi * d0 * d0 / 4 * RHO)
        res["parallel_design_closure"] = close
        res["parallel_feed"] = par; r[f"tube_{tube}"] = res
    out["builds"][b] = r
out["_s"] = time.time() - t0; json.dump(out, open("c9_coolant.json", "w"), indent=1)
for b, r in out["builds"].items():
    print(b, {k: round(v, 3) if isinstance(v, float) else v for k, v in r["loop_dT20.0"].items()})
    for t in ("tube_a6.094", "tube_a6.805"):
        x = r[t]; print(" ", t, {k: round(v, 3) for k, v in x.items() if not isinstance(v, dict)}, "series n10:", {k: round(v, 2) for k, v in x["series_column"]["n10"].items()})
        print("    closure n10", {a: round(c, 3) for a, c in x["parallel_design_closure"]["n10"].items()}); print("    closure n9", {a: round(c, 3) for a, c in x["parallel_design_closure"]["n9"].items()})
        for k, v in x["parallel_feed"].items():
            if k.startswith("n10"): print("    ", k, {a: round(c, 3) if isinstance(c, float) else c for a, c in v.items()})
