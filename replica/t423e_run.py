# t423e: cell-level W/kg (SHJ / thin-film III-V) -> wing-level conversion; credible & stretch stacks. Tag t423e. No repo/baseline/DECISIONS changes.
import sys, os, json, csv
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
src = open(os.path.join(HERE, "orbit_loop_run_t423c.py")).read().split("# ===================================================================================================== PASS A")[0]
src = src.replace("orbit_loop_t423c", "orbit_loop_t423d").replace('"t423c"', '"t423e"').replace('plog.event("milestone"', 'pass  # plog.event("milestone"', 1)
ns = {"__file__": os.path.join(HERE, "orbit_loop_run_t423e.py")}; exec(src, ns)
T, ap, W0, W0f, LV, ORB_FCC, ORB_ALL, addb, O, rec = [ns[k] for k in ("T", "ap", "W0", "W0f", "LV", "ORB_FCC", "ORB_ALL", "addb", "O", "rec")]
RES = ns["RES"]
K3 = dict(dT=20.0, panel_fluid=False); K5 = dict(dT=20.0, panel_fluid=False, run_scale=0.5)
LV.update({"E1c": dict(harness_V=300.0), "C_hot": dict(cool=K3), "C_str": dict(cool=K5, pump=0.10), "PCs": dict(pcdu_kwkg=1.6), "PCf": dict(pcdu_kwkg=0.50)})
CR = ["E1c", "C_hot", "PCf"]; ST = ["R2", "S1", "E1c", "P1", "E2", "D1", "D2", "A2", "C_str", "PCs"]
PD3, PDS = 319.7, 319.7 * 0.72          # W/m2 array-level BOL power density used by the loop (3J, Si)
S3J = 319.7 / 480.0                       # loop's 3J cell-level mass 0.666 kg/m2
NC = {"n_T2": 0.40, "n_FACT": 1.21, "n_ROSAflown": 1.90}   # non-cell kg/m2 (see INTERIM)
def wing_from_cell(cell, Wc, n):
    pd = PDS if cell == "Si" else PD3; return pd / (n + pd / Wc)
def params(b, scale, ids, cell, wing, Wc=None):
    base = W0[b] if scale == "scaled" else W0f[b]
    if cell == "3J": return ap(base, ids, cell="3J", wkg_wing=float(wing))
    # Si: loop sig_arr = 319.7/wkg_wing - 0.666 + 0.72*319.7/si_wkg  -> choose wkg_wing so (319.7/wkg_wing-0.666)=n and si_wkg=Wc
    return ap(base, ids, cell="Si", wkg_wing=float(wing), si_wkg=float(Wc))
def run(b, scale, ids, cell, wing, Wc=None, **kw):
    p = params(b, scale, ids, cell, wing, Wc); p.update(kw); o = T.best_orbit(b, p, ORB_FCC); r = rec(o)
    r["pass_fcc"] = dict(mass=o["M_kg"] < 4000, rad=o["A_rad"] < 200, arr=o["A_arr"] < 1500)
    r["tgt"] = O.TARGET[b]["kwt"]; r["gap_core"] = r["kwt"] - r["tgt"]; r["gap_ab"] = r["kwt_ab"] - r["tgt"]; return r
CASES = []   # (label, cell, Wcell, n, wing)
for n_lab, n in NC.items():
    for Wc in (250, 400, 600, 1000):
        CASES.append((f"SHJ{Wc}|{n_lab}", "Si", Wc, n, 319.7 / (n + S3J)))     # wing arg encodes non-cell n
    for Wc in (480, 884, 2000):
        w = wing_from_cell("3J", Wc, n); CASES.append((f"3J{Wc}|{n_lab}", "3J", Wc, n, w))
# wing-level bounds
BOUND = [("wing250_3Jarea", "3J", None, None, 250.0), ("wing250_Siarea", "Si", 1e12, None, 319.7 / (PDS / 250.0 + S3J - 0.72 * 319.7 / 1e12))]
# SHJ wing W/kg for the SHJ cases: pd/(n + pd/Wc)
R = []
def go(label, cell, Wc, n, warg, kind):
    for b in ("Jun8", "Aug4"):
        for sc in ("scaled", "fixed"):
            for stk, ids in (("credible", CR), ("stretch", ST)):
                if cell == "Si": r = run(b, sc, ids, "Si", warg, Wc if Wc else 1e12)
                else: r = run(b, sc, ids, "3J", warg)
                wing_eff = wing_from_cell(cell, Wc, n) if (Wc and n is not None) else (250.0)
                r.update(dict(label=label, kind=kind, cell=cell, Wcell=Wc, n=n, wing_bol=wing_eff, build=b, scale=sc, stack=stk)); R.append(r)
