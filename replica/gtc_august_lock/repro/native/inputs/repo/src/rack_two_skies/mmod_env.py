"""MMOD environment and ballistic-limit formulas (t189 item 6). IDEALIZED paper formulas from the SPENVIS background page
(https://www.spenvis.eu/help/background/metdeb/metdeb.html): Gruen 1985 meteoroids, NASA90 debris (OUTDATED, ORDEM/MASTER not run),
single-wall thin-plate and Cour-Palais double-wall ballistic limits. Units: cm, g, km/s unless named otherwise."""
import math

import numpy as np

RE = 6378.0
# ---- meteoroids -------------------------------------------------------------------------------
def gruen(m_g):
    """Cumulative flux of mass >= m [g] at 1 AU, m^-2 yr^-1 (Gruen 1985, SPENVIS form)."""
    f1 = (2.2e3 * m_g ** 0.306 + 15.0) ** -4.38
    f2 = 1.3e-9 * (m_g + 1e11 * m_g ** 2 + 1e27 * m_g ** 4) ** -0.36
    f3 = 1.3e-16 * (m_g + 1e6 * m_g ** 2) ** -0.85
    return 3.15576e7 * (f1 + f2 + f3)


def earth_factor(h_km):
    s = (RE + 100.0) / (RE + h_km)
    xi = 0.5 * (1 + math.cos(math.asin(s)))
    ge = 1 + s
    return xi * ge


def rho_met(m_g):
    return 2.0 if m_g < 1e-6 else (1.0 if m_g <= 1e-2 else 0.5)


# ---- debris -----------------------------------------------------------------------------------
PSI = [(28.5, .91), (30, .92), (40, .96), (50, 1.02), (60, 1.09), (70, 1.26), (80, 1.71), (90, 1.37), (100, 1.78), (120, 1.18)]


def psi(i):
    xs, ys = zip(*PSI)
    return float(np.interp(i, xs, ys))


def nasa90(d_cm, h_km, inc, year, S):
    p, q = 0.05, 0.04
    H = 10 ** (0.5 * math.exp(-((math.log10(d_cm) - 0.78) ** 2) / 0.406))
    phi1 = 10 ** (h_km / 200.0 - S / 140.0 - 1.5)
    phi = phi1 / (1 + phi1)
    F1 = 1.22e-5 * d_cm ** -2.5
    F2 = 8.1e10 * (d_cm + 700.0) ** -6
    g1 = (1 + q) ** (year - 1988)
    g2 = 1 + p * (year - 1988)
    return H * phi * psi(inc) * (F1 * g1 + F2 * g2)


# ---- ballistic limit ---------------------------------------------------------------------------
def d_lim_cm(t_cm, rho_p, v_kms, cosa=1.0, K1=0.44):
    return (t_cm / (K1 * rho_p ** 0.519 * v_kms ** 0.875 * cosa ** 0.875)) ** (1 / 1.056)


def solve_t_for_d(d_cm, rho_p, v_kms, cosa=1.0, K1=0.44):
    return d_cm ** 1.056 * K1 * rho_p ** 0.519 * v_kms ** 0.875 * cosa ** 0.875


# ---- Whipple (double-wall) option: Cour-Palais form of SPENVIS Table 6 ---------------------------
# d_lim = t_b / (K1 rho_p^0.5 v rho_b^0.167 S^-0.5), K1 = 0.044 (482.8 MPa / sigma_y_back)^0.5 ; t_b, S in cm, v in km/s.
SIGMA_BACK_MPA = 241.0   # 6061-T6 minimum yield (ESTIMATE of the tube temper)


def d_lim_whipple_cm(t_b_cm, S_cm, rho_p, v):
    K1 = 0.044 * (482.8 / SIGMA_BACK_MPA) ** 0.5
    return t_b_cm / (K1 * rho_p ** 0.5 * v * 2.7 ** 0.167 * S_cm ** -0.5)




def whipple(h_km, inc, year, S, t_b_mm, t_s_mm, geom, theta_deg=30.0, T_yr=5.0, S10=1.5):
    """Tube wall t_b behind a strip bumper t_s at standoff S [mm]. geom: n_tubes_per_panel, tube_width_m, panel_L_m, n_panels.
    Debris at 10 km/s (rho 2.8), meteoroids at 20 km/s (Gruen density); both normal incidence; tumbling-plate flux (conservative for a plate
    whose plane contains the velocity vector). Bumper strip width = tube width + 2 S tan(theta) (covers +-theta obliquity)."""
    A = geom["n_tubes_per_panel"] * geom["tube_width_m"] * geom["panel_L_m"] * geom["n_panels"] * 2  # both faces
    d = d_lim_whipple_cm(t_b_mm / 10, S / 10, 2.8, 10.0)
    fd = nasa90(d, h_km, inc, year, S10)
    rho = 1.0
    for _ in range(20):
        dm = d_lim_whipple_cm(t_b_mm / 10, S / 10, rho, 20.0)
        m = rho * math.pi / 6 * dm ** 3
        rho = rho_met(m)
    fm = gruen(m) * earth_factor(h_km)
    N = (fd + fm) * A * T_yr
    n_tubes = geom["n_tubes_per_panel"] * geom["n_panels"]
    strip_w = geom["tube_width_m"] + 2 * (S / 1000.0) * math.tan(math.radians(theta_deg))
    area = n_tubes * geom["panel_L_m"] * 2 * strip_w
    mass = area * (t_s_mm / 1000.0) * 2700.0
    return dict(S_mm=S, t_b_mm=t_b_mm, t_s_mm=t_s_mm, d_lim_debris_mm=d * 10, d_lim_met_mm=dm * 10, t_s_over_d=t_s_mm / (d * 10),
                A_tube_m2=A, N_5yr=N, P_no_pen=math.exp(-N), panels_hit_fraction=1 - math.exp(-N / geom["n_panels"]),
                bumper_strip_width_mm=strip_w * 1e3, bumper_area_m2=area, bumper_mass_kg=mass)
