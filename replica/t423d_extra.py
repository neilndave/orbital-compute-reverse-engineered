import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
src = open(os.path.join(HERE, "orbit_loop_run_t423c.py")).read().split("# ===================================================================================================== PASS A")[0]
src = src.replace("orbit_loop_t423c", "orbit_loop_t423d").replace('"t423c"', '"t423d"').replace('plog.event("milestone"', 'pass  # plog.event("milestone"', 1)
ns = {"__file__": os.path.join(HERE, "orbit_loop_run_t423d.py")}; exec(src, ns)
T, ap, W0, W0f, LV, ORB_FCC, ORB_ALL, addb, O = [ns[k] for k in ("T", "ap", "W0", "W0f", "LV", "ORB_FCC", "ORB_ALL", "addb", "O")]
RES = ns["RES"]
K3 = dict(dT=20.0, panel_fluid=False); K5 = dict(dT=20.0, panel_fluid=False, run_scale=0.5)
LV.update({"E1c": dict(harness_V=300.0), "C_hot": dict(cool=K3), "C_str": dict(cool=K5, pump=0.10), "PCs": dict(pcdu_kwkg=1.6), "PCf": dict(pcdu_kwkg=0.50)})
CR = ["E1c", "C_hot", "PCf"]; ST = ["R2", "S1", "E1c", "P1", "E2", "D1", "D2", "A2", "C_str", "PCs"]
def kw(b, ids, scale, w): 
    p = ap(W0[b] if scale == "scaled" else W0f[b], ids, wkg_wing=float(w)); o = T.best_orbit(b, p, ORB_FCC); return o["kwt_wet"], addb(o)[1], o
def need(b, ids, scale, tgt, ab):
    f = lambda w: kw(b, ids, scale, w)[1 if ab else 0]
    if f(3000) < tgt: return None
    lo, hi = 60.0, 3000.0
    for _ in range(40):
        m = .5 * (lo + hi); (hi := m) if f(m) >= tgt else (lo := m)
    return hi
R = {}
for b in ("Jun8", "Aug4"):
    tg = O.TARGET[b]["kwt"]
    for sc in ("scaled", "fixed"):
        d = {}
        d["T2_300"] = kw(b, [], sc, 300)[:2]
        d["T2_124"] = kw(b, [], sc, 124)[:2]
        d["cred_124"] = kw(b, CR, sc, 124)[:2]; d["cred_300"] = kw(b, CR, sc, 300)[:2]; d["cred_200"] = kw(b, CR, sc, 200)[:2]; d["cred_massless_array"] = kw(b, CR, sc, 1e9)[:2]
        d["cred_minus_PCf"] = kw(b, ["E1c", "C_hot"], sc, 124)[:2]       # PCDU left at T2 0.85 kW/kg-equivalent
        d["cred_plus_R2S1"] = kw(b, CR + ["R2", "S1"], sc, 124)[:2]
        d["stretch_124"] = kw(b, ST, sc, 124)[:2]; d["stretch_200"] = kw(b, ST, sc, 200)[:2]; d["stretch_300"] = kw(b, ST, sc, 300)[:2]
        d["stretch_Chot_only"] = kw(b, [i if i != "C_str" else "C_hot" for i in ST], sc, 300)[:2]   # credible coolant instead of stretch coolant
        d["stretch_noR2"] = kw(b, [i for i in ST if i != "R2"], sc, 300)[:2]
        d["need_cred_core"] = need(b, CR, sc, tg, False); d["need_cred_ab"] = need(b, CR, sc, tg, True)
        d["need_cred_plusR2S1_core"] = need(b, CR + ["R2", "S1"], sc, tg, False)
        d["need_stretch_core"] = need(b, ST, sc, tg, False); d["need_stretch_ab"] = need(b, ST, sc, tg, True)
        d["need_stretchChot_core"] = need(b, [i if i != "C_str" else "C_hot" for i in ST], sc, tg, False)
        R[f"{b}|{sc}"] = d
    # orbit view: stretch@300 per orbit
    p = ap(W0[b], ST, wkg_wing=300.0); tab = {hl: T.evaluate(b, p, *hl) for hl in ORB_ALL}
    R[f"{b}|orbit_stretch"] = {f"{h}|{l}": dict(kwt=x["kwt_wet"], in_fcc=(h, l) in ORB_FCC, t_ecl=x["t_ecl_max_min"], M=x["M_kg"]) for (h, l), x in tab.items()}
json.dump(R, open(f"{RES}/t423d_extra.json", "w"), indent=1, default=str)
for k, v in R.items():
    if "orbit" in k:
        top = sorted(v.items(), key=lambda kv: -kv[1]["kwt"])[:5]; print(k, [(a, round(c["kwt"], 2), c["in_fcc"]) for a, c in top]); continue
    print(k); [print("  ", a, (tuple(round(x, 1) for x in c) if isinstance(c, (tuple, list)) else (round(c, 0) if c else c))) for a, c in v.items()]
