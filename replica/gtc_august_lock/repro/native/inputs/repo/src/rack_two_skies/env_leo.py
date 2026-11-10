"""LEO environmental heat load on a flat radiator face by quadrature over the Earth sphere.

Earth is a Lambertian sphere of radius R. A face with unit normal n at orbital radius r sees the
visible cap (u.s > R/r); irradiance from a surface element is  M/pi * cos(theta_plate) cos(theta_earth) dA / d^2.
Earth IR exitance M_IR is uniform; albedo is  a * E_sun * max(u.sun, 0) / pi  (Lambertian, a = albedo).
Radiator normal is perpendicular to nadir: beta < 45 deg -> n = orbit normal; beta >= 45 deg (dawn-dusk) -> n = along-track.
[t359] CORRECTION of the earlier wording "perpendicular to nadir (and to the sun)": the normal is perpendicular to nadir, but the Sun is NOT in the radiator
plane except at beta = 90 deg. With the Sun unit vector s = (cos b cos phi, cos b sin phi, sin b) in the orbit frame (phi = orbit angle from the Sun-projection) the along-track
normal gives s.n = cos(b) sin(phi): the Sun leaves the radiator plane by up to 90 deg - beta (31 deg at beta 59, 10.5 deg orbit-mean), so the face sees a direct-sun load that the
albedo / Earth-IR quadrature below does not contain. It is provided by direct_sun_g() and added in the thermal Monte Carlo (q_dir = f_g alpha S g(beta)); q_env() keeps its old
meaning (albedo + Earth IR only) unless direct=True is passed. Orbit-averaged values include the eclipse (zero albedo, zero direct sun).
"""
from __future__ import annotations

import math

import numpy as np

R_EARTH_KM = 6371.0


def _cap_quadrature(r, R, n_theta=400, n_phi=400):
    """Quadrature nodes on the visible Earth cap about nadir. Returns unit vectors (relative to nadir axis z'),
    area weights [R^2 sr] and distances d."""
    th_max = math.acos(R / r)                          # Earth-centre angle to the horizon point
    th = (np.arange(n_theta) + 0.5) / n_theta * th_max
    ph = (np.arange(n_phi) + 0.5) / n_phi * 2 * math.pi
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    dA = R * R * np.sin(TH) * (th_max / n_theta) * (2 * math.pi / n_phi)
    return TH, PH, dA


def view_factor_nadir_plate(h_km=550.0, n=2000):
    """View factor of a plate facing nadir to the Earth (analytic: sin^2 rho = (R/r)^2)."""
    R, r = R_EARTH_KM, R_EARTH_KM + h_km
    TH, PH, dA = _cap_quadrature(r, R, n, 8)
    pts = np.stack([R * np.sin(TH) * np.cos(PH), R * np.sin(TH) * np.sin(PH), R * np.cos(TH)], -1)
    s = np.array([0, 0, r])
    d = pts - s
    dn = np.linalg.norm(d, axis=-1)
    cos_p = -d[..., 2] / dn                              # plate normal toward Earth (-z)
    u = pts / R
    cos_e = -(u * d).sum(-1) / dn
    return float(((cos_p * cos_e * dA / dn**2).sum()) / math.pi)


