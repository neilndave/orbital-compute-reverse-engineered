# t438: explicit margin accounting per build.  Load-path mass from the t436b loadpath() (function text re-used unchanged, evaluated at the FINAL N and adapter/gap), fold hinge mass (n-4)*40*f*0.4*1.519 kg, f = P/188 (repo fold-hinge mass rule used in t436/t438).
import ast, math, json, pathlib
src = open(pathlib.Path(__file__).resolve().parent / "t436b_checks.py").read(); tree = ast.parse(src)
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "loadpath"][0]
ns = {"math": math, "g": 9.81}; exec(compile(ast.Module([fn], []), "lp", "exec"), ns); loadpath = ns["loadpath"]
B = {"Jun": dict(P=150.0, mtot=2130.4348, N=46, fold=5, margin=345.38, adapt=0.05, gap=0.02, kwt_limit=70.0),
     "Aug": dict(P=250.0, mtot=3266.6667, N=30, fold=6, margin=535.05, adapt=0.05, gap=0.02, kwt_limit=75.0)}
out = {}
for k, b in B.items():
    lp_ideal = loadpath(b["N"], b["mtot"], adapt=b["adapt"], gap=b["gap"])      # idealised 3-column / ceil(N/3) levels (t436b model)
    pk = json.load(open(pathlib.Path(__file__).resolve().parent / f"results/t438/scene/{k}/fleet_pack_replica_{k}.json"))["layers"]   # ACTUAL packed layer sequence
    Lr = len(pk); top = pk[-1]["z0"] + pk[-1]["H"]
    lp = loadpath(b["N"], b["mtot"], cols=b["N"] / Lr, H_level=top / Lr - 0.07, adapt=b["adapt"], gap=b["gap"])   # effective columns = N/levels
    f = b["P"] / 188.0; hinge = (b["fold"] - 4) * 40 * f * 0.4 * 1.519
    used = lp["added_kg_per_sat"] + hinge
    out[k] = dict(N=b["N"], fold=b["fold"], P_kW=b["P"], sat_mass_kg=b["mtot"], kW_per_t=round(b["P"] / (b["mtot"] / 1e3), 2), kW_per_t_limit=b["kwt_limit"],
                  fcc_4t_ok=b["mtot"] < 4000, stack_mass_t=round(b["N"] * b["mtot"] / 1e3, 2), margin_line_before_kg=b["margin"], loadpath_kg_per_sat=lp["added_kg_per_sat"], loadpath_kg_per_sat_idealised_3col=lp_ideal["added_kg_per_sat"], packed_levels=Lr, packed_stack_top_m=round(top, 2),
                  loadpath_detail=dict(levels=lp["levels"], stack_height_m=lp["stack_height_m"], posts=lp["post_mass_kg_total"], rod=lp["rod_mass_kg_total"], pins=lp["pin_mass_kg_total"], shortening_mm_6g=lp["stack_shortening_mm_6g"]),
                  fold_hinge_kg_per_sat=round(hinge, 1), absorbed_total_kg=round(used, 1), margin_line_after_kg=round(b["margin"] - used, 1), margin_used_pct=round(100 * used / b["margin"], 1),
                  total_mass_change_kg=0.0)
json.dump(out, open(pathlib.Path(__file__).resolve().parent / "results/t438/margin_table.json", "w"), indent=1); print(json.dumps(out, indent=1))
