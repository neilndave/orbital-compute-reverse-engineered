"""NVIDIA metrics for the GTC FINAL v2 baseline (AI1_GTC_FINAL_V2_AL, all-aluminium radiator).
Identical fp64 problems on GB10 GPU (Warp cuda:0) vs CPU: the same Warp kernels on the Warp CPU backend, plus a conventional NumPy/SciPy CPU code.
 B1 fin solve: v2 fin (Al 6061-T6, k 167 W/mK, half-length 26 mm, t 0.225 mm), June nominal mid-loop root (Tb = 371.65 K, ee 0.89199, sink 185.63 K),
    Newton + Jacobi-PCG (repo warp_fin_ref.Fin, tol 1e-9) at 4 grid sizes (320x8 = production table grid).  CPU references: same Warp code on 'cpu';
    SciPy sparse Newton + direct solve (spsolve) on the same 5-point discretisation.
 B2 thermal-root Monte Carlo: the GB10 parity kernel (fin-table trilinear eta, 70-step bisection for coolant supply, GPU/HBM, mass roll-up) evaluated on
    N perturbed copies of the June/August final nominal rows (emissivity +-3 %, sink +-5 K, IT +-2 %; seeded).  CPU references: same Warp kernel on 'cpu';
    vectorised NumPy port of the same kernel.
Timing: wall clock, 1 warm-up (JIT/compile excluded, reported separately), median of R timed repeats, wp.synchronize() inside the boundary; host->device
copies excluded for B2 kernels (reported separately), included in B1 (solver drives from Python).  GPU power: nvidia-smi power.draw sampled every 100 ms.
usage: python bench_v2.py <out.json> [--quick] [--cpu-only]"""
import json, sys, os, time, math, platform, subprocess, threading, statistics, hashlib
import numpy as np
import warp as wp
wp.config.quiet = True; wp.init()
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import warp_fin_ref as WF
OUT = sys.argv[1]; QUICK = "--quick" in sys.argv; CPU_ONLY = "--cpu-only" in sys.argv
HAS_GPU = wp.get_cuda_device_count() > 0 and not CPU_ONLY
SIG = 5.670374e-8
FIN = dict(k=167.0, L=0.026, t=0.000225, Tb=0.5 * (360.343 + 382.631) + 0.4, ee=0.8919908588528411, Ts=185.63214687303105)
class Power:
    def __init__(s): s.v = []; s.p = None
    def __enter__(s):
        if HAS_GPU:
            try:
                s.p = subprocess.Popen(["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits", "-lms", "100"], stdout=subprocess.PIPE, text=True)
                s.th = threading.Thread(target=s._rd, daemon=True); s.th.start(); time.sleep(0.3)
            except Exception: s.p = None
        return s
    def _rd(s):
        for line in s.p.stdout:
            try: s.v.append(float(line.strip()))
            except ValueError: pass
    def __exit__(s, *a):
        if s.p: s.p.terminate(); s.p.wait()
    def mean(s): return float(np.mean(s.v)) if s.v else None
def idle_power():
    if not HAS_GPU: return None
    with Power() as P: time.sleep(3.0)
    return P.mean()
def timed(fn, R):
    fn()   # warm-up (JIT / caches)
    ts = []
    for _ in range(R):
        t0 = time.perf_counter(); r = fn(); ts.append(time.perf_counter() - t0)
    return ts, r
# ---------------- B1 fin solve ----------------
def warp_fin(dev, nx, ny):
    def go():
        f = WF.Fin(nx, ny, FIN["L"], FIN["L"] * ny / nx, FIN["k"], FIN["ee"], FIN["Tb"], FIN["Ts"], device=dev); f.t.fill_(FIN["t"]); f.solve(tol=1e-9); wp.synchronize_device(dev)
        return dict(Q_W=f.Q(), ncg=f.ncg)
    return go
