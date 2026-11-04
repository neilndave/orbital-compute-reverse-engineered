"""Check 9A (t444): drag ram area by Warp ray-cast projected area on the replica deployed geometry (wp.Mesh + mesh_query_ray), orbit-averaged, vs the loop's A_ram formula.
Frame: z to Sun, x along array wings, y along radiator wings.  Velocity v = (s cos phi, s sin phi, -cos(beta) sin u), s = sqrt(1-(cos(beta) sin u)^2); phi = yaw azimuth of v in the x-y plane (0: radiator faces ram, 90: radiator edge-on).
Panel plate 14 mm, array leaf stack 1 mm (deployed single blanket, ASSUMED) -> edge-on contributions negligible.  ESTIMATE."""
import sys, json, math, time, numpy as np, warp as wp
wp.config.quiet = True
sys.path.insert(0, "replica/checks_t444")
import c8_viewfactor as C
SC = C.SC; dev = "cpu"

def plate(lo, hi): return C.box_tris(lo, hi, 0)
def build_parts(build, x0=4136.6, Wa=14000.0):
    lay = json.load(open(f"{SC}/{build}/fleet_layout_replica_{build}.json")); sp = json.load(open(f"{SC}/{build}/scene_params_{build}.json"))
    G = C.geometry(build, x0, Wa); W, L, gap = lay["panel_W_mm"], lay["panel_L_mm"], lay["gap_mm"]; zt = G["zt"]; cols = sp["radiator"]["panels_per_column"]; w0 = sp["radiator"]["wing0_cols"]
    parts = []
    for ci, n in enumerate(cols):
        zc = -zt + (ci if ci < w0 else ci - w0) * (W + gap) + W / 2
        for j in range(n):
            y0 = lay["y0_mm"] + j * (L + gap); ya, yb = (y0, y0 + L) if ci < w0 else (-(y0 + L), -y0)
            parts.append(plate([-7, ya, zc - W / 2], [7, yb, zc + W / 2]))
    npan = len(parts)
    for sgn in (1, -1):
        xa, xb = sorted((sgn * x0, sgn * (x0 + G["wl"]))); parts.append(plate([xa, -Wa / 2, G["za"] - 0.5], [xb, Wa / 2, G["za"] + 0.5]))
    parts += G["parts"][2:]   # bus + rack pod (no-NOBUS case)
    return parts, npan, G
@wp.kernel
def project(mesh: wp.uint64, o0: wp.vec3, e1: wp.vec3, e2: wp.vec3, d: wp.vec3, n2: int, h: float, cnt: wp.array(dtype=int)):
    t = wp.tid(); a = t // n2; b = t % n2
    o = o0 + e1 * (float(a) * h) + e2 * (float(b) * h)
    q = wp.mesh_query_ray(mesh, o, d, 1.0e6)
    if q.result: wp.atomic_add(cnt, 0, 1)
def area(mesh, v, h=0.05, half=40.0):
    v = np.array(v, float); v /= np.linalg.norm(v); t = np.array([0, 0, 1.0]) if abs(v[2]) < 0.9 else np.array([1.0, 0, 0]); e1 = np.cross(v, t); e1 /= np.linalg.norm(e1); e2 = np.cross(v, e1)
    n = int(2 * half / h); o0 = -half * e1 - half * e2 - 80.0 * v; cnt = wp.zeros(1, dtype=int, device=dev)
    wp.launch(project, n * n, [mesh.id, wp.vec3(*o0), wp.vec3(*e1), wp.vec3(*e2), wp.vec3(*v), n, h, cnt], device=dev)
    return cnt.numpy()[0] * h * h
if __name__ == "__main__":
    out = {}; t00 = time.time()
    for b in ("Jun", "Aug"):
        parts, npan, G = build_parts(b); V, F, g = [], [], []; off = 0
        for v, f, gg in parts: V.append(v); F.append(f + off); g += gg; off += len(v)
        V = np.vstack(V).astype(np.float32) * 1e-3; F = np.vstack(F).astype(np.int32)
        mesh = wp.Mesh(points=wp.array(V, dtype=wp.vec3, device=dev), indices=wp.array(F.ravel(), dtype=int, device=dev))
        res = {}
        for beta in (58.77, math.degrees(math.acos(0.26536)), 90.0):
            for phi in (0.0, 45.0, 90.0):
                us = np.arange(0, 360, 15.0); A = []
                for u in us:
                    c = math.cos(math.radians(beta)); vz = -c * math.sin(math.radians(u)); s = math.sqrt(max(0, 1 - vz * vz))
                    A.append(area(mesh, (s * math.cos(math.radians(phi)), s * math.sin(math.radians(phi)), vz), h=0.1))
                res[f"beta{beta}_phi{phi}"] = dict(mean=float(np.mean(A)), max=float(np.max(A)), min=float(np.min(A)))
                print(b, beta, phi, res[f"beta{beta}_phi{phi}"], flush=True)
        out[b] = res
    out["_s"] = time.time() - t00; json.dump(out, open("c9_ram.json", "w"), indent=1)
