#!/usr/bin/env python3
"""t440 render-scene adapter stage 2b: turns the stage-1 replica layout/pack JSON (copied into an OVERLAY tree) into what the repo scene code expects.
usage: adapt_scene.py <overlay_dir> <Jun|Aug>
 (1) TWO-BOX BODY: the replica satellite body is the 'equip' box (0.7 x 2.0 x 1.12 m) plus the 'rack' box (0.6 x 1.2 x 0.60 m).  The repo scene has ONE bus box and an optional component 'pod'
     (precedent: results/fleet/fleet_pack_A6L_pod_t337.json, kin POD_NAME='comp_pod', staged group, mounted on the bus -z face, clearance 'pod_own').  We re-label rack -> comp_pod (kind 'pod'), keep equip as the bus.
 (2) DEPLOYED BODY GEOMETRY: layout bus_mm = equip dims; z_top = half of the radiator wing width; z_arr = z_top + 0.255 m (repo gap); mast from the bus top to z_arr.  Pod mount (bus -z face + 0.02 m gap) is written to layout['_replica']['pod_mount_m'].
 (3) YOKE ROOT LENGTH: kept at the repo value 4.1366 m (results/phase2_T45/chain_params_T45.json LEN[0]; docs/DERISK_PHASE2_T45.md section 4.2).  The Newton accordion h(t) replayed in the clip was solved with that yoke (21-hinge chain); the stage-1 1.968 m was the packer's own placeholder and is NOT used by the scene.
 (4) CLIP PARAMETERS scaled to the satellite count N (written to layout['_replica']['clip']): release stagger, unfold stagger, drift spacing.  ASSUMED / editorial.
All ESTIMATE / ASSUMED; geometry only."""
import sys, json, pathlib, math
ov = pathlib.Path(sys.argv[1]); B = sys.argv[2]
F = ov / "results/fleet"
pk = json.load(open(F / "fleet_pack_T45.json")); lay = json.load(open(F / "fleet_layout_T45.json"))
d = pk["items_dims_m"]
assert "rack" in d and "equip" in d, "expected replica rack + equip items"
rack = d.pop("rack"); d["comp_pod"] = {"kind": "pod", "dims": rack["dims"]}
for L in pk["layers"]:
    for it in L["items"]:
        if it["name"] == "rack": it["name"] = "comp_pod"; it["kind"] = "pod"
for L in pk["layers"]: L["sats"] = [x for x in L["sats"] if x.get("keep", True)]      # Aug packs 31, the design keeps 30: drop the slack satellite (top layer)
pk["layers"] = [L for L in pk["layers"] if L["sats"]]
# t440c: ONE_SAT=<packed sat index> (RENDER 2, single-satellite unfold): keep only the layer holding that satellite (a single-sat, un-rotated layer), renumbered layer 0 / sat 0, z0 = 0.  The environment has no hard-coded fleet size (Fleet.n = 1).
import os
if os.environ.get("ONE_SAT"):
    _o = int(os.environ["ONE_SAT"]); _L = [L for L in pk["layers"] if any(x["sat"] == _o for x in L["sats"])][0]
    assert len(_L["sats"]) == 1 and not _L["sats"][0].get("rot90"), "ONE_SAT must be a single-satellite, un-rotated layer"
    _L["sats"][0]["sat"] = 0; _L["layer"] = 0; _L["z0"] = 0.0; pk["layers"] = [_L]
eq = d["equip"]["dims"]; rk = rack["dims"]
lay["bus_mm"] = [eq[0] * 1e3, eq[1] * 1e3, eq[2] * 1e3]
ztop = 0.5 * lay["wing_width_mm"]; lay["z_top_mm"] = ztop; lay["z_arr_mm"] = ztop + 255.0
bus_top = 0.5 * eq[2] * 1e3
lay["mast"] = dict(od=200.0, z0=bus_top, z1=lay["z_arr_mm"]); lay["rack_mm"] = [rk[0] * 1e3, rk[1] * 1e3, rk[2] * 1e3]
pod_mount = -(0.5 * eq[2] + 0.5 * rk[2] + 0.02)
n_sat = sum(len(L["sats"]) for L in pk["layers"]); nl = len(pk["layers"])
clip = dict(n_sat=n_sat, n_layers=nl, t_stag=round(min(10.0, 70.0 / max(nl - 1, 1)), 3), t_ust=round(min(3.0, 39.0 / max(n_sat - 1, 1)), 3), v_z=0.0055,
            note="ASSUMED: release stagger so all layers leave inside the 115 s release act; unfold stagger so the last satellite still has ~100 s before TEND; drift spacing ~6 m per rank")
lay["_replica"].update(pod_mount_m=pod_mount, yoke_total_m=4.1366, yoke_source="repo results/phase2_T45/chain_params_T45.json LEN[0] (DERISK_PHASE2_T45.md 4.2)", clip=clip)
# panel mesh thickness: the repo mesh is 14 mm thick (round headers); the replica panel is 3 mm at 10 mm stowed pitch (C1 design) -> z of every panel mesh part scaled by 3/14 in the OVERLAY asset copy (ASSUMED)
import numpy as np
A = dict(np.load(F / "fleet_assets_T45.npz"))
for k in ("sheet", "tubes", "headers", "stubs"):
    v = A[f"panel_{k}_V"].astype(np.float64); v[:, 2] *= 3.0 / 14.0
    # t440b: the repo header/tube lips stick out 14 mm beyond the sheet in y (0 and L = 2944.6 mm), more than the packer's 10-20 mm item gap tolerates (6 mm graze on the pod / bus in the stowed stack);
    # the replica's flat headers are drawn with a 2 mm lip (= half the 4 mm hinge-chain gap) -> y outside [0, L] scaled by 2/14 (ASSUMED, visual + clearance envelope only)
    Lm = lay["panel_L_mm"]; m = v[:, 1] < 0; v[m, 1] *= 2.0 / 14.0; m = v[:, 1] > Lm; v[m, 1] = Lm + (v[m, 1] - Lm) * 2.0 / 14.0
    A[f"panel_{k}_V"] = v.astype(A[f"panel_{k}_V"].dtype)
np.savez(F / "fleet_assets_T45.npz", **A)
lay["_replica"]["rad_pitch_mm"] = 10.0; lay["_replica"]["panel_thick_mm"] = 3.0
json.dump(pk, open(F / "fleet_pack_T45.json", "w")); json.dump(lay, open(F / "fleet_layout_T45.json", "w"), indent=1)
print(B, "adapted: n_sat", n_sat, "layers", nl, "clip", clip["t_stag"], clip["t_ust"], "pod_mount", round(pod_mount, 3), "z_arr_mm", round(lay["z_arr_mm"], 1))
