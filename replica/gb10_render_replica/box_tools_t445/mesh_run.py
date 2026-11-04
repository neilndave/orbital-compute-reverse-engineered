import sys, os, json, time, pathlib
sys.path.insert(0, os.getcwd())
import numpy as np, multiprocessing as mp
import fleet_mesh_clearance_T45 as M
K = M.K; n = M.n; pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
def work(f):
    fn = OUT / f"f{f:04d}.npz"
    if fn.exists(): return f
    fl = M.fl; T = K.sim_time(f / K.FPS); P = fl.poses(T); ob = [M.sat_obbs(P, i) for i in range(n)]
    bb = [M.aabb(*o) for o in ob]; slo = np.array([b[0].min(0) for b in bb]); shi = np.array([b[1].max(0) for b in bb])
    G = np.full(len(pairs), np.nan)
    for pi, (i, j) in enumerate(pairs):
        sg = float(np.maximum(slo[i] - shi[j], slo[j] - shi[i]).max())
        if sg > 3.0: G[pi] = sg; continue
        G[pi] = M.sat_sep(ob[i], ob[j])[0]
    r, d = (M.bay_check(P) if slo[:, 2].min() < 25 else (np.nan, np.nan))
    np.savez(fn, T=T, G=G, rail=r, deck=d); return f
if __name__ == "__main__":
    frames = list(range(0, 217)) + list(range(217, 816, 4)) + [815]
    t0 = time.time()
    with mp.Pool(int(os.environ.get("NP", 4))) as p:
        for k, f in enumerate(p.imap_unordered(work, frames)):
            if k % 20 == 0: print(k, len(frames), f, f"{time.time()-t0:.0f}s", flush=True)
    print("DONE", flush=True)
