"""Phase 2 chunk 2 (1): cross-check of the 21-hinge array chain in NVIDIA Newton 1.7.0 (SolverFeatherstone) against the Warp chain kernel.
Newton supplies the multibody dynamics (fixed bus, planar chain, same geometry/masses as newton_array/run_array.py).  The hinge torque model (min-jerk PD motor with
torque limit, Coulomb friction, captured latch, stow stop) is the same ESTIMATE model as fold_chain_T45.py, applied through Control.joint_f by a small Warp kernel.
usage: RTS_TAG=_T45 python newton_xcheck_T45.py motor TDEP [DT] [fric_scale_hinge fric_scale] | spring [DT]  [--no-implicit-damp]      (GB10 desktop)"""
import sys, os, json, math, time
import numpy as np
import warp as wp, newton
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "newton_array"))
os.environ.setdefault("RTS_TAG", "_T45")
import run_array as A
import fold_chain_T45 as F

def motor_par2(margin, tdep):
    """same inertia-aware motor sizing as run_phase2_motor2.py (copied: that module runs its study at import)"""
    tin = F.I_OUT * 5.77 * F.STROKE / np.where(np.arange(N)==0,ROOT_T,MAIN_T)**2
    tmax = margin * (F.F_NOM + tin); kp = tmax / math.radians(3.0)
    kd = 2 * 0.7 * np.sqrt(kp * F.MASS * F.LEN**2 / 3)
    return kp, kd, tmax, tin
wp.config.quiet = True
N = F.N
ROOT_T=F.ROOT_T; MAIN_T=F.MAIN_T

@wp.kernel
def torque_kernel(tt: wp.array(dtype=wp.float64), q: wp.array(dtype=float), qd: wp.array(dtype=float), sgn: wp.array(dtype=float), stroke: wp.array(dtype=float), mode: int, tdep: float,
                  kp: wp.array(dtype=float), kd: wp.array(dtype=float), tmax: wp.array(dtype=float), fric: wp.array(dtype=float), kspr: float, cdamp: float, over: float, ovr: float,
                  klat: wp.array(dtype=float), clat: wp.array(dtype=float), eps_v: float, f: wp.array(dtype=float),
                  t_latch: wp.array(dtype=float), pk: wp.array(dtype=float)):
    i = wp.tid()
    t = float(tt[0])
    d = sgn[i] * q[i]; dd = sgn[i] * qd[i]
    Fd = float(0.0); Fl = float(0.0)
    if mode == 0:
        Fd = -kspr * (d + over) - cdamp * dd
    else:
        dur=MAIN_T; start=ROOT_T
        if i==0:
            dur=ROOT_T; start=0.0
        x = wp.clamp((t-start)/dur, 0.0, 1.0)
        u = x * x * x * (10.0 - 15.0 * x + 6.0 * x * x)
        ud = float(0.0)
        if t>start and t<start+dur:
            ud = 30.0 * x * x * (1.0 - x) * (1.0 - x) / dur
        dcmd = stroke[i] * (1.0 - u) - ovr * u
        Fm = -kp[i] * (d - dcmd) - kd[i] * (dd + stroke[i] * ud)
        Fd = wp.clamp(Fm, -tmax[i], tmax[i])
    pen = 0.0 - d
    if pen > 0.0 and t_latch[i] < 0.0:
        t_latch[i] = t
    if t_latch[i] >= 0.0:
        Fd = 0.0  # captured mechanical lock: disable motor overdrive
        Fl = klat[i] * pen - clat[i] * dd
    if d > stroke[i]:
        Fd = Fd - klat[i] * (d - stroke[i])
        if dd > 0.0:
            Fd = Fd - clat[i] * dd
    Ff = -fric[i] * wp.tanh(dd / eps_v)
    Qt = sgn[i] * (Fd + Fl + Ff)
    f[i] = Qt
    pk[i] = wp.max(pk[i], wp.abs(Qt))

@wp.kernel
def advance(tt: wp.array(dtype=wp.float64), dt: float):
    tt[0] = tt[0] + wp.float64(dt)

@wp.kernel
def arm_kernel(q: wp.array(dtype=float), qd: wp.array(dtype=float), sgn: wp.array(dtype=float), stroke: wp.array(dtype=float), kd: wp.array(dtype=float), fric: wp.array(dtype=float),
               clat: wp.array(dtype=float), tl: wp.array(dtype=float), eps_v: float, dt: float, arm0: wp.array(dtype=float), arm: wp.array(dtype=float)):
    # t476/t491 fix: same semi-implicit damping as the Warp reference (fold_chain_T45 Dc term on the mass-matrix diagonal):
    # dt * (motor kd + d(friction)/d(rate) + latch/stop damping when engaged), written into joint_armature before each Featherstone step
    # (Featherstone rebuilds the mass matrix every step, so the armature acts as the implicit damping term).  Off: --no-implicit-damp
    i = wp.tid(); d = sgn[i] * q[i]; dd = sgn[i] * qd[i]; th = wp.tanh(dd / eps_v)
    c = fric[i] / eps_v * (1.0 - th * th)
    if tl[i] < 0.0:
        c = c + kd[i]
    if tl[i] >= 0.0 or d > stroke[i]:
        c = c + clat[i]
    arm[i] = arm0[i] + dt * c

