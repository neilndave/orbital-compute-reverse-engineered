"""Fleet clip clearance + momentum check (ESTIMATE, geometry of the kinematic model only, NOT a contact solve). Run in venv_cad: python experiments/poster/fleet_clearance_T45.py -> results/fleet/clearance_T45.json
Per time step: AABB of every satellite (all radiator panels, array plates, bus); pairwise AABB gap = max over axes of the separation (negative = AABBs overlap). Where AABBs overlap, bodies are tested AABB-vs-AABB (panel boxes, plate boxes, bus) for real overlap.
Also: dispenser rails (4 x r 0.08 m at (+-3.3, +-3.3)) vs each satellite while it exits, and the ship-recoil (momentum) bookkeeping using the stowing-study launch mass 6,426 kg (ESTIMATE) and ship 200 t (ASSUMED, release_layers_T45)."""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np, fleet_kin_T45 as K
fl = K.Fleet(); n = fl.n
NP, NQ = K.NPAN_TOT, 2 * K.NLEAF * K.NSEC
def per_sat(P):
    lo = np.full((n, 3), 1e9); hi = np.full((n, 3), -1e9); body = []
    for nm, box, cen, m in (("panel", K.PANEL_BOX, False, NP), ("plate", K.PLATE_BOX, True, NQ)):
        l, h = K.boxes_aabb(P[nm + "_p"], P[nm + "_R"], box, cen)
        for i in range(n): lo[i] = np.minimum(lo[i], l[i * m:(i + 1) * m].min(0)); hi[i] = np.maximum(hi[i], h[i * m:(i + 1) * m].max(0))
    l, h = K.boxes_aabb(P["bus_p"], P["bus_R"], K.BUS, True); lo = np.minimum(lo, l); hi = np.maximum(hi, h); return lo, hi
def bodies(P, i):
    out = []
    for nm, box, cen, m in (("panel", K.PANEL_BOX, False, NP), ("plate", K.PLATE_BOX, True, NQ)):
        l, h = K.boxes_aabb(P[nm + "_p"][i * m:(i + 1) * m], P[nm + "_R"][i * m:(i + 1) * m], box, cen); out.append((l, h))
    return np.concatenate([o[0] for o in out]), np.concatenate([o[1] for o in out])
T_END = 1345.0; ts = np.concatenate([np.arange(0, 400, 0.5), np.arange(400, 1190, 5.0), np.arange(1190, T_END + 0.01, 0.25)])
mingap = np.full((n, n), 1e9); gapT = np.zeros((n, n)); real_overlap = []; rail_min = 1e9
rails = [(sx * 3.3, sy * 3.3) for sx in (-1, 1) for sy in (-1, 1)]
for T in ts:
    P = fl.poses(T); lo, hi = per_sat(P)
    sep = np.maximum(lo[:, None, :] - hi[None, :, :], lo[None, :, :] - hi[:, None, :]).max(-1)     # (n,n) gap, neg = overlap
    for i in range(n):
        for j in range(i + 1, n):
            if sep[i, j] < mingap[i, j]: mingap[i, j] = sep[i, j]; gapT[i, j] = T
            if sep[i, j] < 0.05:
                l1, h1 = bodies(P, i); l2, h2 = bodies(P, j)
                ov = (np.maximum(l1[:, None, :] - h2[None, :, :], l2[None, :, :] - h1[:, None, :]).max(-1) < 0).sum()
                if ov: real_overlap.append((float(T), i, j, int(ov)))
    # rails vs sats while any satellite is still near the bay (x within 6 m of the axis); AABB gap to rail cylinder axis (point) minus radius, in xy, only where z overlaps rail span (-5..22)
    for i in range(n):
        for (rx, ry) in rails:
            if hi[i, 2] > -5 and lo[i, 2] < 22 and abs(lo[i, 0]) < 8:
                l1, h1 = bodies(P, i)
                d = np.maximum(np.maximum(l1[:, 0] - rx, rx - h1[:, 0]), np.maximum(l1[:, 1] - ry, ry - h1[:, 1])); inz = (h1[:, 2] > -5) & (l1[:, 2] < 22)
                if inz.any(): rail_min = min(rail_min, float(d[inz].min()) - 0.08)
iu = np.triu_indices(n, 1); k = np.argmin(mingap[iu])
out = dict(note="ESTIMATE; kinematic model, AABB-level; sample steps 0.5 s (0-400 s), 5 s (to 1190 s), 0.25 s (unfold 1190-1345 s)", n_sats=n, T_end_s=T_END, min_pair_gap_m=float(mingap[iu].min()), min_pair=[int(iu[0][k]), int(iu[1][k])], min_pair_T_s=float(gapT[iu][k]),
           n_pairs_with_negative_gap=int((mingap[iu] < 0).sum()), real_body_overlaps=real_overlap[:50], n_real_overlap_events=len(real_overlap), rail_min_clearance_m=rail_min,
           exit_x_m_s=K.V_EXIT, pair_gap_by_pair={f"{i}-{j}": [float(mingap[i, j]), float(gapT[i, j])] for i in range(n) for j in range(i + 1, n) if mingap[i, j] < 5.0})
m_sat = 6426.1; m_ship = 200000.0; px = sum(sa.sgx * m_sat * K.V_EXIT for sa in fl.sats)
out["momentum"] = dict(label="ESTIMATE / ASSUMED", sat_mass_kg=m_sat, ship_mass_kg=m_ship, sum_sat_px_kg_m_s=px, ship_recoil_x_m_s_if_all_released=-px / (m_ship - 14 * m_sat), note="by construction: each release is an internal impulse; the ship (not drawn moving) takes the opposite momentum; net-zero momentum of ship+fleet. Extra drift velocities (v_y, v_z) are ASSUMED and applied after exit (their reaction is not tracked).")
json.dump(out, open(K.F / "clearance_T45.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "pair_gap_by_pair"}, indent=1)); print(sorted(out["pair_gap_by_pair"].items(), key=lambda kv: kv[1][0])[:8])
