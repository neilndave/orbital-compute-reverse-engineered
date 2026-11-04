# t438: render scene adapter, stage 1 (box CPU, numpy only).  final config + packer -> (a) fleet_pack-format JSON (same schema fleet_kin_T45.py reads through FLEET_PACK),
# (b) fleet_layout-format JSON for the replica satellite (radiator columns, array leaf length, fold n), (c) scene_params JSON (counts, masses, labels).
# usage: replica_scene_adapter.py Jun|Aug   (reads results/t438/final_configs.json, writes results/t438/scene/<build>/...).  Geometry only, ESTIMATE; panel geometry = adopted-baseline panel (363.4 x 2944.6 mm) ASSUMED.
import sys, os, json, math, pathlib, copy
REPO = "vendor/same_rack"; sys.path[:0] = [f"{REPO}/experiments/parity27", f"{REPO}/experiments/knobs", f"{REPO}/src"]
HERE = pathlib.Path(__file__).resolve().parent; sys.argv_backup = sys.argv; sys.argv = ["x"]
import p27, t438_loop as TL
sys.argv = sys.argv_backup
R = p27.R
def arrangement(m, X, Y, gap, maxrows, maxper):
    """same search as p27.layer_cr2 but returns the satellite footprint centres; origin at the centre of the arrangement"""
    best = None
    def parts(rem, mx, k):
        if rem == 0: yield (); return
        if k == 0: return
        for a in range(min(rem, mx), 0, -1):
            for rest in parts(rem - a, a, k - 1): yield (a,) + rest
    for part in parts(m, maxper, maxrows):
        k = len(part)
        for (a, b) in ((X, Y), (Y, X)):
            Hh = k * b + (k - 1) * gap; cr = 0.0; cen = []
            for j, nr in enumerate(part):
                wd = nr * a + (nr - 1) * gap; y0 = -Hh / 2 + j * (b + gap); y1 = y0 + b
                cr = max(cr, math.hypot(wd / 2, max(abs(y0), abs(y1))))
                for i in range(nr): cen.append((-wd / 2 + i * (a + gap) + a / 2, (y0 + y1) / 2))
            if best is None or cr < best[0] - 1e-12: best = (cr, cen, (a, b))
    return best
def column_plan(n_panels, n_stacks):
    """radiator columns of the deployed satellite: n_stacks columns split over 2 wings (ceil on wing 0), panels per column 9 or 10 (+ any remainder). ASSUMED layout rule (the adopted baseline has 12 columns per wing of 9 or 10)."""
    base = n_panels // n_stacks; extra = n_panels - base * n_stacks            # `extra` columns carry base+1 panels
    cols = [base + 1] * extra + [base] * (n_stacks - extra); w0 = (n_stacks + 1) // 2
    return dict(panels_per_column=cols, wing0_cols=w0, wing1_cols=n_stacks - w0)
