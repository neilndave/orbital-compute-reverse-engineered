# [t523 2026-11-05, the author ] BASELINE CHANGE: the C1 5% rack_spare (unsourced) is replaced by 1 spare GPU per sat (Jun 72+1, Aug 79+1): rack_spare = 1/N.  Total mass M and k_rack are HELD (so kW/t and sats per Starship do not move); the freed spare mass goes to the growth reserve (growth is solved).
#   T423G_LEGACY=1 reproduces the pre-t523 run exactly and writes results/t423g_legacy.json only (needed as the held-k_rack source).  Default (t523) writes results/t423g.json.  Backup of the old json: results/t423g.json.bak_t523.
# t423g: calibrate a 'SpaceX-like' design to ~70/75 kW/t and ~46/30 sats per Starship (98 t) by adding realistic margin/redundancy to the first-principles stack.  Box only; ESTIMATE unless tagged.
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
src = open(os.path.join(HERE, "t423e_fp.py")).read().split("OUT = {\"info\": info}")[0]
ns = {"__file__": os.path.join(HERE, "t423e_fp_.py")}; exec(src, ns)
run, O, T, RES, LV, FP_B, info, PD3 = [ns[k] for k in ("run", "O", "T", "RES", "LV", "FP_B", "info", "PD3")]
LEGACY = os.environ.get("T423G_LEGACY") == "1"; NSP = {"Jun8": 72, "Aug4": 79}      # t523: GPUs per sat (the author )
LEG = json.load(open(os.path.join(HERE, "results", "t423g_legacy.json"))) if not LEGACY else None
def wing(n): return ns["array_fp"](884.0, n)
BASE = [i for i in FP_B if i not in ("FPr_b", "FPp_b", "FPs_b", "FPa_b")]      # E1c P1 E2 D1 D2 A2 C_str (coolant/ADCS/pmad as t423d)
def build(b, k_rack, n=0.25, f_struct=0.06, pcdu=5.57, pump_spares=1, rack_spare=0.0, harn=(0.01, 15.0), arr_deg=0.01, growth=0.205, bumper=True, adapter=True):
    LV["G_r"] = dict(f_strip=0.0, rack_kg=k_rack * 188.0, rack_scale=True)
    cool = dict(LV["C_str"]["cool"]); cool["spares"] = pump_spares
    kw = dict(cell="3J", wkg_wing=wing(n), arr_deg=arr_deg, f_struct=f_struct, pcdu_kwkg=pcdu, cool=cool, pump=LV["C_str"]["pump"], rad=(7500.0, 2.0, rack_spare))
    r = run(b, [i for i in BASE if i != "C_str"] + ["G_r"], harn=harn, **kw); o = r["o"]
    M, add = T.with_addbacks(o, growth=growth > 0, bumper=bumper, adapter=adapter, growth_frac=growth)
    L = dict(o["lines"]); 
    for k, v in add.items(): L[k] = L.get(k, 0.0) + v
    return dict(M_core=o["M_kg"], M=M, kwt_core=o["kwt_wet"], kwt=o["P_kW"] / M * 1e3, N98=int(98000 // M), N100=int(100000 // M), orbit=(o["h"], o["ltan"]), A_rad=o["A_rad"], A_arr=o["A_arr"], fcc=o["fcc_flags"], lines=L, add=add, P=o["P_kW"], wing=wing(n), k_rack=k_rack, prop=o["mass"]["propellant"], o=o)
def solve(b, knob="k_rack", lo=0.3, hi=60.0, **kw):
    tg = O.TARGET[b]["kwt"]; N = {"Jun8": 46, "Aug4": 30}[b]; Mt = min(O.TARGET[b]["P"] / tg * 1e3, 98000.0 / N)
    f = lambda x: build(b, **{**kw, knob: x})["M"] - Mt
    a, c = lo, hi
    if f(a) > 0: return None
    if f(c) < 0: return None
    for _ in range(50):
        m = (a * c) ** .5 if a > 0 and knob != "n" else (a + c) / 2
        (c := m) if f(m) > 0 else (a := m)
    return a
CAND = {
 "C1_margin_forward": dict(n=0.60, f_struct=0.08, pcdu=3.0, pump_spares=2, rack_spare=0.05, growth=0.205, desc="blanket 0.60 kg/m2, structure 8%, PCDU 3.0 kW/kg (dual-string), 2 spare pumps, 5% spare compute, growth 20.5% (repo policy), bumper+adapter"),
 "C2_compute_limited": dict(n=0.25, f_struct=0.06, pcdu=5.57, pump_spares=1, rack_spare=0.0, growth=0.10, desc="FP base array/PCDU/structure, 1 spare pump, no spare compute, growth 10%, bumper+adapter"),
}
OUT = {}; 
for b in ("Jun8", "Aug4"):
    OUT[b] = {}; tg = O.TARGET[b]["kwt"]
    for nm, c in CAND.items():
        kw = {k: v for k, v in c.items() if k != "desc"}
        if nm == "C1_margin_forward" and not LEGACY:      # t523: 1 spare GPU per sat; hold k_rack (=> M, kW/t, N98 held), solve growth so that M returns to target (freed kg -> growth reserve)
            kw["rack_spare"] = 1.0 / NSP[b]; k = LEG[b][nm]["k_rack"]; g0 = 0.205; kw.pop("growth")
            gs = solve(b, knob="growth", lo=0.01, hi=3.0, k_rack=k, **kw); kw["growth"] = gs; CAND[nm]["rack_spare"] = kw["rack_spare"]; CAND[nm]["growth"] = gs
            print(b, "t523 C1: rack_spare", round(kw["rack_spare"], 5), "growth", round(g0, 4), "->", round(gs, 5), "(solved, k_rack held at", round(k, 4), ")")
        else: k = solve(b, **kw)
        r = build(b, k_rack=k, **kw)
        if nm == "C1_margin_forward" and not LEGACY:
            dm = r["lines"]["margin"] - LEG[b][nm]["lines"]["margin"]; r["t523_check"] = dict(M_held=abs(r["M"] - LEG[b][nm]["M"]) < 1e-6, N98_held=r["N98"] == LEG[b][nm]["N98"], freed_to_margin_kg=dm,
                spare_line_kg=r["lines"].get("shielding_radiation"), spare_line_kg_legacy=LEG[b][nm]["lines"].get("shielding_radiation"))
            pf = json.load(open(os.path.join(HERE, "gtc_params", {"Jun8": "point_J8_C1.json", "Aug4": "point_A4_C1.json"}[b])))["t523"]["freed_kg"]      # consumed-accounting freed kg (point file, authoritative)
            dprop = LEG[b][nm]["lines"]["propulsion_adcs"] - r["lines"]["propulsion_adcs"]      # t423g first-principles also re-sizes propulsion_adcs a little (point files hold it)
            r["t523_check"].update(freed_pointfile_kg=pf, propulsion_resize_kg=dprop, residual_kg=dm - pf - dprop)
            assert abs(dm - pf - dprop) < 0.15, r["t523_check"]      # residual only the 0.1 kg line rounding
            print(b, "t523 check: freed->margin", round(dm, 2), "kg (t423g) vs point file", pf, "kg + propulsion re-size", round(dprop, 2), "kg; residual", round(dm - pf - dprop, 3))
            assert r["t523_check"]["M_held"] and r["t523_check"]["N98_held"], r["t523_check"]
            if "shielding_radiation" in r["lines"]: r["lines"]["spare_compute"] = r["lines"].pop("shielding_radiation")      # t523: renamed (it is spare compute, not a shield)
        r["lines"] = {a: round(v, 1) for a, v in r["lines"].items()}; OUT[b][nm] = {a: v for a, v in r.items() if a != "o"}
        print(b, nm, "k_rack", round(k, 2), "wing", round(r["wing"]), "M", round(r["M"]), "core", round(r["M_core"]), "kwt", round(r["kwt"], 1), "N98", r["N98"], "N100", r["N100"], r["orbit"], "A_rad", round(r["A_rad"]), "A_arr", round(r["A_arr"]), r["fcc"], r["lines"])
    # single-knob explanations (FP base + full add-back 20.5%): which one knob alone gives target
    sk = {}
    sk["rack_kg_per_kW"] = solve(b, n=0.25, f_struct=0.06, pcdu=5.57, growth=0.205)
    sk["blanket_n_kg_m2"] = solve(b, knob="n", lo=0.05, hi=60.0, k_rack=1.39, f_struct=0.06, pcdu=5.57, growth=0.205)
    sk["growth_frac"] = solve(b, knob="growth", lo=0.01, hi=3.0, k_rack=1.39, n=0.25, f_struct=0.06, pcdu=5.57)
    sk["f_struct"] = solve(b, knob="f_struct", lo=0.01, hi=3.0, k_rack=1.39, n=0.25, pcdu=5.57, growth=0.205)
    sk["pcdu_kwkg"] = None
    f = lambda x: build(b, k_rack=1.39, pcdu=x, n=0.25, f_struct=0.06)["M"]
    OUT[b]["single_knob"] = sk; print(b, "single-knob", {a: (round(v, 3) if v else v) for a, v in sk.items()})
    # tornado around C1: +/- range of each knob -> all-in kW/t (sat count)
    c = CAND["C1_margin_forward"]; kwc = {k: v for k, v in c.items() if k != "desc"}; k0 = OUT[b]["C1_margin_forward"]["k_rack"]
    rng = {"k_rack": (1.4, 7.8), "n": (0.25, 1.2), "f_struct": (0.06, 0.10), "pcdu": (5.57, 1.0), "growth": (0.0, 0.30), "rack_spare": (0.0, 0.15), "pump_spares": (1, 3), "arr_deg": (0.0015, 0.03)}
    tor = {}
    for kn, (lo, hi) in rng.items():
        row = []
        for v in (lo, hi):
            a = dict(kwc); a["k_rack"] = k0; a[kn] = v; r = build(b, **a); row.append((v, r["M"], r["kwt"], r["N98"]))
        tor[kn] = row
    OUT[b]["tornado"] = tor; print(b, "tornado", {k: [(round(x[0], 3), round(x[2], 1)) for x in v] for k, v in tor.items()})
    # iso curves: rack kg/kW needed vs blanket n, for C1-style margins
    iso = {}
    for n in (0.25, 0.4, 0.6, 0.8, 1.0, 1.2):
        a = dict(kwc); a["n"] = n; iso[n] = solve(b, **a)
    OUT[b]["iso_rack_vs_n"] = {str(n): v for n, v in iso.items()}; print(b, "iso", {n: (round(v, 2) if v else v) for n, v in iso.items()})
    # volume
    vol = {}
    for nm in CAND:
        r = OUT[b][nm]; P = r["P"]; Vr = 1.65 * P / 188.0
        for lab, (va, vr, pk) in dict(central=(0.006, 0.012, 0.5), tight=(0.012, 0.020, 0.35), loose=(0.003, 0.008, 0.65)).items():
            rest = r["M"] - r["lines"]["array"] - r["lines"]["radiator"] - r["lines"]["rack"]
            V = Vr + r["A_arr"] * va + r["A_rad"] * vr + (rest + r["lines"]["rack"] * 0) / 591.0
            vol[f"{nm}|{lab}"] = dict(V_sat=V, N_vol=int(1100.0 * pk // V), N_vol_614=int(614.0 * pk // V), thick_over_V3_footprint=V / 24.5)
    OUT[b]["volume"] = vol
    for k, v in vol.items(): print(b, k, {a: round(c, 2) for a, c in v.items()})
json.dump(OUT, open(f"{RES}/t423g_legacy.json" if LEGACY else f"{RES}/t423g.json", "w"), indent=1, default=str)
