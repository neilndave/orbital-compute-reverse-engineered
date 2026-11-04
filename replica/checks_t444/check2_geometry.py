# t444 check 2: audit replica render geometry (scene JSONs) against the final configs. ESTIMATE (geometry arithmetic + Warp AABB kernel).
# Warp kernel: pairwise box-overlap + envelope-radius test for every item in every layer (CPU on the box).
import json, math, sys, time, numpy as np, warp as wp
sys.path.insert(0, "vendor/same_rack/src")
from rack_two_skies import assembly3d as A
SC = "replica/gb10_render_replica/scene"; DR = "replica/gb10_render_replica/derisk"
fc = json.load(open(f"{DR}/final_configs.json")); prm = A.load_params(); prof = A.envelope_profile(prm); CLR = prm["launch_vehicle.clearance_m"]
wp.config.quiet = True; wp.init()
@wp.kernel
def overlap(lo: wp.array(dtype=wp.vec3), hi: wp.array(dtype=wp.vec3), n: int, out: wp.array(dtype=float)):
    i, j = wp.tid()
    if i < j and i < n and j < n:
        ox = wp.min(hi[i][0], hi[j][0]) - wp.max(lo[i][0], lo[j][0]); oy = wp.min(hi[i][1], hi[j][1]) - wp.max(lo[i][1], lo[j][1]); oz = wp.min(hi[i][2], hi[j][2]) - wp.max(lo[i][2], lo[j][2])
        if ox > 0.0 and oy > 0.0 and oz > 0.0:
            wp.atomic_max(out, 0, wp.min(ox, wp.min(oy, oz)))
res = {}
for b, N, nfold_exp, wcols in (("Jun", 46, 5, 4), ("Aug", 30, 6, 7)):
    pk = json.load(open(f"{SC}/{b}/fleet_pack_replica_{b}.json")); sp = json.load(open(f"{SC}/{b}/scene_params_{b}.json")); ly = json.load(open(f"{SC}/{b}/fleet_layout_replica_{b}.json"))
    cfg = fc[b]; S = cfg["S"]; r = {}
    # counts
    sats = [s for l in pk["layers"] for s in l["sats"]]; kept = [s for s in sats if s["keep"]]
    r["sats_listed"] = len(sats); r["sats_kept"] = len(kept); r["N_target"] = cfg["N_target"]; r["N_packed_final_configs"] = cfg["N_packed"]; r["N_packed_pack_json"] = pk["n_sats_packed"]; r["n_sats_pack_json"] = pk["n_sats"]
    r["layers"] = len(pk["layers"]); r["n_levels_scene_params"] = sp["n_levels"]
    # panels per satellite from radiator items (stack thickness -> panels at rpitch)
    rp = S["rpitch"]; l0 = pk["layers"][0]; panels = 0; stacks = 0
    for it in l0["items"]:
        if it["kind"] == "radiator":
            t = min(it["orient_m"]); n = round((t - 0.003) / rp) + 1; panels += n; stacks += 1
    r["rad_stacks_per_sat"] = stacks; r["panels_per_sat_from_pack"] = panels; r["panels_scene_params"] = sp["radiator"]["n_panels"]; r["panels_layout_built"] = ly["n_panels_built"]
    cols = sp["radiator"]["panels_per_column"]; r["panels_per_column_sum"] = sum(cols); r["columns"] = len(cols); r["columns_layout_across_w0_w1"] = [sp["radiator"]["wing0_cols"], sp["radiator"]["wing1_cols"]]
    r["layout_across"] = ly["across"]
    face = panels * sp["radiator"]["panel_planform_m2"]; r["radiator_face_m2_from_panels"] = round(face, 2)
    # array
    ar = sp["array"]; r["array_leaves_per_wing"] = ar["leaves_per_wing"]; r["array_wings"] = ar["wings"]; r["array_fold_expected"] = nfold_exp; r["array_fold_scene"] = ar["fold_n"]; r["array_fold_layout"] = ly["fold"]
    r["array_area_m2"] = round(2 * ar["width_m"] * ar["leaves_per_wing"] * ar["leaf_len_m"], 2); r["array_wing_len_m"] = ar["wing_len_m"]
    r["block_width_m"] = ar["block_width_m"]; r["block_width_x_fold_m"] = round(ar["block_width_m"] * ar["fold_n"], 4); r["stowed_thickness_m"] = ar["stowed_thickness_m"]; r["thickness_expected_leaves_fold_leaf"] = round(ar["leaves_per_wing"] * ar["fold_n"] * S["leaf"], 4)
    ai = [it for it in l0["items"] if it["kind"] == "array"]; r["array_item_dims_m"] = ai[0]["orient_m"] if ai else None; r["array_items_per_sat"] = len(ai)
    r["leaf_pitch_mm_layout"] = ly["stack_pitch_mm"]; r["leaf_mm_final_cfg"] = S["leaf"] * 1e3; r["array_deployed_thick_mm_layout"] = ly["array_thick_mm"]
    # bay: envelope + overlap kernel
    top = 0.0; worst_env = 9.0; worst_layer = None; maxov = 0.0; maxov_layer = None; top_kept = 0.0
    layers_kept = 0
    for l in pk["layers"]:
        zt = l["z0"] + l["H"]; top = max(top, zt)
        if any(s["keep"] for s in l["sats"]): top_kept = max(top_kept, zt); layers_kept += 1
        ra = A.envelope_radius(zt, prof) - CLR
        marg = ra - max(l["corner_r"], l["arr_corner_r"])
        if marg < worst_env: worst_env = marg; worst_layer = (l["layer"], round(zt, 3), round(ra, 3), l["corner_r"])
        lo = np.array([it["lo_m"] for it in l["items"]], dtype=np.float32); hi = lo + np.array([it["orient_m"] for it in l["items"]], dtype=np.float32); n = len(lo)
        o = wp.zeros(1, dtype=float); wp.launch(overlap, dim=(n, n), inputs=[wp.array(lo, dtype=wp.vec3), wp.array(hi, dtype=wp.vec3), n, o]); ov = float(o.numpy()[0])
        if ov > maxov: maxov = ov; maxov_layer = l["layer"]
    r["stack_top_m_all_listed"] = round(top, 3); r["stack_top_m_kept_only"] = round(top_kept, 3); r["layers_with_kept_sats"] = layers_kept; r["bay_height_limit_m"] = prof[-1][0]; r["height_margin_m_kept"] = round(prof[-1][0] - top_kept, 3)
    r["envelope_clearance_m"] = CLR; r["worst_radial_margin_m"] = round(worst_env, 3); r["worst_radial_layer(layer,z_top,r_allowed,corner_r)"] = worst_layer
    r["max_item_overlap_in_layer_m"] = round(maxov, 4); r["max_overlap_layer"] = maxov_layer
    r["sats_per_layer"] = [l["m"] for l in pk["layers"]]
    # dropped sats
    r["dropped"] = [(l["layer"], s["sat"]) for l in pk["layers"] for s in l["sats"] if not s["keep"]]
    res[b] = r
json.dump(res, open("check2_geometry.json", "w"), indent=1)
for b, r in res.items():
    print("==", b)
    for k, v in r.items(): print(f"  {k}: {v}")
