"""Check 8 (t444): radiator-to-array view factor on the replica geometry, NVIDIA Warp ray trace (wp.Mesh + mesh_query_ray) vs the repo's exact Nusselt kernel.
Frame (repo assembly3d): z to Sun, x along array wings, y along radiator wings; radiator panels in plane x=0, face normal +x (mirror face identical); array = horizontal
rectangles at z=z_arr, x in [x0, x0+Lwing], y in [-Wa/2, Wa/2]. Occluders: equip bus box + rack pod box (counted as 'bus' blockage). ESTIMATE/ASSUMED geometry (replica scene adapter)."""
import sys, json, math, time, numpy as np, warp as wp
sys.path.insert(0, "vendor/same_rack/src")
wp.config.quiet = True
from rack_two_skies import viewfactor3d as V3
SC = "replica/gb10_render_replica/scene"
dev = "cpu"

def box_tris(lo, hi, gid):
    lo, hi = np.array(lo, float), np.array(hi, float)
    V = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    F = [[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]]
    return V, np.array(F), [gid] * 12

def rect_tris(x0, x1, ya, yb, z, gid):
    V = np.array([[x0, ya, z], [x1, ya, z], [x1, yb, z], [x0, yb, z]]); F = np.array([[0, 1, 2], [0, 2, 3]]); return V, F, [gid] * 2

def geometry(build, x0, Wa, add_other_wing=True):
    lay = json.load(open(f"{SC}/{build}/fleet_layout_replica_{build}.json")); sp = json.load(open(f"{SC}/{build}/scene_params_{build}.json")); pk = json.load(open(f"{SC}/{build}/fleet_pack_replica_{build}.json"))
    W, L, gap = lay["panel_W_mm"], lay["panel_L_mm"], lay["gap_mm"]; ww = lay["wing_width_mm"]; zt = 0.5 * ww; za = zt + 255.0
    eq = pk["items_dims_m"]["equip"]["dims"]; rk = pk["items_dims_m"]["rack"]["dims"]
    wl = sp["array"]["wing_len_m"] * 1e3
    cols = sp["radiator"]["panels_per_column"]; w0 = sp["radiator"]["wing0_cols"]
    # radiator panel centres (y>0 wing: wing0 columns; wing1 mirrors in y, so evaluate every column once on +y)
    pts = []
    for ci, n in enumerate(cols):
        zc = -zt + (ci % max(w0, 1) if ci < w0 else ci - w0) * (W + gap) + W / 2
        for j in range(n):
            y0 = lay["y0_mm"] + j * (L + gap)
            for s in (0.1667, 0.5, 0.8333):
                pts.append((ci, j, y0 + s * L, zc))
    pts = np.array(pts)
    meshparts = []
    for sgn in (1, -1):
        meshparts.append(rect_tris(sgn * x0, sgn * (x0 + wl), -Wa / 2, Wa / 2, za, 1))        # array wing (group 1)
    pod_z = -(0.5 * eq[2] + 0.5 * rk[2] + 0.02)
    if not __import__('os').environ.get('NOBUS'): meshparts.append(box_tris([-eq[0] / 2 * 1e3, -eq[1] / 2 * 1e3, -eq[2] / 2 * 1e3], [eq[0] / 2 * 1e3, eq[1] / 2 * 1e3, eq[2] / 2 * 1e3], 2))
    if not __import__('os').environ.get('NOBUS'): meshparts.append(box_tris([-rk[0] / 2 * 1e3, -rk[1] / 2 * 1e3, (pod_z - rk[2] / 2) * 1e3], [rk[0] / 2 * 1e3, rk[1] / 2 * 1e3, (pod_z + rk[2] / 2) * 1e3], 2))
    return dict(pts=pts, parts=meshparts, za=za, zt=zt, wl=wl, ww=ww, n_panels=len(cols) and sum(cols), eq=eq, rk=rk, panel_area_m2=W * L * 1e-6, x0=x0, Wa=Wa)

