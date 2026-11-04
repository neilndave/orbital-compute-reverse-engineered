# t434: write the 6 replica design-point parameter files (C1, MID, C2 x Jun8, Aug4) from results/t434_region.json (t423g model).  Box only; never edits repo files.
# Also writes the Newton overlay trees (unchanged repo scripts + replica inputs under the baseline file names) and the thermal builds file for the GB10 bundle.
import os, sys, json, math, shutil, datetime as dt
H = os.path.dirname(os.path.abspath(__file__)); REPO = "vendor/same_rack"; GB = f"{H}/gb10_gtc"
d = json.load(open(f"{H}/results/t434_region.json"))
PW, PL = 363.4175776637853, 2944.5579551660426        # mm, adopted A6L radiator panel (repo results/fleet/fleet_layout_T45.json)
PANEL_M2 = PW * PL * 1e-6
AVG_OVER_PEAK = {"Jun8": 0.80, "Aug4": 0.70}           # orbit_loop.TARGET (t423 loop)
SHORT = {"Jun8": "J8", "Aug4": "A4"}
os.makedirs(f"{H}/gtc_params", exist_ok=True); os.makedirs(f"{GB}/params", exist_ok=True)
BASE_ARRAY_KG, BASE_BOOM = 2524.2966751918093, 24.5
pts = {}
for key, r in d["points"].items():
    b, nm = key.split("|"); pid = f"{SHORT[b]}_{nm}"; P = r["P"]; L = r["lines"]
    n_pan = math.ceil(r["A_rad"] / PANEL_M2); leaf_len = r["A_arr"] / (2 * 14.0 * 20); wing_len = leaf_len * 20
    prm = dict(id=pid, build=b, point=nm, source="t423g model via t434_region.py (ESTIMATE); knobs below", generated=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        targets=dict(kWt=O if (O := {"Jun8": 70.0, "Aug4": 75.0}[b]) else 0, sats_per_starship_98t={"Jun8": 46, "Aug4": 30}[b]),
        knobs=r["knobs"], rack_kg_per_kW=r["k_rack"], wing_W_per_kg=r["wing"],
        result=dict(P_IT_peak_kW=P, P_IT_avg_kW=round(P * AVG_OVER_PEAK[b], 3), mass_kg=r["M"], kW_per_t=r["kwt"], sats_per_98t=r["N98"], sats_per_100t=r["N100"], orbit_h_km=r["orbit"][0], ltan_h=r["orbit"][1], fcc_flags=r["fcc"]),
        areas=dict(A_rad_face_m2=r["A_rad"], A_arr_m2=r["A_arr"], FCC=dict(mass_kg=4000, A_rad_m2=200, A_arr_m2=1500)),
        mass_lines_kg=L,
        geometry_derived=dict(label="ASSUMED/ESTIMATE: same panel and array architecture as the adopted baseline, scaled to the replica areas",
            radiator=dict(panel_W_mm=PW, panel_L_mm=PL, panel_planform_m2=round(PANEL_M2, 5), n_panels=n_pan, n_panels_basis="ceil(A_rad_face / panel planform); baseline 254 panels = 271.8 m2 vs 273.5 m2 stated per face"),
            array=dict(width_m=14.0, leaves_per_wing=20, wings=2, leaf_len_m=round(leaf_len, 5), wing_len_m=round(wing_len, 4), yoke_root_m=1.968278816700644, basis="A_arr / (2 wings x 14 m x 20 leaves); yoke kept at baseline (ASSUMED)"),
            bus=dict(rack_envelope_m=[0.6, 1.2, 2.296], note="packer uses the repo bus model: BX 0.7, BY 2.0, BUS_Z0 + V_eq/(BX BY), V_eq scaled (0.338+0.662 f), f = P/188; rack volume NOT changed with kg/kW (rack density differs between C1 and C2 only in mass: ASSUMED)", f_power=round(P / 188.0, 4))),
        newton_overlay_inputs=dict(m_array_kg=L["array"], A_array_m2=r["A_arr"], wing_len_m=wing_len, array_width_m=14.0, yoke_root_m=1.968278816700644, mass_gaps_ratio_array=L["array"] / BASE_ARRAY_KG, base_kg=r["M"] - L["array"]))
    json.dump(prm, open(f"{H}/gtc_params/point_{pid}.json", "w"), indent=1); shutil.copy(f"{H}/gtc_params/point_{pid}.json", f"{GB}/params/point_{pid}.json"); pts[pid] = prm
    print(pid, "mass", round(r["M"], 1), "n_pan", n_pan, "leaf_len", round(leaf_len, 3), "array_kg", L["array"], "rack_kg", L["rack"])
# thermal builds for the runner (peak W, avg W, A m2): the loop-sized areas, one per build (C1/MID/C2 share them: thermal does not see rack or array mass)
tb = [[f"{SHORT[b]}_loop", pts[f"{SHORT[b]}_C1"]["result"]["P_IT_peak_kW"] * 1e3, pts[f"{SHORT[b]}_C1"]["result"]["P_IT_avg_kW"] * 1e3, pts[f"{SHORT[b]}_C1"]["areas"]["A_rad_face_m2"]] for b in ("Jun8", "Aug4")]
json.dump(dict(builds=tb, note="id, peak W, avg W, radiating face area m2 (t423g loop sizing); identical for C1, MID and C2"), open(f"{GB}/params/thermal_builds.json", "w"), indent=1)
# Newton overlays: unchanged repo scripts + replica input JSONs under the baseline (_T45) file names, so RTS_TAG=_T45 reads replica values
SRC = [("experiments/phase2/fold_chain_T45.py",), ("experiments/phase2/newton_xcheck_T45.py",), ("experiments/newton_array/run_array.py",), ("experiments/newton_deploy/run_hinge.py",), ("src/rack_two_skies/__init__.py",), ("src/rack_two_skies/design_tag.py",)]
od = json.load(open(f"{REPO}/results/full3d/optimized_design_T45.json")); mg = json.load(open(f"{REPO}/results/audit/mass_gaps_T45.json"))
for pid, p in pts.items():
    o = f"{GB}/newton/overlay_{pid}"
    for (s,) in SRC: os.makedirs(f"{o}/{os.path.dirname(s)}", exist_ok=True); shutil.copy2(f"{REPO}/{s}", f"{o}/{s}")
    for sub in ("results/full3d", "results/audit", "results/phase2_T45"): os.makedirs(f"{o}/{sub}", exist_ok=True)
    ni = p["newton_overlay_inputs"]; x = json.loads(json.dumps(od)); x["metrics"]["m_array_kg"] = ni["m_array_kg"]; x["metrics"]["A_array_m2"] = ni["A_array_m2"]; x["v"]["array_width_m"] = ni["array_width_m"]; x["v"]["array_root_m"] = ni["yoke_root_m"]; x["full"]["wing_len_m"] = ni["wing_len_m"]
    x["_replica_note"] = f"replica {pid} inputs written under the baseline file name for the overlay only (t434); not the adopted baseline"
    json.dump(x, open(f"{o}/results/full3d/optimized_design_T45.json", "w"), indent=1)
    g = json.loads(json.dumps(mg)); g["ratios"]["array"] = ni["mass_gaps_ratio_array"]; g["base_kg"] = ni["base_kg"]; g["_replica_note"] = x["_replica_note"]
    json.dump(g, open(f"{o}/results/audit/mass_gaps_T45.json", "w"), indent=1)
