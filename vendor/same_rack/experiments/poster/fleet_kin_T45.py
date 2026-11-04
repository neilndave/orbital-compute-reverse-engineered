"""Fleet deploy clip kinematics (Nov 1 2026, []). numpy only (importable inside Kit).
poses(T) gives, for sim time T since the first release, the world pose of every rigid body of the 14 satellites (229-panel O5 design, 2 x 3.5 m-half array wings per satellite).
LABELS: stowed packing = ESTIMATE (skyline packer of the stowing study, geometry only); the thick (10-panel) radiator stacks on 13 columns = ESTIMATE (balanced 7/6 over the wings); release speed, stagger, extra drift velocities, attitude
acquisition and unfold timing = ASSUMED (see docs/FLEET_DEPLOY_RENDER_T45.md); array accordion angles = Newton 1.7.0 Featherstone solve (spring-mode chain, results/phase2_T45); radiator fold, array width fold, rigid staging and
release = kinematic / analytic (NOT a contact solve). Dispenser rails, deck and ship are a schematic (ASSUMED), not a Starship model. Trunk manifolds and harnesses are not drawn."""
import json, math, os, pathlib
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[2]
F = ROOT / "results/fleet"
LAY = json.load(open(F / "fleet_layout_T45.json")); PK = json.load(open(ROOT / os.environ["FLEET_PACK"] if os.environ.get("FLEET_PACK") else F / "fleet_pack_T45.json"))      # [t337] FLEET_PACK=<json relative to the repo root> = the 13-satellite A6L pack with the component pod
# [t310u options, all default OFF = the original v1 clip]: FLEET_SYNC=1 cable-synchronised accordion (fleet_sync_chain_T45.py) instead of the free-spring Newton replay; FLEET_YOKE=1 real 4.1366 m yoke link (drawn as a boom) instead of the 0.25 m stub;
# FLEET_TAU_N0=<s> start of the accordion; FLEET_TAU_W0=<s> start of the array width fold; FLEET_LIFT=<m> lift-off excursion of each staged group (sideways, away from the bus, sin(pi s) profile); FLEET_DECKFIX=1 clamp the ASSUMED downward z-drift of deck-level satellites while they are still over the deck disc
SYNC = os.environ.get("FLEET_SYNC", "0") == "1"; YOKE = os.environ.get("FLEET_YOKE", "0") == "1"; DECKFIX = os.environ.get("FLEET_DECKFIX", "0") == "1"; LIFT = float(os.environ.get("FLEET_LIFT", "0"))
# [t316u options, default OFF = t310u v2]: FLEET_STUBTRIM=<mm> render the hinge-pin stubs of the radiator panels at most this long (they were drawn 30 mm, longer than the 4 mm column gap; mesh pins poked ~26 mm into the neighbouring
# column's end header); FLEET_STAGEPLAN=<json> collision-planned staging (fleet_stage_plan_T45.py) instead of the straight-line lerp, yokes shown from frame 0 in a stowed pose; FLEET_TEND=<s> sim time at the end of the clip (default 1345); FLEET_RADGAP=<s> pause between a column
# being staged and its fold start.
STUBTRIM = float(os.environ.get("FLEET_STUBTRIM", "0")); PLAN_PATH = os.environ.get("FLEET_STAGEPLAN", ""); PLAN = json.load(open(PLAN_PATH)) if PLAN_PATH else None
def trim_stub_V(V):
    """V: (n,3) stub vertices in mm. pins (x<0 or x>W) shortened to STUBTRIM mm; attach points at x=0 / x=W unchanged"""
    if STUBTRIM <= 0: return V
    V = np.array(V, float); Wm = LAY["panel_W_mm"]; f = STUBTRIM / 30.0; m = V[:, 0] < 0; V[m, 0] *= f; m = V[:, 0] > Wm; V[m, 0] = Wm + (V[m, 0] - Wm) * f; return V
