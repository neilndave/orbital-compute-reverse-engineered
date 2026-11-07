"""Water-retained alternative: pumps ON through eclipse, loop held >= 278.15 K (5 K above 273.15 K, ASSUMED) by battery heaters. Lumped loop (all wetted mass mixed by flow).
Emission 2*ee*sigma*(T^4-Ts_ecl^4) on the physical planform (no fin-efficiency credit: conservative), eclipse sink = 'table' Earth IR. Pump electric power + 500 W bus loss (as nbf) treated as heat in."""
import json, math
SIG = 5.670374419e-8; out = {}
_E = json.load(open("/tmp/gtcfc_root/stages/spin1/../orbit/ECLIPSE_600KM.json"))   # FINAL: 600-km eclipse facts
for tag, nm in (("J8", "June"), ("A4", "August")):
    S = json.load(open(f"scen_{tag}_water_table.json")); TH = json.load(open("/tmp/gtcfc_root/stages/spin1/THERMAL_SPIN1.json"))["cases"][nm]["T0_baseline_nominal"]
    tube_wall = 4 * (6.094e-3 ** 2 - 2.954e-3 ** 2) * 2.9446 * 2700.0
    inv = TH["inventory"]; fluid = inv["fluid_rack"] + inv["fluid_trunk"] + inv["hdr_fluid"] + inv["panel_fluid"]
    C = fluid * 4190 + S["npan"] * (S["fin_kg_per_panel"] + tube_wall + S["hdr_wall_kg_per_panel"]) * 900 + S["Chw"]
    A = S["npan"] * S["plan"]; ee = S["ee"]; Ts = S["Ts_ecl"]; pump = TH["pump_electric_W"]; qin = pump + 0.0   # bus loss leaves the loop -> not credited
    T = S["Tsup"] + 10.0; t = 0.0; dt = 1.0; E = 0.0; ECL = _E["max_shadow_min"] * 60; Th = 278.15; t_hold = None
    while t < ECL:
        P = 2 * ee * SIG * (T ** 4 - Ts ** 4) * A
        if T <= Th:
            if t_hold is None: t_hold = t
            E += max(0.0, P - qin) * dt; T = Th
        else: T += (qin - P) * dt / C
        t += dt
    E_kWh = E / 3.6e6; cycles = _E["eclipsed_orbits_per_year"] * 5; nameplate = E_kWh / 0.93 / (0.40 * 0.88); m = nameplate * 1000 / (512 / 5.8)
    out[nm] = dict(C_J_per_K=C, fluid_kg=fluid, t_reach_278K_min=t_hold / 60 if t_hold else None, hold_power_kW=2 * ee * SIG * (Th ** 4 - Ts ** 4) * A / 1e3, heater_energy_kWh=E_kWh,
                   battery_nameplate_kWh=nameplate, battery_pack_kg=m, cycles_5yr=cycles, pump_W=pump, note="plus pump energy from battery; plus burst/drain risk if any branch stagnates")
    print(nm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[nm].items()})
json.dump(out, open("WATER_KEEPWARM_SPIN1.json", "w"), indent=1)
