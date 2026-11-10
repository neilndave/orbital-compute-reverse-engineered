"""GTC_FINAL_AL fin study (sidecar of GTC_FINAL_CANDIDATE; nothing there is modified).  NVIDIA Warp 2-D fin solver = repo warp_fin_ref.Fin
(float64 Newton + PCG, both faces radiating; same file/sha as t410/t472/t479/t548).  Two parts:
 (1) SCREEN (fin_t548 logic, OD 8 mm / 0.5 mm-wall Al tube cell, same basis as the t479 K13D_AREA_FACTOR 0.9913): q [W per m2 planform, both faces]
     at the GTC_FINAL_CANDIDATE nominal coolant temperatures, Simpson 1-4-1 over supply / mid / radiator inlet, per month, with that month's ee and sink.
     Reference = live K13D70 30/0.20 bonded (h_bond 3000 W/m2K ASSUMED, t479).  Al options have NO bondline (integral / brazed fin).
 (2) TABLE (t410 runner format: eta_cell(Tb, ee, Ts) on tb 320..440/10, ee 0.60..1.00/0.05, ts 150..250/25; nx 320, ny 8; eta_cell = (L eta_fin + d/2)/(L + d/2))
     for the selected Al designs, plus F3_L40_t0p5 regenerated as a parity check against the vendored t410 table.
Materials (handbook values, see REPORT.md sources): Al6061-T6 k 167 W/mK, rho 2700 kg/m3; Al1100-H14 k 218 W/mK, rho 2710 kg/m3 (sensitivity).  ESTIMATE.
usage: python fin_al.py screen|table [--smoke]"""
import json, sys, os, time, math, itertools
import numpy as np
import warp as wp
wp.config.quiet = True; wp.init()
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); OUT = os.path.join(HERE, "results"); os.makedirs(OUT, exist_ok=True)
import warp_fin_ref as WF
MODE = sys.argv[1]; SMOKE = "--smoke" in sys.argv
SIG = 5.670374419e-8; D, TW, RHOT, RHOF = 0.008, 0.0005, 2700.0, 1030.0; W141 = (1.0, 4.0, 1.0)
dev = os.environ.get("WARP_DEVICE", "cuda:0" if wp.get_cuda_device_count() else "cpu")
MAT = {"Al6061-T6": (167.0, 2700.0, None), "Al1100-H14": (218.0, 2710.0, None), "K13D70 h3000 (live ref)": (350.0, 1900.0, 3000.0)}
# GTC_FINAL_CANDIDATE nominal (THERMAL_SPIN1 T2_rec_nominal_MPG40_plus_recharge): supply, inlet, ee, sink
COND = {"June": (360.5107838853224, 382.79830042614805, 0.8919908588528411, 185.63214687303105),
        "August": (349.14598154721835, 371.3383519520863, 0.8808900326405731, 186.2142294872348)}
def fin_q(k, L, t, Tb, ee, Ts, nx, ny):
    f = WF.Fin(nx, ny, L, L * ny / nx, k, ee, Tb, Ts, device=dev); f.t.fill_(t); res = f.solve(tol=1e-9); Ly = f.h * ny
    return f.Q() / Ly, f.Q() / (2 * ee * SIG * (Tb**4 - Ts**4) * L * Ly), f.ncg, res
def cell(k, rho, hb, L, t, cond, nx=160, ny=8):
    s, r_, ee, Ts = cond; TBS = (s, 0.5 * (s + r_), r_); qs = []; etas = []
    for Tb in TBS:
        Tr = Tb
        for _ in range(1 if hb is None else 5):
            qL, ef, _, _ = fin_q(k, L, t, Tr, ee, Ts, nx, ny)
            if hb is not None: Tr = Tb - 2 * qL / (hb * math.pi * D / 2)
        q_cell = 2 * qL + 2 * ee * SIG * (Tb**4 - Ts**4) * D
        qs.append(q_cell / (2 * (L + D / 2))); etas.append(q_cell / (2 * ee * SIG * (Tb**4 - Ts**4) * 2 * (L + D / 2)))
    qm = sum(w * q for w, q in zip(W141, qs)) / 6.0
    sheet = rho * t * L * 2 / (2 * (L + D / 2)); tube = RHOT * math.pi * D * TW / (2 * (L + D / 2)); fluid = RHOF * math.pi * (D - 2 * TW)**2 / 4 / (2 * (L + D / 2))
    return dict(q_Wm2=qs, q_simpson_Wm2=qm, eta_cell=etas, areal_kg_m2=sheet + tube + fluid, sheet_kg_m2=sheet, tube_kg_m2=tube, fluid_kg_m2=fluid,
                kg_per_kW=(sheet + tube + fluid) / qm * 1e3, tube_pitch_mm=2 * (L + D / 2) * 1e3, T_root_last=Tr)
