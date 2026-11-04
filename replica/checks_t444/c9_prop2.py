import sys, math, json
sys.path.insert(0, "replica")
import orbit_loop as O
d = json.load(open("replica/results/t434_region.json"))["points"]; R = json.load(open("c9_ram.json"))
rk = [k for k in R["Jun"]]; mid = [k for k in rk if k.startswith("beta74")]; print("MID", mid)
print(list(O.dens.keys()))
def prop(dry0, Aram, rho, life, isp, v, dvr, dvs):
    p = 0
    for i in range(200):
        dvd = 0.5 * rho * v * v * 2.2 * Aram / (dry0 - p * 0 + 0.5 * p) * life * 365.25 * 86400
        pn = dry0 * (math.exp((dvr + dvd + dvs) / (O.G0 * isp)) - 1) * 1.21
        if abs(pn - p) < 1e-9: break
        p = pn
    return p, dvd
out = {}; h = 600; v = O.v_circ(h); dvr = max(0, O.v_circ(350) - v); dvs = abs(O.v_circ(200) - v)
for k, nm in (("Jun8|C1", "Jun"), ("Aug4|C1", "Aug")):
    p = d[k]; _, cosb = O.beta_stats(h, 6.0); Aloop = p["A_rad"] + 15 + p["A_arr"] * 2 / math.pi * cosb
    # dry such that dry+... : loop dry = M_core - prop(file)  (reproduces t434); full: M - prop
    Mc = p["M_core"] - p["prop"]; Mf = p["M"] - p["prop"]
    ray = {kk: R[nm][kk]["mean"] for kk in mid}
    rows = []
    def add(lab, dry0, A, rho_key="solar_mean", life=3, isp=2500):
        rho = O.dens[rho_key][h]; pr, dvd = prop(dry0, A, rho, life, isp, v, dvr, dvs); rows.append(dict(case=lab, A_ram=A, rho=float(rho), life=life, isp=isp, dv_drag=dvd, prop=pr))
    # note: the t434 fixed point uses dry = M_core - prop(file) as the dry mass entering exp(); iterate on dry0 consistently
    # (c9_prop.py reproduces 38.27/59.63 with Mavg = (M_core - prop_file) + 0.5 prop)
    def solve(Mx, A, rho_key="solar_mean", life=3, isp=2500, lab=""):
        rho = O.dens[rho_key][h]; pr = 0
        for _ in range(200):  # dry = Mx - pr (as in the loop)
            dry = Mx - pr; pn, dvd = prop(dry, A, rho, life, isp, v, dvr, dvs)
            if abs(pn - pr) < 1e-9: break
            pr = pn
        rows.append(dict(case=lab, A_ram=A, rho=float(rho), life=life, isp=isp, dv_drag=dvd, prop=pr))
    solve(p["M_core"], Aloop, lab="t434 as-is (core mass, loop A_ram)")
    solve(p["M"], Aloop, lab="full mass, loop A_ram")
    for kk, a in ray.items(): solve(p["M"], a, lab=f"full mass, Warp ray-cast {kk}")
    a0 = ray[[x for x in mid if x.endswith("phi0.0")][0]]
    for rk_ in O.dens:
        solve(p["M"], Aloop, rho_key=rk_, lab=f"full mass, loop A_ram, density {rk_}")
    for life in (5,): solve(p["M"], Aloop, life=life, lab=f"full mass, loop A_ram, life {life} yr")
    for isp in (2000, 3000): solve(p["M"], Aloop, isp=isp, lab=f"full mass, loop A_ram, isp {isp}")
    # edge on bound (min A) and worst face-on (max over orbit at beta_min) for reference
    out[nm] = dict(M=p["M"], M_core=p["M_core"], prop_file=p["prop"], A_loop=Aloop, rows=rows)
    for r in rows: print(nm, {a: ((round(b, 3) if abs(b) > 1e-3 else b) if isinstance(b, float) else b) for a, b in r.items()})
json.dump(out, open("c9_prop2.json", "w"), indent=1)
