# t444 check 7a: launch-load frame model of the stowed replica stack (Jun 46 / Aug 30) with bay-wall ties.
# NVIDIA Warp: element assembly kernels (fp64, atomics) + warp.optim.linear.cg solves + subspace iteration for modes (small Rayleigh-Ritz in numpy).
# Idealisation = SAME as t440 (post group per level, strength sized at 241 MPa, FS 1.25, E 68.9 GPa, plan arm 6.75 m, rigid satellite bodies, rigid base/wall) so frequencies are comparable. ESTIMATE.
import json, math, sys, time, numpy as np, warp as wp
from warp.optim.linear import cg, aslinearoperator
wp.config.quiet = True; wp.init()
g = 9.81; E = 68.9e9; SIG = 241e6; FS = 1.25; ARM = 6.75; GAP_ADAPT = 0.07
SC = "replica/gb10_render_replica/scene"
MS = {"Jun": 2130.4347826, "Aug": 3266.6666667}

@wp.kernel
def k_axial(kk: wp.array(dtype=wp.float64), K: wp.array2d(dtype=wp.float64)):
    e = wp.tid()   # spring e joins node e (0=ground) and e+1; node index in K = e+1 -> row e (ground removed)
    k = kk[e]
    K[e, e] = K[e, e] + k
    if e > 0:
        K[e - 1, e - 1] = K[e - 1, e - 1] + k
        K[e, e - 1] = K[e, e - 1] - k
        K[e - 1, e] = K[e - 1, e] - k

@wp.kernel
def k_beam(EI: wp.array(dtype=wp.float64), h: wp.array(dtype=wp.float64), K: wp.array2d(dtype=wp.float64)):
    e = wp.tid()   # element e joins node e and e+1; dofs (x_n, th_n) = 2n,2n+1 with ground included (removed later)
    L = h[e]; c = EI[e] / (L * L * L)
    ke = wp.matrix(shape=(4, 4), dtype=wp.float64)
    ke[0, 0] = c * wp.float64(12.0); ke[0, 1] = c * wp.float64(6.0) * L; ke[0, 2] = -c * wp.float64(12.0); ke[0, 3] = c * wp.float64(6.0) * L
    ke[1, 0] = ke[0, 1]; ke[1, 1] = c * wp.float64(4.0) * L * L; ke[1, 2] = -c * wp.float64(6.0) * L; ke[1, 3] = c * wp.float64(2.0) * L * L
    ke[2, 0] = ke[0, 2]; ke[2, 1] = ke[1, 2]; ke[2, 2] = c * wp.float64(12.0); ke[2, 3] = -c * wp.float64(6.0) * L
    ke[3, 0] = ke[0, 3]; ke[3, 1] = ke[1, 3]; ke[3, 2] = ke[2, 3]; ke[3, 3] = c * wp.float64(4.0) * L * L
    for a in range(4):
        for b in range(4):
            wp.atomic_add(K, 2 * e + a, 2 * e + b, ke[a, b])

def build(b, variant):
    pk = json.load(open(f"{SC}/{b}/fleet_pack_replica_{b}.json"))["layers"]; msat = MS[b]
    if variant == "t440":      # same idealisation as t440: all packed layers incl. dropped Aug sats, mean columns, level height = top/L - 0.07
        Lr = len(pk); top = pk[-1]["z0"] + pk[-1]["H"]; N = 46 if b == "Jun" else 30; ce = N / Lr; hl = top / Lr - GAP_ADAPT
        m = np.full(Lr, ce); h = np.full(Lr, hl)
    else:                       # as-kept: only kept sats, per-layer count and per-layer height
        mm_, hh_ = [], []
        for ly in pk:
            n = sum(1 for st in ly["sats"] if st.get("keep", True))
            if n: mm_.append(n); hh_.append(ly["H"])
        m = np.array(mm_, float); h = np.array(hh_)
    return m, h, msat

def size(m, h, msat, dp_factor=1.0):
    L = len(m); pitch = h + GAP_ADAPT; A = np.zeros(L); Mab = np.zeros(L)
    for k in range(L):
        Mk = msat * m[k:].sum(); Hab = pitch[k:].sum(); Mo = Mk * g * 2.0 * Hab / 2; dP = dp_factor * Mo / (m[k] * ARM) * FS
        P6 = Mk / m[k] * g * 6.0 * FS; P35 = Mk / m[k] * g * 3.5 * FS + dP
        A[k] = max(P6, P35) / SIG; Mab[k] = Mk
    return A, pitch, Mab

