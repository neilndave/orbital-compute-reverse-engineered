# t440: iterative stack-stiffness loop. Requirement ASSUMED = Falcon Payload User's Guide style (primary axial > 25 Hz, primary lateral > 10 Hz); Starship states no equivalent number (STATEMENT).
# Levers: (A) stiffer posts / dispenser column (all post areas x kappa), (B) intermediate ties from the stack to the bay wall every s levels (axial + lateral restraint nodes; wall assumed RIGID = upper bound),
# (C) inter-satellite shear ties (lateral story shear stiffness ks), and the mass the ties themselves cost. ESTIMATE only, rigid bodies, no coupled loads.
import json, math, pathlib, numpy as np, scipy.linalg as sl
src = open(pathlib.Path(__file__).resolve().parent / "stack_modes.py").read(); exec(src[:src.index("R = {}")])      # reuse areq/axial/lateral definitions only (no file writes)
HERE = pathlib.Path(__file__).resolve().parent
def areq_t(N, msat, s, cols, H_level, adapt=0.05, gap=0.02, axial_g=6.0, lat2=(3.5, 2.0), plan=(6.75, 1.25)):
    """post area per level with ties every s levels (level index from the base, ties at levels s,2s,.. = restraint nodes): each span carries only its own sats above the post up to the next tie (wall takes the rest)."""
    L = math.ceil(N / cols); pitch = H_level + adapt + gap; A = np.zeros(L); tie = [(k % s == 0) for k in range(1, L + 1)] if s else [False] * L
    for k in range(1, L + 1):
        nxt = next((j for j in range(k, L + 1) if (s and j % s == 0)), L)       # span top
        n_above = nxt - k + 1; above = n_above * cols * msat / cols * 1.0
        n_above_m = n_above * msat
        Pk = n_above_m * g * axial_g * fs; Mo = cols * n_above_m * g * lat2[1] * (n_above * pitch / 2); dP = Mo / (cols * plan[0]) * fs
        A[k - 1] = max(Pk, n_above_m * g * lat2[0] * fs + dP) / sig
    return L, pitch, A, tie
def modes(N, msat, s, kappa, cols, H_level, ks_story=None, plan=(6.75, 1.25), keep=True):
    L, pitch, A, tie = areq_t(N, msat, s, cols, H_level)
    if keep: A = areq_t(N, msat, 0, cols, H_level)[2]      # posts unchanged (strength-sized for the FULL stack, as in t436b/t438); ties are ADDED
    A = A * kappa; h = H_level
    # axial: nodes 1..L (masses msat each, rigid satellite), node 0 = ground; ties fix node s,2s,...
    k = E * A / h; K = np.zeros((L, L))
    for i in range(L):
        K[i, i] += k[i]
        if i: K[i - 1, i - 1] += k[i]; K[i, i - 1] -= k[i]; K[i - 1, i] -= k[i]
    free = [i for i in range(L) if not tie[i]]
    wa = sl.eigh(K[np.ix_(free, free)], np.eye(len(free)) * msat, eigvals_only=True)[0]
    # lateral: beam model, tie nodes fixed in translation
    EI = E * cols * A * (plan[0] / 2) ** 2; nn = L + 1; Kb = np.zeros((2 * nn, 2 * nn)); M = np.zeros(2 * nn)
    for e in range(L):
        ei = EI[e]; phi = 0.0 if ks_story is None else 12 * ei / (ks_story * pitch ** 2); c = ei / ((1 + phi) * pitch ** 3)
        ke = c * np.array([[12, 6 * pitch, -12, 6 * pitch], [6 * pitch, (4 + phi) * pitch ** 2, -6 * pitch, (2 - phi) * pitch ** 2], [-12, -6 * pitch, 12, -6 * pitch], [6 * pitch, (2 - phi) * pitch ** 2, -6 * pitch, (4 + phi) * pitch ** 2]])
        idx = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]; Kb[np.ix_(idx, idx)] += ke
    for i in range(1, nn): M[2 * i] = cols * msat
    ui = [2 * i for i in range(1, nn) if not tie[i - 1]]; ti = [2 * i + 1 for i in range(1, nn)]
    Kuu = Kb[np.ix_(ui, ui)]; Kut = Kb[np.ix_(ui, ti)]; Ktt = Kb[np.ix_(ti, ti)]
    Kr = Kuu - Kut @ np.linalg.solve(Ktt, Kut.T); wl = sl.eigh(Kr, np.diag(M[ui]), eigvals_only=True)[0]
    return float(math.sqrt(wa) / 2 / math.pi), float(math.sqrt(max(wl, 0)) / 2 / math.pi), A, L, pitch, tie
