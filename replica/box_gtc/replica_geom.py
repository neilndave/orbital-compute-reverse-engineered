# t434: idealised deployed-envelope CAD (build123d) of each replica point -> STEP + summary JSON (areas measured from the solids, FCC check).  Box CPU.  ESTIMATE / ASSUMED layout:
# bus box on the origin, two solar wings (14 m wide, wing_len each) along +-Y in the plane, radiator panels edge-on in a block of 2 rows under the bus (idealised, not the adopted fleet layout).
import sys, json, math, pathlib, time
from build123d import Box, Pos, Compound, export_step
H = pathlib.Path(__file__).resolve().parent; out = H / "results"; (out / "step").mkdir(exist_ok=True, parents=True)
def build(pid):
    j = json.load(open(H.parent / "gtc_params" / f"point_{pid}.json")); g = j["geometry_derived"]; r = g["radiator"]; a = g["array"]; t0 = time.time()
    BX, BY, BZ = 0.7, 2.0, 2.4; parts = [Pos(0, 0, 0) * Box(BX, BY, BZ)]
    for s in (-1, 1):                                                   # solar wings: 20 leaves each, 1 cm thick
        for k in range(20): parts.append(Pos(7.0 * 0 + 0, s * (BY / 2 + 1.97 + (k + 0.5) * a["leaf_len_m"]), 0.0) * Box(a["width_m"], a["leaf_len_m"] * 0.98, 0.01))
    pw, pl = r["panel_W_mm"] / 1e3, r["panel_L_mm"] / 1e3; n = r["n_panels"]; cols = math.ceil(n / 2)
    for i in range(n): parts.append(Pos(-(BX / 2 + 0.5) - (i // 2) * (pw + 0.01) * 0 - 0, 0, 0) * Pos(0, 0, 0) * Pos(0, (i % 2 - 0.5) * (pl + 0.02), -(BZ / 2 + 0.3 + (i // 2) * (pw + 0.004))) * Box(pl * 0 + 0.004, pl, pw))
    comp = Compound(parts); bb = comp.bounding_box(); export_step(comp, str(out / "step" / f"replica_{pid}_deployed.step"))
    arr_area = 2 * 20 * a["width_m"] * a["leaf_len_m"] * 0.98; rad_face = n * pw * pl
    s = dict(id=pid, n_solids=len(parts), bbox_m=[round(bb.size.X, 3), round(bb.size.Y, 3), round(bb.size.Z, 3)], array_area_m2=round(arr_area, 2), radiator_face_area_m2=round(rad_face, 2), target_A_arr=j["areas"]["A_arr_m2"], target_A_rad=j["areas"]["A_rad_face_m2"],
             fcc=dict(array_le_1500=arr_area <= 1500, radiator_le_200=rad_face <= 200, mass_le_4000=j["result"]["mass_kg"] <= 4000), build_s=round(time.time() - t0, 1),
             label="ESTIMATE: idealised deployed envelope; panel/array architecture ASSUMED same as adopted baseline; not the fleet layout, not a clearance check; the bbox Z of the radiator block is an artefact of the idealised stacking and must not be quoted -- use only the measured areas and the FCC flags")
    json.dump(s, open(out / f"geom_{pid}.json", "w"), indent=1); print(json.dumps(s))
for pid in (sys.argv[1:] or ["J8_C1", "A4_C1"]): build(pid)
