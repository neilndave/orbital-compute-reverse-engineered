"""Single radiator-panel deployment hinge: Newton 1.7.0 (MuJoCo Warp) vs closed form.
Run on the GB10 in ~/gb10_work/venv_newton.  usage: python run_hinge.py [dt] [solver]
Bus is fixed (static parent).  Zero gravity.  Hinge axis +z, panel along local +x from the hinge.
All hinge numbers except the panel mass and L are ESTIMATE (see docs/NEWTON_DEPLOYMENT.md)."""
import sys, json, math, time, os
RESDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'results', 'newton_deploy'); os.makedirs(RESDIR, exist_ok=True)
import numpy as np
from scipy.optimize import brentq

M_PANEL = 12.871655          # kg, results/full3d/optimized_design.json as_built m_panel_kg (row 52)
L = 3.0                      # m, panel length (brief)
I = M_PANEL * L**2 / 3.0     # kg m^2 about the hinge (thin plate, brief)
TH_L = math.pi / 2           # rad, latch angle: ESTIMATE (a Z-fold stow-to-deploy panel would use 180 deg)
W0 = 1.0                     # rad/s, ESTIMATE: spring-mass natural frequency of the deployment hinge
K = I * W0**2                # N m/rad torsion spring rate (derived from the ESTIMATE W0)
TH_REST = math.pi            # rad, spring rest angle (preload: spring still pushes against the latch), ESTIMATE
ZETA = 0.5                   # ESTIMATE damper ratio of the deployment damper
C = 2 * ZETA * math.sqrt(K * I)
KL = 1.0e5                   # N m/rad latch stiffness: ESTIMATE
ZL = 0.1                     # ESTIMATE latch damping ratio (on k+KL)
CL = 2 * ZL * math.sqrt((K + KL) * I)

def _seg(th0, om0, k, c, eq, tau):
    """exact solution of I th'' + c th' + k (th - eq) = 0 (underdamped), from (th0, om0)."""
    w0 = math.sqrt(k / I); z = c / (2 * math.sqrt(k * I)); wd = w0 * math.sqrt(1 - z**2)
    a = th0 - eq; b = (om0 + z * w0 * a) / wd
    e = np.exp(-z * w0 * tau); cs = np.cos(wd * tau); sn = np.sin(wd * tau)
    th = eq + e * (a * cs + b * sn)
    om = e * (-z * w0 * (a * cs + b * sn) + wd * (-a * sn + b * cs))
    return th, om

def closed_form(t_end, n=4001):
    """Exact piecewise-linear solution of the SAME model Newton integrates:
    free phase  : I th'' + C th' + K (th - TH_REST) = 0
    stop phase  : (th > TH_L) adds KL (th - TH_L) + CL th' (penalty, no clipping, as Featherstone applies it).
    Phases switch whenever th crosses TH_L; events are located by root finding."""
    t = np.linspace(0, t_end, n); th = np.zeros(n); om = np.zeros(n); trq = np.zeros(n)
    ts, th0, om0, contact = 0.0, 0.0, 0.0, False
    first_contact = None
    while ts < t_end:
        k, c, eq = (K + KL, C + CL, (K * TH_REST + KL * TH_L) / (K + KL)) if contact else (K, C, TH_REST)
        idx = np.where(t >= ts)[0]
        tau = t[idx] - ts
        f_th, f_om = _seg(th0, om0, k, c, eq, tau)
        g = f_th - TH_L
        if contact: bad = np.where(g[1:] <= 0)[0]
        else: bad = np.where(g[1:] >= 0)[0]
        if len(bad):
            j = bad[0] + 1; hi = tau[j]; lo = tau[j - 1]
            sgn = 1.0 if contact else -1.0       # root of the signed distance, g>0 in contact
            tev = brentq(lambda x: float(_seg(th0, om0, k, c, eq, np.array(x))[0] - TH_L), lo, hi, xtol=1e-12) if lo > 0 else max(lo, 1e-9)
            sel = idx[:j]
            th[sel], om[sel] = f_th[:j], f_om[:j]
            nth, nom = _seg(th0, om0, k, c, eq, np.array(tev))
            th0, om0, ts = TH_L, float(nom), ts + tev
            if not contact and first_contact is None: first_contact = (ts, om0)
            contact = not contact
            if tev < 1e-9: ts += 1e-9
        else:
            th[idx], om[idx] = f_th, f_om; break
    pen = np.maximum(th - TH_L, 0.0)
    trq = np.where(pen > 0, KL * pen + CL * om, 0.0)
    tL, omL = first_contact
    return dict(t=t, th=th, om=om, trq=trq, tL=tL, omL=omL)