def solve_kappa(N, msat, s, cols, hl, tax, tlat, ks=None, keep=True):
    lo, hi = 1.0, 3000.0
    if modes(N, msat, s, 1.0, cols, hl, ks, keep=keep)[0] >= tax and modes(N, msat, s, 1.0, cols, hl, ks, keep=keep)[1] >= tlat: return 1.0
    for _ in range(70):
        mid = math.sqrt(lo * hi); fa, fl, *_ = modes(N, msat, s, mid, cols, hl, ks, keep=keep)
        if fa >= tax and fl >= tlat: hi = mid
        else: lo = mid
    return hi
def tie_mass(N, msat, s, cols, A_unused, L, pitch, tie, strut_len=1.4):
    """kg per satellite of the wall ties themselves, strength-sized: each tie level carries the lateral reaction of the span it closes (3.5 g x FS) and 2x as much axial shear share as one span weight x 6 g x FS x 0.5, via 4 Al struts (lateral) + 2 shear pads; strut mass = F L/sigma x rho x 1.5 joint. ASSUMED"""
    if not s: return 0.0
    m = 0.0
    for k in range(1, L + 1):
        if not tie[k - 1]: continue
        span = s * cols * msat; Flat = span * g * 3.5 * fs; Fax = span * g * 6.0 * fs * 0.5
        m += (Flat + Fax) * strut_len / sig * 2700 * 1.5 * 2        # x2 both sides
    return m / N
BASE_MARGIN = {"Jun": 345.38, "Aug": 535.05}; USED = {"Jun": 43.5, "Aug": 100.8}
R = {}
fin = json.load(open(HERE / "results/t438/stack_modes.json"))
for b, N, ms in (("Jun", 46, 2130.4348), ("Aug", 30, 3266.6667)):
    pk = json.load(open(HERE / f"results/t438/scene/{b}/fleet_pack_replica_{b}.json"))["layers"]
    Lr = len(pk); top = pk[-1]["z0"] + pk[-1]["H"]; ce = N / Lr; hl = top / Lr - 0.07; rows = []
    base_post = ce * sum(areq_t(N, ms, 0, ce, hl)[2] * hl * 2700 * 1.5) / N
    for s in (0, 12, 8, 6, 4, 3, 2):
        for keep in ((True,) if s == 0 else (True, False)):
            k0 = modes(N, ms, s, 1.0, ce, hl, keep=keep); kax = solve_kappa(N, ms, s, ce, hl, 25.0, 0.0, keep=keep); klat = solve_kappa(N, ms, s, ce, hl, 0.0, 10.0, keep=keep); kap = solve_kappa(N, ms, s, ce, hl, 25.0, 10.0, keep=keep)
            L, pitch, A0, tie = areq_t(N, ms, s, ce, hl); Af = areq_t(N, ms, 0, ce, hl)[2]; mp = ce * sum((Af if keep else A0) * hl * 2700 * 1.5) / N; mt = tie_mass(N, ms, s, ce, A0, L, pitch, tie)
            rows.append(dict(tie_every_levels=s or None, posts="unchanged (full-stack strength sized)" if keep else "re-sized to span load (credit)", n_ties=int(sum(tie)), f_axial_Hz=round(k0[0], 1), f_lat_Hz=round(k0[1], 1), kappa_25Hz_axial=round(kax, 2), kappa_10Hz_lat=round(klat, 2), kappa_both=round(kap, 2),
                             post_kg_per_sat_at_kappa=round(float(mp * kap), 1), tie_hardware_kg_per_sat=round(float(mt), 1), extra_kg_per_sat_vs_t438=round(float(mp * kap + mt - base_post), 1)))
    R[b] = dict(N=N, levels=Lr, eff_cols=round(ce, 2), level_height_m=round(hl, 3), base_post_kg_per_sat=round(base_post, 1), margin_line=BASE_MARGIN[b], margin_used_t438=USED[b], rows=rows)
    print(b)
    for r in rows: print(r)
