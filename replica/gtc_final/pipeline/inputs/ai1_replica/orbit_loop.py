"""AI1 replica feedback loop: orbit (altitude, LTAN) -> sunlit/eclipse -> battery or pause -> radiator environment -> drag/propellant -> radiation shield
-> mass/kW per t/sats per Starship -> check vs SpaceX 70/75 kW/t and FCC caps -> choose orbit -> recompute.  Greedy lever passes + META candidate check each iteration.
Labels: STATEMENT / ESTIMATE / INFERENCE / ASSUMED in every lever record.  Box only; GB10 untouched.  Logs are append-only (process_log/).
Run: eclipse/venv/bin/python orbit_loop.py   (needs repo src on path for env_leo; numpy only)"""
import sys, os, json, math, csv, time, copy, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "gb10_runner"))
sys.path.insert(0, "/tmp/gtcv2_root/inputs/repo/src"); sys.dont_write_bytecode = True
import numpy as np
from rack_two_skies import env_leo
import plog
EC = os.path.join(HERE, "eclipse")
SIG = 5.670374419e-8; MU = 398600.4418; RE = 6378.137; G0 = 9.80665
TARGET = {"Jun8": dict(P=150.0, kwt=70.0, A_rad=110.0, T0=None, avg_over_peak=0.80), "Aug4": dict(P=250.0, kwt=75.0, A_rad=250e3/1400.0, T0=None, avg_over_peak=0.70)}
P_IT_REF = 197.4   # kW, repo bus_model.json reference design for the line items below
# ---------------------------------------------------------------- tables
grid = {}
for r in csv.DictReader(open(f"{EC}/eclipse_grid.csv")):
    grid[(int(float(r["h_km"])), round(float(r["ltan_h"]), 2))] = {k: (float(v) if k not in ("season_start", "season_end", "cyl_season_start", "cyl_season_end") else v) for k, v in r.items()}
daily = json.load(open(f"{EC}/eclipse_daily.json"))
dens = {k: {int(h): v for h, v in d.items()} for k, d in json.load(open(f"{EC}/density_alt.json")).items()}
def beta_stats(h, ltan):
    z = daily[f"{h}_{ltan}"] if f"{h}_{ltan}" in daily else daily[f"{h}_{float(ltan)}"]
    bmin = min(x["beta_min_abs"] for x in z); cosb = float(np.mean([math.cos(math.radians(x["beta_mean"])) for x in z]))
    return bmin, cosb
_envc_path = f"{EC}/env_parts.json"; _envc = json.load(open(_envc_path)) if os.path.exists(_envc_path) else {}
def env_parts(h, beta):
    key = f"{h}_{round(beta)}"
    if key not in _envc:
        F, Ag = env_leo.orbit_average(float(round(beta)), float(h), n_orbit=36, n_theta=150, n_phi=150)
        g = env_leo.direct_sun_g(float(round(beta)), float(h))
        _envc[key] = dict(F=F, Ag=Ag, g=g); json.dump(_envc, open(_envc_path, "w"), indent=1)
    return _envc[key]
def q_abs(h, beta, alpha, eps_ir=0.90, f_g=0.0, M_IR=239.0, albedo=0.30, E=1368.0):
    p = env_parts(h, beta)
    return eps_ir * M_IR * p["F"] + alpha * albedo * E * p["Ag"] + f_g * alpha * E * p["g"]
# dose tables (repo toolchain AE8/AP8+SHIELDOSE-2 at 550; same script run here at other altitudes) -------------
DEPTH = np.array([0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 30, 50, 75, 100])
_rd = json.load(open("/tmp/gtcv2_root/inputs/repo/results/mass_claims/dose_total.json"))
NOM550 = np.array(_rd["design_5yr_rad_si"]["nominal"]); LOW550 = np.array(_rd["design_5yr_rad_si"]["low"]); HIGH550 = np.array(_rd["design_5yr_rad_si"]["high"])
def _tot(b, comps): return sum(np.maximum(np.array(b[c])[:, 2], 2 * np.array(b[c])[:, 0]) for c in comps)
def trapped_mid(j):
    hi = _tot(j["MIN"], ["dose_proton_untrapped"]) + _tot(j["MAX"], ["dose_electron", "dose_bremsstrahlung"])
    lo = _tot(j["MAX"], ["dose_proton_untrapped"]) + _tot(j["MIN"], ["dose_electron", "dose_bremsstrahlung"])
    return 5 * 0.5 * (lo + hi)
