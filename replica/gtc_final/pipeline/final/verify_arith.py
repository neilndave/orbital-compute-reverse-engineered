"""Independent arithmetic re-derivation of every poster-facing number in GTC_FINAL_CANDIDATE.json from primitive inputs
(plain arithmetic written separately from the stage scripts; the thermal ROOT itself is checked independently by the GB10 Warp kernel)."""
import json, math, os
ROOT = os.environ.get("GTCFC_ROOT", "/tmp/gtcv2_root")
J = lambda p: json.load(open(os.path.join(ROOT, p)))
X = J("final/GTC_FINAL_CANDIDATE.json"); B = J("stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"); TH = J("stages/spin1/THERMAL_SPIN1.json")["cases"]
PWJ = J("stages/spin1/POWER_SPIN1.json"); EC = J("stages/orbit/ECLIPSE_600KM.json"); NB = J("inputs/ai1_replica/checks_t538/t596/final_config_NB2F2_t596.json")
checks = []
def chk(name, got, want, tol=1e-9):
    d = abs(got - want); ok = d <= tol * max(1.0, abs(want)); checks.append(dict(check=name, recomputed=got, reported=want, abs_diff=d, passed=ok))
for i, F in enumerate(X["fleets"]):
    nm = F["case"]; b = B["fleets"][i]; N = F["spacecraft_count"]["value"]; tag = ["J8", "A4"][i]
    chk(f"{nm} installed peak MW = N x kW", N * F["installed_peak_per_sc_kW"]["value"] / 1000, F["installed_peak_per_launch_MW"]["value"])
    chk(f"{nm} nominal IT MW = N x kW", N * F["nominal_per_sc_kW"]["value"] / 1000, F["nominal_IT_per_launch_MW"]["value"])
    chk(f"{nm} nominal = {[0.8,0.7][i]} x peak", [0.8, 0.7][i] * F["installed_peak_per_sc_kW"]["value"], F["nominal_per_sc_kW"]["value"])
    L = F["ledger_kg"]["value"]; base_sum = sum(r["kg"] for r in b["ledger"])
    chk(f"{nm} baseline sc mass = ledger sum", base_sum, b["sc_mass_kg"]); chk(f"{nm} baseline launch = N x sc + 2000", N * base_sum + 2000, b["launch_total_kg"])
    # battery (independent): deficit, energy chain, pack
    pk = b["full_peak_steady_sensitivity"]["total_solar_power_and_rejected_heat_W"]; arr = b["solar_area_m2"] * 319.7; deficit = pk - arr
    chk(f"{nm} peak deficit W = peak input - A_arr x 319.7", deficit, F["battery"]["peak_deficit_BOL_W"]["value"])
    E_cell = deficit * 0.5 / 0.93; name_Wh = E_cell / (0.30 * 0.88); pack = name_Wh / (512 / 5.8)
    T_orb = EC["T_orb_min"]; rech_min = T_orb - 30 - EC["max_shadow_min"]; P_ch = E_cell / 0.93 / (rech_min / 60)
    bcdr = max(deficit, P_ch) / 1000 / 5.57; loss = (E_cell - deficit * 0.5) + (E_cell / 0.93 - E_cell); avg = loss / (T_orb / 60); therm = avg / 270 * 3 + 0.5
    chk(f"{nm} battery nameplate kWh", name_Wh / 1000, F["battery"]["nameplate_kWh"]["value"]); chk(f"{nm} battery total kg", pack * 1.05 + bcdr + therm, F["battery"]["total_kg"]["value"])
    chk(f"{nm} battery charge W", P_ch, F["battery"]["charge_W"]["value"]); chk(f"{nm} cycles 5 yr", EC["orbits_per_year"] * 5, F["battery"]["cycles_5yr"]["value"])
    rech_heat = P_ch * (1 / 0.92 - 1)
    # thermal energy bookkeeping around the (GPU-verified) root
    for case, key, load, extra in (("nominal", "T2_rec_nominal_MPG40_plus_recharge", [0.8, 0.7][i], rech_heat), ("peak", "T1_MPG40_peak", 1.0, 0.0)):
        t = TH[nm][key]; IT = t["IT_kW"] * 1000; Q = (IT + 2000 + t["pump_electric_W"]) / 0.92 + extra
        chk(f"{nm} {case} rejected heat W", Q, t["total_solar_power_and_rejected_heat_W"]); chk(f"{nm} {case} radiator rise K = 20 Q/IT", 20 * Q / IT, t["radiator_delta_K"])
        chk(f"{nm} {case} GPU = supply + 10 + 1.7 load 14.22", t["coolant_supply_K"] + 10 + 1.7 * load * 14.22, t["GPU_K"])
        chk(f"{nm} {case} HBM = supply + 10 + 18 load", t["coolant_supply_K"] + 10 + 18 * load, t["HBM_K"])
        chk(f"{nm} {case} inlet = supply + rise", t["coolant_supply_K"] + 20 * Q / IT, t["coolant_radiator_inlet_K"])
    # freeze hardware (independent per-panel port of NB2F2 breakdown)
    nb = NB["BAT_breakdown"][tag]; npan_nb = NB["panels"][tag]; npan = F["radiator_panels"]["value"]; add = NB["ADD_breakdown_kg_per_panel"]
    NTR = 6 / 4.0   # v2 t619: 6 tubes/panel (60 mm pitch, 363.4 mm panel) vs NB2F2 4; fin-root strips + harness are per tube
    per = ((nb["heater_strips_fin_root"] + nb["heater_harness"]) * NTR + nb["swivel_patch_heaters"]) / npan_nb + add["insert_cord"] + add["fitting_swivel_compliance_plugs"]
    k13d_rad = {"June": 122.28, "August": 203.77}[nm]; rel = 1.7526374327573164 / (1.417180087727044 + 7.61 / 81.62815837399465)   # Warp screen areal Al / (K13D + t479 bond)
    chk(f"{nm} Al radiator line = K13D wet line x Al/K13D areal ratio", k13d_rad * rel, F["ledger_kg"]["value"]["radiator"], tol=0.02)
    chk(f"{nm} reserve kg/sc = reserve / N", (100000 - F["launch_mass_kg"]["value"]) / N, F["reserve_kg_per_sc"]["value"])
    FMJ = J("stages/spin1/freeze/FREEZE_MASS_SPIN1.json")[nm]
    chk(f"{nm} freeze hardware kg", per * npan + FMJ["items_kg"]["accumulator"] + 2.0 + 31.25, F["freeze_restart"]["hardware_kg"]["value"])
    acc = NB["accumulator"][tag]; chk(f"{nm} accumulator kg = (kg/L NB2F2) x dV", acc["accumulator_kg"] / acc["dV_cold240_to_hot352_L"] * FMJ["dV_240_to_peak_inlet_L"], FMJ["items_kg"]["accumulator"])
    # rollup
    newsum = sum(L.values()); chk(f"{nm} final sc mass = ledger sum", newsum, F["sc_mass_kg"]["value"])
    chk(f"{nm} final launch = N x sc + 2000", N * newsum + 2000, F["launch_mass_kg"]["value"]); chk(f"{nm} headroom = 100000 - launch", 100000 - (N * newsum + 2000), F["headroom_to_100t_kg"]["value"])
    base_L = {r["item"]: r["kg"] for r in b["ledger"]}
    chk(f"{nm} added lines = battery + coolant swap + propellant", newsum - base_sum, F["battery"]["total_kg"]["value"] + F["coolant"]["swap_delta_kg"]["value"] + L["propellant_delta_inherited_c13_prop"]
        + max(0, F["freeze_restart"]["hardware_kg"]["value"] - base_L["freeze_restart_including_battery"]) + max(0, F["mmod"]["trunk_shield_kg"]["value"] - base_L["MMOD_spare_panel_allocation"]))
    chk(f"{nm} coolant line = baseline + swap delta", base_L["coolant_loop"] + F["coolant"]["swap_delta_kg"]["value"], L["coolant_loop"])
    # downtime
    d = F["freeze_restart"]["added_downtime_h_per_yr"]; chk(f"{nm} added downtime h/yr", F["freeze_restart"]["restart_open_min_cold"]["value"] * EC["eclipsed_orbits_per_year"] / 60, d["value"])
    # MMOD trunk PNP = exp(-N)
    tr = J("stages/spin1/SPIN1_EXACT.json")["fleets"][i]["item3_mmod"]["trunk_SPF_recommended"]; chk(f"{nm} trunk PNP = exp(-N)", math.exp(-tr["N_5yr"]), tr["PNP"])
chk("eclipse mean = shadow h x 60 / n", EC["shadow_hours_per_year"] * 60 / EC["eclipsed_orbits_per_year"], EC["mean_shadow_min_when_eclipsed"])
res = dict(n=len(checks), failed=[c for c in checks if not c["passed"]], passed=all(c["passed"] for c in checks), checks=checks)
json.dump(res, open("ARITH_CHECK.json", "w"), indent=1); print("arith checks", len(checks), "failed", len(res["failed"]))
