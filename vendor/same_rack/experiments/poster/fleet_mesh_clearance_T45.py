"""Fleet clip MESH-LEVEL clearance check (Nov 1 2026, []). ESTIMATE; same poses as the render (fleet_kin_T45.Fleet.poses at the sim time of every rendered frame), but using
the ACTUAL render mesh bounds (panel = union of sheet+tubes+headers+stubs vertices from results/fleet/fleet_assets_T45.npz; plate and bus = the box meshes the render draws).
Per frame: every instance (229 panels + 80 array plates + 1 bus per satellite) becomes an oriented bounding box (OBB) of its own mesh; every OBB of satellite i is tested against every OBB of satellite j
(separating-axis test, 15 axes; exact for boxes, a LOWER BOUND on the true distance, and the boxes enclose the mesh, so a positive value means the real meshes cannot touch).
Also: satellites vs the 4 rails (cylinders r 0.08 m, as drawn), vs the deck/hull (z<=0, r 4.5 m, as drawn).  Not a contact solve.
Run in venv_cad from experiments/poster: python fleet_mesh_clearance_T45.py [outdir] -> mesh_clearance_T45.json (+ .npz of per-frame min gaps)."""
import sys, json, pathlib, time
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fleet_kin_T45 as K
ROOT = K.ROOT; OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/fleet"
SUB = int(sys.argv[2]) if len(sys.argv) > 2 else 1            # sub-samples per rendered frame (1 = exactly the rendered times)
A = np.load(ROOT / "results/fleet/fleet_assets_T45.npz")
V = np.concatenate([(K.trim_stub_V(A[f"panel_{k}_V"].astype(np.float64)) if k == "stubs" else A[f"panel_{k}_V"].astype(np.float64)) for k in ("sheet", "tubes", "headers", "stubs")]) * 1e-3     # [t316u] FLEET_STUBTRIM
V[:, 1] *= K.LSCALE      # [t337] lengthened panels (A6L)
P_LO, P_HI = V.min(0), V.max(0)                              # actual panel mesh bounds, local frame (m)
P_CEN = 0.5 * (P_LO + P_HI); P_HALF = 0.5 * (P_HI - P_LO)
fl = K.Fleet(); n = fl.n; NP = K.NPAN_TOT; NQ = 2 * K.NLEAF * K.NSEC; NI = NP + NQ + 1
def sat_obbs(P, i):
    """centres (NI,3), axes (NI,3,3) (columns = box axes), half (NI,3) of satellite i"""
    pp = P["panel_p"][i * NP:(i + 1) * NP]; pR = P["panel_R"][i * NP:(i + 1) * NP]
    qp = P["plate_p"][i * NQ:(i + 1) * NQ]; qR = P["plate_R"][i * NQ:(i + 1) * NQ]
    C = np.concatenate([pp + np.einsum("kij,j->ki", pR, P_CEN), qp, P["bus_p"][i:i + 1]])
    R = np.concatenate([pR, qR, P["bus_R"][i:i + 1]])
    H = np.concatenate([np.tile(P_HALF, (NP, 1)), np.tile(K.PLATE_BOX / 2, (NQ, 1)), K.BUS[None] / 2])
    if "yoke_p" in P:     # [t310u] yoke boom (2 per satellite, FLEET_YOKE=1)
        yp = P["yoke_p"][2 * i:2 * i + 2]; ok = np.abs(yp).max(1) < 1.0e4      # hidden yokes (moved far away while staging) are not part of the model then
        C = np.concatenate([C, yp[ok]]); R = np.concatenate([R, P["yoke_R"][2 * i:2 * i + 2][ok]]); H = np.concatenate([H, np.tile(K.YOKE_BOX / 2, (int(ok.sum()), 1))])
    if "pod_p" in P:     # [t337] component pod (1 per satellite, rigid block), appended after the yokes
        C = np.concatenate([C, P["pod_p"][i:i + 1]]); R = np.concatenate([R, P["pod_R"][i:i + 1]]); H = np.concatenate([H, (fl.sats[i].pod_box / 2)[None]])
    return C, R, H
def aabb(C, R, H):
    e = np.einsum("kij,kj->ki", np.abs(R), H); return C - e, C + e
