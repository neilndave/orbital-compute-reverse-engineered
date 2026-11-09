"""GTC final candidate: single source-of-truth config = frozen GTC scoped baseline (t602/t603) + spin1 recommended additions
(NO peak battery, BOL-grown array, MPG40 glycol swap + NB2F2-port freeze/restart hardware, 4-trunk Whipple shields; headers/spares OPEN), with every
poster-facing number carrying provenance (stage script + traced inputs + sha256 + tool).  Runs inside the pipeline root ($GTCFC_ROOT)."""
import os
import json, hashlib, os, glob, math
ROOT = os.environ.get("GTCFC_ROOT", os.environ["GTCFC_ROOT"]+"")
def rp(p): return os.path.relpath(p, ROOT)
def sha(p): return hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()
def J(p): return json.load(open(os.path.join(ROOT, p)))
# ---- stage provenance from the open() audit traces ----
STAGE_SCRIPT = dict(s00_t600_screen="stages/t600/baseline_plus_deletions.py", s01_baseline_freeze="stages/baseline/freeze_scoped_baseline.py",
    s02_eclipse_600km="stages/orbit/eclipse_600km.py", s03_power="stages/spin1/power_spin1.py", s04_mmod="stages/spin1/mmod_spin1.py",
    s05_mmod_grid="stages/spin1/mmod_grid_spin1.py", s06_mmod_trunk="stages/spin1/mmod_trunk_alloc_spin1.py", s07_thermal_inputs="stages/spin1/gen_thermal_inputs_spin1.py",
    s08_thermal="stages/spin1/thermal_spin1.py", s09_freeze_scen="stages/spin1/freeze/build_scen.py", s10_freeze_transients="stages/spin1/freeze/nbf_spin1.py",
    s11_water_keepwarm="stages/spin1/freeze/water_keepwarm.py", s12_freeze_mass="stages/spin1/freeze/freeze_mass_spin1.py", s13_assemble_spin1="stages/spin1/assemble_spin1.py")
TOOL = "CPU Python 3 (numpy/scipy brentq/CoolProp); deterministic; no GPU in the pipeline itself"
STAGES = {}; PRODUCER = {}
for st, scr in STAGE_SCRIPT.items():
    rows = [json.loads(l) for l in open(f"{ROOT}/trace/{st}.jsonl")] if os.path.exists(f"{ROOT}/trace/{st}.jsonl") else []
    w = sorted({r["path"] for r in rows if r["write"] and not r["path"].endswith(".txt")})
    rd = sorted({r["path"] for r in rows if not r["write"] and r["path"] not in w and r["path"] != scr})
    STAGES[st] = dict(script=scr, script_sha256=sha(scr), inputs={p: sha(p) for p in rd if os.path.isfile(os.path.join(ROOT, p))}, outputs={p: sha(p) for p in w if p != "stage_timings.tsv" and os.path.isfile(os.path.join(ROOT, p))}, tool=TOOL)
    for p in w: PRODUCER.setdefault(p, st)
WARP_TABLE = "inputs/ai1_replica/gb10_final_al/table_AL6061_L26_t0p225.json"   # v2 t619 Al6061 26/0.225 fin
def V(value, unit, src, path, note=None, warp_fin_table=False):
    st = PRODUCER.get(src); d = dict(value=value, unit=unit, source_file=src, json_path=path, stage=st, script=STAGES[st]["script"] if st else None,
                                     script_sha256=STAGES[st]["script_sha256"] if st else None, source_file_sha256=sha(src), tool=TOOL)
    if warp_fin_table: d["upstream_NVIDIA"] = f"fin-efficiency table {WARP_TABLE} (sha256 {sha(WARP_TABLE)[:16]}...) produced by NVIDIA Warp fp64 CUDA on GB10 (fin_al.py, t410 table format, Warp 1.18.0, 2026-11-07 PT for selected August geometry; legacy table retained for June); thermal root re-verified by native Warp fp64 GB10 parity (GB10_FINAL_PARITY_RESULT.json)"
    if note: d["note"] = note
    return d
