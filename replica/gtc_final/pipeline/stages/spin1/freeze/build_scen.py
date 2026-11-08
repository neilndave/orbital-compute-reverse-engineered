import json, math, sys, numpy as np
sys.argv = sys.argv[:1]; sys.path.insert(0, "/tmp/gtcv2_root/inputs/ai1_replica/checks_t538"); sys.path.insert(0, "/tmp/gtcv2_root/stages/spin1")
import model_t549 as M
sys.path.insert(0, "/tmp/gtcv2_root/stages"); import fin_v2 as FV; NT = FV.FREEZE_GEOM["NT"]; TF = FV.FREEZE_GEOM["tf_m"]   # v2 t619
SIG = 5.670374419e-8
TH = json.load(open("/tmp/gtcv2_root/stages/spin1/THERMAL_SPIN1.json")); base = json.load(open("/tmp/gtcv2_root/stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"))
_E = json.load(open("/tmp/gtcv2_root/stages/spin1/../orbit/ECLIPSE_600KM.json")); betas = np.linspace(_E["beta_abs_range_on_eclipse_days_deg"][0], _E["beta_star_deg"], 9); Fb = float(np.mean(np.interp(betas, M._e["beta"], M._e["F_earth"])))   # FINAL: 600-km eclipse beta range (spin1: 59-67 deg, 550 km)
for i, (tag, nm) in enumerate((("J8", "June"), ("A4", "August"))):
    mo = M.Month(tag); B = base["fleets"][i]; rad = [x["kg"] for x in B["ledger"] if x["item"] == "radiator"][0]
    tube_wall = NT * (6.094e-3 ** 2 - 2.954e-3 ** 2) * 2.9446 * 2700.0
    fin_kg = rad / mo.npan0 - M.C13.PANEL_FLUID - tube_wall; plan = mo.A0 / mo.npan0
    rack = [x["kg"] for x in B["ledger"] if x["item"] == "rack"][0]; Chw = 0.5 * rack * (0.45 * 900 + 0.30 * 385 + 0.05 * 500 + 0.20 * 705)
    for fluid, key in (("MPG40", "T2_rec_nominal_MPG40_plus_recharge"), ("water", "T0_baseline_nominal")):
        r = TH["cases"][nm][key]; inv = r["inventory"]; cp = r["fluid_props"]["cp"]; ee = r["effective_emissivity"]
        for sink, olr in (("table", 239.0), ("cold", 150.0)):
            q = 0.92 * olr * Fb; Ts = (q / (ee * SIG)) ** 0.25
            S = dict(tag=f"{tag}_{fluid}_{sink}", npan=mo.npan0, NT=NT, tf_m=TF, DT=0.04, plan=plan, fin_cap_J_per_m2K=fin_kg / plan * 900.0, fin_kg_per_panel=fin_kg,
                     hdr_fluid_kg_per_panel=inv["hdr_fluid"] / mo.npan0, hdr_wall_kg_per_panel=M.C13.WLP, mdot=r["mass_flow_kg_s"], Tsup=r["coolant_supply_K"], Tret=r["coolant_radiator_inlet_K"],
                     Qavg=r["total_solar_power_and_rejected_heat_W"], Pavg=r["IT_kW"] * 1000.0, ee=ee, Ts_ecl=Ts, Ts_sun=r["effective_radiation_sink_K"], Fb=Fb, olr=olr,
                     Chw=Chw, Cfl=(inv["fluid_rack"] + inv["fluid_trunk"]) * cp, source_case=key)
            json.dump(S, open(f"scen_{S['tag']}.json", "w"), indent=1); print(S["tag"], {k: (round(v, 4) if isinstance(v, float) else v) for k, v in S.items()})
