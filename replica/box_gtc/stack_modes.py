# t438 derisk (c): first-mode ESTIMATE of the stowed stack (our satellites only) vs the SpaceX Falcon payload-guide frequency recommendations.
# Model = the t436b load-path posts (same Areq sizing: 6 g x FS 1.25 at 241 MPa, 3 columns, 4 posts/sat) treated as the axial spring chain; lateral = bending of the same posts (outer posts at +-arm/2) + a story shear stiffness that is NOT designed in the replica.
# ESTIMATE only. Base assumed rigid (upper bound: no dispenser / Starship adapter compliance), satellite bodies rigid masses, posts only. No coupled-loads analysis.
import json, math, pathlib, numpy as np, scipy.linalg as sl
g = 9.81; E = 68.9e9; G = 26e9; sig = 241e6; fs = 1.25
def areq(N, msat, cols=3, axial_g=6.0, lat2=(3.5, 2.0), plan=(6.75, 1.25), H_level=0.76, adapt=0.05, gap=0.02):
    L = math.ceil(N / cols); pitch = H_level + adapt + gap; A = []
    for k in range(1, L + 1):
        above = (L - k + 1) * msat; Pk = above * g * axial_g * fs
        Mo = (cols * above) * g * lat2[1] * ((L - k + 1) * pitch / 2); dP = Mo / (cols * plan[0]) * fs
        A.append(max(Pk, above * g * lat2[0] * fs + dP) / sig)
    return L, pitch, np.array(A)
def axial(N, msat, **kw):
    L, pitch, A = areq(N, msat, **kw); h = kw.get("H_level", 0.76)
    k = E * A / h; K = np.zeros((L, L))
    for i in range(L):
        K[i, i] += k[i]
        if i: K[i, i] += 0;  
    K = np.zeros((L, L))
    for i in range(L):                                   # spring i joins mass i to mass i-1 (mass -1 = ground)
        K[i, i] += k[i]
        if i: K[i - 1, i - 1] += k[i]; K[i, i - 1] -= k[i]; K[i - 1, i] -= k[i]
    w = sl.eigh(K, np.diag([msat] * L), eigvals_only=True); return float(np.sqrt(w[0]) / 2 / math.pi)
def lateral(N, msat, ks_story=None, cols=3, plan=(6.75, 1.25), **kw):
    L, pitch, A = areq(N, msat, cols=cols, plan=plan, **kw)
    EI = E * cols * A * (plan[0] / 2) ** 2               # bending stiffness of the post group at each level
    nn = L + 1; K = np.zeros((2 * nn, 2 * nn)); M = np.zeros(2 * nn)
    for e in range(L):
        h = pitch; ei = EI[e]
        if ks_story is None: phi = 0.0
        else: phi = 12 * ei / (ks_story * h * h)         # Timoshenko, story shear stiffness ks [N/m]
        c = ei / ((1 + phi) * h ** 3)
        ke = c * np.array([[12, 6 * h, -12, 6 * h], [6 * h, (4 + phi) * h * h, -6 * h, (2 - phi) * h * h], [-12, -6 * h, 12, -6 * h], [6 * h, (2 - phi) * h * h, -6 * h, (4 + phi) * h * h]])
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]; K[np.ix_(idx, idx)] += ke
    for i in range(1, nn): M[2 * i] = cols * msat; M[2 * i + 1] = cols * msat * (plan[1] ** 2 + 0.76 ** 2) / 12 * 0   # no rotary inertia (upper-bound frequency)
    ui = [2 * i for i in range(1, nn)]; ti = [2 * i + 1 for i in range(1, nn)]   # base node fixed; condense out the massless rotations exactly
    Kuu = K[np.ix_(ui, ui)]; Kut = K[np.ix_(ui, ti)]; Ktt = K[np.ix_(ti, ti)]
    Kr = Kuu - Kut @ np.linalg.solve(Ktt, Kut.T)
    w = sl.eigh(Kr, np.diag(M[ui]), eigvals_only=True); return float(np.sqrt(max(w[0], 0)) / 2 / math.pi)
