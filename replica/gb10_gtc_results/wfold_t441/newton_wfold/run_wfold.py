"""Second-stage (width) fold of ONE replica wing, Newton Featherstone, planar rigid blocks.   ASSUMED analog of the repo's run_array.py -- UNTESTED on the box (no Newton there); run it on the GB10 desktop.
The repo chain (yoke + 20 leaves, hinge axis = leaf width) has no second-stage fold; the repo clip plays the width fold kinematically (assumed 14 s).  This wrapper re-uses run_array.py UNCHANGED
(import), swaps its module constants for a chain of n rigid BLOCKS (stowed 20-leaf stack, 14 m / n long each, mass = wing array mass / n) and re-derives the arrays the repo functions use.
Hinge spring / damper / latch design = the repo's ESTIMATE values (W0, ZETA, OVER, WL, ZL), W0 scanned because it sets the fold time (time ~ 1/W0).  Zero gravity, rigid blocks, free bus (same as run_array.py 'tuned').
usage: RTS_TAG=_T45 python run_wfold.py N_BLOCKS W0 [t_end] [dt]   (run from an overlay tree: experiments/newton_array/ on sys.path; results go to RES of run_array)
output: results/newton_array/wfold_n<N>_w<W0>.json : latch times, t_all_latched, peak latch torque, sync error, bus rate/yaw, plus blanket-hinge torque per block."""
import sys, os, json, math, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("RUN_ARRAY_DIR", os.path.join(HERE, "..", "..", "experiments", "newton_array")))
import types as _ty   # [t441] load run_array with its trace-sampling indices clipped to the hinge count (analysis output only; physics unchanged)
_src_p = os.path.join(sys.path[0], "run_array.py"); _src = open(_src_p).read().replace("phi[:, [0, 1, 5, 10, 15, 20]]", "phi[:, [i for i in (0, 1, 5, 10, 15, 20) if i < phi.shape[1]]]").replace("tau_latch[:, [0, 10, 20]]", "tau_latch[:, [i for i in (0, 10, 20) if i < tau_latch.shape[1]]]")
R = _ty.ModuleType("run_array"); R.__file__ = _src_p; sys.modules["run_array"] = R; exec(compile(_src, _src_p, "exec"), R.__dict__)
n = int(sys.argv[1]); W0 = float(sys.argv[2]); t_end = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0; dt = float(sys.argv[4]) if len(sys.argv) > 4 else 1e-3
WIDTH = R.W_LEAF                                  # 14 m array width (repo): the length that the n blocks share
LEAF_LEN = R.L_LEAF                               # leaf length (m): the block's dimension along the hinge axis
R.N_LEAF = n; R.W0 = W0
R.W_LEAF = LEAF_LEN                               # block dimension along the hinge axis (Wd in R.build)
R.L_LEAF = WIDTH / n
R.M_LEAF = R.ARRAY_KG_TOTAL / R.N_WINGS / n       # whole wing array mass split over n blocks (stowed stack)
R.YOKE_L = 0.5                                    # ASSUMED short root arm (m) between the bus mount and the first block (repo yoke 1.97 m belongs to stage 1)
R.N_HINGE = n + 1
R.STROKE = np.array([math.pi / 2] + [math.pi] * n)
R.SIGN = np.array([1.0 if i % 2 == 0 else -1.0 for i in range(R.N_HINGE)])
R.LEN = np.array([R.YOKE_L] + [R.L_LEAF] * n)
R.MASS = np.array([R.M_YOKE] + [R.M_LEAF] * n)
R.I_OUT = R.outboard_I(); R.I_LEAF_HINGE = R.MASS * R.LEN ** 2 / 3
t0 = time.time()
r = R.run("tuned", dt, t_end, usd=None)
out = R.analyse(r)
out.update(n_blocks=n, W0=W0, block_len_m=R.L_LEAF, block_kg=R.M_LEAF, wing_kg=R.ARRAY_KG_TOTAL / R.N_WINGS, dt=dt, t_end=t_end, wall_s=time.time() - t0,
           label="ASSUMED analog (repo hinge ESTIMATE values, rigid blocks, planar, zero g); not validated; the repo clip's 14 s width fold is an assumed timing, this gives a dynamics-based time to compare")
for k in [k for k in out if k.startswith("_")]: out.pop(k)
os.makedirs(R.RES, exist_ok=True)
json.dump(out, open(os.path.join(R.RES, f"wfold_n{n}_w{W0:g}.json"), "w"), indent=1)
print({k: v for k, v in out.items() if not isinstance(v, list)}, flush=True)
