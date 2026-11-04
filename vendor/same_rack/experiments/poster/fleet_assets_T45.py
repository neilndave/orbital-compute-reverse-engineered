"""Fleet clip step 2: local-frame panel meshes (sheet / metal parts, mm) and the O5 deployed layout numbers for the fleet clip. Run in venv_cad:
PYTHONPATH=src:$HOME/rack_two_skies/p9_shim:experiments/poster RTS_TAG=_T45 python experiments/poster/fleet_assets_T45.py -> results/fleet/fleet_assets_T45.npz, fleet_layout_T45.json
Geometry = results/full3d/optimized_design_O5_T45.json (216 built panels, 12 across x 9 along x 2 wings; the +13 panels are added by fleet_kin_T45.py as a 10th panel on 13 chains, ESTIMATE)."""
import json, pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render_p9_hero_v2 as H
from rack_two_skies import assembly3d as A
ROOT = pathlib.Path(__file__).resolve().parents[2]
AO = H.AO
design = json.load(open(ROOT / "results/full3d/optimized_design_O5_T45.json")); prm = A.load_params()
for k, v in design["prm_overrides"].items():
    if k != "bus.stowed_size_xyz_m": prm[k] = list(v) if isinstance(v, (list, tuple)) else v
dep = AO.build_deployed3(design, prm)
pm = A.panel_meshes(dep["panel"]); lay = dep["layout"]; rl = dep["rl"]; al = dep["al"]
d = {}
for k in ("sheet", "tubes", "headers", "stubs"):
    d[f"panel_{k}_V"] = np.asarray(pm[k][0], np.float32); d[f"panel_{k}_F"] = np.asarray(pm[k][1], np.int32)
np.savez_compressed(ROOT / "results/fleet/fleet_assets_T45.npz", **d)
info = dep["panel"]["info"]
P = lay["panels"]; Ms = np.array([q["M"] for q in P])
meta = dict(panel_bbox_mm=info["bbox_mm"], panel_W_mm=info["width_mm"], panel_L_mm=info["length_mm"], gap_mm=rl["gap_mm"], across=rl["across"], along=rl["along"], wing_width_mm=rl["wing_width_mm"], wing_length_mm=rl["wing_length_mm"],
            y0_mm=lay["y0"], z_top_mm=lay["z_top"], z_arr_mm=lay["z_arr"], bus_mm=list(lay["bus"]["size"]), rack_mm=list(lay["rack"]["size"]), mast=lay["mast"],
            leaves=al["leaves"], leaf_len_mm=al["leaf_len_mm"], array_width_mm=al["width_mm"], fold=al["fold"], stack_pitch_mm=al["stack_pitch_mm"], array_thick_mm=prm["array.thickness_deployed_m"] * 1e3,
            n_panels_built=int(dep["n_panels"]), first_M_wing0=Ms[0].tolist(), first_M_wing1=Ms[rl["across"] * rl["along"]].tolist(), z_lo_mm=-rl["wing_width_mm"] / 2, panel_pitch_mm=info.get("pitch_mm"), al_keys=list(al.keys()), rl_keys=list(rl.keys()))
json.dump(meta, open(ROOT / "results/fleet/fleet_layout_T45.json", "w"), indent=1, default=float)
for k, v in d.items(): print(k, v.shape, v.min(0).round(1) if k.endswith("_V") else "")
print(json.dumps(meta, default=float)[:1800])
