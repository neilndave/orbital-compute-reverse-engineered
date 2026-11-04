# t436b: first-principles credibility checks of the four stow levers. Every number labelled in the printed table / JSON.  (ESTIMATE unless noted)
import json, math, pathlib
OUT = pathlib.Path(__file__).resolve().parent / "results/t436b"; R = {}
g = 9.81
# ---------- (1) LEAF ----------
Aarr = {"Jun": 503.9, "Aug": 839.8}; P = {"Jun": 150.0, "Aug": 250.0}; leafm2 = 14.0 * 0.89974
kwm3 = {}
for b in Aarr:
    kwm3[b] = {f"{p}mm": round(P[b] / (Aarr[b] * p / 1000), 1) for p in (2, 3, 4, 5, 6, 7.5, 9, 12)}
R["leaf_power_density_kW_per_m3_blanket_only"] = kwm3     # array kW / (A_arr x pitch): stowed leaf-stack volume only (no booms / hold-downs / margins)
pitch_eq = {k: round(P["Jun"] / (Aarr["Jun"] * v) * 1000, 2) for k, v in {"ROSA_flown_40": 40, "MegaROSA_claim_50": 50, "SOLAROSA_claim_60": 60, "SOLAROSA_claim_80": 80}.items()}
R["pitch_equivalent_mm_for_public_kW_m3"] = pitch_eq     # STATEMENT inputs (Redwire flysheet), our arithmetic
# rigid leaf sandwich: faces CFRP, core Al honeycomb
Ef = 70e9; rho_f = 1600.0; rho_core = 50.0
def sandwich(tot_mm, tf_mm=0.15, clr_mm=0.5):
    c = (tot_mm - clr_mm - 2 * tf_mm) / 1000; tf = tf_mm / 1000
    D = Ef * tf * (c + tf) ** 2 / 2            # per unit width, N m
    m = 2 * tf * rho_f + c * rho_core + 0.2    # + 0.2 kg/m2 adhesive/bonding (ASSUMED)
    return D, m, c * 1000
cells = 0.45   # kg/m2: ~150 um GaAs/Ge or Si cell + 100 um cover + interconnect on the sheet (ASSUMED range 0.35-0.6)
leaf = {}
for p in (4, 3, 2):
    D, m, c = sandwich(p); leaf[f"{p}mm"] = dict(core_mm=round(c, 2), D_Nm=round(D, 1), bare_leaf_kg_m2=round(m, 2), with_cells_kg_m2=round(m + cells, 2))
R["rigid_sandwich_leaf"] = leaf
R["replica_array_kg_m2"] = {"Jun_C1": round(484.5 / 503.9, 3), "Jun_C2": round(308.2 / 503.9, 3), "Aug_C1": round(807.6 / 839.8, 3)}
Khinge = 5e5; Lleaf = 0.89974; kh_w = Khinge / 14.0           # N m/rad per m width
R["newton_latch_K_per_m_width_Nm_rad_m"] = kh_w
R["leaf_vs_hinge_stiffness_ratio"] = {k: round((v["D_Nm"] / Lleaf) / kh_w, 4) for k, v in leaf.items()}   # leaf rotational stiffness D/L over latch stiffness per width
Dreq = Lleaf * kh_w; tf = 0.15e-3; c_req = math.sqrt(2 * Dreq / (Ef * tf)); R["core_mm_needed_for_leaf_stiff_equal_latch"] = round(c_req * 1000, 1)
R["newton_peak_hinge_Nm_public_repo_run_k5e4"] = 360.0   # repo results/phase2_T45/xcheck_motor_tdep300_dt0.004_k5e4.json peak_torque ~360 N m (old T45 baseline mass; ESTIMATE)
# flexible blanket
blanket = dict(APSA_layers_um="50 Kapton + 55 Si cell (NTRS 19890015345 / 19850053489, STATEMENT)", assumed_blanket_with_cells_um=(300, 500), assumed_spacer_um=(500, 1500))
R["flexible_blanket_pitch_mm_range_ASSUMED"] = [0.8, 2.0]
# ---------- (2) RADIATOR ----------
W = 0.3634175776637853; tube = 2 * W / 128 * 1000   # mm: repo grid rule (tube_width_cells 2 of 128); F4 check: 0.40217 -> 6.284 mm (STATEMENT in docs/P8A_LAUNCH_FEA.md)
hdr = 14.0
R["radiator"] = dict(tube_outer_mm=round(tube, 2), repo_header_mm=hdr, clearance_mm={f"{p}mm": round(p - tube, 2) for p in (5, 6, 7, 8, 10, 12, 20)})
# flat header: same flow area as the 14 mm square (wall 1.64 mm scaled from F4 1.81 mm at 6.28 mm tube)
wall = 1.8135 * tube / 6.284; A_in = (hdr - 2 * wall) ** 2
for h in (7.0, 8.0):
    Wf = A_in / (h - 2 * wall) + 2 * wall; per = 2 * (h + Wf); R["radiator"][f"flat_header_{h:g}mm_tall"] = dict(width_mm=round(Wf, 1), perimeter_ratio_vs_square=round(per / (4 * hdr), 2), panel_len_growth_mm=round(2 * (Wf - hdr), 0))
