"""Assemble SPIN1_EXACT.json: per-item results, rollup vs 100 t at 0 % weight reserve, thermal deltas.  Rollup rule (conservative): allocations are kept unless the
designed item exceeds them (then the designed value replaces the allocation); new lines (peak battery, MPG40 coolant-line delta, propellant delta) are added."""
import sys, json, math, hashlib
from pathlib import Path
sys.argv = sys.argv[:1]; sys.path.insert(0, "/tmp/gtcfc_root/inputs/ai1_replica/checks_t538")
import model_t549 as M
P = Path(__file__).resolve().parent
base = json.load(open("/tmp/gtcfc_root/stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"))
PW = json.load(open(P / "POWER_SPIN1.json")); TH = json.load(open(P / "THERMAL_SPIN1.json")); FM = json.load(open(P / "freeze/FREEZE_MASS_SPIN1.json"))
WK = json.load(open(P / "freeze/WATER_KEEPWARM_SPIN1.json")); MG = json.load(open(P / "MMOD_GRID_SPIN1.json")); MT = json.load(open(P / "MMOD_TRUNK_ALLOC_SPIN1.json"))
FR = {f.name[4:-5]: json.load(open(f)) for f in sorted((P / "freeze").glob("out_*.json"))}
x = dict(label="GTC scoped baseline concept — SPIN1 sidecar (peak buffer, freeze/restart, MMOD screen)", configuration_id="AI1_GTC_SPIN1_on_t602_t603_scoped_baseline_v1",
         parent_configuration=dict(path="/tmp/gtcfc_root/stages/baseline/GTC_SCOPED_BASELINE_EXACT.json", sha256=hashlib.sha256(open("/tmp/gtcfc_root/stages/baseline/GTC_SCOPED_BASELINE_EXACT.json", "rb").read()).hexdigest()),
         adopted_baseline=False, geometry_unchanged=True, render_change=False, authority="the author t605: do spins 1,2,3; #3 not added to render",
         mass_reserve_fraction=0.0, launch_payload_budget_kg=100000.0, dispenser_all_in_kg=2000.0,
         rollup_rule=__doc__, fleets=[])
