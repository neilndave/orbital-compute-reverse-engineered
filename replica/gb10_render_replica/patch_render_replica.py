#!/usr/bin/env python3
"""[t441] overlay-only patches of the RENDER script and cameras (the repo is never touched).  usage: patch_render_replica.py <overlay_dir> <Jun|Aug>
 1. makes sure the overlay render script is the box-tested one (has the FLEET_HERO_CAM hook and the K.NPAN_TOT caption).  The GB10 repo copy (t359b) is OLDER: no hero-camera hook (so R2 silently used the repo's 900 m fleet camera) and a
    hard-coded '228 radiator panels'.  If the overlay copy differs from scene/box_scripts/ it is replaced (original kept as *.repo_orig in the overlay), same for fleet_hero_t363_T45.py.
 2. fleet-fit camera hook (R1, env FLEET_FIT_CAM)  [patch_fit_cam.py]  and shared-distance hero camera hook (R2, env FLEET_R2_SHARED).
 3. replica caption (env REPLICA_BUILD=Jun|Aug, REPLICA_ONE_SAT=0|1): 'replica, not SpaceX's design', June 46 / August 30 per Starship (ESTIMATE), NASA Blue Marble credit unchanged.
 4. env FLEET_HIDE_SHIP=1 hides the schematic hull/deck/rails (R2: one satellite, the ship is 240 m away and only shows as a grey column in wide views)."""
import sys, pathlib, shutil, subprocess, hashlib
H = pathlib.Path(__file__).resolve().parent; ov = pathlib.Path(sys.argv[1]); q = ov / "experiments/poster"; B = sys.argv[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for n in ("render_fleet_omniverse_t360_T45.py", "fleet_hero_t363_T45.py"):
    src = H / "scene/box_scripts" / n; dst = q / n
    if not dst.exists() or sha(dst) != sha(src):
        if dst.exists(): shutil.copy(dst, str(dst) + ".repo_orig")
        shutil.copy(src, dst); print(f"  replaced {n} by the box-tested copy (repo copy differed or was missing)")
subprocess.run([sys.executable, str(H / "patch_fit_cam.py"), str(ov)], check=True)
shutil.copy(H / "fleet_hero_r2_shared.py", q)
p = q / "render_fleet_omniverse_t360_T45.py"; s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, "patch target not found exactly once: " + old[:70]
    s = s.replace(old, new)
rep('elif os.environ.get("FLEET_HERO_CAM"):\n    import fleet_hero_t363_T45 as HC\n', 'elif os.environ.get("FLEET_R2_SHARED"):      # [t441] R2: June/August at one shared camera distance\n    import fleet_hero_r2_shared as HC\nelif os.environ.get("FLEET_HERO_CAM"):\n    import fleet_hero_t363_T45 as HC\n')
# caption
rep('OV_T337 = f"Fold and release: kinematic.  Array accordion: cable-sync model (ESTIMATE).  Yoke, component pod and blocks: ASSUMED, illustrative.  {K.NPAN_TOT} radiator panels each."',
    '_RB = os.environ.get("REPLICA_BUILD", ""); _RN = {"Jun": 46, "Aug": 30}.get(_RB, 0); _RNAME = {"Jun": "June", "Aug": "August"}.get(_RB, "")   # [t441] replica caption\n'
    'CAP1 = "SIMULATED \\u2013 replica, not SpaceX\'s design \\u2013 assumed parameters (ESTIMATES)" + (f" \\u2013 {_RNAME} build: {_RN} satellites per Starship (ESTIMATE)" if _RN else "")\n'
    'OV_T337 = ("One satellite.  " if os.environ.get("REPLICA_ONE_SAT", "0") == "1" else "") + f"Fold and release: kinematic.  Array accordion: cable-sync model (ESTIMATE).  Yoke, component pod and blocks: ASSUMED.  {K.NPAN_TOT} radiator panels each."')
rep('"SIMULATED \\u2013 assumed dispenser and hinge parameters (ESTIMATES) \\u2013 pre-flight design study, 13 satellites per launch"', 'CAP1')
# hide the schematic ship
rep('NO_RAILS = os.environ.get("FLEET_NO_RAILS", "0") == "1"', 'NO_RAILS = os.environ.get("FLEET_NO_RAILS", "0") == "1" or os.environ.get("FLEET_HIDE_SHIP", "0") == "1"')
rep('cyl("/World/Ship/hull", 4.5, 60.0, (0, 0, -30.3 - DD), HULL); cyl("/World/Ship/deck", 4.5, 0.3, (0, 0, -0.15 - DD), DECKM)\n',
    'cyl("/World/Ship/hull", 4.5, 60.0, (0, 0, -30.3 - DD), HULL); cyl("/World/Ship/deck", 4.5, 0.3, (0, 0, -0.15 - DD), DECKM)\n'
    'if os.environ.get("FLEET_HIDE_SHIP", "0") == "1":      # [t441] R2: no hull / deck / rails (rails are not created because NO_RAILS is forced above)\n'
    '    for _n in ("hull", "deck"): UsdGeom.Imageable(stage.GetPrimAtPath(f"/World/Ship/{_n}")).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)\n')
p.write_text(s); print("patched", p, "(hook, caption, hide-ship)")
