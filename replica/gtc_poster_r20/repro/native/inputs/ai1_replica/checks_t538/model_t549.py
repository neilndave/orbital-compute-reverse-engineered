"""t549 (copy of model_t548 + cref_frac, hbm_off_K; defaults reproduce t548)
t548 (copy of model_t547 + fin_area_rel / fin_mass_rel knobs for the Al-only vs K13D-on-Al trade; defaults 1.0 reproduce t547)
t547 CANDIDATE-ONLY copy of model_t538.py (t538 file untouched). Changes (t547): (1) array AREA follows electrical power only (eratio), array MASS = power/wing_scale -> wing_scale (W/kg) no longer shrinks area; (2) radiator heat = IT + heat pump + coolant pump electric + PMAD/harness loss (pmad_eff 0.92, the repo array-sizing convention) + q_other_kW, iterated with the area-dependent pump power; (3) explicit HBM constraint: coolant reference temperature <= min(T_chip - q R, T_hbm_max - dT_hbm); (4) thermal names: T_cref = coolant temperature the plate resistance is referenced to (loop mean by model convention), T_supply = cold side = radiator outlet = rack inlet, radiator inlet = supply + dT_loop.
t538 docstring: t538 direct design model (box CPU, numpy/scipy; no GPU).  Composes the existing, already-reviewed pieces into one function of design knobs:
  * thermal chain (t536/t468): chip limit -> plate coolant -> supply -> radiator area, with the c52/c8 radiator model (treq) inverted for area;
  * mass lines anchored to the LIVE point files (gtc_params/point_{J8,A4}_C1.json: t494 M55J frame, K13D fin, 62 kg adapter deleted, PCDU 5.57, spare GPU/pumps, 1970 field, 300 V);
  * radiator / coolant (c13 Warp-ladder model) / MMOD bumper (c21 repo Whipple) / propellant (c13.prop) responses to area;
  * consumed accounting (t456): total mass held at the target, reserve = margin / (core + bumper - propellant) (c42);
  * stowed-volume sat count from the repo packer results (c15, c60 tables).
Everything is an ESTIMATE of the replica; each knob label/source is in schema_t538.json.  Reads live data every time (nothing hard-coded)."""
import sys, os, json, math, glob
import numpy as np
from scipy.optimize import brentq
from scipy.interpolate import RegularGridInterpolator
HERE = os.path.dirname(os.path.abspath(__file__)); R0 = os.environ.get("AI1_ROOT", os.path.dirname(HERE))
sys.dont_write_bytecode = True
sys.path.insert(0, R0 + "/gb10_gtc/thermal"); sys.path.insert(0, R0 + "/checks_t454"); sys.path.insert(0, R0)
_argv = sys.argv; sys.argv = sys.argv[:1]
import ai1_specs as S
import coolant_t423d as CT
import orbit_loop as O
import c13_trade as C13
sys.argv = _argv
SIG = S.SIG
SCHEMA = json.load(open(HERE + "/schema_t549.json"))
DEFAULTS = {v["name"]: v["default"] for v in SCHEMA["inputs"]}
PROP0 = {"J8": 40.84, "A4": 63.67}                                  # c42_live_baseline.PROP (propellant inside propulsion_adcs)
_e = json.load(open(R0 + "/gb10_gtc/thermal/data/env_table.json"))
def _load(name):
    t = json.load(open(f"{R0}/gb10_run_t410/results/table_{name}.json")); eta = np.array(t["eta"]).reshape(t["ntb"], t["nee"], t["nts"])
    tb = t["tb0"] + t["dtb"] * np.arange(t["ntb"]); ea = t["ee0"] + t["dee"] * np.arange(t["nee"]); ta = t["ts0"] + t["dts"] * np.arange(t["nts"])
    g = RegularGridInterpolator((tb, ea, ta), eta, bounds_error=False, fill_value=None)
    return lambda Tb, e_, Ts_: float(g([[min(max(Tb, tb[0]), tb[-1]), min(max(e_, ea[0]), ea[-1]), min(max(Ts_, ta[0]), ta[-1])]])[0])