class Frame:
    def __init__(self, m, h, msat, A, pitch, tie_every=0, wall=None):
        self.m, self.h, self.msat, self.A, self.pitch = m, h, msat, A, pitch; L = self.L = len(m)
        self.tie = np.array([bool(tie_every) and (k + 1) % tie_every == 0 for k in range(L)])
        self.kax = E * m * A / h; self.EI = E * m * A * (ARM / 2) ** 2; self.mass = m * msat
        t0 = time.time()
        Ka = wp.zeros((L, L), dtype=wp.float64); wp.launch(k_axial, dim=L, inputs=[wp.array(self.kax, dtype=wp.float64), Ka])
        Kb = wp.zeros((2 * (L + 1), 2 * (L + 1)), dtype=wp.float64); wp.launch(k_beam, dim=L, inputs=[wp.array(self.EI, dtype=wp.float64), wp.array(pitch, dtype=wp.float64), Kb])
        self.Ka = Ka.numpy(); self.Kb = Kb.numpy()
        # ties restrain translation (axial + lateral) of tie nodes; wall compliance factor wall = x (tie spring = x * post stiffness) or None = rigid
        self.t_asm = time.time() - t0
    def _free_ax(self): return np.array([i for i in range(self.L) if not self.tie[i]])
    def _free_lat(self):  # dofs: node n=1..L -> x at 2n, th at 2n+1 ; ground n=0 removed
        return np.array([d for n in range(1, self.L + 1) for d in (2 * n, 2 * n + 1) if not (d == 2 * n and self.tie[n - 1])])
    _cache = {}
    @classmethod
    def wcg(cls, K, b):
        key = id(K)
        if key not in cls._cache: cls._cache[key] = (K, aslinearoperator(wp.array(K, dtype=wp.float64)))
        op = cls._cache[key][1]
        x = wp.zeros(len(b), dtype=wp.float64); cg(op, wp.array(b, dtype=wp.float64), x, tol=1e-13, maxiter=3 * len(b)); return x.numpy()
    def modes_sub(self, K, Mvec, nmode=3, nvec=8, iters=40):
        n = K.shape[0]; rng = np.random.default_rng(1); V = rng.standard_normal((n, nvec)); prev = np.zeros(nmode); M = np.diag(Mvec)
        for _ in range(iters):
            V = np.column_stack([self.wcg(K, M @ V[:, j]) for j in range(nvec)])
            Kr = V.T @ K @ V; Mr = V.T @ M @ V; w, Q = np.linalg.eig(np.linalg.solve(Mr, Kr)); idx = np.argsort(w.real); V = V @ Q[:, idx].real
            V /= np.linalg.norm(V, axis=0)
            wn = np.sqrt(np.maximum(np.sort(w.real)[:nmode], 0)) / 2 / math.pi
            if _ > 3 and np.allclose(wn, prev, rtol=1e-7): break
            prev = wn
        Kr = V.T @ K @ V; Mr = V.T @ M @ V; w = np.sort(np.linalg.eigvals(np.linalg.solve(Mr, Kr)).real)
        return np.sqrt(np.maximum(w[:nmode], 0)) / 2 / math.pi
    def freqs(self):
        fa = self._free_ax(); Kaf = self.Ka[np.ix_(fa, fa)]; fax = self.modes_sub(Kaf, self.mass[fa], nvec=min(6, len(fa)))
        fl = self._free_lat(); Kl = self.Kb[np.ix_(fl, fl)]; Ml = np.array([self.mass[d // 2 - 1] if d % 2 == 0 else 0.0 for d in fl])
        flat = self.modes_sub(Kl, Ml, nvec=min(8, int((Ml > 0).sum())))
        return fax, flat
    def static(self, ax_g, lat_g):
        L = self.L; fa = self._free_ax(); res = {}
        # axial: compressive forces M g ax_g at each node (pushing toward ground)
        f = self.mass * g * ax_g; u = np.zeros(L); u[fa] = self.wcg(self.Ka[np.ix_(fa, fa)], f[fa])
        N = self.kax * (u - np.concatenate([[0], u[:-1]]))            # post-group compression at each level
        react = f - self.Ka @ u                                       # tie reactions (rows of tie nodes): K u - f
        res["axial_u_top_mm"] = float(u[-1] * 1e3); res["axial_rel_closure_mm"] = (u - np.concatenate([[0], u[:-1]])) * 1e3; res["N"] = N
        res["tie_axial_reaction_N"] = [float((self.Ka @ u - f)[i]) for i in range(L) if self.tie[i]]
        res["base_axial_reaction_N"] = float(N[0])
        # lateral
        fl = self._free_lat(); F = np.zeros(2 * (L + 1))
        for n in range(1, L + 1): F[2 * n] = self.mass[n - 1] * g * lat_g
        U = np.zeros(2 * (L + 1)); U[fl] = self.wcg(self.Kb[np.ix_(fl, fl)], F[fl]); r = self.Kb @ U - F
        x = U[0::2]; th = U[1::2]
        # element end moments
        Mend = np.zeros(self.L)
        for e in range(L):
            Lh = self.pitch[e]; c = self.EI[e] / Lh ** 3
            ke = c * np.array([[12, 6 * Lh, -12, 6 * Lh], [6 * Lh, 4 * Lh * Lh, -6 * Lh, 2 * Lh * Lh], [-12, -6 * Lh, 12, -6 * Lh], [6 * Lh, 2 * Lh * Lh, -6 * Lh, 4 * Lh * Lh]])
            fe = ke @ U[2 * e:2 * e + 4]; Mend[e] = max(abs(fe[1]), abs(fe[3]))
        res["lat_x_mm"] = x[1:] * 1e3; res["lat_x_max_mm"] = float(np.abs(x).max() * 1e3); res["M_end"] = Mend
        res["lat_interlevel_mm"] = np.diff(x) * 1e3
        res["tie_lateral_reaction_N"] = [float(r[2 * (i + 1)]) for i in range(L) if self.tie[i]]
        res["base_shear_N"] = float(r[0]) ; res["base_moment_Nm"] = float(r[1])
        return res
    def stress(self, ax, lat_case_ax_g, lat_g):
        s6 = self.static(6.0, 0.0); sl = self.static(lat_case_ax_g, lat_g)
        mA = self.m * self.A
        sig6 = s6["N"] / mA * FS
        sig_comb = (np.array(sl["N"]) / mA + sl["M_end"] / (mA * ARM / 2)) * FS
        return s6, sl, SIG / sig6 - 1, SIG / sig_comb - 1