_nd = np.load(F / ("newton_chain_dense_sync_T45.npz" if SYNC else "newton_chain_dense_T45.npz")); NT = _nd["t"].astype(float); NH = _nd["h"].astype(float)
mm = 1e-3
W = LAY["panel_W_mm"] * mm * float(os.environ.get("FLEET_WSCALE", "1.0")); L = LAY["panel_L_mm"] * mm * float(os.environ.get("FLEET_LSCALE", "1.0")); GAP = LAY["gap_mm"] * mm; PL = L + GAP; PW = W + GAP
ACROSS = LAY["across"]; EXTRA_P = int(os.environ.get("FLEET_ALONG_EXTRA", "0")); ALONG = LAY["along"] + EXTRA_P; # [t359] FLEET_ALONG_EXTRA=1: every radiator column carries one more panel (253-panel layouts, 11 / 10 per column); default 0 unchanged
XX=0; Y0 = LAY["y0_mm"] * mm; Z_LO = LAY["z_lo_mm"] * mm if os.environ.get("FLEET_WSCALE", "1.0") == "1.0" else -0.5 * (ACROSS * W + (ACROSS - 1) * GAP)   # [t337] re-centred when panels are widened
Z_ARR = LAY["z_arr_mm"] * mm; BUS = np.array(LAY["bus_mm"]) * mm; LEAF = LAY["leaf_len_mm"] * mm; NLEAF = LAY["leaves"]; ARRW = LAY["array_width_mm"] * mm
NSEC = 4; SECW = ARRW / NSEC; ROOT_OFF = 0.25; ROOT_X = 0.50 if YOKE else 0.0; TH_ARR = LAY["array_thick_mm"] * mm; P_ARR = 0.009; P_RAD = 0.1633 / 9.0
YOKE_TOTAL = json.load(open(ROOT / "results/phase2_T45/chain_params_T45.json"))["LEN"][0]      # 4.1366 m, root arm from the bus axis (DERISK_PHASE2_T45.md 4.2)
YOKE_DX = float(os.environ.get("FLEET_YOKE_DX", "0")); YOKE_T = float(os.environ.get("FLEET_YOKE_T", "0.10"))      # [t316u] boom shifted DX m in the wing-frame -x direction (away from the folded array stack, which grows toward +x) and section thickness (visual only)
YOKE_L = YOKE_TOTAL - ROOT_X; YOKE_BOX = np.array([YOKE_L, 0.25, YOKE_T])      # drawn boom: ASSUMED 0.25 x 0.10 m section (visual only)
PANEL_BOX = np.array([W, L, 0.014])      # local box [0,W]x[0,L]x[-.007,.007] (sheet envelope used for clearance)
PLATE_BOX = np.array([LEAF, SECW, TH_ARR])
# which 13 columns carry 10 panels (balanced 7 on wing 0 at cols below, 6 on wing 1)  -- ESTIMATE
THICK = {0: [0, 2, 4, 6, 7, 9, 11], 1: [0, 2, 4, 7, 9, 11]}
# [t337] FLEET_LAYOUT selects a z-symmetric panel layout (default "" = the t316 ragged 7/6 layout, kept for the record): A6 = 10-panel columns {2,3,4 | 7,8,9} per wing (centre-weighted), A8 = {1..4 | 7..10}... see docs/DESIGN_FIXES_T45.md section 9
_SPEC = {"S253": {0: [2, 3, 4, 5, 6, 7, 8], 1: [3, 4, 5, 6, 7, 8]}, "S254A": {0: [2, 3, 4, 5, 6, 7, 8], 1: [2, 3, 4, 5, 6, 7, 8]}, "B12A": {0: [3, 4, 5, 6, 7, 8], 1: [3, 4, 5, 6, 7, 8]}}   # [t359] 11-panel (thick) columns of the 253 / 254 / 252-panel layouts (A6L centre bump kept; S253 adds one 11th-panel column on wing 0)
_SYM = {"A6": [3, 4, 5, 6, 7, 8], "A8": [2, 3, 4, 5, 6, 7, 8, 9], "A24": list(range(12)), "A0": []}
LAYOUT = os.environ.get("FLEET_LAYOUT", "")
if LAYOUT in _SYM: THICK = {0: list(_SYM[LAYOUT]), 1: list(_SYM[LAYOUT])}
if LAYOUT in _SPEC: THICK = {0: list(_SPEC[LAYOUT][0]), 1: list(_SPEC[LAYOUT][1])}   # [t359]
WSCALE = float(os.environ.get("FLEET_WSCALE", "1.0")); LSCALE = float(os.environ.get("FLEET_LSCALE", "1.0"))   # [t337] candidate B: panel width / length scale (default 1.0)
NPAN = {(w, c): ALONG + (1 if c in THICK[w] else 0) for w in (0, 1) for c in range(ACROSS)}
NPAN_TOT = sum(NPAN.values())
# ----------------------------------------------------------------------------- math helpers
def Rx(a): c, s = np.cos(a), np.sin(a); z, o = np.zeros_like(c), np.ones_like(c); return np.stack([np.stack([o, z, z], -1), np.stack([z, c, -s], -1), np.stack([z, s, c], -1)], -2)
def Ry(a): c, s = np.cos(a), np.sin(a); z, o = np.zeros_like(c), np.ones_like(c); return np.stack([np.stack([c, z, s], -1), np.stack([z, o, z], -1), np.stack([-s, z, c], -1)], -2)
def Rz(a): c, s = np.cos(a), np.sin(a); z, o = np.zeros_like(c), np.ones_like(c); return np.stack([np.stack([c, -s, z], -1), np.stack([s, c, z], -1), np.stack([z, z, o], -1)], -2)
def rotvec_to_R(v):
    v = np.asarray(v, float); th = np.linalg.norm(v)
    if th < 1e-12: return np.eye(3)
    k = v / th; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]); return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K
def R_to_rotvec(R):
    c = (np.trace(R) - 1) / 2; th = math.acos(max(-1, min(1, c)))
    if th < 1e-9: return np.zeros(3)
    if abs(th - math.pi) < 1e-6:
        w, V = np.linalg.eigh((R + np.eye(3)) / 2); k = V[:, -1]; return k * th
    k = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * math.sin(th)); return k * th
def minjerk(x): x = np.clip(x, 0, 1); return x**3 * (10 - 15 * x + 6 * x * x)

RADGAP = float(os.environ.get("FLEET_RADGAP", "0.5"))       # [t316u] s between a column reaching its staged pose and the start of its fold-out
def _plan_prep():
    if PLAN is None: return
    for sk, sv in PLAN.items():
        for b in sv["bodies"]:
            b["_w"] = [(np.array(c, float), np.array(r, float)) for c, r in b["wps"]]
