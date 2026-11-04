# t423e-FP: first-principles stack (the author 4:40 PM PT rule) + t423f kW/t definition sensitivity.  Every number below is ESTIMATE unless tagged STATEMENT.  No repo/baseline/DECISIONS edits.
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
src = open(os.path.join(HERE, "t423e_run.py")).read().split("CASES = []")[0]
ns = {"__file__": os.path.join(HERE, "t423e_run_.py")}; exec(src, ns)
T, ap, W0, W0f, LV, ORB_FCC, addb, O, rec, RES = [ns[k] for k in ("T", "ap", "W0", "W0f", "LV", "ORB_FCC", "addb", "O", "rec", "RES")]
CR, ST, NC, S3J, PD3 = ns["CR"], ns["ST"], ns["NC"], ns["S3J"], ns["PD3"]
# ------------------------------------------------------------------ first-principles derivations
def pcdu_kwkg(base=12.0, derate=1.2, rad=1.3, redund=1.15, housing=1.2):
    """base = best DEMONSTRATED ground converter specific power (GE 1 MW SiC/Si 12 kVA/kg, STATEMENT NASA/OSTI; HLMC 13 kW/1 kg air-cooled, STATEMENT NASA keynote); multipliers are ESTIMATE
    derate: 300 V bus on devices run <=50% of VDS rating (NEPP Lauenstein SEB); rad: hermetic/ceramic pkg + local shielding; redund: N+1 on ~8 modules; housing: EMI/enclosure/cold-plate mount."""
    mult = derate * rad * redund * housing; return base / mult, mult
def harness_kg(P_kW, V=300.0, loss=0.01, L_one_way=15.0, k_ins=1.5):
    """Al conductors sized for resistive loss fraction at the peak current: m = d*rho_e*L^2*I^2/(loss*P), L = total conductor path (out+back); k_ins for insulation/connectors/supports (ESTIMATE)."""
    I = P_kW * 1e3 / V; L = 2 * L_one_way; m = 2700.0 * 2.82e-8 * L * L * I * I / (loss * P_kW * 1e3); return m * k_ins, I
def rack_fp(bold=False):
    """kg per 72-GPU (132 kW TDP, STATEMENT HPE) unit, bottom-up: only compute silicon + essential power delivery + cold plate + cabling.  All masses ESTIMATE (geometry x density / vendor-class densities)."""
    g = 0.15 if bold else 0.22      # GPU package: substrate 100x100x1.2mm (~25 g) + interposer/dies/8 HBM stacks + Cu lid (~80 g) + solder; bold removes the lid
    cp = 0.10 if bold else 0.15     # cold plate (Al/Cu microchannel) for ~1.3 kW over ~7 cm2 die area
    vpd = 0.30 if bold else 0.40    # 48V->1V current multiplier + regulator + caps for 1.2 kW at ~3-4 kW/kg (Vicor-class 5 A/mm2 STATEMENT, mass ESTIMATE)
    pcb = 0.10                      # board share
    gpu = 72 * (g + cp + vpd + pcb)
    grace = 36 * (0.45 if not bold else 0.35)            # Grace pkg + LPDDR5X + cold plate + VRM
    nic = 36 * 0.15                                     # DPU/NIC boards
    sw = 9 * (2.2 if not bold else 1.6)                 # NVSwitch tray w/o chassis: 2 ASICs + PCB + cold plate + VRM
    nvl = 25.0 if not bold else 15.0                    # ~5,000 coax cables / 2 miles Cu (STATEMENT NVIDIA), mass ESTIMATE; bold = fewer/shorter
    bus = 6.0                                           # 300 V Al busbar ~500 A @ 1 A/mm2, ~2 m x2
    ibc = 132.0 / 5.5                                   # 300 V -> 48 V intermediate stage at 5.5 kW/kg (same FP class as PCDU)
    tot = (gpu + grace + nic + sw + nvl + bus + ibc) * 1.15      # 15% connectors/EMI/mounting
    return tot, dict(gpu=gpu, grace=grace, nic=nic, sw=sw, nvl=nvl, bus=bus, ibc=ibc, total=tot)
