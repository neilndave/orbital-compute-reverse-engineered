"""Independent arithmetic re-derivation of every poster-facing number in GTC_FINAL_CANDIDATE.json from primitive inputs
(plain arithmetic written separately from the stage scripts; the thermal ROOT itself is checked independently by the GB10 Warp kernel)."""
import os
import json, math, os
ROOT = os.environ.get("GTCFC_ROOT", os.environ["GTCFC_ROOT"]+"")
J = lambda p: json.load(open(os.path.join(ROOT, p)))
X = J("final/GTC_FINAL_CANDIDATE.json"); B = J("stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"); TH = J("stages/spin1/THERMAL_SPIN1.json")["cases"]
PWJ = J("stages/spin1/POWER_SPIN1.json"); EC = J("stages/orbit/ECLIPSE_600KM.json"); NB = J("inputs/ai1_replica/checks_t538/t596/final_config_NB2F2_t596.json")
CFG=J("CONFIG_V3.json")
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
    # Array sizing independently from actual full-peak thermal demand.
    pk=TH[nm]["T1_MPG40_peak"]["total_solar_power_and_rejected_heat_W"]
    area=pk/319.7;ratio=area/b["solar_area_m2"];base_L={r["item"]:r["kg"] for r in b["ledger"]}
    chk(f"{nm} array area = full peak input / BOL flux",area,F["solar_area_m2"]["value"])
    for line in ("array","harness","power_electronics"):
        chk(f"{nm} {line} inherited eratio scaling",base_L[line]*ratio,L[line])
    chk(f"{nm} adopted peak battery zero",0,F["battery"]["total_kg"]["value"])
    chk(f"{nm} safe-mode battery retained",31.25,F["battery"]["safe_mode_kg"])
    chk(f"{nm} EOL deficit on grown array",pk*(1-.94),F["array_v3"]["EOL_peak_deficit_W"]["value"])
    rech_heat=0.0
    # thermal energy bookkeeping around the (GPU-verified) root
    for case, key, load, extra in (("nominal", "T2_rec_nominal_MPG40_plus_recharge", [0.8, 0.7][i], rech_heat), ("peak", "T1_MPG40_peak", 1.0, 0.0)):
        t = TH[nm][key]; IT = t["IT_kW"] * 1000; Q = (IT + 2000 + t["pump_electric_W"]) / 0.92 + extra
        chk(f"{nm} {case} rejected heat W", Q, t["total_solar_power_and_rejected_heat_W"]); chk(f"{nm} {case} radiator rise K = 20 Q/IT", 20 * Q / IT, t["radiator_delta_K"])
        chk(f"{nm} {case} GPU = supply + 10 + 1.7 load 14.22", t["coolant_supply_K"] + 10 + 1.7 * load * 14.22, t["GPU_K"])
        chk(f"{nm} {case} HBM = supply + 10 + 18 load", t["coolant_supply_K"] + 10 + 18 * load, t["HBM_K"])
        chk(f"{nm} {case} inlet = supply + rise", t["coolant_supply_K"] + 20 * Q / IT, t["coolant_radiator_inlet_K"])
    # freeze hardware (independent per-panel port of NB2F2 breakdown)
    nb = NB["BAT_breakdown"][tag]; npan_nb = NB["panels"][tag]; npan = F["radiator_panels"]["value"]; add = NB["ADD_breakdown_kg_per_panel"]
    NTR = (CFG["august_radiator"]["NT"] if nm=="August" else 6) / 4.0   # v2 t619: 6 tubes/panel (60 mm pitch, 363.4 mm panel) vs NB2F2 4; fin-root strips + harness are per tube
    per = ((nb["heater_strips_fin_root"] + nb["heater_harness"]) * NTR + nb["swivel_patch_heaters"]) / npan_nb + add["insert_cord"] + add["fitting_swivel_compliance_plugs"]
    k13d_rad = {"June": 122.28, "August": 203.77}[nm]; rel = 1.7526374327573164 / (1.417180087727044 + 7.61 / 81.62815837399465)   # Warp screen areal Al / (K13D + t479 bond)
    if nm=='August':
        a=CFG['august_radiator'];rho=TH[nm]['radiator_mass_reference_fluid_density_kg_m3'];mass=npan*a['NT']*a['panel_length_m']*(2*a['half_length_m']*a['thickness_m']*2700+math.pi*(a['tube_OD_m']**2-a['tube_ID_m']**2)/4*2700+math.pi*a['tube_ID_m']**2/4*rho)
        chk('August exact fin sheet + circular tube annulus + fluid wet mass',mass,L['radiator'])
        chk('August tube geometry closes panel width',a['NT']*(2*a['half_length_m']+a['tube_OD_m']),a['panel_width_m'])
        for ck in ('T2_rec_nominal_MPG40_plus_recharge','T1_MPG40_peak'):
            t=TH[nm][ck];film=t['radiator_film'];AA=npan*a['NT']*math.pi*a['tube_ID_m']*a['panel_length_m']
            chk('August '+ck+' film heat balance',film['delta_K']*film['h_W_m2K']*AA,t['total_solar_power_and_rejected_heat_W'])
    else:
        chk(f"{nm} Al radiator inherited areal ratio", k13d_rad * rel*npan/b["physical_panels"], L['radiator'], tol=0.02)
    chk(f"{nm} reserve kg/sc = reserve / N", (100000 - F["launch_mass_kg"]["value"]) / N, F["reserve_kg_per_sc"]["value"])
    FMJ = J("stages/spin1/freeze/FREEZE_MASS_SPIN1.json")[nm]
    chk(f"{nm} freeze hardware kg", per * npan + FMJ["items_kg"]["accumulator"] + 2.0 + 31.25, F["freeze_restart"]["hardware_kg"]["value"])
    acc = NB["accumulator"][tag]; chk(f"{nm} accumulator kg = (kg/L NB2F2) x dV", acc["accumulator_kg"] / acc["dV_cold240_to_hot352_L"] * FMJ["dV_240_to_peak_inlet_L"], FMJ["items_kg"]["accumulator"])
    # rollup
    newsum = sum(L.values()); chk(f"{nm} final sc mass = ledger sum", newsum, F["sc_mass_kg"]["value"])
    chk(f"{nm} final launch = N x sc + 2000", N * newsum + 2000, F["launch_mass_kg"]["value"]); chk(f"{nm} headroom = 100000 - launch", 100000 - (N * newsum + 2000), F["headroom_to_100t_kg"]["value"])
    base_L = {r["item"]: r["kg"] for r in b["ledger"]}
    chk(f"{nm} added lines = array-distribution growth + coolant swap + propellant", newsum - base_sum, sum(base_L[k]*(ratio-1) for k in ("array","harness","power_electronics")) + (L["radiator"]-base_L["radiator"])+sum(base_L[k]*(max(1,npan/b["physical_panels"])-1) for k in ("structure_mech","deployment_mechanisms")) + F["coolant"]["swap_delta_kg"]["value"] + L["propellant_delta_inherited_c13_prop"]
        + max(0, F["freeze_restart"]["hardware_kg"]["value"] - base_L["freeze_restart_including_battery"]) + max(0, F["mmod"]["trunk_shield_kg"]["value"] - base_L["MMOD_spare_panel_allocation"]))
    chk(f"{nm} coolant line = baseline + swap delta", base_L["coolant_loop"] + F["coolant"]["swap_delta_kg"]["value"], L["coolant_loop"])
    # Independent drag/rocket-equation iteration (no calls into stage prop()).
    pt=J(f"inputs/ai1_replica/gtc_params/point_{tag}_C1.json")
    core0=sum(v for k,v in pt["mass_lines_kg"].items() if k not in ("margin","adapter","mmod_bumper"))
    daily=J("inputs/ai1_replica/eclipse/eclipse_daily.json")["600_6.0"]
    cosbeta=sum(math.cos(math.radians(day["beta_mean"])) for day in daily)/len(daily)
    ram0=b["radiator_effective_area_m2"]+15+b["solar_area_m2"]*2/math.pi*cosbeta
    ram1=ram0+(area-b["solar_area_m2"])*2/math.pi*cosbeta+(F["radiator_effective_area_m2"]["value"]-b["radiator_effective_area_m2"])
    rho=J("inputs/ai1_replica/eclipse/density_alt.json")["solar_mean"]["600"]
    vc=lambda h: math.sqrt(398600.4418/(6378.137+h))*1000
    v=vc(600);dv0=max(0,vc(350)-v)+abs(vc(200)-v)
    def prop_ind(core,ram):
        pr=0.0
        for outer in range(300):
            dry=core-pr;p=0.0
            for inner in range(300):
                dvd=.5*rho*v*v*2.2*ram/(dry+.5*p)*3*365.25*86400
                pn=dry*math.expm1((dv0+dvd)/(9.80665*2500))*1.21
                if abs(pn-p)<1e-9:break
                p=pn
            if abs(p-pr)<1e-9:break
            pr=p
        return pr
    dryadd=sum(L.values())-L["propellant_delta_inherited_c13_prop"]-base_sum
    chk(f"{nm} propellant delta with larger ram area",prop_ind(core0+dryadd,ram1)-prop_ind(core0,ram0),L["propellant_delta_inherited_c13_prop"])
    chk(f"{nm} area increment vs v2",area-b["solar_area_m2"],F["array_v3"]["added_area_m2"]["value"])
    chk(f"{nm} wing extension = area increment / 28",(area-b["solar_area_m2"])/28,F["array_v3"]["wing_length_change_m"]["value"])
    chk(f"{nm} EOL additional array area (not adopted)",area*(1/.94-1),F["array_v3"]["EOL_cover_extra_vs_v3_m2"]["value"])
    # downtime
    d = F["freeze_restart"]["added_downtime_h_per_yr"]; chk(f"{nm} added downtime h/yr", F["freeze_restart"]["restart_open_min_cold"]["value"] * EC["eclipsed_orbits_per_year"] / 60, d["value"])
    # MMOD trunk PNP = exp(-N)
    tr = J("stages/spin1/SPIN1_EXACT.json")["fleets"][i]["item3_mmod"]["trunk_SPF_recommended"]; chk(f"{nm} trunk PNP = exp(-N)", math.exp(-tr["N_5yr"]), tr["PNP"])
chk("eclipse mean = shadow h x 60 / n", EC["shadow_hours_per_year"] * 60 / EC["eclipsed_orbits_per_year"], EC["mean_shadow_min_when_eclipsed"])
res = dict(n=len(checks), failed=[c for c in checks if not c["passed"]], passed=all(c["passed"] for c in checks), checks=checks)
json.dump(res, open("ARITH_CHECK.json", "w"), indent=1); print("arith checks", len(checks), "failed", len(res["failed"])); assert res["passed"], res["failed"]
