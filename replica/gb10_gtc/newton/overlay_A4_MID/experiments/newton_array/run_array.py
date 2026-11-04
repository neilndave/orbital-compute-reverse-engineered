"""Z-fold rigid-panel solar-array wing deployment with Newton 1.7.0 (Featherstone, penalty latches), one wing on a free bus.
Chain = yoke + 20 leaves (21 spring-driven hinges).  Planar (hinge axes = z, the 14 m leaf width).  Zero gravity, rigid bodies.
Geometry / mass from the repo: results/full3d/optimized_design.json (array 789.58 m2, 3.197 kg/m2, 2,524.3 kg, 2 wings, width 14 m,
wing 28.20 m, root 1.97 m), configs/assembly3d.yaml (20 leaves per wing), configs/mass_gaps.yaml (boom 24.5 kg, M_total 9,585.85 kg).
Hinge, spring, damper, latch and cable values are ESTIMATE (see docs/NEWTON_ARRAY_DEPLOYMENT.md).
usage: python run_array.py CASE   CASE in naive | tuned | ccl | validate"""
import sys, os, json, math, time
import numpy as np
import warp as wp, newton
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "..", "..", "results", "newton_array"); os.makedirs(RES, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "..", "newton_deploy")); import run_hinge as H
wp.config.quiet = True

# ---- repo geometry and mass (D) -------------------------------------------------------------------------------------------------
ARRAY_KG_TOTAL, BOOM_KG, A_TOTAL, N_WINGS = 2524.2966751918093, 24.5, 789.5829450083859, 2
sys.path.insert(0, os.path.join(HERE, "..", "..", "src")); from rack_two_skies import design_tag as DT   # P14: RTS_TAG=_T45 -> the 45 C baseline geometry / masses; "" keeps the 70 C numbers
TAG = DT.TAG
W_LEAF = 14.0                               # m, results/full3d/optimized_design.json v.array_width_m
WING_L, YOKE_L = 28.19939089315706, 1.968278816700644   # m, wing_len_m ; v.array_root_m
if TAG:      # 45 C baseline: array mass / area / wing length / root from results/full3d/optimized_design_T45.json, boom scaled with the array (mass_gaps_tag), bus from results/audit/mass_gaps_T45.json base_kg
    _d = json.load(open(os.path.join(HERE, "..", "..", "results", "full3d", f"optimized_design{TAG}.json")))
    _g = json.load(open(os.path.join(HERE, "..", "..", "results", "audit", f"mass_gaps{TAG}.json")))
    ARRAY_KG_TOTAL, A_TOTAL = _d["metrics"]["m_array_kg"], _d["metrics"]["A_array_m2"]
    BOOM_KG = 24.5 * _g["ratios"]["array"]
    W_LEAF = _d["v"]["array_width_m"]; WING_L, YOKE_L = _d["full"]["wing_len_m"], _d["v"]["array_root_m"]
N_LEAF = 20                                 # configs/assembly3d.yaml array.leaves_per_wing (E)
L_LEAF = WING_L / N_LEAF
M_LEAF = ARRAY_KG_TOTAL / N_WINGS / N_LEAF  # kg per leaf (3.197 kg/m2 x 19.7 m2)
M_YOKE = BOOM_KG / N_WINGS                  # kg, repo boom mass split over 2 wings (very light; ESTIMATE use as yoke)
M_BUS_TOTAL = 9585.85 if not TAG else _g["base_kg"]                       # kg, configs/mass_gaps.yaml
BX, BY = 6.0, 6.0                           # m, ESTIMATE bus box (same as run_chain.py); standoff 0.25 m
STANDOFF = 0.25
# ---- deployment hinge design (all ESTIMATE) -------------------------------------------------------------------------------------
W0 = 0.10                                   # rad/s, ESTIMATE spring natural frequency of each hinge on its outboard inertia
ZETA = 0.5                                  # ESTIMATE hinge damper ratio on the outboard inertia
OVER = math.radians(10.0)                   # rad, ESTIMATE spring over-travel past the latch (preload at latch)
WL = 15.0                                   # rad/s, ESTIMATE latch natural frequency (on outboard inertia)
ZL = 0.1                                    # ESTIMATE latch damping ratio
WC_FACTOR = 3.0                             # ESTIMATE: CCL coupling natural frequency = 3 x W0 (cable + pulley stiffness)
CCL_PULLEY_R = 0.10                         # m, ESTIMATE pulley radius (cable tension = torque / r)
N_HINGE = N_LEAF + 1
STROKE = np.array([math.pi / 2] + [math.pi] * N_LEAF)             # yoke folds 90 deg against the bus face, leaves 180 deg
SIGN = np.array([1.0 if i % 2 == 0 else -1.0 for i in range(N_HINGE)])   # alternating fold direction (Z-fold)
LEN = np.array([YOKE_L] + [L_LEAF] * N_LEAF)
MASS = np.array([M_YOKE] + [M_LEAF] * N_LEAF)

