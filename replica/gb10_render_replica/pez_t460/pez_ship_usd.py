"""[t460] Render-scene ship for the indexed-PEZ Render 1 (SCHEMATIC, ASSUMED - not a Starship model): horizontal cylinder along world X (r 4.5 m, 60 m long), bay wall r 4.0 m,
slot window cut through the shell on the top (+Z, leeward): 7.3 m wide (Y, 3RD public figure) x 1.8 m long (X, ASSUMED), with jamb faces.  Built as USD meshes."""
import math
import numpy as np
import pez_release as PR

def build(stage, UsdGeom, Gf, Vt, UsdShade, mat_out, mat_in, x0=-30.0, x1=30.0):
    R, RI, hw, hl = PR.HULL_R, PR.BAY_R, PR.SLOT_W / 2.0, PR.SLOT_H / 2.0
    tw = math.asin(hw / R); twi = math.asin(hw / RI) if hw < RI else math.pi / 2     # window half-angle on the outer / inner surface (measured from +Z)
    # theta grid (0 = +Z top, periodic), aligned to +-tw
    def thetas(tw_):
        n_in = 14; a = np.linspace(-tw_, tw_, n_in + 1)
        n_out = 60; b = np.linspace(tw_, 2 * math.pi - tw_, n_out + 1)
        return np.concatenate([a[:-1], b[:-1]]), n_in
    xs = np.unique(np.concatenate([np.linspace(x0, -hl, 12), np.linspace(-hl, hl, 3), np.linspace(hl, x1, 12)]))
    def surf(path, r, tw_, inward, mat):
        th, n_in = thetas(tw_); nt = len(th); nx = len(xs)
        pts = [(x, r * math.sin(t), r * math.cos(t)) for x in xs for t in th]
        nrm = [(0.0, (-1 if inward else 1) * math.sin(t), (-1 if inward else 1) * math.cos(t)) for x in xs for t in th]
        cnt = []; idx = []
        for i in range(nx - 1):
            for j in range(nt):
                j2 = (j + 1) % nt
                in_win = (abs(0.5 * (xs[i] + xs[i + 1])) < hl) and (j < n_in)      # quads between +-tw_ are the window
                if in_win: continue
                a, b, c, d = i * nt + j, i * nt + j2, (i + 1) * nt + j2, (i + 1) * nt + j
                idx += ([a, d, c, b] if inward else [a, b, c, d]); cnt.append(4)
        m = UsdGeom.Mesh.Define(stage, path); m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, p)) for p in pts])); m.CreateFaceVertexCountsAttr(Vt.IntArray(cnt)); m.CreateFaceVertexIndicesAttr(Vt.IntArray(idx))
        m.CreateSubdivisionSchemeAttr("none"); m.CreateDoubleSidedAttr(True)
        pv = UsdGeom.PrimvarsAPI(m.GetPrim()).CreatePrimvar("normals", __import__("pxr").Sdf.ValueTypeNames.Normal3fArray, UsdGeom.Tokens.vertex); pv.Set(Vt.Vec3fArray([Gf.Vec3f(*map(float, q)) for q in nrm]))
        UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat); return m
    surf("/World/Ship/pez_hull", R, tw, False, mat_out); surf("/World/Ship/pez_bay", RI, twi, True, mat_in)
    # jamb faces: two ends of the window (x = +-hl) and two sides (theta = +-tw), r from RI to R
    pts = []; idx = []; cnt = []
    def quad(p):
        k = len(pts); pts.extend(p); idx.extend([k, k + 1, k + 2, k + 3]); cnt.append(4)
    th_o = np.linspace(-tw, tw, 15); th_i = np.linspace(-twi, twi, 15)
    for sx in (-hl, hl):
        for j in range(14):
            quad([(sx, R * math.sin(th_o[j]), R * math.cos(th_o[j])), (sx, R * math.sin(th_o[j + 1]), R * math.cos(th_o[j + 1])), (sx, RI * math.sin(th_i[j + 1]), RI * math.cos(th_i[j + 1])), (sx, RI * math.sin(th_i[j]), RI * math.cos(th_i[j]))])
    for s, (to, ti) in ((-1, (-tw, -twi)), (1, (tw, twi))):
        quad([(-hl, R * math.sin(to), R * math.cos(to)), (hl, R * math.sin(to), R * math.cos(to)), (hl, RI * math.sin(ti), RI * math.cos(ti)), (-hl, RI * math.sin(ti), RI * math.cos(ti))])
    m = UsdGeom.Mesh.Define(stage, "/World/Ship/pez_jambs"); m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, p)) for p in pts])); m.CreateFaceVertexCountsAttr(Vt.IntArray(cnt)); m.CreateFaceVertexIndicesAttr(Vt.IntArray(idx))
    m.CreateSubdivisionSchemeAttr("none"); m.CreateDoubleSidedAttr(True); UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat_out)
    # end discs (schematic closure of the 60 m tube)
    for nm, x in (("aft", x0), ("fwd", x1)):
        n = 64; ring = [(x, R * math.sin(2 * math.pi * k / n), R * math.cos(2 * math.pi * k / n)) for k in range(n)]
        d = UsdGeom.Mesh.Define(stage, f"/World/Ship/pez_cap_{nm}"); d.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, p)) for p in ring])); d.CreateFaceVertexCountsAttr(Vt.IntArray([n])); d.CreateFaceVertexIndicesAttr(Vt.IntArray(list(range(n))))
        d.CreateSubdivisionSchemeAttr("none"); d.CreateDoubleSidedAttr(True); UsdShade.MaterialBindingAPI.Apply(d.GetPrim()).Bind(mat_out)
    print(f"PEZ ship built: slot {PR.SLOT_W} x {PR.SLOT_H} m, hull r {R}, bay r {RI}", flush=True)