def scipy_fin(nx, ny):
    import scipy.sparse as sp, scipy.sparse.linalg as spl
    k, t, L, ee, Tb, Ts = FIN["k"], FIN["t"], FIN["L"], FIN["ee"], FIN["Tb"], FIN["Ts"]; h = L / nx; n = nx * ny
    idx = np.arange(n).reshape(ny, nx); rows = []; cols = []; vals = []; diag = np.zeros(n); b = np.zeros(n)
    for (dj, di) in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        J, I = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij"); J2, I2 = J + dj, I + di; m = (J2 >= 0) & (J2 < ny) & (I2 >= 0) & (I2 < nx)
        rows.append(idx[m]); cols.append(idx[J2[m], I2[m]]); vals.append(np.full(m.sum(), k * t)); np.add.at(diag, idx[m], k * t)
    edge = idx[:, 0]; diag[edge] += 2 * k * t; b[edge] += 2 * k * t * Tb
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)); A = sp.diags(diag) - A   # conduction operator (SPD)
    c = 2 * ee * SIG * h * h
    def go():
        T = np.full(n, Tb); it = 0
        while True:   # full Newton, sparse direct (SuperLU) solve; stop when the update max|dT| < 1e-8 K
            R = b - A @ T - c * (T**4 - Ts**4)
            Jm = A + sp.diags(4 * c * T**3); dT = spl.spsolve(Jm.tocsc(), R); T = T + dT; it += 1
            if np.max(np.abs(dT)) < 1e-8 or it > 50: break
        Q = float(np.sum(c * (T**4 - Ts**4))) / 1.0
        return dict(Q_W=Q, newton=it)
    return go
# ---------------- B2 thermal-root MC (parity kernel) ----------------
SRC = open(os.path.join(HERE, "..", "pipeline", "final", "gb10_final_parity.py")).read(); assert SRC[:SRC.index("import os\nR=Path")] == open(os.path.join(HERE, "mc_kernels.py")).read()   # mc_kernels.py = verbatim copy of the parity kernels
from mc_kernels import solve
def mc_rows(N, cfg_dir):
    c = json.load(open(os.path.join(cfg_dir, "GTC_FINAL_CANDIDATE.json"))); th = json.load(open(os.path.join(cfg_dir, "THERMAL_SPIN1.json")))["cases"]
    base = []; mass = []
    for f in c["fleets"]:
        z = th[f["case"]]["T2_rec_nominal_MPG40_plus_recharge"]
        base.append([z["IT_kW"] * 1000, z["pump_electric_W"], f["radiator_effective_area_m2"]["value"], 1.0, z["effective_emissivity"], z["effective_radiation_sink_K"], z["load_fraction"],
                     f["spacecraft_count"]["value"], z.get("extra_heat_W", 0.0), z.get("dR_plate_KW", 0.0)])
        L = list(f["ledger_kg"]["value"].values()); mass.append(L + [0.0] * (20 - len(L)))
    rng = np.random.default_rng(20261107); pick = rng.integers(0, 2, N); X = np.array(base)[pick].copy(); M = np.array(mass)[pick].copy()
    X[:, 4] *= 1 + 0.03 * rng.uniform(-1, 1, N); X[:, 5] += 5.0 * rng.uniform(-1, 1, N); X[:, 0] *= 1 + 0.02 * rng.uniform(-1, 1, N)
    return X, M