def outboard_I():
    """fully-extended thin-chain moment of inertia of everything outboard of hinge i about hinge i (kg m2)."""
    x0 = np.concatenate([[0.0], np.cumsum(LEN)[:-1]])            # hinge position along the chain
    I = np.zeros(N_HINGE)
    for i in range(N_HINGE):
        for k in range(i, N_HINGE):
            xc = x0[k] + LEN[k] / 2 - x0[i]
            I[i] += MASS[k] * (LEN[k]**2 / 12 + xc**2)
    return I
I_OUT = outboard_I()
I_LEAF_HINGE = MASS * LEN**2 / 3

def hinge_params(case):
    Iref = I_LEAF_HINGE if case == "naive" else I_OUT
    K = Iref * W0**2; C = 2 * ZETA * Iref * W0
    KL = I_OUT * WL**2; CL = 2 * ZL * I_OUT * WL
    Kc = np.zeros(N_HINGE); 
    if case == "ccl":
        Kc[:-1] = I_OUT[1:] * (WC_FACTOR * W0)**2 * (STROKE[:-1] / math.pi)**-1   # pair i <-> i+1, scaled to the yoke stroke
    import os; Kc = Kc * float(os.environ.get('KC_SCALE', '1.0'))   # ESTIMATE: CCL coupling scale (full strength is explicit-unstable)
    return K, C, KL, CL, Kc

@wp.kernel
def ccl_kernel(q: wp.array(dtype=float), qd: wp.array(dtype=float), qoff: int, doff: int, s: wp.array(dtype=float), stroke: wp.array(dtype=float),
               kc: wp.array(dtype=float), cc: wp.array(dtype=float), n: int, f: wp.array(dtype=float)):
    i = wp.tid()
    # deployment fraction u_i = (stroke - s*theta)/stroke  (0 stowed, 1 latched);  generalised force on phi_i, then to theta: Q_theta = -s Q_phi
    ui = (stroke[i] - s[i] * q[qoff + i]) / stroke[i]
    vi = -s[i] * qd[doff + i] / stroke[i]
    Qphi = float(0.0)
    if i + 1 < n:
        uj = (stroke[i + 1] - s[i + 1] * q[qoff + i + 1]) / stroke[i + 1]; vj = -s[i + 1] * qd[doff + i + 1] / stroke[i + 1]
        Qphi += -(kc[i] * (ui - uj) + cc[i] * (vi - vj)) / stroke[i]
    if i > 0:
        uj = (stroke[i - 1] - s[i - 1] * q[qoff + i - 1]) / stroke[i - 1]; vj = -s[i - 1] * qd[doff + i - 1] / stroke[i - 1]
        Qphi += (kc[i - 1] * (uj - ui) + cc[i - 1] * (vj - vi)) / stroke[i]
    f[doff + i] = -s[i] * Qphi

