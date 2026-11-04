"""[t460] Indexed PEZ release for Render 1 (Aug, 30 sats).  KINEMATICS ONLY (no contact solve).
Installed into the overlay fleet_kin_T45 module (patch_pez.py) and active ONLY when env FLEET_PEZ=1.
World frame: the ship is a horizontal cylinder along world X, belly to Earth (-Z), slot on top (+Z, leeward).
  pack (x lateral, y exit normal, z bay axis)  ->  world (X=z_p - zoff, Y=x_p, Z=y_p), M=[[0,0,1],[1,0,0],[0,1,0]] (det +1).
Sequence: layers are indexed to the slot plane one at a time (slot is fixed, the stack moves), each satellite shuttles
laterally to the slot centre (only the 2nd of a 2-across layer; the 1st exits in place, the 3-across layer exits sides first, centre last),
is pushed out edge-first along +Z (hull normal) at V_PUSH with no tumble, coasts, then acquires its unfold attitude and unfolds (unchanged act).
[t483] V_PUSH default 2.0 m/s (was 0.40): INFERENCE from the Flight 14 clip, see README section 8 (apparent 1-4.7 m/s, chosen 2.0).  ATT_DELAY 15 -> 6 s (the sat is 12 m clear after 6 s at 2 m/s).
All numbers below are ASSUMED unless labelled (GAP, V_PUSH, SHUTTLE_S, INDEX_S ... knobs via env FLEET_PEZ_*)."""
import math, os
import numpy as np

# ---- slot / hull geometry (3RD: slot width 7.3 m public figure; heights ASSUMED = tallest layer + 2 x 0.10 m clearance)
HULL_R = 4.5; BAY_R = 4.0; SLOT_W = 7.3; SLOT_H = 1.80; CLEAR_Y = 4.65     # CLEAR_Y: trailing edge must pass this pack-y (hull outer r 4.5 + 0.15) before it is "clear"
ENV_Y = 4.10                                                              # pack-y of the trailing edge at which the stack may index
M = np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0]])

def _ef(k, d): return float(os.environ.get("FLEET_PEZ_" + k, d))
GAP = _ef("GAP", 36.0); V_PUSH = _ef("VPUSH", 2.0); T_RAMP = _ef("RAMP", 0.0); SHUTTLE_S = _ef("SHUTTLE", 6.0); SHUTTLE_ON = _ef("SHUTTLE_ON", 0.0) > 0.5; INDEX_S = _ef("INDEX", 6.0)
ATT_DELAY = _ef("ATT_DELAY", 6.0); ATT_DUR = _ef("ATT_DUR", 120.0); UNFOLD_WAIT = _ef("UNFOLD_WAIT", 10.0); UNFOLD_S = _ef("UNFOLD_S", 160.0)
FAN = _ef("FAN", 0.0)
# [t460, "delete first" review] DEFAULTS NOW: no lateral shuttle (SHUTTLE_ON=0), no velocity ramp (RAMP=0), no fan drift (FAN=0).  The shuttle is not needed: both sats of a 2-across layer already fit the 7.3 m slot in place
# (lateral reach 3.13 m vs 3.65 m half-width).  The v1 variant (shuttle, 2 s ramp, FAN 0.02) = FLEET_PEZ_SHUTTLE_ON=1 FLEET_PEZ_RAMP=2 FLEET_PEZ_FAN=0.02 (file pez_release.py.v1_shuttle_t460).

def pushdist(t):
    """distance travelled after push start: min-jerk velocity ramp over T_RAMP to V_PUSH, then constant"""
    t = max(t, 0.0)
    if T_RAMP <= 0: return V_PUSH * t
    if t < T_RAMP: u = t / T_RAMP; return V_PUSH * T_RAMP * (2.5 * u**4 - 3 * u**5 + u**6)
    return V_PUSH * T_RAMP * 0.5 + V_PUSH * (t - T_RAMP)
def push_time(D):
    D = max(D, 0.0)
    if T_RAMP <= 0: return D / V_PUSH
    if D <= 0.5 * V_PUSH * T_RAMP:       # inside the ramp: bisect
        lo, hi = 0.0, T_RAMP
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if pushdist(mid) < D: lo = mid
            else: hi = mid
        return hi
    return D / V_PUSH + 0.5 * T_RAMP

