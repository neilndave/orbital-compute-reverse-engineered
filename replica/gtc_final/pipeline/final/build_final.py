"""GTC final candidate: single source-of-truth config = frozen GTC scoped baseline (t602/t603) + spin1 recommended additions
(30-min peak battery, MPG40 glycol swap + NB2F2-port freeze/restart hardware, 4-trunk Whipple shields; headers/spares OPEN), with every
poster-facing number carrying provenance (stage script + traced inputs + sha256 + tool).  Runs inside the pipeline root (/tmp/gtcv2_root)."""
import json, hashlib, os, glob, math
ROOT = os.environ.get("GTCFC_ROOT", "/tmp/gtcv2_root")
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
    STAGES[st] = dict(script=scr, script_sha256=sha(scr), inputs={p: sha(p) for p in rd if os.path.isfile(os.path.join(ROOT, p))}, outputs={p: sha(p) for p in w if os.path.isfile(os.path.join(ROOT, p))}, tool=TOOL)
    for p in w: PRODUCER.setdefault(p, st)
WARP_TABLE = "inputs/ai1_replica/gb10_final_al/table_AL6061_L26_t0p225.json"   # v2 t619 Al6061 26/0.225 fin
def V(value, unit, src, path, note=None, warp_fin_table=False):
    st = PRODUCER.get(src); d = dict(value=value, unit=unit, source_file=src, json_path=path, stage=st, script=STAGES[st]["script"] if st else None,
                                     script_sha256=STAGES[st]["script_sha256"] if st else None, source_file_sha256=sha(src), tool=TOOL)
    if warp_fin_table: d["upstream_NVIDIA"] = f"fin-efficiency table {WARP_TABLE} (sha256 {sha(WARP_TABLE)[:16]}...) produced by NVIDIA Warp fp64 CUDA on GB10 (fin_al.py, t410 table format, Warp 1.18.0, 2026-11-06 PT); thermal root re-verified by native Warp fp64 GB10 parity (GB10_FINAL_PARITY_RESULT.json)"
    if note: d["note"] = note
    return d