def run_newton(dt, t_end, solver_name="mujoco"):
    import warp as wp, newton
    wp.config.quiet = True
    b = newton.ModelBuilder(gravity=(0.0, 0.0, 0.0))
    com_inertia = np.diag([M_PANEL * L**2 / 20.0, M_PANEL * L**2 / 20.0, M_PANEL * L**2 / 12.0]).astype(np.float32)   # Izz about COM so I_hinge = m L^2/3
    body = b.add_link(xform=wp.transform_identity(), mass=M_PANEL, com=wp.vec3(0, 0, 0), inertia=wp.mat33(com_inertia))
    # hinge at world origin; COM is L/2 along +x of the hinge (child frame offset -L/2)
    jt = b.add_joint_revolute(parent=-1, child=body, axis=wp.vec3(0, 0, 1),
                         parent_xform=wp.transform_identity(), child_xform=wp.transform((-L / 2, 0.0, 0.0), wp.quat_identity()),
                         target_pos=TH_REST, target_vel=0.0, target_ke=K, target_kd=C,
                         limit_lower=-10.0, limit_upper=TH_L, limit_ke=KL, limit_kd=CL, armature=0.0,
                         actuator_mode=newton.JointTargetMode.POSITION)
    b.add_articulation([jt])
    model = b.finalize()
    s0, s1 = model.state(), model.state(); ctrl = model.control()
    print('ctrl target_pos before', ctrl.joint_target_q.numpy(), 'vel', ctrl.joint_target_qd.numpy(), flush=True)
    ctrl.joint_target_q.assign(np.array([TH_REST], dtype=np.float32)); ctrl.joint_target_qd.assign(np.array([0.0], dtype=np.float32))
    if solver_name == "mujoco":
        solver = newton.solvers.SolverMuJoCo(model, iterations=50, ls_iterations=50)
    elif solver_name == "featherstone":
        solver = newton.solvers.SolverFeatherstone(model)
    else:
        solver = newton.solvers.SolverSemiImplicit(model)
    newton.eval_fk(model, model.joint_q, model.joint_qd, s0)
    n = int(round(t_end / dt)); ts = np.zeros(n + 1); th = np.zeros(n + 1); om = np.zeros(n + 1)
    t0 = time.time()
    for i in range(n):
        solver.step(s0, s1, ctrl, None, dt)
        s0, s1 = s1, s0
        q = s0.joint_q.numpy(); qd = s0.joint_qd.numpy()
        ts[i + 1] = (i + 1) * dt; th[i + 1] = q[0]; om[i + 1] = qd[0]
    wall = time.time() - t0
    return dict(t=ts, th=th, om=om, wall=wall, model=model, state=s0)

if __name__ == "__main__":
    dt = float(sys.argv[1]) if len(sys.argv) > 1 else 2e-4
    sname = sys.argv[2] if len(sys.argv) > 2 else "mujoco"
    t_end = 4.0
    cf = closed_form(t_end, int(round(t_end / dt)) + 1)
    r = run_newton(dt, t_end, sname)
    pen = np.maximum(r["th"] - TH_L, 0.0)
    trq = np.where(pen > 0, KL * pen + CL * r["om"], 0.0)
    out = dict(dt=dt, solver=sname, I=I, K=K, C=C, KL=KL, CL=CL, TH_L=TH_L, TH_REST=TH_REST,
               tL_closed=cf["tL"], omL_closed=cf["omL"],
               peak_formula_wL_sqrtKLI=cf["omL"] * math.sqrt(KL * I),
               peak_closed_exact=float(cf["trq"].max()),
               peak_newton_penalty_recon=float(trq.max()),
               max_err_deg_phase1=float(np.degrees(np.abs(r["th"] - cf["th"])[cf["t"] < cf["tL"]].max())),
               first_stop_torque_peak_t=float(cf["t"][cf["trq"].argmax()]),
               max_err_deg_all=float(np.degrees(np.abs(r["th"] - cf["th"]).max())),
               max_err_pct_of_latch=float(100 * np.abs(r["th"] - cf["th"]).max() / TH_L),
               tL_newton=float(r["t"][np.argmax(r["th"] >= TH_L)]) if (r["th"] >= TH_L).any() else None,
               overshoot_closed_deg=float(np.degrees(cf["th"].max() - TH_L)), overshoot_newton_deg=float(np.degrees(r["th"].max() - TH_L)),
               final_th_newton_deg=float(np.degrees(r["th"][-1])), final_th_closed_deg=float(np.degrees(cf["th"][-1])),
               wall_s=r["wall"])
    print(json.dumps(out, indent=1))
    np.savez(f"{RESDIR}/hinge_{sname}_{dt:g}.npz", t=r["t"], th=r["th"], om=r["om"], trq=trq, cf_th=cf["th"], cf_trq=cf["trq"])
    json.dump(out, open(f"{RESDIR}/hinge_{sname}_{dt:g}.json", "w"), indent=1)
