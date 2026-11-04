import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
src = open(os.path.join(HERE, "t423e_fp.py")).read().split("OUT = {\"info\": info}")[0]
ns = {"__file__": os.path.join(HERE, "t423e_fp_.py")}; exec(src, ns)
run, info, O, T, ap, W0, ORB_FCC, rk_b, FP_B = [ns[k] for k in ("run", "info", "O", "T", "ap", "W0", "ORB_FCC", "rk_b", "FP_B")]
RES = ns["RES"]; LV = ns["LV"]; BASE_ST = ns["BASE_ST"]; CR = ns["CR"]
X = {}
for b in ("Jun8", "Aug4"):
    tg = O.TARGET[b]["kwt"]; d = {}
    base = run(b, FP_B); d["FP_base"] = dict(M=base["M"], kwt=base["kwt"], kwt_ab=base["kwt_ab"], orbit=base["orbit"], N98=base["N98"], N100=base["N100"], N98_ab=base["N98_ab"], N100_ab=base["N100_ab"], fcc=base["fcc_flags"], T_rad=base["T_rad"], A_rad=base["A_rad"], A_arr=base["A_arr"], lines=base["lines"])
    # revert one FP lever at a time to the t423d stretch value
    rv = {}
    def r1(name, ids, **kw): 
        x = run(b, ids, **kw); rv[name] = dict(M=x["M"], kwt=x["kwt"], kwt_ab=x["kwt_ab"], N98=x["N98"])
    kwa = dict(cell="3J", wkg_wing=info["wing_base"], arr_deg=0.01)
    r1("revert_array->300 W/kg", [i for i in FP_B if i != "FPa_b"], wkg_wing=300.0)
    r1("revert_rack->t423d 3.8 kg/kW", [i for i in FP_B if i != "FPr_b"] + ["R2"])
    r1("revert_PCDU->1.6 kW/kg", [i for i in FP_B if i != "FPp_b"] + ["PCs"])
    r1("revert_struct->0.15", [i for i in FP_B if i != "FPs_b"])
    r1("revert_arr_deg->0.0015", FP_B, arr_deg=0.0015)
    r1("flown_class_PCDU_0.5", [i for i in FP_B if i != "FPp_b"] + ["PCf"])
    d["revert"] = rv
    # rack kg/kW at which FP_base just meets 70/75 (core and add-back)
    def kw_rack(k, ab):
        LV["FPr_x"] = dict(f_strip=0.0, rack_kg=k * 188.0, rack_scale=True); x = run(b, [i for i in FP_B if i != "FPr_b"] + ["FPr_x"]); return x["kwt_ab" if ab else "kwt"]
    for ab in (False, True):
        lo, hi = 0.5, 40.0
        for _ in range(40):
            m = (lo * hi) ** .5; (lo := m) if kw_rack(m, ab) >= tg else (hi := m)
        d["rack_kgkW_breakeven_" + ("ab" if ab else "core")] = lo
    # array W/kg at which FP_base (other FP) meets target with add-backs
    # definitions: mass budget under each kW/t definition
    P = O.TARGET[b]["P"]; avg = {"Jun8": 120.0, "Aug4": 175.0}[b]
    d["budget_kg"] = dict(peak_IT=P / tg * 1e3, avg_IT=avg / tg * 1e3)
    X[b] = d
    print(b, json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items() if k not in ("FP_base", "revert")}, default=str))
    print(" FP_base orbit", base["orbit"], "T_rad", round(base["T_rad"]), "N100", base["N100"], base["N100_ab"])
    for k, v in rv.items(): print("  ", k, {a: round(c, 1) for a, c in v.items()})
json.dump(X, open(f"{RES}/t423e_fp_extra.json", "w"), indent=1, default=str)
