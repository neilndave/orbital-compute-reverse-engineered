"""Oct 31 2026 ([] 'see what else can be done to fit more satellites by volume in Starship'): VOLUME-PACKING LEVERS on top of the adopted Aug envelope + split array wing.
Box CPU, geometry only (ESTIMATE; no dispenser, no loads, no hinge access). Reuses the skyline packer, envelope and rules of repack_stacks_T45.py / k31_packing_T45.py (1 cm grid, 0.30 m adapter, 0.05 m clearance).
Stage 1 (this file, --stage tables): for each lever (an item-set what-if) the (X, Y, H) table of slab footprints; --stage dp: layer dynamic programme over the 17.24 m fairing (layers of 1 to 6 identical satellites,
row arrangements inside the radius allowed at the layer top, adapter / gap / fairing profile as separate levers); results/knobs_T45/volume_levers_T45.json.
Every number is a what-if ESTIMATE; PROPOSALS only, the baseline is unchanged. Usage: python experiments/knobs/volume_levers_T45.py [--stage tables|dp|all] [--stacks stack_R5,stack_O5,ref]"""
import json, math, pathlib, sys, time, functools, itertools, argparse
import numpy as np
from multiprocessing import Pool
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "experiments/knobs"))
import repack_stacks_T45 as R   # noqa: E402   (packer + envelope)
OUT = ROOT / "results/knobs_T45"
GAP0, ADAPT0 = 0.05, 0.30
HINGE_LAUNCH_FACTOR = 48.5962 / 32.0     # launch kg per kg of added hinge hardware (chain_aug_split_T45_launch.json hinge_effect_kg / hinge_kg)
HINGE_KG = 0.4; HINGE_KG_LOW = 0.11      # per added fold line (SPLIT_WING_AUG_ENVELOPE_T45.md; Airbus DS NL datasheet / Caltech tape-spring hinge)
N_LEAVES = 20; PITCH_ARR0 = 0.012; ARRAY_WIDTH = 14.0; PITCH_RAD0 = 0.020; FOLD0 = 4
EXT_EXTRA = 22.0 - 17.24                 # 'extended payload volume up to 22 m' (Starship User's Guide); the profile above 17.24 m is NOT published -> ogive shifted up by this (ASSUMED)
V_EQ_DENSITY0 = 400.0                    # kg/m3 equipment bay bulk density (configs/bus.yaml, ESTIMATE)
BUS_Z0 = 2.296 + 2 * 0.05 + 0.10         # rack height + 2 x clearance + margin (bus_model.py): bz = BUS_Z0 + V_eq / (bx * by)

# ------------------------------------------------------------------ item-set levers (what-ifs, each with the mass it would cost, ESTIMATE where given)
def split_items(base):
    d = {"bus": [], "array": [], "radiator": []}
    for n, k, dims in base: d[k].append((n, k, tuple(dims)))
    return d