def build(case, free_bus=True):
    K, C, KL, CL, Kc = hinge_params(case)
    n_leaf_chain = N_LEAF
    m_bus = M_BUS_TOTAL - M_YOKE - N_LEAF * M_LEAF            # bus + the other wing stowed (lumped)
    b = newton.ModelBuilder(gravity=(0.0, 0.0, 0.0))
    Ib = np.diag([m_bus * (BY**2 + 6.0**2) / 12, m_bus * (BX**2 + 6.0**2) / 12, m_bus * (BX**2 + BY**2) / 12]).astype(np.float32)
    bus = b.add_link(xform=wp.transform_identity(), mass=m_bus, com=wp.vec3(0, 0, 0), inertia=wp.mat33(Ib), label="bus")
    jb = b.add_joint_free(child=bus) if free_bus else b.add_joint_fixed(parent=-1, child=bus)
    shp = newton.ModelBuilder.ShapeConfig(density=0.0, has_shape_collision=False, has_particle_collision=False)
    b.add_shape_box(bus, hx=BX / 2, hy=BY / 2, hz=3.0, cfg=shp)
    joints = [jb]; parent = bus; plen = None
    for i in range(N_HINGE):
        m, L = MASS[i], LEN[i]; Wd = W_LEAF if i > 0 else 1.0
        I = np.diag([m * Wd**2 / 12, m * (L**2 + Wd**2) / 12, m * L**2 / 12]).astype(np.float32)
        p = b.add_link(xform=wp.transform_identity(), mass=float(m), com=wp.vec3(0, 0, 0), inertia=wp.mat33(I), label=("yoke" if i == 0 else f"leaf{i}"))
        px = (BX / 2 + STANDOFF) if i == 0 else plen / 2
        s = SIGN[i]; rest = -s * OVER                     # spring rest angle in theta (beyond the latch at theta = 0)
        lo, hi = (0.0, 10.0) if s > 0 else (-10.0, 0.0)
        j = b.add_joint_revolute(parent=parent, child=p, axis=wp.vec3(0, 0, 1),
                                 parent_xform=wp.transform((px, 0.0, 0.0), wp.quat_identity()),
                                 child_xform=wp.transform((-L / 2, 0.0, 0.0), wp.quat_identity()),
                                 target_pos=rest, target_vel=0.0, target_ke=float(K[i]), target_kd=float(C[i]),
                                 limit_lower=lo, limit_upper=hi, limit_ke=float(KL[i]), limit_kd=float(CL[i]),
                                 actuator_mode=newton.JointTargetMode.POSITION)
        b.add_shape_box(p, hx=L / 2, hy=0.01, hz=Wd / 2 if i > 0 else 0.5, cfg=shp)
        joints.append(j); parent = p; plen = L
    b.add_articulation(joints)
    return b.finalize(), m_bus, (K, C, KL, CL, Kc)

def run(case, dt, t_end, usd=None, free_bus=True, rec_every=10, frame_dt=0.1):
    model, m_bus, (K, C, KL, CL, Kc) = build(case, free_bus)
    s0, s1 = model.state(), model.state(); ctrl = model.control()
    nq0 = 7 if free_bus else 0; nd0 = 6 if free_bus else 0
    q = model.joint_q.numpy().copy(); q[nq0:] = SIGN * STROKE; model.joint_q.assign(q)
    tgt = np.zeros(nd0 + N_HINGE, dtype=np.float32); tgt[nd0:] = -SIGN * OVER; ctrl.joint_target_q.assign(tgt)
    solver = newton.solvers.SolverFeatherstone(model)
    s0.joint_q.assign(q); s1.joint_q.assign(q)
    newton.eval_fk(model, s0.joint_q, s0.joint_qd, s0)
    sg = wp.array(SIGN.astype(np.float32), dtype=float); stk = wp.array(STROKE.astype(np.float32), dtype=float)
    kc = wp.array(Kc.astype(np.float32), dtype=float); cc = wp.array((0.3 * 2 * np.sqrt(np.maximum(Kc, 0) * I_OUT)).astype(np.float32), dtype=float)
    use_ccl = case == "ccl"
    viewer = None
    if usd:
        viewer = newton.viewer.ViewerUSD(output_path=usd, fps=int(round(1 / frame_dt)), up_axis="Z"); viewer.set_model(model)
    n = int(round(t_end / dt)); every = int(round(frame_dt / dt))
    T, TH, OM, BODY = [], [], [], []
    for i in range(n + 1):
        if i % rec_every == 0:
            T.append(i * dt); TH.append(s0.joint_q.numpy()[nq0:].copy()); OM.append(s0.joint_qd.numpy()[nd0:].copy()); BODY.append(s0.body_q.numpy().copy())
        if viewer is not None and i % every == 0:
            viewer.begin_frame(i * dt); viewer.log_state(s0); viewer.end_frame()
        if i == n: break
        if use_ccl:
            wp.launch(ccl_kernel, dim=N_HINGE, inputs=[s0.joint_q, s0.joint_qd, nq0, nd0, sg, stk, kc, cc, N_HINGE], outputs=[ctrl.joint_f])
        solver.step(s0, s1, ctrl, None, dt); s0, s1 = s1, s0
    if viewer is not None: viewer.close()
    return dict(t=np.array(T), th=np.array(TH), om=np.array(OM), body=np.array(BODY), m_bus=m_bus, K=K, C=C, KL=KL, CL=CL, Kc=Kc)

