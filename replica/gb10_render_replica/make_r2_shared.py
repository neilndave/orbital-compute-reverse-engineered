#!/usr/bin/env python3
"""[t441] Build scene/R2_shared_dist.json: the shared hero-camera distance table for Render 2 (June + August single satellites at the SAME scale).
usage: make_r2_shared.py <overlay_Jun> <overlay_Aug> <out.json>      overlays = ov1_Jun / ov1_Aug made by make_overlay.sh (ONE_SAT=44 / 29), numpy+scipy only (no Isaac).
For each build the repo hero-fit module computes the distance that puts its bbox at FILL of the frame (raw table, every 4 frames); the shared distance is the pointwise MAX of the two raw tables, then the same
envelope smoothing as the repo (max filter + gaussian).  So neither satellite is cropped and both are drawn at the same pixels/metre.  Run again whenever FLEET_TAU_W (width-fold timing) or a stage plan changes."""
import sys, os, json, subprocess, pathlib, numpy as np
HERE = pathlib.Path(__file__).resolve().parent; PYV = os.environ.get("PYV", sys.executable)
ovs = {"Jun": os.path.abspath(sys.argv[1]), "Aug": os.path.abspath(sys.argv[2])}; out = os.path.abspath(sys.argv[3])
SUB = r'''
import sys, os, json, numpy as np
sys.path.insert(0, os.getcwd())
import fleet_hero_t363_T45 as H
json.dump({"f": H._GF.tolist(), "G": H._G.tolist(), "FOV": H.FOV, "FILL": H.FILL, "AZ": float(np.degrees(H.AZ)), "EL": float(np.degrees(H.EL))}, open(sys.argv[1], "w"))
'''
raw = {}
for B, ov in ovs.items():
    import tempfile; tmp = pathlib.Path(tempfile.gettempdir()) / f"r2_raw_{B}.json"
    env = dict(os.environ); env.update(RTS_TAG="_T45", FLEET_OVERLAY="new", FLEET_ODD_SPEED=env.get("FLEET_ODD_SPEED", "2.6"),
        FLEET_STAGEPLAN=str(HERE / f"scene/{B}/stage_plan_single_{B}.json"), FLEET_HERO_CAM=(HERE / "scene/R2_hero_cam.json").read_text())
    # the replica render env (width-fold timing etc.) is sourced from the overlay's env file
    cmd = f'cd "{ov}/experiments/poster" && source ./fleet_replica_env.sh >/dev/null && "{PYV}" -c \'{SUB}\' "{tmp}"'
    subprocess.run(["bash", "-c", cmd], env=env, check=True); raw[B] = json.load(open(tmp)); tau_w = None
tw = subprocess.run(["bash", "-c", f'cd "{ovs["Aug"]}/experiments/poster" && source ./fleet_replica_env.sh >/dev/null && echo $FLEET_TAU_W'], capture_output=True, text=True, env={**os.environ, "RTS_TAG": "_T45"}).stdout.strip()
f = np.array(raw["Jun"]["f"]); assert np.allclose(f, raw["Aug"]["f"])
dj = np.array(raw["Jun"]["G"])[:, 3]; da = np.array(raw["Aug"]["G"])[:, 3]; d = np.maximum(dj, da)
from scipy.ndimage import maximum_filter1d, gaussian_filter1d
SW, SS = 1, 3.0                                   # repo defaults (R2_hero_cam.json has no sw/ss)
ds = gaussian_filter1d(maximum_filter1d(d, size=2 * SW + 1, mode="nearest"), sigma=SS / 4.0, mode="nearest")
ds = np.maximum(ds, d)                            # never below either raw fit distance (gaussian can dip below a narrow peak)
json.dump({"f": f.tolist(), "d": ds.tolist(), "tau_w": float(tw), "d_raw_Jun": dj.tolist(), "d_raw_Aug": da.tolist(), "fov": raw["Aug"]["FOV"], "fill": raw["Aug"]["FILL"], "az": raw["Aug"]["AZ"], "el": raw["Aug"]["EL"],
           "note": "shared hero-camera distance (m) for Render 2, built by make_r2_shared.py; ESTIMATE/ASSUMED editorial camera"}, open(out, "w"))
print(f"wrote {out}: shared d {ds.min():.1f}..{ds.max():.1f} m (June raw max {dj.max():.1f}, August raw max {da.max():.1f}), tau_w {tw}")
