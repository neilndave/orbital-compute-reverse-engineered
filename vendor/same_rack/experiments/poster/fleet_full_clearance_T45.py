"""[t316u] FULL own-satellite + wing + radiator clearance over every rendered clip frame (816 frames x 14 satellites).  Mesh level, OBB/SAT LOWER BOUND on separation (same method as fleet_mesh_clearance_T45.py; ESTIMATE, not a contact solve).
Per satellite and frame every part is an OBB (229 radiator panels, 160 array plates, bus, 2 yokes).  All part pairs whose AABB gap < 0.6 m are SAT-tested, except the pairs that are hinged to each other BY DESIGN (exempt, listed):
  - two panels of the same radiator column whose panel index differs by <= 1 (hinge neighbours); - two array plates of the same wing whose leaf differs by <= 1 (leaf = plate index // 4); - yoke w vs the first 4 plates (leaf 0) of its own wing.
Categories of the reported minimum gap (m): colcol_adj (columns k,k+1 of the same wing = hinge pitch neighbours), colcol_other, col_bus, col_wing (radiator vs array plates), col_yoke, wing_bus, wing_wing (wing0 vs wing1), wing_yoke (other leaves / other wing), yoke_bus, yoke_yoke, intra_col (non-adjacent panels), intra_wing (non-adjacent leaves).
usage: python fleet_full_clearance_T45.py out.npz [frame_stride] [first last]      env = the render's (FLEET_SYNC=1 FLEET_YOKE=1 ..., FLEET_STUBTRIM, FLEET_STAGEPLAN)"""
import sys, json, time, pathlib, os
import numpy as np
from multiprocessing import Pool
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
OUTP = sys.argv[1]; STRIDE = int(sys.argv[2]) if len(sys.argv) > 2 else 1
_a = sys.argv; sys.argv = [_a[0], "/tmp"]
import fleet_kin_T45 as K
import fleet_mesh_clearance_T45 as M
sys.argv = _a
CATS = ["colcol_adj", "colcol_other", "col_bus", "col_wing", "col_yoke", "wing_bus", "wing_wing", "wing_yoke", "yoke_bus", "yoke_yoke", "intra_col", "intra_wing", "pod_own"]
fl = None; LAB = None
def labels(sa):
    """per OBB of the satellite (order: panels in n_cols order, plates (2x80), bus, yokes): group code, sub-index"""
    kind = []; grp = []; sub = []; wing = []; col = []
    for gi, wc in enumerate(sa.n_cols):
        for p in range(K.NPAN[wc]): kind.append(0); grp.append(gi); sub.append(p); wing.append(wc[0]); col.append(wc[1])
    for w in (0, 1):
        for q in range(80): kind.append(1); grp.append(w); sub.append(q); wing.append(w); col.append(-1)
    kind.append(2); grp.append(0); sub.append(0); wing.append(-1); col.append(-1)
    for w in (0, 1): kind.append(3); grp.append(w); sub.append(0); wing.append(w); col.append(-1)
    if getattr(sa, 'pod_pack', None) is not None: kind.append(4); grp.append(0); sub.append(0); wing.append(-1); col.append(-1)   # [t337] pod, after the yokes
    return [np.array(x) for x in (kind, grp, sub, wing, col)]
def init():
    global fl, LAB
    fl = K.Fleet(); LAB = [labels(fl.sats[i]) for i in range(fl.n)]
def sat_pairs(C, R, H, ia, ib):
    Ra_, Rb_ = R[ia], R[ib]; ha, hb = H[ia], H[ib]; d = C[ib] - C[ia]
    axes = [Ra_[:, :, i] for i in range(3)] + [Rb_[:, :, j] for j in range(3)]
    for i in range(3):
        for j in range(3):
            c = np.cross(Ra_[:, :, i], Rb_[:, :, j]); nn = np.linalg.norm(c, axis=1, keepdims=True); axes.append(np.where(nn > 1e-6, c / np.maximum(nn, 1e-12), 0.0))
    best = np.full(len(ia), -1e9)
    for L in axes:
        ok = np.linalg.norm(L, axis=1) > 0.5
        ra = (np.abs(np.einsum("kij,kj->ki", np.transpose(Ra_, (0, 2, 1)), L)) * ha).sum(1); rb = (np.abs(np.einsum("kij,kj->ki", np.transpose(Rb_, (0, 2, 1)), L)) * hb).sum(1)
        s = np.abs((d * L).sum(1)) - ra - rb; best = np.where(ok, np.maximum(best, s), best)
    return best