BASE = "stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"; SP = "stages/spin1/SPIN1_EXACT.json"; TH = "stages/spin1/THERMAL_SPIN1.json"
PW = "stages/spin1/POWER_SPIN1.json"; FM = "stages/spin1/freeze/FREEZE_MASS_SPIN1.json"; EC = "stages/orbit/ECLIPSE_600KM.json"; WK = "stages/spin1/freeze/WATER_KEEPWARM_SPIN1.json"
CFG=J("CONFIG_V3.json")
b = J(BASE); s = J(SP); th = J(TH)["cases"]; pw = J(PW)["cases"]; fm = J(FM); ec = J(EC); wk = J(WK)
x = dict(label="GTC FINAL v3 baseline (all-Al radiator, no peak battery, full-peak BOL array)", configuration_id=CFG["configuration_id"],
         supersedes=dict(configuration_id="AI1_GTC_FINAL_V2_AL",sha256="1cfbdb7793ec72e5509f7cf3a1de071465930565aa0013b3316ef49db072c13e",change="delete peak battery; extend solar wings for actual MPG40 BOL peak; scaled harness/PCDU, view-factor and ram-area propagation"),
         radiator_fin=dict(alloy="Al 6061-T6", k_W_mK=167.0, rho_kg_m3=2700.0, half_length_mm=26.0, thickness_mm=0.225, tube_pitch_mm=60.0, bondline=False, warp_table=WARP_TABLE, area_factor=1.0, coating="unchanged", material_source="ASM/MatWeb 6061-T6 (AA typical)"),
         adopted_baseline=True, status="Owner-approved high-level v3 lock; battery-only v3a preserved; engineering OPEN items retained, not vendor-qualified", geometry_unchanged=False, render_change=True,
         authority=["the author t602/t603: scoped baseline, 0 % weight reserve, 370/378.15 K caps waived for this concept", "the author t605: spin1 items 1-3 (item 3 not rendered)", "the author t606: final-candidate audit", "the author t612-t615: Al-only radiator study (GTC_FINAL_AL)", "the author t619: ADOPT Al option (b) as the new final baseline"],
         mass_reserve_fraction=0.0, mass_reserve_policy="Minimum weight reserve 0 %; all unused mass under the 100 t launch budget is listed as RESERVE (kg/sc, t/launch, % of 100 t) (t615).", launch_payload_budget_kg=100000.0, dispenser_all_in_kg=2000.0,
         orbit=dict(h_km=600, ltan_h=6.0, max_shadow_min=V(ec["max_shadow_min"], "min", EC, "max_shadow_min"), eclipsed_orbits_per_year=V(ec["eclipsed_orbits_per_year"], "1/yr", EC, "eclipsed_orbits_per_year"),
                    mean_shadow_min_when_eclipsed=V(ec["mean_shadow_min_when_eclipsed"], "min", EC, "mean_shadow_min_when_eclipsed"), shadow_hours_per_year=V(ec["shadow_hours_per_year"], "h/yr", EC, "shadow_hours_per_year"),
                    eclipse_strategy="IT paused in eclipse (inherited DECISIONS #65)"),
         selected_additions=dict(item1="NO peak battery; solar array enlarged for full peak at BOL; safe-mode battery 31.25 kg retained", item2="coolant swap water-proxy -> MPG40 (40 wt% PG) with NB2F2-port fin-root heaters (array-powered at sunrise), N2/EPDM insert, accumulator; pumps off in eclipse",
                                 item3="Whipple shields on the 4 central coolant trunks (SPF, bus side, no fin view)"),
         open_items=["radiator header MMOD protection (no simple bumper closes; architecture change needed)", "panel-spare coverage", "deployment/capture/release/interlock hardware (70/120 kg allocation)",
                     "life/hardening/compute provision (50/80 kg allocation)", "EOL peak deficit (94% array retention); EOL growth informational only, not adopted", "MPG40 high-temperature properties, life and pressure qualification still OPEN despite modeled inlet closure", "6061 braze process for the integral/brazed fin-tube panel (narrow braze window; post-braze re-age) not designed", "August selected tube pitch increases tube exposure versus old 60-mm pitch; no tube-resolved ORDEM qualification",
                     "ORDEM-based MMOD flux (NASA90+Gruen used)", "launcher same-orbit performance, finite-hardware packing/CG, qualification"],
         fleets=[])