TABS = {n: _load(n) for n in ("F1_L60_t0p8", "F3_L40_t0p5")}
VF = json.load(open(R0 + "/checks_t444/c8_viewfactor.json"))
K13D_AREA_FACTOR = 0.9913                                           # t479: K13D 30x0.20 vs Al F3 (INFERENCE, same eta_cell basis)
BLK = 0.0092; U_SEASON = 0.25
def env(eps0, alpha, qscale, u=U_SEASON):
    dec = math.radians(23.44) * math.sin(2 * math.pi * u); inc = math.radians(97.57)
    beta = abs(math.degrees(math.asin(math.sin(dec) * math.cos(inc) + math.cos(dec) * math.sin(inc))))
    doy = 79.0 + u * 365.25; Sun = 1367.0 * (1 + 0.0334 * math.cos(2 * math.pi * (doy - 3.0) / 365.25))
    Fb = np.interp(beta, _e["beta"], _e["F_earth"]); Ab = np.interp(beta, _e["beta"], _e["albedo_geom"])
    return qscale * (eps0 * 239.0 * Fb + alpha * 0.30 * Sun * Ab), beta
def gs_of(T, ee, Ts, dT0, tab):
    gs = 0.0
    for m, w in ((0, 1.0), (1, 4.0), (2, 1.0)):
        Tm = T + dT0 * 0.5 * m; gs += w * 2 * ee * SIG * (Tm**4 - Ts**4) * tab(Tm, ee, Ts)
    return gs
def _ee_Ts(eps0, F0, alpha, qscale):
    q, beta = env(eps0, alpha, qscale); ee = eps0 * F0 * (1 - min(0.15, BLK * math.exp(-0.045))); Ts = (q / (ee * SIG)) ** 0.25
    return ee, Ts, beta
def area_for_supply(Pw, Tsup, eps0, F0, alpha, qscale, dT0, table):
    """radiator face area (m2) that rejects Pw watts with coolant supply Tsup (c52 treq balance A*gs/6 = P, solved for A)"""
    ee, Ts, _ = _ee_Ts(eps0, F0, alpha, qscale); gs = gs_of(Tsup, ee, Ts, dT0, TABS[table])
    return 6.0 * Pw / gs if gs > 0 else float("inf")
def supply_for_area(Pw, A, eps0, F0, alpha, qscale, dT0, table):
    ee, Ts, _ = _ee_Ts(eps0, F0, alpha, qscale)
    return brentq(lambda T: A * gs_of(T, ee, Ts, dT0, TABS[table]) / 6.0 - Pw, 250.0, 450.0, xtol=1e-9)
# ---- bumper (c21 repo Whipple, exact exp(-N) form; N is linear in panel count) ----
_src = open(R0 + "/checks_t454/c21_bumper.py").read().split("res = {}")[0]; _ns = {"__name__": "c21_import"}; _cwd = os.getcwd(); os.chdir(R0 + "/checks_t454"); exec(_src, _ns); os.chdir(_cwd)
_Sg = np.arange(20.0, 301.0, 1.0)
_N1 = np.array([_ns["flux_N"](lambda rp, V, s=s: _ns["d_lim_whipple_cm"](0.157, s / 10, rp, V), 1, s)[0] for s in _Sg])
_STRIP = np.array([_ns["strip"](s) for s in _Sg]); _LM, _NT = _ns["LM"], _ns["NT"]
def bumper_kg(npan, Pt):
    """Whipple 0.5 mm bumper sized to P(no puncture, 5 yr) >= Pt: smallest standoff S (continuous), mass = strip area x 0.5 mm Al.  inf if S>300 mm."""
    need = -math.log(Pt) / npan
    if need < _N1[-1]: return 1e5, 301.0   # no standoff <= 300 mm reaches Pt: flagged infeasible (huge mass, keeps arrays finite)
    if need >= _N1[0]: return npan * _NT * _LM * 2 * _STRIP[0] * 0.5e-3 * 2700.0, 20.0
    i = int(np.searchsorted(-_N1, -need)); f = (_N1[i - 1] - need) / (_N1[i - 1] - _N1[i]); Sx = _Sg[i - 1] + f * (_Sg[i] - _Sg[i - 1]); st = _STRIP[i - 1] + f * (_STRIP[i] - _STRIP[i - 1])
    return npan * _NT * _LM * 2 * st * 0.5e-3 * 2700.0, Sx
