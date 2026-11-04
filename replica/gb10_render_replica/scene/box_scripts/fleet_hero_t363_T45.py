"""[t363] OPT-IN hero close-up camera + unfold retime (default OFF; nothing here is imported unless env FLEET_HERO_CAM is set).
Render-level / playback-level only: kinematics, plan and physics are untouched.  All values editorial (ASSUMED) except where measured.
env FLEET_HERO_CAM = JSON {"hero":11,"az":0,"el":45,"fov":40,"fill":0.62,"p0":350,"p1":425,"q0":776,"q1":815,"u0":436,"u1":772,"speed":0.5,"ramp":20}
  hero      satellite index followed (full-colour hero)
  az, el    camera direction from the hero, degrees (az 0 = from -y, positive toward +x; el above the horizontal)
  fov       horizontal fov of the close-up (deg); fill = fraction of the frame height the hero bbox occupies
  p0..p1    push-in window (ORIGINAL clip frames), q0..q1 ease-out window back to the unchanged fleet camera
  u0..u1    hero unfold interval (original frames); speed = playback speed factor in it (0.5 = half speed, 2x frame density)
  keys      [t364, opt-in] list of [orig_frame, az_deg, el_deg] keyframes: camera direction varies smoothly (smoothstep between keys); absent = fixed az/el as before
Output frame n maps to original (fractional) frame fo(n); frames before u0-ramp are identical to the unchanged clip."""
import os, json
import numpy as np
import fleet_kin_T45 as K
C = json.loads(os.environ["FLEET_HERO_CAM"])
HERO = int(C["hero"]); AZ = np.radians(C.get("az", 0.0)); EL = np.radians(C.get("el", 45.0)); FOV = float(C.get("fov", 40.0)); FILL = float(C.get("fill", 0.68))
P0, P1, Q0, Q1 = C.get("p0", 350.0), C.get("p1", 425.0), C.get("q0", 760.0), C.get("q1", 815.0)
U0, U1, SPD, RAMP = C.get("u0", 436.0), C.get("u1", 772.0), C.get("speed", 0.5), C.get("ramp", 20.0)
GROUP = [int(x) for x in C.get("group", [1, 2, 5, 6, 9, 11])]; GFILL = float(C.get("gfill", 0.80))   # end-of-clip fleet view: the sats the unchanged camera follows (left group)
ASPECT = float(os.environ.get("FLEET_HERO_ASPECT", str(9 / 16)))
_E = K._ease
# ---------------------------------------------------------------- retime (playback only)
def speed(fo):
    """playback speed (sim-time advance per output frame relative to the unchanged clip): 1 outside, SPD in [u0,u1], smooth ramps of RAMP frames just outside"""
    d = _E((fo - (U0 - RAMP)) / RAMP) - _E((fo - U1) / RAMP)
    return 1.0 - (1.0 - SPD) * d
