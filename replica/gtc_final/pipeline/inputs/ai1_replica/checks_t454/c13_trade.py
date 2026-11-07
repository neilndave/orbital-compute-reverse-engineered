"""t454: mass / kW per t / sats-per-Starship recompute with ALL approved changes, and the radiator-growth trade.  Box CPU, NVIDIA Warp for thermal-geometry (c14), MMOD MC (c12 method), coolant ladder (c10c).  ESTIMATE; labelled assumptions inline."""
import sys, os, json, math, numpy as np, warp as wp
wp.config.quiet = True
HERE = "/tmp/gtcfc_root/inputs/ai1_replica"; sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/checks_t454"); sys.dont_write_bytecode = True
sys.argv = sys.argv[:1]
import coolant_t423d as CT
import orbit_loop as O
from c10_coolant import RHO, panel_dp, LS
from c10c_taper import taper, fluid_kg, ladder_t
sys.path.insert(0, "/tmp/gtcfc_root/inputs/repo/src")
from rack_two_skies.mmod_env import whipple
from c12_mmod_fn import sweep
PT = json.load(open(f"{HERE}/results/t434_region.json"))["points"]
TH = json.load(open(f"{HERE}/checks_t454/c14_thermal.json"))
B = dict(Jun=dict(key="Jun8|C1", N=46, npan=77, P=150.0, Mt=150 / 70 * 1e3, floor=70.0), Aug=dict(key="Aug4|C1", N=30, npan=128, P=250.0, Mt=250 / 75 * 1e3, floor=75.0))
PIT_AL = 0.0                                                                           # unused
WALL_T = 0.8e-3; RHO_AL = 2700.0; FLEX = 1.1                                         # header wall 0.8 mm Al (ASSUMED), x1.1 for corrugated hinge sections (10 % of length at 2x wall, ASSUMED)
HDR = dict(droot=20e-3, dmin=10e-3, n=10)                                              # chosen from c10c_taper: 20 mm root / 10 mm min, orifice ko 9.6
def hdr_per_panel():
    ds, dr = taper(HDR["droot"], HDR["n"], HDR["dmin"]); fl = fluid_kg(ds, dr) / HDR["n"]
    wall = sum(math.pi * d * WALL_T * RHO_AL * LS for d in list(ds) + list(dr)) / HDR["n"] * FLEX
    return fl, wall
FLP, WLP = hdr_per_panel()
PANEL_FLUID = 4 * ((6.094 - 2 * 1.57) * 1e-3) ** 2 * 2.9446 * RHO                    # kg per panel (4 tubes, bore 2.954 mm)
def prop(Mcore, Aram, life=3, isp=2500, rho_key="solar_mean", h=600):
    v = O.v_circ(h); dvr = max(0, O.v_circ(350) - v); dvs = abs(O.v_circ(200) - v); rho = O.dens[rho_key][h]; pr = 0.0
    for _ in range(300):
        dry = Mcore - pr; p = 0.0
        for i in range(300):
            dvd = 0.5 * rho * v * v * 2.2 * Aram / (dry + 0.5 * p) * life * 365.25 * 86400
            pn = dry * (math.exp((dvr + dvd + dvs) / (O.G0 * isp)) - 1) * 1.21
            if abs(pn - p) < 1e-9: break
            p = pn
        if abs(p - pr) < 1e-9: break
        pr = p
    return pr
