"""SPIN1 freeze/restart port of t596 nbf_t596.py (source copy: ../nbf_t596_source_copy.py, sha256 2e0c193a...) onto the GTC scoped baseline.
Changes vs nbf_t596 (all deliberate, listed so the port is auditable):
 * scenario built from GTC_SCOPED_BASELINE_EXACT.json (77/128 panels, nominal 120/175 kW, baseline effective emissivity, nominal flow at 20 K rack rise),
   NOT from eclipse5_t590.scen (NB2F candidate);
 * radiation on the fin-resolved nodes uses 2*ee*sigma*(T^4-Ts^4) with NO fin-efficiency table factor (fins are resolved; the table would double-count; more emission = conservative for freezing);
 * fluid selectable: water (baseline proxy; liquidus 273.15 K, 0.5 K mushy band, latent 334 kJ/kg) or MPG40 (Dow DOWFROST wt% liquidus, as t596);
 * gas/EPDM insert on for MPG40 (t596 NB2F2 cord), off for water;
 * header: inherited c13 round tapered header (fluid kg/panel = C13.FLP x rho ratio), length per panel and radiating width are inputs; the header is lumped as in t596;
 * fin heat capacity matched to the baseline wet radiator ledger (122.28/203.77 kg) minus tube walls and panel fluid; fin conduction Al 6061 (v2: 0.225 mm, 6 tubes/panel from scenario NT/tf_m; spin1: 0.5 mm, 4 tubes);
 * rack nodes: Chw = 0.5 x rack kg x mixed cp (t596 convention), Cfl = central rack+trunk fluid (headers are in the panel model).
Everything else (heater logic, open criterion liquidus+2 K, bypass restart, IT throttle, bus loss, energy closure) follows nbf_t596."""
import os, sys, json, math, numpy as np
SIG = 5.670374419e-8; KAL = 167.0; RAL = 2700.0; CAL = 900.0; KICE = 2.2; LAT = 334e3
FLUIDS = {
 "MPG40": dict(cp=3650.0, rho=1040.0, k=0.38, mu=0.0035, wt=[40, 45, 50, 55, 60.0, 65.0], Tl=[-21.1, -26.7, -33.5, -41.6, -51.1, -61.0], insert=True),
 "water": dict(cp=4190.0, rho=1000.0, k=0.58, mu=0.0015, insert=False)}
def make_fluid(name):
    F = FLUIDS[name]
    if name == "MPG40":
        wt = np.array(F["wt"]); Tl = np.array(F["Tl"]) + 273.15; TLIQ = float(Tl[0])
        def xice(T):
            T = np.asarray(T, float); w = np.interp(-T, -Tl, wt); return np.where(T >= TLIQ, 0.0, np.clip(1 - 40.0 / w, 0.0, 1.0))
    else:
        TLIQ = 273.15
        def xice(T):
            T = np.asarray(T, float); return np.clip((TLIQ - T) / 0.5, 0.0, 1.0)
    Tg = np.linspace(150.0, 420.0, 5401); Hg = F["cp"] * (Tg - TLIQ) - LAT * xice(Tg)
    return F, TLIQ, xice, (lambda H: np.interp(H, Hg, Tg)), (lambda T: np.interp(T, Tg, Hg))