_dose_files = {400: "dose_400km_97.03deg.json", 500: "dose_500km_97.40deg.json", 550: None, 600: "dose_600km_97.79deg.json", 725: "dose_725km_98.28deg.json",
               800: "dose_800km_98.60deg.json", 1000: "dose_1000km_99.47deg.json", 1200: "dose_1200km_100.4deg.json"}
_t550 = trapped_mid(json.load(open("/tmp/gtcv2_root/inputs/repo/results/mass_claims/dose_depth_550km_97.6deg.json")))
_adder = NOM550 - _t550     # non-trapped part (SPE + GCR) at 550, reused at all altitudes (ESTIMATE: SPE cutoff differs little for polar orbits)
def dose5(h):
    f = _dose_files.get(h)
    t = _t550 if f is None else trapped_mid(json.load(open(f"{EC}/dose/{f}")))
    return np.minimum.accumulate(np.maximum(t + _adder, 1.0))
def depth_for(dose, limit):
    if dose[0] <= limit: return float(DEPTH[0])
    if dose[-1] > limit: return float(DEPTH[-1] * 1.5)       # beyond table: extrapolate crudely (flag)
    return float(np.interp(math.log(limit), -np.log(dose)[::-1] * -1, DEPTH[::-1])) if False else float(np.exp(np.interp(limit, dose[::-1], np.log(DEPTH)[::-1])))
# ---------------------------------------------------------------- lever register  (nominal = repo/public baseline; best_T1 = documented/flown or repo's own optimistic case; best_T2 = target or ASSUMED sweep)
def L(i, name, key, nom, worst, t1, t2, label, src, group="core", note=""):
    return dict(id=i, name=name, key=key, nominal=nom, worst=worst, best_T1=t1, best_T2=t2, label=label, source=src, group=group, note=note)