BASE = "stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"; SP = "stages/spin1/SPIN1_EXACT.json"; TH = "stages/spin1/THERMAL_SPIN1.json"
PW = "stages/spin1/POWER_SPIN1.json"; FM = "stages/spin1/freeze/FREEZE_MASS_SPIN1.json"; EC = "stages/orbit/ECLIPSE_600KM.json"; WK = "stages/spin1/freeze/WATER_KEEPWARM_SPIN1.json"
b = J(BASE); s = J(SP); th = J(TH)["cases"]; pw = J(PW)["cases"]; fm = J(FM); ec = J(EC); wk = J(WK)
x = dict(label="GTC FINAL v2 baseline (scoped baseline t602/t603 + spin1 additions + t619 all-aluminium radiator, GTC_FINAL_AL option (b))", configuration_id="AI1_GTC_FINAL_V2_AL",
         supersedes=dict(configuration_id="AI1_GTC_FINAL_CANDIDATE_v1", sha256="b89c202f6372032f0337f4cb81888e99df3f5c7290745c26fac786c4f0a24d00", change="K13D70 30/0.20 bonded CFRP fins -> Al 6061-T6 26 mm / 0.225 mm integral/brazed fins, same 77/128 panels"),
         radiator_fin=dict(alloy="Al 6061-T6", k_W_mK=167.0, rho_kg_m3=2700.0, half_length_mm=26.0, thickness_mm=0.225, tube_pitch_mm=60.0, bondline=False, warp_table=WARP_TABLE, area_factor=1.0, coating="unchanged", material_source="ASM/MatWeb 6061-T6 (AA typical)"),
         adopted_baseline=True, status="FINAL v2 baseline (adopted t619); not published; not vendor-qualified", geometry_unchanged=True, render_change=False,
         authority=["the author t602/t603: scoped baseline, 0 % weight reserve, 370/378.15 K caps waived for this concept", "the author t605: spin1 items 1-3 (item 3 not rendered)", "the author t606: final-candidate audit", "the author t612-t615: Al-only radiator study (GTC_FINAL_AL)", "the author t619: ADOPT Al option (b) as the new final baseline"],
         mass_reserve_fraction=0.0, mass_reserve_policy="Minimum weight reserve 0 %; all unused mass under the 100 t launch budget is listed as RESERVE (kg/sc, t/launch, % of 100 t) (t615).", launch_payload_budget_kg=100000.0, dispenser_all_in_kg=2000.0,
         orbit=dict(h_km=600, ltan_h=6.0, max_shadow_min=V(ec["max_shadow_min"], "min", EC, "max_shadow_min"), eclipsed_orbits_per_year=V(ec["eclipsed_orbits_per_year"], "1/yr", EC, "eclipsed_orbits_per_year"),
                    mean_shadow_min_when_eclipsed=V(ec["mean_shadow_min_when_eclipsed"], "min", EC, "mean_shadow_min_when_eclipsed"), shadow_hours_per_year=V(ec["shadow_hours_per_year"], "h/yr", EC, "shadow_hours_per_year"),
                    eclipse_strategy="IT paused in eclipse (inherited DECISIONS #65)"),
         selected_additions=dict(item1="30-min-per-orbit peak battery (VES16-class 8s4p packs, 30 % DoD)", item2="coolant swap water-proxy -> MPG40 (40 wt% PG) with NB2F2-port fin-root heaters (array-powered at sunrise), N2/EPDM insert, accumulator; pumps off in eclipse",
                                 item3="Whipple shields on the 4 central coolant trunks (SPF, bus side, no fin view)"),
         open_items=["radiator header MMOD protection (no simple bumper closes; architecture change needed)", "panel-spare coverage", "deployment/capture/release/interlock hardware (70/120 kg allocation)",
                     "life/hardening/compute provision (50/80 kg allocation)", "sustained / EOL peak power (battery covers <=30-min BOL bursts only)", "MPG40 peak inlet 403.4/404.1 K > Dow 393 K recommended max (pressurisation, glycol life)", "6061 braze process for the integral/brazed fin-tube panel (narrow braze window; post-braze re-age) not designed", "+13 % tube length per m2 (60 vs 68 mm pitch) raises tube MMOD exposure; not re-screened",
                     "ORDEM-based MMOD flux (NASA90+Gruen used)", "launcher same-orbit performance, finite-hardware packing/CG, qualification"],
         fleets=[])