# panel sag at 6 g between pads (simply supported, 7 pad rows -> span L/6), F4-type panel (repo FEA panel EI)
E = 68.9e9; nt = 4; b = tube / 1000; t = wall / 1000; I = nt * (b**4 - (b - 2 * t)**4) / 12; Lp = 2.9446; span = Lp / 6; w_ = (168.4 / 77) / Lp * g * 6
R["radiator"]["sag_mm_6g_between_7_pad_rows_simply_supported"] = round(5 * w_ * span**4 / (384 * E * I) * 1000, 3)
R["radiator"]["sag_mm_at_2x_amp"] = round(2 * R["radiator"]["sag_mm_6g_between_7_pad_rows_simply_supported"], 3)
# ---------- (3) DENSITY ----------
dens = {"GB200 NVL72 rack (public dims 2236x600x1068 mm, ~1.36 t)": 1360 / (2.236 * 0.6 * 1.068),
        "NVL72 HPE variant (1472 kg, 2495 tall)": 1472 / (2.495 * 0.6 * 1.068),
        "DGX H100 8U (130.45 kg, 356x482.3x897.1 mm; NVIDIA docs)": 130.45 / (0.356 * 0.4823 * 0.8971),
        "Repo rack (1814 kg in 0.6x1.2x2.296)": 1814 / (0.6 * 1.2 * 2.296),
        "Starlink V2 Mini-class whole sat stowed (960 kg over ~4.1x2.7x0.3 m; 3rd-party dims, INFERENCE)": 960 / (4.1 * 2.7 * 0.3 * 1.0),
        "Repo equipment default (rho 400)": 400.0}
R["densities_kg_m3"] = {k: round(v) for k, v in dens.items()}
# what mass does the equipment slab hold? Jun C1 ledger (kg)
jun = dict(total=2130.0, array=484.5, rack=408.5, radiator=168.4, margin=345.4, mmod=137.7, adapter=62.0)
other = jun["total"] - jun["array"] - jun["rack"] - jun["radiator"]
VEQ0 = 2.982   # p27.VEQ0 (repo)
Veq = VEQ0 * (0.338 + 0.662 * 150 / 188)
R["equip_check_Jun_C1"] = dict(non_array_rack_rad_mass_kg=round(other), Veq_at_400_m3=round(Veq, 2), implied_density_if_all_boxed={rho: round(other / (Veq * 400 / rho)) for rho in (400, 600, 800)},
                               mass_excl_margin_mmod_adapter_kg=round(other - jun["margin"] - jun["mmod"] - jun["adapter"]))
