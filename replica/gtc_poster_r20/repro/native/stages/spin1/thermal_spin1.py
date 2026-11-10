"""SPIN1 thermal rerun (box CPU, scipy brentq; same model as the frozen baseline's operating(): v2: Al6061 26/0.225 Warp fin table (fin_v2.py), area factor 1.0 (was F3_L40_t0p5 / K13D 0.9913), 0.44 K MC margin,
pmad 0.92, aux 2 kW, rack rise 20 K at the load, radiator rise = 20 K x Q/IT). Knobs added (defaults reproduce the frozen baseline exactly):
  fluid: 'water_proxy' (rho 978, cp 4180, mu 4e-4 = baseline CT.G) or 'MPG40' (CoolProp INCOMP::MPG[0.4] at the rack-mean temperature, iterated);
         MPG40 hydraulic penalty: rack and column dp scaled by mu_MPG40/mu_model (laminar-conservative, ASSUMED), trunk via Re (CT.cool);
  extra_heat_W: added heat into the main radiator (battery-recharge PMAD loss);  F_scale: emission view multiplier (bumper ridge blockage).
Plate resistance 14.22 K/kW and HBM 18 K/load-fraction are unchanged (inherited)."""
import os
import sys, json, math, copy
ARGS = sys.argv[1:]; sys.argv = sys.argv[:1]; sys.path.insert(0, os.environ["GTCFC_ROOT"]+"/inputs/ai1_replica/checks_t538")
import model_t549 as M
sys.path.insert(0, os.environ['GTCFC_ROOT']+'/stages'); import fin_v2 as FV; FIN_TAB = FV.register(M, os.environ['GTCFC_ROOT']+'')   # v2 t619 Al fin table
import CoolProp.CoolProp as CPr
from geometry_v3 import apply,CFG
if CFG.get("august_radiator"): FV.register_selected(M,os.environ["GTCFC_ROOT"]+"",CFG["august_radiator"])
CT = M.CT; C13 = M.C13
WATER = dict(rho=978.0, cp=4180.0, mu=4.0e-4)
def mpg40(T):
    T = min(T, 373.15)   # CoolProp INCOMP::MPG validity limit; properties clamped above 373.15 K (peak diagnostics only, flagged)
    return dict(rho=CPr.PropsSI("D", "T", T, "P", 3e5, "INCOMP::MPG[0.4]"), cp=CPr.PropsSI("C", "T", T, "P", 3e5, "INCOMP::MPG[0.4]"), mu=CPr.PropsSI("V", "T", T, "P", 3e5, "INCOMP::MPG[0.4]"), k=CPr.PropsSI("L", "T", T, "P", 3e5, "INCOMP::MPG[0.4]"))
def cool2f(P, A_rad, npan, ncol, dT, ps, fp, pump_unit=2.0, valve=0.5, eta=0.20, head_extra_kPa=10.0, dp_col_kPa=40.4):
    mur = fp["mu"] / WATER["mu"]; G0 = dict(CT.G); CT.G.update(man_dp=0.0, panel_dp0=0.0, cp=fp["cp"], rho=fp["rho"], mu=fp["mu"], rack_dp=CT.G["rack_dp"] * mur)
    try: c = CT.cool(P, A_rad, dT=dT, panel_fluid=False, run_scale=0.5, pump=0.10, spares=2, fluid_props=fp)
    finally: CT.G.clear(); CT.G.update(G0)
    c = dict(c); c["fluid_total"] = c["fluid_rack"] + c["fluid_trunk"]; ctot = c["pumps"] + c["valves"] + c["piping"] + c["fluid_total"]
    rr = fp["rho"] / WATER["rho"]
    Vd = c["diag"]["Vdot_L_s"] * 1e-3; Qc = Vd / npan * (npan / ncol); head = (dp_col_kPa * mur + head_extra_kPa) * 1e3
    Phyd = Qc * head; mod = max(pump_unit, 0.0586 * Phyd) + valve
    col = (ncol + ps) * mod + C13.FLP * rr * npan + C13.WLP * npan + 0.02 * npan + C13.PANEL_FLUID * rr * npan
    return ctot + col, c["diag"]["P_hyd_W"] / 0.5 + ncol * Phyd / eta, mod, dict(fluid_rack=c["fluid_rack"], fluid_trunk=c["fluid_trunk"], hdr_fluid=C13.FLP * rr * npan, panel_fluid=C13.PANEL_FLUID * rr * npan, mu_ratio=mur, Vdot_L_s=c["diag"]["Vdot_L_s"])
