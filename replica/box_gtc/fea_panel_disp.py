# t438 derisk (b): CalculiX static displacement of ONE adopted-baseline-geometry radiator panel (0.3634 x 2.9446 m, 4 tubes; repo P8a model, UNCHANGED, 7-station pad layout) under the launch load corners,
# to compare the peak out-of-plane deflection with the clearance left by a 10 mm stack pitch.  Header (flat 34x7 mm) is carried as lumped end-row mass with no stiffness, as in the repo P8a model (conservative for sag).
# ESTIMATE: idealised screening model, assumed pad layout, quasi-static, not a coupled-loads or sign-off analysis.  Box CPU, CalculiX 2.21 (ccx, 1 thread).
import os, sys, json, math, pathlib, subprocess, time
os.environ["P8A_VARIANT"] = "_f4_O5_T45"
sys.path.insert(0, "vendor/same_rack/experiments/p8a_launch_fea"); import numpy as np, p8a_model as pm
H = pathlib.Path(__file__).resolve().parent; W = H / "fea_panel"; W.mkdir(exist_ok=True)
cfg = pm.load_cfg(); mdl = pm.build(cfg, "stack_7station"); m = mdl["mesh"]; nn = len(m.xyz)
pm.write_inp(mdl, W / "d.inp", cfg, steps=())
with open(W / "d.inp", "a") as f:
    f.write(f"*NSET, NSET=NALL, GENERATE\n1, {nn}, 1\n")
    for dx in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        f.write(f"*STEP\n*STATIC\n*DLOAD, OP=NEW\nEALL, GRAV, {pm.G0}, {dx[0]}, {dx[1]}, {dx[2]}\n*NODE PRINT, NSET=NALL\nU\n*END STEP\n")
t0 = time.time(); env = dict(os.environ, OMP_NUM_THREADS="1")
r = subprocess.run(["ccx", "-i", "d"], cwd=W, capture_output=True, text=True, env=env); print("ccx rc", r.returncode, round(time.time() - t0, 1), "s"); (W / "ccx_stdout.txt").write_text(r.stdout + r.stderr)
U = []; cur = None
for line in open(W / "d.dat"):
    if "displacements (vx,vy,vz)" in line: cur = np.zeros((nn, 3)); U.append(cur); continue
    a = line.split()
    if cur is not None and len(a) == 4 and a[0].isdigit(): cur[int(a[0]) - 1] = [float(x) for x in a[1:]]
assert len(U) == 3, len(U)
xyz = np.array(m.xyz)
corners = {"max_axial": (6.0, 0.5), "max_lateral": (3.5, 2.0), "tension_lat": (-1.5, 2.0), "max_tension": (-2.0, 0.5)}   # (axial g, lateral g), repo P8a loads (Starship UG v1 Fig 5 / Falcon UG Table 5-3, as in docs/P8A_LAUNCH_FEA.md)
res = {}
for nm, (az, lat) in corners.items():
    best = (0, 0, None)
    for th in range(0, 360, 15):
        u = az * U[2] + lat * (math.cos(math.radians(th)) * U[0] + math.sin(math.radians(th)) * U[1])      # sign: +axial = +z gravity vector
        uz = np.abs(u[:, 2]).max(); uh = np.hypot(u[:, 0], u[:, 1]).max()
        if uz > best[0]: best = (uz, uh, th, xyz[np.abs(u[:, 2]).argmax()].tolist())
    res[nm] = dict(max_abs_uz_mm=round(best[0] * 1e3, 3), max_inplane_mm=round(best[1] * 1e3, 3), theta_deg=best[2], at_xyz_m=[round(v, 3) for v in best[3]])
tube = 5.678; res["clearance_mm"] = {f"{p}mm_pitch": round(p - tube, 2) for p in (8, 10, 12, 20)}
res["unit_1g_max_uz_mm"] = round(float(np.abs(U[2][:, 2]).max()) * 1e3, 4); res["mass_kg"] = mdl["total_kg"]; res["n_nodes"] = nn
res["label"] = "ESTIMATE: repo P8a O5_T45 panel + stack_7station pad layout (ASSUMED), quasi-static, header as lumped mass; relative displacement of one panel vs its pads; two adjacent panels deflect together only if both are loaded alike (this is the worst-case magnitude vs the clearance, not a contact analysis)"
json.dump(res, open(H / "results/t438/fea_panel_disp.json", "w"), indent=1); print(json.dumps(res, indent=1))