_plan_prep_done = False
def planpose(sat, bi, tau):
    """[t316u] pose (Cc, rotvec) of staging body bi (0..23 radiator columns in n_cols order, 24/25 array stacks, 26/27 yokes) of satellite sat at unfold time tau; min-jerk stop-and-go along the planned waypoints"""
    b = PLAN[str(sat)]["bodies"][bi]; w = b["_w"]; t = tau - b["t0"]
    if t <= 0: return w[0]
    for (c0, r0), (c1, r1), d in zip(w[:-1], w[1:], b["durs"]):
        if t <= d: u = float(minjerk(t / d)); return c0 * (1 - u) + c1 * u, r0 * (1 - u) + r1 * u
        t -= d
    return w[-1]
def plan_ready(sat, bi): return PLAN[str(sat)]["bodies"][bi]["t1"]
_plan_prep()
def R_to_quat_wxyz(R):
    R = np.asarray(R); n = R.shape[:-2]; out = np.zeros(n + (4,)); tr = R[..., 0, 0] + R[..., 1, 1] + R[..., 2, 2]
    q = np.zeros(n + (4,))
    a = tr > 0; s = np.sqrt(np.maximum(tr + 1, 1e-30)) * 2
    q[..., 0] = np.where(a, 0.25 * s, 0); q[..., 1] = np.where(a, (R[..., 2, 1] - R[..., 1, 2]) / s, 0); q[..., 2] = np.where(a, (R[..., 0, 2] - R[..., 2, 0]) / s, 0); q[..., 3] = np.where(a, (R[..., 1, 0] - R[..., 0, 1]) / s, 0)
    b = (~a) & (R[..., 0, 0] >= R[..., 1, 1]) & (R[..., 0, 0] >= R[..., 2, 2]); s = np.sqrt(np.maximum(1 + R[..., 0, 0] - R[..., 1, 1] - R[..., 2, 2], 1e-30)) * 2
    q[..., 0] = np.where(b, (R[..., 2, 1] - R[..., 1, 2]) / s, q[..., 0]); q[..., 1] = np.where(b, 0.25 * s, q[..., 1]); q[..., 2] = np.where(b, (R[..., 0, 1] + R[..., 1, 0]) / s, q[..., 2]); q[..., 3] = np.where(b, (R[..., 0, 2] + R[..., 2, 0]) / s, q[..., 3])
    c = (~a) & (~b) & (R[..., 1, 1] >= R[..., 2, 2]); s = np.sqrt(np.maximum(1 + R[..., 1, 1] - R[..., 0, 0] - R[..., 2, 2], 1e-30)) * 2
    q[..., 0] = np.where(c, (R[..., 0, 2] - R[..., 2, 0]) / s, q[..., 0]); q[..., 1] = np.where(c, (R[..., 0, 1] + R[..., 1, 0]) / s, q[..., 1]); q[..., 2] = np.where(c, 0.25 * s, q[..., 2]); q[..., 3] = np.where(c, (R[..., 1, 2] + R[..., 2, 1]) / s, q[..., 3])
    d = (~a) & (~b) & (~c); s = np.sqrt(np.maximum(1 + R[..., 2, 2] - R[..., 0, 0] - R[..., 1, 1], 1e-30)) * 2
    q[..., 0] = np.where(d, (R[..., 1, 0] - R[..., 0, 1]) / s, q[..., 0]); q[..., 1] = np.where(d, (R[..., 0, 2] + R[..., 2, 0]) / s, q[..., 1]); q[..., 2] = np.where(d, (R[..., 1, 2] + R[..., 2, 1]) / s, q[..., 2]); q[..., 3] = np.where(d, 0.25 * s, q[..., 3])
    return q / np.linalg.norm(q, axis=-1, keepdims=True)
# ----------------------------------------------------------------------------- deployed-frame chains (canonical wing +; wing - = Rz(pi) of it)
RW = Ry(np.float64(-math.pi / 2))
def rad_chain(col, phi, n_max=ALONG + 1):
    """col: (nc,) z-column index, phi: (nc,) fold angle (pi folded .. 0 deployed), returns pos (nc,n_max,3), R (nc,n_max,3,3) panel local-origin pose in wing + frame (panel k>=nP unused)"""
    nc = len(col); k = np.arange(n_max)
    alpha = np.where(k[None, :] % 2 == 1, -phi[:, None], 0.0)                                     # (nc, n_max)
    ca, sa = np.cos(alpha), np.sin(alpha)
    # O_{k+1} = O_k + Rz(alpha_k) (0, PL, 0) = O_k + PL(-sin a_k, cos a_k)
    stepx = np.concatenate([np.zeros((nc, 1)), -PL * sa[:, :-1]], 1); stepy = np.concatenate([np.zeros((nc, 1)), PL * ca[:, :-1]], 1)
    X = np.cumsum(stepx, 1); Y = Y0 + np.cumsum(stepy, 1)
    X = X + (k[None, :] * P_RAD * (phi[:, None] / math.pi))
    Z = (Z_LO + col * PW)[:, None] * np.ones((1, n_max))
    pos = np.stack([X, Y, Z], -1)
    R = np.einsum("ckij,jl->ckil", Rz(alpha), RW)
    return pos, R
