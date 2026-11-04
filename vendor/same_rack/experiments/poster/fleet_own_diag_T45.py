"""[t316u] Own-satellite clearance by ITEM (bus, 24 radiator columns, 2 array plate stacks, 2 yokes) over the unfold clock tau, mesh level (OBB/SAT lower bound, same as fleet_mesh_clearance_T45.py).
Reports, per item pair, the minimum gap and the tau ranges where it is negative.  Hinged neighbours excluded: plates of the same wing (single group), yoke-wing own plate stack (yoke_w vs plates_w).
Adjacent radiator columns of the same wing are 4 mm apart by design (GAP), so for column-column pairs only gap < -0.001 m counts as overlap.  ESTIMATE.
usage: python fleet_own_diag_T45.py out_prefix sat tau0 tau1 dt"""
import sys, json, pathlib
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
_a = sys.argv; sys.argv = [_a[0], "/tmp"]
import fleet_kin_T45 as K
import fleet_mesh_clearance_T45 as M
sys.argv = _a
def items(fl, sa, tau):
    pp, pR, qp, qR, bp = fl.local(sa, tau); g = {"bus": (bp[None], np.eye(3)[None], (K.BUS / 2)[None])}
    C = pp + np.einsum("kij,j->ki", pR, M.P_CEN); H = np.tile(M.P_HALF, (len(pp), 1)); o = 0
    for gi, wc in enumerate(sa.n_cols):
        n = K.NPAN[wc]; g[f"col{wc[0]}_{wc[1]:02d}"] = (C[o:o + n], pR[o:o + n], H[o:o + n]); o += n
    for w in (0, 1): g[f"plates{w}"] = (qp[w * 80:(w + 1) * 80], qR[w * 80:(w + 1) * 80], np.tile(K.PLATE_BOX / 2, (80, 1)))
    if K.YOKE:
        for w in (0, 1): g[f"yoke{w}"] = (sa._yoke[0][w:w + 1], sa._yoke[1][w:w + 1], (K.YOKE_BOX / 2)[None])
    return g
def gbox(t):
    lo, hi = M.aabb(*t); return lo.min(0), hi.max(0)
def run(sat, t0, t1, dt, prefix, verbose=True):
    fl = K.Fleet(); sa = fl.sats[sat]; taus = np.arange(t0, t1 + 1e-9, dt); names = None; G = None
    for ti, tau in enumerate(taus):
        g = items(fl, sa, tau); yk_hidden = K.YOKE and tau < K.TAU_STAGE + K.TAU_GSTEP * 26
        if names is None:
            names = list(g); pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]
                                      if not (a.startswith("plates") and b.startswith("plates") and False) and not (a.startswith("yoke") and b == "plates" + a[-1])]
            G = np.full((len(taus), len(pairs)), 9.0)
        bb = {k: gbox(v) for k, v in g.items()}
        for pi, (a, b) in enumerate(pairs):
            if yk_hidden and (a.startswith("yoke") or b.startswith("yoke")): continue
            sg = float(np.maximum(bb[a][0] - bb[b][1], bb[b][0] - bb[a][1]).max())
            if sg > 0.6: G[ti, pi] = sg; continue
            s, _, _ = M.sat_sep(g[a], g[b], tol=0.6); G[ti, pi] = s
    np.savez_compressed(prefix + ".npz", tau=taus, gap=G, pairs=np.array([f"{a}|{b}" for a, b in pairs]))
    return taus, G, pairs
def summarize(taus, G, pairs, thr_col=-0.001):
    out = {}
    for pi, (a, b) in enumerate(pairs):
        thr = thr_col if (a.startswith("col") and b.startswith("col")) else 0.0
        bad = taus[G[:, pi] < thr]
        if len(bad): out[f"{a}|{b}"] = dict(min_gap_m=float(G[:, pi].min()), tau_at_min=float(taus[np.argmin(G[:, pi])]), n_steps=int(len(bad)), tau_first=float(bad[0]), tau_last=float(bad[-1]))
    return out
if __name__ == "__main__":
    prefix = sys.argv[1]; sat = int(sys.argv[2]); t0, t1, dt = map(float, sys.argv[3:6])
    taus, G, pairs = run(sat, t0, t1, dt, prefix); S = summarize(taus, G, pairs)
    json.dump(dict(env=dict(SYNC=K.SYNC, YOKE=K.YOKE, TAU_N0=K.TAU_N0, TAU_W0=K.TAU_W0), sat=sat, overlaps=S), open(prefix + ".json", "w"), indent=1)
    print(f"{len(S)} overlapping item pairs"); 
    for k, v in sorted(S.items(), key=lambda kv: kv[1]["min_gap_m"])[:40]: print(k, {kk: round(vv, 3) for kk, vv in v.items()})