def face_irradiance(n_vec, s_vec, sun_vec, r, R=R_EARTH_KM, n_theta=300, n_phi=300):
    """(F_earth, albedo_geometry) for one satellite position.
    n_vec: plate normal, s_vec: satellite position unit vector (Earth-centred), sun_vec: unit vector to Sun.
    F_earth = view factor of the plate to the Earth; albedo_geometry = integral of max(u.sun,0)*kernel/pi
    (multiply by albedo * E_sun)."""
    nadir = -s_vec
    # orthonormal frame about nadir
    a = np.array([1.0, 0, 0]) if abs(nadir[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(nadir, a); e1 /= np.linalg.norm(e1); e2 = np.cross(nadir, e1)
    TH, PH, dA = _cap_quadrature(r, R, n_theta, n_phi)
    # Earth-centre angle theta measured from the sub-satellite point
    u = (np.cos(TH)[..., None] * s_vec + np.sin(TH)[..., None] * (np.cos(PH)[..., None] * e1 + np.sin(PH)[..., None] * e2))
    d = R * u - r * s_vec
    dn = np.linalg.norm(d, axis=-1)
    cos_p = np.clip((d @ n_vec) / dn, 0, None)
    cos_e = np.clip(-(u * d).sum(-1) / dn, 0, None)
    k = cos_p * cos_e * dA / dn**2 / math.pi
    lit = np.clip(u @ sun_vec, 0, None)
    return float(k.sum()), float((k * lit).sum())


def orbit_average(beta_deg, h_km=550.0, n_orbit=72, **kw):
    """Orbit-averaged (F_earth, albedo_geometry) for a face with normal perpendicular to nadir and sun."""
    R = R_EARTH_KM; r = R + h_km
    b = math.radians(beta_deg)
    sun = np.array([math.cos(b), 0.0, math.sin(b)])
    Fs, As = [], []
    for phi in (np.arange(n_orbit) + 0.5) / n_orbit * 2 * math.pi:
        s = np.array([math.cos(phi), math.sin(phi), 0.0])
        n = np.array([0.0, 0.0, 1.0]) if beta_deg < 45 else np.array([-math.sin(phi), math.cos(phi), 0.0])
        F, A = face_irradiance(n, s, sun, r, **kw)
        # eclipse: satellite behind the Earth as seen from the Sun
        along = s * r @ sun
        eclipsed = along < 0 and np.linalg.norm(s * r - along * sun) < R
        Fs.append(F); As.append(0.0 if eclipsed else A)
    return float(np.mean(Fs)), float(np.mean(As))


def q_env(beta_deg, h_km=550.0, M_IR=239.0, albedo=0.30, E_sun=1368.0, alpha_sol=0.2, eps_ir=0.9, direct=False, f_g=1.0, **kw):
    """Absorbed environmental flux per radiating face [W/m^2] and its parts.  direct=False (default) = albedo + Earth IR only (the earlier, logged meaning);
    direct=True [t359] adds the radiator-plane direct-sun load f_g alpha E_sun g(beta) (see direct_sun_g) and reports it as direct_W_m2."""
    F, Ag = orbit_average(beta_deg, h_km, **kw)
    ir = M_IR * F
    alb = albedo * E_sun * Ag
    out = dict(F_earth=F, ir_W_m2=ir, albedo_W_m2=alb, q_env=eps_ir * ir + alpha_sol * alb)
    if direct:
        qd = f_g * alpha_sol * E_sun * direct_sun_g(beta_deg, h_km); out["direct_W_m2"] = qd; out["q_env"] += qd
    return out


def direct_sun_g(beta_deg, h_km=550.0, n_orbit=2880):
    """[t359] Orbit-mean geometric direct-sun factor per radiating face for the along-track radiator normal (dawn-dusk, beta >= 45 deg):
    g(beta) = 0.5 * mean_phi( cos(beta) |sin(phi)| * sunlit(phi) ).  The 0.5 splits the plane-projected load over the two radiating faces (the same convention as the existing
    0.5 alpha S sin(pointing) term of the Monte Carlo).  Absorbed flux per face = f_g * alpha * E_sun * g(beta); f_g = 1 means the absorptance does not fall off at grazing incidence
    (ASSUMED, conservative: white-paint alpha(theta) at grazing angles is not measured for our coating).  Eclipse (sr < 0 and perpendicular distance < R) excluded.
    g(59) = 0.144, g(75) = 0.082, g(89) = 0.0056.  beta < 45 deg uses the orbit normal as plate normal and is not modelled here (the design orbit is dawn-dusk)."""
    R = R_EARTH_KM + 0.0; a = R_EARTH_KM + h_km
    b = math.radians(beta_deg)
    phi = (np.arange(n_orbit) + 0.5) / n_orbit * 2 * math.pi
    sr = a * math.cos(b) * np.cos(phi)
    perp = np.sqrt(np.maximum(a * a - sr * sr, 0.0))
    lit = ~((sr < 0) & (perp < R))
    return float(0.5 * np.mean(math.cos(b) * np.abs(np.sin(phi)) * lit))