def sat_sep(a, b, tol=1.0):
    """min SAT separation between any OBB of a and any OBB of b (only instance pairs whose AABB gap < tol are tested). returns (sep, ia, ib)"""
    (Ca, Ra, Ha), (Cb, Rb, Hb) = a, b
    lo_a, hi_a = aabb(Ca, Ra, Ha); lo_b, hi_b = aabb(Cb, Rb, Hb)
    g = np.maximum(lo_a[:, None, :] - hi_b[None, :, :], lo_b[None, :, :] - hi_a[:, None, :]).max(-1)
    ia, ib = np.nonzero(g < tol)
    if len(ia) == 0: return float(g.min()), -1, -1       # AABB gap is itself a valid lower bound when no pair is near
    Ra_, Rb_ = Ra[ia], Rb[ib]; ha, hb = Ha[ia], Hb[ib]; d = Cb[ib] - Ca[ia]
    axes = [Ra_[:, :, i] for i in range(3)] + [Rb_[:, :, j] for j in range(3)]
    for i in range(3):
        for j in range(3):
            c = np.cross(Ra_[:, :, i], Rb_[:, :, j]); nn = np.linalg.norm(c, axis=1, keepdims=True); axes.append(np.where(nn > 1e-6, c / np.maximum(nn, 1e-12), 0.0))
    best = np.full(len(ia), -1e9)
    for L in axes:
        ok = np.linalg.norm(L, axis=1) > 0.5
        ra = (np.abs(np.einsum("kij,kj->ki", np.transpose(Ra_, (0, 2, 1)), L)) * ha).sum(1); rb = (np.abs(np.einsum("kij,kj->ki", np.transpose(Rb_, (0, 2, 1)), L)) * hb).sum(1)
        s = np.abs((d * L).sum(1)) - ra - rb; best = np.where(ok, np.maximum(best, s), best)
    k = int(np.argmin(best)); return float(best[k]), int(ia[k]), int(ib[k])
RAILS = [(sx * 3.3, sy * 3.3) for sx in (-1, 1) for sy in (-1, 1)]; RAIL_R = 0.08; RAIL_Z = (-0.3, 18.2); HULL_R = 4.5
ZS = np.linspace(RAIL_Z[0], RAIL_Z[1], 370)
CS8 = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float)
def bay_check(P):
    """min distance of any OBB to a rail axis (minus r), min z of any OBB corner whose xy footprint reaches the deck disc (r<4.5)"""
    rail = 1e9; zdeck = 1e9
    for i in range(n):
        C, R, H = sat_obbs(P, i); lo, hi = aabb(C, R, H)
        corners = C[:, None, :] + np.einsum("kij,kmj->kmi", R, CS8[None] * H[:, None, :])          # (NI,8,3)
        rmin = np.hypot(np.clip(np.abs(C[:, 0]) - (hi[:, 0] - lo[:, 0]) / 2, 0, None), np.clip(np.abs(C[:, 1]) - (hi[:, 1] - lo[:, 1]) / 2, 0, None))
        on = rmin < HULL_R
        if on.any(): zdeck = min(zdeck, float(corners[on][:, :, 2].min()))
        for (rx, ry) in RAILS:
            near = np.nonzero((hi[:, 0] > rx - 1) & (lo[:, 0] < rx + 1) & (hi[:, 1] > ry - 1) & (lo[:, 1] < ry + 1) & (lo[:, 2] < RAIL_Z[1]) & (hi[:, 2] > RAIL_Z[0]))[0]
            if len(near) == 0: continue
            pts = np.stack([np.full_like(ZS, rx), np.full_like(ZS, ry), ZS], 1)
            loc = np.einsum("kji,kmj->kmi", R[near], pts[None] - C[near][:, None, :])               # (K,370,3) in OBB frame
            dd = np.linalg.norm(np.maximum(np.abs(loc) - H[near][:, None, :], 0), axis=2).min() - RAIL_R
            rail = min(rail, float(dd))
    return rail, zdeck