for lab, cell, Wc, n, w in CASES: go(lab, cell, Wc, n, w, "cell")
for lab, cell, Wc, n, w in BOUND: go(lab, cell, Wc, n, w, "wing_bound")
# reference stacks from t423d (124 and 300 W/kg wing, 3J)
for w in (124, 200, 300): go(f"ref3J_wing{w}", "3J", None, None, float(w), "ref")
# threshold wing W/kg for 70/75 (stretch, scaled, core) -- from t423d: 200/212 ; and cell-level W/kg needed given n
def kwt_at(b, ids, scale, cell, Wc, n, ab=False):
    pdn = PDS if cell == "Si" else PD3
    if cell == "Si": r = run(b, scale, ids, "Si", 319.7 / (n + S3J), Wc)
    else: r = run(b, scale, ids, "3J", wing_from_cell("3J", Wc, n))
    return r["kwt_ab" if ab else "kwt"]
NEED = {}
for b in ("Jun8", "Aug4"):
    tg = O.TARGET[b]["kwt"]
    for n_lab, n in NC.items():
        for cell in ("Si", "3J"):
            for stk, ids in (("credible", CR), ("stretch", ST)):
                for ab in (False, True):
                    f = lambda Wc: kwt_at(b, ids, "scaled", cell, Wc, n, ab)
                    if f(1e6) < tg: NEED[f"{b}|{n_lab}|{cell}|{stk}|{'ab' if ab else 'core'}"] = None; continue
                    lo, hi = 50.0, 1e6
                    for _ in range(45):
                        m = (lo * hi) ** .5; (hi := m) if f(m) >= tg else (lo := m)
                    NEED[f"{b}|{n_lab}|{cell}|{stk}|{'ab' if ab else 'core'}"] = hi
# efficiency / degradation sweep (SHJ 250 & 600 cell-level, n_FACT, stretch scaled)
SW = []
for b in ("Jun8", "Aug4"):
    for Wc in (250, 600):
        for ef in (0.72, 0.80, 0.90, 1.00):      # BOL W/m2 factor vs 3J 319.7 (0.72 ~ 20% AM0 Si cell; 1.0 ~ 29% 3J-class)
            for deg in (0.0015, 0.01, 0.02, 0.03):
                p = ap(W0[b], ST, cell="Si", wkg_wing=319.7 / (NC["n_FACT"] + S3J), si_wkg=float(Wc), arr_deg=deg)
                T_ = T
                # eff factor: scale Si power density by monkey-patching via si area factor -> emulate by scaling si_wkg and area: use cell="Si" with factor ef/0.72 on W/m2 through wkg parameters
                o = T.best_orbit(b, p, ORB_FCC); r = rec(o)
                # area & mass correction for ef != 0.72: array area scales 0.72/ef, array mass scales likewise (area-proportional sig_arr)
                k = 0.72 / ef; dm = o["mass"].get("array", None)
                SW.append(dict(build=b, Wcell=Wc, ef=ef, deg=deg, kwt=r["kwt"], kwt_ab=r["kwt_ab"], M=r["M"], A_arr=r["A_arr"] * k))
json.dump(dict(rows=R, need=NEED, sweep=SW, NC=NC), open(f"{RES}/t423e_results.json", "w"), indent=1, default=str)
with open(f"{RES}/t423e_passes.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow("label kind build scale stack Wcell n wing_bol M kwt kwt_ab N98 N100 N98_ab A_arr A_rad gap_core gap_ab orbit".split())
    for r in R: w.writerow([r["label"], r["kind"], r["build"], r["scale"], r["stack"], r["Wcell"], r["n"], round(r["wing_bol"], 1), round(r["M"]), round(r["kwt"], 1), round(r["kwt_ab"], 1), r["N98"], r["N100"], r["N98_ab"], round(r["A_arr"]), round(r["A_rad"]), round(r["gap_core"], 1), round(r["gap_ab"], 1), r["orbit"]])
print("rows", len(R)); 
for r in R:
    if r["scale"] == "scaled" and r["build"] in ("Jun8", "Aug4"):
        print(r["build"], r["stack"][:4], r["label"], round(r["wing_bol"]), "kwt", round(r["kwt"], 1), "ab", round(r["kwt_ab"], 1), "M", round(r["M"]), "N98", r["N98"], "A_arr", round(r["A_arr"]), r["pass_fcc"])
print(json.dumps(NEED, indent=0, default=lambda x: x))
