import sys, math, json
sys.path.insert(0, "replica")
import orbit_loop as O
d = json.load(open("replica/results/t434_region.json"))["points"]
for k in ("Jun8|C1", "Aug4|C1"):
    p = d[k]; h = 600; bmin, cosb = O.beta_stats(h, 6.0)
    rho = O.dens["solar_mean"][h]; v = O.v_circ(h)
    dv_raise = max(0, O.v_circ(350) - v); dv_disp = abs(O.v_circ(200) - v)
    print(k, "bmin", bmin, "cosb", cosb, "rho", rho, "v", v, "dv_raise", dv_raise, "dv_disp", dv_disp)
    for lab, dry in (("M-prop", p["M"] - p["prop"]), ("Mcore-prop", p["M_core"] - p["prop"])):
        A_ram = p["A_rad"] + 15 + p["A_arr"] * 2 / math.pi * cosb
        prop = 0
        for i in range(60):
            Mavg = dry + 0.5 * prop; dvd = 0.5 * rho * v * v * 2.2 * A_ram / Mavg * 3 * 365.25 * 86400
            pn = dry * (math.exp((dv_raise + dvd + dv_disp) / (O.G0 * 2500)) - 1) * 1.21
            if abs(pn - prop) < 1e-9: break
            prop = pn
        print(lab, "A_ram", A_ram, "dv_drag", dvd, "prop", prop, "vs file", p["prop"])
