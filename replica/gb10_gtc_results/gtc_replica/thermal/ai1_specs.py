"""AI1 / Starmind replica: shared constants and build specs (pure Python, no GPU).
Labels: STATEMENT = quoted public number or exact arithmetic on one; ESTIMATE = our model output; INFERENCE = derived by us from a statement;
ASSUMED = a choice we made because SpaceX has not said (always swept or flagged). Sources are in PLAN.md sec. 1-3."""
import math
SIG = 5.670374419e-8                    # W/m2/K4, CODATA 2018
T_C = 273.15
# ---------- SpaceX stated builds ----------
JUN8 = dict(name="Jun8", P_peak_W=150e3, P_avg_W=120e3, kw_per_t=70.0, A_arr_m2=600.0, A_rad_m2=110.0,
            flux_planform_Wm2=1400.0, wing_len_m=30.0, wing_wid_m=9.8, wing_gap_m=9.9, span_m=70.0, array_Wm2=250.0,
            label="STATEMENT (Jun 8 slide; arrays 590 m2 measured in drawing)")
AUG4 = dict(name="Aug4", P_peak_W=250e3, P_avg_W=175e3, kw_per_t=75.0, A_arr_m2=1000.0, A_rad_m2=250e3/1400.0,
            flux_planform_Wm2=1400.0, wing_len_m=30.0, wing_wid_m=1000.0/60.0, wing_gap_m=9.9, span_m=75.0, array_Wm2=250.0,
            label="STATEMENT for 250 kW, 1,000 m2, 75 m span, 75 kW/t; radiator area is ASSUMED (Jun 8 flux 1,400 W/m2 per planform m2)")
# ---------- mass model (repo values) ----------
RACK_KG = 1814.0                        # 4,000 lb stock NVL72 rack (STATEMENT, docs/BOUNDS.md; The Register)
SIGMA_ARR = 3.197                       # kg per array m2 (adopted baseline, DECISIONS row 83)
SIGMA_RAD_PLAN = 7.1                    # kg per radiator planform m2 both faces (INFERENCE, likely a low bound; docs/MASS_CLAIMS.md)
# ---------- environment (repo env_leo, 550 km dawn-dusk, per radiating face) ----------
Q_ABS_FACE = 57.0                       # W/m2 absorbed per face (ESTIMATE, repo q_env; 56-59 W/m2)
S_MEAN = 1367.0
# ---------- fin / radiator design variables (ASSUMED) ----------
K_AL = 167.0                            # W/m/K, 6061-T6 near 370 K (ASSUMED handbook value)
RHO_AL = 2700.0
TUBE_OD_M = 0.008                       # ASSUMED
TUBE_WALL_M = 0.0005                    # ASSUMED
FLUID_RHO = 1030.0                      # kg/m3, water-glycol-ish (ASSUMED)
FIN_DESIGNS = {                         # half-width of fin from tube edge L [m], sheet thickness t [m]
    "F1_L60_t0p8": dict(L=0.060, t=0.0008),
    "F2_L80_t1p0": dict(L=0.080, t=0.0010),
    "F3_L40_t0p5": dict(L=0.040, t=0.0005),
}
TB_GRID = [320.0 + 10.0 * i for i in range(0, 11)]        # 320..420 K mean tube temperature
EE_GRID = [0.60, 0.70, 0.80, 0.90, 0.95]                   # eps x F (effective)
TS_GRID = [150.0, 200.0, 250.0]                            # effective sink temperature [K] (about q_abs/(ee sigma))^(1/4)
LIMIT_SUPPLY_K = 370.15                 # Musk "97 C" hot-chip number used as a coolant supply cap (ASSUMED reading; repo hot97 convention)
LIMIT_70C_K = 343.15
def mass_budget_kg(P_W, kwpt): return P_W / 1000.0 / kwpt * 1000.0
def array_area_for(P_W): return P_W / 250.0
def fin_areal_mass_planform(design):
    """kg per planform m2 of sheet + tube wall + coolant for the assumed fin design (headers, mounts, shielding NOT included)."""
    L, t = design["L"], design["t"]; d = TUBE_OD_M
    cell_w = L + d / 2.0                                    # cell half width; one tube per 2*cell_w
    sheet = RHO_AL * t * L * 2.0
    tube = RHO_AL * math.pi * d * TUBE_WALL_M
    di = d - 2 * TUBE_WALL_M
    fluid = FLUID_RHO * math.pi * di * di / 4.0
    return (sheet + tube + fluid) / (2.0 * cell_w)