def np_kernel(X, M, tab):
    tab = np.asarray(tab)
    def eta(T, E, S):
        z = (np.clip(T, 320.0, 440.0) - 320.0) / 10.0; y = (np.clip(E, .6, 1.0) - .6) / .05; x = (np.clip(S, 150.0, 250.0) - 150.0) / 25.0
        i = np.minimum(np.floor(z).astype(np.int64), 11); j = np.minimum(np.floor(y).astype(np.int64), 7); k = np.minimum(np.floor(x).astype(np.int64), 3)
        f = z - i; g = y - j; h = x - k; v = 0.0
        for di in (0, 1):
            for dj in (0, 1):
                for dk in (0, 1):
                    v = v + (f if di else 1 - f) * (g if dj else 1 - g) * (h if dk else 1 - h) * tab[((i + di) * 9 + (j + dj)) * 5 + k + dk]
        return v
    flux = lambda T, E, S: 2.0 * E * 5.670374419e-8 * (T * T * T * T - S * S * S * S) * eta(T, E, S)
    P = X[:, 0]; pump = X[:, 1]; Q = (P + 2000.0 + pump) / .92 + X[:, 8]; rise = 20.0 * Q / P; lo = np.full(len(P), 250.0); hi = np.full(len(P), 450.0); E = X[:, 4]; S = X[:, 5]
    for _ in range(70):
        mid = (lo + hi) * .5; q = X[:, 2] / X[:, 3] * (flux(mid, E, S) + 4.0 * flux(mid + rise * .5, E, S) + flux(mid + rise, E, S)) / 6.0
        lt = q < Q; lo = np.where(lt, mid, lo); hi = np.where(lt, hi, mid)
    supply = (lo + hi) * .5 + .44; ref = supply + 10.0; load = X[:, 6]; m = M.sum(1)
    return np.stack([Q, rise, supply, ref, ref + 1.7 * load * (14.22 + X[:, 9]), ref + 18.0 * load, supply + rise, m, X[:, 7] * m + 2000.0, Q - (P + 2000.0 + pump) / .92 - X[:, 8]], 1)
def warp_mc(dev, X, M, tab):
    Xa = wp.array(X, dtype=wp.float64, device=dev); Ma = wp.array(M, dtype=wp.float64, device=dev); Ta = wp.array(np.array(tab), dtype=wp.float64, device=dev); O = wp.zeros((len(X), 10), dtype=wp.float64, device=dev)
    def go():
        wp.launch(solve, dim=len(X), inputs=[Xa, Ma, Ta, O], device=dev); wp.synchronize_device(dev); return O
    return go
