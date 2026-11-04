#!/usr/bin/env python3
"""t438 render-scene adapter stage 2: patch the OVERLAY COPY of experiments/poster/fleet_kin_T45.py (never the repo file) so it reads the replica layout:
  (1) per-wing radiator column counts and 9/10-panel columns from layout['_replica']['column_plan'] (repo: 12 columns per wing, 13 thick / 11 thin);
  (2) radiator items assigned to columns in order (repo: thick/thin by item thickness, which the replica packer does not distinguish);
  (3) second-stage array fold n sections (repo: hard-coded NSEC=4) via layout['fold'] (kinematic: zig-zag sections about the leaf axis, ASSUMED, same as the repo's n=4 model).
usage: patch_fleet_kin.py <overlay_dir>.   Each replacement is asserted to match exactly once."""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / "experiments/poster/fleet_kin_T45.py"; s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, ("patch target not found exactly once", old[:70]); s = s.replace(old, new)
rep("NSEC = 4; SECW = ARRW / NSEC;", "NSEC = int(LAY.get('fold', 4)) if '_replica' in LAY else 4; SECW = ARRW / NSEC;")
rep("NPAN = {(w, c): ALONG + (1 if c in THICK[w] else 0) for w in (0, 1) for c in range(ACROSS)}",
    "_REP = LAY.get('_replica')\nif _REP:\n    _cp = _REP['column_plan']; NCOLS = {0: _cp['wing0_cols'], 1: _cp['wing1_cols']}; _ppc = _cp['panels_per_column']; _cmn = min(_ppc)\n    THICK = {0: [c for c in range(NCOLS[0]) if _ppc[c] > _cmn], 1: [c for c in range(NCOLS[1]) if _ppc[NCOLS[0] + c] > _cmn]}\nelse: NCOLS = {0: ACROSS, 1: ACROSS}\nNPAN = {(w, c): ALONG + (1 if c in THICK[w] else 0) for w in (0, 1) for c in range(NCOLS[w])}")
rep("want_thick = [(w, c) for w in (0, 1) for c in range(ACROSS) if NPAN[(w, c)] > ALONG]; want_thin = [(w, c) for w in (0, 1) for c in range(ACROSS) if NPAN[(w, c)] == ALONG]",
    "want_thick = [(w, c) for w in (0, 1) for c in range(NCOLS[w]) if NPAN[(w, c)] > ALONG]; want_thin = [(w, c) for w in (0, 1) for c in range(NCOLS[w]) if NPAN[(w, c)] == ALONG]")
rep("assert len(thick) == len(want_thick) and len(thin) == len(want_thin), (len(thick), len(thin))",
    "if _REP: thick = rad_items[:len(want_thick)]; thin = rad_items[len(want_thick):]      # t438: replica packer items are not distinguished by thickness; assigned in order\n        assert len(thick) == len(want_thick) and len(thin) == len(want_thin), (len(thick), len(thin))")
# generalised array section chain (n sections, zig-zag -a,0,-a,0,...; anchor = section 1 at its deployed position)
rep("    al = np.array([-a, 0.0, -a, 0.0]); yv = np.zeros(4); nv = np.zeros(4); yv[1] = -SECW / 2\n    yv[2] = yv[1] + 0.5 * SECW * (math.cos(al[1]) + math.cos(al[2])); nv[2] = nv[1] + 0.5 * SECW * (math.sin(al[1]) + math.sin(al[2]))\n    yv[3] = yv[2] + 0.5 * SECW * (math.cos(al[2]) + math.cos(al[3])); nv[3] = nv[2] + 0.5 * SECW * (math.sin(al[2]) + math.sin(al[3]))\n",
    "    al = np.array([(-a if k % 2 == 0 else 0.0) for k in range(NSEC)]); yv = np.zeros(NSEC); nv = np.zeros(NSEC); yv[1] = (1 - (NSEC - 1) / 2) * SECW\n    for k in range(2, NSEC):\n        yv[k] = yv[k - 1] + 0.5 * SECW * (math.cos(al[k - 1]) + math.cos(al[k])); nv[k] = nv[k - 1] + 0.5 * SECW * (math.sin(al[k - 1]) + math.sin(al[k]))\n")