def array_fp(cell_wkg, n):   # wing W/kg (BOL, 3J-area basis): P_dens/(n + P_dens/Wcell)
    return PD3 / (n + PD3 / cell_wkg)
rk_b, rk_d = rack_fp(False), rack_fp(True)
pc_b, pc_mult = pcdu_kwkg(); pc_d, _ = pcdu_kwkg(base=19.0)
info = dict(rack_base=rk_b[1], rack_bold=rk_d[1], rack_kg_per_kW_base=rk_b[0] / 132.0, rack_kg_per_kW_bold=rk_d[0] / 132.0, pcdu_base=pc_b, pcdu_bold=pc_d, pcdu_mult=pc_mult,
            wing_base=array_fp(884.0, 0.25), wing_bold=array_fp(2000.0, 0.20))
print(json.dumps(info, indent=1))
LV.update({"FPr_b": dict(f_strip=0.0, rack_kg=rk_b[0] / 132.0 * 188.0, rack_scale=True), "FPr_d": dict(f_strip=0.0, rack_kg=rk_d[0] / 132.0 * 188.0, rack_scale=True),
           "FPp_b": dict(pcdu_kwkg=pc_b), "FPp_d": dict(pcdu_kwkg=pc_d), "FPs_b": dict(f_struct=0.06), "FPs_d": dict(f_struct=0.05),
           "FPa_b": dict(cell="3J", wkg_wing=info["wing_base"], arr_deg=0.01), "FPa_d": dict(cell="3J", wkg_wing=info["wing_bold"], arr_deg=0.01)})
def with_harness(b, p, loss, L):
    P = O.TARGET[b]["P"]; r = P / O.P_IT_REF; H, I = harness_kg(P, 300.0, loss, L); q = dict(p); q["harness_V"] = 349.2 * r * q.get("pmad", 0.5) * 100.0 / H; return q, H
def run(b, ids, scale="scaled", harn=(0.01, 15.0), **kw):
    p = ap(W0[b], ids, **kw)
    if harn: p, H = with_harness(b, p, *harn)
    o = T.best_orbit(b, p, ORB_FCC); r = rec(o); r["fcc_ok"] = not o["fcc_flags"]; r["fcc_flags"] = o["fcc_flags"]; r["tgt"] = O.TARGET[b]["kwt"]; r["o"] = o; return r