# ---- coolant (c13 model, with loop rise as a variable) ----
def cool2(P, A_rad, npan, ncol, dT, ps, pump_unit=2.0, valve=0.5, eta=0.20, head_extra_kPa=10.0, dp_col_kPa=40.4):
    G0 = dict(CT.G); CT.G["man_dp"] = 0.0; CT.G["panel_dp0"] = 0.0
    try: c = CT.cool(P, A_rad, dT=dT, panel_fluid=False, run_scale=0.5, pump=0.10, spares=2)
    finally: CT.G.clear(); CT.G.update(G0)
    c = dict(c); c["fluid_total"] = c["fluid_rack"] + c["fluid_trunk"]; ctot = c["pumps"] + c["valves"] + c["piping"] + c["fluid_total"]
    Vd = c["diag"]["Vdot_L_s"] * 1e-3; Qc = Vd / npan * (npan / ncol); head = (dp_col_kPa + head_extra_kPa) * 1e3
    Phyd = Qc * head; mod = max(pump_unit, 0.0586 * Phyd) + valve
    col = (ncol + ps) * mod + C13.FLP * npan + C13.WLP * npan + 0.02 * npan + C13.PANEL_FLUID * npan
    return ctot + col, c["diag"]["P_hyd_W"] / 0.5 + ncol * Phyd / eta, mod
# ---- volume table ----
def _pack_table():
    T = {}
    for f in glob.glob(R0 + "/checks_t454/c15_pack_*.json") + glob.glob(HERE + "/pack_*.json"):
        d = json.load(open(f)); m = "J8" if d["id"].startswith("J8") else "A4"; rp = round(d["S"]["rpitch"] * 1e3, 3)
        if "t479" in f: continue
        T.setdefault((m, rp), {}); n = d["res"]["layers"]["n"]; T[(m, rp)][d["npan"]] = max(n, T[(m, rp)].get(d["npan"], 0))
    return {k: sorted(v.items()) for k, v in T.items()}
PACK = _pack_table()
def n_vol(m, npan, rpitch_mm):
    """sats per Starship allowed by stowed volume: piecewise-linear in panel count through the packer points (upper envelope), floor; uses the smallest tabulated pitch >= rpitch (conservative); clamps outside the table (flag)."""
    ks = sorted(k[1] for k in PACK if k[0] == m and k[1] >= rpitch_mm - 1e-9); ks = ks or [max(k[1] for k in PACK if k[0] == m)]
    pts = PACK[(m, ks[0])]; x = [p[0] for p in pts]; y = [p[1] for p in pts]
    # upper envelope from the right: if a bigger radiator packs n sats, a smaller one can too (with a re-tuned stack count; the default stack count n=round(npan/9.54) is not optimal at every size).  Optimistic by the stack-count noise -> finalists are re-packed with a stack-count scan.
    for i in range(len(y) - 2, -1, -1): y[i] = max(y[i], y[i + 1])
    return math.floor(np.interp(npan, x, y) + 1e-9), (npan > x[-1])
