# t436: packing loop driver. Repo packer (p27.table_rows + dp2, unchanged) on a lever-parametrised replica item model. Box CPU. ESTIMATE.
# usage: t436_loop.py <passname> <json list of configs> ; appends to results/t436/passes.jsonl
import sys, os, json, math, time, pathlib
from multiprocessing import Pool
REPO = "vendor/same_rack"; sys.path[:0] = [f"{REPO}/experiments/parity27", f"{REPO}/experiments/knobs", f"{REPO}/src"]
HERE = pathlib.Path(__file__).resolve().parent; PP = HERE.parent / "gtc_params"; OUT = HERE / os.environ.get("T436_OUT", "results/t438")
PW, PL = 0.3634175776637853, 2.9445579551660426
RHO_RACK0 = 1814.0 / (0.6 * 1.2 * 2.296)      # baseline rack kg over its 0.6x1.2x2.296 m envelope (repo numbers; INFERENCE) = ~1097 kg/m3
LINES = json.load(open(HERE.parent / "results/t434_region.json"))["points"]
def items_for(p27, pid, S):
    j = json.load(open(PP / f"point_{pid}.json")); P = j["result"]["P_IT_peak_kW"]; npan = j["geometry_derived"]["radiator"]["n_panels"]; Aarr = j["areas"]["A_arr_m2"]
    f = P / 188.0; its = []; n = S.get("fold", 4); p = S.get("leaf", 0.009); w = Aarr / (2 * 14.0 * 20)
    if S.get("roll_kw_m3"):      # rolled blanket (ROSA-like): stowed volume = array kW / (kW per m3); 2 pieces per wing
        pieces = S.get("pieces", 2); L = 14.0 / pieces; Vw = P / 2 / S["roll_kw_m3"]
        dia = math.sqrt(4 * (Vw / pieces) / (math.pi * L)) + 0.02
        for i in range(2):
            for k in range(pieces): its.append((f"array_{i}_r{k}", "array", (L, dia, dia)))
    else:
        for i in range(2): its.append((f"array_{i}", "array", (14.0 / n, w, 20 * p * n)))
    ns = max(1, round(npan / (229 / 24.0))); ns = S.get("n_stacks", ns); rp = S.get("rpitch", 0.02); thick = (npan / ns - 1.0) * rp + 0.003
    its += [(f"rad_{i}", "radiator", (PW, PL, thick)) for i in range(ns)]
    Veq = p27.VEQ0 * (0.338 + 0.662 * f) * (400.0 / S.get("rho", 400.0)); bm = S.get("bus", "mono")
    if bm == "mono": its.append(("bus", "bus", (p27.BX, p27.BY, p27.BUSZ0 + Veq / (p27.BX * p27.BY))))
    else:   # 'rackeq': compute rack as its own small box at rack density (replica rack kg, C2 = conservative), equipment slab separate
        rk = LINES[S.get("rackline", "Jun8|C1" if pid.startswith("J8") else "Aug4|C1")]["lines"]["rack"]   # t438: default = the point being packed (was C2 in t436/t436b)
        Vr = rk / S.get("rho_rack", RHO_RACK0); rh = Vr / (0.6 * 1.2)
        if S.get("rackform", "tall") == "tall": its.append(("rack", "bus", (0.6, 1.2, rh))); its.append(("equip", "bus", (p27.BX, p27.BY, Veq / (p27.BX * p27.BY) + 0.2)))
        else: its.append(("busflat", "bus", (p27.BX, p27.BY, Veq / (p27.BX * p27.BY) + 0.2 + Vr / (p27.BX * p27.BY))))   # rack laid flat inside the equipment slab footprint (t438 form-factor lever)
    return its, ns, thick
def job(a):
    name, pid, S = a; sys.argv = ["x"]
    import p27
    t0 = time.time(); its, ns, thick = items_for(p27, pid, S); step = S.get("step", 0.25); rows = p27.table_rows(its, step); res = {}
    for arch in S.get("archs", ["layers", "stack1", "books"]):
        n, seq = p27.dp2(rows, adapt=S.get("adapt", 0.15), gap=S.get("gap", 0.05), pmode=S.get("pmode", "std"), **p27.ARCH[arch]); res[arch] = dict(n=n, seq=seq)
    vol = sum(a * b * c for _, _, (a, b, c) in its)
    return dict(pass_=name, id=pid, S=S, n_stacks=ns, item_vol_m3=round(vol, 3), items=[(k, kd, [round(x, 3) for x in d]) for k, kd, d in its], res=res, secs=round(time.time() - t0, 1))
if __name__ == "__main__":
    pname = sys.argv[1]; cfgs = json.loads(sys.argv[2]); jobs = []
    for c in cfgs:
        for pid in c.get("ids", ["J8_C1", "A4_C1"]): jobs.append((c["tag"] if "tag" in c else pname, pid, {k: v for k, v in c.items() if k not in ("ids", "tag")}))
    with Pool(int(os.environ.get("NW", "2"))) as pool:
        for r in pool.imap_unordered(job, jobs):
            print(r["pass_"], r["id"], {k: v["n"] for k, v in r["res"].items()}, "vol", r["item_vol_m3"], "S", r["S"], flush=True)
            open(OUT / "passes.jsonl", "a").write(json.dumps(r) + "\n")
