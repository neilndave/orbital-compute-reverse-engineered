#!/usr/bin/env python3
"""AI1 replica GB10 runner. Chunked, atomic, resumable, pausable.
  python runner.py --profile full|tiny [--device auto|cpu|cuda] [--root DIR]
Results: <root>/results/<chunk>.json (written atomically; a finished chunk is skipped on rerun).  PAUSE: `touch <root>/PAUSE` -> stops at the next chunk boundary and exits (GPU freed).
Thermal gate: before every GPU chunk, if hw/sw thermal slowdown is active or GPU temp >= 85 C it sleeps ~5 min (PAUSE still honoured) and logs a thermal_pause row.
Metrics: <root>/metrics/metrics.csv + summary.json (see ai1_metrics.py)."""
import os, sys, json, time, math, zlib, argparse, fcntl, signal, itertools, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--profile", default="full"); ap.add_argument("--device", default="auto"); ap.add_argument("--root", default=HERE); ap.add_argument("--max-chunks", type=int, default=0)
ap.add_argument("--phases", default="")
args = ap.parse_args(); ROOT = os.path.abspath(args.root); PROF = args.profile
if args.device == "cpu": os.environ["CUDA_VISIBLE_DEVICES"] = ""   # must be set before warp is imported
import ai1_specs as S, ai1_metrics as MT
import ai1_model as M
import warp as wp
for d in ("results", "metrics", "logs", "state"): os.makedirs(os.path.join(ROOT, d), exist_ok=True)
RES, MET, ST = (os.path.join(ROOT, x) for x in ("results", "metrics", "state")); PAUSE = os.path.join(ROOT, "PAUSE")
GPU = M.get_devices(); DEV = GPU if (GPU and args.device in ("auto", "cuda")) else "cpu"
USE_GPU = DEV.startswith("cuda")
THERMAL_TEMP = float(os.environ.get("AI1_THERMAL_TEMP_C", 85)); THERMAL_PAUSE_S = float(os.environ.get("AI1_THERMAL_PAUSE_S", 300))
FAKE = os.path.join(ST, "FAKE_GPU_TEMP")      # test hook: file containing a temperature in C
stop_flag = {"stop": False}
signal.signal(signal.SIGTERM, lambda *a: stop_flag.update(stop=True)); signal.signal(signal.SIGINT, lambda *a: stop_flag.update(stop=True))
def log(*a):
    print(MT.now_pt(), *a, flush=True)
