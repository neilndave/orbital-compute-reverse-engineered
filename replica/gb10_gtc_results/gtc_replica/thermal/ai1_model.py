"""AI1 replica physics: (1) float64 Warp fin solves -> fin-efficiency table, (2) float64 Warp Monte Carlo of the required coolant supply temperature,
(3) host reference checks. Fin solver is the repo's rack_two_skies.warp_fin (copied unchanged to lib/warp_fin_ref.py).
MC input distributions follow experiments/thermal_mc/thermal_mc_c9_T45.py (INPUTS block); the radiator model itself (flat strips, no panel-to-panel view) is NEW and ASSUMED."""
import os, sys, json, math, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "lib"))
import warp as wp
wp.config.quiet = True
import ai1_specs as S
f64 = wp.float64
def get_devices(pref="auto"):
    wp.init(); n = wp.get_cuda_device_count()
    gpu = "cuda:0" if n > 0 else None
    return gpu
# ---------------------------------------------------------------- fin solves
def fin_eta(design, Tb, ee, Ts, device, nx=160, ny=8, tol=1e-9):
    """fin efficiency of the fin sheet (tube edge to mid-plane, half width L): Q / (2 ee sigma (Tb^4-Ts^4) L Ly).  Returns (eta_fin, n_cg, wall_s)."""
    import warp_fin_ref as WF
    L, t = design["L"], design["t"]
    f = WF.Fin(nx, ny, L, L * ny / nx, S.K_AL, ee, Tb, Ts, device=device)
    f.t.fill_(t)
    t0 = time.time(); res = f.solve(tol=tol); Q = f.Q(); wp.synchronize()
    Ly = f.h * ny
    return Q / (2 * ee * S.SIG * (Tb**4 - Ts**4) * L * Ly), f.ncg, time.time() - t0, res
def eta_cell(eta_fin, design):
    L, d = design["L"], S.TUBE_OD_M
    return (L * eta_fin + d / 2.0) / (L + d / 2.0)
def fin_1d_reference(design, Tb, ee, Ts):
    """independent check: 1-D fin ODE  k t T'' = 2 ee sigma (T^4 - Ts^4), T(0)=Tb, T'(L)=0 solved with scipy solve_bvp.  -> eta_fin"""
    from scipy.integrate import solve_bvp
    L, t, k = design["L"], design["t"], S.K_AL
    c = 2 * ee * S.SIG / (k * t)
    def f(x, y): return np.vstack([y[1], c * (y[0]**4 - Ts**4)])
    def bc(a, b): return np.array([a[0] - Tb, b[1]])
    x = np.linspace(0, L, 200); y0 = np.vstack([np.full_like(x, Tb), np.zeros_like(x)])
    sol = solve_bvp(f, bc, x, y0, tol=1e-10, max_nodes=100000)
    xs = np.linspace(0, L, 20001); T = sol.sol(xs)[0]
    Q = np.trapezoid(2 * ee * S.SIG * (T**4 - Ts**4), xs)
    return Q / (2 * ee * S.SIG * (Tb**4 - Ts**4) * L)
# ---------------------------------------------------------------- Monte Carlo kernel
@wp.func
def interp1(x: f64, xs: wp.array(dtype=f64), ys: wp.array(dtype=f64), n: int) -> f64:
    if x <= xs[0]: return ys[0]
    if x >= xs[n - 1]: return ys[n - 1]
    i = int(0)
    for j in range(n - 1):
        if x >= xs[j]: i = j
    t = (x - xs[i]) / (xs[i + 1] - xs[i])
    return ys[i] * (f64(1.0) - t) + ys[i + 1] * t
@wp.func
def clipd(x: f64, lo: f64, hi: f64) -> f64:
    return wp.min(hi, wp.max(lo, x))
@wp.func
def gidx(x: f64, x0: f64, dx: f64, n: int):
    u = (x - x0) / dx
    i = int(wp.floor(u))
    i = wp.max(0, wp.min(n - 2, i))
    w = clipd(u - f64(i), f64(0.0), f64(1.0))
    return i, w
@wp.func
def tab3(tab: wp.array(dtype=f64), p: wp.array(dtype=f64), Tb: f64, ee: f64, Ts: f64) -> f64:
    ntb = int(p[20]); nee = int(p[23]); nts = int(p[26])
    i, a = gidx(Tb, p[18], p[19], ntb); j, b = gidx(ee, p[21], p[22], nee); k, c = gidx(Ts, p[24], p[25], nts)
    v = f64(0.0)
    for di in range(2):
        for dj in range(2):
            for dk in range(2):
                w = (a if di == 1 else f64(1.0) - a) * (b if dj == 1 else f64(1.0) - b) * (c if dk == 1 else f64(1.0) - c)
                v += w * tab[((i + di) * nee + (j + dj)) * nts + (k + dk)]
    return v