for i, f in enumerate(b["fleets"]):
    nm = f["case"]; sf = s["fleets"][i]; T = th[nm]; nom = T["T2_rec_nominal_MPG40_plus_recharge"]; pk = T["T1_MPG40_peak"]; P = pw[nm]; bat = P["battery_table"]["30min"]
    fz = fm[nm]; tag = ["J8", "A4"][i]
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
      GPU_peak_K=V(pk["GPU_K"], "K", TH, f"{thk}.T1_MPG40_peak.GPU_K", "full-peak steady diagnostic (battery-buffered <=30 min/orbit)", warp_fin_table=True),
      HBM_peak_K=V(pk["HBM_K"], "K", TH, f"{thk}.T1_MPG40_peak.HBM_K", warp_fin_table=True),
      coolant_supply_nominal_K=V(nom["coolant_supply_K"], "K", TH, f"{thk}.T2.coolant_supply_K", warp_fin_table=True),
      coolant_radiator_inlet_nominal_K=V(nom["coolant_radiator_inlet_K"], "K", TH, f"{thk}.T2.coolant_radiator_inlet_K", warp_fin_table=True),
      coolant_radiator_inlet_peak_K=V(pk["coolant_radiator_inlet_K"], "K", TH, f"{thk}.T1.coolant_radiator_inlet_K", "exceeds Dow 393.15 K recommended max", warp_fin_table=True),
      rack_rise_K=V(20.0, "K", TH, f"{thk}.T2 (fixed dT_loop 20 K in operating())", "ASSUMED loop convention"),
      radiator_rise_nominal_K=V(nom["radiator_delta_K"], "K", TH, f"{thk}.T2.radiator_delta_K"), radiator_rise_peak_K=V(pk["radiator_delta_K"], "K", TH, f"{thk}.T1.radiator_delta_K"),
      rejected_heat_nominal_W=V(nom["total_solar_power_and_rejected_heat_W"], "W", TH, f"{thk}.T2.total_solar_power_and_rejected_heat_W"),
      radiator_effective_area_m2=V(f["radiator_effective_area_m2"], "m2", BASE, f"{bk}.radiator_effective_area_m2"), radiator_panels=V(f["physical_panels"], "-", BASE, f"{bk}.physical_panels"),
      solar_area_m2=V(f["solar_area_m2"], "m2", BASE, f"{bk}.solar_area_m2"),
      coolant=dict(fluid="MPG40 (40 wt% propylene glycol), CoolProp INCOMP::MPG[0.4]", liquidus_K=252.05,
                   loop_package_kg=V(sf["ledger_kg"]["coolant_loop"], "kg", SP, f"{sk}.ledger_kg.coolant_loop"), MPG40_inventory_kg=V(fz["MPG40_inventory_kg"], "kg", FM, f"{nm}.MPG40_inventory_kg"),
                   mass_flow_kg_s=V(nom["mass_flow_kg_s"], "kg/s", TH, f"{thk}.T2.mass_flow_kg_s"), swap_delta_kg=V(T["coolant_line_delta_kg"], "kg", TH, f"{thk}.coolant_line_delta_kg")),
      battery=dict(window_min=30.0, nameplate_kWh=V(bat["nameplate_Wh"] / 1000, "kWh", PW, f"cases/{nm}.battery_table.30min.nameplate_Wh/1000"), total_kg=V(bat["total_kg"], "kg", PW, f"cases/{nm}.battery_table.30min.total_kg"),
                   cycles_5yr=V(bat["cycles_5yr"], "-", PW, f"cases/{nm}.battery_table.30min.cycles_5yr"), charge_W=V(bat["P_charge_W"], "W", PW, f"cases/{nm}.battery_table.30min.P_charge_W"),
                   peak_deficit_BOL_W=V(P["verified_deficit_W"], "W", PW, f"cases/{nm}.verified_deficit_W"), EOL_peak_deficit_W=V(P["EOL"]["peak_deficit_EOL_W"], "W", PW, f"cases/{nm}.EOL.peak_deficit_EOL_W")),
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
                header_N_le_1_kg=V(hdr1["total_kg"], "kg", SP, f"{sk}.item3_mmod.header_N_le_1_ledger_routing.total_kg", "OPEN; would cost +5.7-5.8 K GPU and push August over 100 t"),
                header_status="OPEN", spares_status="OPEN"),
      open_item_allocations_kg=dict(deployment_mechanisms=sf["ledger_kg"]["deployment_mechanisms"], MMOD_spare_panel_allocation=sf["ledger_kg"]["MMOD_spare_panel_allocation"],
                                    freeze_restart_including_battery=sf["ledger_kg"]["freeze_restart_including_battery"], life_and_compute_provision=sf["ledger_kg"]["life_and_compute_provision"]),
      baseline_reference=dict(launch_mass_kg=f["launch_total_kg"], GPU_nominal_K=f["nominal"]["GPU_K"], HBM_nominal_K=f["nominal"]["HBM_K"], GPU_peak_K=f["full_peak_steady_sensitivity"]["GPU_K"]))
    x["fleets"].append(F)
x["stages"] = STAGES
x["NVIDIA_upstream_inputs"] = {WARP_TABLE: dict(sha256=sha(WARP_TABLE), produced_by="NVIDIA Warp 1.18.0 fp64 CUDA fin solves on GB10 cuda:0 (fin_al.py table mode, 585 solves, nx 320 x ny 8; 2026-11-06 PT); box-CPU Warp reproduction max |d eta| 3.1e-15", used_by="every coolant/GPU/HBM temperature via model_t549.supply_for_area (area factor 1.0)"),
    "inputs/ai1_replica/gb10_final_al/screen_al_fine.json": dict(sha256=sha("inputs/ai1_replica/gb10_final_al/screen_al_fine.json"), produced_by="NVIDIA Warp fp64 GB10 fin screen (fin_al_v2.py)", used_by="Al/K13D areal ratio -> radiator mass line (fin_v2.FIN_MASS_REL)")}
json.dump(x, open("GTC_FINAL_CANDIDATE.json", "w"), indent=1, sort_keys=False); print("written GTC_FINAL_CANDIDATE.json")
