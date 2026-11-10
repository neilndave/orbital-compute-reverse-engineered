"""Freeze/restart hardware mass for the MPG40 option, ported per panel from t596 NB2F2 (final_config_NB2F2_t596.json BAT/ADD breakdown, 125/208 panels) onto 77/128 panels."""
import os
import json, sys, CoolProp.CoolProp as CP
sys.path.insert(0, os.environ["GTCFC_ROOT"]+"/stages"); import fin_v2 as FV; NTR = FV.FREEZE_GEOM["NT"] / 4.0   # v2 t619: fin-root heater strips are per tube; NB2F2 panels had 4 tubes
NB = json.load(open(os.environ["GTCFC_ROOT"]+"/inputs/ai1_replica/checks_t538/t596/final_config_NB2F2_t596.json"))
TH = json.load(open(os.environ["GTCFC_ROOT"]+"/stages/spin1/THERMAL_SPIN1.json"))["cases"]
def rho(T):
    if T < 253.0:
        r0, r1 = rho(253.0), rho(263.0); return r0 + (r0 - r1) / 10.0 * (253.0 - T)   # linear extrapolation below the CoolProp liquid range (ASSUMED, as t596 used 240 K)
    if T <= 373.15: return CP.PropsSI("D", "T", T, "P", 3e5, "INCOMP::MPG[0.4]")
    r1, r0 = rho(373.15), rho(363.15); return r1 + (r1 - r0) / 10.0 * (T - 373.15)   # linear extrapolation above CoolProp range (ASSUMED)
CFG=json.load(open(os.environ["GTCFC_ROOT"]+"/CONFIG_V3.json"))
out = {}
for tag, nm, npan_nb in (("J8", "June", 125), ("A4", "August", 208)):
    NT=CFG["august_radiator"]["NT"] if nm=="August" and CFG.get("august_radiator") else FV.FREEZE_GEOM["NT"];NTR=NT/4.
    b = NB["BAT_breakdown"][tag]; add = NB["ADD_breakdown_kg_per_panel"]; acc = NB["accumulator"][tag]
    per = dict(heater_strips=b["heater_strips_fin_root"] / npan_nb * NTR, heater_harness=b["heater_harness"] / npan_nb * NTR, swivel_patch_heaters=b["swivel_patch_heaters"] / npan_nb,
               insert_cord=add["insert_cord"], compliance_plugs=add["fitting_swivel_compliance_plugs"])
    npan = TH[nm]["geometry_v3"]["radiator_panels"]; R = TH[nm]["T2_rec_nominal_MPG40_plus_recharge"]; inv = R["inventory"]
    m = inv["fluid_rack"] + inv["fluid_trunk"] + inv["hdr_fluid"] + inv["panel_fluid"]
    Thot_nom = R["coolant_radiator_inlet_K"]; Thot_pk = TH[nm]["T1_MPG40_peak"]["coolant_radiator_inlet_K"]
    dV_nom = m * (1 / rho(Thot_nom) - 1 / rho(240.0)) * 1e3; dV_pk = m * (1 / rho(Thot_pk) - 1 / rho(240.0)) * 1e3
    kg_per_L = acc["accumulator_kg"] / acc["dV_cold240_to_hot352_L"]; acc_kg = kg_per_L * dV_pk
    items = {k: v * npan for k, v in per.items()}; items.update(accumulator=acc_kg, switching=b["switching"], housekeeping_battery_once=b["row80_safe_mode"])
    coolant_delta = TH[nm]["coolant_line_delta_kg"]
    total_hw = sum(items.values()); total_with_swap = total_hw + coolant_delta
    alloc = {"June": 66.0, "August": 90.0}[nm]
    out[nm] = dict(per_panel_kg=per, items_kg=items, MPG40_inventory_kg=m, dV_240_to_nominal_inlet_L=dV_nom, dV_240_to_peak_inlet_L=dV_pk, T_hot_nominal_K=Thot_nom, T_hot_peak_K=Thot_pk,
                   accumulator_kg_per_L_from_NB2F2=kg_per_L, freeze_hw_total_kg=total_hw, MPG40_coolant_line_delta_kg=coolant_delta, item_total_incl_glycol_swap_kg=total_with_swap,
                   allocation_kg=alloc, pass_hw_only=total_hw <= alloc, pass_incl_swap=total_with_swap <= alloc, heater_kW_array_powered=npan * NT * 2.9446 * 40.0 / 1e3,
                   Dow_recommended_max_K=393.15, peak_inlet_exceeds_Dow_max=Thot_pk > 393.15)
    print(nm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[nm].items() if not isinstance(v, dict)}); print("  items", {k: round(v, 3) for k, v in items.items()})
json.dump(out, open("FREEZE_MASS_SPIN1.json", "w"), indent=1, default=float)
