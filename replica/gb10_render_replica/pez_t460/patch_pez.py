#!/usr/bin/env python3
"""[t460] overlay-only: indexed-PEZ build for Render 1.  usage: patch_pez.py <overlay_dir>   (run AFTER make_overlay's other patches; everything is gated by env FLEET_PEZ=1 / FLEET_PEZ_CAM, so overlay behaviour without them is unchanged)"""
import sys, pathlib, shutil
H = pathlib.Path(__file__).resolve().parent; q = pathlib.Path(sys.argv[1]) / "experiments/poster"
for f in ("pez_release.py", "fleet_pez_cam.py", "pez_ship_usd.py"): shutil.copy(H / f, q)
def sub(p, old, new, cnt=1):
    s = p.read_text(); assert s.count(old) == cnt, (p.name, old[:60], s.count(old)); p.write_text(s.replace(old, new))
# 1) kinematics: install before the module-level fleet is created
k = q / "fleet_kin_T45.py"
sub(k, "_FL = Fleet()\n", 'if os.environ.get("FLEET_PEZ", "0") == "1":      # [t460] indexed PEZ release (Render 1 only)\n    import pez_release as _PZ; _PZ.install(globals())\n_FL = Fleet()\n')
# 2) render script
r = q / "render_fleet_omniverse_t360_T45.py"
sub(r, 'def set_cam(eye, tgt, fov):', 'def set_cam(eye, tgt, fov, up=None):')
sub(r, 'Gf.Vec3d(0, 0, 1)).GetInverse())', 'Gf.Vec3d(0, 0, 1) if up is None else Gf.Vec3d(*map(float, up))).GetInverse())')
sub(r, 'set_cam(*(HC.camera(tc * K.FPS, FL, T) if HC is not None else K.camera(tc, FL, T))); set_rails(tc * K.FPS)',
       'set_cam(*(HC.camera(tc * K.FPS, FL, T) if HC is not None else K.camera(tc, FL, T)), up=(HC.up(tc * K.FPS) if (HC is not None and hasattr(HC, "up")) else None)); set_rails(tc * K.FPS)')
sub(r, 'if os.environ.get("FLEET_FIT_CAM"):      # [t441] fleet-fit camera (R1)\n    import fleet_fit_cam_replica as HC\n',
       'if os.environ.get("FLEET_PEZ_CAM"):      # [t460] slot camera -> fleet-fit (indexed PEZ, R1)\n    import fleet_pez_cam as HC\nelif os.environ.get("FLEET_FIT_CAM"):      # [t441] fleet-fit camera (R1)\n    import fleet_fit_cam_replica as HC\n')
sub(r, 'OV_ORIG = os.environ.get("FLEET_OVERLAY", "new") == "orig"',
       'if os.environ.get("FLEET_PEZ", "0") == "1": OV_T337 = "Indexed pass-through release: the stack steps layer by layer past the slot and each satellite is pushed out edge-first.  Slot 7.3 m (3RD) x 1.8 m (ASSUMED).  Push speed 2.0 m/s (INFERENCE)."   # [t460]\nOV_ORIG = os.environ.get("FLEET_OVERLAY", "new") == "orig"')
sub(r, '    d.rectangle([0, H - int(fs * 2.6), W, H], fill=(0, 0, 0, BA))\n    lab = K.time_label(T)',
       '    if os.environ.get("FLEET_PEZ", "0") == "1":      # [t483] third caption line (labels + stowed-yoke note), clear of the bottom credit\n        d.rectangle([0, int(fs * 3.3), W, int(fs * 4.8)], fill=(0, 0, 0, BA)); d.text((m, int(fs * 3.3)), "Push-speed basis: public Flight 14 clip.  Fold: kinematic.  Yoke, pod, blocks: ASSUMED.  Stowed yokes omitted for clarity; they appear during unfold.", font=f2, fill=(215, 215, 215, 255))\n    d.rectangle([0, H - int(fs * 2.6), W, H], fill=(0, 0, 0, BA))\n    lab = K.time_label(T)')
sub(r, 'DECKM = material("deck"', 'DECKM = material("deck"')   # sanity: anchor exists
sub(r, 'for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)] if not NO_RAILS else []): cyl(',
       'if os.environ.get("FLEET_PEZ", "0") == "1":      # [t460] indexed PEZ: slotted horizontal hull, old vertical hull/deck/rails hidden\n    assert NO_RAILS, "set FLEET_NO_RAILS=1 for the PEZ build"\n    for _n in ("hull", "deck"): UsdGeom.Imageable(stage.GetPrimAtPath(f"/World/Ship/{_n}")).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)\n    import pez_ship_usd; pez_ship_usd.build(stage, UsdGeom, Gf, Vt, UsdShade, HULL, DECKM)\nfor i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)] if not NO_RAILS else []): cyl(')
sub(r, '(f"time-lapse x{rate:,.0f}" if rate > 1.5 else "real time") + SLOWTAG',
       '(f"time-lapse x{rate:,.0f}" if rate > 1.5 else "real time") + SLOWTAG + ("   |   time-compressed; real gaps ~30-70 s" if (os.environ.get("FLEET_PEZ", "0") == "1" and T < K.T_U0) else "")')
print("patched PEZ ->", q)

# [t460] per-satellite accordion start (env FLEET_N0_SAT="27:36.55,28:36.55,29:36.75", unset = unchanged).  CAUSE: sats 27-29 are planned (plates+yoke) until tau 36.05-36.25 s, AFTER the global accordion start N0 = 29.6 s; the yoke (anchored to the plates) then folds through the bus (yoke_bus -0.42 m, yoke_yoke -0.12 m, tau 31.7-35.5 s).  FIX: those sats start their accordion when their plan has finished (N0_s = t_ready + 0.5 s).
_k = pathlib.Path(sys.argv[1]) / "experiments/poster/fleet_kin_T45.py"; _s = _k.read_text()
_o1 = 'TAU_N0 = float(os.environ.get("FLEET_TAU_N0", "27.0"));'
_o2 = "tn = tau - TAU_N0;"
assert _s.count(_o1) == 1 and _s.count(_o2) == 1, "N0_SAT patch target"
_s = _s.replace(_o1, _o1 + ' N0_SAT = {int(_a.split(":")[0]): float(_a.split(":")[1]) for _a in os.environ.get("FLEET_N0_SAT", "").split(",") if _a};').replace(_o2, "tn = tau - N0_SAT.get(sa.idx, TAU_N0);")
_k.write_text(_s); print("patched N0_SAT ->", _k)
shutil.copy(pathlib.Path(__file__).parent / "yokehold_plan_n0s.py", pathlib.Path(sys.argv[1]) / "experiments/poster/yokehold_plan_n0s.py")