def arr_chain(h, a):
    """h (21,) Newton hinge angles, a width-fold angle (pi folded .. 0). returns pos (NLEAF,NSEC,3), R (NLEAF,NSEC,3,3) of plate CENTRES in wing + frame"""
    if YOKE: h = -h                                                                   # mirrored fold sense: the folded yoke lies DOWN the bus +x face (inside the bus height) instead of standing up above the bus
    beta = np.cumsum(h); J = np.zeros((NLEAF + 2, 3)); J[0] = (ROOT_X, 0, Z_ARR)
    J[1] = J[0] + (YOKE_L if YOKE else ROOT_OFF) * np.array([np.cos(beta[0]), 0, np.sin(beta[0])])
    dirs = np.stack([np.cos(beta[1:]), np.zeros(NLEAF), np.sin(beta[1:])], -1)        # (20,3)
    for i in range(NLEAF): J[i + 2] = J[i + 1] + LEAF * dirs[i]
    cen = J[1:NLEAF + 1] + 0.5 * LEAF * dirs                                          # (20,3) leaf centres
    Rl = Ry(-beta[1:])                                                                 # (20,3,3) leaf frame u=link, v=y, n
    f = (np.abs(h[1:]) / math.pi) ** 2
    # sections: alpha = [-a, 0, -a, 0]; base = section 1 at y = -SECW/2 (deployed centres y = (s-1.5)*SECW)
    al = np.array([-a, 0.0, -a, 0.0]); yv = np.zeros(4); nv = np.zeros(4); yv[1] = -SECW / 2
    yv[2] = yv[1] + 0.5 * SECW * (math.cos(al[1]) + math.cos(al[2])); nv[2] = nv[1] + 0.5 * SECW * (math.sin(al[1]) + math.sin(al[2]))
    yv[3] = yv[2] + 0.5 * SECW * (math.cos(al[2]) + math.cos(al[3])); nv[3] = nv[2] + 0.5 * SECW * (math.sin(al[2]) + math.sin(al[3]))
    yv[0] = yv[1] - 0.5 * SECW * (math.cos(al[1]) + math.cos(al[0])); nv[0] = nv[1] - 0.5 * SECW * (math.sin(al[1]) + math.sin(al[0]))
    lev = np.array([3, 2, 1, 0]) * P_ARR * (a / math.pi)                              # stack position inside a leaf block while the width fold is closed
    pos = np.zeros((NLEAF, NSEC, 3)); R = np.zeros((NLEAF, NSEC, 3, 3))
    for s in range(NSEC):
        Rs = Rx(np.float64(al[s]))                                                     # rotation about the leaf u axis
        loc = np.array([0.0, yv[s], nv[s]])
        for i in range(NLEAF):
            pos[i, s] = cen[i] + Rl[i] @ loc + np.array([4 * i * P_ARR * f[i] + lev[s], 0, 0]) * 1.0
            R[i, s] = Rl[i] @ Rs
    return pos, R
def yoke_pose(h):
    """pose of the yoke box (centre, R with local x along the link) in wing + frame"""
    b0 = -h[0]; d = np.array([np.cos(b0), 0, np.sin(b0)]); c = np.array([ROOT_X - YOKE_DX, 0, Z_ARR]) + 0.5 * YOKE_L * d
    return c, Ry(np.float64(-b0))
# ----------------------------------------------------------------------------- stowed pack -> staged poses
def _perm_Q(dims, orient):
    perm = []; used = set()
    for j in range(3):
        for i in range(3):
            if i not in used and abs(dims[i] - orient[j]) < 1e-6: perm.append(i); used.add(i); break
    Q = np.zeros((3, 3))
    for j in range(3): Q[j, perm[j]] = 1
    if np.linalg.det(Q) < 0: Q[:, perm[2]] *= -1
    return Q
EX, EY, EZ = np.eye(3)
P_ITEM = {"radiator": np.stack([EZ, EY, EX], 1), "array": np.stack([EY, EZ, EX], 1), "bus": np.eye(3), "pod": np.eye(3)}   # D <- item local axes
POD_NAME = "comp_pod"; POD_MOUNT = np.array([0.0, 0.0, -(0.5 * 4.6259399977594295 + 0.6 + 0.05)])   # [t337] component pod (ASSUMED illustrative 0.47 x 0.8 x 1.2 m box) mounted on the bus anti-Sun (-z) face, 0.05 m gap; staging group index 28
def _staged_boxes(kind_cols):
    return None
