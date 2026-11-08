"""Phase 2 chunk 1: planar rigid Z-fold array-leaf chain (yoke + 20 leaves = 21 hinges, 45 C baseline, RTS_TAG=_T45), fixed bus,
batched over worlds with a NVIDIA Warp kernel (one thread per world, forward dynamics by the exact planar mass matrix, Cholesky solve).
Free-motion dynamics cross-checked against the Newton 1.7.0 Featherstone chain by newton_xcheck_T45.py (chunk 2; latch capture is not yet stable in Newton at dt 10 ms).  Every hinge number is an ESTIMATE.
Modes: spring (per-hinge torsion springs + damper + penalty latch) or motor (per-hinge PD motor following one common deploy profile, torque limited).
usage: RTS_TAG=_T45 python fold_chain_T45.py nominal|sweep|mc|check  (see main)"""
import sys, os, json, math, time
import numpy as np
import warp as wp
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "newton_array"))
os.environ.setdefault("RTS_TAG", "_T45")
import run_array as A          # geometry, masses (T45 baseline), stroke, sign
wp.config.quiet = True
RES = os.path.join(HERE, "..", "..", "results", "phase2_T45"); os.makedirs(RES, exist_ok=True)
N = A.N_HINGE; LEN = A.LEN; MASS = A.MASS; STROKE = A.STROKE; SIGN = A.SIGN; I_OUT = A.I_OUT
IZ = MASS * LEN**2 / 12
ROOT_T=float(os.environ.get('LOCK_ROOT_SECONDS','180')); MAIN_T=float(os.environ.get('LOCK_MAIN_SECONDS','600'))
KLAT = 2.0e4; ZLAT = 0.3          # ESTIMATE latch angular stiffness N m/rad and damping ratio on the leaf's own hinge inertia
OVER = math.radians(10.0); OVR = math.radians(3.0)

