#!/usr/bin/env python3
"""[t441] overlay-only: let the render script use the fleet-fit camera module when env FLEET_FIT_CAM is set (same HC hook as the hero camera; default unchanged).  usage: patch_fit_cam.py <overlay_dir>"""
import sys, pathlib, shutil
H = pathlib.Path(__file__).resolve().parent; q = pathlib.Path(sys.argv[1]) / "experiments/poster"; shutil.copy(H / "fleet_fit_cam_replica.py", q)
p = q / "render_fleet_omniverse_t360_T45.py"; s = p.read_text()
old = 'if os.environ.get("FLEET_HERO_CAM"):\n    import fleet_hero_t363_T45 as HC\n'
new = 'if os.environ.get("FLEET_FIT_CAM"):      # [t441] fleet-fit camera (R1)\n    import fleet_fit_cam_replica as HC\nelif os.environ.get("FLEET_HERO_CAM"):\n    import fleet_hero_t363_T45 as HC\nif HC is not None:\n'
assert s.count(old) == 1, "patch target not found exactly once"
s = s.replace(old, new); p.write_text(s)
# the print line that followed is now under "if HC is not None:" (indent unchanged, 4 spaces)
print("patched", p)