if __name__ == "__main__":
    t0 = time.time(); nf = int(round(K.CLIP_S * K.FPS)); fr = np.arange(nf * SUB) / SUB
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    G = np.full((len(fr), len(pairs)), np.nan); Tl = np.zeros(len(fr)); RAIL = np.full(len(fr), np.nan); DECK = np.full(len(fr), np.nan); IDX = {}
    for fi, f in enumerate(fr):
        T = K.sim_time(f / K.FPS); Tl[fi] = T; P = fl.poses(T); ob = [sat_obbs(P, i) for i in range(n)]
        bb = [aabb(*o) for o in ob]; slo = np.array([b[0].min(0) for b in bb]); shi = np.array([b[1].max(0) for b in bb])
        for pi, (i, j) in enumerate(pairs):
            sg = float(np.maximum(slo[i] - shi[j], slo[j] - shi[i]).max())
            if sg > 3.0: G[fi, pi] = sg; continue
            s, ia, ib = sat_sep(ob[i], ob[j]); G[fi, pi] = s
            if s < 0.5: IDX[(fi, pi)] = (ia, ib)
        if slo[:, 2].min() < 25: RAIL[fi], DECK[fi] = bay_check(P)
        if fi % 100 == 0: print(f"{fi}/{len(fr)} {time.time() - t0:.0f}s min so far {np.nanmin(G[:fi + 1]):.4f}", flush=True)
    gm = np.nanmin(G, axis=1); k = np.unravel_index(np.nanargmin(G), G.shape)
    per_pair = {f"{i}-{j}": [float(np.nanmin(G[:, pi])), float(fr[np.nanargmin(G[:, pi])])] for pi, (i, j) in enumerate(pairs)}
    # closest approach AFTER release (excluding frames where the pair is still inside the stowed pack: both satellites have Trel+exit not yet reached)
    rel_end = np.array([[max(fl.sats[i].Tex, fl.sats[j].Tex) for (i, j) in pairs]])
    after = Tl[:, None] > rel_end; Ga = np.where(after, G, np.nan)
    ka = np.unravel_index(np.nanargmin(Ga), Ga.shape)
    pair_exit = {f"{i}-{j}": float(max(fl.sats[i].Tex, fl.sats[j].Tex)) for (i, j) in pairs}
    out = dict(note="ESTIMATE; mesh-level (instance OBB of the actual render mesh bounds), SAT lower bound on separation; frame = rendered frame index (sub-sampled by SUB)", sub=SUB, n_frames=len(fr),
               panel_mesh_bounds_mm=[(P_LO * 1e3).tolist(), (P_HI * 1e3).tolist()], panel_box_used_by_old_check_mm=(K.PANEL_BOX * 1e3).tolist(),
               min_pair_gap_m=float(G[k]), min_pair=list(pairs[k[1]]), min_pair_frame=float(fr[k[0]]), min_pair_T_s=float(Tl[k[0]]), n_frames_with_overlap=int((gm < 0).sum()),
               frames_with_overlap=[float(x) for x in fr[gm < 0][:200]], pairs_with_overlap={f"{pairs[pi][0]}-{pairs[pi][1]}": int((G[:, pi] < 0).sum()) for pi in range(len(pairs)) if (G[:, pi] < 0).any()},
               min_gap_after_pair_exit_m=float(Ga[ka]), min_gap_after_exit_pair=list(pairs[ka[1]]), min_gap_after_exit_frame=float(fr[ka[0]]), min_gap_after_exit_T_s=float(Tl[ka[0]]),
               rail_min_clearance_m=float(np.nanmin(RAIL)), rail_min_frame=float(fr[np.nanargmin(RAIL)]), deck_min_z_m=float(np.nanmin(DECK)), deck_min_z_frame=float(fr[np.nanargmin(DECK)]), pair_exit_T_s=pair_exit, per_pair_min_gap_m_and_frame=per_pair)
    json.dump(out, open(OUT / "mesh_clearance_T45.json", "w"), indent=1)
    np.savez_compressed(OUT / "mesh_clearance_T45_series.npz", frames=fr, T=Tl, gap=G, pairs=np.array(pairs), rail=RAIL, deck=DECK)
    print(json.dumps({kk: v for kk, v in out.items() if kk not in ("per_pair_min_gap_m_and_frame", "frames_with_overlap", "pair_exit_T_s")}, indent=1)); print(f"total {time.time() - t0:.0f} s")
