"""Chunk 2 / T27 (Oct 30 2026): the P19 stowed-layout repack (experiments/cad3d/repack_stowed.py, same packer, same envelope, same rules) applied to the stowed item boxes of each stack
(ref, R4, O4, R5, O5; boxes dumped by experiments/knobs/run_chain_stacks_T45.py at the FULL grid, best radiator-stack column count). Box CPU, geometry only; ESTIMATE where used as a launch count
(no dispenser, no loads, no deploy-hinge access). Reads results/knobs_T45/chain_stacks_T45.json; writes results/knobs_T45/repack_stacks_T45.json (new).
Usage: python experiments/knobs/repack_stacks_T45.py [stack,...]"""
import json, math, pathlib, sys, functools
import numpy as np
from scipy.ndimage import maximum_filter
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from rack_two_skies import assembly3d as A   # noqa: E402
_PC = {}
items = []
RES = 0.01
prm = A.load_params(); prof = A.envelope_profile(prm); CLR = prm["launch_vehicle.clearance_m"]
def cells(x): return int(math.ceil(round(x / RES, 6)))
def orients(dims, flat):
    a, b, c = dims
    if flat:   # thin axis (smallest dimension) stays vertical
        thin = min(dims); rest = [x for x in dims]; rest.remove(thin)
        return {(rest[0], rest[1], thin), (rest[1], rest[0], thin)}
    return {(x, y, z) for x, y, z in ((a, b, c), (b, a, c), (a, c, b), (c, a, b), (b, c, a), (c, b, a))}

def pack(X, Y, flat):
    key = (X, Y, flat)
    if key in _PC: return _PC[key]
    r = _pack(X, Y, flat); _PC[key] = r; return r

def _pack(X, Y, flat):
    """Return (H_m, placed list) for footprint X x Y m, or None if an item cannot fit the footprint."""
    nx, ny = cells(X), cells(Y); h = np.zeros((nx, ny)); placed = []
    for name, kind, dims in sorted(items, key=lambda t: -t[2][0] * t[2][1] * t[2][2]):
        best = None
        for (a, b, c) in orients(dims, flat and kind != "bus"):
            ca, cb, cc = cells(a + 0.01), cells(b + 0.01), cells(c + 0.01)
            if ca > nx or cb > ny: continue
            m = maximum_filter(h, size=(ca, cb), mode="constant", cval=0.0)
            base = m[ca // 2: ca // 2 + nx - ca + 1, cb // 2: cb // 2 + ny - cb + 1]
            top = base + cc
            i, j = np.unravel_index(np.argmin(top + 1e-9 * (np.arange(top.shape[0])[:, None] + np.arange(top.shape[1])[None, :])), top.shape)
            cand = (float(top[i, j]), float(base[i, j]), i, j, ca, cb, cc, (a, b, c))
            if best is None or cand[:2] < best[:2]: best = cand
        if best is None: return None
        t, bz, i, j, ca, cb, cc, o = best
        h[i:i + ca, j:j + cb] = t; placed.append(dict(name=name, kind=kind, orient_m=o, lo_m=(i * RES, j * RES, bz * RES)))
    return float(h.max()) * RES, placed

def r_allowed(z): return A.envelope_radius(z, prof) - CLR
ZTOP = prof[-1][0]
def count(a, flat):
    """Stack slabs along the axis; each takes the widest footprint (step 0.05 m) of aspect a whose corner is inside the radius allowed at its top."""
    z = 0.3; seq = []
    while True:
        ok = None
        Xmax = 2 * r_allowed(8.0) * a / math.sqrt(1 + a * a)
        for X in np.arange(math.floor(Xmax * 20) / 20, 0.5, -0.05):
            Y = X / a; r = pack(round(float(X), 2), round(float(Y), 2), flat)
            if r is None: break      # smaller footprints cannot hold the longest item either
            H = r[0]
            if z + H <= ZTOP and math.hypot(X, Y) / 2 <= r_allowed(z + H):
                ok = (float(X), float(Y), H); break
        if ok is None: break
        seq.append(dict(X=ok[0], Y=ok[1], H=ok[2], z0=z, z1=z + ok[2], corner_r_m=math.hypot(ok[0], ok[1]) / 2)); z += ok[2] + 0.05 + 0.30
    return seq


def run_one(its):
    global items, _PC
    items = its; _PC = {}
    V = sum(a * b * c for _, _, (a, b, c) in items)
    res = dict(V_items_m3=V, n_items=len(items), aspects={})
    for a in (1.0, 2.0, 4.0):
        Xmax = 2 * r_allowed(8.0) * a / math.sqrt(1 + a * a)
        for flat in (False, True):
            X = math.floor(Xmax * 20) / 20; Y = round(X / a, 3)
            r = pack(round(X, 2), round(Y, 2), flat); seq = count(a, flat)
            res["aspects"][f"AR{a:g}_{'flat' if flat else 'free'}"] = dict(aspect=a, flat=flat, X_m=X, Y_m=Y, H_m=None if r is None else r[0], fits_footprint=r is not None,
                efficiency=None if r is None else V / (X * Y * r[0]), n_in_17p24=len(seq), sats=seq)
    return res

if __name__ == "__main__":
    ch = json.load(open(ROOT / "results/knobs_T45/chain_stacks_T45.json"))
    f = ROOT / "results/knobs_T45/repack_stacks_T45.json"; out = json.load(open(f)) if f.exists() else {}
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(ch)
    for nm in names:
        if nm in out: continue
        row = ch[nm]["reopt"] if ch[nm].get("reopt", {}).get("feasible") else ch[nm]["as_saved"]   # the re-optimised row only if it passes min cons >= -1e-6 (stack_R5 re-opt misses by 1.5e-8: its as-saved row is used)
        its = [(it["name"], it["kind"], tuple((np.array(it["hi_mm"]) - np.array(it["lo_mm"])) / 1e3)) for it in row["stowed_items"]]
        out[nm] = run_one(its); out[nm]["source"] = "re-optimised full grid" if row is ch[nm].get("reopt") else "as saved, full grid"
        print(nm, "items", len(its), "V", round(out[nm]["V_items_m3"], 3), {k: (v["n_in_17p24"], None if v["H_m"] is None else round(v["H_m"], 2)) for k, v in out[nm]["aspects"].items()}, flush=True)
        json.dump(out, open(f, "w"), indent=1, default=float)