for i, f in enumerate(b["fleets"]):
    nm = f["case"]; WARP_TABLE=CFG["august_radiator"]["table_rel"] if nm=="August" else "inputs/ai1_replica/gb10_final_al/table_AL6061_L26_t0p225.json"; sf = s["fleets"][i]; T = th[nm]; nom = T["T2_rec_nominal_MPG40_plus_recharge"]; pk = T["T1_MPG40_peak"]; P = pw[nm]; bat = P["battery_table"]["30min"]
    fz = fm[nm]; tag = ["J8", "A4"][i]; arr=P["adopted_array"]
    def out(case): return f"stages/spin1/freeze/out_{tag}_MPG40_{case}.json"
    oc = J(out("cold_qt40")); ot = J(out("table_qt40")); o60 = J(out("cold_qt60")); o550 = J(out("cold_qt40_e550max")); ow = J(f"stages/spin1/freeze/out_{tag}_water_cold_qt40.json")
    thk = f"cases/{nm}"; bk = f"fleets[{i}]"; sk = f"fleets[{i}]"
    n_ecl = ec["eclipsed_orbits_per_year"]; yr_h = 8766.0
    down_h = oc["t_open_min"] * n_ecl / 60.0
    trunk = sf["item3_mmod"]["trunk_SPF_recommended"]; hdr1 = sf["item3_mmod"]["header_N_le_1_ledger_routing"]
    F = dict(case=nm, point=f"{tag}_C1",
      spacecraft_count=V(f["count"], "-", BASE, f"{bk}.count"),
      installed_peak_per_sc_kW=V(f["peak_per_sc_kW"], "kW", BASE, f"{bk}.peak_per_sc_kW"),
      nominal_per_sc_kW=V(f["nominal_per_sc_kW"], "kW", BASE, f"{bk}.nominal_per_sc_kW"),
      installed_peak_per_launch_MW=V(f["peak_installed_compute_MW"], "MW", BASE, f"{bk}.peak_installed_compute_MW", "installed peak compute-power-equivalent rating; not continuous delivery"),
      nominal_IT_per_launch_MW=V(f["nominal_fleet_IT_MW"], "MW", BASE, f"{bk}.nominal_fleet_IT_MW"),
      sc_mass_kg=V(sf["sc_mass_kg"], "kg", SP, f"{sk}.sc_mass_kg"), launch_mass_kg=V(sf["launch_total_kg"], "kg", SP, f"{sk}.launch_total_kg", "includes 2 t all-in dispenser; 0 % weight reserve"),
      headroom_to_100t_kg=V(sf["margin_to_100t_kg"], "kg", SP, f"{sk}.margin_to_100t_kg", "alias of reserve_kg (t615)"),
      reserve_kg=V(sf["margin_to_100t_kg"], "kg", SP, f"{sk}.margin_to_100t_kg", "RESERVE per launch = all unused mass under 100 t (0 % minimum)"),
      reserve_kg_per_sc=dict(value=sf["margin_to_100t_kg"] / f["count"], unit="kg", derivation="reserve_kg / spacecraft_count"),
      reserve_t_per_launch=dict(value=sf["margin_to_100t_kg"] / 1000.0, unit="t", derivation="reserve_kg / 1000"),
      reserve_pct_of_100t=dict(value=sf["margin_to_100t_kg"] / 1000.0, unit="%", derivation="reserve_kg / 100000 x 100"),
      ledger_kg=V(sf["ledger_kg"], "kg", SP, f"{sk}.ledger_kg"),
      GPU_nominal_K=V(nom["GPU_K"], "K", TH, f"{thk}.T2_rec_nominal_MPG40_plus_recharge.GPU_K", warp_fin_table=True),
      HBM_nominal_K=V(nom["HBM_K"], "K", TH, f"{thk}.T2_rec_nominal_MPG40_plus_recharge.HBM_K", warp_fin_table=True),
      GPU_peak_K=V(pk["GPU_K"], "K", TH, f"{thk}.T1_MPG40_peak.GPU_K", "full-peak steady sunlit BOL diagnostic; no battery; eclipse/restart pause retained", warp_fin_table=True),
      HBM_peak_K=V(pk["HBM_K"], "K", TH, f"{thk}.T1_MPG40_peak.HBM_K", warp_fin_table=True),
      coolant_supply_nominal_K=V(nom["coolant_supply_K"], "K", TH, f"{thk}.T2_rec_nominal_MPG40_plus_recharge.coolant_supply_K", warp_fin_table=True),
      coolant_radiator_inlet_nominal_K=V(nom["coolant_radiator_inlet_K"], "K", TH, f"{thk}.T2_rec_nominal_MPG40_plus_recharge.coolant_radiator_inlet_K", warp_fin_table=True),
      coolant_radiator_inlet_peak_K=V(pk["coolant_radiator_inlet_K"], "K", TH, f"{thk}.T1_MPG40_peak.coolant_radiator_inlet_K", "compare with 393 K requested limit and 393.15 K source recommendation; model closure is not fluid qualification", warp_fin_table=True),
      rack_rise_K=V(20.0, "K", TH, f"{thk}.T2 (fixed dT_loop 20 K in operating())", "ASSUMED loop convention"),
      radiator_rise_nominal_K=V(nom["radiator_delta_K"], "K", TH, f"{thk}.T2_rec_nominal_MPG40_plus_recharge.radiator_delta_K"), radiator_rise_peak_K=V(pk["radiator_delta_K"], "K", TH, f"{thk}.T1_MPG40_peak.radiator_delta_K"),
      rejected_heat_nominal_W=V(nom["total_solar_power_and_rejected_heat_W"], "W", TH, f"{thk}.T2_rec_nominal_MPG40_plus_recharge.total_solar_power_and_rejected_heat_W"),
      radiator_effective_area_m2=V(T["geometry_v3"]["radiator_face_area_m2"], "m2", TH, f"{thk}.geometry_v3.radiator_face_area_m2"), radiator_panels=V(T["geometry_v3"]["radiator_panels"], "-", TH, f"{thk}.geometry_v3.radiator_panels"),
      solar_area_m2=V(arr["area_m2"], "m2", PW, f"cases/{nm}.adopted_array.area_m2"),
      coolant=dict(fluid="MPG40 (40 wt% propylene glycol), CoolProp INCOMP::MPG[0.4]", liquidus_K=252.05,
                   loop_package_kg=V(sf["ledger_kg"]["coolant_loop"], "kg", SP, f"{sk}.ledger_kg.coolant_loop"), MPG40_inventory_kg=V(fz["MPG40_inventory_kg"], "kg", FM, f"{nm}.MPG40_inventory_kg"),
                   mass_flow_kg_s=V(nom["mass_flow_kg_s"], "kg/s", TH, f"{thk}.T2_rec_nominal_MPG40_plus_recharge.mass_flow_kg_s"), swap_delta_kg=V(T["coolant_line_delta_kg"], "kg", TH, f"{thk}.coolant_line_delta_kg")),
      battery=dict(adopted=False,total_kg=V(0.0,"kg",PW,f"cases/{nm}.adopted_array.peak_battery_kg"),safe_mode_kg=31.25,note="31.25 kg safe-mode pack retained once inside freeze hardware; no peak pack/BCDR/radiator/heaters/integration/recharge"),
      array_v3={k: V(v,"kg/m2" if k=="kg_per_m2_inherited" else "m2" if "area" in k and "ratio" not in k and "frac" not in k and "view" not in k else "kg" if "kg" in k else "W" if k.endswith("_W") else "m" if k.endswith("_m") else "-",PW,f"cases/{nm}.adopted_array.{k}") for k,v in arr.items() if isinstance(v,(int,float)) and not isinstance(v,bool)},
      freeze_restart=dict(hardware_kg=V(fz["freeze_hw_total_kg"], "kg", FM, f"{nm}.freeze_hw_total_kg"), allocation_kg=fz["allocation_kg"], pass_hardware=fz["pass_hw_only"], pass_incl_glycol_swap=fz["pass_incl_swap"],
                   heater_kW=V(oc["heater_kW"], "kW", out("cold_qt40"), "heater_kW"), restart_open_min_cold=V(oc["t_open_min"], "min", out("cold_qt40"), "t_open_min"),
                   restart_open_min_table=V(ot["t_open_min"], "min", out("table_qt40"), "t_open_min"), restart_open_min_60Wm=V(o60["t_open_min"], "min", out("cold_qt60"), "t_open_min"),
                   restart_open_min_550km_envelope=V(o550["t_open_min"], "min", out("cold_qt40_e550max"), "t_open_min", "21.66-min eclipse (550-km t590 count) conservative sensitivity"),
                   tube_min_K=V(oc["T_tube_fluid_min_in_eclipse"], "K", out("cold_qt40"), "T_tube_fluid_min_in_eclipse"), header_fluid_min_K=V(oc["T_header_fluid_min_in_eclipse"], "K", out("cold_qt40"), "T_header_fluid_min_in_eclipse"),
                   slush_max=V(oc["ice_max_tube"], "-", out("cold_qt40"), "ice_max_tube", "clamped at 0.385 (Dow-data limit)"),
                   added_downtime_h_per_yr=dict(value=down_h, unit="h/yr", derivation=f"t_open_min(cold,40 W/m) x eclipsed_orbits_per_year / 60 = {oc['t_open_min']} x {n_ecl} / 60", sources=[out("cold_qt40"), EC]),
                   added_downtime_frac=dict(value=down_h / yr_h, unit="-", derivation="/ 8766 h"), eclipse_pause_frac=dict(value=ec["shadow_hours_per_year"] / yr_h, unit="-", derivation="shadow_hours_per_year / 8766 h", sources=[EC]),
                   water_pumps_off=dict(ice_max_tube=ow["ice_max_tube"], t_open_min=ow["t_open_min"], verdict="FAIL (freezes solid)"),
                   water_keepwarm_battery_kg=V(wk[nm]["battery_pack_kg"], "kg", WK, f"{nm}.battery_pack_kg", "alternative rejected: exceeds allocation")),
      mmod=dict(trunk_shield_kg=V(trunk["total_kg"], "kg", SP, f"{sk}.item3_mmod.trunk_SPF_recommended.total_kg"), trunk_PNP_5yr_flux_x3=V(trunk["PNP"], "-", SP, f"{sk}.item3_mmod.trunk_SPF_recommended.PNP"),
                allocation_kg=f["ledger"][[r["item"] for r in f["ledger"]].index("MMOD_spare_panel_allocation")]["kg"],
                header_unprotected_N_5yr=V(sf["item3_mmod"]["unprotected"]["ledger"]["N_5yr"], "-", SP, f"{sk}.item3_mmod.unprotected.ledger.N_5yr"),
                header_N_le_1_kg=V(hdr1["total_kg"], "kg", SP, f"{sk}.item3_mmod.header_N_le_1_ledger_routing.total_kg", "OPEN legacy long-edge shield comparison; new rerouted options and finite stow in overall review"),
                header_status="OPEN", spares_status="OPEN"),
      open_item_allocations_kg=dict(deployment_mechanisms=sf["ledger_kg"]["deployment_mechanisms"], MMOD_spare_panel_allocation=sf["ledger_kg"]["MMOD_spare_panel_allocation"],
                                    freeze_restart_including_battery=sf["ledger_kg"]["freeze_restart_including_battery"], life_and_compute_provision=sf["ledger_kg"]["life_and_compute_provision"]),
      baseline_reference=dict(launch_mass_kg=f["launch_total_kg"], GPU_nominal_K=f["nominal"]["GPU_K"], HBM_nominal_K=f["nominal"]["HBM_K"], GPU_peak_K=f["full_peak_steady_sensitivity"]["GPU_K"]))
    if nm=='August':
        F['radiator_fin']=CFG['august_radiator'];F['radiator_film_nominal']=nom['radiator_film'];F['radiator_film_peak']=pk['radiator_film']
    x['fleets'].append(F)