def install(G):
    """G = module globals of fleet_kin_T45 (called just before _FL = Fleet())"""
    Fleet = G["Fleet"]; minjerk = G["minjerk"]; rotvec_to_R = G["rotvec_to_R"]; R_to_rotvec = G["R_to_rotvec"]; K_boxes = G["boxes_aabb"]
    NP, NQ = G["NPAN_TOT"], 2 * G["NLEAF"] * G["NSEC"]
    # ---- stowed AABB per satellite in the pack frame (needed for the clear distance and the layer centres)
    f0 = Fleet(); n = f0.n; P = f0.poses(0.0)
    lo = np.full((n, 3), 1e9); hi = np.full((n, 3), -1e9)
    for nm, box, cen, m in (("panel", G["PANEL_BOX"], False, NP), ("plate", G["PLATE_BOX"], True, NQ)):
        l, h = K_boxes(P[nm + "_p"], P[nm + "_R"], box, cen)
        for i in range(n): lo[i] = np.minimum(lo[i], l[i * m:(i + 1) * m].min(0)); hi[i] = np.maximum(hi[i], h[i * m:(i + 1) * m].max(0))
    l, h = K_boxes(P["bus_p"], P["bus_R"], G["BUS"], True); lo = np.minimum(lo, l); hi = np.maximum(hi, h)
    sats = f0.sats; layers = sorted(set(s.layer for s in sats))
    zc = {k: 0.5 * (min(lo[i, 2] for i in range(n) if sats[i].layer == k) + max(hi[i, 2] for i in range(n) if sats[i].layer == k)) for k in layers}
    layer_h = {k: max(hi[i, 2] for i in range(n) if sats[i].layer == k) - min(lo[i, 2] for i in range(n) if sats[i].layer == k) for k in layers}
    # ---- exit order: layers bottom-up; inside a layer +x first, centre sat last (shuttles to the slot centre if it is the 2nd of 2)
    order = []
    for k in layers:
        idx = [i for i in range(n) if sats[i].layer == k]
        idx.sort(key=lambda i: (abs(sats[i].p0[0]) < 0.5, -sats[i].p0[0])); order += idx
    # ---- per-sat schedule
    info = {}
    for e, i in enumerate(order):
        sa = sats[i]; k = sa.layer; in_layer = [j for j in order if sats[j].layer == k]; pos_in = in_layer.index(i)
        shuttle = SHUTTLE_ON and (len(in_layer) == 2 and pos_in == 1)
        x0 = float(sa.p0[0]); x_exit = 0.0 if shuttle else x0
        Te = GAP * e; Tp0 = Te + (SHUTTLE_S if shuttle else 0.0)
        lo_y = float(lo[i, 1] - sa.p0[1]); y0 = float(sa.p0[1])
        D_clear = CLEAR_Y - lo_y - y0; D_env = ENV_Y - lo_y - y0
        info[i] = dict(e=e, shuttle=shuttle, x0=x0, x_exit=x_exit, Te=Te, Tp0=Tp0, y0=y0, Tclear=Tp0 + push_time(D_clear), Tenv=Tp0 + push_time(D_env), D_clear=D_clear,
                       lo_y=lo_y, ext_x=(float(lo[i, 0] - x0), float(hi[i, 0] - x0)), ext_z=(float(lo[i, 2] - sa.p0[2]), float(hi[i, 2] - sa.p0[2])))
        info[i]["Tatt0"] = info[i]["Tclear"] + ATT_DELAY; info[i]["Tatt1"] = info[i]["Tatt0"] + ATT_DUR
        # deterministic fan (ASSUMED): small world-X / world-Y drift velocities after clearing
        info[i]["vX"] = FAN * math.sin(1.7 * e + 0.6); info[i]["vY"] = FAN * math.cos(2.3 * e + 0.2)
    # ---- indexing: after the last sat of a layer has its trailing edge past ENV_Y the stack steps to the next layer centre
    idx_t = {}
    for a, b in zip(layers[:-1], layers[1:]):
        last = [j for j in order if sats[j].layer == a][-1]; t0 = info[last]["Tenv"]; idx_t[a] = (t0, t0 + INDEX_S)
        first_next = [j for j in order if sats[j].layer == b][0]
        assert t0 + INDEX_S <= info[first_next]["Te"] + 1e-6, ("index overruns next event", a, t0, info[first_next]["Te"])
    # stack offset at a time is a cumulative sum; recompute robustly
    def zoff(T):
        z = zc[layers[0]]
        for a, b in zip(layers[:-1], layers[1:]):
            t0, t1 = idx_t[a]; z += (zc[b] - zc[a]) * float(minjerk((T - t0) / (t1 - t0)))
        return z
    T_last_clear = max(v["Tclear"] for v in info.values()); T_last_att = max(v["Tatt1"] for v in info.values())
    T_U0n = max(GAP * (n - 1) + 0.0, T_last_att) + UNFOLD_WAIT; T_ENDn = T_U0n + UNFOLD_S
    G["PEZ_INFO"] = info; G["PEZ_ORDER"] = order; G["PEZ_IDX"] = idx_t; G["PEZ_ZC"] = zc
    G["T_U0"] = T_U0n; G["T_END_SIM"] = T_ENDn
    # ---- patched Fleet
    _init = Fleet.__init__
    def __init__(self):
        _init(self)
        for sa in self.sats:
            f = info[sa.idx]; sa.sgx = 1.0; sa.vx = V_PUSH; sa.Trel = f["Te"]; sa.Tex = f["Tclear"]; sa.vy = f["vY"]; sa.vz = f["vX"]
            sa.pez = f; sa.rv_w = R_to_rotvec(M @ rotvec_to_R(sa.rv_p))
    Fleet.__init__ = __init__
    def centre(self, sa, T):
        f = sa.pez; sm = float(minjerk((T - f["Te"]) / SHUTTLE_S)) if f["shuttle"] else 0.0
        xp = f["x0"] + (f["x_exit"] - f["x0"]) * sm
        yp = f["y0"] + pushdist(T - f["Tp0"])
        tc = max(T - f["Tclear"], 0.0)
        zo = zoff(min(T, f["Te"])) if True else 0.0
        return np.array([float(sa.p0[2]) - zo + f["vX"] * tc, xp + f["vY"] * tc, yp])       # world (X, Y, Z)
    def Rsat(self, sa, T):
        f = sa.pez; s = float(minjerk((T - f["Tatt0"]) / (f["Tatt1"] - f["Tatt0"]))); return rotvec_to_R((1 - s) * sa.rv_w)
    Fleet.centre = centre; Fleet.Rsat = Rsat
    # ---- time map (clip s -> sim s): 960 frames @24 fps, release 0-20 s (per-event cells), coast, unfold 20-40 s at the unchanged 160 s sim window
    G["CLIP_S"] = 40.0
    # [t483] per-event clip allocation.  Sat 0 is shown in REAL TIME while it is pushed clear (4.5 s sim = 4.5 s clip), sats 1 and 2 are slowed around their layer-index steps
    # (x5 and x8 over 10 s sim), all later cells are 0.35 s clip per 36 s sim.  Each entry = list of (sim seconds, clip seconds) pieces that add up to GAP sim seconds.
    def _cell(e):
        if e == 0: return [(4.5, 4.5), (GAP - 4.5, 0.8)]
        if e == 1: return [(10.0, 2.0), (GAP - 10.0, 0.4)]
        if e == 2: return [(10.0, 1.0), (GAP - 10.0, 0.3)]
        return [(GAP, 0.35)]
    knots_c = [0.0]; knots_s = [0.0]
    for e in range(n):
        for ds, dc in _cell(e): knots_c.append(knots_c[-1] + dc); knots_s.append(knots_s[-1] + ds)
    assert knots_c[-1] < 19.5, knots_c[-1]
    knots_c.append(20.0); knots_s.append(T_U0n)
    knots_c.append(40.0); knots_s.append(T_ENDn)
    G["PEZ_KNOTS"] = (knots_c, knots_s)
    G["time_label"] = lambda T: (lambda t: f"T+{int(t // 60):02d}:{int(t % 60):02d}")(max(float(T), 0.0) + 1e-6)     # [t483] T = -1e-14 at frame 0 printed "T+-1:59"
    def _tables():
        dt = 1.0 / 240; t = np.arange(0, 40.0 + dt / 2, dt); T = np.interp(t, knots_c, knots_s)
        k = int(round(0.25 / dt)); s0 = (T[1] - T[0]) / dt; s1 = (T[-1] - T[-2]) / dt; pad = np.concatenate([T[0] - s0 * dt * np.arange(k, 0, -1), T, T[-1] + s1 * dt * np.arange(1, k + 1)])   # linear extension at both ends (no edge flattening)      # smooth the sim time (kernel 0.25 s) so rate changes are not abrupt
        Ts = np.convolve(pad, np.ones(k) / k, mode="same")[k:-k]; Ts = np.maximum.accumulate(Ts)
        return t, Ts, np.gradient(Ts, t)
    G["_tables"] = _tables; G["_TT"], G["_TS"], G["_TR"] = _tables()
    G["_SEG"] = [(knots_c[0], 20.0, 0.0, T_U0n), (20.0, 40.0, T_U0n, T_ENDn)]
    return info
