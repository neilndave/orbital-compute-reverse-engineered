"""[t460] Indexed-PEZ check (Render 1).  Same poses as the render (fleet_kin_T45.Fleet.poses at sim time T, PEZ kinematics ON).  ESTIMATE; geometry of the kinematic model, NOT a contact solve.
Per sample time T:
  1. sat-sat: AABB gap per pair (negative = AABBs overlap) and, when the AABB gap < 3 m, the minimum OBB-vs-OBB separating-axis separation over all instance pairs (panels/plates/bus/pod/yoke, actual render-mesh bounds)  -> same method as the t445 mesh check.
  2. sat vs slot frame / hull: every instance whose AABB straddles the shell (r_min < 4.5 and r_max > 4.0, r = distance from the ship axis X) must lie inside the slot window |X| <= 0.9, |Y| <= 3.65 (7.3 x 1.8 m); margin = min(0.9-|X|max, 3.65-|Y|max) (conservative: AABB of each OBB).
  3. slot lateral margin vs the +-3.65 m jambs, and the arrays-stowed condition (instance AABB extent never exceeds the stowed envelope before the satellite is clear) are reported through (2).
usage: python pez_check.py OUTDIR [step_release=0.5] [step_unfold=0.25]   (run from <overlay>/experiments/poster with FLEET_PEZ=1; NP processes)"""
import sys, os, json, time, pathlib
sys.path.insert(0, os.getcwd())
import numpy as np, multiprocessing as mp
_A = list(sys.argv); sys.argv = [_A[0], _A[1]]      # the imported mesh module reads argv[2] as an int
import fleet_mesh_clearance_T45 as M
import pez_release as PR
K = M.K; n = M.n; pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
HW, HL, R_OUT, R_IN = PR.SLOT_W / 2, PR.SLOT_H / 2, PR.HULL_R, PR.BAY_R
def work(T):
    fn = OUT / f"T{int(round(T * 1000)):08d}.npz"
    if fn.exists(): return T
    fl = M.fl; P = fl.poses(T); ob = [M.sat_obbs(P, i) for i in range(n)]
    bb = [M.aabb(*o) for o in ob]; slo = np.array([b[0].min(0) for b in bb]); shi = np.array([b[1].max(0) for b in bb])
    Ga = np.full(len(pairs), np.nan); Go = np.full(len(pairs), np.nan)
    for pi, (i, j) in enumerate(pairs):
        sg = float(np.maximum(slo[i] - shi[j], slo[j] - shi[i]).max()); Ga[pi] = sg
        if sg > 3.0: continue
        Go[pi] = M.sat_sep(ob[i], ob[j])[0]
    slot_m = np.full(n, np.nan); wall_m = np.full(n, np.nan)       # per sat: window margin of straddling instances; (nan = no instance straddles the shell)
    for i in range(n):
        lo, hi = bb[i]
        dy = np.maximum(np.maximum(lo[:, 1], -hi[:, 1]), 0); dz = np.maximum(np.maximum(lo[:, 2], -hi[:, 2]), 0); rmin = np.hypot(dy, dz)
        rmax = np.hypot(np.maximum(np.abs(lo[:, 1]), np.abs(hi[:, 1])), np.maximum(np.abs(lo[:, 2]), np.abs(hi[:, 2])))
        inx = (hi[:, 0] > -30) & (lo[:, 0] < 30)
        st = (rmin < R_OUT) & (rmax > R_IN) & inx
        if st.any():
            mx = np.maximum(np.abs(lo[st, 0]), np.abs(hi[st, 0])).max(); my = np.maximum(np.abs(lo[st, 1]), np.abs(hi[st, 1])).max()
            slot_m[i] = min(HL - mx, HW - my); wall_m[i] = lo[st, 2].min()       # wall_m: lowest z of a straddling instance (must be > 0: the window is on the +Z side)
    np.savez(fn, T=T, Ga=Ga, Go=Go, slot=slot_m, wallz=wall_m); return T
if __name__ == "__main__":
    s1 = float(_A[2]) if len(_A) > 2 else 0.5; s2 = float(_A[3]) if len(_A) > 3 else 0.25
    ts = np.concatenate([np.arange(0, K.T_U0, s1), np.arange(K.T_U0, K.T_END_SIM + 1e-6, s2)]); t0 = time.time()
    if os.environ.get("PEZ_ADAPT") == "1":      # [t483] fast push: fine steps (PEZ_FINE s, default 0.25) in each satellite's slot passage [Te-1, Tclear+1.5] and in each indexing step, s1 elsewhere
        fine = float(os.environ.get("PEZ_FINE", 0.25)); extra = []
        for f in K.PEZ_INFO.values(): extra.append(np.arange(max(f["Te"] - 1.0, 0.0), f["Tclear"] + 1.5, fine))
        for (a_, b_) in K.PEZ_IDX.values(): extra.append(np.arange(a_ - 1.0, b_ + 1.0, 0.5))
        ts = np.unique(np.round(np.concatenate([ts] + extra), 3)); ts = ts[ts <= K.T_END_SIM + 1e-6]
    with mp.Pool(int(os.environ.get("NPROC", 8))) as p:
        for k, f in enumerate(p.imap_unordered(work, ts, chunksize=4)):
            if k % 100 == 0: print(k, len(ts), f"{time.time() - t0:.0f}s", flush=True)
    print("DONE", flush=True)
