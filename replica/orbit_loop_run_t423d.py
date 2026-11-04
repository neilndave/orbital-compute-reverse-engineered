"""t423d: coolant-loop breakdown + levers, PCDU specific power (space-qualified-realistic), 300 V bus cap, credible vs stretch stacks, required array W/kg, meta-scan.
Run: eclipse/venv/bin/python orbit_loop_run_t423d.py   (box only; logs through plog tag t423d)"""
import sys, os, json, time, math, csv
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
MODE = os.environ.get("T423D_MODE", "run")
src = open(os.path.join(HERE, "orbit_loop_run_t423c.py")).read().split("# ===================================================================================================== PASS A")[0]
src = src.replace("orbit_loop_t423c", "orbit_loop_t423d").replace('"t423c"', '"t423d"').replace("t423c_%Y", "t423d_%Y")
src = src.replace('TAG = "t423c"', 'TAG = "t423d"')
if MODE != "run": src = src.replace('plog.event("milestone"', 'pass  # plog.event("milestone"', 1)
ns = globals(); exec(src, ns)
import coolant_t423d as CT
if MODE == "run": plog.event("milestone", f"t423d run {RUN} started (parent msg Nov 3 2026 4:21 PM PT = Nov 4 8:21 AM Taipei): coolant-loop breakdown, PCDU lever, 300 V cap, credible vs stretch stacks, meta-scan; orbit swept every pass", tag=TAG)
BUILDS = ("Jun8", "Aug4")
# ---------------------------------------------------------------- lever definitions
PUMP_ISS = 1.0; PUMP_T2 = 0.25; PUMP_LIGHT = 0.10      # multipliers on the ISS EATCS module mass (353.8 kg / 604 W hydraulic = 0.585 kg/W): 0.25 -> 0.146 kg/W ; 0.10 -> 0.058 kg/W
PCDU_FLOWN = 0.50      # kW/kg  Terma BepiColombo MTM PCDU 14 kW / 28.1 kg (flown); Airbus PSR 100 V 23 kW / 54 kg = 0.43 kW/kg (STATEMENT via vendor sheets)
PCDU_SMALLSAT = 1.60   # kW/kg  EnduroSat EPS IV 7.2 kW / 4.5 kg (NASA SST SoA 2026 Table 3-8; flight heritage not stated) -> ESTIMATE for a space-qualified next generation
COOL = dict(
  K1=dict(dT=9.8),                                    # geometry-consistent coolant model (manifold + panel fluid scaled to actual radiator area); dT as in P6 sizing
  K2=dict(dT=9.8, panel_fluid=False),                 # + remove panel-fluid double count (radiator areal mass already includes tube + fluid)
  K3=dict(dT=20.0, panel_fluid=False),                # + loop rise 20 K (what the radiator fit assumes)
  K4=dict(dT=40.0, panel_fluid=False),                # stretch: hot loop 40 K rise (radiator fit not re-run)
  K5=dict(dT=20.0, panel_fluid=False, run_scale=0.5), # + shorter runs (trunk + wing manifold length x0.5) ESTIMATE
  K6=dict(dT=20.0, panel_fluid=False, rack_liq_scale=0.5),  # rack liquid inventory 60 L -> 30 L (ESTIMATE; 60 L itself unpublished)
  K7=dict(dT=20.0, panel_fluid=False, two_phase=True),      # two-phase pumped water (stretch; no flown loop >kW class)
  K8=dict(dT=20.0, panel_fluid=False, fluid="nh3"),         # single-phase ammonia
)
def cool_rec(o): c = o.get("cool"); return None if c is None else {k: (v if not isinstance(v, dict) else v) for k, v in c.items()}
def rec2(o):
    r = rec(o); r["cool_kg"] = o["cool_kg"]; r["cool"] = cool_rec(o); r["A_rad"] = o["A_rad"]; return r
def need_wkg(b, p, target, ab=False, lo=60.0, hi=3000.0):
    f = lambda w: (lambda o: (addb(o)[1] if ab else o["kwt_wet"]))(T.best_orbit(b, dict(p, wkg_wing=float(w)), ORB_FCC))
    if f(hi) < target: return None
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if f(mid) >= target: hi = mid
        else: lo = mid
    return hi
out = dict(run=RUN)
# ================================================================================================= PASS K : coolant-loop breakdown (item 1)
K = {}
for b in BUILDS:
    base = W0[b]
    o = run_pass("K-legacy", b, base, "none", "t423c working baseline W0 (legacy linear-in-P coolant lines)", note_extra=dict(item="coolant")); K[f"{b}|legacy"] = rec2(o)
    for nm in ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8"):
        o = run_pass("K-coolant", b, ap(base, [], cool=COOL[nm]), f"coolant {nm}: {COOL[nm]}", "coolant-loop sub-model (coolant_t423d.py) on the W0 baseline, pump multiplier 0.25 as T2", note_extra=dict(item="coolant", lever=nm))
        K[f"{b}|{nm}"] = rec2(o)
    for pf in (1.0, 0.25, 0.10):
        o = run_pass("K-pump", b, ap(base, [], cool=COOL["K3"], pump=pf), f"coolant K3 with pump multiplier {pf} of ISS module mass", "pump specific mass sweep", note_extra=dict(item="coolant", pump=pf)); K[f"{b}|K3|pump{pf}"] = rec2(o)
    for pf in (1.0,):   # flown ISS pump with K1 (what the repo would give without the light-pump estimate, new geometry)
        o = run_pass("K-pump", b, ap(base, [], cool=COOL["K1"], pump=pf), "coolant K1 with ISS-flown pump (x1.0)", "pump honesty check", note_extra=dict(item="coolant", pump=pf)); K[f"{b}|K1|pump1.0"] = rec2(o)
