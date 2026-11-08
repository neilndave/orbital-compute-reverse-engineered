"""Physical validation + cold/warm timing for the v2 fin solver (Al 6061-T6, L 26 mm, t 0.225 mm, June nominal mid-loop root; same point as bench_v2 B1).
 V1 grid convergence: Warp fp64 Q' (W per m of tube, half-fin, both faces) at nx = 80..1280 (GPU when present, else CPU) + SciPy direct to nx 10240;
    observed order p and Richardson extrapolate.
 V2 independent reference: 1-D BVP  k t T'' = 2 ee sigma (T^4 - Ts^4), T(0) = Tb, T'(L) = 0  (scipy solve_bvp, tol 1e-10, different discretisation;
    the 2-D problem is uniform in y, so it reduces exactly to 1-D).
 V3 energy balance: root conduction into the fin, sum_rows 2 k t (Tb - T[:,0]) (the solver's own Dirichlet flux), vs radiated Q; relative residual.
 V4 cold vs warm: fresh empty Warp kernel cache in a new process -> first solve includes kernel compile; then warm solves (median of 5).
usage: python validate_v2.py <out.json>"""
import json, sys, os, time, tempfile, statistics, platform
import warp as wp
COLD_DIR = tempfile.mkdtemp(prefix="warp_cold_"); wp.config.kernel_cache_dir = COLD_DIR; wp.config.quiet = True
t_init0 = time.perf_counter(); wp.init(); t_init = time.perf_counter() - t_init0
import numpy as np
from scipy.integrate import solve_bvp
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import warp_fin_ref as WF
from bench_v2 import FIN, scipy_fin   # same design point / same SciPy reference as the benchmark (bench_v2 main guarded)
SIG = 5.670374e-8; OUT = sys.argv[1]; dev = "cuda:0" if wp.get_cuda_device_count() else "cpu"
k, t, L, ee, Tb, Ts = FIN["k"], FIN["t"], FIN["L"], FIN["ee"], FIN["Tb"], FIN["Ts"]
def warp_run(nx, ny=8, d=dev):
    f = WF.Fin(nx, ny, L, L * ny / nx, k, ee, Tb, Ts, device=d); f.t.fill_(t); r = f.solve(tol=1e-9); wp.synchronize_device(d)
    Q = f.Q(); Ly = f.h * ny; T = f.T.numpy(); qin = float(np.sum(2 * k * t * (Tb - T[:, 0])))
    return dict(nx=nx, ny=ny, Qp_W_per_m=Q / Ly, energy_residual_rel=abs(qin - Q) / Q, newton_residual=float(r), pcg_iters=f.ncg)
res = dict(meta=dict(machine=platform.machine(), device=dev, device_name=(wp.get_device(dev).name if dev != "cpu" else "cpu"), warp=wp.__version__, point=FIN,
                     started=time.strftime("%Y-%m-%d %H:%M:%S %Z")))
# V4 cold / warm (first thing in the process, empty kernel cache)
cw = {}
for d in ([dev] if dev == "cpu" else [dev, "cpu"]):
    t0 = time.perf_counter(); warp_run(320, 8, d); cold = time.perf_counter() - t0
    ws = []
    for _ in range(5):
        t0 = time.perf_counter(); warp_run(320, 8, d); ws.append(time.perf_counter() - t0)
    cw[d] = dict(cold_first_solve_s_incl_kernel_compile=cold, warm_median_s=statistics.median(ws), warm_min_s=min(ws), warm_max_s=max(ws), repeats=5, grid="320x8")
    print("V4", d, cw[d], flush=True)
res["V4_cold_warm"] = dict(warp_init_s=t_init, kernel_cache="fresh empty dir", devices=cw)
# V2 reference
def ode(x, y): return np.vstack([y[1], 2 * ee * SIG * (y[0]**4 - Ts**4) / (k * t)])
x = np.linspace(0, L, 2001); sol = solve_bvp(ode, lambda a, b: np.array([a[0] - Tb, b[1]]), x, np.vstack([np.full_like(x, Tb), np.zeros_like(x)]), tol=1e-10, max_nodes=10**6)
xf = np.linspace(0, L, 200001); Tf = sol.sol(xf)[0]; Qref = float(np.trapezoid(2 * ee * SIG * (Tf**4 - Ts**4), xf)); Qroot = float(-k * t * sol.sol(0.0)[1])
res["V2_reference_1D_BVP"] = dict(Qp_W_per_m=Qref, root_conduction_W_per_m=Qroot, bvp_energy_residual_rel=abs(Qroot - Qref) / Qref, status=sol.status, nodes=int(sol.x.size),
                                  fin_efficiency=Qref / (2 * ee * SIG * (Tb**4 - Ts**4) * L), tip_T_K=float(sol.sol(L)[0]))
print("V2", res["V2_reference_1D_BVP"], flush=True)
# V1 convergence
rows = []
for nx in (80, 160, 320, 640, 1280):
    r = warp_run(nx); r["err_vs_BVP_rel"] = abs(r["Qp_W_per_m"] - Qref) / Qref; rows.append(r); print("V1 warp", r, flush=True)
sc = []
for nx in (320, 640, 1280, 2560, 5120, 10240):
    rr = scipy_fin(nx, 8)(); Ly = (L / nx) * 8; q = rr["Q_W"] / Ly; sc.append(dict(nx=nx, Qp_W_per_m=q, err_vs_BVP_rel=abs(q - Qref) / Qref)); print("V1 scipy", sc[-1], flush=True)
q1, q2, q3 = rows[-3]["Qp_W_per_m"], rows[-2]["Qp_W_per_m"], rows[-1]["Qp_W_per_m"]; p = float(np.log(abs(q1 - q2) / abs(q2 - q3)) / np.log(2.0)); rich = q3 + (q3 - q2) / (2**p - 1)
res["V1_grid_convergence"] = dict(warp=rows, scipy_direct=sc, observed_order=p, richardson_Qp=rich, richardson_err_vs_BVP_rel=abs(rich - Qref) / Qref,
                                  production_grid_err_vs_BVP_rel=[r for r in rows if r["nx"] == 320][0]["err_vs_BVP_rel"])
res["meta"]["finished"] = time.strftime("%Y-%m-%d %H:%M:%S %Z"); json.dump(res, open(OUT, "w"), indent=1); print("DONE", OUT)