class Sat:
    def __init__(self, layer, sat_idx):
        self.layer = layer; self.idx = sat_idx
        Ly = PK["layers"][layer]; dims = PK["items_dims_m"]; items = Ly["items"]
        cen = {}; Qs = {}
        for it in items:
            d = dims[it["name"]]["dims"]; o = it["orient_m"]; lo = np.array(it["lo_m"]); cen[it["name"]] = lo + np.array(o) / 2; Qs[it["name"]] = _perm_Q(d, o)
        bn = [n for n in cen if dims[n]["kind"] == "bus"][0]
        self.Rp = Qs[bn]; self.cbus = cen[bn]
        self.fD = self.Rp.T @ (np.array([Ly["X"] / 2, Ly["Y"] / 2, Ly["H_pack"] / 2]) - self.cbus)
        self.p0 = np.array([Ly["sats"][0]["centre_xy"][0], 0, 0])    # replaced below
        s = [q for q in Ly["sats"] if q["sat"] == sat_idx][0]; self.p0 = np.array([s["centre_xy"][0], s["centre_xy"][1], Ly["z0"] + Ly["H_pack"] / 2])
        # items -> columns
        arr_items = sorted([n for n in cen if dims[n]["kind"] == "array"]); rad_items = sorted([n for n in cen if dims[n]["kind"] == "radiator"], key=lambda n: int(n.split("_")[1]))
        _thr = 0.17 + 0.018144 * EXTRA_P; thick = [n for n in rad_items if dims[n]["dims"][2] > _thr]; thin = [n for n in rad_items if dims[n]["dims"][2] <= _thr]   # [t359] threshold moves with the extra panel
        want_thick = [(w, c) for w in (0, 1) for c in range(ACROSS) if NPAN[(w, c)] > ALONG]; want_thin = [(w, c) for w in (0, 1) for c in range(ACROSS) if NPAN[(w, c)] == ALONG]
        assert len(thick) == len(want_thick) and len(thin) == len(want_thin), (len(thick), len(thin))   # [t337] was == 13 / == 11
        self.col_item = {}
        for n, wc in zip(thick, want_thick): self.col_item[wc] = n
        for n, wc in zip(thin, want_thin): self.col_item[wc] = n
        def rp(n):
            R = self.Rp.T @ Qs[n] @ P_ITEM[dims[n]["kind"]].T
            if np.linalg.det(R) < 0: R = R @ np.diag([-1.0, 1, 1])
            return R, self.Rp.T @ (cen[n] - self.cbus)
        self.arr_pack = {w: rp(arr_items[w]) for w in (0, 1)}
        self.pod_pack = rp(POD_NAME) if POD_NAME in cen else None; self.pod_box = np.array(dims[POD_NAME]["dims"]) if POD_NAME in cen else None   # [t337]
        self.col_pack = {wc: rp(n) for wc, n in self.col_item.items()}
        self.n_cols = sorted(self.col_item)
        # group order: 24 radiator columns then 2 arrays (for staggered staging)
        self.col_lookup = {wc: i for i, wc in enumerate(self.n_cols)}
    def staged_group_centre_rad(self, w, c):
        n = NPAN[(w, c)]; pos, R = rad_chain(np.array([c]), np.array([math.pi]), n_max=ALONG + 1); pos = pos[0, :n]; Rr = R[0, :n]
        corners = np.array([[x, y, z] for x in (0, W) for y in (0, L) for z in (-.007, .007)])
        pts = np.einsum("kij,mj->kmi", Rr, corners) + pos[:, None, :]; pts = pts.reshape(-1, 3)
        if w == 1: pts = pts @ Rz(np.float64(math.pi)).T
        return 0.5 * (pts.min(0) + pts.max(0))
    def staged_group_centre_arr(self, w):
        pos, R = arr_chain(NH[0], math.pi); pts = []
        cs = np.array([[x, y, z] for x in (-LEAF / 2, LEAF / 2) for y in (-SECW / 2, SECW / 2) for z in (-TH_ARR / 2, TH_ARR / 2)])
        for i in range(NLEAF):
            for s in range(NSEC): pts.append(cs @ R[i, s].T + pos[i, s])
        pts = np.concatenate(pts)
        if w == 1: pts = pts @ Rz(np.float64(math.pi)).T
        return 0.5 * (pts.min(0) + pts.max(0))
# ----------------------------------------------------------------------------- timeline (all ASSUMED)
V_EXIT = 0.20; T_STAG = 10.0; V_Y = 0.04; V_Z = 0.01
T_U0 = 1200.0; T_UST = 3.0; T_ATT0 = 30.0; T_ATT1 = 500.0
TAU_STAGE = 9.0; TAU_GSTEP = 0.15; TAU_RAD0 = float(os.environ.get("FLEET_TAU_RAD0", "13.0")); TAU_RAD = 30.0; TAU_RSTEP = 0.4; TAU_W0 = float(os.environ.get("FLEET_TAU_W0", "13.0")); TAU_W = 14.0; TAU_N0 = float(os.environ.get("FLEET_TAU_N0", "27.0")); NEWT_1TO1 = 40.0; NEWT_FAST = 6.0
def newton_nu(tn):
    return np.where(tn <= NEWT_1TO1, tn, NEWT_1TO1 + NEWT_FAST * (tn - NEWT_1TO1))
def h_at(nu):
    nu = float(min(max(nu, 0), NT[-1])); i = nu / 0.05; i0 = int(i); i1 = min(i0 + 1, len(NT) - 1); w = i - i0
    return NH[i0] * (1 - w) + NH[i1] * w
