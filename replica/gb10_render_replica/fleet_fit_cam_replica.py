"""[t441] OPT-IN fleet-fit camera for Render 1 (default OFF; nothing here is imported unless env FLEET_FIT_CAM is set; kinematics and plan untouched, playback = identity: output frame f = clip frame f, 816 frames).
Same module interface as fleet_hero_t363_T45 (HERO, N_TOTAL, camera(fo, FL, T), orig_frame, rate_label, speed) so the render script and camera_extent_replica.py use it through the same hook (patch_fit_cam.py).
Design (all editorial = ASSUMED):  frames < b0  the unchanged repo camera K.camera (release act; it frames the fleet there);  b0..b1  smoothstep blend to a FLEET-FIT camera;  after b1 the fit camera:
 look direction = from the repo's A0 direction (frame 0) to the repo's B1 direction (side view from -y, ~19 deg elevation, as in the unchanged clip) by frame 216; target = centre of the projected bbox of ALL satellites (or env group);
 distance = smallest that keeps every satellite corner inside the safe box at FILL of the half-frame, then a GUARD pass (tabulated every 4 frames) that only ever zooms OUT until all corners are inside the 960x540 safe box (x 10..950, y 60..505), then an upper-envelope + gaussian smooth.
env FLEET_FIT_CAM = JSON, e.g. {} or {"fov":40,"fill":0.80,"b0":60,"b1":170,"group":[0,1,2],"el_end":null}.  group = satellites to keep framed (default: all)."""
import os, json
import numpy as np
import fleet_kin_T45 as K
C = json.loads(os.environ.get("FLEET_FIT_CAM") or "{}")
FOV = float(C.get("fov", 40.0)); FILL = float(C.get("fill", 0.80)); B0 = float(C.get("b0", 60.0)); B1 = float(C.get("b1", 170.0)); A_END = float(C.get("dir_end_f", 216.0))
_FL = K.Fleet(); GROUP = [int(x) for x in C["group"]] if "group" in C else list(range(_FL.n))
HERO = K.HERO; N_TOTAL = 816; ASPECT = float(os.environ.get("FLEET_HERO_ASPECT", str(9 / 16)))
_E = K._ease
def speed(fo): return 1.0
def orig_frame(n): return min(float(n), 815.0)
def rate_label(fo): return K.sim_rate(fo / K.FPS)
_OFF = np.array([[sx * 1.3, sy * 1.3, sz * 0.6] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
def _pts(T, sats):
    P = _FL.poses(T); np_, nq = K.NPAN_TOT, 2 * K.NLEAF * K.NSEC; Qs = []
    for h in sats:
        Qs.append(np.concatenate([P["panel_p"][h * np_:(h + 1) * np_], P["plate_p"][h * nq:(h + 1) * nq], P["bus_p"][h:h + 1], P["yoke_p"][2 * h:2 * h + 2], P["pod_p"][h:h + 1]]))
    return (np.concatenate(Qs)[:, None, :] + _OFF[None]).reshape(-1, 3)
_A0 = (np.array([52.0, -44.0, 16.0]), np.array([0.0, 0.0, 9.0])); _B1 = (np.array([260.0, -820.0, 300.0]), np.array([0.0, 0.0, 8.0]))
_D0 = (_A0[0] - _A0[1]) / np.linalg.norm(_A0[0] - _A0[1]); _D1 = (_B1[0] - _B1[1]) / np.linalg.norm(_B1[0] - _B1[1])
def _dir(fo):
    w = _E(fo / A_END); d = _D0 * (1 - w) + _D1 * w; return d / np.linalg.norm(d)
def _fit(Q, D):
    f = -D; r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f); tx = np.tan(np.radians(FOV) / 2); ty = tx * ASPECT
    c = 0.5 * (Q.min(0) + Q.max(0)); d = 60.0
    for _ in range(60):
        e = c + D * d; v = Q - e; z = v @ f; xn = (v @ r) / z / tx; yn = (v @ u) / z / ty
        c = c + r * (0.5 * (xn.min() + xn.max()) * tx * d) + u * (0.5 * (yn.min() + yn.max()) * ty * d)
        e = c + D * d; v = Q - e; z = v @ f; xn = (v @ r) / z / tx; yn = (v @ u) / z / ty
        ext = max(0.5 * (xn.max() - xn.min()) / FILL, 0.5 * (yn.max() - yn.min()) / FILL); d = max(d * (ext ** 0.8 if ext > 0 else 1.0), 4.0)
    return c, d
def _inbox(Q, e, t):
    fwd = t - e; fwd = fwd / np.linalg.norm(fwd); r = np.cross(fwd, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, fwd); v = Q - e; z = v @ fwd
    if (z <= 0.1).any(): return False
    fpx = 0.5 * 960 / np.tan(np.radians(FOV) / 2); X = 480 + fpx * (v @ r) / z; Y = 270 - fpx * (v @ u) / z
    return bool((X >= 12).all() and (X <= 948).all() and (Y >= 62).all() and (Y <= 503).all())
_GF = np.arange(0.0, 816.0, 4.0); _GF = np.append(_GF, 815.0); _TAB = []; _KQ = []
def _blend(fo, c, d):
    base = K.camera(fo / K.FPS, _FL, K.sim_time(fo / K.FPS)); w = _E((fo - B0) / (B1 - B0))
    e = c + _dir(fo) * d
    if w <= 0.0: return base
    return base[0] * (1 - w) + e * w, base[1] * (1 - w) + c * w, base[2] * (1 - w) + FOV * w
for _f in _GF:
    _T = K.sim_time(_f / K.FPS); _Q = _pts(_T, GROUP); _c, _d = _fit(_Q, _dir(_f)); _e, _t, _fv = _blend(_f, _c, _d); _k = 1.0
    if _fv == FOV or _f > B0:
        while not _inbox(_Q, _t + (_e - _t) * _k, _t) and _k < 40.0: _k *= 1.02
    _TAB.append((_c, _d, _k))
_C = np.array([x[0] for x in _TAB]); _D = np.array([x[1] for x in _TAB]); _KK = np.array([x[2] for x in _TAB])
from scipy.ndimage import maximum_filter1d, gaussian_filter1d
_KS = np.maximum(gaussian_filter1d(maximum_filter1d(_KK, size=7, mode="nearest"), sigma=1.5, mode="nearest"), _KK)      # envelope then smooth, never below the per-frame requirement
_DS = gaussian_filter1d(_D, sigma=2.0, mode="nearest"); _CS = gaussian_filter1d(_C, sigma=2.0, axis=0, mode="nearest")
def camera(fo, FL=None, T=None):
    c = np.array([np.interp(fo, _GF, _CS[:, i]) for i in range(3)]); d = float(np.interp(fo, _GF, _DS)); k = float(np.interp(fo, _GF, _KS))
    e, t, fv = _blend(fo, c, d); return t + (e - t) * k, t, fv
