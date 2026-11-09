"""View factor from a radiator panel face to the solar-array back face (P6, docs/PLAN_3D_IDEALIZED.md): EXACT, not Monte Carlo.

Geometry (deployed frame of assembly3d.py, metres): a radiator panel lies in the plane x = 0 and its face normal is +x (the -x face is the mirror
image and has the same view factor). The array is a set of axis-aligned rectangles in horizontal planes z = z_r:  x in [x0, x1], y in [ya, yb], with
x0 > 0, so every array vertex is in front of the face (no clipping needed).

Exact formula (Nusselt contour integral for a polygon seen from a differential area dA with unit normal n):
    F(dA -> polygon) = 1/(2 pi) * sum_edges  theta_i  (n . ghat_i),    ghat_i = (v_i x v_{i+1}) / |v_i x v_{i+1}|,    theta_i = angle(v_i, v_{i+1})
with v_i = vertex_i - point. One Warp thread per point, float64, each thread writes its own output (no atomic adds): the result is bit-for-bit
repeatable on the GPU and smooth in every geometric parameter, so finite differences of it are clean to ~1e-9.
Occlusion by the bus and the mast is NOT modelled (declared in docs/CAD_3D.md); the array is treated as an opaque grey wall at T_arr.

A Monte Carlo kernel (cosine-weighted rays from the point, fixed seed) is provided ONLY to validate the exact kernel and to quantify the noise a
Monte Carlo view factor would put into the optimiser gradients (docs/CAD_3D.md, section P6). It is not used in the optimisation.
"""
from __future__ import annotations

import numpy as np
import warp as wp

wp.config.quiet = True
f64 = wp.float64
PI = 3.141592653589793


@wp.kernel
def _vf_exact(py: wp.array(dtype=f64), pz: wp.array(dtype=f64), rects: wp.array2d(dtype=f64), F: wp.array(dtype=f64)):
    """rects[r] = (x0, x1, ya, yb, z). Point = (0, py, pz), normal +x."""
    i = wp.tid()
    tot = f64(0.0)
    for r in range(rects.shape[0]):
        x0 = rects[r, 0]
        x1 = rects[r, 1]
        ya = rects[r, 2]
        yb = rects[r, 3]
        zr = rects[r, 4]
        # vertices in counter-clockwise order seen from +z (above): the sign is fixed by taking the absolute value of the sum
        v0 = wp.vec3d(x0, ya - py[i], zr - pz[i])
        v1 = wp.vec3d(x1, ya - py[i], zr - pz[i])
        v2 = wp.vec3d(x1, yb - py[i], zr - pz[i])
        v3 = wp.vec3d(x0, yb - py[i], zr - pz[i])
        s = f64(0.0)
        for e in range(4):
            a = v0
            b = v1
            if e == 1:
                a = v1
                b = v2
            if e == 2:
                a = v2
                b = v3
            if e == 3:
                a = v3
                b = v0
            c = wp.cross(a, b)
            cn = wp.length(c)
            if cn > f64(1e-300):
                th = wp.atan2(cn, wp.dot(a, b))
                s = s + th * c[0] / cn            # n = (1, 0, 0)
        tot = tot + wp.abs(s) / (f64(2.0) * f64(3.141592653589793))
    F[i] = tot


def exact(py, pz, rects, device="cpu"):
    """F for every point (py[i], pz[i]) to the sum of rectangles ``rects`` (n,5). Returns a float64 numpy array."""
    py = np.ascontiguousarray(py, np.float64).ravel()
    pz = np.ascontiguousarray(pz, np.float64).ravel()
    r = np.ascontiguousarray(np.atleast_2d(rects), np.float64)
    out = wp.zeros(py.size, dtype=f64, device=device)
    wp.launch(_vf_exact, py.size, [wp.array(py, dtype=f64, device=device), wp.array(pz, dtype=f64, device=device), wp.array(r, dtype=f64, device=device), out], device=device)
    return out.numpy()

