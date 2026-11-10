"""Chunk wrapper: verbatim gpu_core.sweep body with i = wp.tid() + off, writing out[i - off]. All physics via gpu_core @wp.func."""
import warp as wp
from gpu_core import temperatures, mass, radiator_mass
@wp.kernel
def sweep_off(p: wp.array(dtype=wp.float64), fe: wp.array(dtype=wp.float64), cool: wp.array(dtype=wp.float64), tab: wp.array(dtype=wp.float64), out: wp.array2d(dtype=wp.float64), off: int):
    j = wp.tid()
    i = j + off
    ai = i % 64
    ti = i // 64 % 64
    nti = i // 4096 % 9
    ni = i // 36864
    n = wp.float64(112 + ni)
    nt = wp.float64(6 + nti)
    L = (wp.float64(0.3634175776637853) / nt - wp.float64(0.008)) / wp.float64(2.0)
    t = wp.float64(0.0001) + wp.float64(ti) * wp.float64(6.349206349206349e-06)
    arr = p[31] * (wp.float64(1.0) + wp.float64(ai) * wp.float64(0.0006349206349206349))
    pavail = (arr + wp.float64(1e-06)) * p[16] * wp.float64(0.92) - wp.float64(2000.0) - p[17]
    T = temperatures(n, L, t, wp.float64(0.92), wp.float64(14.22), wp.float64(18.0), wp.float64(0.92), wp.float64(20.0), wp.float64(1.0), wp.float64(1.0), wp.float64(1.0), wp.float64(1.0), wp.float64(167.0), p, fe, tab, wp.float64(1.), wp.float64(1.), wp.float64(1.))
    m = mass(n, L, t, arr, p, cool)
    hard = wp.float64(0.0)
    design = wp.float64(0.0)
    if n <= p[34] and arr <= p[31] + wp.float64(1e-06) and pavail >= p[43] and (m <= wp.float64(3266.6666666666665)) and (T[0] <= wp.float64(370.0)) and (T[2] <= wp.float64(393.0)):
        hard = wp.float64(1.0)
    if hard > wp.float64(0.5) and T[0] <= p[32] and (T[2] <= p[33]):
        design = wp.float64(1.0)
    out[j, 0] = m
    out[j, 1] = T[0]
    out[j, 2] = T[1]
    out[j, 3] = T[2]
    out[j, 4] = n
    out[j, 5] = nt
    out[j, 6] = L
    out[j, 7] = t
    out[j, 8] = arr
    out[j, 9] = hard
    out[j, 10] = design
    out[j, 11] = radiator_mass(n, L, t)