@wp.kernel
def trace(mesh: wp.uint64, gid: wp.array(dtype=int), py: wp.array(dtype=float), pz: wp.array(dtype=float), nray: int, seed: int, cnt: wp.array2d(dtype=int)):
    i = wp.tid(); st = wp.rand_init(seed, i)
    o = wp.vec3(0.001, py[i], pz[i])
    for k in range(nray):
        # cosine-weighted hemisphere about +x
        u1 = wp.randf(st); u2 = wp.randf(st)
        r = wp.sqrt(u1); ph = 6.283185307 * u2
        d = wp.vec3(wp.sqrt(wp.max(0.0, 1.0 - u1)), r * wp.cos(ph), r * wp.sin(ph))
        q = wp.mesh_query_ray(mesh, o, d, 1.0e6)
        if q.result:
            g = gid[q.face]
            wp.atomic_add(cnt, i, g, 1)

def run_mc(G, nray, seed=7):
    V, F, g = [], [], []; off = 0
    for v, f, gg in G["parts"]:
        V.append(v); F.append(f + off); g += gg; off += len(v)
    V = np.vstack(V).astype(np.float32); F = np.vstack(F).astype(np.int32)
    mesh = wp.Mesh(points=wp.array(V * 1e-3, dtype=wp.vec3, device=dev), indices=wp.array(F.ravel(), dtype=int, device=dev))
    pts = G["pts"]; n = len(pts)
    cnt = wp.zeros((n, 3), dtype=int, device=dev)
    wp.launch(trace, n, [mesh.id, wp.array(np.array(g, np.int32), dtype=int, device=dev), wp.array(pts[:, 2] * 1e-3, dtype=float, device=dev), wp.array(pts[:, 3] * 1e-3, dtype=float, device=dev), nray, seed, cnt], device=dev)
    return cnt.numpy()[:, 1:3] / nray

def exact(G):
    rects = np.array([[G["x0"] * 1e-3 if False else G["x0"] * 1e-3, (G["x0"] + G["wl"]) * 1e-3, -G["Wa"] * 5e-4, G["Wa"] * 5e-4, G["za"] * 1e-3]])
    return V3.exact(G["pts"][:, 2] * 1e-3, G["pts"][:, 3] * 1e-3, rects)

if __name__ == "__main__":
    nray = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    out = {}
    scen = {"S0_render_yoke4.137_W14": (4136.6, 14000.0), "S1_stage1_yoke1.968_W14": (1968.3, 14000.0), "S2_repo_root0.25_W14": (250.0, 14000.0), "S3_repo_root0.25_W8": (250.0, 8000.0), "S4_yoke4.137_W8": (4136.6, 8000.0)}
    t00 = time.time()
    for b in ("Jun", "Aug"):
        for name, (x0, Wa) in scen.items():
            G = geometry(b, x0, Wa); t0 = time.time(); mc = run_mc(G, nray); tmc = time.time() - t0
            ex = exact(G)
            ar = G["panel_area_m2"]; fa = mc[:, 0]; fb = mc[:, 1]
            # three sample points per panel -> mean per panel; every panel same area; whole radiator = mean over points
            res = dict(n_points=len(fa), f_array_mc_mean=float(fa.mean()), f_array_exact_mean=float(ex.mean()), f_bus_mc_mean=float(fb.mean()), f_array_max=float(ex.max()), f_array_min=float(ex.min()),
                       mc_minus_exact_rms=float(np.sqrt(np.mean((fa - ex) ** 2))), mc_minus_exact_max=float(np.abs(fa - ex).max()), nray=nray, mc_s=tmc,
                       z_arr_mm=G["za"], radiator_z_halfwidth_mm=G["zt"], x0_mm=x0, array_width_mm=Wa, n_panels=int(G["n_panels"]))
            # worst 10% of panels (closest to the array)
            res["f_array_p90"] = float(np.percentile(ex, 90))
            out[f"{b}/{name}"] = res
            print(b, name, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in res.items() if k in ("f_array_mc_mean", "f_array_exact_mean", "f_bus_mc_mean", "f_array_max", "mc_minus_exact_rms", "mc_minus_exact_max", "mc_s")}, flush=True)
    out["_total_s"] = time.time() - t00
    json.dump(out, open(__import__("os").environ.get("C8OUT","c8_viewfactor.json"), "w"), indent=1)