def run(S, fluid="MPG40", ecl_min=21.66, q_t=40.0, q_h=0.0, QLOSS=500.0, NL=6, NF=6, DT=0.1, pre_s=3600.0, post_s=3600.0, HL=5.602, hdr_w=0.016):
    F, TLIQ, xice, T_of_H, H_of_T = make_fluid(fluid); CPL, RHO, KL = F["cp"], F["rho"], F["k"]
    DT = S.get("DT", DT)   # v2 t619: 0.225 mm / 6-tube fin nodes need a smaller explicit step (stability Cf/(Gf+G0) ~ 0.08 s)
    NT = S.get("NT", 4); L = 2.9446; B = 2.954e-3; AO = 6.094e-3; PHI_C = 0.057 if F["insert"] else 0.0; DC = 0.8e-3
    A_bore = B * B; A_f = A_bore * (1 - PHI_C); P_w = 4 * B; Dh = 4 * A_f / (P_w + (math.pi * DC if PHI_C > 0 else 0.0))
    C_cord = A_bore * PHI_C * 0.3 * 1200 * 1500
    A_alt = AO * AO - B * B; C_wall = A_alt * RAL * CAL + C_cord
    npan = S["npan"]; W = S["plan"] / L
    hw = W / NT / 2 - AO / 2; dx = hw / NF; tf_k = S.get("tf_m", 0.5e-3)   # v2 t619: 6 tubes/panel, Al 0.225 mm fin
    Cf = S["fin_cap_J_per_m2K"] * dx; Gf = KAL * tf_k / dx; G0 = KAL * tf_k / (dx / 2 + AO / 4)
    dz = L / NL; Mseg = A_f * RHO * dz
    Mh_tot = S["hdr_fluid_kg_per_panel"] * (1 - PHI_C); Mh = Mh_tot / 2; Chw_h = S["hdr_wall_kg_per_panel"] * CAL / 2
    md0 = S["mdot"]; Tsup0, Tret0 = S["Tsup"], S["Tret"]; Qavg = S["Qavg"]; Pavg = S["Pavg"]; ee = S["ee"]
    gE = lambda T: 2 * ee * SIG * (np.asarray(T) ** 4 - S["Ts_ecl"] ** 4); gS = lambda T: 2 * ee * SIG * (np.asarray(T) ** 4 - S["Ts_sun"] ** 4)
    Tw = np.linspace(Tret0, Tsup0, NL); Hf = H_of_T(Tw); Tfin = np.repeat(Tw[:, None], NF, 1); Hh = H_of_T(np.array([Tret0, Tsup0])); Twh = np.array([Tret0, Tsup0])
    Thw = Tret0 + 2.0; Tr = Tret0; f = 1.0; t_ = -pre_s; ECL = ecl_min * 60.0; TRACK = 275.15
    R = dict(T_rad_min=1e9, T_fin_min=1e9, ice_max_tube=0.0, ice_max_header=0.0, t_open_min=None, Thw_min=1e9, E_heater_J=0.0, E_lost_J=0.0, E_rad_J=0.0, E_loss_J=0.0, E_it_J=0.0, supply_min_after_open=1e9)
    opened = False; Ein = Eout = 0.0; E0 = None
    def stored():
        tube = NT * npan * (np.sum(Hf * Mseg) + np.sum(C_wall * dz * Tw) + 2 * np.sum(Cf * dz * Tfin))
        head = npan * (np.sum(Hh * Mh) + np.sum(Chw_h * Twh)); return tube + head + S["Chw"] * Thw + S["Cfl"] * Tr
    while t_ < ECL + post_s:
        ecl = 0.0 <= t_ < ECL; pre = t_ < 0.0
        if t_ >= 0.0 and E0 is None: E0 = stored(); Ein = Eout = 0.0
        Tf_ = T_of_H(Hf); Th_ = T_of_H(Hh); x = xice(Tf_); xh = xice(Th_)
        heat = (t_ >= ECL) and not opened; g = gE if ecl else gS
        if pre: f = 1.0
        elif ecl or not opened: f = 0.0
        else:
            To = Th_[1]; fcap = 1.0 if To >= Tr else min(1.0, max(0.0, (Tr - TRACK - 0.5) / max(1e-6, Tr - To))); f = min(fcap, f + 0.002 * DT)
        md = md0; mt = f * md / (npan * NT); mh = f * md / npan
        ke = KL * (1 - x) + KICE * x
        if mt > 1e-7:
            Re = mt * Dh / (A_f * F["mu"]); Pr = CPL * F["mu"] / KL; Nu = 0.9 * 0.023 * Re ** 0.8 * Pr ** 0.4 if Re > 2300 else 3.6
        else: Nu = 3.6
        Gwf = np.maximum(Nu, 3.6) * ke / Dh * P_w
        dhh = math.sqrt(4 * (S["hdr_fluid_kg_per_panel"] / RHO / HL) / math.pi)   # equivalent round bore of the lumped header
        keh = KL * (1 - xh) + KICE * xh; Gwfh = 3.66 * keh / dhh * math.pi * dhh * (HL / 2)
        if mh > 1e-6: Gwfh = Gwfh * 8.0
        qrf = g(Tfin) * dx; qa = Gf * (Tfin[:, :-1] - Tfin[:, 1:]); q0 = G0 * (Tw - Tfin[:, 0])
        dTfin = -qrf; dTfin[:, 0] += q0 + ((q_t / 2) if heat else 0.0); dTfin[:, :-1] -= qa; dTfin[:, 1:] += qa
        qwf = Gwf * (Tw - Tf_)
        qtube = -2 * q0 - g(Tw) * AO - qwf
        adv = np.zeros(NL)
        if mt > 0:
            Hin = np.concatenate(([Hh[0]], Hf[:-1])); adv = mt * (Hin - Hf)
        dHf = (qwf * dz + adv) / Mseg
        qrh = g(Twh) / 2 * math.pi * hdr_w * HL / 2   # g is per planform both faces = 2 ee sigma dT4; isolated cylinder surface pi*d per m -> ee sigma dT4 * pi d (conservative: no panel/bumper shadow)
        qwfh = Gwfh * (Twh - Th_); qhw = (q_h * HL / 2 if heat else 0.0) - qrh - qwfh
        advh = np.zeros(2)
        if mh > 0: advh[0] = mh * (H_of_T(Tr) - Hh[0]); advh[1] = mh * (Hf[-1] - Hh[1])
        dHh = (qwfh + advh) / Mh
        Tsup = f * Th_[1] + (1 - f) * Tr if (pre or opened) else Tr
        Qit = 0.0
        if pre: Qit = Qavg
        elif t_ >= ECL and opened: Qit = Qavg * min(1.0, max(0.0, (Tret0 + 1.0 - Thw) / 3.0))
        if pre or (t_ >= ECL):
            qp = 0.9 * md * CPL * (Thw - Tsup); dThw = (Qit - qp) / S["Chw"]; dTr = (qp - md * CPL * (Tr - Tsup)) / S["Cfl"]
            ql = QLOSS if (t_ >= ECL and not opened) else 0.0; dThw -= ql / S["Chw"]
        else:
            ql = QLOSS; qhr = 200.0 * (Thw - Tr); dThw = (-ql - qhr) / S["Chw"]; dTr = qhr / S["Cfl"]
        Tfin = Tfin + DT * dTfin / Cf; Tw = Tw + DT * qtube / C_wall; Hf = Hf + DT * dHf
        Twh = Twh + DT * qhw / Chw_h; Hh = Hh + DT * dHh; Thw += DT * dThw; Tr += DT * dTr
        Prad = npan * NT * dz * np.sum(2 * qrf.sum(1) + g(Tw) * AO) + npan * qrh.sum(); Ph = (npan * NT * L * q_t + npan * HL * q_h) if heat else 0.0
        if t_ >= 0.0:
            Ein += (Qit + Ph) * DT; Eout += (Prad + ql) * DT; R["E_heater_J"] += Ph * DT; R["E_rad_J"] += Prad * DT; R["E_loss_J"] += ql * DT; R["E_it_J"] += Qit * DT
            R["E_lost_J"] += (Pavg - Qit * Pavg / Qavg) * DT
            R["T_rad_min"] = min(R["T_rad_min"], float(min(Tf_.min(), Th_.min()))); R["T_fin_min"] = min(R["T_fin_min"], float(Tfin.min())); R["Thw_min"] = min(R["Thw_min"], Thw)
            R["ice_max_tube"] = max(R["ice_max_tube"], float(x.max())); R["ice_max_header"] = max(R["ice_max_header"], float(xh.max()))
            if ecl: R["T_tube_fluid_min_in_eclipse"] = min(R.get("T_tube_fluid_min_in_eclipse", 1e9), float(Tf_.min())); R["T_header_fluid_min_in_eclipse"] = min(R.get("T_header_fluid_min_in_eclipse", 1e9), float(Th_.min()))
            if ecl and R.get("t_first_ice_min") is None and x.max() > 0: R["t_first_ice_min"] = round(t_ / 60.0, 2)
        if t_ >= ECL and not opened and min(Tf_.min(), Th_.min()) >= TLIQ + 2.0:
            opened = True; R["t_open_min"] = round((t_ - ECL) / 60.0, 2); R["heater_kW"] = round((npan * NT * L * q_t + npan * HL * q_h) / 1e3, 2)
        if opened and t_ > ECL: R["supply_min_after_open"] = min(R["supply_min_after_open"], Tsup)
        if pre and abs(t_ + DT) < DT / 2: R["presun_Q_rad_kW"] = round(Prad / 1e3, 2); R["presun_Q_audit_kW"] = round(Qavg / 1e3, 2); R["presun_Tsup"] = round(Tsup, 2)
        t_ += DT
    E1 = stored(); R["energy_closure"] = round((E0 + Ein - Eout - E1) / max(Ein, Eout, 1.0), 5); R["f_end"] = round(f, 3); R["Thw_end"] = round(Thw, 2)
    for k in [k for k in R if k.endswith("_J")]: R[k.replace("_J", "_kWh")] = round(R.pop(k) / 3.6e6, 3)
    R.update(fluid=fluid, liquidus_K=TLIQ, npan=npan, ecl_min=ecl_min, q_t_W_per_m=q_t, q_h_W_per_m=q_h, QLOSS_W=QLOSS, header_len_m_per_panel=HL, header_radiating_d_m=hdr_w, insert=bool(PHI_C > 0), eclipse_pause_kWh=round(Pavg * ECL / 3.6e6, 3))
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in R.items()}
if __name__ == "__main__":
    S = json.load(open(sys.argv[1])); kw = json.loads(sys.argv[2]); out = sys.argv[3]
    r = run(S, **kw); r["scenario"] = S["tag"]; json.dump(r, open(out, "w"), indent=1); print(out, json.dumps(r))
