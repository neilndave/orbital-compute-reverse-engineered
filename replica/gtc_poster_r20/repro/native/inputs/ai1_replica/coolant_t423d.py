"""t423d coolant-loop sub-model: re-implements the repo's bus_model.py coolant block (src/rack_two_skies/bus_model.py lines 109-149, configs/bus.yaml)
with the P6 reference geometry (results/p6/bus_model.json) so each line item can be decomposed and each lever (dT, pump specific mass, fluid, two-phase, shorter runs) tested.
At the reference (197.4 kW, dT 9.8 K, water, ISS pump modules, 208.6 m2 planform) it reproduces 1061.4 / 8.0 / 4.45 / 207.9 kg.
Labels: C/D/E from the repo yaml; new items tagged in REF_SRC below.  Box only."""
import math
P_REF = 197.4; A_REF = 417.2143539385501 / 2.0           # planform m2 of the P6 radiator (2 wings x 30.05 m x 3.512 m)
G = dict(cp=4180.0, rho=978.0, mu=4.0e-4, u=2.0, wall_min=0.8e-3, p_des=800e3, allow=60e6, rho_pipe=2700.0, L_trunk=4.1, extra=3.0,
         rack_liq_L=60.0, rack_dp=100e3, man_dp=50e3, panel_dp0=0.4537e3, wing_len=30.04986423186551, panel_L=58.58897881521675,
         pm_kg=353.8, pm_flow=1.67e-3, pm_dp=362e3, spares=1, valve_kg=2.0, n_valves=4, dT0=9.8, n_trunk=2, dp_exp=1.8)
FLUID = {"water": dict(rho=978.0, cp=4180.0, mu=4.0e-4, p_des=800e3),
         # CoolProp 6.x saturated liquid at 343 K: rho 526.6, cp 5468; sat pressure 33.0 bar at 343 K (59 bar at 370 K); design pressure = 1.3 x sat (ESTIMATE); mu ESTIMATE kept at water value (not looked up)
         "nh3": dict(rho=526.6, cp=5468.0, mu=2.0e-4, p_des=1.3 * 33.0e5)}
def cool(P, A_rad, dT=9.8, pump=1.0, fluid="water", spares=1, panel_fluid=True, run_scale=1.0, rack_liq_scale=1.0, two_phase=False, x_exit=0.5, hfg=2.265e6, u_vap=25.0,
         rho_vap=0.54, pm_floor=0.25, fluid_props=None):
    """kg of pumps/valves/piping/fluid for a loop carrying P kW (peak) with radiator planform A_rad (m2, one face).  pump = multiplier on the ISS module mass (repo's 0.25 = 'light pump')."""
    g = dict(G); g.update(FLUID[fluid]); g.update(fluid_props or {}); r = P / P_REF; ar = A_rad / A_REF
    if two_phase: mdot = P * 1e3 / (hfg * x_exit)
    else: mdot = P * 1e3 / (g["cp"] * dT)
    Vdot = mdot / g["rho"]; nt = g["n_trunk"]; nl = 2 * nt; q = Vdot / nt
    d = math.sqrt(4 * q / (math.pi * g["u"])); t = max(g["wall_min"], g["p_des"] * d / (2 * g["allow"]))
    L = g["L_trunk"] * run_scale
    m_pipe = nl * L * g["rho_pipe"] * math.pi * ((d / 2 + t) ** 2 - (d / 2) ** 2); v_trunk = nl * L * math.pi * (d / 2) ** 2 * 1e3
    m_vap_pipe = 0.0
    if two_phase:    # add vapour return lines sized at u_vap (INFERENCE)
        Vv = mdot * x_exit / rho_vap; dv = math.sqrt(4 * (Vv / nt) / (math.pi * u_vap)); tv = max(g["wall_min"], g["p_des"] * dv / (2 * g["allow"]))
        m_vap_pipe = nl * L * g["rho_pipe"] * math.pi * ((dv / 2 + tv) ** 2 - (dv / 2) ** 2)
    scale_dp = (g["dT0"] / dT) ** g["dp_exp"] if not two_phase else ((mdot / (P * 1e3 / (g["cp"] * g["dT0"]))) ** g["dp_exp"])
    dp_rack = g["rack_dp"] * scale_dp; dp_man = g["man_dp"] * scale_dp
    Re = g["rho"] * g["u"] * d / g["mu"]; f = 0.316 * Re ** -0.25 if Re > 4000 else 64 / Re
    dp_trunk = (f * (2 * L) / d + 4.0) * g["rho"] * g["u"] ** 2 / 2 * (1.0 if not two_phase else 1.0)
    dp_panel = g["panel_dp0"] * (g["dT0"] / dT) * (r / ar) if not two_phase else g["panel_dp0"]
    dp = dp_rack + dp_man + dp_trunk + dp_panel; P_hyd = Vdot * dp
    P_mod = g["pm_flow"] * g["pm_dp"]; n_act = max(1, math.ceil(P_hyd / P_mod - 1e-9)); u_ld = P_hyd / n_act / P_mod
    mod_kg = g["pm_kg"] * pump * (1.0 if u_ld >= 0.5 else max(pm_floor, 2.0 * u_ld))
    pumps = (n_act + spares) * mod_kg
    valves = g["n_valves"] * g["valve_kg"]
    v_rack = g["rack_liq_L"] * r * rack_liq_scale * (0.5 if two_phase else 1.0)
    L_wing = g["wing_len"] * ar * run_scale
    v_man = 0.5 * nl * math.pi * (d / 2) ** 2 * L_wing * 1e3
    v_panel = g["panel_L"] * ar * (0.5 if two_phase else 1.0)
    fl = lambda L_: L_ * 1e-3 * g["rho"]
    parts = dict(pumps=pumps, valves=valves, piping=m_pipe + m_vap_pipe, fluid_rack=fl(v_rack), fluid_trunk=fl(v_trunk), fluid_manifold=fl(v_man),
                 fluid_panel=fl(v_panel) if panel_fluid else 0.0)
    parts["fluid_total"] = parts["fluid_rack"] + parts["fluid_trunk"] + parts["fluid_manifold"] + parts["fluid_panel"]
    parts["accumulator_L_check"] = 0.10 * (v_rack + v_trunk + v_man + v_panel)   # ISS pump module already contains an accumulator; volume check only
    parts["total"] = parts["pumps"] + parts["valves"] + parts["piping"] + parts["fluid_total"]
    parts["diag"] = dict(mdot=mdot, Vdot_L_s=Vdot * 1e3, d_mm=d * 1e3, P_hyd_W=P_hyd, n_active=n_act, module_kg=mod_kg, dp_kPa=dp / 1e3, load=u_ld, P_pump_elec_W=P_hyd / 0.5)
    return parts
if __name__ == "__main__":
    c = cool(197.4, A_REF); print({k: (round(v, 2) if not isinstance(v, dict) else v) for k, v in c.items()})