class Fleet:
    def __init__(self):
        self.sats = []; idx = 0
        for Ly in PK["layers"]:
            for s in Ly["sats"]: self.sats.append(Sat(Ly["layer"], s["sat"]))
        self.n = len(self.sats)
        self.zrank = {}
        order = sorted(range(self.n), key=lambda i: (self.sats[i].p0[2], self.sats[i].p0[1])); self.rank = {i: r for r, i in enumerate(order)}
        for sa in self.sats:
            sa.sgx = 1.0 if sa.layer % 2 == 0 else -1.0; sa.Trel = T_STAG * sa.layer; X = PK["layers"][sa.layer]["X"]
            sa.Tex = sa.Trel + (X / 2 + 3.7) / V_EXIT; sa.vy = V_Y * (1 if sa.p0[1] > 0 else (-1 if sa.p0[1] < 0 else 0)); sa.vz = V_Z * (self.rank[sa.idx] - 6.5)
            sa.Tu = T_U0 + T_UST * self.rank[sa.idx]
            sa.rv_p = R_to_rotvec(sa.Rp)
            sa.gc = {wc: sa.staged_group_centre_rad(*wc) for wc in sa.n_cols}; sa.ga = {w: sa.staged_group_centre_arr(w) for w in (0, 1)}
        # proto order (fixed counts)
        self.n_panel = NPAN_TOT; self.n_plate = 2 * NLEAF * NSEC
    def centre(self, sa, T):
        p = sa.p0.copy(); p[0] += sa.sgx * V_EXIT * max(T - sa.Trel, 0.0)
        t2 = max(T - sa.Tex, 0.0); p[1] += sa.vy * t2
        if DECKFIX and sa.layer == 0 and sa.vz < 0:   # [t310u] hold the deck-level satellites at their release height while their footprint is still over the deck disc (4.0 s after exit), then fall 3x faster back onto the original ASSUMED vz line (reached at t2 = 6 s: later frames unchanged)
            p[2] += max(sa.vz * t2, min(0.0, 3.0 * sa.vz * (t2 - 4.0)))
        else: p[2] += sa.vz * t2
        return p
    def Rsat(self, sa, T):
        s = minjerk((T - (sa.Tex + T_ATT0)) / (T_ATT1 - T_ATT0)); return rotvec_to_R((1 - s) * sa.rv_p)
    def local(self, sa, tau):
        """body poses in the footprint-centre frame (before the satellite rotation): panels, plates, bus. tau = unfold clock (<=0 stowed)"""
        panels_p = []; panels_R = []; plates_p = []; plates_R = []; yokes_p = []; yokes_R = []
        def stage(g):
            return minjerk((tau - TAU_GSTEP * g) / TAU_STAGE)
        for gi, wc in enumerate(sa.n_cols):
            w, c = wc; n = NPAN[wc]; s = stage(gi); Rpk, cpk = sa.col_pack[wc]; Cs = sa.gc[wc]
            t_rad = TAU_RAD0 + TAU_RSTEP * (c + ACROSS * w)
            if PLAN is not None: t_rad = max(t_rad, plan_ready(sa.idx, gi) + RADGAP)      # [t316u] a column starts folding out only after it reached its staged pose
            phi = np.array([math.pi * (1 - minjerk((tau - t_rad) / TAU_RAD))])
            pos, R = rad_chain(np.array([c]), phi, n_max=n); pos = pos[0]; R = R[0]
            if w == 1: pos = pos @ Rz(np.float64(math.pi)).T; R = np.einsum("ij,kjl->kil", Rz(np.float64(math.pi)), R)
            Rs = rotvec_to_R((1 - s) * R_to_rotvec(Rpk)); Cc = cpk * (1 - s) + Cs * s + LIFT * math.sin(math.pi * s) * np.array([1.0 if w == 0 else -1.0, 0, 0])
            if PLAN is not None: Cc, rvv = planpose(sa.idx, gi, tau); Rs = rotvec_to_R(rvv)
            if tau > TAU_STAGE + TAU_GSTEP * 26 or s >= 1.0: pass
            panels_p.append(Cc + (pos - Cs) @ Rs.T - sa.fD); panels_R.append(np.einsum("ij,kjl->kil", Rs, R))
        for w in (0, 1):
            s = stage(len(sa.n_cols) + w); Rpk, cpk = sa.arr_pack[w]; Cs = sa.ga[w]
            a = math.pi * (1 - minjerk((tau - TAU_W0) / TAU_W)); tn = tau - TAU_N0; nu = float(newton_nu(max(tn, 0.0)))
            pos, R = arr_chain(h_at(nu), a); pos = pos.reshape(-1, 3); R = R.reshape(-1, 3, 3)
            if w == 1: pos = pos @ Rz(np.float64(math.pi)).T; R = np.einsum("ij,kjl->kil", Rz(np.float64(math.pi)), R)
            Rs = rotvec_to_R((1 - s) * R_to_rotvec(Rpk)); Cc = cpk * (1 - s) + Cs * s + LIFT * math.sin(math.pi * s) * np.array([1.0 if w == 0 else -1.0, 0, 0])
            if PLAN is not None: Cc, rvv = planpose(sa.idx, len(sa.n_cols) + w, tau); Rs = rotvec_to_R(rvv)
            plates_p.append(Cc + (pos - Cs) @ Rs.T - sa.fD); plates_R.append(np.einsum("ij,kjl->kil", Rs, R))
            if YOKE:
                yc, yR = yoke_pose(h_at(nu))
                if w == 1: yc = Rz(np.float64(math.pi)) @ yc; yR = Rz(np.float64(math.pi)) @ yR
                yokes_p.append(Cc + (yc - Cs) @ Rs.T - sa.fD); yokes_R.append(Rs @ yR)
                if PLAN is not None and tau < plan_ready(sa.idx, len(sa.n_cols) + 2 + w):      # [t316u] yoke travels on its own planned path from its stowed pose on the pack's top face (translation only)
                    ycc, _ = planpose(sa.idx, len(sa.n_cols) + 2 + w, tau); yokes_p[-1] = ycc - sa.fD; yokes_R[-1] = yR
        sa._yoke = (np.array(yokes_p), np.array(yokes_R)) if YOKE else None
        if sa.pod_pack is not None:      # [t337] component pod: rigid block, staged group 28 (planned path with FLEET_STAGEPLAN, else lerp), ends mounted on the bus -z face
            Rpk, cpk = sa.pod_pack; s_ = stage(28); Cc = cpk * (1 - s_) + POD_MOUNT * s_; Rs = rotvec_to_R((1 - s_) * R_to_rotvec(Rpk))
            if PLAN is not None: Cc, rvv = planpose(sa.idx, 28, tau); Rs = rotvec_to_R(rvv)
            sa._pod = (Cc - sa.fD, Rs)
        return (np.concatenate(panels_p), np.concatenate(panels_R), np.concatenate(plates_p), np.concatenate(plates_R), -sa.fD)
    def poses(self, T):
        """world poses: dict of arrays pos/R per prototype class, sat-major"""
        PP = []; PR = []; QP = []; QR = []; BP = []; BR = []; YP = []; YR = []; DP = []; DR = []
        for sa in self.sats:
            c = self.centre(sa, T); Rs = self.Rsat(sa, T); tau = T - sa.Tu
            pp, pr, qp, qr, bp = self.local(sa, tau)
            PP.append(c + pp @ Rs.T); PR.append(np.einsum("ij,kjl->kil", Rs, pr)); QP.append(c + qp @ Rs.T); QR.append(np.einsum("ij,kjl->kil", Rs, qr))
            BP.append((c + Rs @ bp)[None]); BR.append((Rs @ np.eye(3))[None])
            if sa.pod_pack is not None: DP.append((c + Rs @ sa._pod[0])[None]); DR.append((Rs @ sa._pod[1])[None])
            if YOKE: YP.append(c + sa._yoke[0] @ Rs.T + (0.0 if (PLAN is not None or tau >= TAU_STAGE + TAU_GSTEP * 26) else 1.0e5)); YR.append(np.einsum("ij,kjl->kil", Rs, sa._yoke[1]))
        ex = dict(yoke_p=np.concatenate(YP), yoke_R=np.concatenate(YR)) if YOKE else {}
        if DP: ex.update(pod_p=np.concatenate(DP), pod_R=np.concatenate(DR))      # [t337]
        return dict(**ex, panel_p=np.concatenate(PP), panel_R=np.concatenate(PR), plate_p=np.concatenate(QP), plate_R=np.concatenate(QR), bus_p=np.concatenate(BP), bus_R=np.concatenate(BR))