if __name__ == "__main__":
    t0 = time.time()
    if MODE == "screen":
        global_MAT = None
        Ls = [0.03] if SMOKE else [0.015, 0.020, 0.025, 0.030, 0.035, 0.040, 0.050]
        ts = [0.2e-3] if SMOKE else [0.10e-3, 0.15e-3, 0.20e-3, 0.25e-3, 0.30e-3, 0.35e-3, 0.40e-3, 0.50e-3, 0.60e-3]
        G = os.environ.get("AL_SCREEN_GRID")   # fine grid: {"Ls": [...], "ts": [...], "tag": "fine", "mats": [...]}
        if G: G = json.loads(G); Ls, ts = G["Ls"], G["ts"]; MAT = {k: v for k, v in MAT.items() if k in G["mats"] or v[2]}
        res = {}
        for m, cond in COND.items():
            res[m] = {}
            for name, (k, rho, hb) in MAT.items():
                grid = [(0.03, 0.2e-3)] if hb else list(itertools.product(Ls, ts)) + ([(0.04, 0.5e-3)] if not (SMOKE or G) else [])
                rows = []
                for L, t in dict.fromkeys(grid):
                    r = cell(k, rho, hb, L, t, cond); r.update(L=L, t=t); rows.append(r)
                res[m][name] = rows; print(m, name, len(rows), round(time.time() - t0, 1), "s", flush=True)
        res["_meta"] = dict(device=dev, device_name=(wp.get_device(dev).name if dev != "cpu" else "cpu"), warp=wp.__version__, wall_s=time.time() - t0, smoke=SMOKE,
                            cond=COND, simpson=W141, grid="160x8", tube=dict(OD=D, wall=TW), materials=MAT, label="ESTIMATE (Warp fin solver, repo warp_fin_ref.Fin)")
        json.dump(res, open(os.path.join(OUT, f"screen_al{'_smoke' if SMOKE else ''}{('_' + G['tag']) if G else ''}.json"), "w"), indent=1)
    elif MODE == "table":
        DES = json.loads(os.environ.get("AL_TABLES", '[["F3_L40_t0p5",167.0,0.040,0.0005],["AL6061_L30_t0p20",167.0,0.030,0.0002]]'))
        if SMOKE: TB = [360.0]; EE = [0.9]; TS = [175.0]; nx, ny = 160, 8
        else: TB = [320.0 + 10 * i for i in range(13)]; EE = [0.60 + 0.05 * i for i in range(9)]; TS = [150.0 + 25 * i for i in range(5)]; nx, ny = 320, 8
        meta = {}
        for nm, k, L, t in DES:
            t1 = time.time(); eta = []; worst = 0.0; ncg = 0
            for Tb in TB:
                for ee in EE:
                    for Ts in TS:
                        _, ef, n, r = fin_q(k, L, t, Tb, ee, Ts, nx, ny); eta.append((L * ef + D / 2) / (L + D / 2)); ncg += n; worst = max(worst, float(r) if r is not None else 0.0)
            tbl = dict(id=nm, k_W_mK=k, L=L, t=t, tb0=TB[0], dtb=10.0, ntb=len(TB), ee0=EE[0], dee=0.05, nee=len(EE), ts0=TS[0], dts=25.0, nts=len(TS), eta=eta,
                       profile=("smoke" if SMOKE else "full"), nx=nx, ny=ny, n_cg_total=ncg, worst_residual=worst, device=dev, warp=wp.__version__, wall_s=time.time() - t1,
                       label="ESTIMATE (Warp fin solver float64; geometry ASSUMED; t410 table format)")
            json.dump(tbl, open(os.path.join(OUT, f"table_{nm}{'_smoke' if SMOKE else ''}.json"), "w"))
            print(nm, "done", round(time.time() - t1, 1), "s", "eta[mid]", eta[len(eta) // 2], flush=True); meta[nm] = tbl["wall_s"]
    print("DONE wall_s", round(time.time() - t0, 1), flush=True)