def analyse(r, free_bus=True):
    t = r["t"]; th = r["th"]; om = r["om"]
    phi = np.pi - SIGN[None, :] * th                      # rotation done in the mirrored "latch at pi" coordinate (hinge 0: latch at pi/2 via stroke)
    phi = STROKE[None, :] - SIGN[None, :] * th            # 0 stowed -> STROKE latched
    phid = -SIGN[None, :] * om
    rest = STROKE + OVER
    tau_drive = r["K"][None, :] * (rest[None, :] - phi) - r["C"][None, :] * phid          # spring + damper torque driving the hinge (N m)
    pen = np.maximum(phi - STROKE[None, :], 0.0)
    tau_latch = np.where(pen > 0, r["KL"][None, :] * pen + r["CL"][None, :] * phid, 0.0)
    out = dict(n_hinge=N_HINGE)
    # latch times: first time phi >= stroke - 0.5 deg ; settle time: last time |phi - stroke| > 2 deg
    tl, ts = [], []
    for i in range(N_HINGE):
        hit = np.where(phi[:, i] >= STROKE[i])[0]; tl.append(float(t[hit[0]]) if len(hit) else None)
        off = np.where(np.abs(phi[:, i] - STROKE[i]) > math.radians(2.0))[0]; ts.append(float(t[off[-1] + 1]) if len(off) and off[-1] + 1 < len(t) else (0.0 if not len(off) else None))
    out["t_latch_first_contact_s"] = tl; out["t_settle_2deg_s"] = ts
    ok = [x for x in tl if x is not None]
    out["n_latched"] = len(ok); out["t_all_latched_s"] = max(ok) if len(ok) == N_HINGE else None
    out["t_all_settled_s"] = max(ts) if all(x is not None for x in ts) else None
    # out-of-order: for a Z-fold the outboard hinge should not latch before the inboard one (root first), report inversions vs root-to-tip order
    inv = sum(1 for i in range(N_HINGE - 1) if tl[i] is not None and tl[i + 1] is not None and tl[i + 1] < tl[i] - 1e-9)
    out["latch_order_inversions_root_to_tip"] = inv
    out["latch_time_spread_s"] = (max(ok) - min(ok)) if ok else None
    out["peak_spring_torque_stowed_Nm"] = (r["K"] * (rest - 0.0)).tolist()
    out["peak_drive_torque_Nm"] = np.abs(tau_drive).max(0).tolist()
    out["peak_latch_torque_Nm"] = tau_latch.max(0).tolist()
    out["peak_latch_torque_max_Nm"] = float(tau_latch.max())
    out["peak_latch_torque_hinge"] = int(tau_latch.max(0).argmax())
    out["peak_drive_torque_max_Nm"] = float(np.abs(tau_drive).max())
    # worst out-of-sync: max |u_i - u_{i+1}| in fractions while deploying
    u = phi / STROKE[None, :]
    out["max_sync_error_frac"] = float(np.abs(u[:, 1:] - u[:, :-1]).max())
    out["max_overshoot_deg"] = (np.degrees((phi - STROKE[None, :]).max(0))).tolist()
    # CCL load
    if r["Kc"].any():
        dcc = (u[:, :-1] - u[:, 1:]); tq = np.abs(r["Kc"][None, :-1] * dcc)    # torque in u-space; cable torque ~ Kc*du / stroke
        cab = np.abs(r["Kc"][None, :-1] * dcc / STROKE[None, :-1])
        out["ccl_peak_cable_torque_Nm"] = float(cab.max()); out["ccl_peak_cable_tension_N_at_r"] = float(cab.max() / CCL_PULLEY_R)
    if free_bus:
        B = r["body"]; yaw = np.unwrap(2 * np.arctan2(B[:, :, 5], B[:, :, 6]), axis=0)
        out["bus_yaw_final_deg"] = float(np.degrees(yaw[-1, 0])); out["bus_yaw_peak_deg"] = float(np.degrees(np.abs(yaw[:, 0]).max()))
        w = np.gradient(yaw[:, 0], t); out["bus_rate_peak_deg_s"] = float(np.degrees(np.abs(w).max()))
        masses = np.concatenate([[r["m_bus"]], MASS])
        Izz = np.concatenate([[r["m_bus"] * (BX**2 + BY**2) / 12], MASS * LEN**2 / 12])
        com = (B[:, :, :2] * masses[None, :, None]).sum(1) / masses.sum()
        pos = B[:, :, :2] - com[:, None, :]; v = np.gradient(pos, t, axis=0); wb = np.gradient(yaw, t, axis=0)
        Lz = (masses[None, :] * (pos[:, :, 0] * v[:, :, 1] - pos[:, :, 1] * v[:, :, 0]) + Izz[None, :] * wb).sum(1)
        Lwing = (masses[None, 1:] * (pos[:, 1:, 0] * v[:, 1:, 1] - pos[:, 1:, 1] * v[:, 1:, 0]) + Izz[None, 1:] * wb[:, 1:]).sum(1)
        out["ang_mom_total_max_abs"] = float(np.abs(Lz).max()); out["ang_mom_wing_peak_Nms"] = float(np.abs(Lwing).max())
        out["bus_Izz_kgm2"] = float(r["m_bus"] * (BX**2 + BY**2) / 12)
        out["com_drift_m"] = float(np.abs(com - com[0]).max())
        out["bus_xy_shift_m"] = float(np.linalg.norm(B[-1, 0, :2] - B[0, 0, :2]))
        out["_bus_yaw_deg"] = np.degrees(yaw[:, 0]).round(4).tolist()
    out["_t"] = t.tolist(); out["_phi_deg"] = np.degrees(phi[:, [0, 1, 5, 10, 15, 20]]).round(3).tolist()
    out["_tau_latch"] = tau_latch[:, [0, 10, 20]].round(2).tolist()
    return out

