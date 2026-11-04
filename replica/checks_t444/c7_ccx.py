# t444 check 7a cross-check: CalculiX 2.21 B31 beam model of the same frame (modes + static 6 g axial / 2 g lateral). ESTIMATE.
import subprocess, re, sys, json, numpy as np, os
from c7_frame import *
CCX = "ccx"
def write(name, F, tie_nodes, nu=0.33, step="freq", ax_g=0.0, lat_g=0.0, nmode=6):
    L = F.L; z = np.concatenate([[0], np.cumsum(F.pitch)]); lines = ["*NODE"]
    for i in range(L + 1): lines.append(f"{i+1},0,0,{z[i]:.6f}")
    for e in range(L): lines += [f"*ELEMENT,TYPE=B31,ELSET=B{e+1}", f"{e+1},{e+1},{e+2}"]
    rm = ARM / 2; SQ = rm * math.sqrt(12.0)                        # square solid proxy section SQ x SQ (I = A_s SQ^2/12 = A_s rm^2); E scaled per element so EA and EI equal the real post group (EA=E*A, EI=E*A*rm^2) in BOTH lateral directions
    for e in range(L):
        A = F.m[e] * F.A[e]; Ee = E * A / (SQ * SQ)
        lines += [f"*MATERIAL,NAME=M{e+1}", "*ELASTIC", f"{Ee:.6e},{nu}", "*DENSITY", "1e-9",
                  f"*BEAM SECTION,ELSET=B{e+1},MATERIAL=M{e+1},SECTION=RECT", f"{SQ:.8f},{SQ:.8f}", "1.,0.,0."]
    for i in range(1, L + 1): lines += [f"*ELEMENT,TYPE=MASS,ELSET=M{i}", f"{1000+i},{i+1}", f"*MASS,ELSET=M{i}", f"{F.mass[i-1]:.6f}"]
    lines += ["*BOUNDARY", "1,1,6"]
    for i in range(2, L + 2): lines += [f"{i},6,6"]
    for t in tie_nodes: lines.append(f"{t},1,3")
    if step == "freq": lines += ["*STEP", f"*FREQUENCY", f"{nmode}", "*NODE FILE", "U", "*END STEP"]
    else:
        lines += ["*STEP", "*STATIC", "*CLOAD"]
        for i in range(2, L + 2):
            if ax_g: lines.append(f"{i},3,{-F.mass[i-2]*g*ax_g:.6f}")   # downward = compression
            if lat_g: lines.append(f"{i},1,{F.mass[i-2]*g*lat_g:.6f}")
        lines += ["*NODE FILE", "U", "*NODE PRINT,NSET=NALL", "U", "*END STEP"]
    open(f"ccx/{name}.inp", "w").write("\n".join(lines).replace("*NODE\n", "*NODE,NSET=NALL\n", 1) + "\n")
def run(name):
    subprocess.run([CCX, "-i", f"ccx/{name}"], capture_output=True, cwd=".")
    txt = open(f"ccx/{name}.dat").read() if os.path.exists(f"ccx/{name}.dat") else ""
    return txt
def freqs(name):
    t = run(name); f = []
    for ln in t.splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0].isdigit() and "." in p[3] and len(p) == 5: f.append(float(p[3]))
    f = sorted(f); u = []
    for x in f:
        if not u or abs(x - u[-1]) > 1e-3 * x: u.append(x)
    return u
    return f
def dens(F, e, Ae):   # node masses spread onto adjacent truss elements (MASS elements are rejected by ccx when y dof is restrained): element mass = (m_lower + m_upper)/2, top element carries the full top node
    lo = F.mass[e - 1] if e > 0 else 0.0; up = F.mass[e]; mm = (lo + up) / 2 + (up / 2 if e == F.L - 1 else 0.0)
    return mm / (Ae * F.pitch[e])
def write_truss(name, F, tie_nodes, nmode=4):
    L = F.L; z = np.concatenate([[0], np.cumsum(F.pitch)]); lines = ["*NODE,NSET=NALL"]
    for i in range(L + 1): lines.append(f"{i+1},0,0,{z[i]:.6f}")
    for e in range(L):   # axial stiffness identical to Frame (EA/h, h = post length; adapter+gap rigid in axial) -> A_eff = m*A*pitch/h
        Ae = F.m[e] * F.A[e] * F.pitch[e] / F.h[e] if hasattr(F.h, "__len__") else F.m[e] * F.A[e] * F.pitch[e] / F.h
        lines += [f"*ELEMENT,TYPE=T3D2,ELSET=B{e+1}", f"{e+1},{e+1},{e+2}", f"*MATERIAL,NAME=M{e+1}", "*ELASTIC", f"{E:.6e},0.3", "*DENSITY", f"{dens(F, e, Ae):.9e}", f"*SOLID SECTION,ELSET=B{e+1},MATERIAL=M{e+1}", f"{Ae:.9e}"]
    lines += ["*BOUNDARY", "1,1,3"]
    for i in range(2, L + 2): lines += [f"{i},1,2"]
    for t in tie_nodes: lines.append(f"{t},3,3")
    lines += ["*STEP", "*FREQUENCY", f"{nmode}", "*NODE FILE", "U", "*END STEP"]
    open(f"ccx/{name}.inp", "w").write("\n".join(lines) + "\n")
if __name__ == "__main__":
    out = {}
    for b in ("Jun", "Aug"):
        for var in ("t440", "kept"):
            m, h, ms = build(b, var); A, p, Mab = size(m, h, ms)
            for lab, te in (("tie3", 3), ("none", 0)):
                F = Frame(m, h, ms, A, p, te); tn = [i + 2 for i in range(F.L) if F.tie[i]]
                name = f"{b}_{var}_{lab}"; write(name + "_L", F, tn, nu=-0.95, nmode=12); fl = freqs(name + "_L")
                write_truss(name + "_A", F, tn); fa = freqs(name + "_A")
                wa, wl = F.freqs()
                out[name] = dict(ccx_axial=[round(x, 2) for x in fa[:3]], warp_axial=wa.round(2).tolist(), ccx_beam_all=[round(x, 2) for x in fl[:8]], warp_lateral=wl.round(2).tolist())
                print(name, out[name], flush=True)
    json.dump(out, open("c7_ccx_modes.json", "w"), indent=1)