def own_frame(P, i):
    C, R, H = M.sat_obbs(P, i); kind, grp, sub, wing, col = LAB[i]
    if len(C) != len(kind):       # hidden yokes were dropped by sat_obbs
        keep = np.ones(len(kind), bool); yp = P["yoke_p"][2 * i:2 * i + 2]
        for w in (0, 1):
            if np.abs(yp[w]).max() >= 1.0e4: keep[np.nonzero((kind == 3) & (grp == w))[0]] = False
        kind, grp, sub, wing, col = [x[keep] for x in (kind, grp, sub, wing, col)]
    lo, hi = M.aabb(C, R, H); out = np.full(len(CATS), 9.0); n = len(C)
    gm = np.maximum(lo[:, None, :] - hi[None, :, :], lo[None, :, :] - hi[:, None, :]).max(-1)
    ia, ib = np.nonzero(np.triu(gm < 0.6, 1))
    ka, kb = kind[ia], kind[ib]; ga, gb = grp[ia], grp[ib]; sa_, sb_ = sub[ia], sub[ib]; wa, wb = wing[ia], wing[ib]
    same = (ka == kb) & (ga == gb)
    ex = same & (((ka == 0) & (np.abs(sa_ - sb_) <= 1)) | ((ka == 1) & (np.abs(sa_ // 4 - sb_ // 4) <= 1)))
    ex |= ((ka == 3) & (kb == 1) & (ga == gb) & (sb_ < 4)) | ((kb == 3) & (ka == 1) & (ga == gb) & (sa_ < 4))
    # colcol hinge pitch neighbours: same wing, column index differs by 1
    ia, ib = ia[~ex], ib[~ex]
    if len(ia) == 0: return out
    s = sat_pairs(C, R, H, ia, ib); ka, kb = kind[ia], kind[ib]; ga, gb = grp[ia], grp[ib]; wa, wb = wing[ia], wing[ib]; ca, cb = col[ia], col[ib]
    def put(cat, m):
        if m.any(): out[CATS.index(cat)] = min(out[CATS.index(cat)], float(s[m].min()))
    cc = (ka == 0) & (kb == 0); samecol = cc & (ga == gb)
    put("intra_col", samecol); put("colcol_adj", cc & ~samecol & (wa == wb) & (np.abs(ca - cb) == 1)); put("colcol_other", cc & ~samecol & ~((wa == wb) & (np.abs(ca - cb) == 1)))
    def has(k1, k2): return ((ka == k1) & (kb == k2)) | ((ka == k2) & (kb == k1))
    put("col_bus", has(0, 2)); put("col_wing", has(0, 1)); put("col_yoke", has(0, 3))
    ww = (ka == 1) & (kb == 1); put("intra_wing", ww & (ga == gb)); put("wing_wing", ww & (ga != gb)); put("wing_bus", has(1, 2)); put("wing_yoke", has(1, 3)); put("yoke_bus", has(3, 2)); put("yoke_yoke", (ka == 3) & (kb == 3)); put("pod_own", (ka == 4) | (kb == 4))
    return out
def work(f):
    T = K.sim_time(f / K.FPS); P = fl.poses(T)
    return f, T, np.array([own_frame(P, i) for i in range(fl.n)])
if __name__ == "__main__":
    nf = int(round(K.CLIP_S * K.FPS)); fr = list(range(0, nf, STRIDE))
    if len(_a) > 4: fr = [f for f in fr if int(_a[3]) <= f <= int(_a[4])]
    t0 = time.time(); res = {}
    with Pool(int(os.environ.get("NPROC", "6")), initializer=init) as pool:
        for k, (f, T, a) in enumerate(pool.imap_unordered(work, fr, chunksize=2)):
            res[f] = (T, a)
            if k % 50 == 0: print(f"{k}/{len(fr)} {time.time() - t0:.0f}s", flush=True)
    fs = np.array(sorted(res)); G = np.stack([res[f][1] for f in fs]); Tl = np.array([res[f][0] for f in fs])
    np.savez_compressed(OUTP, frames=fs, T=Tl, gap=G, cats=np.array(CATS))
    print("global min per category (m):")
    for c, name in enumerate(CATS):
        k = np.unravel_index(np.argmin(G[:, :, c]), G[:, :, c].shape); print(f"  {name:13s} min {G[:, :, c].min():+.4f}  frame {fs[k[0]]}  sat {k[1]}  n<=0 sat-frames {(G[:, :, c] <= 0).sum()}")
    print(f"total {time.time() - t0:.0f}s")
