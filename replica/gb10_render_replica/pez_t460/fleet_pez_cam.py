"""[t483] CHASE camera for the indexed-PEZ Render 1 (module interface = fleet_fit_cam_replica: HERO, N_TOTAL, camera(fo,FL,T), orig_frame, rate_label, speed; plus up(fo)).
Replaces the t460 slot-camera -> whole-fleet-fit camera (the column is now ~2 km long at the 2 m/s push, so the whole fleet cannot be framed).
The camera frames a GROUP of the 2 most recently released satellites while sats are leaving (the one in the slot and the one before it), then the final 3 (27, 28, 29) from the last release on (before that many have flown: those that exist).
 - Slot phase (f < B0): the slot window and a +-8 m patch of hull are kept in the fit, so the viewer sees the indexing step and each sat leave the slot.
 - Slot hand-over (B0..B1): the slot points are faded out of the fit (smoothstep) and the 90 deg roll starts so the column lies along the long side of the 16:9 frame.
 - Chase (f > B1): the fit follows the group only.  After the last event the group is the final three sats (27, 28, 29) and stays that group through the unfold window (unchanged 160 s sim window).
 - Direction: blends from the slot view direction to the unchanged repo final view direction (from -y, ~19 deg elevation).
The fit is tabulated every 4 frames and smoothed; a safe-box guard keeps every group sat inside the frame.  Editorial parameters = ASSUMED.
env FLEET_PEZ_CAM = JSON {"b0":..,"b1":..,"fov":..,"fill":..,"roll":1,"n":3,"n_release":2}."""
import os, json
import numpy as np
import fleet_kin_T45 as K
C = json.loads(os.environ.get("FLEET_PEZ_CAM") or "{}")
FOV = float(C.get("fov", 40.0)); FILL = float(C.get("fill", 0.80)); B0 = float(C.get("b0", 200.0)); B1 = float(C.get("b1", 330.0)); A_END = float(C.get("dir_end_f", 520.0)); ROLL = float(C.get("roll", 1.0)); NG = int(C.get("n", 3)); NR = int(C.get("n_release", 2))
N_TOTAL = int(round(K.CLIP_S * K.FPS)); HERO = K.HERO; ASPECT = float(os.environ.get("FLEET_HERO_ASPECT", str(9 / 16)))
_FL = K.Fleet(); _E = K._ease; _ORD = list(K.PEZ_ORDER); _TE = [K.PEZ_INFO[i]["Te"] for i in _ORD]
def speed(fo): return 1.0
def orig_frame(n): return min(float(n), N_TOTAL - 1.0)
def rate_label(fo): return K.sim_rate(fo / K.FPS)
def group(T):
    rel = [i for i, te in zip(_ORD, _TE) if te <= T + 1e-6] or _ORD[:1]
    return rel[-(NG if T >= _TE[-1] - 1e-6 else NR):]      # 2 sats while sats are still leaving the slot, the final 3 (27, 28, 29) once the last one is out
UP0 = np.array([0.0, 0.0, 1.0]); UP1 = np.array([-1.0, 0.0, 0.0])
def _w(fo): return _E((fo - B0) / (B1 - B0))
def up(fo):
    w = _w(fo) * ROLL; v = UP0 * (1 - w) + UP1 * w; return v / np.linalg.norm(v)