if __name__ == "__main__":
    root = os.path.normpath(os.path.join(HERE, ".."))
    cfg_dir = os.environ.get("V2_CFG_DIR", root)   # needs GTC_FINAL_CANDIDATE.json + THERMAL_SPIN1.json
    tab = json.load(open(os.path.join(root, "pipeline", "inputs", "ai1_replica", "gb10_final_al", "table_AL6061_L26_t0p225.json")))["eta"]
    cpuinfo = subprocess.run("lscpu | grep -m2 'Model name'; nproc", shell=True, capture_output=True, text=True).stdout.split("\n")
    meta = dict(machine=platform.machine(), python=platform.python_version(), warp=wp.__version__, numpy=np.__version__, cpu=[l.strip() for l in cpuinfo if l.strip()],
                gpu=(wp.get_device("cuda:0").name if HAS_GPU else None), precision="fp64 throughout", quick=QUICK, host_label=os.environ.get("HOST_LABEL", platform.node()[:0] or "unnamed"),
                started=time.strftime("%Y-%m-%d %H:%M:%S %Z"), script_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
                fin_table_sha256=hashlib.sha256(open(os.path.join(root, "pipeline", "inputs", "ai1_replica", "gb10_final_al", "table_AL6061_L26_t0p225.json"), "rb").read()).hexdigest(),
                config_sha256=hashlib.sha256(open(os.path.join(cfg_dir, "GTC_FINAL_CANDIDATE.json"), "rb").read()).hexdigest())
    try: import scipy; meta["scipy"] = scipy.__version__
    except Exception: pass
    meta["gpu_idle_W"] = idle_power(); res = dict(meta=meta, B1_fin=[], B2_mc=[])
    grids = [(320, 8), (640, 16)] if QUICK else [(320, 8), (640, 16), (1280, 32), (2560, 64)]
    grids = [g for g in grids if g[0] * g[1] <= int(os.environ.get("BENCH_MAX_CELLS", "10000000"))]; meta["max_cells"] = max(a * b for a, b in grids)
    for nx, ny in grids:
        row = dict(nx=nx, ny=ny, cells=nx * ny)
        devs = [] if os.environ.get("BENCH_ONLY") == "scipy" else (["cuda:0"] if HAS_GPU else []) + ["cpu"]
        for dev in devs:
            R = 5 if (dev != "cpu" or nx * ny <= 10240) else (3 if nx * ny <= 40960 else 1)
            t0 = time.perf_counter(); g = warp_fin(dev, nx, ny); first = None
            with Power() as P:
                ts, r = timed(g, R)
            row["warp_" + dev.replace(":0", "")] = dict(repeats=R, median_s=statistics.median(ts), min_s=min(ts), max_s=max(ts), Q_W=r["Q_W"], pcg_iters=r["ncg"],
                                                       gpu_mean_W=P.mean() if dev != "cpu" else None, n_power_samples=len(P.v))
            print("B1", nx, ny, dev, round(statistics.median(ts), 4), "s", r, flush=True)
        R = 5 if nx * ny <= 40960 else 3
        ts, r = timed(scipy_fin(nx, ny), R); row["scipy_direct_cpu"] = dict(repeats=R, median_s=statistics.median(ts), min_s=min(ts), max_s=max(ts), Q_W=r["Q_W"], newton=r["newton"])
        print("B1", nx, ny, "scipy", round(statistics.median(ts), 4), r, flush=True)
        res["B1_fin"].append(row); json.dump(res, open(OUT, "w"), indent=1)
    Ns = [10**3, 10**4, 10**5, 10**6] if QUICK else [10**3, 10**4, 10**5, 10**6, 10**7]
    Ns = [n for n in Ns if n <= int(os.environ.get("BENCH_MAX_N", "10000000"))] if os.environ.get("BENCH_ONLY") != "scipy" else []
    for N in Ns:
        X, M = mc_rows(N, cfg_dir); row = dict(N=N)
        t0 = time.perf_counter(); ref = np_kernel(X, M, tab); tnp = time.perf_counter() - t0
        R = 3 if N <= 10**6 else 1
        ts, ref = timed(lambda: np_kernel(X, M, tab), R) if N <= 10**6 else ([tnp], ref)
        row["numpy_cpu"] = dict(repeats=len(ts), median_s=statistics.median(ts), draws_per_s=N / statistics.median(ts))
        for dev in (["cuda:0"] if HAS_GPU else []) + ["cpu"]:
            if dev == "cpu" and N > 10**6: continue
            t0 = time.perf_counter(); g = warp_mc(dev, X, M, tab); h2d = time.perf_counter() - t0
            with Power() as P:
                ts, O = timed(g, 5 if dev != "cpu" else 3)
            v = O.numpy(); d = float(np.max(np.abs(v[:, :9] - ref[:, :9])))
            row["warp_" + dev.replace(":0", "")] = dict(repeats=len(ts), median_s=statistics.median(ts), min_s=min(ts), draws_per_s=N / statistics.median(ts), alloc_copy_s=h2d,
                                                       max_abs_diff_vs_numpy=d, gpu_mean_W=P.mean() if dev != "cpu" else None, n_power_samples=len(P.v))
            print("B2", N, dev, round(statistics.median(ts), 5), "s diff", d, "W", P.mean(), flush=True)
        row["GPU_K_mean_numpy"] = float(ref[:, 4].mean()); row["GPU_K_p99_numpy"] = float(np.percentile(ref[:, 4], 99))
        res["B2_mc"].append(row); json.dump(res, open(OUT, "w"), indent=1)
    res["meta"]["finished"] = time.strftime("%Y-%m-%d %H:%M:%S %Z"); json.dump(res, open(OUT, "w"), indent=1); print("DONE", OUT)