def jdump(path, obj):
    tmp = path + f".tmp{os.getpid()}"
    with open(tmp, "w") as f: json.dump(obj, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
def done(cid): return os.path.exists(os.path.join(RES, cid + ".json"))
def seed_of(cid): return zlib.crc32(cid.encode()) & 0x7FFFFFFF
# ------------------------------------------------------------------ profile
FULL = dict(nx=320, ny=8, tb=(320.0, 10.0, 13), ee=(0.60, 0.05, 9), ts=(150.0, 25.0, 5), N=4_000_000, K=3, Nsz=1_000_000, sz_iter=14, bench_N=2_000_000, pack_N=2_000_000, pack_K=5, big=(1280, 32), nbig=2, small_solves=12)
TINY = dict(nx=40, ny=4, tb=(340.0, 40.0, 3), ee=(0.60, 0.20, 3), ts=(150.0, 50.0, 3), N=20_000, K=1, Nsz=20_000, sz_iter=6, bench_N=20_000, pack_N=20_000, pack_K=1, big=(160, 8), nbig=1, small_solves=2)
P = FULL if PROF == "full" else TINY
grid = lambda t: [t[0] + t[1] * i for i in range(t[2])]
TB, EE, TS = grid(P["tb"]), grid(P["ee"]), grid(P["ts"])
BUILDS = [("J8_110", 150e3, 120e3, 110.0), ("A4_178.6", 250e3, 175e3, 178.6), ("A4_160", 250e3, 175e3, 160.0), ("A4_110", 250e3, 175e3, 110.0)]
_bj = os.environ.get("GTC_BUILDS_JSON")   # t434: replica override (id, peak W, avg W, face area m2); the original four builds are kept above for reference
if _bj: BUILDS = [tuple(x) for x in json.load(open(_bj))["builds"]]
OPTICS = [("e95F100", 0.95, 1.00), ("e92F99", 0.92, 0.99), ("e92F95", 0.92, 0.95), ("e90F85", 0.90, 0.85)]
DESIGNS = list(S.FIN_DESIGNS.keys())
if PROF == "tiny": BUILDS = BUILDS[:2]; OPTICS = OPTICS[:2]; DESIGNS = DESIGNS[:1]
BASE = dict(sigma_pt=0.0, fg=0.0, dT0=20.0, pairing=0.0, leak=False, blk=0.0092)
SENS = {"pt1": dict(sigma_pt=1.0), "pt2": dict(sigma_pt=2.0), "pt3": dict(sigma_pt=3.0), "fg1_nonyaw": dict(fg=1.0), "pt2_fg1": dict(sigma_pt=2.0, fg=1.0), "dT10": dict(dT0=10.0), "dT15": dict(dT0=15.0), "dT30": dict(dT0=30.0),
        "pair1": dict(pairing=1.0), "leak": dict(leak=True), "blk3pct": dict(blk=0.03)}
if PROF == "tiny": SENS = {k: SENS[k] for k in ("pt2", "leak")}
# ------------------------------------------------------------------ chunk kinds
def tab_path(des): return os.path.join(RES, f"table_{des}.json")
def load_table(des):
    p = tab_path(des)
    if os.path.exists(p): return json.load(open(p))
    rows = []
    for Tb in TB:
        r = json.load(open(os.path.join(RES, f"fin_{des}_Tb{int(Tb)}.json"))); rows.append(r["eta_cell"])
    eta = np.array(rows).reshape(-1).tolist()      # [Tb][ee][Ts]
    tbl = dict(id=des, tb0=P["tb"][0], dtb=P["tb"][1], ntb=P["tb"][2], ee0=P["ee"][0], dee=P["ee"][1], nee=P["ee"][2], ts0=P["ts"][0], dts=P["ts"][1], nts=P["ts"][2], eta=eta, profile=PROF)
    jdump(p, tbl); return tbl
def chunk_fin(prm):
    des = S.FIN_DESIGNS[prm["design"]]; out = np.zeros((len(EE), len(TS))); ncg = 0; worst = 0.0
    for i, ee in enumerate(EE):
        for j, ts in enumerate(TS):
            e, n, w, res = M.fin_eta(des, prm["Tb"], ee, ts, DEV, nx=P["nx"], ny=P["ny"]); out[i, j] = M.eta_cell(e, des); ncg += n; worst = max(worst, res)
    return dict(design=prm["design"], Tb=prm["Tb"], eta_cell=out.tolist(), n_cg_total=ncg, worst_residual=worst, nx=P["nx"], ny=P["ny"], label="ESTIMATE (Warp fin solver float64; geometry ASSUMED)"), len(EE) * len(TS), "fin solves"
def chunk_validate(prm):
    des = S.FIN_DESIGNS["F1_L60_t0p8"]; rows = []; worst = 0.0
    for Tb, ee, ts in ((370.0, 0.9, 200.0), (400.0, 0.95, 150.0), (330.0, 0.7, 250.0), (420.0, 0.8, 200.0)):
        e, n, w, res = M.fin_eta(des, Tb, ee, ts, DEV, nx=P["nx"], ny=P["ny"]); ref = M.fin_1d_reference(des, Tb, ee, ts); rel = abs(e - ref) / ref; worst = max(worst, rel)
        rows.append(dict(Tb=Tb, ee=ee, Ts=ts, eta_warp=e, eta_1d_scipy=ref, rel_err=rel, wall_s=w))
    conv = []
    for nx in ([20, 40, 80, 160, 320, 640] if PROF == "full" else [20, 40]):
        e, n, w, res = M.fin_eta(des, 370.0, 0.9, 200.0, DEV, nx=nx, ny=4); conv.append(dict(nx=nx, eta=e, wall_s=w))
    return dict(points=rows, worst_rel_err_vs_1d=worst, mesh_convergence=conv, label="ESTIMATE (independent 1-D check)"), len(rows) + len(conv), "fin solves"
def pct_hist(x, lo=280.0, hi=440.0, nb=320):
    h, _ = np.histogram(x, bins=nb, range=(lo, hi)); return h.tolist()
def case_prm(build, load, optics, extra):
    b = next(x for x in BUILDS if x[0] == build); o = next(x for x in OPTICS if x[0] == optics)
    c = dict(BASE); c.update(extra or {}); c.update(P0=b[1] if load == "peak" else b[2], A=b[3], eps0=o[1], F0=o[2]); return c
def chunk_mc(prm):
    tbl = load_table(prm["design"]); c = case_prm(prm["build"], prm["load"], prm["optics"], prm.get("extra")); N = P["N"]
    T, q, ee = M.run_mc(tbl, c, N, seed_of(prm["id"]), DEV)
    return dict(case=prm["case"], N=N, hist=pct_hist(T), mean=float(T.mean()), std=float(T.std()), q_abs_mean=float(q.mean()), ee_mean=float(ee.mean()), frac_gt_370=float((T > S.LIMIT_SUPPLY_K).mean()), frac_gt_343=float((T > S.LIMIT_70C_K).mean()),
                p=dict(zip(("p01", "p05", "p50", "p95", "p99"), np.percentile(T, (1, 5, 50, 95, 99)).tolist())), label="ESTIMATE (MC of required coolant SUPPLY temperature, K; flat-strip radiator model ASSUMED)"), N, "draws"
def chunk_size(prm):
    tbl = load_table(prm["design"]); c = case_prm(prm["build"], prm["load"], prm["optics"], None); lim = prm["limit"]; qq = prm["q"]; N = P["Nsz"]; seed = seed_of(prm["id"])
    def f(sc):
        cc = dict(c); cc["A"] = c["A"] * sc; T, _, _ = M.run_mc(tbl, cc, N, seed, DEV); return float(np.percentile(T, qq)) - lim     # want <= 0
    lo, hi = 0.3, 6.0
    if f(hi) > 0: return dict(case=prm["case"], note="not reachable below 6x", A_needed_m2=None), N, "draws"
    for _ in range(P["sz_iter"]):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0: lo = mid
        else: hi = mid
    A = c["A"] * hi
    return dict(case=prm["case"], limit_K=lim, percentile=qq, A_stated_m2=c["A"], A_needed_m2=A, scale=hi, fin_areal_kg_m2=S.fin_areal_mass_planform(S.FIN_DESIGNS[prm["design"]]), radiator_fin_tube_fluid_kg=A * S.fin_areal_mass_planform(S.FIN_DESIGNS[prm["design"]]),
                label="ESTIMATE (area at which P(T_supply <= limit) = 95 %; fin+tube+fluid mass only, headers/mounts/shield not included)"), N * (P["sz_iter"] + 1), "draws"
def chunk_kernelcheck(prm):
    tbl = load_table(DESIGNS[0]); out = []
    for c in (case_prm(BUILDS[1][0], "peak", "e92F99", None), case_prm(BUILDS[0][0], "peak", OPTICS[-1][0], dict(fg=1.0, pairing=1.0, leak=True))):
        T, q, ee = M.run_mc(tbl, c, 8, 1, DEV, det=True); h = M.host_treq_det(tbl, c); out.append(dict(kernel_T=float(T[0]), host_T=h[0], diff_K=float(T[0] - h[0]), q_kernel=float(q[0]), q_host=float(h[1])))
    return dict(rows=out, worst_abs_diff_K=max(abs(r["diff_K"]) for r in out), label="ESTIMATE (kernel vs host reference, deterministic draw)"), 16, "draws"
def chunk_bench(prm):
    dev = prm["dev"]; kind = prm["kind"]
    if kind == "fin_small":
        d = S.FIN_DESIGNS["F1_L60_t0p8"]; t0 = time.time(); n = P["small_solves"]
        for i in range(n): M.fin_eta(d, 360.0 + 3 * i, 0.9, 200.0, dev, nx=P["nx"], ny=P["ny"])
        return dict(kind=kind, device=dev, solves=n, wall_s=time.time() - t0, grid=[P["nx"], P["ny"]]), n, "fin solves"
    if kind == "fin_big":
        d = S.FIN_DESIGNS["F1_L60_t0p8"]; t0 = time.time(); n = P["nbig"]
        for i in range(n): M.fin_eta(d, 360.0 + 5 * i, 0.9, 200.0, dev, nx=P["big"][0], ny=P["big"][1])
        return dict(kind=kind, device=dev, solves=n, wall_s=time.time() - t0, grid=list(P["big"])), n, "fin solves"
    if kind == "mc":
        tbl = load_table(DESIGNS[0]); c = case_prm(BUILDS[1][0], "peak", "e92F99", None); N = P["bench_N"]; t0 = time.time(); T, q, e = M.run_mc(tbl, c, N, 4242, dev); w = time.time() - t0
        return dict(kind=kind, device=dev, draws=N, wall_s=w, p50=float(np.median(T))), N, "draws"
def chunk_pack(prm):
    rng = np.random.default_rng(seed_of(prm["id"])); N = P["pack_N"]
    cases = {"Aug4_budget_3333kg": 3333.0, "FCC_cap_4000kg": 4000.0, "O5_stack_launch_6279kg": 6279.0, "Jun8_budget_2143kg": 2143.0, "Jun8_repo_masses_4513kg": 4513.0}; out = {}
    pay = rng.choice([100e3, 114e3], N); V = rng.uniform(614.0, 1100.0, N); eta = rng.uniform(0.25, 0.50, N); rho = rng.uniform(591.0, 1000.0, N)
    for k, m in cases.items():
        nm = np.floor(pay / m); nv = np.floor(eta * V / (m / rho)); n = np.minimum(nm, nv)
        out[k] = dict(p05=float(np.percentile(n, 5)), p50=float(np.percentile(n, 50)), p95=float(np.percentile(n, 95)), frac_volume_bound=float((nv < nm).mean()), mass_only_p50=float(np.median(nm)))
    return dict(N=N, cases=out, ranges=dict(payload_t=[100, 114], bay_m3=[614, 1100], packing=[0.25, 0.5], stowed_density_kg_m3=[591, 1000]), label="ESTIMATE (CPU numpy MC; ranges ASSUMED/third-party; real stow = CAD repack, not done here)"), N, "draws"
KINDS = dict(fin=chunk_fin, validate=chunk_validate, mc=chunk_mc, size=chunk_size, kcheck=chunk_kernelcheck, bench=chunk_bench, pack=chunk_pack)
# ------------------------------------------------------------------ task list
def tasks():
    T = []
    T.append(dict(id="validate_fin", phase="G0_validate", kind="validate"))
    for des in DESIGNS:
        for Tb in TB: T.append(dict(id=f"fin_{des}_Tb{int(Tb)}", phase="G1_fin_table", kind="fin", design=des, Tb=Tb))
    T.append(dict(id="kernel_check", phase="G0_validate", kind="kcheck"))
    for kind in ("fin_small", "fin_big", "mc"):
        for dev in (["cpu"] + ([GPU] if USE_GPU else [])): T.append(dict(id=f"bench_{kind}_{dev.split(':')[0]}", phase="G0_bench", kind="bench", dev=dev, bkind=kind))
    for b in BUILDS:
        for load in ("peak", "avg"):
            for des in DESIGNS:
                for o in OPTICS:
                    for k in range(P["K"]):
                        cid = f"mc_{b[0]}_{load}_{des}_{o[0]}_r{k}"; T.append(dict(id=cid, phase="G2_mc_base", kind="mc", case=f"{b[0]}|{load}|{des}|{o[0]}|base", build=b[0], load=load, design=des, optics=o[0], extra=None))
    for b in BUILDS[:2]:
        for sk, ex in SENS.items():
            for k in range(P["K"]):
                cid = f"mc_{b[0]}_peak_{DESIGNS[0]}_e92F99_{sk}_r{k}"; T.append(dict(id=cid, phase="G3_mc_sens", kind="mc", case=f"{b[0]}|peak|{DESIGNS[0]}|e92F99|{sk}", build=b[0], load="peak", design=DESIGNS[0], optics="e92F99", extra=ex))
    for lim, lt in ((S.LIMIT_SUPPLY_K, "370K"), (S.LIMIT_70C_K, "343K")):
        for b in BUILDS[:2]:
            for load in ("peak", "avg"):
                for des in DESIGNS:
                    for o in [x for x in OPTICS if x[0] in ("e92F99", "e90F85")]:
                        cid = f"size_{b[0]}_{load}_{des}_{o[0]}_{lt}"; T.append(dict(id=cid, phase="G4_area_sizing", kind="size", case=f"{b[0]}|{load}|{des}|{o[0]}|{lt}", build=b[0], load=load, design=des, optics=o[0], limit=lim, q=95.0))
    for k in range(P["pack_K"]): T.append(dict(id=f"pack_r{k}", phase="G5_packing_mc", kind="pack"))
    if args.phases: keep = args.phases.split(","); T = [t for t in T if t["phase"].split("_")[0] in keep]
    for t in T:
        if t["kind"] == "bench": t["kind"] = "bench"; t["kind_b"] = t.pop("bkind"); t["kind"] = "bench"
    return T
def run_chunk(t):
    prm = dict(t)
    if t["kind"] == "bench": prm["kind"] = t["kind_b"]
    fn = KINDS[t["kind"]]; return fn(prm)
# ------------------------------------------------------------------ pause / thermal
def user_pause_requested(): return os.path.exists(PAUSE) or stop_flag["stop"]
def thermal_gate():
    """returns True if the run should stop (PAUSE or SIGTERM during a thermal wait)."""
    if not USE_GPU: 
        if not os.path.exists(FAKE): return False
    while True:
        if user_pause_requested(): return True
        g = MT.read_gpu()
        if os.path.exists(FAKE):
            try: g = dict(temp=float(open(FAKE).read().strip()), hw=0, swt=0, hwt=0)
            except Exception: pass
        if g is None: return False
        hot = g["temp"] >= THERMAL_TEMP or g.get("hw") or g.get("swt") or g.get("hwt")
        if not hot: return False
        log(f"THERMAL pause: gpu {g['temp']} C hw={g.get('hw')} sw_thermal={g.get('swt')} hw_thermal={g.get('hwt')}; waiting {THERMAL_PAUSE_S:.0f} s")
        MT.append_row(os.path.join(MET, "metrics.csv"), dict(type="thermal_pause", phase="gate", chunk="", device=DEV, wall_s=THERMAL_PAUSE_S, temp_start_C=g["temp"], zone_max_C=MT.zone_max(), note=f"hw={g.get('hw')} swt={g.get('swt')} hwt={g.get('hwt')}"))
        status(note=f"thermal pause (gpu {g['temp']} C)")
        t0 = time.time()
        while time.time() - t0 < THERMAL_PAUSE_S:
            if user_pause_requested(): return True
            time.sleep(min(2.0, THERMAL_PAUSE_S))
        if os.path.exists(FAKE) and os.path.getsize(FAKE) == 0: pass
        if os.path.exists(FAKE) and os.environ.get("AI1_FAKE_ONCE") == "1":
            os.remove(FAKE)
STAT = dict(t_start=time.time(), n_done=0, n_total=0, durs={}, last="")
def status(note="", state="running"):
    d = dict(state=state, pid=os.getpid(), device=DEV, profile=PROF, updated_pt=MT.now_pt(), done=STAT["n_done"], total=STAT["n_total"], last_chunk=STAT["last"], note=note, root=ROOT)
    rem = {}
    for ph, v in STAT["durs"].items(): rem[ph] = sum(v) / len(v)
    d["gpu_temp_C"] = (MT.read_gpu() or {}).get("temp"); z = MT.zone_max(); d["zone_max_C"] = z if z == z else None
    jdump(os.path.join(ST, "status.json"), d)
# ------------------------------------------------------------------ main
def main():
    lock = open(os.path.join(ST, "runner.lock"), "w")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError: log("another runner holds the lock; exiting"); return 3
    T = tasks(); STAT["n_total"] = len(T); todo = [t for t in T if not done(t["id"])]; STAT["n_done"] = len(T) - len(todo)
    log(f"runner start profile={PROF} device={DEV} gpu={'yes' if USE_GPU else 'no'} chunks total={len(T)} todo={len(todo)} root={ROOT}")
    if os.path.exists(PAUSE): log("PAUSE file present: not starting. Remove it (resume.sh) to continue."); status("PAUSE present at start", "paused"); return 0
    status("started"); ran = 0; csvp = os.path.join(MET, "metrics.csv")
    phase_prev = None
    for t in todo:
        if user_pause_requested():
            MT.append_row(csvp, dict(type="user_pause", phase=t["phase"], chunk=t["id"], device=DEV, note="PAUSE at chunk boundary")); log("PAUSE: stopping at chunk boundary"); status("paused by PAUSE file", "paused"); MT.build_summary(csvp, os.path.join(MET, "summary.json"), os.path.expanduser("~/gb10_work/logs/thermal.csv")); return 0
        if thermal_gate():
            MT.append_row(csvp, dict(type="user_pause", phase=t["phase"], chunk=t["id"], device=DEV, note="PAUSE during thermal wait")); status("paused (during thermal wait)", "paused"); MT.build_summary(csvp, os.path.join(MET, "summary.json"), os.path.expanduser("~/gb10_work/logs/thermal.csv")); return 0
        devname = t.get("dev", DEV) if t["kind"] == "bench" else DEV
        try:
            with MT.Meter(enabled=USE_GPU) as m:
                res, n, unit = run_chunk(t)
            s = m.summary(); s.update(type="chunk", phase=t["phase"], chunk=t["id"], device=devname, work_n=n, work_unit=unit, rate_per_s=round(n / max(s["wall_s"], 1e-9), 2))
            if USE_GPU or t["kind"] == "bench":
                wp.synchronize() if USE_GPU else None
            try: s["warp_pool_mib"] = round(wp.get_mempool_used_mem_current(DEV) / 2**20, 1) if USE_GPU else ""
            except Exception: pass
            res["metrics"] = {k: v for k, v in s.items() if k in ("wall_s", "gpu_busy_s", "energy_Wh", "util_mean", "power_mean_W", "temp_max_C")}
            jdump(os.path.join(RES, t["id"] + ".json"), res)         # result first, then metrics row (a crash in between only repeats one chunk's metrics, never loses results)
            MT.append_row(csvp, s)
        except Exception as e:
            log("CHUNK FAILED", t["id"], repr(e)); traceback.print_exc(); MT.append_row(csvp, dict(type="error", phase=t["phase"], chunk=t["id"], device=devname, note=repr(e)[:200])); status(f"error in {t['id']}", "error"); time.sleep(5); return 2
        STAT["n_done"] += 1; STAT["last"] = t["id"]; STAT["durs"].setdefault(t["phase"], []).append(s["wall_s"]); ran += 1
        if STAT["n_done"] % 10 == 0 or t["phase"] != phase_prev: log(f"[{STAT['n_done']}/{STAT['n_total']}] {t['phase']} {t['id']} {s['wall_s']:.1f}s rate={s['rate_per_s']} {unit} util={s.get('util_mean','-')} T={s.get('temp_max_C','-')}")
        phase_prev = t["phase"]; status()
        if os.environ.get("AI1_CHUNK_SLEEP_S"): time.sleep(float(os.environ["AI1_CHUNK_SLEEP_S"]))   # test hook only
        if args.max_chunks and ran >= args.max_chunks: log("max-chunks reached"); status("max-chunks", "stopped"); MT.build_summary(csvp, os.path.join(MET, "summary.json")); return 0
    finalize()
    status("all chunks done", "finished"); MT.build_summary(csvp, os.path.join(MET, "summary.json"), os.path.expanduser("~/gb10_work/logs/thermal.csv")); log("FINISHED all chunks"); return 0
def finalize():
    """merge chunks -> results/summary_*.json / csv (host-side, idempotent)."""
    import csv
    hist = {}; edges = np.linspace(280.0, 440.0, 321)
    for f in sorted(os.listdir(RES)):
        if f.startswith(("mc_",)) and f.endswith(".json"):
            r = json.load(open(os.path.join(RES, f))); h = hist.setdefault(r["case"], dict(h=np.zeros(320), N=0, qabs=0.0, ee=0.0, n=0)); h["h"] += np.array(r["hist"]); h["N"] += r["N"]; h["qabs"] += r["q_abs_mean"]; h["ee"] += r["ee_mean"]; h["n"] += 1
    rows = []
    for case, h in sorted(hist.items()):
        c = np.cumsum(h["h"]) / h["N"]; q = lambda p: float(np.interp(p, np.concatenate([[0], c]), edges))
        T370 = float(1 - np.interp(S.LIMIT_SUPPLY_K, edges[1:], c)); T343 = float(1 - np.interp(S.LIMIT_70C_K, edges[1:], c))
        rows.append(dict(case=case, N=h["N"], p01_K=q(0.01), p05_K=q(0.05), p50_K=q(0.5), p95_K=q(0.95), p99_K=q(0.99), p50_C=q(0.5) - 273.15, p95_C=q(0.95) - 273.15, frac_over_370K=T370, frac_over_343K=T343, q_abs_mean=h["qabs"] / h["n"], ee_mean=h["ee"] / h["n"]))
    if rows:
        with open(os.path.join(RES, "summary_mc.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    sz = [json.load(open(os.path.join(RES, f))) for f in sorted(os.listdir(RES)) if f.startswith("size_")]
    if sz:
        with open(os.path.join(RES, "summary_sizing.csv"), "w", newline="") as f:
            ks = ["case", "limit_K", "percentile", "A_stated_m2", "A_needed_m2", "scale", "fin_areal_kg_m2", "radiator_fin_tube_fluid_kg"]; w = csv.DictWriter(f, fieldnames=ks, extrasaction="ignore"); w.writeheader(); w.writerows(sz)
    jdump(os.path.join(RES, "summary_all.json"), dict(mc=rows, sizing=sz, profile=PROF, note="Results of the AI1 replica GB10 runner. Labels: ESTIMATE (model) with ASSUMED radiator fin geometry; see PLAN.md."))
if __name__ == "__main__":
    try: rc = main()
    except SystemExit as e: rc = e.code
    sys.exit(rc)