_OFF = np.array([[sx * 1.3, sy * 1.3, sz * 0.6] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
_SLOT = np.array([[sx, sy, 0.0] for sx in (-4.0, 4.0) for sy in (-4.0, 4.0)] + [[sx, sy, 0.0] for sx in (-0.9, 0.9) for sy in (-3.65, 3.65)] + [[0.0, 0.0, -3.0]])   # slot window (7.3 x 1.8 m) + hull patch
def _pts(T, sats):
    P = _FL.poses(T); np_, nq = K.NPAN_TOT, 2 * K.NLEAF * K.NSEC; Qs = []
    for h in sats:
        Qs.append(np.concatenate([P["panel_p"][h * np_:(h + 1) * np_], P["plate_p"][h * nq:(h + 1) * nq], P["bus_p"][h:h + 1], P["yoke_p"][2 * h:2 * h + 2][np.abs(P["yoke_p"][2 * h:2 * h + 2]).max(1) < 1.0e4], P["pod_p"][h:h + 1]]))      # hidden (stowed) yokes sit ~1e4 m away: not part of the framing
    return (np.concatenate(Qs)[:, None, :] + _OFF[None]).reshape(-1, 3)
_SD = np.array([-0.80, -0.30, 0.34]); _SD = _SD / np.linalg.norm(_SD)         # slot-phase view direction (aft / side / above)
_B1 = np.array([260.0, -820.0, 300.0]); _D1 = _B1 / np.linalg.norm(_B1)       # unchanged repo final view direction (from -y, ~19 deg elevation)
def _dir(fo):
    w = _E(fo / A_END); d = _SD * (1 - w) + _D1 * w; return d / np.linalg.norm(d)
def _basis(D, upv):
    f = -D; r = np.cross(f, upv); r /= np.linalg.norm(r); u = np.cross(r, f); return f, r, u
def _fit(Q, D, upv, dmin=4.0):
    f, r, u = _basis(D, upv); tx = np.tan(np.radians(FOV) / 2); ty = tx * ASPECT
    c = 0.5 * (Q.min(0) + Q.max(0)); d = 60.0
    for _ in range(80):
        e = c + D * d; v = Q - e; z = v @ f; xn = (v @ r) / z / tx; yn = (v @ u) / z / ty
        c = c + r * (0.5 * (xn.min() + xn.max()) * tx * d) + u * (0.5 * (yn.min() + yn.max()) * ty * d)
        e = c + D * d; v = Q - e; z = v @ f; xn = (v @ r) / z / tx; yn = (v @ u) / z / ty
        ext = max(0.5 * (xn.max() - xn.min()) / FILL, 0.5 * (yn.max() - yn.min()) / FILL); d = max(d * (ext ** 0.8 if ext > 0 else 1.0), dmin)
    return c, d
def _inbox(Q, e, t, upv):
    fwd = t - e; fwd = fwd / np.linalg.norm(fwd); r = np.cross(fwd, upv); r /= np.linalg.norm(r); u = np.cross(r, fwd); v = Q - e; z = v @ fwd
    if (z <= 0.1).any(): return False
    fpx = 0.5 * 960 / np.tan(np.radians(FOV) / 2); X = 480 + fpx * (v @ r) / z; Y = 270 - fpx * (v @ u) / z
    return bool((X >= 12).all() and (X <= 948).all() and (Y >= 62).all() and (Y <= 503).all())
_GF = np.arange(0.0, N_TOTAL, 4.0); _GF = np.append(_GF, N_TOTAL - 1.0); _TAB = []
for _f in _GF:
    _T = K.sim_time(_f / K.FPS); _upv = up(_f); _D = _dir(_f); _Q = _pts(_T, group(_T)); _ss = 1.0 - _w(_f)
    _c1, _d1 = _fit(_Q, _D, _upv)
    if _ss > 1e-6:
        _c0, _d0 = _fit(np.concatenate([_Q, _SLOT]), _D, _upv, dmin=14.0); _c = _c0 * _ss + _c1 * (1 - _ss); _dd = _d0 * _ss + _d1 * (1 - _ss)
    else: _c, _dd = _c1, _d1
    _k = 1.0
    while not _inbox(_Q, _c + _D * _dd * _k, _c, _upv) and _k < 4.0: _k *= 1.02
    _TAB.append((_c, _dd, _k))
_C = np.array([x[0] for x in _TAB]); _DD = np.array([x[1] for x in _TAB]); _KK = np.array([x[2] for x in _TAB])
from scipy.ndimage import maximum_filter1d, gaussian_filter1d
_SG = 2.5      # smoothing sigma in table steps (= 10 frames = 1/3 s): removes the event-to-event group-switch ripple
_KS = np.maximum(gaussian_filter1d(maximum_filter1d(_KK, size=9, mode="nearest"), sigma=2.0, mode="nearest"), _KK)
_DS = gaussian_filter1d(_DD, sigma=_SG, mode="nearest"); _CS = gaussian_filter1d(_C, sigma=_SG, axis=0, mode="nearest")
def camera(fo, FL=None, T=None):
    c = np.array([np.interp(fo, _GF, _CS[:, i]) for i in range(3)]); d = float(np.interp(fo, _GF, _DS)); k = float(np.interp(fo, _GF, _KS))
    D = _dir(fo); e = c + D * d * k
    return e, c, FOV