def boxes_aabb(pos, R, box, centred):
    """per-instance AABB (min,max) of boxes (local [0,box] or centred)"""
    lo = -box / 2 if centred else np.zeros(3); hi = box / 2 if centred else box
    cs = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    pts = np.einsum("nij,mj->nmi", R, cs) + pos[:, None, :]; return pts.min(1), pts.max(1)

# ----------------------------------------------------------------------------- clip timeline and camera (all ASSUMED / editorial)
FPS = 24.0; CLIP_S = 34.0; T_END_SIM = float(os.environ.get("FLEET_TEND", "1345.0"))
_SEG = [(0.0, 9.0, 0.0, 115.0), (9.0, 14.0, 115.0, T_U0), (14.0, CLIP_S, T_U0, T_END_SIM)]     # (clip s0, clip s1, sim s0, sim s1): act 1 release, act 2 coast time-lapse, act 3 unfold
def _tables():
    dt = 1.0 / 240; t = np.arange(0, CLIP_S + dt / 2, dt); rate = np.zeros_like(t)
    for c0, c1, s0, s1 in _SEG: rate[(t >= c0) & (t < c1 + 1e-9)] = (s1 - s0) / (c1 - c0)
    k = int(round(1.2 / dt)); pad = np.concatenate([np.full(k, rate[0]), rate, np.full(k, rate[-1])]); rs = np.convolve(pad, np.ones(k) / k, mode="same")[k:-k]
    T = np.concatenate([[0], np.cumsum(0.5 * (rs[1:] + rs[:-1]) * dt)]); T *= T_END_SIM / T[-1]; return t, T, rs * T_END_SIM / T[-1] * 0 + np.gradient(T, t)