out["K"] = K
# ================================================================================================= PASS P : PCDU lever (item 2) ; PASS V : bus voltage (item 3)
PC = {}
for b in BUILDS:
    for kk in (PCDU_FLOWN, 0.85, 0.92, PCDU_SMALLSAT):
        o = run_pass("P-PCDU", b, ap(W0[b], [], pcdu_kwkg=kk), f"PCDU {kk} kW/kg", "PCDU specific power: flown 0.43-0.50, T2 implied 0.85, Pumpkin AMPS 0.92, EnduroSat EPS IV 1.6 (2026 NASA SoA table), lab GaN 4.9-24 not used", note_extra=dict(item="pcdu", kwkg=kk)); PC[f"{b}|{kk}"] = rec2(o)
out["pcdu"] = PC
V = {}
for b in BUILDS:
    for vv in (100.0, 300.0, 400.0):
        o = run_pass("V-bus-voltage", b, ap(W0[b], [], harness_V=vv), f"bus {vv} V (harness only)", "harness copper mass scales as 1/V in the loop; ROSA published ~300 V; 400 V beyond published ROSA rating", note_extra=dict(item="bus_V", V=vv)); V[f"{b}|{vv}"] = rec2(o)
out["voltage"] = V
# ================================================================================================= STACKS (item 4)
LV.update({"E1c": dict(harness_V=300.0), "C_hot": dict(cool=COOL["K3"]), "C_str": dict(cool=COOL["K5"], pump=PUMP_LIGHT), "PCs": dict(pcdu_kwkg=PCDU_SMALLSAT), "PCf": dict(pcdu_kwkg=PCDU_FLOWN)})
CRED_IDS = ["E1c", "C_hot", "PCf"]                      # flown/published basis only: 300 V (ROSA), coolant corrections consistent with radiator fit (K3), PCDU at flown 0.50 kW/kg
CRED_KW = dict(wkg_wing=124.0)                          # flown ROSA best wing (71-124 W/kg, Redwire flysheet; 100 in NASA SoA 2026)
STRETCH_IDS = ["R2", "S1", "E1c", "P1", "E2", "D1", "D2", "A2", "C_str", "PCs"]   # everything, with 300 V cap; array W/kg solved below
def stack(b, ids, scale, **kw): return ap(W0[b] if scale == "scaled" else W0f[b], ids, **kw)
ST = {}
for b in BUILDS:
    for scale in ("scaled", "fixed"):
        for nm, ids, kw in (("T2_ref", [], {}), ("credible", CRED_IDS, CRED_KW), ("credible_200", CRED_IDS, dict(wkg_wing=200.0)), ("stretch_300W", STRETCH_IDS, dict(wkg_wing=300.0)), ("stretch_400W", STRETCH_IDS, dict(wkg_wing=400.0)),
                            ("stretch_400V", [i if i != "E1c" else "E1" for i in STRETCH_IDS], dict(wkg_wing=300.0))):
            p = stack(b, ids, scale, **kw)
            o = run_pass(f"S-stack-{nm}", b, p, f"{nm} ({scale} rack)", "credible = flown/published levers only; stretch = all levers incl. unflown", note_extra=dict(stack=nm, scale=scale))
            ST[f"{b}|{scale}|{nm}"] = rec2(o)
        # required array W/kg
        for nm, ids in (("credible", CRED_IDS), ("stretch", STRETCH_IDS)):
            p = stack(b, ids, scale)
            tg = O.TARGET[b]["kwt"]
            ST[f"{b}|{scale}|need|{nm}"] = dict(core=need_wkg(b, p, tg), addback=need_wkg(b, p, tg, ab=True))
out["stacks"] = ST
# marginal contribution of each stretch lever (dropping one at a time from stretch_300W, scaled rack)
MG = {}
for b in BUILDS:
    full = stack(b, STRETCH_IDS, "scaled", wkg_wing=300.0); k0 = T.best_orbit(b, full, ORB_FCC)["kwt_wet"]
    for i in STRETCH_IDS:
        q = stack(b, [j for j in STRETCH_IDS if j != i], "scaled", wkg_wing=300.0); MG[f"{b}|{i}"] = k0 - T.best_orbit(b, q, ORB_FCC)["kwt_wet"]
out["marginal_if_removed_from_stretch300"] = MG
# ================================================================================================= PASS M : meta-scan, mass-ledger of remaining lines after stretch
ML = {}
for b in BUILDS:
    o = run_pass("M-meta-ledger", b, stack(b, STRETCH_IDS, "scaled", wkg_wing=300.0), "stretch stack at 300 W/kg: remaining mass ledger", "meta-scan: what is left after every lever", note_extra=dict(item="meta"))
    ML[b] = rec2(o); ML[b]["mass_loop"] = o["mass"]
out["meta_ledger"] = ML
json.dump(out, open(f"{RES}/t423d_results.json", "w"), indent=1, default=str)
with open(f"{RES}/t423d_passes_{RUN}.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["pass_no", "task", "build", "changed", "M_kg", "kwt_core", "orbit_h", "orbit_ltan", "N98", "N100", "A_rad"])
    for p_ in PASSES: w.writerow([p_["pass_no"], p_["task"], p_["build"], p_["changed"], round(p_["M"], 1), round(p_["kwt"], 2), p_["orbit"][0], p_["orbit"][1], p_["N98"], p_["N100"], round(p_["A_rad"], 1)])
plog.event("milestone", f"t423d run {RUN} done: {PASSNO[0]} passes; results/t423d_results.json", tag=TAG)
print("done", RUN, PASSNO[0])