def req_story_shear(N, msat, target=10.0, **kw):
    lo, hi = 1e5, 1e12
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if lateral(N, msat, ks_story=mid, **kw) < target: lo = mid
        else: hi = mid
    return hi
R = {}
for b, N, ms in (("Jun", 46, 2130.4348), ("Aug", 30, 3266.6667)):
    L, pitch, A = areq(N, ms)
    fa = axial(N, ms); fl = lateral(N, ms); sa = (25 / fa) ** 2; sl_ = (10 / fl) ** 2
    mposts = 3 * sum(A * 0.76 * 2700 * 1.5) / N      # kg per sat, posts only (t436b formula, joint factor 1.5)
    R[b] = dict(N=N, levels=L, stack_height_m=round(L * pitch, 2), stack_mass_t=round(N * ms / 1e3, 1), post_area_base_cm2_per_column=round(A[0] * 1e4, 1),
                axial_f1_Hz_rigid_base_strength_sized_posts=round(fa, 1), lateral_f1_Hz_post_bending_only_rigid_shear=round(fl, 1),
                post_stiffness_scale_for_25Hz_axial=round(sa, 1), post_stiffness_scale_for_10Hz_lateral_bending_only=round(sl_, 1),
                post_mass_kg_per_sat_strength_sized=round(mposts, 1), post_mass_kg_per_sat_if_scaled_for_25Hz=round(mposts * sa, 0), post_mass_kg_per_sat_if_scaled_for_10Hz_lat=round(mposts * sl_, 0),
                margin_line_kg_per_sat=345.38 if b == "Jun" else 535.05)
R["recommendation_STATEMENT"] = "SpaceX Falcon Payload User's Guide (2025-05-09 and 2021-09 editions): primary lateral > 10 Hz, primary axial > 25 Hz, secondary structure > 35 Hz (a recommendation; payloads below it 'can be accommodated' with mission-specific loads). Written for payloads of ~1.8-9 t (Rev 2 text); a 98 t stack is far outside that range. The Starship Payload User's Guide v1 gives load factors only and states no frequency requirement (so applying 10/25 Hz to Starship is an ASSUMPTION)."
R["label"] = "ESTIMATE: posts-only axial spring chain, rigid base and bodies (upper-bound frequency); lateral = post-group bending plus an undesigned shear path; not a coupled-loads analysis"
json.dump(R, open(pathlib.Path(__file__).resolve().parent / "results/t438/stack_modes.json", "w"), indent=1); print(json.dumps(R, indent=1))

# ---- t438b: same chain on the ACTUAL packed layer sequence (replica_scene_adapter output): effective columns = N/levels, mean level height from the packed stack top (packed Aug uses 2 sats per level, not 3: 18 levels, 16.5 m)
RR = {}
for b, N, ms in (("Jun", 46, 2130.4348), ("Aug", 30, 3266.6667)):
    pk = json.load(open(pathlib.Path(__file__).resolve().parent / f"results/t438/scene/{b}/fleet_pack_replica_{b}.json"))["layers"]
    Lr = len(pk); top = pk[-1]["z0"] + pk[-1]["H"]; ce = N / Lr; hl = top / Lr - 0.07
    kw = dict(cols=ce, H_level=hl)
    fa = axial(N, ms, **kw); fl = lateral(N, ms, **kw); L, pitch, A = areq(N, ms, **kw)
    RR[b] = dict(N=N, levels=Lr, stack_top_m=round(top, 2), eff_cols=round(ce, 2), axial_f1_Hz=round(fa, 1), lateral_f1_Hz_bending_only=round(fl, 1),
                 post_stiffness_scale_for_25Hz_axial=round((25 / fa) ** 2, 1), post_stiffness_scale_for_10Hz_lateral=round((10 / fl) ** 2, 1), post_mass_kg_per_sat_strength_sized=round(ce * sum(A * hl * 2700 * 1.5) / N, 1))
R["actual_packed_stack_t438b"] = RR
json.dump(R, open(pathlib.Path(__file__).resolve().parent / "results/t438/stack_modes.json", "w"), indent=1); print(json.dumps(RR, indent=1))