def radiator_film(mo,p,Q,fp):
    if not getattr(mo,'v3_fin',{}).get('radiator_film'):return dict(delta_K=0.,Re=0.,Nu=0.,h_W_m2K=0.)
    a=mo.v3_fin;D=a['tube_ID_m'];nt=a['NT'];md=p*1000/(fp['cp']*20.)
    Re=4*(md/(mo.ncol0*nt))/(math.pi*D*fp['mu']);Pr=fp['cp']*fp['mu']/fp.get('k',.6)
    f=(.79*math.log(max(Re,3000.))-1.64)**-2
    turbulent=(f/8*(max(Re,3000.)-1000)*Pr)/(1+12.7*math.sqrt(f/8)*(Pr**(2/3)-1))
    Nu=3.66 if Re<=2300 else turbulent if Re>=3000 else 3.66+(turbulent-3.66)*(Re-2300)/700
    h=Nu*fp.get('k',.6)/D;area=mo.npan0*nt*math.pi*D*a['panel_length_m']
    return dict(delta_K=Q/(h*area),Re=Re,Nu=Nu,h_W_m2K=h,internal_area_m2=area,model='Gnielinski/laminar transition, circular 8/7-mm tubes; engineering correlation')
def operating(mo, load, fluid="water_proxy", extra_heat_W=0.0, F_scale=1.0, dR_KW=0.0):
    dT = 20.; p = mo.P * load; npan = mo.npan0; ncol = mo.ncol0; area = mo.A0
    Tm = 365.0; it = 0
    while True:
        fp = WATER if fluid == "water_proxy" else mpg40(Tm)
        c, pump, mod, inv = cool2f(p, area, npan, ncol, dT, 2, fp)
        Q = (p * 1000 + 2000 + pump) / .92 + extra_heat_W; rad_dT = dT * Q / (p * 1000)
        k = M.DEFAULTS; F = mo.Fe * k['yoke_Feff_scale'] * (k['coat_F0'] / .99) * F_scale; ee, sink, beta = M._ee_Ts(k['eps0'], F, k['alpha_eol'], k['qscale'])
        root = M.supply_for_area(Q, area / FV.AREA_FACTOR, k['eps0'], F, k['alpha_eol'], k['qscale'], rad_dT, getattr(mo,"v3_fin",{}).get("fin_id",FIN_TAB))
        film=radiator_film(mo,p,Q,fp)
        supply = root + .44 + film["delta_K"]; ref = supply + dT / 2
        it += 1
        if fluid == "water_proxy" or abs(ref - Tm) < 1e-6 or it > 30: break
        Tm = ref
    gpu = ref + 1.7 * load * (14.22 + dR_KW); hbm = ref + 18 * load
    return dict(radiator_film=film,fin_root_supply_K=root+.44,load_fraction=load, IT_kW=p, fluid=fluid, fluid_props=fp, pump_electric_W=pump, extra_heat_W=extra_heat_W, F_scale=F_scale, dR_plate_KW=dR_KW,
                total_solar_power_and_rejected_heat_W=Q, radiator_delta_K=rad_dT, coolant_supply_K=supply, coolant_rack_mean_K=ref, coolant_radiator_inlet_K=supply + rad_dT,
                GPU_K=gpu, HBM_K=hbm, effective_emissivity=ee, effective_radiation_sink_K=sink, mass_flow_kg_s=p * 1000 / (fp["cp"] * dT), inventory=inv,
                coolant_colder_than_chips=(supply + rad_dT) < min(gpu, hbm))
def coolant_line(mo, fluid):
    """calibrated coolant line (same calibration as the frozen baseline: L0/cool0 at peak sizing) minus the identified duplicated panel fluid"""
    fp = WATER if fluid == "water_proxy" else mpg40(372.0)
    raw, _, _, inv = cool2f(mo.P, mo.A0, mo.npan0, mo.ncol0, 20.0, 2, fp); scale = mo.L0["coolant_loop"] / mo.cool0
    credit = scale * C13.PANEL_FLUID * mo.npan0 * (fp["rho"] / WATER["rho"])
    return scale * raw - credit, dict(raw=raw, scale=scale, credit=credit, props_at_K=372.0 if fluid != "water_proxy" else None)
