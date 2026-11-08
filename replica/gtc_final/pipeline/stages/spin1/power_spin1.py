"""SPIN1 item 1: peak-power buffering on the GTC scoped baseline (no geometry change for the battery option).  Labels: SOURCED / INHERITED / ASSUMED."""
import json, math
base = json.load(open("/tmp/gtcv2_root/stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"))
SRC = dict(
  VES16_cell_Wh_kg=">155 Wh/kg cell, 16 Wh, <=112 g (Saft VES16; https://newspacemarket.com/products/saft-ves16-cell/ ; NASA-hosted Saft LEO test update https://www.nasa.gov/wp-content/uploads/2024/01/saft-ves16-cell-life-test-performance-update.pdf)",
  VES16_pack="VES16 8s4p module 512 Wh, 5.8 kg -> 88.3 Wh/kg incl. cell balancing, heaters, sensors, Al plate; LEO DoD 30 % (https://www.satnow.com/products/batteries/saft/98-1277-ves16-8s4p-battery ; https://www.directindustry.com/prod/saft/product-19840-2536059.html)",
  VES16_life="real-time LEO cycling 30 % DoD: 27,000 cycles with <12 % capacity loss; >60,000 cycles at 20-40 % DoD (<20 % loss) (NASA-hosted Saft pdf above)",
  XTJ_Prime="Spectrolab XTJ Prime 30.7 % BOL AM0; Pmp retention 0.94 at 1e14 1-MeV e/cm2 labelled '10-yr LEO' (https://www.spectrolab.com/photovoltaics/XTJ-Prime_Data_Sheet%20_07.27.22.pdf)",
  AZUR_4G32="AZUR 4G32C-Advanced 31.3 % BOL at 1367 W/m2 (https://www.azurspace.com/media/uploads/file_links/file/bdb_00010895-02-00_4g32-advanced_4x8.pdf)")
ASM = dict(peak_window_min=30.0, eta_discharge_chain=0.93, eta_charge_chain=0.93, DoD=0.30, capacity_EOL_fraction=0.88, pack_Wh_kg=512.0 / 5.8,
           bcdr_kW_per_kg=5.57, integration_frac=0.05, batt_rad_kg_m2=3.0, batt_rad_net_W_m2=270.0, batt_heater_ctrl_kg=0.5, eol_array_retention=0.94)
_E = json.load(open("/tmp/gtcv2_root/stages/spin1/../orbit/ECLIPSE_600KM.json"))   # FINAL: 600-km grid values (spin1 used the 550-km t590 21.66 min)
ORBIT = dict(T_orb_min=_E["T_orb_min"], max_shadow_min=_E["max_shadow_min"], orbits_per_year=_E["orbits_per_year"], life_yr=5.0)
def battery(deficit_W, window_min, nominal_headroom_W):
    E_bus = deficit_W * window_min / 60.0                      # Wh delivered to bus
    E_cell = E_bus / ASM["eta_discharge_chain"]                 # Wh out of cells
    nameplate = E_cell / (ASM["DoD"] * ASM["capacity_EOL_fraction"])
    pack = nameplate / ASM["pack_Wh_kg"]
    recharge_min = ORBIT["T_orb_min"] - window_min - ORBIT["max_shadow_min"]
    E_charge_bus = E_cell / ASM["eta_charge_chain"]; P_ch = E_charge_bus / (recharge_min / 60.0)
    bcdr = max(deficit_W, P_ch) / 1000.0 / ASM["bcdr_kW_per_kg"]
    loss_Wh_orbit = (E_cell - E_bus) + (E_charge_bus - E_cell); avg_loss_W = loss_Wh_orbit / (ORBIT["T_orb_min"] / 60.0)
    rad_m2 = avg_loss_W / ASM["batt_rad_net_W_m2"]; therm = rad_m2 * ASM["batt_rad_kg_m2"] + ASM["batt_heater_ctrl_kg"]
    integ = ASM["integration_frac"] * pack; total = pack + bcdr + therm + integ
    cycles = ORBIT["orbits_per_year"] * ORBIT["life_yr"]
    return dict(window_min=window_min, E_bus_Wh=E_bus, E_cell_Wh=E_cell, nameplate_Wh=nameplate, pack_kg=pack, bcdr_kg=bcdr, thermal_kg=therm, integration_kg=integ, total_kg=total,
                recharge_window_min=recharge_min, P_charge_W=P_ch, charge_fits_nominal_BOL_headroom=P_ch <= nominal_headroom_W, C_rate_discharge=deficit_W / nameplate, C_rate_charge=P_ch / nameplate,
                cycles_5yr=cycles, battery_loss_Wh_per_orbit=loss_Wh_orbit, battery_avg_loss_W=avg_loss_W, battery_radiator_m2=rad_m2,
                main_radiator_extra_heat_W_during_recharge=P_ch * (1 / 0.92 - 1))