BASE_ST = ["R2", "S1", "E1c", "P1", "E2", "D1", "D2", "A2", "C_str", "PCs"]
FP_B = ["E1c", "P1", "E2", "D1", "D2", "A2", "C_str", "FPr_b", "FPp_b", "FPs_b", "FPa_b"]
FP_D = ["E1c", "P1", "E2", "D1", "D2", "A2", "C_str", "FPr_d", "FPp_d", "FPs_d", "FPa_d"]
OUT = {"info": info}
for b in ("Jun8", "Aug4"):
    d = {}
    # reference lines
    d["ref_credible"] = run(b, CR, wkg_wing=124.0, harn=None); d["ref_stretch300"] = run(b, ST, wkg_wing=300.0, harn=None)
    # ladder: start at stretch@300 (t423d) then swap each lever to its first-principles value
    lad = [("stretch@300 (t423d)", BASE_ST, {}), ("+FP array (884 W/kg cell, 0.25 kg/m2 blanket, 1%/yr)", [i for i in BASE_ST] , dict(cell="3J", wkg_wing=info["wing_base"], arr_deg=0.01))]
    cur = list(BASE_ST); steps = []
    steps.append(("stretch (t423d, wing 300)", dict(ids=list(cur), kw=dict(wkg_wing=300.0), h=None)))
    kw = dict(cell="3J", wkg_wing=info["wing_base"], arr_deg=0.01); steps.append(("+array FP", dict(ids=list(cur), kw=dict(kw), h=None)))
    cur2 = [i for i in cur if i not in ("R2", "PCs")] + ["FPr_b"]; steps.append(("+rack FP", dict(ids=list(cur2), kw=dict(kw), h=None)))
    cur3 = [i for i in cur2] + ["FPp_b"]; steps.append(("+PCDU FP", dict(ids=list(cur3), kw=dict(kw), h=None)))
    cur4 = cur3 + ["FPs_b"]; steps.append(("+structure FP", dict(ids=list(cur4), kw=dict(kw), h=None)))
    steps.append(("+harness FP", dict(ids=list(cur4), kw=dict(kw), h=(0.01, 15.0))))
    d["ladder"] = []
    for nm, s in steps:
        r = run(b, s["ids"], harn=s["h"], **s["kw"]); d["ladder"].append(dict(step=nm, **{k: r[k] for k in ("M", "kwt", "kwt_ab", "N98", "N100", "N98_ab", "A_rad", "A_arr", "fcc_flags")}, lines=r["lines"]))
    d["FP_base"] = run(b, FP_B); d["FP_bold"] = run(b, FP_D)
    # conservative-FP: credible-class numbers for the same stack structure (everything flown-class) is ref_credible
    OUT[b] = d
    for k in ("ref_credible", "ref_stretch300", "FP_base", "FP_bold"):
        r = d[k]; print(b, k, "M", round(r["M"]), "kwt", round(r["kwt"], 1), "ab", round(r["kwt_ab"], 1), "N98", r["N98"], "N98ab", r["N98_ab"], "A_rad", round(r["A_rad"]), "A_arr", round(r["A_arr"]), r["fcc_flags"], {a: round(c) for a, c in r["lines"].items()})
    for s in d["ladder"]: print("   ", s["step"], round(s["M"]), round(s["kwt"], 1), round(s["kwt_ab"], 1), s["N98"])
# ---------------- t423f: kW/t definition sensitivity (peak vs average, IT vs array, wet vs dry)
F = {}
for b in ("Jun8", "Aug4"):
    for nm in ("ref_credible", "ref_stretch300", "FP_base", "FP_bold"):
        o = OUT[b][nm]["o"]; P = o["P_kW"]; M = o["M_kg"]; Md = o["M_dry_kg"]
        eol = 1 - o["avg_over_peak"] * 0  # placeholder
        arr_nameplate_kW = o["A_arr"] * 319.7 / 1000.0 * (0.72 if False else 1.0)       # BOL array nameplate at 319.7 W/m2 (3J-area basis; all stacks here are 3J)
        F[f"{b}|{nm}"] = dict(P_IT_peak=P, M=M, M_dry=Md, kwt_peak_wet=P / M * 1e3, kwt_peak_dry=P / Md * 1e3, kwt_avg_wet=o["kwt_avg_wet"], kwt_avg_dry=P * o["avg_over_peak"] / Md * 1e3,
                              kwt_array_nameplate_wet=arr_nameplate_kW / M * 1e3, kwt_array_nameplate_dry=arr_nameplate_kW / Md * 1e3, avg_over_peak=o["avg_over_peak"], tgt=O.TARGET[b]["kwt"],
                              tgt_avg_equiv=O.TARGET[b]["kwt"] * 0.8 if b == "Jun8" else O.TARGET[b]["kwt"] * 0.7)
for b in ("Jun8", "Aug4"):
    for nm in OUT[b]:
        if isinstance(OUT[b][nm], dict) and "o" in OUT[b][nm]: OUT[b][nm].pop("o")
OUT["t423f"] = F
json.dump(OUT, open(f"{RES}/t423e_fp.json", "w"), indent=1, default=str)
for k, v in F.items(): print(k, {a: round(c, 1) for a, c in v.items()})