def build(build, outroot):
    F = json.load(open(HERE / "results/t438/final_configs.json"))[build]; S = F["S"]; pid = F["id"]; arch = F.get("arch", "layers"); N_target = F["N_target"]
    its, ns, thick = TL.items_for(p27, pid, S); R.items = its; R._PC = {}
    rec = None
    for l in open(HERE / "results/t438/passes.jsonl"):
        r = json.loads(l)
        if r["pass_"] == F["pass"] and r["id"] == pid: rec = r
    seq = rec["res"][arch]["seq"]; k = p27.ARCH[arch]; gap = S.get("gap", 0.05)
    out = dict(note=f"ESTIMATE, geometry only (t438 replica adapter): {build} {pid} {arch} packing from pass {F['pass']}; satellites beyond N_target={N_target} are dropped from the last levels; no dispenser, no loads", layers=[])
    nsat = 0; kept = 0
    for li, l in enumerate(seq):
        m, X, Y, H, z0 = l["m"], l["X"], l["Y"], l["H"], l["z0"]
        cr, cen, (a, b) = arrangement(m, X, Y, gap, k["maxrows"], k["maxper"]); r = R._pack(X, Y, False); assert r is not None
        Hp, placed = r; assert abs(Hp - H) < 0.011, (li, Hp, H)
        sats = []
        for (cx, cy) in cen:
            rot90 = abs(a - X) > 1e-9 and abs(a - Y) < 1e-9 and abs(X - Y) > 1e-9
            sats.append(dict(sat=nsat, centre_xy=[cx, cy], rot90=bool(rot90), keep=nsat < N_target)); nsat += 1
        out["layers"].append(dict(layer=li, m=m, X=X, Y=Y, H=H, z0=z0, corner_r=l["corner_r"], arr_corner_r=cr, arr_ab=[a, b], H_pack=Hp, sats=sats,
                                  items=[dict(name=p["name"], kind=p["kind"], orient_m=list(p["orient_m"]), lo_m=list(p["lo_m"])) for p in placed]))
    out["items_dims_m"] = {n: dict(kind=kd, dims=list(d)) for n, kd, d in its}; out["n_sats_packed"] = nsat; out["n_sats"] = min(nsat, N_target)
    d = outroot / build; d.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(d / f"fleet_pack_replica_{build}.json", "w"), indent=1)
    pt = json.load(open(HERE.parent / "gtc_params" / f"point_{pid}.json")); g = pt["geometry_derived"]; rad = g["radiator"]; arr = g["array"]
    cp = column_plan(rad["n_panels"], ns)
    base = json.load(open(f"{REPO}/results/fleet/fleet_layout_T45.json"))   # baseline layout kept for every number not overridden (bus, yoke, panel mesh, gap, z offsets)
    lay = copy.deepcopy(base)
    lay.update(across=max(cp["wing0_cols"], cp["wing1_cols"]), along=min(cp["panels_per_column"]), leaf_len_mm=arr["leaf_len_m"] * 1e3, leaves=arr["leaves_per_wing"],
               array_width_mm=arr["width_m"] * 1e3, fold=S.get("fold", 4), stack_pitch_mm=S.get("leaf", 0.009) * 1e3, array_thick_mm=S.get("leaf", 0.009) * 1e3 * 0 + base["array_thick_mm"],
               wing_length_mm=arr["wing_len_m"] * 1e3, rack_mm=[600.0, 1200.0, [i for i in out["items_dims_m"].items() if i[0] == "rack"][0][1]["dims"][2] * 1e3], n_panels_built=rad["n_panels"])
    lay["wing_width_mm"] = lay["across"] * (lay["panel_W_mm"] + lay["gap_mm"]) - lay["gap_mm"]; lay["z_lo_mm"] = -lay["wing_width_mm"] / 2
    lay["_replica"] = dict(build=build, id=pid, column_plan=cp, label="ASSUMED: panel mesh = adopted-baseline panel; columns/wing from the packer's radiator stack count; array deployed thickness kept at the baseline 10 mm; yoke root kept at the baseline 1.968 m (point JSON) vs 4.137 m in the repo chain params (to resolve)")
    json.dump(lay, open(d / f"fleet_layout_replica_{build}.json", "w"), indent=1)
    sp = dict(build=build, point=pid, N_per_Starship_target=N_target, N_packed=nsat, arch=arch, S=S, n_levels=len(seq), radiator=dict(rad, n_stacks=ns, **cp), array=dict(arr, fold_n=S.get("fold", 4), leaf_mm=S.get("leaf", 0.009) * 1e3,
              block_width_m=14.0 / S.get("fold", 4), stowed_thickness_m=20 * S.get("leaf", 0.009) * S.get("fold", 4)),
              mass=pt["result"], mass_lines_kg=pt["mass_lines_kg"], newton_overlay_inputs=pt["newton_overlay_inputs"], label="ESTIMATE / ASSUMED, see GTC_REPLICA_PLAN.md section 3c")
    json.dump(sp, open(d / f"scene_params_{build}.json", "w"), indent=1); print(build, "levels", len(seq), "sats packed", nsat, "kept", out["n_sats"], "columns", cp)
if __name__ == "__main__":
    for b in (sys.argv[1:] or ["Jun", "Aug"]): build(b, HERE / "results/t438/scene")