json.dump(R, open(HERE / "results/t440/stack_stiffness.json", "w"), indent=1)

# ---- wall-compliance sensitivity at the recommended spacing s=3 (posts unchanged): each tie = axial spring to ground of stiffness x * (post stiffness of that level); x=inf is the rigid-wall case above
def f_axial_compliant(N, msat, s, cols, hl, x):
    L, pitch, A0, tie = areq_t(N, msat, s, cols, hl); A = areq_t(N, msat, 0, cols, hl)[2]; k = E * A / hl; K = np.zeros((L, L))
    for i in range(L):
        K[i, i] += k[i]
        if i: K[i - 1, i - 1] += k[i]; K[i, i - 1] -= k[i]; K[i - 1, i] -= k[i]
    for i in range(L):
        if tie[i]: K[i, i] += x * k[i]
    return float(math.sqrt(sl.eigh(K, np.eye(L) * msat, eigvals_only=True)[0]) / 2 / math.pi)
W = {}
for b, N, ms in (("Jun", 46, 2130.4348), ("Aug", 30, 3266.6667)):
    pk = json.load(open(HERE / f"results/t438/scene/{b}/fleet_pack_replica_{b}.json"))["layers"]; Lr = len(pk); top = pk[-1]["z0"] + pk[-1]["H"]; ce = N / Lr; hl = top / Lr - 0.07
    W[b] = {f"s={s}": {f"x={x}": round(f_axial_compliant(N, ms, s, ce, hl, x), 1) for x in (1, 3, 10, 30, 1000)} for s in (3, 2)}
    print(b, "wall-compliance sensitivity f_axial Hz", W[b])
R["wall_compliance_sensitivity"] = W; json.dump(R, open(HERE / "results/t440/stack_stiffness.json", "w"), indent=1)

def f_ax_kappa(N, msat, s, cols, hl, x, kap):
    L, pitch, A0, tie = areq_t(N, msat, s, cols, hl); A = areq_t(N, msat, 0, cols, hl)[2] * kap; k = E * A / hl; K = np.zeros((L, L))
    for i in range(L):
        K[i, i] += k[i]
        if i: K[i - 1, i - 1] += k[i]; K[i, i - 1] -= k[i]; K[i - 1, i] -= k[i]
    for i in range(L):
        if tie[i]: K[i, i] += x * k[i]
    return float(math.sqrt(sl.eigh(K, np.eye(L) * msat, eigvals_only=True)[0]) / 2 / math.pi)
KK = {}
for b, N, ms in (("Jun", 46, 2130.4348), ("Aug", 30, 3266.6667)):
    pk = json.load(open(HERE / f"results/t438/scene/{b}/fleet_pack_replica_{b}.json"))["layers"]; Lr = len(pk); top = pk[-1]["z0"] + pk[-1]["H"]; ce = N / Lr; hl = top / Lr - 0.07
    base = ce * sum(areq_t(N, ms, 0, ce, hl)[2] * hl * 2700 * 1.5) / N; KK[b] = {}
    for s in (3, 2):
        L, pitch, A0, tie = areq_t(N, ms, s, ce, hl); mt = tie_mass(N, ms, s, ce, A0, L, pitch, tie)
        for x in (10, 3):
            lo, hi = 1.0, 50.0
            if f_ax_kappa(N, ms, s, ce, hl, x, 1.0) >= 25: kap = 1.0
            else:
                for _ in range(60):
                    mid = math.sqrt(lo * hi)
                    if f_ax_kappa(N, ms, s, ce, hl, x, mid) >= 25: hi = mid
                    else: lo = mid
                kap = hi
            KK[b][f"s={s},x={x}"] = dict(kappa=round(kap, 2), extra_kg_per_sat=round(float(base * (kap - 1) + mt), 1), ties_kg=round(float(mt), 1), n_ties=int(sum(tie)))
    print(b, KK[b])
R["kappa_for_25Hz_with_compliant_wall"] = KK; json.dump(R, open(HERE / "results/t440/stack_stiffness.json", "w"), indent=1)