@wp.kernel
def chain_kernel(n: int, nsteps: int, dt: float, rec_every: int,
                 len_: wp.array(dtype=float), mass: wp.array(dtype=float), iz: wp.array(dtype=float), sgn: wp.array(dtype=float), stroke: wp.array(dtype=float), child_: wp.array(dtype=float), com_: wp.array(dtype=float),
                 kspr: wp.array2d(dtype=float), cdamp: wp.array2d(dtype=float), fric: wp.array2d(dtype=float), dlatch: wp.array2d(dtype=float),
                 klat: wp.array(dtype=float), clat: wp.array(dtype=float), over: float,
                 mode: wp.array(dtype=int), tdep: wp.array(dtype=float), kp: wp.array2d(dtype=float), kd: wp.array2d(dtype=float), tmax: wp.array2d(dtype=float),
                 eps_v: float, ovr: float,
                 # scratch
                 th: wp.array2d(dtype=float), om: wp.array2d(dtype=float), Mm: wp.array3d(dtype=float), rhs: wp.array2d(dtype=float),
                 P: wp.array3d(dtype=float), C: wp.array3d(dtype=float), VP: wp.array3d(dtype=float), VC: wp.array3d(dtype=float), AB: wp.array3d(dtype=float),
                 qdd: wp.array2d(dtype=float), Qt: wp.array2d(dtype=float), Ql: wp.array2d(dtype=float), Dc: wp.array2d(dtype=float),
                 # outputs
                 pk_hinge: wp.array2d(dtype=float), pk_latch: wp.array2d(dtype=float), pk_rootF: wp.array(dtype=float), pk_rootM: wp.array(dtype=float),
                 t_latch: wp.array2d(dtype=float), dfin: wp.array2d(dtype=float), hist: wp.array3d(dtype=float), nrec: int):
    w = wp.tid()
    for i in range(n):
        th[w, i] = sgn[i] * stroke[i]; om[w, i] = 0.0; t_latch[w, i] = -1.0
        pk_hinge[w, i] = 0.0; pk_latch[w, i] = 0.0
    pk_rootF[w] = 0.0; pk_rootM[w] = 0.0
    for step in range(nsteps+1):
        t = float(step) * dt
        # ---- kinematics ----
        a = float(0.0); wabs = float(0.0)
        P[w, 0, 0] = 0.0; P[w, 0, 1] = 0.0; VP[w, 0, 0] = 0.0; VP[w, 0, 1] = 0.0
        for i in range(n):
            a = a + th[w, i]; wabs = wabs + om[w, i]
            ca = wp.cos(a); sa = wp.sin(a); L = len_[i]
            rx = 0.5 * L * ca + (child_[i]-com_[i]) * sa; ry = 0.5 * L * sa - (child_[i]-com_[i]) * ca
            C[w, i, 0] = P[w, i, 0] + rx; C[w, i, 1] = P[w, i, 1] + ry
            VC[w, i, 0] = VP[w, i, 0] - wabs * ry; VC[w, i, 1] = VP[w, i, 1] + wabs * rx
            dy = float(0.0)
            if i+1 < n:
                dy = child_[i+1]-child_[i]
            rx=L*ca-dy*sa; ry=L*sa+dy*ca
            P[w, i + 1, 0] = P[w, i, 0] + rx; P[w, i + 1, 1] = P[w, i, 1] + ry
            VP[w, i + 1, 0] = VP[w, i, 0] - wabs * ry; VP[w, i + 1, 1] = VP[w, i, 1] + wabs * rx
        # bias acceleration of each COM: sum_{j<=k} om_j * zhat x (vc_k - vp_j)
        for k in range(n):
            ax = float(0.0); ay = float(0.0)
            for j in range(k + 1):
                dx = VC[w, k, 0] - VP[w, j, 0]; dy = VC[w, k, 1] - VP[w, j, 1]
                ax = ax - om[w, j] * dy; ay = ay + om[w, j] * dx
            AB[w, k, 0] = ax; AB[w, k, 1] = ay
        # ---- applied joint torques (theta coordinates) ----
        md = mode[w]
        u = float(0.0); ud = float(0.0)
        if md == 1:
            x = t / tdep[w]
            if x > 1.0:
                x = 1.0
            u = x * x * x * (10.0 - 15.0 * x + 6.0 * x * x)      # min-jerk deploy fraction 0..1
            if t < tdep[w]:
                ud = 30.0 * x * x * (1.0 - x) * (1.0 - x) / tdep[w]
            u = u * (1.0 + 0.0)
        for i in range(n):
            if md == 1:
                dur=MAIN_T; start=ROOT_T
                if i==0:
                    dur=ROOT_T; start=0.0
                x=wp.clamp((t-start)/dur,0.0,1.0)
                u=x*x*x*(10.0-15.0*x+6.0*x*x); ud=float(0.0)
                if t>start and t<start+dur:
                    ud=30.0*x*x*(1.0-x)*(1.0-x)/dur
            d = sgn[i] * th[w, i]; dd = sgn[i] * om[w, i]        # d = remaining deploy angle (stroke ... 0 at latch), dd its rate
            Fd = float(0.0); Fl = float(0.0)
            if md == 0:
                Fd = -kspr[w, i] * (d + over) - cdamp[w, i] * dd
            else:
                dcmd = stroke[i] * (1.0 - u) - ovr * u
                Fm = -kp[w, i] * (d - dcmd) - kd[w, i] * (dd + stroke[i] * ud)
                if Fm > tmax[w, i]:
                    Fm = tmax[w, i]
                if Fm < -tmax[w, i]:
                    Fm = -tmax[w, i]
                Fd = Fm
            # latch: captured when d reaches dlatch, then held two-sided (ratchet / over-centre lock model, ESTIMATE)
            pen = dlatch[w, i] - d
            capt = float(0.0)
            if pen > 0.0 and t_latch[w, i] < 0.0:
                t_latch[w, i] = t
            if t_latch[w, i] >= 0.0:
                capt = 1.0
                Fd = 0.0  # disable motor after captured mechanical lock
                Fl = klat[i] * pen - clat[i] * dd
            # stow-side stop: adjacent stacked leaves / launch lock cannot be over-folded (one-sided contact)
            if d > stroke[i]:
                Fd = Fd - klat[i] * (d - stroke[i])
                if dd > 0.0:
                    Fd = Fd - clat[i] * dd
            # Coulomb friction (regularised), always opposing rate
            Ff = -fric[w, i] * wp.tanh(dd / eps_v)
            Dc[w, i] = dt * (cdamp[w, i] + fric[w, i] / eps_v * (1.0 - wp.tanh(dd / eps_v) * wp.tanh(dd / eps_v)))
            if md == 1 and capt == 0.0:
                Dc[w, i] = Dc[w, i] + dt * kd[w, i]
            if capt > 0.0 or d > stroke[i]:
                Dc[w, i] = Dc[w, i] + dt * clat[i]
            Ql[w, i] = sgn[i] * Fl
            Qt[w, i] = sgn[i] * (Fd + Fl + Ff)
        # mass matrix and bias
        for i in range(n):
            hb = float(0.0)
            for k in range(i, n):
                rx = C[w, k, 0] - P[w, i, 0]; ry = C[w, k, 1] - P[w, i, 1]
                hb = hb + mass[k] * (-ry * AB[w, k, 0] + rx * AB[w, k, 1])
            rhs[w, i] = -hb
            for j in range(i + 1):
                s = float(0.0)
                for k in range(i, n):
                    s = s + iz[k] + mass[k] * ((C[w, k, 0] - P[w, i, 0]) * (C[w, k, 0] - P[w, j, 0]) + (C[w, k, 1] - P[w, i, 1]) * (C[w, k, 1] - P[w, j, 1]))
                Mm[w, i, j] = s
            Mm[w, i, i] = Mm[w, i, i] + Dc[w, i]
        for i in range(n):
            rhs[w, i] = rhs[w, i] + Qt[w, i]
        # ---- Cholesky solve (lower stored) ----
        for j in range(n):
            s = Mm[w, j, j]
            for k in range(j):
                s = s - Mm[w, j, k] * Mm[w, j, k]
            dj = wp.sqrt(s); Mm[w, j, j] = dj
            for i in range(j + 1, n):
                s2 = Mm[w, i, j]
                for k in range(j):
                    s2 = s2 - Mm[w, i, k] * Mm[w, j, k]
                Mm[w, i, j] = s2 / dj
        for i in range(n):
            s = rhs[w, i]
            for k in range(i):
                s = s - Mm[w, i, k] * qdd[w, k]
            qdd[w, i] = s / Mm[w, i, i]
        for ii in range(n):
            i = n - 1 - ii
            s = qdd[w, i]
            for k in range(i + 1, n):
                s = s - Mm[w, k, i] * qdd[w, k]
            qdd[w, i] = s / Mm[w, i, i]
        # ---- loads: hinge torque = applied torque row, root force = sum m a_c ----
        fx = float(0.0); fy = float(0.0)
        for k in range(n):
            ax = AB[w, k, 0]; ay = AB[w, k, 1]
            for j in range(k + 1):
                rx = C[w, k, 0] - P[w, j, 0]; ry = C[w, k, 1] - P[w, j, 1]
                ax = ax - qdd[w, j] * ry; ay = ay + qdd[w, j] * rx
            fx = fx + mass[k] * ax; fy = fy + mass[k] * ay
        fr = wp.sqrt(fx * fx + fy * fy)
        if fr > pk_rootF[w]:
            pk_rootF[w] = fr
        for i in range(n):
            q = wp.abs(Qt[w, i])
            if q > pk_hinge[w, i]:
                pk_hinge[w, i] = q
            ql = wp.abs(Ql[w, i])
            if ql > pk_latch[w, i]:
                pk_latch[w, i] = ql
        if wp.abs(Qt[w, 0]) > pk_rootM[w]:
            pk_rootM[w] = wp.abs(Qt[w, 0])
        # ---- history ----
        if step % rec_every == 0:
            r = step // rec_every
            if r < nrec:
                for i in range(n):
                    hist[w, r, i] = th[w, i]
        # ---- semi-implicit Euler ----
        if step < nsteps:
            for i in range(n):
                om[w, i] = om[w, i] + dt * qdd[w, i]
                th[w, i] = th[w, i] + dt * om[w, i]
    for i in range(n):
        dfin[w, i] = sgn[i] * th[w, i]