@wp.kernel
def mc_treq(seed: int, N: int, p: wp.array(dtype=f64), tab: wp.array(dtype=f64), bx: wp.array(dtype=f64), Fe: wp.array(dtype=f64), Ag: wp.array(dtype=f64), nb: int,
            gx: wp.array(dtype=f64), gv: wp.array(dtype=f64), ng: int, out: wp.array2d(dtype=f64)):
    tid = wp.tid()
    st = wp.rand_init(seed, tid)
    pi = 3.141592653589793
    det = p[17] > f64(0.5)
    u_year = f64(wp.randf(st))
    if det: u_year = f64(0.25)
    dec = f64(23.44 * pi / 180.0) * wp.sin(f64(2.0 * pi) * u_year)
    inc = 97.57 * pi / 180.0
    sb = wp.sin(dec) * f64(wp.cos(inc)) + wp.cos(dec) * f64(wp.sin(inc))
    beta = wp.abs(wp.asin(sb)) * f64(180.0 / pi)
    doy = f64(79.0) + u_year * f64(365.25) + p[7] * f64(182.625)
    Sun = f64(1367.0) * (f64(1.0) + f64(0.0334) * wp.cos(f64(2.0 * pi) * (doy - f64(3.0)) / f64(365.25)))
    g = wp.vector(f64(0.0), f64(0.0), f64(0.0), f64(0.0), f64(0.0), f64(0.0), f64(0.0), f64(0.0), length=8)
    for i in range(8):
        u1 = f64(wp.max(wp.randf(st), 1.0e-9)); u2 = f64(wp.randf(st))
        g[i] = wp.sqrt(f64(-2.0) * wp.log(u1)) * wp.cos(f64(2.0 * pi) * u2)
        if det: g[i] = f64(0.0)
    IR = clipd(f64(239.0) + f64(6.2) * g[0], f64(190.0), f64(290.0))
    alb = clipd(f64(0.30) + f64(0.04) * g[1], f64(0.12), f64(0.50))
    age = f64(wp.randf(st)); a_eol = f64(0.30)
    if wp.randf(st) < 0.15: a_eol = f64(0.36)
    alpha = f64(0.20) + (a_eol - f64(0.20)) * age
    deps = f64(0.02) * f64(wp.randf(st))
    if wp.randf(st) >= 0.85: deps = f64(0.02) + f64(0.02) * f64(wp.randf(st))
    if det:
        age = f64(0.0); alpha = f64(0.20); deps = f64(0.0)
    eps = p[2] - deps * age
    eF = f64(0.003) * g[2]
    blk = wp.min(f64(0.15), p[9] * wp.exp(f64(0.30) * g[3] - f64(0.045)))
    pt = wp.abs(p[4] * g[4]) * f64(pi / 180.0)
    flow = clipd(f64(1.0) + f64(0.05) * g[5], f64(0.7), f64(1.3))
    Fb = interp1(beta, bx, Fe, nb); Ab = interp1(beta, bx, Ag, nb)
    q = eps * IR * Fb + alpha * alb * Sun * Ab + f64(0.5) * alpha * Sun * wp.sin(pt) + p[5] * alpha * Sun * interp1(beta, gx, gv, ng)
    Feff = p[3] * (f64(1.0) + eF) * (f64(1.0) - blk)
    ee = eps * Feff
    Ts = wp.pow(q / (ee * f64(5.670374419e-8)), f64(0.25))
    dTl = p[6] / flow
    lo = f64(250.0); hi = f64(420.0)
    for it in range(48):
        T = f64(0.5) * (lo + hi)
        # 3-point Simpson over the coolant temperature drop through the radiator (supply T .. return T+dTl)
        gsum = f64(0.0)
        for m in range(3):
            Tm = T + dTl * f64(0.5) * f64(m)
            wgt = f64(4.0) if m == 1 else f64(1.0)
            ec = tab3(tab, p, Tm, ee, Ts)
            gsum += wgt * f64(2.0) * ee * f64(5.670374419e-8) * (Tm * Tm * Tm * Tm - Ts * Ts * Ts * Ts) * ec
        qpl = gsum / f64(6.0)
        H = p[0]
        if p[8] > f64(0.5): H = p[0] * (f64(1.0) + f64(0.002) * (T + f64(0.5) * dTl - f64(318.15)))
        if p[1] * qpl - H > f64(0.0): hi = T
        else: lo = T
    out[tid, 0] = f64(0.5) * (lo + hi)
    out[tid, 1] = q
    out[tid, 2] = ee