def validate():
    """one leaf hinge (the tip leaf, hinge 20) on a fixed base: Newton Featherstone vs exact piecewise-linear closed form (run_hinge.closed_form)."""
    i = N_LEAF
    I = I_OUT[i]
    H.M_PANEL = MASS[i]; H.L = LEN[i]; H.I = I; H.W0 = W0; H.K = I * W0**2; H.TH_REST = math.pi + OVER; H.TH_L = math.pi
    H.ZETA = ZETA; H.C = 2 * ZETA * math.sqrt(H.K * I); H.KL = I * WL**2; H.ZL = ZL; H.CL = 2 * ZL * I * WL
    res = {}
    t_end = 40.0
    for dt in (5e-4, 1e-3):
        cf = H.closed_form(t_end, int(round(t_end / dt)) + 1)
        r = H.run_newton(dt, t_end, "featherstone")
        pen = np.maximum(r["th"] - H.TH_L, 0.0); trq = np.where(pen > 0, H.KL * pen + H.CL * r["om"], 0.0)
        res[str(dt)] = dict(I=I, K=H.K, C=H.C, KL=H.KL, CL=H.CL, tL_closed=cf["tL"], tL_newton=float(r["t"][np.argmax(r["th"] >= H.TH_L)]),
                            peak_closed_Nm=float(cf["trq"].max()), peak_newton_Nm=float(trq.max()),
                            max_err_deg_free_phase=float(np.degrees(np.abs(r["th"] - cf["th"])[cf["t"] < cf["tL"]].max())),
                            max_err_deg_all=float(np.degrees(np.abs(r["th"] - cf["th"]).max())), wall_s=r["wall"],
                            overshoot_closed_deg=float(np.degrees(cf["th"].max() - H.TH_L)), overshoot_newton_deg=float(np.degrees(r["th"].max() - H.TH_L)))
        if dt == 5e-4:
            sl = slice(None, None, 400)
            res["series"] = dict(t=cf["t"][sl].tolist(), cf_deg=np.degrees(cf["th"][sl]).tolist(), nw_deg=np.degrees(r["th"][sl]).tolist())
            k = np.argmax(cf["trq"]); j0, j1 = max(k - 3000, 0), k + 3000
            res["impact"] = dict(t=cf["t"][j0:j1:20].tolist(), cf_trq=cf["trq"][j0:j1:20].tolist(), nw_trq=trq[j0:j1:20].tolist())
        print(dt, res[str(dt)], flush=True)
    json.dump(res, open(os.path.join(RES, f"validate_leaf_hinge{TAG}.json"), "w"))

if __name__ == "__main__":
    case = sys.argv[1]
    if case == "validate": validate(); sys.exit()
    dt = float(sys.argv[2]) if len(sys.argv) > 2 else 5e-4; t_end = float(sys.argv[3]) if len(sys.argv) > 3 else 80.0
    t0 = time.time()
    r = run(case, dt, t_end, usd=os.path.join(RES, f"array_deploy_{case}{TAG}.usd") if case in ("ccl", "tuned") else None)
    out = analyse(r); out.update(case=case, dt=dt, t_end=t_end, wall_s=time.time() - t0, W0=W0, ZETA=ZETA, OVER_deg=math.degrees(OVER), WL=WL, ZL=ZL,
                                 K=r["K"].tolist(), C=r["C"].tolist(), KL=r["KL"].tolist(), I_out=I_OUT.tolist(), m_bus=r["m_bus"])
    json.dump(out, open(os.path.join(RES, f"array_{case}{TAG}.json"), "w"))
    print({k: v for k, v in out.items() if not k.startswith("_") and not isinstance(v, list)}, flush=True)
