"""t423c: copy of orbit_loop_t423.py with four extra switches (rack_scale/rack_ref_kW, pcdu_kwkg, dv_extra, deorbit). All other physics identical; defaults reproduce t423."""
"""t423: orbit_loop with (1) the replica's fin-table / required-supply-temperature radiator step, switchable against the old flat-strip step,
(2) a peak-vs-average radiator sizing lever with its consequence, (3) finer mass bookkeeping (PCDU vs harness, subsystem map) and an optional repo-accounting add-back layer.
Does NOT modify orbit_loop.py, results/*.json or any adopted baseline.  New file only.  Box only (numpy/scipy/pandas).
Labels: STATEMENT / ESTIMATE / INFERENCE / ASSUMED as in orbit_loop.py.
Radiator model 'replica_fin' (ESTIMATE, calibrated interpolation of the t410 GB10 Monte Carlo + sizing runs, 12 fin x optics fits, residual <= 1.9 %):
   q_face + q_abs_replica = a * SIGMA * (T_supply_p95 - c)^4     with q_face = P/(2A) per face,  fit per (fin, optics)   [see fit_replica()]
   area at a coolant-supply cap:  A = P*1000 / (2*(a*SIGMA*(T_cap-c)^4 - q_abs_loop))   (loop's own orbit/alpha q_abs replaces the replica's mean q_abs)
   mass = A * (fin_areal_kg_m2[fin] + rad_overhead)   -> fin sheet + tube + fluid only; no headers, pumps or shield (lower bound, as in the t410 write-up).
T_cap is a COOLANT SUPPLY cap (p95 of the Monte Carlo, 20 K loop rise), not a chip temperature."""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import numpy as np
import coolant_t423d as CT, pandas as pd
from scipy.optimize import least_squares
import orbit_loop as O
SIG = O.SIG
R = os.path.join(HERE, "gb10_run_t410", "results")
FIN_KG = {"F1_L60_t0p8": 2.599752, "F2_L80_t1p0": 3.009335, "F3_L40_t0p5": 2.063276}   # kg per planform m2 (t410 summary_sizing.csv fin_areal_kg_m2; STATEMENT of the run output, ESTIMATE physically)
LOADS = {("J8", "peak"): 150.0, ("J8", "avg"): 120.0, ("A4", "peak"): 250.0, ("A4", "avg"): 175.0}   # kW; SpaceX 150/250 peak, 120/175 avg (repo SPACEX_ENVELOPE, STATEMENT)
def fit_replica(write=True):
    m = pd.read_csv(f"{R}/summary_mc.csv"); s = pd.read_csv(f"{R}/summary_sizing.csv"); rows = []; qa = {}
    for _, r in m[m.case.str.endswith("|base")].iterrows():
        b, load, fin, opt, _ = r.case.split("|"); bk, A = b.split("_"); rows.append((fin, opt, load, bk, float(A), r.p95_K)); qa[opt] = float(r.q_abs_mean)
    for _, r in s.iterrows():
        b, load, fin, opt, lim = r.case.split("|"); bk, A = b.split("_"); rows.append((fin, opt, load, bk, float(r.A_needed_m2), float(r.limit_K)))
    d = pd.DataFrame(rows, columns=["fin", "opt", "load", "bk", "A", "T"]); d["P"] = [LOADS[(b, l)] for b, l in zip(d.bk, d.load)]; d["q"] = d.P * 1000 / (2 * d.A)
    fit = {}
    for (fin, opt), g in d.groupby(["fin", "opt"]):
        q = g.q.values + qa[opt]; T = g["T"].values
        f = lambda x: (x[0] * SIG * (T - x[1]) ** 4) / q - 1
        r = least_squares(f, [0.5, -40.0])
        fit[f"{fin}|{opt}"] = dict(a=float(r.x[0]), c=float(r.x[1]), q_abs_replica=qa[opt], n_points=int(len(g)), max_rel_err=float(abs(r.fun).max()),
                                   T_range_K=[float(T.min()), float(T.max())], q_range_Wm2=[float(g.q.min()), float(g.q.max())])
    if write: json.dump(fit, open(os.path.join(HERE, "results", "radiator_fit_t423.json"), "w"), indent=1)
    return fit
