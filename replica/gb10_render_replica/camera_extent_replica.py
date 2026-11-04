"""Replica camera framing check (R1 fleet / R2 single): projects every satellite OBB corner through the clip camera at sampled frames and reports the fraction of frames with any corner outside the 960x540 safe box.
Run from <overlay>/experiments/poster with the replica env sourced and (R1) FLEET_STAGEPLAN set.  usage: camera_extent_replica.py [stride=20] [f0 f1]
ESTIMATE: uses the repo camera (t360 hold) unchanged; satellites outside the box = the camera does not frame them (R1 needs a camera retune if many)."""
import sys, os, numpy as np
sys.path.insert(0, os.getcwd()); _a = sys.argv; sys.argv = [_a[0], "/tmp/x.json", "0", "1", "1"]
import silhouette_check_T45 as S
K = S.K; fl = S.fl; sys.argv = _a
H = None
if os.environ.get('FLEET_R2_SHARED'):
    import fleet_hero_r2_shared as H     # [t441] R2: shared-distance hero camera (June and August at one scale)
elif os.environ.get('FLEET_FIT_CAM'):
    import fleet_fit_cam_replica as H    # [t441] R1: fleet-fit camera (frame number in)
elif os.environ.get('FLEET_HERO_CAM'):
    import fleet_hero_t363_T45 as H      # R2: hero-fit close-up camera (frame number in, not clip seconds)
st = int(_a[1]) if len(_a) > 1 else 20; f0 = int(_a[2]) if len(_a) > 2 else 0; f1 = int(_a[3]) if len(_a) > 3 else int(round(K.CLIP_S * K.FPS))
rows = []; nout = 0
for f in range(f0, f1, st):
    T = K.sim_time(f / K.FPS); P = fl.poses(T); eye, tgt, fov = (H.camera(float(f), fl, T) if H else K.camera(f / K.FPS, fl, T))
    pts = np.vstack([S.corners(P, i)[0] for i in range(fl.n)]); uv, zc = S.proj(pts, eye, tgt, fov)
    ok = (zc > 0.1)
    out = (uv[:, 0] < 10) | (uv[:, 0] > 950) | (uv[:, 1] < 60) | (uv[:, 1] > 505) | ~ok
    nsat_out = len({i for i in range(fl.n)} ) if False else None
    frac = out.mean(); nout += frac > 0
    ppm = 960 / (2 * np.linalg.norm(eye - tgt) * np.tan(np.radians(fov) / 2))     # [t441] pixels per metre at the target depth (960 px wide frame; equal fov+distance = equal scale)
    rows.append((f, T, frac, uv[ok, 0].min(), uv[ok, 0].max(), uv[ok, 1].min(), uv[ok, 1].max()))
    print(f"frame {f:4d} T {T:7.1f}s  corners outside safe box {100 * frac:5.1f}%  extent x {rows[-1][3]:.0f}..{rows[-1][4]:.0f} y {rows[-1][5]:.0f}..{rows[-1][6]:.0f}  scale {ppm:6.2f} px/m", flush=True)
print(f"frames with any corner outside: {nout}/{len(rows)}")