def coolant_new(b, P, A_rad, npan, ncol, pump_unit=2.0, valve=0.5, eta=0.20, head_extra_kPa=10.0, dp_col_kPa=40.4):
    G0 = dict(CT.G); CT.G["man_dp"] = 0.0; CT.G["panel_dp0"] = 0.0
    try: c = CT.cool(P, A_rad, dT=20.0, panel_fluid=False, run_scale=0.5, pump=0.10, spares=2)
    finally: CT.G.clear(); CT.G.update(G0)
    c = dict(c); c["fluid_manifold"] = 0.0; c["fluid_total"] = c["fluid_rack"] + c["fluid_trunk"]; c["total"] = c["pumps"] + c["valves"] + c["piping"] + c["fluid_total"]
    Vd = c["diag"]["Vdot_L_s"] * 1e-3; Qc = Vd / npan * (npan / ncol); head = (dp_col_kPa + head_extra_kPa) * 1e3
    Phyd = Qc * head; mod = max(pump_unit, 0.0586 * Phyd) + valve; col_pumps = (ncol + 2) * mod
    col = dict(n_col=ncol, Q_col_L_s=Qc * 1e3, head_kPa=head / 1e3, P_hyd_W=Phyd, P_elec_W=Phyd / eta, module_kg=mod, pumps_col=col_pumps, hdr_fluid=FLP * npan, hdr_wall=WLP * npan, orifices=0.02 * npan, panel_fluid=PANEL_FLUID * npan)
    col["total"] = col["pumps_col"] + col["hdr_fluid"] + col["hdr_wall"] + col["orifices"] + col["panel_fluid"]
    tot = c["total"] + col["total"]
    return dict(central=c, columns=col, total=tot, P_elec_total_W=c["diag"]["P_hyd_W"] / 0.5 + ncol * Phyd / eta)
def build_case(b, npan_new, Aoverride, struct_dkg, bump_kg, ncol, pump_unit=2.0, margin_mode="policy"):
    d = B[b]; p = PT[d["key"]]; L = dict(PT[d["key"]]["lines"] if "lines" in PT[d["key"]] else {})
    pt = json.load(open(f"{HERE}/gtc_params/point_{'J8' if b == 'Jun' else 'A4'}_C1.json")); L = dict(pt["mass_lines_kg"])
    A0 = p["A_rad"]; A1 = A0 * npan_new / d["npan"]
    cn = coolant_new(b, d["P"], A1, npan_new, ncol, pump_unit=pump_unit)
    core0 = sum(v for k, v in L.items() if k not in ("margin", "mmod_bumper", "adapter"))
    lines = dict(L); lines["radiator"] = L["radiator"] * npan_new / d["npan"]; lines["coolant_loop"] = cn["total"]; lines["structure_mech"] = L["structure_mech"] + struct_dkg
    core = sum(v for k, v in lines.items() if k not in ("margin", "mmod_bumper", "adapter"))
    Aram = A1 + 15 + p["A_arr"] * 2 / math.pi * O.beta_stats(600, 6.0)[1]
    # propulsion line carries the propellant: replace by dry part + new propellant (loop fixed point on M_core)
    pr0 = p["prop"]; pr1 = prop(core, Aram); lines["propulsion_adcs"] = L["propulsion_adcs"] - pr0 + pr1; core = sum(v for k, v in lines.items() if k not in ("margin", "mmod_bumper", "adapter"))
    pr1 = prop(core, Aram); lines["propulsion_adcs"] = L["propulsion_adcs"] - pr0 + pr1; core = sum(v for k, v in lines.items() if k not in ("margin", "mmod_bumper", "adapter"))
    lines["mmod_bumper"] = bump_kg
    if margin_mode == "policy": lines["margin"] = 0.205 * (core + bump_kg - pr1)            # repo policy: 20.5 % of (core + bumper - propellant)
    elif margin_mode == "fixed": lines["margin"] = L["margin"]                              # margin kept at the baseline kg (added items NOT charged growth)
    else: lines["margin"] = L["margin"] - ((core + bump_kg) - (core0 + L["mmod_bumper"]))    # 'consumed': total mass held, items paid from the growth reserve
    M = sum(lines.values()); res = dict(M=M, kwt=d["P"] / M * 1e3, N98=int(98000 // M), N100=int(100000 // M), core=core, prop=pr1, margin=lines["margin"], A_rad=A1, npan=npan_new, lines={k: round(v, 2) for k, v in lines.items()},
                                          cool=cn, margin_pct_of_core=lines["margin"] / (core + bump_kg - pr1))
    return res
if __name__ == "__main__":
    print(FLP, WLP, PANEL_FLUID)