out = dict(sources=SRC, assumptions=ASM, orbit=ORBIT, cases={})
for f in base["fleets"]:
    nm = f["case"]; nom = f["nominal"]; pk = f["full_peak_steady_sensitivity"]; arr = f["original_array_gross_BOL_W"]; A = f["solar_area_m2"]
    m_arr = [x["kg"] for x in f["ledger"] if x["item"] == "array"][0]
    deficit = pk["total_solar_power_and_rejected_heat_W"] - arr; headroom = arr - nom["total_solar_power_and_rejected_heat_W"]
    assert abs(deficit - f["full_peak_BOL_power_shortfall_W"]) < 1e-6 and abs(headroom - f["nominal_BOL_solar_headroom_W"]) < 1e-6 and abs(arr - A * 319.7) < 1e-6
    duty_max = headroom / (pk["total_solar_power_and_rejected_heat_W"] - nom["total_solar_power_and_rejected_heat_W"])
    duty_max_rt = headroom / (headroom + deficit / (ASM["eta_discharge_chain"] * ASM["eta_charge_chain"]))   # with battery round-trip losses
    kg_per_m2 = m_arr / A; W_per_kg = arr / m_arr
    dA = deficit / 319.7; arr_kg = dA * kg_per_m2
    dA_eol = pk["total_solar_power_and_rejected_heat_W"] / (319.7 * ASM["eol_array_retention"]) - A
    eol_arr = arr * ASM["eol_array_retention"]; eol_def = pk["total_solar_power_and_rejected_heat_W"] - eol_arr; eol_head = eol_arr - nom["total_solar_power_and_rejected_heat_W"]
    R = dict(verified_deficit_W=deficit, verified_nominal_headroom_W=headroom, array_gross_BOL_W=arr, peak_input_W=pk["total_solar_power_and_rejected_heat_W"], nominal_input_W=nom["total_solar_power_and_rejected_heat_W"],
             energy_duty_limit_peak_fraction_lossless=duty_max, energy_duty_limit_with_battery_losses=duty_max_rt,
             battery_table={f"{w:g}min": battery(deficit, w, headroom) for w in (10, 15, 30, 45, 60)},
             array_option=dict(added_area_m2=dA, added_area_frac=dA / A, kg_per_m2_inherited=kg_per_m2, W_per_kg_inherited=W_per_kg, added_kg=arr_kg,
                               added_kg_at_ROSA_flown_110Wkg=deficit / 110.0, wing_length_change_m=dA / (2 * 14.0), geometry_changed=True),
             EOL=dict(retention=ASM["eol_array_retention"], array_EOL_W=eol_arr, nominal_headroom_EOL_W=eol_head, peak_deficit_EOL_W=eol_def,
                      array_option_added_area_m2=dA_eol, array_option_added_kg=dA_eol * kg_per_m2, battery_30min_EOL=battery(eol_def, 30.0, eol_head)),
             cell_upgrade_note=dict(ratio_AZUR_over_XTJ=(31.3 / 1367.0) / (30.7 / 1353.0), covers_W=arr * ((31.3 / 1367.0) / (30.7 / 1353.0) - 1), status="NOT credited: 319.7 W/m2 basis not traced to a specific cell"))
    out["cases"][nm] = R
    b = R["battery_table"]["30min"]
    print(nm, "deficit", round(deficit, 3), "headroom", round(headroom, 3), "duty", round(duty_max, 4), round(duty_max_rt, 4))
    print("  batt30", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in b.items()})
    print("  array", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in R["array_option"].items()})
    print("  EOL", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in R["EOL"].items() if k != "battery_30min_EOL"}, "batt30EOL kg", round(R["EOL"]["battery_30min_EOL"]["total_kg"], 2))
    print("  cell", R["cell_upgrade_note"])
    for w, bb in R["battery_table"].items(): print("   ", w, round(bb["total_kg"], 2), "nameplate", round(bb["nameplate_Wh"], 1))
json.dump(out, open("POWER_SPIN1.json", "w"), indent=1, default=float)