for i, f in enumerate(base["fleets"]):
    nm = f["case"]; tag = ["J8", "A4"][i]; N = f["count"]; mo = M.Month(tag)
    L = {r["item"]: r["kg"] for r in f["ledger"]}
    bat = PW["cases"][nm]["battery_table"]["30min"]; arr = PW["cases"][nm]["array_option"]
    fz = FM[nm]; cool_d = TH["cases"][nm]["coolant_line_delta_kg"]
    trunk = MT[nm]["P0.95_flux3"]; hdrN1 = MG["cases"][nm]["ledger"]["min_mass_N<=1.0"]; hdr_alloc = MT[nm]["header_best_N_within_allocation"]
    newL = dict(L)
    newL["peak_power_buffer_battery_NEW"] = bat["total_kg"]
    newL["coolant_loop"] = L["coolant_loop"] + cool_d
    newL["freeze_restart_including_battery"] = max(L["freeze_restart_including_battery"], fz["freeze_hw_total_kg"])
    newL["MMOD_spare_panel_allocation"] = max(L["MMOD_spare_panel_allocation"], trunk["total_kg"])
    dry_add = sum(newL.values()) - sum(L.values())
    core0 = mo.core0; prop0 = M.C13.prop(core0, mo.Aram0); prop1 = M.C13.prop(core0 + dry_add, mo.Aram0); dprop = prop1 - prop0
    newL["propellant_delta_inherited_c13_prop"] = dprop
    sc = sum(newL.values()); launch = N * sc + 2000.0
    # sensitivity: header protection to N<=1 expected header penetrations / 5 yr
    sensL = dict(newL); sensL["MMOD_spare_panel_allocation"] = max(L["MMOD_spare_panel_allocation"], trunk["total_kg"] + hdrN1["total_kg"])
    dry_add_s = sum(sensL.values()) - sensL["propellant_delta_inherited_c13_prop"] - sum(L.values()); sensL["propellant_delta_inherited_c13_prop"] = M.C13.prop(core0 + dry_add_s, mo.Aram0) - prop0
    sc_s = sum(sensL.values()); launch_s = N * sc_s + 2000.0
    # array alternative (geometry change): replace battery by array add
    altL = dict(newL); altL.pop("peak_power_buffer_battery_NEW"); altL["array_added_area_ALT"] = arr["added_kg"]
    dry_add_a = sum(altL.values()) - altL["propellant_delta_inherited_c13_prop"] - sum(L.values()); altL["propellant_delta_inherited_c13_prop"] = M.C13.prop(core0 + dry_add_a, mo.Aram0) - prop0
    sc_a = sum(altL.values()); launch_a = N * sc_a + 2000.0
    T = TH["cases"][nm]; b0n, b0p = T["T0_baseline_nominal"], T["T0_baseline_peak"]; rn, rp = T["T2_rec_nominal_MPG40_plus_recharge"], T["T1_MPG40_peak"]
    sn, sp = T["T4_sens_header_protected_nominal"], T["T4_sens_header_protected_peak"]
    fr = {k: v for k, v in FR.items() if k.startswith(tag)}
    x["fleets"].append(dict(case=nm, count=N, peak_per_sc_kW=f["peak_per_sc_kW"], nominal_per_sc_kW=f["nominal_per_sc_kW"],
        item1_peak_power=dict(verified_deficit_W=PW["cases"][nm]["verified_deficit_W"], baseline_stated_deficit_W=f["full_peak_BOL_power_shortfall_W"], recommended="(a) battery, 30-min peak window per orbit, render-neutral",
                              battery=bat, array_alternative=arr, energy_duty_limit=PW["cases"][nm]["energy_duty_limit_with_battery_losses"], EOL=PW["cases"][nm]["EOL"], table={k: v["total_kg"] for k, v in PW["cases"][nm]["battery_table"].items()}),
        item2_freeze=dict(baseline_coolant="water proxy (rho 978, cp 4180) — NOT freeze tolerant", water_transient={k: v for k, v in fr.items() if "water" in k}, water_keepwarm_alternative=WK[nm],
                          recommended="swap to MPG40 (40 wt% PG) + t596 NB2F2-style fin-root heaters (array-powered at sunrise, IT off) + N2/EPDM insert + accumulator; pumps off in eclipse",
                          MPG40_transient={k: v for k, v in fr.items() if "MPG40" in k}, mass=fz),
        item3_mmod=dict(trunk_SPF_recommended=trunk, header_best_within_allocation=hdr_alloc, header_N_le_1_ledger_routing=hdrN1,
                        unprotected=dict(ledger=json.load(open(P / "MMOD_SPIN1.json"))["cases"][nm]["ledger"]["unprotected"]), status="headers NOT closable by a simple bumper in rendered routing; spares coverage OPEN"),
        ledger_kg=newL, sc_mass_kg=sc, launch_total_kg=launch, margin_to_100t_kg=100000.0 - launch, mass_fit=launch <= 100000.0,
        delta_vs_baseline=dict(sc_kg=sc - f["sc_mass_kg"], launch_kg=launch - f["launch_total_kg"]),
        sensitivity_header_protected=dict(ledger_kg=sensL, sc_mass_kg=sc_s, launch_total_kg=launch_s, margin_to_100t_kg=100000.0 - launch_s, GPU_nominal_K=sn["GPU_K"], HBM_nominal_K=sn["HBM_K"], GPU_peak_K=sp["GPU_K"], F_scale=sn["F_scale"]),
        alternative_array_instead_of_battery=dict(sc_mass_kg=sc_a, launch_total_kg=launch_a, margin_to_100t_kg=100000.0 - launch_a, geometry_changed=True),
        thermal=dict(nominal=rn, peak=rp, baseline_nominal_GPU_K=b0n["GPU_K"], baseline_nominal_HBM_K=b0n["HBM_K"], baseline_peak_GPU_K=b0p["GPU_K"],
                     dGPU_nominal_K=rn["GPU_K"] - b0n["GPU_K"], dHBM_nominal_K=rn["HBM_K"] - b0n["HBM_K"], dGPU_peak_K=rp["GPU_K"] - b0p["GPU_K"],
                     film_sensitivity_GPU_nominal_K=T["T5_sens_film_nominal"]["GPU_K"], film_dR_KW=T["T5_sens_film_dR_KW"], header_protected_sensitivity_GPU_nominal_K=sn["GPU_K"])))
    print(nm, "sc", round(sc, 3), "launch", round(launch, 3), "headroom", round(100000 - launch, 3), "dprop", round(dprop, 3), "| sens launch", round(launch_s, 1), "| array-alt launch", round(launch_a, 1))
    print("   ledger", {k: round(v, 3) for k, v in newL.items()})
x["source_hashes"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.glob("*.py")) + sorted((P / "freeze").glob("*.py"))}
(P / "SPIN1_EXACT.json").write_text(json.dumps(x, indent=1, default=float) + "\n")
print("sha", hashlib.sha256((P / "SPIN1_EXACT.json").read_bytes()).hexdigest())
