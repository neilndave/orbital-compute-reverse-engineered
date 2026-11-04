import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
src = open(os.path.join(HERE, "t423e_fp.py")).read().split("OUT = {\"info\": info}")[0]
ns = {"__file__": os.path.join(HERE, "t423e_fp_.py")}; exec(src, ns)
run, O, RES, FP_B, BASE_ST = [ns[k] for k in ("run", "O", "RES", "FP_B", "BASE_ST")]
SI_T = 0.14   # kg/m2 : 60 um Si x 2330 kg/m3 (STATEMENT geometry)
def kwt(b, ids, eta, deg, n, **kw):
    Pd = eta * 1361.0 * 0.92; sig = n + SI_T; sigl = 319.7 / Pd * sig
    r = run(b, ids, cell="3J", wkg_wing=319.7 / sigl, arr_deg=deg, **kw); return r["kwt"], r["kwt_ab"], r["A_arr"] * 319.7 / Pd
OUT = {}
for b in ("Jun8", "Aug4"):
    tg = O.TARGET[b]["kwt"]; OUT[b] = {}
    for sname, ids, n, h in (("stretch(t423d) + SHJ n=0.40", [i for i in BASE_ST], 0.40, None), ("FP stack + SHJ n=0.25", FP_B, 0.25, True)):
        grid = {}
        for eta in (0.12, 0.14, 0.16, 0.18, 0.20, 0.22):
            for deg in (0.0015, 0.01, 0.03, 0.06):
                try:
                    if h: k, ab, A = kwt(b, ids, eta, deg, n)
                    else:
                        Pd = eta * 1361.0 * 0.92; sigl = 319.7 / Pd * (n + SI_T); r = run(b, ids, harn=None, cell="3J", wkg_wing=319.7 / sigl, arr_deg=deg); k, ab, A = r["kwt"], r["kwt_ab"], r["A_arr"] * 319.7 / Pd
                except Exception as e: k = ab = A = float("nan")
                grid[f"{eta:.2f}|{deg}"] = dict(kwt=k, kwt_ab=ab, A_arr_true=A)
        OUT[b][sname] = grid
        print(b, sname, "target", tg)
        for eta in (0.12, 0.14, 0.16, 0.18, 0.20, 0.22):
            print("  eta", eta, " ".join(f"{grid[f'{eta:.2f}|{d}']['kwt']:.0f}/{grid[f'{eta:.2f}|{d}']['kwt_ab']:.0f}(A{grid[f'{eta:.2f}|{d}']['A_arr_true']:.0f})" for d in (0.0015, 0.01, 0.03, 0.06)))
json.dump(OUT, open(f"{RES}/t423e_eff.json", "w"), indent=1)