F_NOM = 2.0       # N m, ESTIMATE nominal hinge friction (bearing preload + harness / MLI drag), every hinge
def spring_set(margin=3.0, tau_c=20.0, f_nom=F_NOM):
    """spring torque at the latch (K * over) = margin x f_nom; damper c = tau_c * K  (tau_c in s sets the overdamped deploy time, about 3 tau_c)"""
    K = np.full(N, margin * f_nom / OVER); C = tau_c * K
    return K, C

def run(B, mode, K, Cd, fric, dlatch, tdep=60.0, tend=60.0, dt=2e-3, kp=None, kd=None, tmax=None, rec_every=500, eps_v=1e-3, klat_val=None, zlat_val=None):
    """K, Cd, fric, dlatch, kp, kd, tmax: (B,N) arrays (or broadcastable); mode: scalar 0 spring / 1 motor"""
    f = lambda x: wp.array(np.broadcast_to(np.asarray(x, float), (B, N)).copy(), dtype=float, ndim=2)
    z = lambda: wp.zeros((B, N), dtype=float)
    nsteps = int(round(tend / dt)); nrec = nsteps // rec_every + 1
    kl_ = KLAT if klat_val is None else klat_val; zl_ = ZLAT if zlat_val is None else zlat_val   # chunk 3: latch stiffness/damping overrides (N m/rad, ratio)
    klat = np.full(N, kl_); clat = 2 * zl_ * np.sqrt(kl_ * np.minimum(I_OUT,float(os.environ.get('LOCK_DAMP_CAP','64'))*MASS*LEN**2/3))
    kp = np.zeros(N) if kp is None else kp; kd = np.zeros(N) if kd is None else kd; tmax = np.zeros(N) if tmax is None else tmax
    out = dict(pk_hinge=z(), pk_latch=z(), pk_rootF=wp.zeros(B, dtype=float), pk_rootM=wp.zeros(B, dtype=float), t_latch=z(), dfin=z(), hist=wp.zeros((B, nrec, N), dtype=float))
    ws = dict(th=z(), om=z(), Mm=wp.zeros((B, N, N), dtype=float), rhs=z(), P=wp.zeros((B, N + 1, 2), dtype=float), C=wp.zeros((B, N, 2), dtype=float),
              VP=wp.zeros((B, N + 1, 2), dtype=float), VC=wp.zeros((B, N, 2), dtype=float), AB=wp.zeros((B, N, 2), dtype=float), qdd=z(), Qt=z(), Ql=z(), Dc=z())
    v1 = lambda x: wp.array(np.asarray(x, float), dtype=float)
    t0 = time.time()
    wp.launch(chain_kernel, dim=B, inputs=[N, nsteps, dt, rec_every, v1(LEN), v1(MASS), v1(IZ), v1(SIGN), v1(STROKE), v1(A.CHILD_OFF), v1(A.COM_OFF), f(K), f(Cd), f(fric), f(dlatch), v1(klat), v1(clat), OVER,
              wp.array(np.full(B, mode, np.int32), dtype=int), v1(np.broadcast_to(np.asarray(tdep, float), (B,))), f(kp), f(kd), f(tmax), eps_v, OVR,
              ws["th"], ws["om"], ws["Mm"], ws["rhs"], ws["P"], ws["C"], ws["VP"], ws["VC"], ws["AB"], ws["qdd"], ws["Qt"], ws["Ql"], ws["Dc"],
              out["pk_hinge"], out["pk_latch"], out["pk_rootF"], out["pk_rootM"], out["t_latch"], out["dfin"], out["hist"], nrec])
    wp.synchronize()
    r = {k: v.numpy() for k, v in out.items()}; r["wall_s"] = time.time() - t0; r["dt"] = dt; r["rec_every"] = rec_every
    return r

def summarize(r, i=0):
    d = r["dfin"][i]; tl = r["t_latch"][i]
    return dict(n_latched=int((tl >= 0).sum()), n_hinges=N, d_final_deg_max=float(np.degrees(np.abs(d).max())), d_final_deg=np.degrees(d).round(2).tolist(), t_latch_first_s=float(tl[tl >= 0].min()) if (tl >= 0).any() else None,
                t_latch_last_s=float(tl.max()) if (tl >= 0).all() else None, peak_hinge_Nm_max=float(r["pk_hinge"][i].max()), peak_hinge_hinge=int(r["pk_hinge"][i].argmax()),
                peak_latch_Nm_max=float(r["pk_latch"][i].max()), peak_rootF_N=float(r["pk_rootF"][i]), peak_rootM_Nm=float(r["pk_rootM"][i]))