def make(base, **kw):
    """Return list of (name, kind, dims) for a what-if. kw: array_n (fold across width), array_pitch, array_roll (None|'7'|'3.5'), rad_pitch, rad_mode ('stacks'|'x2side'|'x2tall'|'x4side'|'zfold'),
    bus_mode ('mono'|'split2'|'ydim:<y>'|'wide'|'rho:<density>'), rack_f (1.0 | 0.5, ESTIMATE scaling)."""
    d = split_items(base)
    bus = d["bus"][0][2]; arr = d["array"]; rad = d["radiator"]
    bx, by, bz = bus
    items = []
    # ---- array
    n = kw.get("array_n", FOLD0); p = kw.get("array_pitch", PITCH_ARR0); roll = kw.get("array_roll")
    t0 = N_LEAVES * PITCH_ARR0 * FOLD0; L0 = ARRAY_WIDTH / FOLD0
    w0 = float(np.prod(arr[0][2])) / (L0 * t0)                  # leaf-length side of the stack (1.343 m R5; the same at all three stacks)
    f_arr = kw.get("rack_f", 1.0)
    w = w0 * f_arr                                              # half rack -> half the array area -> half the leaf length (ESTIMATE)
    if roll:
        # ROSA-class rolled blanket: ~40 kW/m3 stowed (Redwire flysheet, STATEMENT) vs our block; V per wing = P_wing / 40 kW/m3 (ESTIMATE); 2 hinged rolls of 7 m (iROSA has a mid hinge) or 4 rolls of 3.5 m; bounding box of a cylinder
        P_wing = 188.0 * f_arr / 2; Vw = P_wing / 40.0
        for i in range(len(arr)):
            pieces = 2 if roll == "7" else 4; L = ARRAY_WIDTH / pieces
            dia = math.sqrt(4 * (Vw / pieces) / (math.pi * L)) + 0.02
            for j in range(pieces): items.append((f"array_{i}_roll{j}", "array", (L, dia, dia)))
    else:
        L = ARRAY_WIDTH / n; t = N_LEAVES * p * n
        for i in range(len(arr)): items.append((f"array_{i}", "array", (L, w, t)))
    # ---- radiators
    rp = kw.get("rad_pitch", PITCH_RAD0); mode = kw.get("rad_mode", "stacks")
    nrad = len(rad) if kw.get("rack_f", 1.0) == 1.0 else int(round(len(rad) * kw["rack_f"]))
    a, b, c = sorted(rad[0][2]); a0, b0, c0 = rad[0][2]; thick = min(rad[0][2]); wide, long_ = sorted(rad[0][2])[1], max(rad[0][2])
    thick *= rp / PITCH_RAD0
    if mode == "stacks":
        for i in range(nrad): items.append((f"rad_{i}", "radiator", (wide, long_, thick)))
    elif mode == "x2side":
        for i in range(nrad // 2): items.append((f"rad_{i}", "radiator", (2 * wide + 0.01, long_, thick)))
        if nrad % 2: items.append(("rad_odd", "radiator", (wide, long_, thick)))
    elif mode == "x2tall":
        for i in range(nrad // 2): items.append((f"rad_{i}", "radiator", (wide, long_, 2 * thick)))
        if nrad % 2: items.append(("rad_odd", "radiator", (wide, long_, thick)))
    elif mode == "x4side":
        for i in range(nrad // 4): items.append((f"rad_{i}", "radiator", (4 * wide + 0.03, long_, thick)))
        for i in range(nrad % 4): items.append((f"rad_r{i}", "radiator", (wide, long_, thick)))
    elif mode == "zfold":    # each panel folded once along its 2.94 m length (z-fold): half the length, twice the stack thickness
        for i in range(nrad): items.append((f"rad_{i}", "radiator", (wide, long_ / 2 + 0.02, 2 * thick)))
    # ---- bus
    bm = kw.get("bus_mode", "mono"); Veq = (bz - BUS_Z0) * bx * by
    fV = kw.get("rack_f", 1.0)
    if fV != 1.0: Veq *= kw.get("veq_scale", 0.669)            # half rack: equipment volume scaled by the plain-baseline bus_excl_rack ratio 1,935 / 2,893 (t23_T45.json / chain_aug_split_T45.json), ESTIMATE
    if bm.startswith("rho:"): Veq *= V_EQ_DENSITY0 / float(bm[4:]); bm = "mono"
    if bm == "mono": items.append(("bus", "bus", (bx, by, BUS_Z0 + Veq / (bx * by))))
    elif bm == "split2": items += [("bus_rack", "bus", (bx, by, BUS_Z0)), ("bus_equip", "bus", (bx, by, Veq / (bx * by)))]
    elif bm.startswith("ydim:"):
        y = float(bm[5:]); items.append(("bus", "bus", (bx, y, BUS_Z0 + Veq / (bx * y))))
    elif bm == "wide": items.append(("bus", "bus", (1.4, by, BUS_Z0 + Veq / (1.4 * by))))
    return items

def hinge_delta_kg(**kw):
    """Launch kg (ESTIMATE, nominal 0.4 kg per added fold line, low case 0.11) relative to the adopted fold-4 wing. Negative = fewer lines."""
    n = kw.get("array_n", FOLD0)
    lines = (n - FOLD0) * N_LEAVES * 2          # added fold lines vs fold 4 (2 wings, 20 leaves each; 80 lines per 2 folds)
    ex = 0.0
    if kw.get("rad_mode") == "zfold": ex = 264 * 1.0  # one extra fold line per radiator panel; scaled below
    return lines, ex

# ------------------------------------------------------------------ lever table
def lever_list():
    L = []
    def add(i, grp, desc, cfg=None, **kw): L.append(dict(id=i, group=grp, desc=desc, kw=kw, cfg=cfg or {}))
    add("L0", "ref", "adopted: fold 4 (3.5 m blocks, 0.96 m), leaf pitch 12 mm, radiator pitch 20 mm, monolithic bus")
    # thickness
    for p, tag in ((0.009, "0.75"), (0.006, "0.5")): add(f"C_arr_p{int(p*1000)}", "thickness", f"array leaf pitch 12 -> {p*1000:.0f} mm (x{tag} block thickness)", array_pitch=p)
    for p in (0.014, 0.010): add(f"C_rad_p{int(p*1000)}", "thickness", f"radiator stack pitch 20 -> {p*1000:.0f} mm", rad_pitch=p)
    add("C_both_half", "thickness", "array pitch 6 mm and radiator pitch 10 mm (both x0.5)", array_pitch=0.006, rad_pitch=0.010)
    add("C_both_75", "thickness", "array pitch 9 mm and radiator pitch 14 mm", array_pitch=0.009, rad_pitch=0.014)
    add("C_roll7", "thickness", "array = 4 rolls of 7 m (ROSA-class 40 kW/m3, 2 hinged rolls per wing)", array_roll="7")
    add("C_roll35", "thickness", "array = 8 rolls of 3.5 m (ROSA-class 40 kW/m3)", array_roll="3.5")
    # fold lines
    for n in (2, 3, 6, 8): add(f"F_fold{n}", "folds", f"array fold across width {n} ({14/n:.2f} m x {N_LEAVES*0.012*n:.2f} m blocks; {abs(n-4)*40} lines {'more' if n>4 else 'fewer'})", array_n=n)
    # radiator arrangement
    add("R_x2side", "radiator", "radiator stacks merged 2:1 side by side (12 blocks 0.86 x 2.94 m)", rad_mode="x2side")
    add("R_x2tall", "radiator", "radiator stacks merged 2:1 stacked (0.43 x 2.94 x 0.4 m)", rad_mode="x2tall")
    add("R_x4side", "radiator", "radiator stacks merged 4:1 side by side (1.7 x 2.94 m)", rad_mode="x4side")
    add("R_zfold", "radiator", "radiator panel z-fold (each panel folded once along its 2.94 m): 0.43 x 1.49 x 0.40 m stacks", rad_mode="zfold")
    # bus
    add("B_rho600", "bus", "equipment bay density 400 -> 600 kg/m3 (bus 5.0 -> about 4.2 m)", bus_mode="rho:600")
    add("B_rho800", "bus", "equipment bay density 400 -> 800 kg/m3", bus_mode="rho:800")
    add("B_split2", "bus", "bus split into a rack module (0.7 x 2.0 x 2.5 m) and an equipment module", bus_mode="split2")
    add("B_y3", "bus", "bus width y 2.0 -> 3.0 m (same equipment volume), shorter bus", bus_mode="ydim:3.0")
    add("B_y4", "bus", "bus width y 2.0 -> 4.0 m (same equipment volume), shorter bus", bus_mode="ydim:4.0")
    add("B_wide", "bus", "bus thickness x 0.7 -> 1.4 m (same equipment volume), 1.4 x 2.0 x about 3.8 m", bus_mode="wide")
    # rack fraction
    add("G_half", "rack", "half rack satellite (94 kW): 12 radiator stacks, half array leaf length, equipment volume x0.669 (ESTIMATE scaling of the adopted items)", rack_f=0.5)
    # ---- combinations (stage 2 of the study; every part is a what-if above)
    A15 = dict(adapt=0.15); A05 = dict(adapt=0.05)
    add("K_a9_s15", "combo", "array pitch 9 mm + adapter 0.15 m", cfg=A15, array_pitch=0.009)
    add("K_a9_rho600_s15", "combo", "array pitch 9 mm + equipment density 600 + adapter 0.15 m", cfg=A15, array_pitch=0.009, bus_mode="rho:600")
    add("K_a6_s15", "combo", "array pitch 6 mm + adapter 0.15 m", cfg=A15, array_pitch=0.006)
    add("K_both75_rho600_s15", "combo", "array pitch 9 + radiator pitch 14 + density 600 + adapter 0.15 m", cfg=A15, array_pitch=0.009, rad_pitch=0.014, bus_mode="rho:600")
    add("K_fold3_rho600_s15", "combo", "fold 3 (4.67 x 0.72 m blocks, slot-compatible) + density 600 + adapter 0.15 m", cfg=A15, array_n=3, bus_mode="rho:600")
    add("K_fold3_rho800_s05", "combo", "fold 3 + density 800 + adapter 0.05 m", cfg=A05, array_n=3, bus_mode="rho:800")
    add("K_fold3_a9_s15", "combo", "fold 3 with leaf pitch 9 mm (0.54 m blocks) + adapter 0.15 m (no density change)", cfg=A15, array_n=3, array_pitch=0.009, bus_mode="rho:600")
    add("K_roll35_rho600_s15", "combo", "8 rolls of 3.5 m + density 600 + adapter 0.15 m", cfg=A15, array_roll="3.5", bus_mode="rho:600")
    add("K_a9_s15_ext22", "combo", "array pitch 9 mm + adapter 0.15 m + 22 m payload volume", cfg=dict(adapt=0.15, pmode="ext22"), array_pitch=0.009)
    add("K_all_half_rho800_s05", "combo", "both pitches x0.5 + density 800 + adapter 0.05 m (volume-first limit case)", cfg=A05, array_pitch=0.006, rad_pitch=0.010, bus_mode="rho:800")
    add("K_a9_split2_s15", "combo", "array pitch 9 mm + bus split into two modules + adapter 0.15 m", cfg=A15, array_pitch=0.009, bus_mode="split2")
    return L

# ------------------------------------------------------------------ packing tables (pool)
def cand_grid(step=0.25):
    rmax = R.r_allowed(8.0); c = set()
    xs = [1.5 + step * i for i in range(int(round((7.75 - 1.5) / step)) + 1)] + [7.05, 7.1, 7.35, 6.05, 6.55, 5.05, 5.55, 5.3, 3.6]
    for X in xs:
        ys = [0.75 + step * j for j in range(int(round((X - 0.75) / step)) + 1)] + [X / 2]
        for Y in ys:
            if Y <= X + 1e-9 and math.hypot(X, Y) / 2 <= rmax + 1e-9: c.add((round(X, 3), round(Y, 3)))
    return sorted(c)

def table(args):
    stack, lid, its = args
    R.items = its; R._PC = {}; rows = []
    for X, Y in cand_grid():
        r = R._pack(X, Y, False)
        if r is not None: rows.append((X, Y, r[0]))
    return stack, lid, rows

# ------------------------------------------------------------------ layer DP
@functools.lru_cache(None)
def layer_cr(m, X, Y, gap):
    """Smallest corner radius of m identical X x Y rectangles arranged in up to 3 centred rows (counts non-increasing, each <= 3), either orientation."""
    best = None
    for (a, b) in ((X, Y), (Y, X)):
        for k in (1, 2, 3):
            for part in itertools.product(range(1, 4), repeat=k):
                if sum(part) != m or list(part) != sorted(part, reverse=True): continue
                Hh = k * b + (k - 1) * gap; cr = 0.0
                for j, nr in enumerate(part):
                    wd = nr * a + (nr - 1) * gap; y0 = -Hh / 2 + j * (b + gap); y1 = y0 + b
                    cr = max(cr, math.hypot(wd / 2, max(abs(y0), abs(y1))))
                if best is None or cr < best: best = cr
    return best

def profile(mode):
    r8 = R.r_allowed(8.0)
    if mode == "std": return (lambda z: R.r_allowed(z)), R.ZTOP
    if mode == "cyl": return (lambda z: r8), R.ZTOP
    if mode == "ext22": return (lambda z: r8 if z <= 8.0 + EXT_EXTRA else R.r_allowed(z - EXT_EXTRA)) if False else (lambda z: R.r_allowed(z) if z <= 8.0 else (r8 if z <= 8.0 + EXT_EXTRA else R.r_allowed(z - EXT_EXTRA))), 22.0
    raise ValueError(mode)

def dp(rows, mmax=6, gap=GAP0, adapt=ADAPT0, pmode="std"):
    rfun, ztop = profile(pmode)
    cands = []
    for X, Y, H in rows:
        for m in range(1, mmax + 1):
            cr = layer_cr(m, X, Y, gap)
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

def slot_check(its, sh=0.8, sw=7.3):
    bad = []
    for n, k, d in its:
        s = sorted(d)
        if not (s[0] <= sh and s[1] <= sw): bad.append(n)
    return len(bad) == 0, sorted({b.split("_")[0] for b in bad})

# ------------------------------------------------------------------ main
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", default="all"); ap.add_argument("--stacks", default="stack_R5,stack_O5"); ap.add_argument("--levers", default="")
    a = ap.parse_args(); t0 = time.time()
    ch = json.load(open(OUT / "chain_aug_split_T45.json"))
    tab_f = OUT / "volume_levers_tables_T45.json"; tabs = json.load(open(tab_f)) if tab_f.exists() else {}
    levers = lever_list()
    if a.levers: levers = [l for l in levers if l["id"] in a.levers.split(",")]
    bases = {}
    for st in ("ref", "stack_R5", "stack_O5"):
        row = ch[st]["reopt"]
        bases[st] = [(i["name"], i["kind"], tuple((np.array(i["hi_mm"]) - np.array(i["lo_mm"])) / 1e3)) for i in row["stowed_items"]]
    if a.stage in ("tables", "all"):
        tasks = []
        for st in a.stacks.split(","):
            for lv in levers:
                key = f"{st}|{lv['id']}"
                if key in tabs: continue
                its = make(bases[st], **lv["kw"])
                if lv["id"].startswith("G_half") and st == "stack_O5": pass
                tasks.append((st, lv["id"], its))
        print(len(tasks), "tasks", flush=True)
        with Pool(8) as p:
            for st, lid, rows in p.imap_unordered(table, tasks, chunksize=1):
                tabs[f"{st}|{lid}"] = rows; json.dump(tabs, open(tab_f, "w"))
                print(st, lid, len(rows), round(time.time() - t0), "s", flush=True)
    print("done", round(time.time() - t0), "s")