_FIT = None
def FIT():
    global _FIT
    if _FIT is None: _FIT = fit_replica(write=False)
    return _FIT
def G_gross(fin, opt, T):                 # W/m2 per face, includes the replica's mean absorbed flux (see module doc)
    f = FIT()[f"{fin}|{opt}"]; return f["a"] * SIG * (T - f["c"]) ** 4
def area_at_cap(P_kW, fin, opt, T_cap, qa_loop):
    return P_kW * 1000.0 / (2.0 * (G_gross(fin, opt, T_cap) - qa_loop))
def req_supply_K(P_kW, A, fin, opt, qa_loop):
    """required coolant supply temperature (p95) for load P on area A (planform, per face)."""
    f = FIT()[f"{fin}|{opt}"]; q = P_kW * 1000.0 / (2 * A) + qa_loop
    return f["c"] + (q / (f["a"] * SIG)) ** 0.25
# ----------------------------------------------------------------------------------------------------------------- evaluate (copy of O.evaluate + new switches)
DEFAULTS = dict(rad_model="flat_strip", rad_fin="F1_L60_t0p8", rad_opt="e92F99", T_cap_K=370.0, rad_basis="peak", rad_overhead=0.0,
                rack_kg=1814.0, harness_V=100.0, pmad_eff=0.92, f_struct_base=None,
                rack_scale=False, rack_ref_kW=188.0, pcdu_kwkg=None, dv_extra=0.0, deorbit=False, si_wkg=960.0)