rep("lev = np.array([3, 2, 1, 0]) * P_ARR * (a / math.pi)", "lev = (NSEC - 1 - np.arange(NSEC)) * P_ARR * (a / math.pi)")
rep("t_rad = TAU_RAD0 + TAU_RSTEP * (c + ACROSS * w)", "t_rad = TAU_RAD0 + TAU_RSTEP * (c + ACROSS * w)   # (ACROSS = max columns per wing)")
# ---- t440: pod mount from layout, pod body index = n_cols+4 (repo hard-codes 28 = 24 columns + 2 arrays + 2 yokes), clip scaling to N satellites, width-fold timing hook
rep("POD_MOUNT = np.array([0.0, 0.0, -(0.5 * 4.6259399977594295 + 0.6 + 0.05)])", "POD_MOUNT = np.array([0.0, 0.0, LAY['_replica']['pod_mount_m'] if LAY.get('_replica') else -(0.5 * 4.6259399977594295 + 0.6 + 0.05)])")
rep("s_ = stage(28); Cc = cpk * (1 - s_)", "s_ = stage(len(sa.n_cols) + 4); Cc = cpk * (1 - s_)")
rep("planpose(sa.idx, 28, tau)", "planpose(sa.idx, len(sa.n_cols) + 4, tau)")
rep("T_U0 = 1200.0; T_UST = 3.0; T_ATT0 = 30.0; T_ATT1 = 500.0",
    "T_U0 = 1200.0; T_UST = 3.0; T_ATT0 = 30.0; T_ATT1 = 500.0\nif LAY.get('_replica'):\n    _c = LAY['_replica']['clip']; T_STAG = float(os.environ.get('FLEET_T_STAG', _c['t_stag'])); T_UST = float(os.environ.get('FLEET_T_UST', _c['t_ust'])); V_Z = float(os.environ.get('FLEET_VZ', _c['v_z']))   # t440: scaled to N satellites (ASSUMED)")
rep("sa.vz = V_Z * (self.rank[sa.idx] - 6.5)", "sa.vz = V_Z * (self.rank[sa.idx] - 0.5 * (len(self.sats) - 1))")
rep("TAU_W = 14.0;", "TAU_W = float(os.environ.get('FLEET_TAU_W', '14.0'));")   # 14 s PLACEHOLDER (repo value) until Newton wfold results; apply_wfold_timing.py prints the value to export
# ---- t440: stowed pitches of the replica (radiator panels 10 mm pitch, 3 mm panel; array leaves = layout stack_pitch, plate box 1 mm thinner than the pitch). Repo: 18.14 mm / 14 mm panel, 9 mm leaf pitch, 10 mm plate.
rep('TH_ARR = LAY["array_thick_mm"] * mm; P_ARR = 0.009; P_RAD = 0.1633 / 9.0', 'TH_ARR = (LAY["stack_pitch_mm"] - 1.0) * mm if "_replica" in LAY else LAY["array_thick_mm"] * mm; P_ARR = LAY["stack_pitch_mm"] * mm if "_replica" in LAY else 0.009; P_RAD = LAY["_replica"]["rad_pitch_mm"] * mm if "_replica" in LAY else 0.1633 / 9.0')
rep("PANEL_BOX = np.array([W, L, 0.014])", "PANEL_BOX = np.array([W, L, 0.003 if '_replica' in LAY else 0.014])")
# ---- t440b: layer cells whose satellites are rot90 in the packer's arrangement (Jun 17 of 19 layers, Aug 12 of 18) are stowed yawed 90 deg about z (the repo only had unrotated cells); the yaw is part of the stowed attitude Rp' = Rz90 @ Rp and relaxes to nominal with the repo attitude slerp
rep('s = [q for q in Ly["sats"] if q["sat"] == sat_idx][0]; self.p0 =', 's = [q for q in Ly["sats"] if q["sat"] == sat_idx][0]; self.rot90 = bool(s.get("rot90", False)) and bool(LAY.get("_replica")); self.p0 =')
rep("sa.rv_p = R_to_rotvec(sa.Rp)", "sa.rv_p = R_to_rotvec((Rz(np.float64(math.pi / 2)) @ sa.Rp) if sa.rot90 else sa.Rp)")
rep("sa.Tex = sa.Trel + (X / 2 + 3.7) / V_EXIT;", "sa.Tex = sa.Trel + ((abs(sa.p0[0]) + (PK['layers'][sa.layer]['Y'] if sa.rot90 else X) / 2 + 3.7) if sa.rot90 or '_replica' in LAY else (X / 2 + 3.7)) / V_EXIT;")
rep("HERO = 6\ndef camera", "HERO = int(os.environ.get('FLEET_HERO_IDX', '6'))\ndef camera")   # t440c: R2 single-satellite scenes follow sat 0 (the repo index 6 does not exist with 1 satellite)
rep("hero = fleet.centre(fleet.sats[HERO], T)", "hero = fleet.centre(fleet.sats[min(HERO, len(fleet.sats) - 1)], T)")
p.write_text(s); print("patched", p)

# ---- also patch the full-clearance checker (hard-codes 80 plates/wing = 20 leaves x 4 sections) in the overlay copy
q = pathlib.Path(sys.argv[1]) / "experiments/poster/fleet_full_clearance_T45.py"; s = q.read_text()
rep("for q in range(80): kind.append(1)", "for q in range(K.NLEAF * K.NSEC): kind.append(1)")
rep("np.abs(sa_ // 4 - sb_ // 4) <= 1", "np.abs(sa_ // K.NSEC - sb_ // K.NSEC) <= 1")
rep("(ga == gb) & (sb_ < 4)) | ((kb == 3) & (ka == 1) & (ga == gb) & (sa_ < 4))", "(ga == gb) & (sb_ < K.NSEC)) | ((kb == 3) & (ka == 1) & (ga == gb) & (sa_ < K.NSEC))")
q.write_text(s); print("patched", q)
