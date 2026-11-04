# t434: stowed-volume packing of the replica satellites in the Starship bay with the repo's own packer (experiments/parity27/p27.py table_rows + dp2, unchanged).
# Only the ITEM MODEL is new (replica radiator stack count, array leaf size, bus bay); everything else is the repo code.  Box CPU.  ESTIMATE.
# usage: replica_pack.py <id|BASE254> [step] ; reads ../gtc_params/point_<id>.json ; writes results/pack_<id>_step<step>.json
import sys, os, json, math, time, pathlib
REPO = "vendor/same_rack"; sys.path[:0] = [f"{REPO}/experiments/parity27", f"{REPO}/experiments/knobs", f"{REPO}/src"]
pid = sys.argv[1]; step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25; argv0 = sys.argv; sys.argv = ["x"]
import p27
HERE = pathlib.Path(__file__).resolve().parent; PP = HERE.parent / "gtc_params"
PW, PL = 0.3634175776637853, 2.9445579551660426      # A6L panel (m)
def items_for(P_kW, n_pan, A_arr, S, per_stack=229 / 24.0):
    its = []; n = S.get("fold", 4); p = S.get("leaf", 0.009); w = A_arr / (2 * 14.0 * 20)       # array leaf side (m)
    for i in range(2): its.append((f"array_{i}", "array", (14.0 / n, w, 20 * p * n)))
    ns = max(1, round(n_pan / per_stack)); rp = S.get("rpitch", 0.02); thick = (n_pan / ns - 1.0) * rp + 0.003
    its += [(f"rad_{i}", "radiator", (PW, PL, thick)) for i in range(ns)]
    f = P_kW / 188.0; Veq = p27.VEQ0 * (0.338 + 0.662 * f) * (p27.V.V_EQ_DENSITY0 / S.get("rho", 400.0)) * float(os.environ.get("VEQ_SCALE", "1.0"))   # VEQ_SCALE: sensitivity probe only (default 1.0 = repo scaling)
    its.append(("bus", "bus", (p27.BX, p27.BY, p27.BUSZ0 + Veq / (p27.BX * p27.BY))))
    return its, ns, thick
if pid == "BASE254": P, npan, Aarr, tgt = 188.0, 254, 752.0, 13           # adopted baseline: repo says 13 per Starship (DECISIONS rows 81/83)
else:
    j = json.load(open(PP / f"point_{pid}.json")); P = j["result"]["P_IT_peak_kW"]; npan = j["geometry_derived"]["radiator"]["n_panels"]; Aarr = j["areas"]["A_arr_m2"]; tgt = j["targets"]["sats_per_starship_98t"]
VS = os.environ.get("VEQ_SCALE", "1.0"); out = dict(veq_scale=float(VS), id=pid, P_kW=P, n_panels=npan, A_arr_m2=Aarr, target_sats_mass_bound=tgt, step=step, runs={})
for fold in (2, 4):
    t0 = time.time(); S = dict(fold=fold, leaf=0.009); its, ns, thick = items_for(P, npan, Aarr, S); rows = p27.table_rows(its, step); tt = time.time() - t0
    for arch in ("layers", "stack1", "books"):
        k = p27.ARCH[arch]; n, seq = p27.dp2(rows, adapt=0.15, pmode="std", **k)
        out["runs"][f"fold{fold}|{arch}"] = dict(n_sat=n, layers=seq, n_stacks=ns, stack_thick_m=round(thick, 4), item_vol_m3=sum(a * b * c for _, _, (a, b, c) in its), table_s=round(tt, 1))
        print(pid, f"fold{fold}", arch, "n_sat", n, "stacks", ns, "table_s", round(tt, 1), flush=True)
out["label"] = "ESTIMATE: repo packer (p27 table_rows/dp2) on a replica item model; 9 mm leaves, 20 mm radiator pitch, adapter 0.15 m, standard Starship bay profile; no dispenser, no loads"
json.dump(out, open(HERE / "results" / f"pack_{pid}_step{step}" + ("" if VS == "1.0" else f"_veq{VS}") + ".json", "w"), indent=1)