class Month:
    def __init__(self, tag):
        self.tag = tag; pf = f"{R0}/gtc_params/point_{tag}_C1.json"; d = json.load(open(pf)); self.pt = d; self.L0 = dict(d["mass_lines_kg"])
        self.P = d["result"]["P_IT_peak_kW"]; self.Mt = d["result"]["mass_kg"]; self.Nt = d["targets"]["sats_per_starship_98t"]; self.kWt_floor = d["targets"]["kWt"]
        self.A0 = d["areas"]["A_rad_face_m2"]; self.npan0 = d["geometry_derived"]["radiator"]["n_panels"]; self.plan = self.A0 / self.npan0
        self.Aarr0 = d["areas"]["A_arr_m2"]; self.frame0 = d["t494_frame"]["frame_kg"]; self.fcc = d["areas"]["FCC"]
        self.vfk = f"{'Jun' if tag == 'J8' else 'Aug'}/S0_render_yoke4.137_W14"; r = VF[self.vfk]
        self.Fe = 1 - r["f_array_exact_mean"] - (r["f_bus_mean"] if "f_bus_mean" in r else r["f_bus_mc_mean"])
        self.ncol0 = max(1, round(self.npan0 / 10)); self.dT0 = 20.0
        self.cool0, self.pel0, self.mod0 = cool2(self.P, self.A0, self.npan0, self.ncol0, 20.0, 2)
        self.bump_f0 = bumper_kg(self.npan0, 0.90)[0]; self.beta_stat = O.beta_stats(600, 6.0)[1]
        self.core0 = sum(v for k, v in self.L0.items() if k not in ("margin", "adapter", "mmod_bumper"))
        self.Aram0 = self.A0 + 15 + self.Aarr0 * 2 / math.pi * self.beta_stat; self.prop_f0 = C13.prop(self.core0, self.Aram0)
        t = json.load(open(R0 + "/checks_t454/t523_results.json")); k = "J8" if tag == "J8" else "A4"
        s = t["sens"][k]; kk = [x for x in s if x.startswith("k=0 spare")][0]; k2 = [x for x in s if x.startswith("k=2 spare")][0]
        self.avail = {0: s[kk]["avail"], 1: t["after"][k]["avail"], 2: s[k2]["avail"]}
        self.spare1 = self.L0["spare_compute"]; self.pcdu0 = d["knobs"]["pcdu"]; assert d["knobs"]["spare_gpus_per_sat"] == 1
    def ev(self, kn=None, A_override=None, **kw):
        k = dict(DEFAULTS); k.update(kn or {}); k.update(kw)
        if k["frame_kg"] is None: k["frame_kg"] = self.frame0
        P0 = self.P; P = P0 * k["derate"]; L0 = self.L0
        Tlim = k["T_chip_K"] + k["hbm_offset_K"]; dT_chip = k["q_plate_kW"] * 1000.0 * k["derate"] * k["R_plate_KW"]
        dT_hbm = (dT_chip if k["hbm_dT_K"] < 0 else k["hbm_dT_K"]) + k["hbm_off_K"]   # t549: HBM runs hbm_off_K above the die-equivalent rise (ASSUMED bracket 0..+8 K)
        Tc_chip = Tlim - dT_chip; Tc_hbm = k["T_hbm_max_K"] - dT_hbm; Tplate = min(Tc_chip, Tc_hbm); binding = "chip" if Tc_chip <= Tc_hbm else "HBM"
        Tsup = Tplate - k["dT_loop_K"] * k["cref_frac"]   # t549: R reference point in the plate coolant rise: 0 inlet, 0.5 mean (t547), 1.0 outlet (conservative)
        fin = int(round(k["fin"])); tab = "F3_L40_t0p5" if fin else "F1_L60_t0p8"; af = K13D_AREA_FACTOR if fin else 1.0
        af = af * k["fin_area_rel"]   # t548: fin option area factor vs the live K13D 30/0.20 fin at equal duty (Warp fin_t548, ESTIMATE)
        F0 = self.Fe * k["yoke_Feff_scale"] * (k["coat_F0"] / 0.99); W = 0.0; lift = k["hp_lift_K"]
        if lift > 1e-9:
            cop = k["hp_eta"] * Tplate / lift; W = P / cop
        Trad = Tsup + lift - k["mc_offset_K"]; pel_it = self.pel0
        for _it in range(6):
            P_el = P + W + pel_it / 1e3 + k["q_other_kW"]; pmad_loss = P_el * (1.0 / k["pmad_eff"] - 1.0) * k["pmad_heat_to_rad"]
            Qrej = P + W + pel_it / 1e3 + k["q_other_kW"] + pmad_loss
            if A_override is None: A = area_for_supply(Qrej * 1e3, Trad, k["eps0"], F0, k["alpha_eol"], k["qscale"], k["dT_loop_K"], tab) * af
            else: A = A_override
            pel_new = cool2(P if k["derate"] < 1 else P0, A, A / self.plan, max(1, round(A / self.plan / 10)), k["dT_loop_K"], k["pump_spares"])[1]
            if abs(pel_new - pel_it) < 0.5: pel_it = pel_new; break
            pel_it = pel_new
        npan_c = A / self.plan; npan = math.ceil(npan_c - 1e-9)
        Tsup_ach = supply_for_area(Qrej * 1e3, A / af, k["eps0"], F0, k["alpha_eol"], k["qscale"], k["dT_loop_K"], tab) - 0 + k["mc_offset_K"]   # supply the area actually delivers (deterministic + MC offset)
        Tchip_ach = Tsup_ach - lift + k["dT_loop_K"] * k["cref_frac"] + k["q_plate_kW"] * 1000.0 * k["derate"] * k["R_plate_KW"]
        ncol = max(1, round(npan_c / 10))
        c_tot, pel, mod = cool2(P if k["derate"] < 1 else P0, A, npan_c, ncol, k["dT_loop_K"], k["pump_spares"])
        bk, Sx = bumper_kg(npan_c, k["P_mmod"])
        dPel = pel - self.pel0; Pe_extra = (k["derate"] - 1) * P0 + dPel / 1e3 + W + k["extra_power_kW"] + k["q_other_kW"]
        eratio = (P0 + Pe_extra) / P0
        Ln = dict(L0)
        Ln["radiator"] = L0["radiator"] * npan_c / self.npan0 * k["fin_mass_rel"]   # t548: kg per m2 planform vs live K13D panel (fin_t548 areal ratio incl. bond, ESTIMATE)
        Ln["coolant_loop"] = L0["coolant_loop"] * c_tot / self.cool0
        Sx0 = bumper_kg(self.npan0, 0.90)[1]
        Ln["mmod_bumper"] = L0["mmod_bumper"] + (bk - self.bump_f0) + k["standoff_kg_per_mm_panel"] * (Sx * npan_c - Sx0 * self.npan0) + k["standoff_hw_kg_per_panel"] * npan_c
        Ln["array"] = L0["array"] * eratio / k["wing_scale"]
        Ln["power_electronics"] = L0["power_electronics"] * eratio * (self.pcdu0 / k["pcdu_kWkg"])
        Ln["harness"] = L0["harness"] * eratio * (300.0 / k["bus_V"]) ** 2
        Ln["structure_mech"] = (L0["structure_mech"] - self.frame0 + k["frame_kg"]) * k["struct_scale"]
        Ln["adapter"] = k["adapter_kg"]; Ln["spare_compute"] = self.spare1 * k["spare_gpus"]
        Ln["heat_pump"] = k["hp_kg_per_kW_el"] * W; Ln["extra"] = k["extra_mass_kg"]
        # t547: array area follows electrical power only (not wing_scale)
        Aarr = self.Aarr0 * eratio; Aram = A + 15 + Aarr * 2 / math.pi * self.beta_stat
        pr = PROP0[self.tag]
        for _ in range(3):
            core = sum(v for kk, v in Ln.items() if kk not in ("margin", "adapter", "mmod_bumper", "propulsion_adcs")) + L0["propulsion_adcs"] - PROP0[self.tag] + pr
            pr = PROP0[self.tag] + C13.prop(core, Aram) - self.prop_f0 if _ > 0 else PROP0[self.tag] + C13.prop(core, Aram) - self.prop_f0
        Ln["propulsion_adcs"] = L0["propulsion_adcs"] - PROP0[self.tag] + pr
        core = sum(v for kk, v in Ln.items() if kk not in ("margin", "adapter", "mmod_bumper")); den = core + Ln["mmod_bumper"] - pr
        other = sum(v for kk, v in Ln.items() if kk != "margin"); f = k["reserve_floor"]
        margin_Mt = self.Mt - other; res_pct = margin_Mt / den
        M_req = other + f * den
        rack_max = (self.Mt - (other - Ln["rack"]) - f * (den - Ln["rack"])) / (1 + f)
        kWt = P / M_req * 1e3; N98 = int(98000.0 // M_req); nv, extrap = n_vol(self.tag, npan, k["rpitch_mm"]); sats = min(N98, nv)
        fcc = [] 
        if A > self.fcc["A_rad_m2"]: fcc.append("A_rad")
        if M_req > self.fcc["mass_kg"]: fcc.append("mass")
        if Aarr > self.fcc["A_arr_m2"]: fcc.append("A_arr")
        deliv_per_launch = sats * P / 1e3; target_launch = self.Nt * P0 / 1e3
        meets = (sats * k["derate"] >= self.Nt - 1e-9) and (kWt >= self.kWt_floor - 1e-9) and not fcc and Sx <= 300.0 and (M_req <= self.Mt + 1e-6 or N98 * k["derate"] >= self.Nt)
        Ea = 0.7; kB = 8.62e-5
        return dict(k_rack_solved=rack_max / P0, M_req_kg=M_req, kWt=kWt, N98=N98, n_vol=nv, n_vol_extrap=extrap, sats=sats, reserve_pct_at_Mt=100 * res_pct, margin_Mt_kg=margin_Mt, A_rad_m2=A, A_arr_m2=Aarr, npan_c=npan_c, npan=npan, T_supply_K=Tsup, T_supply_ach_K=Tsup_ach,
                    T_plate_mean_K=Tplate, T_cref_K=Tplate, T_rad_inlet_K=Tsup + k["dT_loop_K"], binding=binding, Tc_chip_K=Tc_chip, Tc_hbm_K=Tc_hbm, T_hbm_ach_K=Tchip_ach - dT_chip + dT_hbm, pmad_loss_kW=pmad_loss, q_other_kW=k["q_other_kW"], T_chip_limit_K=Tlim, T_chip_ach_K=Tchip_ach, rad_kg=Ln["radiator"], coolant_kg=Ln["coolant_loop"], bumper_kg=Ln["mmod_bumper"], standoff_mm=Sx, array_kg=Ln["array"], pcdu_kg=Ln["power_electronics"],
                    prop_kg=pr, den_kg=den, other_kg=other, W_hp_kW=W, Q_rej_kW=Qrej, pump_el_W=pel, derate=k["derate"], compute_per_launch_MW=deliv_per_launch, target_compute_per_launch_MW=target_launch, fcc=fcc, meets=bool(meets),
                    AF_vs_95C=math.exp(Ea / kB * (1 / 368.15 - 1 / Tlim)), avail_inf=float(np.interp(k["spare_gpus"], [0, 1, 2], [self.avail[0], self.avail[1], self.avail[2]])), lines={kk: round(v, 3) for kk, v in Ln.items()}, margin_floor_kg=f * den)
def check_baseline(verbose=True):
    """t547: run with the t547 additions neutralised (pmad_heat_to_rad 0, HBM limit high) -> must reproduce live."""
    """verify the model reproduces the live point files and the c52/c42 numbers when the area is the live area and the baseline knobs are used."""
    out = {}
    for tag in ("J8", "A4"):
        m = Month(tag); r = m.ev(A_override=m.A0, standoff_hw_kg_per_panel=0.0, pmad_heat_to_rad=0.0, T_hbm_max_K=1e4, wing_scale=1.0); L0 = m.L0
        for kk in ("radiator", "coolant_loop", "mmod_bumper", "array", "power_electronics", "harness", "structure_mech", "propulsion_adcs", "spare_compute"):
            assert abs(r["lines"][kk] - L0[kk]) < 0.02, (tag, kk, r["lines"][kk], L0[kk])
        live = json.load(open(R0 + f"/gtc_params/point_{tag}_C1.json")); L = live["mass_lines_kg"]; core = sum(v for k_, v in L.items() if k_ not in ("margin", "adapter", "mmod_bumper")); den = core + L["mmod_bumper"] - PROP0[tag]
        assert abs(r["reserve_pct_at_Mt"] - 100 * L["margin"] / den) < 0.02, (tag, r["reserve_pct_at_Mt"], 100 * L["margin"] / den)
        T0 = supply_for_area(m.P * 1e3, m.A0, 0.92, m.Fe, 0.2, 1.0, 20.0, "F1_L60_t0p8")
        assert abs(T0 - {"J8": 377.38, "A4": 378.55}[tag]) < 0.01, (tag, T0)
        out[tag] = dict(T_supply_peak_K=T0, reserve_pct=r["reserve_pct_at_Mt"], n_vol=r["n_vol"], npan=r["npan"], prop_model_kg=r["prop_kg"])
    if verbose: print("baseline reproduction OK:", json.dumps(out))
    return out
if __name__ == "__main__":
    check_baseline()