if __name__ == "__main__":
    base = json.load(open(os.environ["GTCFC_ROOT"]+"/stages/baseline/GTC_SCOPED_BASELINE_EXACT.json"))
    inp = json.load(open(ARGS[0])) if len(ARGS) > 0 else {}
    out = dict(doc=__doc__, cases={})
    for i, tag in enumerate(["J8", "A4"]):
        mo = M.Month(tag); nm = ["June", "August"][i]; nl = [.8, .7][i]; B = base["fleets"][i]; R = {}
        R["T0_baseline_nominal"] = operating(mo, nl); R["T0_baseline_peak"] = operating(mo, 1.0)
        R["T0_check_GPU_diff_K"] = [R["T0_baseline_nominal"]["GPU_K"] - B["nominal"]["GPU_K"], R["T0_baseline_peak"]["GPU_K"] - B["full_peak_steady_sensitivity"]["GPU_K"]]
        R["T0_check_Q_diff_W"] = [R["T0_baseline_nominal"]["total_solar_power_and_rejected_heat_W"] - B["nominal"]["total_solar_power_and_rejected_heat_W"], R["T0_baseline_peak"]["total_solar_power_and_rejected_heat_W"] - B["full_peak_steady_sensitivity"]["total_solar_power_and_rejected_heat_W"]]
        cw, _ = coolant_line(mo, "water_proxy"); apply(mo,nm); cg, cgd = coolant_line(mo, "MPG40"); R["geometry_v3"]=dict(radiator_panels=mo.npan0,radiator_face_area_m2=mo.A0,radiator_columns=mo.ncol0,fin=getattr(mo,'v3_fin',FV.FIN))
        if getattr(mo,'v3_fin',None):
            a=mo.v3_fin;nt=a['NT'];ll=a['panel_length_m'];rho=mpg40(352.)['rho']
            R['radiator_wet_mass_kg']=mo.npan0*nt*ll*(2*a['half_length_m']*a['thickness_m']*2700+math.pi*(a['tube_OD_m']**2-a['tube_ID_m']**2)/4*2700+math.pi*a['tube_ID_m']**2/4*rho)
            R['radiator_mass_reference_fluid_density_kg_m3']=rho
        R["coolant_line_water_kg"] = cw; R["coolant_line_MPG40_kg"] = cg; R["coolant_line_delta_kg"] = cg - cw; R["coolant_line_baseline_kg"] = [x["kg"] for x in B["ledger"] if x["item"] == "coolant_loop"][0]; R["coolant_detail"] = cgd
        power_v3=json.load(open("POWER_SPIN1.json"))["cases"][nm]["adopted_array"]
        mo.Fe=power_v3["effective_view_new"]
        R["T0_scenario_new_geometry"]=operating(mo,nl)
        R["array_v3_view_factor_delta"]=power_v3["delta_array_view_factor"]
        R["T1_MPG40_nominal"] = operating(mo, nl, "MPG40"); R["T1_MPG40_peak"] = operating(mo, 1.0, "MPG40")
        xh = inp.get(nm, {}).get("recharge_heat_W", 0.0); Fs = inp.get(nm, {}).get("header_protect_F_scale", 1.0)
        R["T2_rec_nominal_MPG40_plus_recharge"] = operating(mo, nl, "MPG40", extra_heat_W=xh); R["T2_rec_peak_MPG40"] = R["T1_MPG40_peak"]
        R["T4_sens_header_protected_nominal"] = operating(mo, nl, "MPG40", extra_heat_W=xh, F_scale=Fs); R["T4_sens_header_protected_peak"] = operating(mo, 1.0, "MPG40", F_scale=Fs)
        kw_ = CPr.PropsSI("L", "T", R["T1_MPG40_nominal"]["coolant_rack_mean_K"], "P", 3e5, "Water"); kg_ = R["T1_MPG40_nominal"]["fluid_props"]["k"]
        dR = 14.22 * 0.5 * (kw_ / kg_ - 1.0); R["T5_sens_film_dR_KW"] = dR; R["T5_sens_film_nominal"] = operating(mo, nl, "MPG40", extra_heat_W=xh, dR_KW=dR)
        out["cases"][nm] = R
        for k in ("T0_baseline_nominal", "T0_baseline_peak", "T1_MPG40_nominal", "T1_MPG40_peak", "T2_rec_nominal_MPG40_plus_recharge", "T4_sens_header_protected_nominal", "T4_sens_header_protected_peak", "T5_sens_film_nominal"):
            r = R[k]; print(nm, k, "Q", round(r["total_solar_power_and_rejected_heat_W"], 1), "pump", round(r["pump_electric_W"], 1), "sup", round(r["coolant_supply_K"], 3), "GPU", round(r["GPU_K"], 3), "HBM", round(r["HBM_K"], 3), "inlet", round(r["coolant_radiator_inlet_K"], 3))
        print(nm, "checks", R["T0_check_GPU_diff_K"], R["T0_check_Q_diff_W"], "coolant", cw, cg, R["coolant_line_baseline_kg"], "dR", dR)
    json.dump(out, open(ARGS[1] if len(ARGS) > 1 else "THERMAL_SPIN1.json", "w"), indent=1, default=float)