x["config_v3"] = dict(file="CONFIG_V3.json",sha256=sha("CONFIG_V3.json"),parameters=J("CONFIG_V3.json"))
x["authority"].append("owner approved peak-battery deletion and BOL array growth, 2026-11-07 18:26 PT")
x["proposal_pending_confirmation"]=CFG["proposal_pending_confirmation"]
x["authority"].append("Owner lock 2026-11-07 20:54 PT: 140 panels, deleted peak battery, full freeze hardware charged; engineering and reference-allocation FAIL/OPEN items remain visible.")
x["radiator_fin"]["scope"]="Legacy June only; final August fin specification is fleets/August/radiator_fin"
x["application"]="August AI1 application; June retained as legacy DR comparison, not in poster"
x["NVIDIA_design_decision"]=J("inputs/NVIDIA_DECISION_V3.json")
x["NVIDIA_design_decision_source"]=dict(file="inputs/NVIDIA_DECISION_V3.json",sha256=sha("inputs/NVIDIA_DECISION_V3.json"),scope="Frozen GB10 decision experiment; timings are measured inputs, not rerun-dependent pipeline outputs")
x["stages"] = STAGES
x["NVIDIA_upstream_inputs"]={}
for month,table in [('June','inputs/ai1_replica/gb10_final_al/table_AL6061_L26_t0p225.json'),('August',CFG['august_radiator']['table_rel'])]:
    x['NVIDIA_upstream_inputs'][table]=dict(sha256=sha(table),produced_by='Native NVIDIA Warp fp64 finite-volume fin table, 585 points, 320 x 8 grid; selected August regenerated on GB10 cuda:0 2026-11-07 PT; legacy June table retained and rechecked',used_by=month+' coolant/GPU/HBM root; not the other fleet')
x['NVIDIA_upstream_inputs']['inputs/ai1_replica/gb10_final_al/screen_al_fine.json']=dict(sha256=sha('inputs/ai1_replica/gb10_final_al/screen_al_fine.json'),produced_by='Historical v2 Al fin screen',used_by='June legacy Al/K13D mass ratio ONLY; final August uses explicit sheet/round-annulus/fluid geometry')
x['authority'].append('2026-11-07 18:58 PT: August application only; NVIDIA sweep drives geometry. August nominal GPU study cap 370 K and inlet cap 393 K; full-peak chip limits and robust uncertainty closure remain OPEN. June is preserved legacy comparison.')
x['NVIDIA_tools_evidence']=J('inputs/NVIDIA_TOOL_EVIDENCE_V3.json')
x['NVIDIA_tools_evidence_source']=dict(file='inputs/NVIDIA_TOOL_EVIDENCE_V3.json',sha256=sha('inputs/NVIDIA_TOOL_EVIDENCE_V3.json'))
x['builder']=dict(script='final/build_final.py',sha256=sha('final/build_final.py'))
json.dump(x, open("GTC_FINAL_CANDIDATE.json", "w"), indent=1, sort_keys=False); print("written GTC_FINAL_CANDIDATE.json")