_FG = np.arange(0.0, 816.0 + 1e-9, 0.25); _NG = np.concatenate([[0.0], np.cumsum(0.5 * (1.0 / np.array([speed(x) for x in _FG[1:]]) + 1.0 / np.array([speed(x) for x in _FG[:-1]])) * 0.25)])
N_TOTAL = int(np.floor(_NG[-1] + 1e-9)) + 1
def orig_frame(n): return min(float(np.interp(n, _NG, _FG)), 815.0)
def rate_label(fo): return K.sim_rate(fo / K.FPS) * speed(fo)       # sim seconds per OUTPUT clip second: truthful label under the retime
# ---------------------------------------------------------------- hero-fit camera
_FL = K.Fleet(); _OFF = np.array([[sx * 1.3, sy * 1.3, sz * 0.6] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
def _pts(T, sats=None):
    P = _FL.poses(T); np_, nq = K.NPAN_TOT, 2 * K.NLEAF * K.NSEC; Qs = []
    for h in ([HERO] if sats is None else sats):
        Qs.append(np.concatenate([P["panel_p"][h * np_:(h + 1) * np_], P["plate_p"][h * nq:(h + 1) * nq], P["bus_p"][h:h + 1], P["yoke_p"][2 * h:2 * h + 2], P["pod_p"][h:h + 1]]))
    return (np.concatenate(Qs)[:, None, :] + _OFF[None]).reshape(-1, 3)
DIR = np.array([np.sin(AZ) * np.cos(EL), -np.cos(AZ) * np.cos(EL), np.sin(EL)])
KEYS = C.get("keys")     # [t364] opt-in angled camera: [[fo, az, el], ...]
def _dir(fo):
    if not KEYS: return DIR
    ks = np.array(KEYS, float); fo = min(max(fo, ks[0, 0]), ks[-1, 0]); i = int(np.clip(np.searchsorted(ks[:, 0], fo, side="right") - 1, 0, len(ks) - 2))
    w = _E((fo - ks[i, 0]) / (ks[i + 1, 0] - ks[i, 0])); az, el = np.radians(ks[i, 1:] * (1 - w) + ks[i + 1, 1:] * w)
    return np.array([np.sin(az) * np.cos(el), -np.cos(az) * np.cos(el), np.sin(el)])
def _fit(Q, FILL=FILL, DIR=DIR):
    f = -DIR; r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f); tx = np.tan(np.radians(FOV) / 2); ty = tx * ASPECT
    c = 0.5 * (Q.min(0) + Q.max(0)); d = 60.0
    for _ in range(40):
        e = c + DIR * d; v = Q - e; z = v @ f; xn = (v @ r) / z / tx; yn = (v @ u) / z / ty
        mx, my = 0.5 * (xn.min() + xn.max()), 0.5 * (yn.min() + yn.max())
        c = c + r * (mx * tx * d) + u * (my * ty * d)          # centre the projected bbox
        e = c + DIR * d; v = Q - e; z = v @ f; xn = (v @ r) / z / tx; yn = (v @ u) / z / ty
        ext = max(0.5 * (xn.max() - xn.min()) / FILL, 0.5 * (yn.max() - yn.min()) / FILL)
        d *= ext ** 0.8 if ext > 0 else 1.0
        d = max(d, 4.0)
    return c, d
_GF = np.arange(300.0, 816.0 + 1e-9, 4.0); _G = []; _GG = []
for _f in _GF:
    _T = K.sim_time(_f / K.FPS); _D = _dir(_f); _c, _d = _fit(_pts(_T), FILL, _D); _G.append(np.concatenate([_c, [_d]])); _c, _d = _fit(_pts(_T, GROUP), GFILL, _D); _GG.append(np.concatenate([_c, [_d]]))
_G = np.array(_G); _GG = np.array(_GG)
SMW = int(C.get("sw", 1)); SMS = float(C.get("ss", 3.0))     # envelope half-window (grid steps of 4 frames) and gaussian sigma (original frames)
def _smooth(a, s=None, w=None):
    s = SMS if s is None else s; w = SMW if w is None else w
    from scipy.ndimage import maximum_filter1d, gaussian_filter1d
    out = a.copy(); out[:, 3] = maximum_filter1d(a[:, 3], size=2 * w + 1, mode="nearest")         # upper envelope: smoothing must not let the array outgrow the frame
    return gaussian_filter1d(out, sigma=s / 4.0, axis=0, mode="nearest")
_GS = _smooth(_G); _GGS = _smooth(_GG)
def _cam(tab, fo): g = np.array([np.interp(fo, _GF, tab[:, i]) for i in range(4)]); return g[:3] + _dir(fo) * g[3], g[:3], FOV
def fit_camera(fo): return _cam(_GS, fo)
def camera(fo, FL=None, T=None):
    """push-in (p0..p1) from the unchanged camera to the hero close-up; hero close-up through the unfold; ease-out (q0..q1) to a fit of the whole left group (hero stays inside the frame)"""
    base = K.camera(fo / K.FPS, FL, T)
    w = _E((fo - P0) / (P1 - P0))
    if w <= 0.0: return base
    e, t, fv = _cam(_GS, fo); e = base[0] * (1 - w) + e * w; t = base[1] * (1 - w) + t * w; fv = base[2] * (1 - w) + fv * w
    v = _E((fo - Q0) / (Q1 - Q0))
    if v > 0.0:
        e2, t2, f2 = _cam(_GGS, fo); e = e * (1 - v) + e2 * v; t = t * (1 - v) + t2 * v; fv = fv * (1 - v) + f2 * v
    return e, t, fv
