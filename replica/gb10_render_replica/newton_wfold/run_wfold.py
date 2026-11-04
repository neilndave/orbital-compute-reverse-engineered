"""Second-stage (width) fold of ONE replica wing array, n rigid blocks, CABLE-SYNCHRONISED Z-fold (the repo's run_array_sync.py model re-built for n blocks).  ASSUMED analog, ESTIMATE hinge values; not validated.
WHY THIS REPLACES THE OLD run_wfold.py (t441 audit): the old file drove run_array.run('tuned') = independent spring hinges, no cable coupling.  The repo's OWN 21-hinge 'tuned' result (results/newton_array/array_tuned_T45.json) already
latches only 1 of 21 hinges (sync error 2.14, peak drive torque 9.6e5 N m) and 'naive'/'ccl' are NaN/unstable; the repo's deployable model is run_array_sync.py (one deploy coordinate u, cable loop treated as exact; latch at 28.7 s, W0 = 0.10).
So the n-block run showing 1 latched hinge was the repo model's behaviour, not a stale-array bug.  Derived arrays WERE all rebuilt (build()/hinge_params()/analyse() read module globals at call time); BUT run_array_sync.py copies
N, SIGN, STROKE, LEN, MASS, IZ, K0, C0, KL, CL, M_BUS, IZ_BUS at IMPORT time, so this wrapper swaps the run_array globals for n blocks BEFORE importing it (the stale-array trap is handled here).
Hinge spring / damper / latch = repo ESTIMATE values (W0 scanned, fold time ~ 1/W0), zero gravity, planar, free bus.  Cable sync is an exact constraint here (by construction: sync error 0), so the loads of interest are latch torque and cable-constraint torque.
Both repo modules are loaded from source with the hard-coded trace columns [0,1,5,10,15,20] / [0,10,20] clipped to the hinge count (reporting only, physics unchanged); the GB10-side t441 loader approach is kept.
usage: RTS_TAG=_T45 python run_wfold.py N_BLOCKS W0 [t_end] [dt]    (run from an overlay: experiments/newton_array on sys.path / RUN_ARRAY_DIR)    output: results/newton_array/wfold_n<N>_w<W0>.json
keys: t_all_latched_s (= t_all_latched, s: all hinges share one coordinate), n_latched, peak_latch_torque_max_Nm, peak_cable_constraint_torque_max_Nm, max_sync_error_frac (0 by construction), bus_rate_peak_deg_s, bus_yaw_peak_deg, com_drift_m ..."""
import sys, os, json, math, time, types
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
NA = os.path.abspath(os.environ.get("RUN_ARRAY_DIR", os.path.join(HERE, "..", "..", "experiments", "newton_array"))); sys.path.insert(0, NA)
def _load(name, subs):
    p = os.path.join(NA, name + ".py"); src = open(p).read()
    for a, b in subs: src = src.replace(a, b)
    m = types.ModuleType(name); m.__file__ = p; sys.modules[name] = m; exec(compile(src, p, "exec"), m.__dict__); return m
R = _load("run_array", [("phi[:, [0, 1, 5, 10, 15, 20]]", "phi[:, [i for i in (0, 1, 5, 10, 15, 20) if i < phi.shape[1]]]"), ("tau_latch[:, [0, 10, 20]]", "tau_latch[:, [i for i in (0, 10, 20) if i < tau_latch.shape[1]]]")])
n = int(sys.argv[1]); W0 = float(sys.argv[2]); t_end = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0; dt = float(sys.argv[4]) if len(sys.argv) > 4 else 1e-3
WIDTH = R.W_LEAF                                  # array width (m): the length that the n blocks share
LEAF_LEN = R.L_LEAF                               # leaf length (m): block dimension along the hinge axis
R.N_LEAF = n; R.W0 = W0
R.W_LEAF = LEAF_LEN; R.L_LEAF = WIDTH / n
R.M_LEAF = R.ARRAY_KG_TOTAL / R.N_WINGS / n       # whole wing array mass split over n blocks (stowed stack)
R.YOKE_L = 0.5                                    # ASSUMED short root arm (m) between the bus mount and the first block
R.N_HINGE = n + 1
R.STROKE = np.array([math.pi / 2] + [math.pi] * n)
R.SIGN = np.array([1.0 if i % 2 == 0 else -1.0 for i in range(R.N_HINGE)])
R.LEN = np.array([R.YOKE_L] + [R.L_LEAF] * n)
R.MASS = np.array([R.M_YOKE] + [R.M_LEAF] * n)
R.I_OUT = R.outboard_I(); R.I_LEAF_HINGE = R.MASS * R.LEN ** 2 / 3
S = _load("run_array_sync", [("Tl[:, [0, 10, 20]]", "Tl[:, [i for i in (0, 10, 20) if i < Tl.shape[1]]]"), ("Th[:, [0, 10, 20]]", "Th[:, [i for i in (0, 10, 20) if i < Th.shape[1]]]")])
# static audit: every array the sync model copied at import must now have n+1 entries and the swapped values
assert S.N == n + 1 and len(S.SIGN) == len(S.STROKE) == len(S.LEN) == len(S.MASS) == len(S.IZ) == len(S.K0) == len(S.C0) == len(S.KL) == len(S.CL) == n + 1, "stale 21-hinge arrays"
assert abs(S.MASS.sum() - (R.M_YOKE + R.ARRAY_KG_TOTAL / R.N_WINGS)) < 1e-6 and abs(S.LEN[1:].sum() - WIDTH) < 1e-9 and abs(S.M_BUS - (R.M_BUS_TOTAL - R.M_YOKE - R.ARRAY_KG_TOTAL / R.N_WINGS)) < 1e-6
t0 = time.time()
w1 = S.Wing(0.0, 1.0); out = S.simulate([w1], dt, t_end, log=lambda s: print(s, flush=True))
r = S.analyse(out, [w1], f"wfold_n{n}_w{W0:g}"); r["com_drift_m"] = S.com_drift(out, [w1])
tl = r["t_latch_first_contact_s"]
r.update(n_hinge=n + 1, n_blocks=n, W0=W0, block_len_m=R.L_LEAF, block_kg=R.M_LEAF, wing_kg=R.ARRAY_KG_TOTAL / R.N_WINGS, dt=dt, t_end=t_end, wall_s=time.time() - t0,
         n_latched=(n + 1 if tl is not None else 0), t_all_latched_s=tl, t_all_latched=tl, max_sync_error_frac=0.0, peak_latch_torque=r["peak_latch_torque_max_Nm"], bus_rate_peak=r["bus_rate_peak_deg_s"], bus_yaw=r["bus_yaw_peak_deg"],
         label="ASSUMED analog: repo hinge ESTIMATE values, cable-synchronised (sync error 0 by construction), rigid blocks, planar, zero g; not validated; the repo clip's 14 s width fold is an assumed timing, this gives a dynamics-based time to compare")
os.makedirs(R.RES, exist_ok=True)
json.dump(r, open(os.path.join(R.RES, f"wfold_n{n}_w{W0:g}.json"), "w"), indent=1)
print({k: v for k, v in r.items() if not k.startswith("_") and not isinstance(v, list)}, flush=True)
