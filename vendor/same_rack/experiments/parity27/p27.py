"""T306 parity-27 packing optimisation, instrumented joint-optimisation driver (box CPU; the same thermal kernel runs on the GB10 GPU with --device cuda:0).
Joint loop per candidate = [packing enumeration -> sizing (thermal closure, mass chain, FCC) -> structural checks].  Every stage is wall-clocked into results/parity27/timing_*.jsonl.
Labels: all model outputs are ESTIMATE (reduced models calibrated to the repo's Warp 3-D results); STATEMENT only for public figures; ASSUMED where not public.
"""
import functools, itertools, json, math, os, pathlib, sys, time
from multiprocessing import Pool
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "experiments/knobs")); sys.path.insert(0, str(ROOT / "src"))
import volume_levers_T45 as V
R = V.R
OUT = ROOT / "results/parity27"; OUT.mkdir(parents=True, exist_ok=True)
GAP = 0.05; ZSTD = R.ZTOP
# ---------------------------------------------------------------- satellite item model (geometry of the stored O5 stowed layout: 24 radiator stacks, 2 array blocks, 1 bus)
RAD_W = {"cold45": 0.423, "hot97": 0.424}; RAD_L = {"cold45": 2.973, "hot97": 2.624}; AP_FACE = {"cold45": 2.1403, "hot97": 1.8879}
N_STACKS = 24; W0_ARR = {"cold45": 1.343, "hot97": 830.19 / (2 * 14.0 * 20)}   # array leaf-length side [m] at f = 1 (area / (2 wings x 14 m x 20 leaves))
BX, BY = 0.7, 2.0; BUSZ0 = V.BUS_Z0
VEQ0 = (4.626 - BUSZ0) * BX * BY; EXCL_RATIO = {"cold45": 1.0, "hot97": 1564.0 / 1935.0 if False else 1.0}   # hot bus equipment volume kept = cold (ESTIMATE, bus_excl_rack differs by < 20 %)
RISK = {"leaf9": 1, "leaf6": 2, "rad14": 1, "rad10": 2, "fold3": 1, "fold2": 2, "roll7": 2, "roll3.5": 2, "zfold": 3, "x2side": 1, "x2tall": 1, "split": 1, "rho800": 1, "adapt15": 1, "adapt05": 2, "hot97": 3, "ext22": 3, "books": 2}
def build_items(fam, f, n_pan, S):
    """S: dict of shape levers: fold, leaf (m), roll (None|'7'|'3.5'), rpitch (m), rmode, bus ('mono'|'split<k>'|'wide'), rho (kg/m3 of equipment bay)."""
    its = []
    n = S.get("fold", 4); p = S.get("leaf", 0.012); roll = S.get("roll"); w = W0_ARR[fam] * f
    if roll:
        Vw = 188.0 * f / 2 / 40.0; pieces = 2 if roll == "7" else 4; L = 14.0 / pieces
        dia = math.sqrt(4 * (Vw / pieces) / (math.pi * L)) + 0.02
        for i in range(2):
            for j in range(pieces): its.append((f"array_{i}_r{j}", "array", (L, dia, dia)))
    else:
        for i in range(2): its.append((f"array_{i}", "array", (14.0 / n, w, 20 * p * n)))
    rp = S.get("rpitch", 0.02); thick = (n_pan / N_STACKS - 1.0) * rp + 0.003; wd, ln = RAD_W[fam], RAD_L[fam]; mode = S.get("rmode", "stacks")
    if mode == "stacks": its += [(f"rad_{i}", "radiator", (wd, ln, thick)) for i in range(N_STACKS)]
    elif mode == "x2side": its += [(f"rad_{i}", "radiator", (2 * wd + 0.01, ln, thick)) for i in range(N_STACKS // 2)]
    elif mode == "x2tall": its += [(f"rad_{i}", "radiator", (wd, ln, 2 * thick)) for i in range(N_STACKS // 2)]
    elif mode == "zfold": its += [(f"rad_{i}", "radiator", (wd, ln / 2 + 0.02, 2 * thick)) for i in range(N_STACKS)]
    Veq = VEQ0 * (0.338 + 0.662 * f) * (V.V_EQ_DENSITY0 / S.get("rho", 400.0))
    bus = S.get("bus", "mono")
    if bus == "mono": its.append(("bus", "bus", (BX, BY, BUSZ0 + Veq / (BX * BY))))
    elif bus == "wide": its.append(("bus", "bus", (1.4, BY, BUSZ0 + Veq / (1.4 * BY))))
    elif bus.startswith("split"):
        k = int(bus[5:]); rack_h = BUSZ0 / k + 0.10
        its += [(f"rackmod_{i}", "bus", (BX, BY, rack_h)) for i in range(k)] + [("equip", "bus", (BX, BY, Veq / (BX * BY)))]
    return its
def cand_grid(step):
    rmax = R.r_allowed(8.0); c = set()
    xs = [1.5 + step * i for i in range(int(round((7.75 - 1.5) / step)) + 1)] + [7.05, 7.35, 6.05, 6.55, 5.05, 5.55]
    for X in xs:
        ys = [0.75 + step * j for j in range(int(round((X - 0.75) / step)) + 1)] + [X / 2]
        for Y in ys:
            if Y <= X + 1e-9 and math.hypot(X, Y) / 2 <= rmax + 1e-9: c.add((round(X, 3), round(Y, 3)))
    return sorted(c)
def table_rows(its, step):
    R.items = its; R._PC = {}; rows = []
    for X, Y in cand_grid(step):
        r = R._pack(X, Y, False)
        if r is not None: rows.append((X, Y, r[0]))
    return rows
# ---------------------------------------------------------------- layer DP (V.dp generalised: layers of m identical slabs, rows<=maxrows, per row<=maxper, m<=mmax)
@functools.lru_cache(None)
def layer_cr2(m, X, Y, gap, maxrows, maxper):
    best = None
    def parts(rem, mx, k):
        if rem == 0: yield (); return
        if k == 0: return
        for a in range(min(rem, mx), 0, -1):
            for rest in parts(rem - a, a, k - 1): yield (a,) + rest
    for part in parts(m, maxper, maxrows):
        k = len(part)
        for (a, b) in ((X, Y), (Y, X)):
            Hh = k * b + (k - 1) * gap; cr = 0.0
            for j, nr in enumerate(part):
                wd = nr * a + (nr - 1) * gap; y0 = -Hh / 2 + j * (b + gap); y1 = y0 + b
                cr = max(cr, math.hypot(wd / 2, max(abs(y0), abs(y1))))
            if best is None or cr < best: best = cr
    return best
def dp2(rows, mmax=6, maxrows=3, maxper=3, gap=GAP, adapt=0.30, pmode="std"):
    rfun, ztop = V.profile(pmode); cands = []
    for X, Y, H in rows:
        for m in range(1, mmax + 1):
            cr = layer_cr2(m, X, Y, gap, maxrows, maxper)
            if cr is not None: cands.append((m, X, Y, H, cr))
    cands.sort(key=lambda c: c[3])
    @functools.lru_cache(None)
    def f(zc):
        z = zc / 100; best = (0, None)
        for m, X, Y, H, cr in cands:
            top = z + H
            if top > ztop + 1e-9: break
            if cr <= rfun(top) + 1e-9:
                v = m + f(int(round((top + gap + adapt) * 100)))[0]
                if v > best[0]: best = (v, (m, X, Y, H, z, cr))
        return best
    zc = int(round(adapt * 100)); seq = []; n = f(zc)[0]
    while True:
        v, c = f(zc)
        if c is None: break
        seq.append(dict(m=c[0], X=c[1], Y=c[2], H=round(c[3], 3), z0=round(c[4], 2), corner_r=round(c[5], 3))); zc = int(round((c[4] + c[3] + gap + adapt) * 100))
    return n, seq
ARCH = {"stack1": dict(mmax=1, maxrows=1, maxper=1),          # one satellite per level, flat-pack stack
        "layers": dict(mmax=6, maxrows=3, maxper=3),           # 2-3 columns / side-by-side / hex-like, up to 6 per level (adopted K-lever packer)
        "books": dict(mmax=12, maxrows=4, maxper=8)}           # slabs on edge side-by-side (radial / book-shelf), up to 12 per level, <=4 rows x 8
import pickle
P_CACHE = pathlib.Path(os.environ.get('P27_CACHE', OUT / 'cache')); P_CACHE.mkdir(exist_ok=True, parents=True)
def pack_job(args):
    key, fam, f, n, S, step, cfgs = args; tf = P_CACHE / f"tab_{key}.pkl"; t0 = time.perf_counter(); hit = tf.exists()
    its = build_items(fam, f, n, S)
    if hit: rows = pickle.load(open(tf, "rb")); tt = 0.0
    else:
        t1 = time.perf_counter(); rows = table_rows(its, step); tt = time.perf_counter() - t1; pickle.dump(rows, open(tf, "wb"))
    t2 = time.perf_counter(); res = {}
    for (arch, bay, adapt) in cfgs:
        k = ARCH[arch]; nn, seq = dp2(rows, mmax=k["mmax"], maxrows=k["maxrows"], maxper=k["maxper"], adapt=adapt, pmode=bay); res[f"{arch}|{bay}|{adapt}"] = (nn, seq)
    return key, dict(res=res, table_s=tt, dp_s=time.perf_counter() - t2, cache_hit=hit, item_vol=sum(a * b * c for _, _, (a, b, c) in its), slot_ok=V.slot_check(its)[0])

# ---------------------------------------------------------------- evaluation of the packing stage
def pack_eval(args):
    """worker: (shape key, fam, f, n_pan, S, step, cfgs) -> table + dp for each (arch, bay, adapter) cfg.  Returns counts and per-stage seconds."""
    key, fam, f, n_pan, S, step, cfgs = args
    t0 = time.perf_counter(); its = build_items(fam, f, n_pan, S); t1 = time.perf_counter()
    rows = table_rows(its, step); t2 = time.perf_counter(); res = {}
    for (arch, bay, adapt) in cfgs:
        k = ARCH[arch]; n, seq = dp2(rows, mmax=k["mmax"], maxrows=k["maxrows"], maxper=k["maxper"], adapt=adapt, pmode=bay); res[f"{arch}|{bay}|{adapt}"] = (n, seq)
    t3 = time.perf_counter()
    vol = sum(float(np.prod(d)) for _, _, d in its)
    return key, dict(res=res, sec=dict(items=t1 - t0, table=t2 - t1, dp=t3 - t2), n_items=len(its), item_vol_m3=vol, min_H=min(r[2] for r in rows) if rows else None,
                     slot_ok=V.slot_check(its)[0])

# ---------------------------------------------------------------- sizing: thermal closure (reduced model + Warp MC), mass chain, structural margins, FCC
LF = V.HINGE_LAUNCH_FACTOR; THR_ADOPT = {"E_092_099": 1.658, "O5knobs_095_095": 0.651}   # adopted p05 LEO margins (K): thermal closure target "adopted-equivalent"
_TH = {}; DEV = None
def thermal_mod():
    if "m" not in _TH:
        import thermal_p27 as TP; _TH["m"] = TP
    return _TH["m"]
def mc_margins(fam, n, f, N, device=None, orbits=(0, 1)):
    TP = thermal_mod(); o = {}
    for opt in TP.OPT:
        for orb in orbits:
            o[f"{opt}|{'SSO' if orb == 0 else 'LEO'}"] = TP.run_mc(fam, opt, orb, n, f, N, 20261111 + orb, device=device)
        o[f"{opt}|worst"] = TP.worst_margin(fam, opt, n, f)
    return o
def closure(fam, f, mode="adopt", N=200000, device=None, cache={}):
    """smallest integer panel count n with p05 LEO >= threshold at both optics (adopt: adopted-equivalent thresholds; min: p05>=0 SSO+LEO+worst>=0).  Returns n, margins, seconds, mc_calls."""
    key = (fam, f, mode, N, device)
    if key in cache: return cache[key]
    TP = thermal_mod(); t0 = time.perf_counter(); calls = [0]
    thr = THR_ADOPT if mode == "adopt" else {o: 0.0 for o in TP.OPT}
    def ok(n):
        for opt in TP.OPT:
            r = TP.run_mc(fam, opt, 1, n, f, N, 20261112, device=device); calls[0] += 1
            if r["p05"] < thr[opt]: return False
        return True
    n0 = (229 if fam == "cold45" else 156) * f; lo, hi = max(4, int(0.6 * n0)), int(1.5 * n0) + 4
    while not ok(hi): hi = int(hi * 1.3) + 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ok(mid): hi = mid
        else: lo = mid
    m = mc_margins(fam, hi, f, N, device); calls[0] += 4
    out = dict(n=hi, margins=m, sec=time.perf_counter() - t0, mc_calls=calls[0]); cache[key] = out; return out
_MM = {}
def mass_model(fam, f, n_pan):
    if "m" not in _MM:
        import massmodel_p27 as MM; _MM["m"] = MM
    return _MM["m"].launch_mass(fam, f, n_pan, hold_kg=221.3 * n_pan / 229.0)
def mass_add(fam, f, n_pan, S):
    """lever mass costs (launch kg, nominal), same conventions as volume_levers_dp_T45.mass_delta; split-rack interface 25 kg per added cut is ASSUMED."""
    d = 0.0; notes = []
    n = S.get("fold", 4); dl = (n - 4) * 40 * f
    if dl: d += dl * V.HINGE_KG * LF
    if S.get("rmode") == "zfold": d += 264 * (n_pan / 229.0) * V.HINGE_KG * LF
    if S.get("roll"):
        arr_kg = 961.64 * f * (830.19 / 752.0 if fam == "hot97" else 1.0); d += (188000.0 * f / 124.0 - arr_kg) * LF
    b = S.get("bus", "mono")
    if b.startswith("split"): d += 25.0 * (int(b[5:]) - 1)
    if b == "wide":
        bz = 4.626; Veq = (bz - BUSZ0) * BX * BY; b2 = (1.4, 2.0, BUSZ0 + Veq / 2.8); area = lambda x: 2 * (x[0] * x[1] + x[0] * x[2] + x[1] * x[2])
        d += 0.20 * (600.0 * f + Veq * 400.0) * (area(b2) / area((BX, BY, bz)) - 1) * LF
    return d
def mass_hold(fam, f, n_pan, S):
    r = mass_model(fam, f, n_pan); return r["launch"] + 20.0 + mass_add(fam, f, n_pan, S), r
def struct_fcc(fam, f, n_pan, S, M_launch, mm, N):
    x = mm["f1"]; sm = x["structure_allocated_kg"] / x["primary_required_kg"] - 1.0
    holdf1 = 35.536 * (1.0 if fam == "cold45" else (2.9446 / RAD_L[fam]) ** 2)          # 7-station clamped hold-down f1 (CalculiX F4: 35.5 Hz cold panel); hot panel f ~ 1/L^2 (INFERENCE)
    n = S.get("fold", 4); Lb = 14.0 / n if not S.get("roll") else 14.0 / (2 if S["roll"] == "7" else 4)
    wing_idx = (26.86 / (26.86 * f * (830.19 / 752.0 if fam == "hot97" else 1.0))) ** 2     # deployed cantilever f1 index vs adopted ~ 1/L^2 (INFERENCE; wing width fixed at 14 m)
    rad_pf = n_pan * AP_FACE[fam] / 2 if False else n_pan * thermal_mod().AP[fam] / 2.0
    arr = 752.0 * f * (830.19 / 752.0 if fam == "hot97" else 1.0)
    bz = BUSZ0 + VEQ0 * (0.338 + 0.662 * f) / (BX * BY); bus_big = BY * bz; bus_skin = 2 * (BX * BY + BX * bz + BY * bz)
    return dict(primary_margin=sm, holddown_f1_Hz=holdf1, holddown_margin=holdf1 / 35.0 - 1, stow_block_freq_idx=((3.5 / Lb) ** 2 if not S.get("roll") else None),
                deployed_f1_idx=wing_idx, stack_axial_MN=max(N - 1, 0) * M_launch * 9.81 * 6.0 / 1e6,
                fcc=dict(mass_launch=M_launch, mass_ok=M_launch < 4000, rad_per_face=rad_pf, rad_both=2 * rad_pf, rad_ok_per_face=rad_pf < 200, rad_ok_both=2 * rad_pf < 200,
                         array=arr, array_ok=arr < 1500, bus_largest_face=bus_big, bus_skin=bus_skin, bus_ok_face=bus_big < 21, bus_ok_skin=bus_skin < 21))
def risk(S, fam, f, bay, arch, adapt):
    r = 0; k = []
    leaf = S.get("leaf", .012); r += RISK["leaf9"] if abs(leaf - .009) < 1e-6 else RISK["leaf6"] if leaf < .0085 else 0
    rp = S.get("rpitch", .02); r += RISK["rad14"] if abs(rp - .014) < 1e-6 else RISK["rad10"] if rp < .0125 else 0
    fo = S.get("fold", 4); r += RISK["fold3"] if fo == 3 else RISK["fold2"] if fo == 2 else 0
    if S.get("roll"): r += RISK["roll" + S["roll"]]
    rm = S.get("rmode", "stacks"); r += RISK.get(rm, 0) if rm != "stacks" else 0
    b = S.get("bus", "mono"); r += (int(b[5:]) - 1) * RISK["split"] if b.startswith("split") else 0
    r += RISK["rho800"] if S.get("rho", 400.0) > 500 else 0
    r += RISK["adapt15"] if abs(adapt - .15) < 1e-6 else RISK["adapt05"] if adapt < .1 else 0
    r += RISK["hot97"] if fam == "hot97" else 0; r += RISK["ext22"] if bay == "ext22" else 0; r += RISK["books"] if arch == "books" else 0
    return r
