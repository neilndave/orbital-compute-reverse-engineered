"""[t441] OPT-IN Render-2 camera with ONE SHARED DISTANCE for the June and the August clip (true common scale).  Imported only when env FLEET_R2_SHARED=<table.json> is set (together with FLEET_HERO_CAM).
It is the repo hero-fit camera (fleet_hero_t363_T45) with its distance column replaced by the shared table scene/R2_shared_dist.json (made by make_r2_shared.py = envelope of the June and the August fit distances,
so BOTH satellites stay inside the safe box).  Same fov + same distance in both clips -> identical pixels per metre at equal depth; the camera centre/direction still follow each satellite.  Kinematics untouched.
Safety: the table records FLEET_TAU_W and the stage-plan checksum it was built for; a mismatch aborts (re-run make_r2_shared.py after applying new width-fold timing)."""
import os, json, hashlib
import numpy as np
import fleet_hero_t363_T45 as H
_T = json.load(open(os.environ["FLEET_R2_SHARED"]))
if abs(float(_T["tau_w"]) - float(os.environ.get("FLEET_TAU_W", "14.0"))) > 1e-6:
    raise SystemExit(f"R2 shared-distance table was built for FLEET_TAU_W={_T['tau_w']} but the env has {os.environ.get('FLEET_TAU_W')}: re-run make_r2_shared.py")
_d = np.interp(H._GF, np.array(_T["f"], float), np.array(_T["d"], float))
H._GS[:, 3] = _d; H._GGS[:, 3] = _d          # hero close-up and the (unused, q0 > 815) group fit share the distance
HERO = H.HERO; N_TOTAL = H.N_TOTAL; camera = H.camera; orig_frame = H.orig_frame; rate_label = H.rate_label; speed = H.speed
_FL = H._FL; _pts = H._pts; _cam = H._cam; _GS = H._GS; _GF = H._GF; FOV = H.FOV
print("R2 shared-distance camera on:", os.environ["FLEET_R2_SHARED"], "d(340)=%.1f d(815)=%.1f m" % (np.interp(340, H._GF, _d), np.interp(815, H._GF, _d)), flush=True)