# ---------- (4) LOAD PATH ----------
def loadpath(N, msat, cols=3, axial_g=6.0, lat_g=0.5, lat2=(3.5, 2.0), fs=1.25, sig=241e6, rho=2700.0, joint=1.5, plan=(6.75, 1.25), H_level=0.76, adapt=0.10, gap=0.03):
    L = math.ceil(N / cols); pitch = H_level + adapt + gap; Htot = L * pitch
    # per column: sat at level k (1=bottom) carries (L-k) sats above plus itself -> post load at bottom of level k
    mass_col = []; Areq = []
    for k in range(1, L + 1):
        above = (L - k + 1) * msat           # mass at or above the bottom of level k (incl. own)
        Pk = above * g * axial_g * fs
        # lateral combo: axial 3.5 g + lateral 2 g, overturning about base, plan arm = plane length
        Mo = (cols * above) * g * lat2[1] * ((L - k + 1) * pitch / 2)
        arm = plan[0]                        # lateral along slab length: outer posts at +-arm/2
        dP = Mo / (cols * arm) * fs          # extra post-pair force per column
        P2 = above * g * lat2[0] * fs + dP
        Areq.append(max(Pk, P2) / sig)
    m_posts = cols * sum(A * H_level * rho for A in Areq) * joint
    # tension rod for -2 g axial: rod holds all above; per column
    Trod = [((L - k + 1) * msat) * g * 2.0 * fs for k in range(1, L + 1)]
    Arod = max(Trod) / 880e6                 # Ti-6Al-4V ~880 MPa yield (ASSUMED handbook)
    m_rod = cols * (Arod * 0.5) * Htot * 4430.0     # taper ~ half
    # lateral shear pins: 2 g x mass above x fs at base
    Vb = (L * msat) * g * lat2[1] * fs; m_pins = 4 * (Vb / (0.6 * 880e6)) * 0.2 * 4430.0
    strain = sum((max(A * sig, 0) / (A * 68.9e9)) * H_level for A in Areq)   # at yield-design stress/1.25
    dz = strain / fs * 1000
    return dict(N=N, levels=L, stack_height_m=round(Htot, 2), base_post_area_cm2=round(Areq[0] * 1e4, 1), n_posts_per_sat=4, post_area_cm2_each_base=round(Areq[0] * 1e4 / 4, 1),
                post_mass_kg_total=round(m_posts, 0), rod_mass_kg_total=round(m_rod, 0), pin_mass_kg_total=round(m_pins, 0), total_added_kg=round(m_posts + m_rod + m_pins, 0),
                added_kg_per_sat=round((m_posts + m_rod + m_pins) / N, 1), stack_shortening_mm_6g=round(dz, 1), base_shear_MN=round(Vb / 1e6, 2), base_axial_MN_per_col=round(max(Areq) * sig / 1e6, 2))
R["loadpath"] = {"Jun_N46_2130kg": loadpath(46, 2130.0), "Jun_N44_2130kg": loadpath(44, 2130.0), "Aug_N30_3267kg": loadpath(30, 3267.0), "Jun_N35": loadpath(35, 2130.0), "Aug_N25": loadpath(25, 3267.0)}
R["mass_ceiling"] = {k: dict(without=math.floor(98000 / m + 1e-6), with_added=math.floor(98000 / (m + R["loadpath"][nm]["added_kg_per_sat"]))) for k, m, nm in (("Jun", 2130.4348, "Jun_N46_2130kg"), ("Aug", 3266.6667, "Aug_N30_3267kg"))}
R['margin_fraction_used'] = {k: round(R['loadpath'][nm]['added_kg_per_sat'] / mg, 3) for k, nm, mg in (('Jun', 'Jun_N46_2130kg', 345.4), ('Aug', 'Aug_N30_3267kg', 535.0))}
R["margin_lines_kg"] = {"Jun_C1": 345.4, "Aug_C1": 535.0, "adapter_line_per_sat": 62.0, "structure_line_Jun": 106.9}
json.dump(R, open(OUT / "checks.json", "w"), indent=1); print(json.dumps(R, indent=1))