def build():
    K, C, KL, CL, Kc = A.hinge_params("tuned")
    model, m_bus, _ = A.build("tuned", free_bus=False)
    for nm in ("joint_target_ke", "joint_target_kd", "joint_limit_ke", "joint_limit_kd"):
        a = getattr(model, nm); a.assign(np.zeros(a.shape, dtype=np.float32))
    return model

def run(mode, tdep=300.0, dt=4e-3, tend=None, fric_scale=None, margin=3.0, tau=10.0, rec_every=None, klat_val=None, zlat_val=None, implicit_damp=True):
    rec_every = rec_every or int(round(1.0 / dt))
    model = build(); tend = tend if tend is not None else (tdep + 90.0 if mode == "motor" else 600.0)
    s0, s1 = model.state(), model.state(); ctrl = model.control()
    q0 = F.SIGN * F.STROKE
    s0.joint_q.assign(q0.astype(np.float32)); s1.joint_q.assign(q0.astype(np.float32)); newton.eval_fk(model, s0.joint_q, s0.joint_qd, s0)
    solver = newton.solvers.SolverFeatherstone(model)
    fr = np.full(N, F.F_NOM)
    if fric_scale:
        for h, s in fric_scale.items(): fr[h] *= s
    kp, kd, tmax, _ = motor_par2(margin, tdep)
    Ksp, Cd = F.spring_set(margin, tau)
    kl_ = F.KLAT if klat_val is None else klat_val; zl_ = F.ZLAT if zlat_val is None else zlat_val
    clat = 2 * zl_ * np.sqrt(kl_ * np.minimum(F.I_OUT,float(os.environ.get('LOCK_DAMP_CAP','64'))*F.MASS*F.LEN**2/3))
    dev = lambda x: wp.array(np.asarray(x, np.float32), dtype=float)
    sg, stk, kpd, kdd, tmx, frd, kl, cl = dev(F.SIGN), dev(F.STROKE), dev(kp), dev(kd), dev(tmax), dev(fr), dev(np.full(N, kl_)), dev(clat)
    tl = dev(np.full(N, -1.0)); pk = dev(np.zeros(N)); ctrl.joint_f.assign(np.zeros(N, dtype=np.float32))
    n = int(round(tend / dt)); H = []; t0 = time.time(); md = 1 if mode == "motor" else 0
    tt = wp.array(np.array([0.],np.float64),dtype=wp.float64)
    arm0 = wp.clone(model.joint_armature); assert arm0.shape[0] == N, arm0.shape
    def one(a, b):
        if implicit_damp:
            wp.launch(arm_kernel, dim=N, inputs=[a.joint_q, a.joint_qd, sg, stk, kdd, frd, cl, tl, 1e-3, float(dt), arm0], outputs=[model.joint_armature])
        wp.launch(torque_kernel, dim=N, inputs=[tt, a.joint_q, a.joint_qd, sg, stk, md, float(tdep), kpd, kdd, tmx, frd, float(Ksp[0]), float(Cd[0]), F.OVER, F.OVR, kl, cl, 1e-3],
                  outputs=[ctrl.joint_f, tl, pk])
        solver.step(a, b, ctrl, None, dt)
        wp.launch(advance, dim=1, inputs=[tt, dt])
    # warm-up step is skipped: capture two steps (s0->s1, s1->s0) as one CUDA graph; state is restored by re-assigning q after capture
    q_init = s0.joint_q.numpy().copy()
    with wp.ScopedCapture() as cap:
        
        for _ in range(50):
            one(s0, s1); one(s1, s0)
    graph = cap.graph
    s0.joint_q.assign(q_init); s0.joint_qd.zero_(); s1.joint_qd.zero_(); tt.assign(np.array([0.0], np.float64)); tl.assign(np.full(N, -1.0, np.float32)); pk.zero_()
    newton.eval_fk(model, s0.joint_q, s0.joint_qd, s0)
    t0 = time.time()
    t_nan = None; PK = []
    for i in range(0, n + 1, 100):
        if i % 10000 == 0: print(f'Newton t={i*dt:.1f}s / {tend:g}s',flush=True)
        if i % rec_every == 0:
            qn = s0.joint_q.numpy().copy(); H.append(qn); PK.append(pk.numpy().copy())
            if not np.isfinite(qn).all() or not np.isfinite(PK[-1]).all():
                t_nan = i * dt; break
        if i >= n: break
        wp.capture_launch(graph)
    wp.synchronize(); wall = time.time() - t0
    PK = np.array(PK); good = np.isfinite(PK).all(1); pk_last = PK[good][-1] if good.any() else pk.numpy()
    return dict(h=np.array(H), t_latch=tl.numpy(), pk=pk_last, wall=wall, dt=dt, d_final=(F.SIGN * s0.joint_q.numpy())[:N], t_nan=t_nan, klat=kl_, zlat=zl_, implicit_damp=bool(implicit_damp))