def evaluate(build, p, h, ltan):
    q_ = dict(DEFAULTS); q_.update(p); p = q_
    B = O.TARGET[build]; P = B["P"]; r = P / O.P_IT_REF
    ec = O.grid[(h, ltan)]; sun = ec["sunlit_frac_equiv"]; t_ecl = ec["max_shadow_min"]; T_orb = ec["T_orb_min"]
    bmin, cosb = O.beta_stats(h, ltan); life = p["life"]
    eol = 1.0 - p["arr_deg"] * life
    bol_cell = 319.7 * (0.72 if p["cell"] == "Si" else 1.0)
    A_arr = P * 1000.0 / (bol_cell * p["pmad_eff"] * eol)
    sig_cell_3J = 319.7 / 480.0; sig_total_3J = 319.7 / p["wkg_wing"]
    sig_arr = sig_total_3J
    if p["cell"] == "Si": sig_arr = sig_total_3J - sig_cell_3J + (319.7 * 0.72 / p["si_wkg"])
    batt = 0.0; A_extra = 0.0; lost = 1.0 - sun
    if p["strategy"] in ("ride", "half"):
        Pr = P * (1.0 if p["strategy"] == "ride" else 0.5); E_kwh = Pr * (t_ecl / 60.0) / (0.8 * 0.9); batt = E_kwh * 1000.0 / p["wh_kg"]
        P_ch = Pr * t_ecl / 0.9 / max(T_orb - t_ecl, 1.0); A_extra = P_ch * 1000.0 / (319.7 * p["pmad_eff"] * eol); lost = (1.0 - sun) * (0.5 if p["strategy"] == "half" else 0.0)
    A_arr_tot = A_arr + A_extra; m_arr = A_arr_tot * sig_arr
    m_deploy = p["deploy"][0] * m_arr + p["deploy"][1] * p["deploy"][2]
    # ---- radiator step (the t423 change)
    ee = 0.90; qa = O.q_abs(h, bmin, p["alpha"], f_g=p["f_g"]); T0 = B["T0"]
    if T0 is None:
        qa0 = O.q_abs(550, O.beta_stats(550, 6.0)[0], O.NOM["alpha"], f_g=O.NOM["f_g"]); q_face0 = P * 1000.0 / (2.0 * B["A_rad"]); T0 = ((q_face0 + qa0) / (ee * SIG)) ** 0.25; B["T0"] = T0
    P_rad = P * (B["avg_over_peak"] if p["rad_basis"] == "avg" else 1.0)       # load the radiator is sized for
    if p["rad_model"] == "flat_strip":
        T = p["T_rad_K"] if p["T_rad_K"] else T0; q_net = ee * SIG * T ** 4 - qa; A_rad = P_rad * 1000.0 / (2.0 * q_net); sig_rad = p["sig_rad"]; T_report = T
    elif p["rad_model"] == "replica_fin":
        T = p["T_cap_K"]; q_net = G_gross(p["rad_fin"], p["rad_opt"], T) - qa; A_rad = P_rad * 1000.0 / (2.0 * q_net); sig_rad = FIN_KG[p["rad_fin"]] + p["rad_overhead"]; T_report = T
    else: raise ValueError(p["rad_model"])
    m_rad = A_rad * sig_rad
    rack = p["rack_kg"] * (1.0 - p["f_strip"]) * ((P / p["rack_ref_kW"]) if p["rack_scale"] else 1.0)
    _cm = None
    if p.get("cool") is not None:       # t423d: physical coolant-loop sub-model (coolant_t423d.py); None keeps the legacy linear-in-P lines
        _cm = CT.cool(P, A_rad, pump=p["pump"], **p["cool"])
    _pu, _va, _pi, _fl = (_cm["pumps"], _cm["valves"], _cm["piping"], _cm["fluid_total"]) if _cm else (1061.4 * r * p["pump"], 8.0, 4.45 * r, 207.9 * r)
    eq = dict(pumps=_pu, valves=_va, piping=_pi, coolant=_fl, pcdu=((P / p["pcdu_kwkg"]) if p["pcdu_kwkg"] else 463.9 * r * p["pmad"]), harness=349.2 * r * p["pmad"] * (100.0 / p["harness_V"]),
              battery_safe=31.25, optical=11.9 * p["n_term"], rf_ttc=6.0, fc=1.2, st=7.8, sens=5.0, thr_ppu=21.6, adcs=144.0 * p["adcs"])
    equip = sum(eq.values()); struct = p["f_struct"] / (1.0 - p["f_struct"]) * (rack + equip)
    d5 = O.dose5(p["life"] and h) * life / 5.0 if False else O.dose5(h) * life / 5.0
    tol, inh, spare = p["rad"]; depth = O.depth_for(d5, tol); add = max(0.0, depth / 10.0 * 2.70 - inh)
    area_rack = 2 * (0.6 * 1.2 + 1.2 * 2.296 + 0.6 * 2.296); shield = area_rack * add * 10.0; spares_kg = spare * rack
    dens = O.dens
    rho = dens[p["solar"]][h] if h in dens[p["solar"]] else float(np.exp(np.interp(h, sorted(dens[p["solar"]]), np.log([dens[p["solar"]][k] for k in sorted(dens[p["solar"]])]))))
    A_ram = A_rad + p["ram_bus"] + A_arr_tot * (2.0 / math.pi) * cosb
    v = O.v_circ(h); dv_raise = max(0.0, O.v_circ(350) - v) if h > 350 else 0.0; dv_disp = abs(O.v_circ(200) - v)
    dry = rack + equip + struct + m_arr + m_deploy + m_rad + batt + shield + spares_kg
    prop = 0.0; resid = 0.0; n_it = 0
    for it in range(60):
        Mavg = dry + 0.5 * prop; dv_drag = 0.5 * rho * v * v * 2.2 * A_ram / Mavg * life * 365.25 * 86400.0; dv = dv_raise + dv_drag + dv_disp + p["dv_extra"] + (dv_raise if p["deorbit"] else 0.0)
        prop_new = dry * (math.exp(dv / (O.G0 * p["isp"])) - 1.0) * 1.10 * 1.10; n_it = it + 1; resid = abs(prop_new - prop) / max(dry + prop_new, 1.0)
        if resid < 1e-6: prop = prop_new; break
        prop = prop_new
    M = dry + prop
    avg_delivered = P * (1.0 - lost) if p["strategy"] != "pause" else P * sun
    out = dict(build=build, h=h, ltan=ltan, P_kW=P, M_kg=M, M_dry_kg=dry, kwt_wet=P / M * 1000.0, kwt_dry=P / dry * 1000.0, kwt_avg_wet=avg_delivered / M * 1000.0,
               target_kwt=B["kwt"], gap_ratio=B["kwt"] / (P / M * 1000.0), budget_kg=P / B["kwt"] * 1000.0,
               A_arr=A_arr_tot, A_rad=A_rad, T_rad_K=T_report, q_abs=qa, q_net=q_net, sig_rad=sig_rad, P_rad_sized_kW=P_rad, sunlit=sun, rho=rho, prop_iters=n_it, avg_over_peak=avg_delivered / P,
               dv=dict(raise_=dv_raise, drag=dv_drag, disp=dv_disp), A_ram=A_ram, t_ecl_max_min=t_ecl, shield_depth_mm=depth)
    out["cool"] = _cm; out["cool_kg"] = _pu + _va + _pi + _fl
    out["mass"] = dict(rack=rack, pumps_coolant=eq["pumps"] + eq["valves"] + eq["piping"] + eq["coolant"], pmad_harness=eq["pcdu"] + eq["harness"], adcs=eq["adcs"],
                       comms_misc=eq["optical"] + eq["rf_ttc"] + eq["fc"] + eq["st"] + eq["sens"] + eq["thr_ppu"] + eq["battery_safe"], structure=struct, array=m_arr, deploy=m_deploy,
                       radiator=m_rad, battery_eclipse=batt, shield=shield, spares=spares_kg, propellant=prop)
    out["lines"] = dict(rack=rack, array=m_arr, radiator=m_rad, coolant_loop=eq["pumps"] + eq["valves"] + eq["piping"] + eq["coolant"],
                        structure_mech=struct + m_deploy, power_electronics=eq["pcdu"] + eq["battery_safe"] + batt, harness=eq["harness"],
                        propulsion_adcs=prop + eq["thr_ppu"] + eq["adcs"], shielding_radiation=shield + spares_kg, mmod_bumper=0.0,
                        avionics_links=eq["optical"] + eq["rf_ttc"] + eq["fc"] + eq["st"] + eq["sens"], margin=0.0)
    out["N_mass_100t"] = int(100000.0 // M); out["N_mass_98t"] = int(98000.0 // M); out["N_mass_114t"] = int(114000.0 // M)
    out["N_vol"] = int(614.0 * 0.35 // (M / 800.0)); out["N_sat"] = min(out["N_mass_100t"], out["N_vol"]); out["limit"] = "mass" if out["N_mass_100t"] <= out["N_vol"] else "volume"
    out["fcc"] = dict(mass_over_cap=M > 4000.0, rad_ok=A_rad <= 200.0, arr_ok=A_arr_tot <= 1500.0)
    out["fcc_flags"] = [k for k, ok in [("mass>4000", not (M <= 4000.0)), ("rad>200", not (A_rad <= 200.0)), ("arr>1500", not (A_arr_tot <= 1500.0))] if ok]
    out["fcc_flags"] = [k for k, bad in [("mass>4000kg", M > 4000.0), ("radiator>200m2", A_rad > 200.0), ("array>1500m2", A_arr_tot > 1500.0)] if bad]
    return out
def best_orbit(build, p, allowed=None):
    best = None
    for (h, l) in (allowed or O.ORBITS):
        o = evaluate(build, p, h, l)
        if best is None or o["kwt_wet"] > best["kwt_wet"]: best = o
    return best
# ----------------------------------------------------------------------------------------------------------------- repo-accounting add-back layer (NOT in the loop's physics)
ADD = dict(bumper_per_bothface_m2=367.0 / 435.0,      # MASS_LEVERS_T45 §2: 367 kg MMOD bumper + loop hardening for 435 m2 both-face radiator (ESTIMATE, scaled by radiator area = INFERENCE)
           adapter_kg=62.0,                           # O5 separation adapter (ESTIMATE); PAS 1666 floor 40 kg
           stiffening_kg=221.0,                       # O5 launch-load stiffening (not stack-dependent per MASS_GAP_BREAKDOWN §1(a)); may partly overlap loop structure fraction
           growth_frac=1041.0 / (6337.0 - 1041.0 - 154.0 - 62.0))   # growth / CBE dry in O5 = 20.5 % (repo nominal policy; ASSUMED to carry)
def with_addbacks(o, growth=True, bumper=True, adapter=True, stiffening=False, growth_frac=None):
    L = dict(o["lines"]); add = {}
    if bumper: add["mmod_bumper"] = ADD["bumper_per_bothface_m2"] * 2.0 * o["A_rad"]
    if adapter: add["adapter"] = ADD["adapter_kg"]
    if stiffening: add["stiffening"] = ADD["stiffening_kg"]
    base = o["M_kg"] + sum(add.values())
    cbe = base - L["propulsion_adcs"] * 0 - 0.0
    if growth: add["margin"] = (growth_frac if growth_frac is not None else ADD["growth_frac"]) * (base - o["mass"]["propellant"] - add.get("adapter", 0.0))
    M = o["M_kg"] + sum(add.values()); return M, add
# ----------------------------------------------------------------------------------------------------------------- peak-vs-average consequence (task 2)
PCM_LATENT_KJ_KG = 250.0   # paraffin 155-253 kJ/kg (NASA NTRS 20160000793), n-octadecane 244; take 250 (STATEMENT range); melting point must match coolant range (ASSUMED feasible)
PCM_EFF = 0.5              # ASSUMED: PCM share of storage-pack mass (fins, enclosure, headers)
def peak_consequence(build, p, o, windows_min=(5, 15, 60)):
    """o: evaluation with rad_basis='avg'. What happens when the load goes to peak on the avg-sized radiator."""
    B = O.TARGET[build]; Pk = B["P"]; Pa = Pk * B["avg_over_peak"]
    fin, opt = p.get("rad_fin", "F1_L60_t0p8"), p.get("rad_opt", "e92F99"); A = o["A_rad"]; qa = o["q_abs"]
    if p.get("rad_model") == "replica_fin":
        T_at_peak = req_supply_K(Pk, A, fin, opt, qa); T_cap = p["T_cap_K"]; Prej_cap = 2 * A * (G_gross(fin, opt, T_cap) - qa) / 1000.0
    else:
        ee = 0.90; T_cap = p["T_rad_K"]; T_at_peak = ((Pk * 1000 / (2 * A) + qa) / (ee * SIG)) ** 0.25; Prej_cap = 2 * A * (ee * SIG * T_cap ** 4 - qa) / 1000.0
    out = dict(P_peak_kW=Pk, P_avg_kW=Pa, A_rad_m2=A, T_cap_K=T_cap, T_needed_at_peak_K=T_at_peak, dT_over_cap_K=T_at_peak - T_cap, P_reject_at_cap_kW=Prej_cap,
               throttle_fraction_to_stay_at_cap=Prej_cap / Pk, storage={})
    for w in windows_min:
        E_MJ = (Pk - Prej_cap) * w * 60.0 / 1000.0
        out["storage"][w] = dict(E_MJ=E_MJ, pcm_kg=E_MJ * 1000.0 / PCM_LATENT_KJ_KG / PCM_EFF)
    return out