_TT, _TS, _TR = _tables()
def sim_time(tc): return float(np.interp(tc, _TT, _TS))
def sim_rate(tc): return float(np.interp(tc, _TT, _TR))
def _ease(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
HERO = 6
def camera(tc, fleet=None, T=None):
    """returns (eye, target, horizontal fov deg) for clip time tc"""
    fleet = fleet or _FL
    T = sim_time(tc) if T is None else T
    A0 = (np.array([52.0, -44.0, 16.0]), np.array([0.0, 0.0, 9.0]), 40.0)
    A1 = (np.array([88.0, -76.0, 34.0]), np.array([0.0, 0.0, 9.0]), 42.0)
    B1 = (np.array([260.0, -820.0, 300.0]), np.array([0.0, 0.0, 8.0]), 46.0)
    _cj = os.environ.get("FLEET_CAMA", "")      # [t320u] camera override for the release act: JSON {"A0":[ex,ey,ez,tx,ty,tz,fov],"A1":[...]}
    if _cj:
        _c = json.loads(_cj)
        if "A0" in _c: v = _c["A0"]; A0 = (np.array(v[0:3], float), np.array(v[3:6], float), float(v[6]))
        if "A1" in _c: v = _c["A1"]; A1 = (np.array(v[0:3], float), np.array(v[3:6], float), float(v[6]))
    if tc <= 9.0:
        s = _ease(tc / 9.0); return A0[0] * (1 - s) + A1[0] * s, A0[1] * (1 - s) + A1[1] * s, A0[2] * (1 - s) + A1[2] * s
    if tc <= 14.0:
        s = _ease((tc - 9.0) / 5.0); return A1[0] * (1 - s) + B1[0] * s, A1[1] * (1 - s) + B1[1] * s, A1[2] * (1 - s) + B1[2] * s
    s = _ease((tc - 14.0) / (CLIP_S - 14.0) / 0.92)
    hero = fleet.centre(fleet.sats[HERO], T)
    tgt = B1[1] * (1 - s) + hero * s
    off0 = B1[0] - B1[1]; off1 = np.array([110.0, -175.0, 125.0]); off = off0 * (1 - s) ** 1.0 + off1 * (1 - (1 - s) ** 1.0) if False else off0 * (1 - s) + off1 * s
    return tgt + off, tgt, B1[2] * (1 - s) + 44.0 * s
_camera_base = camera   # [t357] unchanged original camera path
def camera(tc, fleet=None, T=None):
    """[t357] optional egress camera hold, env FLEET_CAMHOLD JSON {"H":[ex,ey,ez,tx,ty,tz,fov],"H1":[...],"dolly_f":60,"hold_f":150,"end_f":216}:
    view H until frame dolly_f, smoothstep dolly to H1 by hold_f (H1 optional: no dolly if absent), hold H1 until hold_f, then smoothstep-blend to the unchanged camera path, reached exactly at end_f (frames > end_f identical to the original)."""
    out = _camera_base(tc, fleet, T)
    _h = os.environ.get("FLEET_CAMHOLD", "")
    if not _h: return out
    c = json.loads(_h); f = tc * FPS; f1 = float(c.get("end_f", 216)); fh = float(c.get("hold_f", 150))
    def _v(k): v = c[k]; return np.array(v[0:3], float), np.array(v[3:6], float), float(v[6])
    H = _v("H")
    if "H1" in c:
        H1 = _v("H1"); fd = float(c.get("dolly_f", 60)); q = _ease((f - fd) / (fh - fd))
        H = (H[0] * (1 - q) + H1[0] * q, H[1] * (1 - q) + H1[1] * q, H[2] * (1 - q) + H1[2] * q)
    s = _ease((f - fh) / (f1 - fh))
    if s >= 1.0: return out
    return H[0] * (1 - s) + out[0] * s, H[1] * (1 - s) + out[1] * s, H[2] * (1 - s) + out[2] * s

# ---- [t360] optional render-level clearance lift of one satellite (env FLEET_SATLIFT, JSON {"sat":0,"dz":0.6,"f0":38,"f1":56,"f2":96,"f3":130}):
# the satellite is raised by dz (smoothstep f0->f1), held, and lowered back to its planned path by f3 (smoothstep f2->f3).  Rigid shift of all its instances (panels, plates, bus, yokes, pod); other satellites and all frames > f3 unchanged.
_poses_base = Fleet.poses
def _lift_dz(T, c):
    fr = float(np.interp(T, _TS, _TT)) * FPS     # sim time -> clip frame (sim_time is monotone)
    up = _ease((fr - c["f0"]) / (c["f1"] - c["f0"])); dn = _ease((fr - c["f2"]) / (c["f3"] - c["f2"]))
    return float(c["dz"]) * up * (1.0 - dn)
def _poses_lift(self, T):
    P = _poses_base(self, T); _l = os.environ.get("FLEET_SATLIFT", "")
    if not _l: return P
    c = json.loads(_l); dz = _lift_dz(T, c)
    if dz == 0.0: return P
    i = int(c.get("sat", 0)); NP_, NQ_ = NPAN_TOT, 2 * NLEAF * NSEC
    P = dict(P)
    for k, a, b in (("panel_p", i * NP_, (i + 1) * NP_), ("plate_p", i * NQ_, (i + 1) * NQ_), ("bus_p", i, i + 1), ("yoke_p", 2 * i, 2 * i + 2), ("pod_p", i, i + 1)):
        if k in P:
            v = np.array(P[k], copy=True); v[a:b, 2] += dz; P[k] = v
    return P
Fleet.poses = _poses_lift
_FL = Fleet()
def time_label(T):
    return f"T+{int(T // 60):02d}:{int(T % 60):02d}"