_ENV = None
def env_arrays(device):
    global _ENV
    key = str(device)
    e = json.load(open(os.path.join(HERE, "data", "env_table.json"))); gt = json.load(open(os.path.join(HERE, "data", "g_table.json")))
    A = lambda v: wp.array(np.array(v, float), dtype=f64, device=device)
    return dict(bx=A(e["beta"]), Fe=A(e["F_earth"]), Ag=A(e["albedo_geom"]), nb=len(e["beta"]), gx=A(gt["beta"]), gv=A(gt["g"]), ng=len(gt["beta"]))
def run_mc(table, case, N, seed, device, det=False):
    """table: dict(tb0,dtb,ntb, ee0,dee,nee, ts0,dts,nts, eta=flat list). case: dict(P0,A,eps0,F0,sigma_pt,fg,dT0,pairing,leak,blk).  -> (T_req[K] array, q_abs, ee)"""
    p = np.zeros(32)
    p[0] = case["P0"]; p[1] = case["A"]; p[2] = case["eps0"]; p[3] = case["F0"]; p[4] = case["sigma_pt"]; p[5] = case["fg"]; p[6] = case["dT0"]; p[7] = case["pairing"]
    p[8] = 1.0 if case.get("leak") else 0.0; p[9] = case.get("blk", 0.0092); p[17] = 1.0 if det else 0.0
    p[18], p[19], p[20] = table["tb0"], table["dtb"], table["ntb"]; p[21], p[22], p[23] = table["ee0"], table["dee"], table["nee"]; p[24], p[25], p[26] = table["ts0"], table["dts"], table["nts"]
    dev = device
    cache = getattr(run_mc, "_cache", {})
    ck = (str(dev), table["id"])
    if ck not in cache:
        cache[ck] = (wp.array(np.array(table["eta"], float), dtype=f64, device=dev), env_arrays(dev)); run_mc._cache = cache
    tab, env = cache[ck]
    pw = wp.array(p, dtype=f64, device=dev); out = wp.zeros((N, 3), dtype=f64, device=dev)
    wp.launch(mc_treq, dim=N, inputs=[int(seed), N, pw, tab, env["bx"], env["Fe"], env["Ag"], env["nb"], env["gx"], env["gv"], env["ng"], out], device=dev); wp.synchronize()
    o = out.numpy(); return o[:, 0], o[:, 1], o[:, 2]
def host_treq_det(table, case):
    """host (numpy+scipy) re-implementation of the deterministic draw for validation of the kernel."""
    from scipy.optimize import brentq
    e = json.load(open(os.path.join(HERE, "data", "env_table.json"))); gt = json.load(open(os.path.join(HERE, "data", "g_table.json")))
    u = 0.25; dec = math.radians(23.44) * math.sin(2 * math.pi * u); inc = math.radians(97.57)
    beta = abs(math.degrees(math.asin(math.sin(dec) * math.cos(inc) + math.cos(dec) * math.sin(inc))))
    doy = 79.0 + u * 365.25 + case["pairing"] * 182.625; Sun = 1367.0 * (1 + 0.0334 * math.cos(2 * math.pi * (doy - 3.0) / 365.25))
    Fb = np.interp(beta, e["beta"], e["F_earth"]); Ab = np.interp(beta, e["beta"], e["albedo_geom"])
    alpha = 0.2; eps = case["eps0"]; q = eps * 239.0 * Fb + alpha * 0.30 * Sun * Ab + 0.0 + case["fg"] * alpha * Sun * np.interp(beta, gt["beta"], gt["g"])
    ee = eps * case["F0"] * (1 - min(0.15, case["blk"] * math.exp(-0.045)))
    Ts = (q / (ee * S.SIG)) ** 0.25
    eta_tab = np.array(table["eta"]).reshape(table["ntb"], table["nee"], table["nts"])
    def tab(Tb, e_, Ts_):
        from scipy.interpolate import RegularGridInterpolator
        tb = table["tb0"] + table["dtb"] * np.arange(table["ntb"]); ea = table["ee0"] + table["dee"] * np.arange(table["nee"]); ta = table["ts0"] + table["dts"] * np.arange(table["nts"])
        return float(RegularGridInterpolator((tb, ea, ta), eta_tab, bounds_error=False, fill_value=None)([[min(max(Tb, tb[0]), tb[-1]), min(max(e_, ea[0]), ea[-1]), min(max(Ts_, ta[0]), ta[-1])]])[0])
    dT = case["dT0"]
    def bal(T):
        gs = 0.0
        for m, w in ((0, 1.0), (1, 4.0), (2, 1.0)):
            Tm = T + dT * 0.5 * m; gs += w * 2 * ee * S.SIG * (Tm**4 - Ts**4) * tab(Tm, ee, Ts)
        H = case["P0"] * (1 + 0.002 * (T + 0.5 * dT - 318.15)) if case.get("leak") else case["P0"]
        return case["A"] * gs / 6.0 - H
    return brentq(bal, 250.0, 420.0, xtol=1e-9), q, ee