def warp_ref(mode, tdep=300.0, dt=4e-3, tend=None, fric_scale=None, margin=3.0, tau=10.0):
    tend = tend if tend is not None else (tdep + 90.0 if mode == "motor" else 600.0)
    fr = np.full(N, F.F_NOM)
    if fric_scale:
        for h, s in fric_scale.items(): fr[h] *= s
    if mode == "motor":
        kp, kd, tmax, _ = motor_par2(margin, tdep); return F.run(1, 1, 0, 0, fr, 0.0, tdep=tdep, tend=tend, dt=dt, kp=kp, kd=kd, tmax=tmax, rec_every=int(round(1.0 / dt)))
    K, C = F.spring_set(margin, tau); return F.run(1, 0, K, C, fr, 0.0, tend=tend, dt=dt, rec_every=int(round(1.0 / dt)))

def compare(rn, rw, label):
    hn = rn["h"]; hw = rw["hist"][0]; m = min(len(hn), len(hw)); dth = np.degrees(np.abs(hn[:m] - hw[:m])); fin = np.isfinite(dth).all(1); dth = dth[fin] if fin.any() else dth
    tw = rw["t_latch"][0]; tn = rn["t_latch"]; both = (tw >= 0) & (tn >= 0)
    out = dict(label=label, implicit_damp=rn.get("implicit_damp"), t_nan_newton_s=rn.get("t_nan"), klat=rn.get("klat"), zlat=rn.get("zlat"), newton_wall_s=rn["wall"], warp_wall_s=rw["wall_s"], dt=rn["dt"], n_latched_newton=int((tn >= 0).sum()), n_latched_warp=int((tw >= 0).sum()),
               max_angle_diff_deg=float(dth.max()), rms_angle_diff_deg=float(np.sqrt((dth**2).mean())),
               max_angle_diff_deg_per_hinge_p50=float(np.median(dth.max(0))),
               latch_time_diff_s_max=float(np.abs(tn[both] - tw[both]).max()) if both.any() else None,
               t_latch_last_newton=float(tn.max()) if (tn >= 0).all() else None, t_latch_last_warp=float(tw.max()) if (tw >= 0).all() else None,
               peak_torque_newton=float(rn["pk"].max()), peak_torque_warp=float(rw["pk_hinge"][0].max()),
               peak_root_moment_newton=float(rn["pk"][0]), peak_root_moment_warp=float(rw["pk_rootM"][0]),
               final_err_deg_newton=float(np.degrees(np.abs(rn["d_final"]).max())), final_err_deg_warp=float(np.degrees(np.abs(rw["dfin"][0]).max())))
    return out

if __name__ == "__main__":
    mode = sys.argv[1]
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--klat", type=float); ap.add_argument("--zlat", type=float); ap.add_argument("--tend", type=float); ap.add_argument("--tag", default="")
    ap.add_argument("--no-implicit-damp", dest="imp", action="store_false", help="t476 fix off (old explicit damping; NaNs near 263-270 s in variant B)")
    ex, rest = ap.parse_known_args(sys.argv[2:]); sys.argv = [sys.argv[0], mode] + rest
    if ex.klat: F.KLAT = ex.klat
    if ex.zlat: F.ZLAT = ex.zlat
    if mode == "motor":
        tdep = float(sys.argv[2]); dt = float(sys.argv[3]) if len(sys.argv) > 3 else 4e-3
        fs = {int(sys.argv[4]): float(sys.argv[5])} if len(sys.argv) > 5 else None
        lab = "motor_tdep%g_dt%g%s%s" % (tdep, dt, "" if not fs else "_f%d_x%g" % list(fs.items())[0], ex.tag + ("" if ex.imp else "_explicit"))
        rn = run("motor", tdep, dt, tend=ex.tend, fric_scale=fs, klat_val=ex.klat, zlat_val=ex.zlat, implicit_damp=ex.imp); rw = warp_ref("motor", tdep, dt, tend=ex.tend, fric_scale=fs)
    else:
        dt = float(sys.argv[2]) if len(sys.argv) > 2 else 4e-3; lab = "spring_dt%g%s" % (dt, ex.tag + ("" if ex.imp else "_explicit"))
        rn = run("spring", dt=dt, tend=ex.tend, klat_val=ex.klat, zlat_val=ex.zlat, implicit_damp=ex.imp); rw = warp_ref("spring", dt=dt, tend=ex.tend)
    c = compare(rn, rw, lab); print(json.dumps(c, indent=1), flush=True)
    os.makedirs(F.RES, exist_ok=True); np.savez(os.path.join(F.RES, "xcheck_%s.npz" % lab), hn=rn["h"], hw=rw["hist"][0])
    json.dump(c, open(os.path.join(F.RES, "xcheck_%s.json" % lab), "w"), indent=1)
