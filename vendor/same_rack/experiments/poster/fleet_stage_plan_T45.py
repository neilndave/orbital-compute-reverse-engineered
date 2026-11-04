"""[t316u] Collision-planned STAGING of one satellite (the 26 rigid blocks leaving the stowed pack: 24 radiator columns + 2 array stacks, plus the 2 yoke booms) -- replaces the straight-line lerp of fleet_kin_T45.Fleet.local
(which swept blocks through each other and through the bus: 142 item pairs overlapped at tau 1-11 s).  RENDER KINEMATICS ONLY (the real trunk/truss mechanism is not modelled).  ESTIMATE / ASSUMED.
Method: every block is a rigid compound of OBBs (the actual mesh bounds of fleet_mesh_clearance_T45).  Block path = stowed pose -> LIFT along one footprint axis (orientation kept) -> [HOVER = staged pose displaced along an axis, orientation = staged] -> staged pose;
segments are min-jerk, stop-and-go, at a mean speed V_MEAN.  Greedy scheduling: repeatedly pick the block/candidate path/start time that finishes first, with every sample (dt 0.1 s) of the motion tested against every other block (stowed if not yet
scheduled, on its planned trajectory otherwise) by SAT; a pair must keep a gap >= min(MARGIN, its resting gap in the stowed pack or in the staged layout) - 1 mm.  The yoke of wing w is allowed to touch leaf 0 of its own array stack (it is hinged to it).
Yokes are stowed lying on the pack's top face (the face that points world +z at release) in the 0.22 m layer gap (ASSUMED; the real stowed volume of the yoke is NOT in the packing study -- design question).
usage: python fleet_stage_plan_T45.py out.json [sat ...]   (env as the render: FLEET_SYNC=1 FLEET_YOKE=1 ...)"""
import sys, json, math, pathlib, time
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
_a = sys.argv; sys.argv = [_a[0], "/tmp"]
import fleet_kin_T45 as K
import fleet_mesh_clearance_T45 as M
sys.argv = _a
NEAR_S = float(__import__('os').environ.get('PLAN_NEAR_S', 0.6)); NEAR_M = float(__import__('os').environ.get('PLAN_NEAR_M', 0.9))   # [t316c] near-filters widened: bodies move up to ~0.5 m between 0.1 s samples
DT = 0.1; TG = 70.0; NT = int(TG / DT) + 1; MARGIN = 0.04; V_MEAN = float(__import__('os').environ.get('PLAN_V', 1.4)); ROT_W = 1.2; MINSEG = 1.0
DIRS = [np.array(v, float) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
L1S = [0.5, 1.0, 1.6, 2.4, 3.2, 4.0]; L2S = [0.8, 1.6, 2.8]
class Body:
    def __init__(s, name, A, R0, H, Cs, Cc0, rv0, Cc1, rv1, fD, kind):
        s.name = name; s.A = A; s.R0 = R0; s.H = H; s.fD = fD; s.kind = kind; s.Cc0 = np.asarray(Cc0, float); s.rv0 = np.asarray(rv0, float); s.Cc1 = np.asarray(Cc1, float); s.rv1 = np.asarray(rv1, float)
    def boxes(s, Cc, rv):
        Rs = K.rotvec_to_R(rv); return (Cc - s.fD) + s.A @ Rs.T, np.einsum("ij,kjl->kil", Rs, s.R0), s.H
def aabb_of(b, Cc, rv):
    X, R, H = b.boxes(Cc, rv); lo, hi = M.aabb(X, R, H); return lo.min(0), hi.max(0)
def seg_path(wps, V=V_MEAN):
    """wps: list of (Cc, rv); returns durations"""
    d = []
    for (c0, r0), (c1, r1) in zip(wps[:-1], wps[1:]): d.append(max(MINSEG, (np.linalg.norm(c1 - c0) + ROT_W * np.linalg.norm(r1 - r0)) / V))
    return d
def path_at(wps, durs, t):
    """pose at time t after start (t<0 -> first, t>total -> last)"""
    if t <= 0: return wps[0]
    for (c0, r0), (c1, r1), d in zip(wps[:-1], wps[1:], durs):
        if t <= d: u = float(K.minjerk(t / d)); return c0 * (1 - u) + c1 * u, r0 * (1 - u) + r1 * u
        t -= d
    return wps[-1]
def rest_sep(bs, poses, a, b, tol=0.6):
    return M.sat_sep(bs[a].boxes(*poses[a]), bs[b].boxes(*poses[b]), tol=tol)[0]
def build(fl, sa):
    fD = sa.fD; g = {}
    import fleet_own_diag_T45 as D
    items = D.items(fl, sa, 13.0)
    bodies = []
    for gi, wc in enumerate(sa.n_cols):
        nm = f"col{wc[0]}_{wc[1]:02d}"; C, R, H = items[nm]; Rpk, cpk = sa.col_pack[wc]; Cs = sa.gc[wc]
        bodies.append(Body(nm, C + fD - Cs, R, H, Cs, cpk, K.R_to_rotvec(Rpk), Cs, np.zeros(3), fD, "col"))
    for w in (0, 1):
        nm = f"plates{w}"; C, R, H = items[nm]; Rpk, cpk = sa.arr_pack[w]; Cs = sa.ga[w]
        bodies.append(Body(nm, C + fD - Cs, R, H, Cs, cpk, K.R_to_rotvec(Rpk), Cs, np.zeros(3), fD, "arr"))
    C, R, H = items["bus"]; bus = Body("bus", C + 0 * fD - 0, R, H, None, fD, np.zeros(3), fD, np.zeros(3), fD, "bus"); bus.A = C.copy() + 0.0; bus.fD = np.zeros(3); bus.Cc0 = np.zeros(3); bus.Cc1 = np.zeros(3)
    # yokes: stowed on the pack's top face
    st = [b for b in bodies]
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for b in bodies + [bus]:
        l, h = aabb_of(b, b.Cc0, b.rv0) if b.kind != "bus" else aabb_of(b, b.Cc0, b.rv0); lo = np.minimum(lo, l); hi = np.maximum(hi, h)
    Rs0 = K.rotvec_to_R(sa.rv_p); top_plus = Rs0[2, 0] > 0      # local +x points to world +z at release
    face = hi[0] if top_plus else lo[0]; sgn = 1.0 if top_plus else -1.0
    xc = face + sgn * 0.11; zc = 0.5 * (lo[2] + hi[2])
    yk = []
    for w in (0, 1):
        C, R, H = items[f"yoke{w}"]; Xf = C[0]; ys = (-1.0 if w == 0 else 1.0) * 0.8 + 0.5 * (lo[1] + hi[1])
        Xs = np.array([xc, ys, zc]); yk.append(Body(f"yoke{w}", np.zeros((1, 3)), R, H, None, Xs + fD, np.zeros(3), Xf + fD, np.zeros(3), fD, "yoke"))
    if sa.pod_pack is not None:      # [t337] component pod = body 28: stowed pack pose -> mount on the bus -z face (ASSUMED illustrative mount)
        Rpk, cpk = sa.pod_pack; yk.append(Body("pod", np.zeros((1, 3)), np.eye(3)[None], (sa.pod_box / 2)[None], None, cpk, K.R_to_rotvec(Rpk), K.POD_MOUNT, np.zeros(3), fD, "pod"))
    return bodies + yk, bus, dict(top_plus=bool(top_plus), face=float(face), pack_lo=lo.tolist(), pack_hi=hi.tolist())
def exact_gap(a, pa, b, pb, tol=0.25):
    Ba = a.boxes(*pa); Bb = b.boxes(*pb)
    if a.kind == "yoke" and b.name == "plates" + a.name[-1]: Bb = tuple(x[4 * 1:] for x in Bb)       # leaf 0 (first 4 sections) is hinged to the yoke
    if b.kind == "yoke" and a.name == "plates" + b.name[-1]: Ba = tuple(x[4 * 1:] for x in Ba)
    return M.sat_sep(Ba, Bb, tol=tol)[0]
def compute_parks(bodies, bus, fl_sa):
    """PARK layout = the final staged layout scaled outward from the bus centre by f (orientation kept) -> every block is spread apart, so stowed -> park can never be blocked by a final pose of another block (the cyclic dead-lock of the direct stowed -> final planning)"""
    cb = bus.A.mean(0); best = None
    for f in [x for x in (1.5, 1.8, 2.2, 2.7, 3.3, 4.0) if x >= float(__import__('os').environ.get('PLAN_PARK_FMIN', 0))]:      # [t344] PLAN_PARK_FMIN: start the (existing) spread ladder higher; thresholds untouched
        for b in bodies:
            cw = b.Cc1 - b.fD + b.A.mean(0); b.park = (b.Cc1 + (f - 1.0) * (cw - cb), b.rv1.copy())
        mg = 9.0
        for i, a in enumerate(bodies):
            for b in bodies[i + 1:]:
                g = exact_gap(a, a.park, b, b.park, tol=0.25)
                if a.kind == "yoke" or b.kind == "yoke": continue
                mg = min(mg, g)
            mg = min(mg, exact_gap(a, a.park, bus, (bus.Cc0, bus.rv0), tol=0.25))
        if best is None or mg > best[0]: best = (mg, f, [b.park for b in bodies])
        if mg >= 0.06: break
    for b, pk in zip(bodies, best[2]): b.park = pk
    # [t316] any block whose park overlaps another block's STOWED pose (cyclic dead-lock) is shifted along an axis until clear
    for yb in [b for b in bodies if b.kind != "yoke"]:
        def conf(pk):
            mg = 9.0
            for o in bodies:
                if o is yb: continue
                mg = min(mg, exact_gap(yb, pk, o, (o.Cc0, o.rv0), tol=0.25))
            return mg
        if conf(yb.park) >= 0.0: continue
        base = yb.park; done = False
        for mag in (0.2, 0.4, 0.7, 1.0, 1.5, 2.2):
            for d in DIRS:
                pk = (base[0] + d * mag, base[1])
                if conf(pk) < 0.05: continue
                if min(exact_gap(yb, pk, o, o.park, tol=0.25) for o in bodies if o is not yb and o.kind != "yoke") < 0.05 or exact_gap(yb, pk, bus, (bus.Cc0, bus.rv0), tol=0.25) < 0.05: continue
                yb.park = pk; done = True; print("   park shifted", yb.name, mag, d, flush=True); break
            if done: break
        if not done: print("   WARNING park not clear", yb.name, flush=True)
    # yoke park: shift along an axis until it clears every other block both in its stowed pose and in its park pose (own leaf 0 exempt)
    for yb in [b for b in bodies if b.kind == "yoke"]:
        base = yb.park; done = False
        for mag in (0.0, 0.3, 0.6, 1.0, 1.5, 2.2):
            for d in (DIRS if mag > 0 else DIRS[:1]):
                pk = (base[0] + d * mag, base[1]); mg = 9.0
                for o in bodies + [bus]:
                    if o is yb or o.kind == "yoke": continue
                    mg = min(mg, exact_gap(yb, pk, o, (o.Cc0, o.rv0), tol=0.25))
                    if o is not bus: mg = min(mg, exact_gap(yb, pk, o, o.park, tol=0.25))
                if mg >= 0.05: yb.park = pk; done = True; break
            if done: break
        if not done: print("   WARNING yoke park not clear", yb.name, flush=True)
    return best[0], best[1]
def plan_sat(fl, sat, phase="A", verbose=True):
    sa = fl.sats[sat]; bodies, bus, info = build(fl, sa); n = len(bodies); allb = bodies + [bus]; nb = len(allb)
    pgap, pf = compute_parks(bodies, bus, sa); info["park_gap"] = float(pgap); info["park_f"] = float(pf)
    if verbose: print(f"  sat {sat} phase {phase}: park layout f={pf} min gap {pgap:.3f}", flush=True)
    for b in bodies:
        if phase == "A": b.Cc1, b.rv1 = b.park
        else: b.Cc0, b.rv0 = b.park
    # thresholds: min(MARGIN, max(rest gap stowed, rest gap staged)) - 1 mm
    thr = np.zeros((nb, nb)); issues = []
    for i in range(nb):
        for j in range(i + 1, nb):
            a, b = allb[i], allb[j]
            g0 = exact_gap(a, (a.Cc0, a.rv0), b, (b.Cc0, b.rv0)); g1 = exact_gap(a, (a.Cc1, a.rv1), b, (b.Cc1, b.rv1))
            if a.kind == "yoke" or b.kind == "yoke": g0 = 9.0         # yokes are not part of the stowed pack
            thr[i, j] = thr[j, i] = min(MARGIN, g0, g1) - 0.001
            if g1 < 0.0: issues.append((a.name, b.name, "staged-final overlap", float(g1)))
            if g0 < 0.0 and not (a.kind == "yoke" or b.kind == "yoke"): issues.append((a.name, b.name, "stowed overlap", float(g0)))
    # grid state: Cc/rv arrays (NT,3) per body; unscheduled = constant stowed
    CC = [np.tile(b.Cc0, (NT, 1)) for b in allb]; RV = [np.tile(b.rv0, (NT, 1)) for b in allb]
    LO = np.zeros((nb, NT, 3)); HI = np.zeros((nb, NT, 3))
    def fill_aabb(i):
        b = allb[i]; cache = {}
        for k in range(NT):
            key = (tuple(np.round(CC[i][k], 6)), tuple(np.round(RV[i][k], 6)))
            if key not in cache: cache[key] = aabb_of(b, CC[i][k], RV[i][k])
            LO[i, k], HI[i, k] = cache[key]
    for i in range(nb): fill_aabb(i)
    sched = {}; last_end = 0
    def check(ci, path_Cc, path_rv, i0, kmax, exempt_static=False):
        """path arrays at grid samples i0..i0+kmax (inclusive); returns True if clear vs all others in the CURRENT grid state"""
        a = allb[ci]
        for k in range(kmax + 1):
            gi = i0 + k
            if gi >= NT: return False
            lo, hi = aabb_of(a, path_Cc[k], path_rv[k]) if (k == 0 or not np.array_equal(path_Cc[k], path_Cc[k - 1]) or not np.array_equal(path_rv[k], path_rv[k - 1])) else (lo, hi)
            for j in range(nb):
                if j == ci: continue
                gap = np.maximum(lo - HI[j, gi], LO[j, gi] - hi).max()
                if gap > 0.3: continue
                e = exact_gap(a, (path_Cc[k], path_rv[k]), allb[j], (CC[j][gi], RV[j][gi]))
                if e < thr[ci, j]: return False
        return True
    unsched = set(range(n)); t_start = time.time()
    xc0 = np.mean([bb.Cc0[0] for bb in bodies[:24]])
    order = [26, 27] + sorted(range(24), key=lambda i: -abs(bodies[i].Cc0[0] - xc0)) + [24, 25] + ([28] if n > 28 else [])
    if __import__('os').environ.get('PLAN_ORDER') == 'platesrev': order = [26, 27, 24, 25] + sorted(range(24), key=lambda i: abs(bodies[i].Cc0[0] - xc0)) + ([28] if n > 28 else [])
    if __import__('os').environ.get('PLAN_ORDER') == 'platesfirst': order = [26, 27, 24, 25] + sorted(range(24), key=lambda i: -abs(bodies[i].Cc0[0] - xc0)) + ([28] if n > 28 else [])
    if __import__('os').environ.get('PLAN_ORDER', '').startswith('shuffle'):      # [t344] diversity: yokes first, then a seeded random order of the 24 columns + 2 arrays, pod last (pure ordering heuristic; no threshold changes)
        _rng = np.random.RandomState(int(__import__('os').environ['PLAN_ORDER'][7:])); order = [26, 27] + [int(x) for x in _rng.permutation(26)] + ([28] if n > 28 else [])
    if __import__('os').environ.get('PLAN_FIRST'):      # [t344] ordering heuristic only: named bodies are planned first, right after the yokes
        _f = [[b.name for b in bodies].index(x) for x in __import__('os').environ['PLAN_FIRST'].split(',')]; order = [26, 27] + _f + [x for x in order if x not in _f and x not in (26, 27)]
    def try_plan(ci):
        b = allb[ci]; cands = []
        rot = float(np.linalg.norm(b.rv1 - b.rv0)) > 1e-6
        for d in DIRS:
            for L1 in L1S:
                lift = (b.Cc0 + d * L1, b.rv0); liftR = (b.Cc0 + d * L1, b.rv1)
                cands.append(("lift", [(b.Cc0, b.rv0), lift, (b.Cc1, b.rv1)]))
                if rot: cands.append(("lift_rot", [(b.Cc0, b.rv0), lift, liftR, (b.Cc1, b.rv1)]))
                for hd in DIRS:
                    for L2 in L2S:
                        hov = (b.Cc1 + hd * L2, b.rv1)
                        cands.append(("hov", [(b.Cc0, b.rv0), lift, hov, (b.Cc1, b.rv1)]))
                        if rot: cands.append(("hov_rot", [(b.Cc0, b.rv0), lift, liftR, hov, (b.Cc1, b.rv1)]))
        cands = [(sum(seg_path(c[1])), c) for c in cands]; cands.sort(key=lambda x: x[0]); tried = 0
        for dur, c in cands:
            wps = c[1]; durs = seg_path(wps); T = sum(durs); K_ = int(math.ceil(T / DT)); kext = max(K_, last_end + 1)
            pc = []; pr = []; pcm = []; prm = []
            for k in range(K_ + 1): cc, rr = path_at(wps, durs, k * DT); pc.append(cc); pr.append(rr)
            for k in range(K_ + 1): cc, rr = path_at(wps, durs, (k + 0.5) * DT); pcm.append(cc); prm.append(rr)
            los = np.zeros((kext + 1, 3)); his = np.zeros((kext + 1, 3)); cache = {}
            for k in range(kext + 1):
                kk = min(k, K_); key = (tuple(np.round(pc[kk], 6)), tuple(np.round(pr[kk], 6)))
                if key not in cache: cache[key] = aabb_of(b, pc[kk], pr[kk])
                los[k], his[k] = cache[key]
            ok = True
            for j in list(unsched) + [n]:
                if j == ci: continue
                o = allb[j]; gp = np.maximum(los[:K_ + 1] - HI[j, 0], LO[j, 0] - his[:K_ + 1]).max(-1)
                for k in np.nonzero(gp < NEAR_S)[0]:
                    if exact_gap(b, (pc[k], pr[k]), o, (o.Cc0, o.rv0)) < thr[ci, j]: ok = False; break
                    if k < K_ and exact_gap(b, (pcm[k], prm[k]), o, (o.Cc0, o.rv0)) < thr[ci, j]: ok = False; break      # [t316c] mid-sample
                if not ok: break
            if not ok: continue
            tried += 1
            sch = [j for j in range(nb) if j != ci and j not in unsched and j != n]
            i0s = np.arange(0, NT - kext - 1, 2); ks = np.arange(kext + 1)
            if __import__('os').environ.get('PLAN_PRUNE') == '1': i0s = i0s[i0s <= max(last_end + 2, 2)]      # [t344] exact speed-up: every slot starting after the last scheduled body has landed sees the identical static environment, so one such slot is enough; idx = i0s[:, None] + ks[None, :]
            idx = i0s[:, None] + ks[None, :]
            nears = []
            for j in sch:
                gp = np.maximum(los[None] - HI[j][idx], LO[j][idx] - his[None]).max(-1)       # (ni0, kext+1)
                nears.append(gp < NEAR_M)
            found = None
            for ii, i0 in enumerate(i0s):
                good = True
                for jj, j in enumerate(sch):
                    for k in np.nonzero(nears[jj][ii])[0]:
                        kk = min(k, K_)
                        if exact_gap(b, (pc[kk], pr[kk]), allb[j], (CC[j][i0 + k], RV[j][i0 + k])) < thr[ci, j]: good = False; break
                        if k < kext and exact_gap(b, (pcm[kk], prm[kk]), allb[j], ((CC[j][i0 + k] + CC[j][i0 + k + 1]) / 2, (RV[j][i0 + k] + RV[j][i0 + k + 1]) / 2)) < thr[ci, j]: good = False; break      # [t316c] mid-sample (moving vs moving)
                    if not good: break
                if good: found = int(i0); break
            if found is not None: return found, wps, durs, c[0]
            if tried >= int(__import__("os").environ.get("PLAN_TRIES", 40)): break
        print(f"    {b.name}: no plan; cands {len(cands)} passed-sweep {tried}", flush=True)
        return None
    import os
    part = os.environ.get("PLAN_PARTIAL", "") + f".s{sat}{phase}.json" if os.environ.get("PLAN_PARTIAL") else None
    def apply(ci, i0, wps, durs):
        nonlocal last_end
        b = allb[ci]; K_ = int(math.ceil(sum(durs) / DT))
        for k in range(NT):
            cc, rr = path_at(wps, durs, (k - i0) * DT); CC[ci][k] = cc; RV[ci][k] = rr
        fill_aabb(ci); sched[ci] = dict(name=b.name, t0=i0 * DT, wps=[[list(map(float, c)), list(map(float, r))] for c, r in wps], durs=[float(x) for x in durs], t1=i0 * DT + sum(durs)); last_end = max(last_end, i0 + K_)
        unsched.discard(ci)
    if part and pathlib.Path(part).exists():
        for e in json.load(open(part)):
            ci = [x.name for x in allb].index(e["name"])
            apply(ci, int(round(e["t0"] / DT)), [(np.array(c), np.array(r)) for c, r in e["wps"]], e["durs"])
        print("  resumed", len(sched), "bodies", flush=True)
    def explain(ci):
        b = allb[ci]; print("   explain", b.name, "stowed gaps vs others (static, thr):", flush=True)
        for j in range(nb):
            if j == ci: continue
            e0 = exact_gap(b, (b.Cc0, b.rv0), allb[j], (CC[j][0], RV[j][0])) if j in unsched or j == n else exact_gap(b, (b.Cc0, b.rv0), allb[j], (CC[j][-1], RV[j][-1]))
            e1 = exact_gap(b, (b.Cc1, b.rv1), allb[j], (CC[j][-1], RV[j][-1]))
            if e0 < 0.1 or e1 < 0.1: print(f"     vs {allb[j].name:9s} stow/pose gap {e0:7.3f}  final/pose gap {e1:7.3f} thr {thr[ci, j]:.3f} {'UNSCHED' if j in unsched else ''}", flush=True)
    while unsched:
        progress = False
        for ci in [i for i in order if i in unsched]:
            r = try_plan(ci)
            if r is None: continue
            i0, wps, durs, kind = r; b = allb[ci]; K_ = int(math.ceil(sum(durs) / DT))
            apply(ci, i0, wps, durs); progress = True
            if part: json.dump([sched[i] for i in sched], open(part, "w"))
            if verbose: print(f"  sat {sat}: {b.name:9s} t0 {i0 * DT:5.1f} dur {sum(durs):5.1f} end {i0 * DT + sum(durs):5.1f}  [{len(sched)}/{n}] ({time.time() - t_start:.0f}s)", flush=True)
        if not progress:
            print("sat", sat, "DEADLOCK, unscheduled:", [allb[i].name for i in sorted(unsched)], flush=True)
            for ci in sorted(unsched)[:2]: explain(ci)
            return None
    return dict(sat=sat, info=info, issues=issues, bodies=[sched[i] for i in range(n)], t_ready=max(v["t1"] for v in sched.values()))
def combine(rA, rB, pause=0.5):
    """join phase A (stowed -> park) and phase B (park -> final); B starts pause s after the last A block arrives"""
    tB = rA["t_ready"] + pause; bodies = []
    for a, b in zip(rA["bodies"], rB["bodies"]):
        assert a["name"] == b["name"]
        hold = max(0.01, (tB + b["t0"]) - a["t1"])
        wps = a["wps"] + b["wps"]; durs = a["durs"] + [hold] + b["durs"]
        bodies.append(dict(name=a["name"], t0=a["t0"], wps=wps, durs=durs, t1=a["t0"] + sum(durs)))
    return dict(sat=rA["sat"], info=dict(rA["info"], phaseB_start=tB), issues=rA["issues"] + rB["issues"], bodies=bodies, t_ready=max(x["t1"] for x in bodies))
def plan_two(fl, sat):
    rA = plan_sat(fl, sat, "A")
    if rA is None: return None
    rB = plan_sat(fl, sat, "B")
    if rB is None: return None
    return combine(rA, rB)
if __name__ == "__main__":
    out = sys.argv[1]; sats = [int(x) for x in sys.argv[2:]]; fl = K.Fleet(); res = {}
    if pathlib.Path(out).exists(): res = json.load(open(out))
    for s in (sats or range(fl.n)):
        if str(s) in res: continue
        r = plan_two(fl, s)
        if r is not None: res[str(s)] = r; json.dump(res, open(out, "w"), indent=1)
        print("sat", s, "ready", None if r is None else round(r["t_ready"], 1), "issues", None if r is None else r["issues"][:5], flush=True)