REG = [
 L("V1", "radiator mean surface temperature [K] (chip/coolant temp)", "T_rad_K", None, 318.15, None, 365.0, "ASSUMED sweep; nominal backsolved from SpaceX 1,400 W/m2 (ESTIMATE)",
   "SpaceX Jun 8 1,400 W/m2 (STATEMENT); Musk 370 K chip (repo, Jan 20 2026 STATEMENT); 318 K = 45 C coolant (ASSUMED)", note="nominal pinned so stated radiator area is reproduced"),
 L("V2a", "array specific power, wing level BOL [W/kg]", "wkg_wing", 100.0, 71.0, 120.0, 300.0, "STATEMENT (ROSA flown 100-120; Phenacite 71) / ESTIMATE target (ROSA-Max 300-500 not flown)",
   "https://www.satnow.com/products/solar-panels/redwire-space/102-1191-roll-out-solar-array-rosa- ; https://techport.nasa.gov/projects/9814"),
 L("V2b", "cell type", "cell", "3J", "Si", "3J", "3J", "STATEMENT (Si 28% lower BOL power; 17.4% best space Si; Starlink uses Si)",
   "https://phys.org/news/2026-09-silicon-solar-cells-satellite-power.html ; https://www.energy.gov/documents/2026-ieso-space-photovoltaics-workshop",
   note="INFERENCE: delivered 250 W/m2 needs ~26% cell eff at 0.9 pack, 0.92 PMAD, 0.85 EOL, i.e. 3J-class, not Si"),
 L("V3", "radiator coating solar absorptance alpha (aged)", "alpha", 0.20, 0.36, 0.12, 0.09, "STATEMENT (AZW/LA-II 0.09 BOL -> 0.119 after 4 yr MISSE; Z-93 0.15 -> 0.36 at 30 yr)",
   "https://www.aztechnology.com/uploadimage/AZW-LA-II.pdf ; https://ntrs.nasa.gov/citations/19920048673"),
 L("V3b", "direct-sun load factor f_g on radiator (dawn-dusk, beta<90)", "f_g", 0.0, 1.0, 0.0, 0.0, "ASSUMED (repo f_g=1 conservative; 0 = ideal knife edge)", "repo env_leo.direct_sun_g docstring"),
 L("V4", "design life [yr] (refresh vs EOL sizing)", "life", 5.0, 5.0, 3.0, 2.0, "ESTIMATE (repo 5 yr; Suncatcher 5-yr refresh logic; 2-3 yr refresh ASSUMED by the task)",
   "https://arxiv.org/html/2511.19468 ; configs/bus.yaml"),
 L("V4b", "array degradation per year", "arr_deg", 0.03, 0.03, 0.03, 0.0015, "ESTIMATE (repo 0.85 EOL over 5 yr = 3%/yr linear) / STATEMENT (Starcloud 0.15%/yr demonstrated for selected cells)",
   "Starcloud white paper (local source copy, line 111)"),
 L("V5", "radiation hardness: (tolerance rad(Si), inherent Al g/cm2, spare fraction)", "rad", (1000.0, 1.0, 0.02), (500.0, 0.5, 0.05), (7500.0, 2.0, 0.0), (7500.0, 2.0, 0.0),
   "ESTIMATE (repo triple; Suncatcher HBM irregularities from 2 krad(Si), TPU 15 krad no hard failure)", "https://arxiv.org/html/2511.19468 ; configs/mass_gaps.yaml radiation"),
 L("V6a", "solar activity for drag", "solar", "solar_mean", "solar_max", "solar_min", "solar_min", "ESTIMATE (MSIS F10.7 70/150/230 at LST 6/18)", "pymsis 0.13 (NRLMSIS2)"),
 L("V6b", "bus ram area [m2] (excl. radiator/array)", "ram_bus", 15.0, 100.0, 8.0, 8.0, "ESTIMATE (repo triple 8/15/100)", "configs/mass_gaps.yaml propulsion"),
 L("V6c", "thruster Isp [s]", "isp", 1650.0, 1650.0, 2500.0, 2500.0, "STATEMENT 2500 s (SpaceX Starlink V2 mini argon Hall thruster, flown 2023); 1650 = Safran PPS1350 repo nominal", "https://www.ispreview.co.uk/index.php/2023/02/spacex-set-to-launch-first-v2-mini-starlink-broadband-satellites.html ; https://www.satellitetoday.com/technology/2023/02/27/spacex-shares-details-of-higher-bandwidth-v2-mini-starlink-satellites/"),
 L("V7", "optical terminals per satellite", "n_term", 4, 6, 3, 3, "STATEMENT (Starlink V2 mini: 3 lasers; Tesat SCOT80 11.9 kg/80 W repo)", "https://starlink.com/technology ; https://www.satnow.com/products/laser-communication-terminals/tesat-spacecom-gmbh-co-kg/155-1423-scot80"),
 L("V8a", "primary structure fraction of dry bus", "f_struct", 0.20, 0.27, 0.20, 0.15, "ESTIMATE (SMAD 20/27%); 0.15 ASSUMED", "configs/bus.yaml / mass_gaps.yaml"),
 L("V8b", "deployment: (boom fraction of array, holddown points x kg)", "deploy", (0.05, 32, 3.0), (0.05, 64, 6.0), (0.05, 16, 1.0), (0.05, 16, 1.0), "ESTIMATE (repo mass_gaps mechanisms)", "configs/mass_gaps.yaml mechanisms"),
 L("V10", "load following: strategy", "strategy", "pause", "ride", "pause", "pause", "ASSUMED choice (DECISIONS #65 pause in eclipse)", "repo DECISIONS #65"),
 L("V10b", "battery specific energy [Wh/kg] (ride only)", "wh_kg", 150.0, 100.0, 150.0, 250.0, "ASSUMED (150 = repo reference)", "configs/bus.yaml (battery 0.12 kWh/kg usable)"),
 # meta-added candidates (start inactive; activated when swing >= 5 %)
 L("M1", "coolant pump mass scale (1 = ISS-based repo, 0.25 = repo light-pump case)", "pump", 1.0, 1.0, 0.25, 0.25, "ESTIMATE (repo bus_model pump_modules 1,061 kg at 197 kW; light case 25% of ISS)", "results/p6/bus_model.json", group="meta"),
 L("M2", "rack mass stripped fraction (ground frame etc.)", "f_strip", 0.0, 0.0, 340.0/1814.0, 0.30, "INFERENCE 340/1814 = ground frame (repo ESTIMATE) ; 0.30 ASSUMED", "configs/bus.yaml rack_frame_kg", group="meta"),
 L("M3", "PCDU+harness mass scale", "pmad", 1.0, 1.25, 1.0, 0.5, "ASSUMED sweep (repo 464+349 kg at 197 kW; no public Starlink value)", "results/p6/bus_model.json", group="meta"),
 L("M4", "radiator areal mass [kg/planform m2]", "sig_rad", 7.1, 11.0, 7.1, 2.6, "INFERENCE: 7.1 runner low bound; 11.0 = repo adopted design (2,265 kg / 205 m2 planform); 2.6 = fin sheet+tube+fluid only (no headers)", "gb10_runner/ai1_specs.py ; configs/mass_gaps.yaml base", group="meta"),
 L("M5", "ADCS (wheels) mass scale", "adcs", 1.0, 1.0, 0.5, 0.25, "ASSUMED sweep (repo 12 wheels 144 kg at 197 kW)", "results/p6/bus_model.json adcs", group="meta"),
]
NOM = {v["key"]: v["nominal"] for v in REG}
# ---------------------------------------------------------------- mass model
def v_circ(h): return math.sqrt(MU / (RE + h)) * 1000.0
def evaluate(build, p, h, ltan, retT=False):
    """Inner fixed point on propellant/drag; returns full output dict."""
    B = TARGET[build]; P = B["P"]; r = P / P_IT_REF
    ec = grid[(h, ltan)]; sun = ec["sunlit_frac_equiv"]; t_ecl = ec["max_shadow_min"]; T_orb = ec["T_orb_min"]
    bmin, cosb = beta_stats(h, ltan)
    life = p["life"]
    # --- array
    eol = 1.0 - p["arr_deg"] * life
    bol_cell = 319.7 * (0.72 if p["cell"] == "Si" else 1.0)
    A_arr = P * 1000.0 / (bol_cell * 0.92 * eol)
    sig_cell_3J = 319.7 / 480.0                                  # kg/m2, cell level from 455-505 W/kg (INFERENCE)
    sig_total_3J = 319.7 / p["wkg_wing"]
    sig_arr = sig_total_3J - (sig_cell_3J if p["cell"] == "Si" else 0.0) + (319.7 * 0.72 / 960.0 if p["cell"] == "Si" else 0.0) - (0.0)
    if p["cell"] == "Si": sig_arr = sig_total_3J - sig_cell_3J + (319.7 * 0.72 / 960.0) * 1.0    # swap cell layer mass (Si 920-1000 W/kg cell level, 0.72 BOL density)
    # --- battery / eclipse (load following)
    batt = 0.0; A_extra = 0.0; lost_hours_frac = 1.0 - sun
    if p["strategy"] in ("ride", "half"):
        Pr = P * (1.0 if p["strategy"] == "ride" else 0.5)
        E_kwh = Pr * (t_ecl / 60.0) / (0.8 * 0.9)                   # DoD 0.8, eta 0.9 (ASSUMED, as task)
        batt = E_kwh * 1000.0 / p["wh_kg"]
        P_ch = Pr * t_ecl / 0.9 / max(T_orb - t_ecl, 1.0)           # kW to recharge in the sunlit part of the orbit
        A_extra = P_ch * 1000.0 / (319.7 * 0.92 * eol)
        lost_hours_frac = (1.0 - sun) * (0.5 if p["strategy"] == "half" else 0.0)
    A_arr_tot = A_arr + A_extra
    m_arr = A_arr_tot * sig_arr
    m_deploy = p["deploy"][0] * m_arr + p["deploy"][1] * p["deploy"][2]
    # --- radiator (area from T)
    ee = 0.90
    qa = q_abs(h, bmin, p["alpha"], f_g=p["f_g"])
    T0 = B["T0"]
    if T0 is None:                                              # anchor: stated area reproduced at nominal params and the reference orbit
        qa0 = q_abs(550, beta_stats(550, 6.0)[0], NOM["alpha"], f_g=NOM["f_g"])
        q_face0 = P * 1000.0 / (2.0 * B["A_rad"]); T0 = ((q_face0 + qa0) / (ee * SIG)) ** 0.25; B["T0"] = T0
    T = p["T_rad_K"] if p["T_rad_K"] else T0
    q_net = ee * SIG * T ** 4 - qa
    A_rad = P * 1000.0 / (2.0 * q_net)
    m_rad = A_rad * p["sig_rad"]
    # --- rack, equipment (repo bus_model lines scaled by P/197.4)
    rack = 1814.0 * (1.0 - p["f_strip"])
    eq = dict(pumps=1061.4 * r * p["pump"], valves=8.0, piping=4.45 * r, coolant=207.9 * r, pcdu=463.9 * r * p["pmad"], harness=349.2 * r * p["pmad"],
              battery_safe=31.25, optical=11.9 * p["n_term"], rf_ttc=6.0, fc=1.2, st=7.8, sens=5.0, thr_ppu=21.6, adcs=144.0 * p["adcs"])
    equip = sum(eq.values())
    struct = p["f_struct"] / (1.0 - p["f_struct"]) * (rack + equip)
    # --- radiation
    d5 = dose5(h) * life / 5.0
    tol, inh, spare = p["rad"]
    depth = depth_for(d5, tol); add = max(0.0, depth / 10.0 * 2.70 - inh)
    area_rack = 2 * (0.6 * 1.2 + 1.2 * 2.296 + 0.6 * 2.296)
    shield = area_rack * add * 10.0; spares_kg = spare * rack
    # --- propulsion fixed point
    rho = dens[p["solar"]][h] if h in dens[p["solar"]] else float(np.exp(np.interp(h, sorted(dens[p["solar"]]), np.log([dens[p["solar"]][k] for k in sorted(dens[p["solar"]])]))))
    A_ram = A_rad + p["ram_bus"] + A_arr_tot * (2.0 / math.pi) * cosb
    v = v_circ(h)
    dv_raise = max(0.0, v_circ(350) - v) if h > 350 else 0.0
    dv_disp = abs(v_circ(200) - v)
    dry = rack * 1.0 + equip + struct + m_arr + m_deploy + m_rad + batt + shield + spares_kg
    prop = 0.0; resid = 0.0; n_it = 0
    for it in range(60):
        Mavg = dry + 0.5 * prop
        dv_drag = 0.5 * rho * v * v * 2.2 * A_ram / Mavg * life * 365.25 * 86400.0
        dv = dv_raise + dv_drag + dv_disp
        prop_new = dry * (math.exp(dv / (G0 * p["isp"])) - 1.0) * 1.10 * 1.10     # 10 % reserve, 10 % tank (repo nominal)
        n_it = it + 1; resid = abs(prop_new - prop) / max(dry + prop_new, 1.0)
        if resid < 1e-6: prop = prop_new; break
        prop = prop_new
    M = dry + prop
    thrust_days = M * dv / 0.18 / 86400.0
    avg_delivered = P * (1.0 - lost_hours_frac) if p["strategy"] != "pause" else P * sun
    # --- Starship
    out = dict(build=build, h=h, ltan=ltan, P_kW=P, M_kg=M, M_dry_kg=dry, kwt_wet=P / M * 1000.0, kwt_dry=P / dry * 1000.0, kwt_avg_wet=avg_delivered / M * 1000.0,
               target_kwt=B["kwt"], gap_ratio=B["kwt"] / (P / M * 1000.0), budget_kg=P / B["kwt"] * 1000.0,
               mass=dict(rack=rack, pumps_coolant=eq["pumps"] + eq["valves"] + eq["piping"] + eq["coolant"], pmad_harness=eq["pcdu"] + eq["harness"], adcs=eq["adcs"],
                         comms_misc=eq["optical"] + eq["rf_ttc"] + eq["fc"] + eq["st"] + eq["sens"] + eq["thr_ppu"] + eq["battery_safe"], structure=struct, array=m_arr, deploy=m_deploy,
                         radiator=m_rad, battery_eclipse=batt, shield=shield, spares=spares_kg, propellant=prop),
               A_arr=A_arr_tot, A_arr_extra=A_extra, A_rad=A_rad, T_rad_K=T, q_abs=qa, q_net=q_net, sunlit=sun, t_ecl_max_min=t_ecl, season_days=ec["season_days"],
               beta_min=bmin, dv=dict(raise_=dv_raise, drag=dv_drag, disp=dv_disp), A_ram=A_ram, rho=rho, shield_depth_mm=depth, dose5_at_10mm=float(np.interp(10, DEPTH, d5)),
               thrust_days=thrust_days, prop_iters=n_it, prop_resid=resid, lost_hours_frac=lost_hours_frac, avg_over_peak=avg_delivered / P)
    # Starship: payload 100 t (STATEMENT 100+ t), bay 614 m3 x 0.35 packing (ASSUMED), stowed density 800 kg/m3 (ASSUMED)
    out["N_mass_100t"] = int(100000.0 // M); out["N_mass_114t"] = int(114000.0 // M)
    out["N_vol"] = int(614.0 * 0.35 // (M / 800.0)); out["N_sat"] = min(out["N_mass_100t"], out["N_vol"])
    out["limit"] = "mass" if out["N_mass_100t"] <= out["N_vol"] else "volume"
    out["fcc"] = dict(mass_ok=M <= 4000.0, rad_ok=A_rad <= 200.0, arr_ok=A_arr_tot <= 1500.0)
    out["fcc_flags"] = [k for k, ok in out["fcc"].items() if not ok]
    return out
# ---------------------------------------------------------------- loop machinery
ORBITS = [(h, l) for h in (400, 500, 550, 600, 725, 800, 1000, 1200) for l in (6.0, 6.5, 7.0)]
def best_orbit(build, p, allowed=None):
    best = None
    for (h, l) in (allowed or ORBITS):
        o = evaluate(build, p, h, l)
        if best is None or o["kwt_wet"] > best["kwt_wet"]: best = o
    return best
def level(v, lvl): return v[lvl] if lvl in v else v["nominal"]
def apply(p, key, val): q = dict(p); q[key] = val; return q
def tornado(build, p, h, ltan, active):
    base = evaluate(build, p, h, ltan)["kwt_wet"]; out = {}
    for v in REG:
        if v["id"] not in active: continue
        k = v["key"]; lo = v["worst"]; hi = v["best_T2"]
        e = dict(base=base)
        for nm, val in (("worst", lo), ("best_T2", hi), ("best_T1", v["best_T1"])):
            val = val if val is not None else p[k]
            if k == "T_rad_K" and val is None: val = None
            e[nm] = evaluate(build, apply(p, k, val), h, ltan)["kwt_wet"] - base
        out[v["id"]] = e
    return out
def seed_params():
    p = dict(NOM); p["T_rad_K"] = None; return p
