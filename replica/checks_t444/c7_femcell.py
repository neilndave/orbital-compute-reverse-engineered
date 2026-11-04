# t444 check 7c: warp.fem hex (trilinear, fp64) solid model of ONE representative post (square section) clamped at its base:
# axial stiffness EA/h and cantilever tip stiffness 3EI/h^3 vs closed-form. Same warp.fem path as NVIDIA's cantilever example (Grid3D, integrate, project_linear_system, bsr_cg). ESTIMATE.
import json, time, numpy as np, warp as wp, warp.fem as fem
from warp.examples.fem import utils as U
wp.config.quiet = True
E=68.9e9; NU=0.33; H=0.823; AREA=75e-4   # ASSUMED: base post group area 300 cm2 (Jun kept) split into 4 posts -> 75 cm2 each
S=AREA**0.5
@wp.func
def hooke(strain: wp.mat33d, lame: wp.vec2d):
    return wp.float64(2.0)*lame[1]*strain + lame[0]*wp.trace(strain)*wp.identity(n=3, dtype=wp.float64)
@fem.integrand
def k_form(s: fem.Sample, u: fem.Field, v: fem.Field, lame: wp.vec2d):
    return wp.ddot(fem.D(v, s), hooke(fem.D(u, s), lame))
@fem.integrand
def clamp_form(s: fem.Sample, domain: fem.Domain, u: fem.Field, v: fem.Field, zc: wp.float64):
    x = fem.position(domain, s)
    if x[2] <= zc: return wp.dot(u(s), v(s))
    return wp.float64(0.0)
@fem.integrand
def load_form(s: fem.Sample, domain: fem.Domain, v: fem.Field, zl: wp.float64, tr: wp.vec3d):
    x = fem.position(domain, s)
    if x[2] >= zl: return wp.dot(v(s), tr)
    return wp.float64(0.0)
def solve(n, nz, dirn, F=1.0e4):
    geo = fem.Grid3D(res=wp.vec3i(n, n, nz), scalar_type=wp.float64, bounds_lo=wp.vec3d(0,0,0), bounds_hi=wp.vec3d(S, S, H))
    cells = fem.Cells(geometry=geo); quad = fem.RegularQuadrature(cells, order=2)
    sp = fem.make_polynomial_space(geo, degree=1, dtype=wp.vec3d); part = fem.make_space_partition(sp.topology, with_halo=False)
    test = fem.make_test(space=sp, space_partition=part, domain=cells); trial = fem.make_trial(space=sp, space_partition=part, domain=cells)
    lame = wp.vec2d(E*NU/((1+NU)*(1-2*NU)), E/(2*(1+NU)))
    K = fem.integrate(k_form, quadrature=quad, fields={"u": trial, "v": test}, values={"lame": lame}, output_dtype=wp.float64)
    bd = fem.BoundarySides(geo); bt = fem.make_test(space=sp, space_partition=part, domain=bd); btr = fem.make_trial(space=sp, space_partition=part, domain=bd)
    dz = H/nz
    P = fem.integrate(clamp_form, fields={"u": btr, "v": bt}, values={"zc": 0.25*dz}, assembly="nodal", output_dtype=wp.float64); fem.normalize_dirichlet_projector(P)
    tr = wp.vec3d(0,0,-F/AREA) if dirn=="axial" else wp.vec3d(F/AREA,0,0)
    b = fem.integrate(load_form, fields={"v": bt}, values={"zl": H-0.25*dz, "tr": tr}, output_dtype=wp.vec3d)
    fem.project_linear_system(K, b, P, normalize_projector=False)
    x = wp.zeros_like(b); r, it = U.bsr_cg(K, b=b, x=x, max_iters=20000, tol=1e-10, quiet=True)
    xs = x.numpy(); pos = sp.node_positions().numpy()
    return xs, pos, int(it), K.nrow
res = {}
for dirn in ("axial", "bending"):
    for (n, nz) in ((2, 16), (4, 32), (6, 48)):
        t0 = time.time(); xs, pos, it, nd = solve(n, nz, dirn); dt = time.time()-t0
        if pos is None: raise SystemExit("no vertex positions")
        top = pos[:,2] > H-1e-9
        if dirn == "axial": d = float(-xs[top,2].mean()); ana = 1e4*H/(E*AREA)
        else: d = float(xs[top,0].mean()); ana = 1e4*H**3/(3*E*(S**4/12))
        res[f"{dirn}_{n}x{n}x{nz}"] = dict(fem_disp_m=d, closed_form_m=ana, ratio=d/ana, cg_iters=it, nodes=nd, secs=round(dt,2)); print(dirn, n, nz, res[f"{dirn}_{n}x{n}x{nz}"], flush=True)
json.dump(res, open("c7_femcell.json","w"), indent=1)
