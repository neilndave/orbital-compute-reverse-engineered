"""P8a model: one radiator panel (sheet + 5 square tubes) as S8R shells, with an ASSUMED pad mount layout, for CalculiX.
IDEALIZED screening model, not a sign-off.  Axes: x across the width, y along the tubes, z normal to the panel (the stack / launch axis).
Surface stress convention (checked on a cantilever strip, see docs/P8A_LAUNCH_FEA.md): CalculiX prints shell stress at the two-point Gauss
points through the thickness (+-t/(2 sqrt3)); the surface value is  s_surf = s_mid + (s_gp - s_mid) * sqrt(3)."""
import json
import math
import os
import pathlib
import sys

import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from rack_two_skies.cad import thickness_field, tube_columns   # numpy-only helpers (build123d is imported lazily elsewhere)

VARIANT = os.environ.get("P8A_VARIANT", "")
TUBE_SCALE = float(os.environ.get("P8A_TK", "1.0"))        # tube wall thickness multiplier (sensitivity, adds metal mass like the sheet scale)      # "" = P6 panel (configs/p8a_launch_fea.yaml), "_f4" = F4 full-system optimum panel (configs/p8a_launch_fea_f4.yaml)
TKF = float(os.environ.get("P8A_TKF", "1.0"))               # GAP lever: extra scale on the tube flange (TTOP, TBOT) wall only (on top of P8A_TK)
TKW = float(os.environ.get("P8A_TKW", "1.0"))               # GAP lever: extra scale on the tube web (TWEB) wall only
RIBS = json.loads(os.environ.get("P8A_RIBS", "[]"))         # GAP lever: longitudinal ribs, list of {"at": "edge"|"gap"|<x_m list>, "hr": half height m, "t": thickness m}
EDGEK = float(os.environ.get("P8A_EDGEK", "1.0"))           # GAP lever: extra thickness multiplier on the two free edge strips of the sheet (outside the outer tubes)
EDGEW = float(os.environ.get("P8A_EDGEW", "1.0"))           # GAP lever: fraction of the edge strip width (measured from the outer tube) that gets the EDGEK thickening
G0 = 9.80665
SQ3 = math.sqrt(3.0)


def load_cfg(path=None):
    return yaml.safe_load(open(path or ROOT / "configs" / f"p8a_launch_fea{VARIANT}.yaml"))


class Mesh:
    """Structured S8R shell mesh built from rectangular patches; nodes shared by coordinate."""

    def __init__(self):
        self.key, self.xyz, self.elems = {}, [], []     # elems: (nodes[8], group, t, area, centroid)

    def node(self, p):
        k = tuple(int(round(c * 1e8)) for c in p)
        if k not in self.key:
            self.key[k] = len(self.xyz) + 1
            self.xyz.append(tuple(p))
        return self.key[k]

    def patch(self, o, u, v, nu, nv, group, t_of):
        """Rectangle o + s u + r v, nu x nv S8R elements.  t_of(centroid)->thickness."""
        o, u, v = (np.asarray(a, float) for a in (o, u, v))
        area = np.linalg.norm(np.cross(u, v)) / (nu * nv)
        for b in range(nv):
            for a in range(nu):
                def P(i, j):
                    return o + u * (i / (2 * nu)) + v * (j / (2 * nv))
                i, j = 2 * a, 2 * b
                c = [(i, j), (i + 2, j), (i + 2, j + 2), (i, j + 2), (i + 1, j), (i + 2, j + 1), (i + 1, j + 2), (i, j + 1)]
                ids = [self.node(P(*q)) for q in c]
                cen = P(i + 1, j + 1)
                self.elems.append((ids, group, float(t_of(cen)), area, tuple(cen)))


def build(cfg=None, layout=None, sheet_scale=None):
    """Return dict with mesh, sets, masses.  All lengths in m, masses kg."""
    cfg = cfg or load_cfg()
    gm = cfg["geometry"]
    d = json.load(open(ROOT / gm["design_json"]))
    nx, ny, n = d["nx"], d["ny"], d["n_tubes"]
    W, L = d["width_m"], d["length_m"]
    h, hy = W / nx, L / ny
    tw = max(int(d["tube_width_cells"]) * nx // 128, 1)
    a = tw * h                                            # tube outer width = height
    w = gm["tube_wall_m"] * TUBE_SCALE
    hc = (a - w) / 2.0                                    # half side of the wall mid-surface square
    tubes = tube_columns(nx, n, tw)
    xc = [(lo + hi) / 2 * h for lo, hi in tubes]
    tf = thickness_field(d["p"], nx, ny, d["thickness_control"])      # (ny, nx), m
    rho = cfg["material"]["rho_kg_m3"]
    binw = float(cfg["mesh"]["t_bin_m"])
    k_sheet = float(sheet_scale if sheet_scale is not None else os.environ.get("P8A_SHEETK", gm.get("sheet_t_scale", 1.0)))     # sheet thickness multiplier (sensitivity; adds metal mass)

    def edge_hit(x):       # True on the part of the two free edge strips that carries the EDGEK thickening (inner EDGEW fraction, from the tube)
        ws = xc[0] - hc
        return (x < ws and ws - x <= EDGEW * ws + 1e-9) or (x > W - ws and x - (W - ws) <= EDGEW * ws + 1e-9)

    def t_sheet(c):
        i = min(max(int(c[0] / h), 0), nx - 1)
        j = min(max(int(c[1] / hy), 0), ny - 1)
        ke = EDGEK if edge_hit(c[0]) else 1.0
        return round(k_sheet * ke * tf[j, i] / binw) * binw

    m = Mesh()
    nyel = int(os.environ.get("P8A_NYEL", cfg["mesh"]["ny_el"]))   # GAP lever: mesh-convergence override
    xs = [(0.0, xc[0] - hc, int(os.environ.get("P8A_NEDGE", cfg["mesh"]["n_edge"])))]
    for i in range(n - 1):
        xs.append((xc[i] + hc, xc[i + 1] - hc, int(os.environ.get("P8A_NGAP", cfg["mesh"]["n_gap"]))))
    xs.append((xc[-1] + hc, W, int(os.environ.get("P8A_NEDGE", cfg["mesh"]["n_edge"]))))
    for lo, hi, ne in xs:
        if hi - lo > 1e-9:
            m.patch((lo, 0, 0), (hi - lo, 0, 0), (0, L, 0), ne, nyel, "SHEET", t_sheet)
    for k, x0 in enumerate(xc):
        m.patch((x0 - hc, 0, hc), (2 * hc, 0, 0), (0, L, 0), 1, nyel, "TTOP", lambda c: w * TKF)
        m.patch((x0 - hc, 0, -hc), (2 * hc, 0, 0), (0, L, 0), 1, nyel, "TBOT", lambda c: w * TKF)
        m.patch((x0 - hc, 0, -hc), (0, 0, 2 * hc), (0, L, 0), 1, nyel, "TWEB", lambda c: w * TKW)
        m.patch((x0 + hc, 0, -hc), (0, 0, 2 * hc), (0, L, 0), 1, nyel, "TWEB", lambda c: w * TKW)

    # ---- GAP lever: longitudinal ribs (flanges standing on the sheet, half height hr above and below the sheet plane, full length), group RIB
    rib_x = []
    for rb in RIBS:
        at = rb["at"]
        ws0 = xc[0] - hc
        xr = [0.0, W] if at == "edge" else [rb["frac"] * ws0, W - rb["frac"] * ws0] if at == "edgein" else ([(xc[i] + xc[i + 1]) / 2 for i in range(n - 1)] if at == "gap" else list(at))
        for x0 in xr:
            m.patch((x0, 0, 0), (0, 0, rb["hr"]), (0, L, 0), 1, nyel, "RIB", lambda c, t=rb["t"]: t)
            m.patch((x0, 0, -rb["hr"]), (0, 0, rb["hr"]), (0, L, 0), 1, nyel, "RIB", lambda c, t=rb["t"]: t)
    # ---- mass bookkeeping: structural metal, header+stub lump on the tube end rows, remaining overhead spread over sheet + tube top faces
    E = m.elems
    struct = sum(e[3] * e[2] * rho for e in E)
    sheet_kg = sum(e[3] * e[2] * rho for e in E if e[1] == "SHEET")
    rib_kg = sum(e[3] * e[2] * rho for e in E if e[1] == "RIB")
    lump = gm["header_kg"] + gm["stub_kg"]
    tube_kg = sum(e[3] * e[2] * rho for e in E if e[1].startswith("T"))
    tube_scale_g = dict(TTOP=TUBE_SCALE * TKF, TBOT=TUBE_SCALE * TKF, TWEB=TUBE_SCALE * TKW)          # per-group wall multiplier vs the nominal wall (== TUBE_SCALE when TKF = TKW = 1)
    tube_nom_kg = sum(e[3] * e[2] * rho / tube_scale_g[e[1]] for e in E if e[1] in tube_scale_g)
    xyz_a = np.array(m.xyz)
    sheet_nom_kg = 0.0
    for e in E:
        if e[1] == "SHEET":
            cx = float(xyz_a[np.array(e[0]) - 1, 0].mean())
            sheet_nom_kg += e[3] * e[2] * rho / (k_sheet * (EDGEK if edge_hit(cx) else 1.0))
    struct_nom = struct - rib_kg - sheet_kg + sheet_nom_kg - tube_kg + tube_nom_kg
    overhead = gm["panel_kg_total"] - struct_nom - lump      # overhead fixed at the nominal-sheet / nominal-wall value; thickened sheet, wall or ribs add metal on top
    area_oh = sum(e[3] for e in E if e[1] in ("SHEET", "TTOP"))
    sigma = overhead / area_oh                                         # kg/m2 added on sheet + tube-top elements
    end_els = [i for i, e in enumerate(E) if e[1].startswith("T") and (e[4][1] < L / nyel or e[4][1] > L - L / nyel)]
    end_m = lump / len(end_els)                                         # kg per end-row tube element
    end_set = set(end_els)
    rho_eff, mass_el = [], []
    for i, e in enumerate(E):
        extra = (sigma * e[3] if e[1] in ("SHEET", "TTOP") else 0.0) + (end_m if i in end_set else 0.0)
        r = rho + extra / (e[3] * e[2])
        rho_eff.append(r)
        mass_el.append(e[3] * e[2] * r)
    # ---- mount pads
    ml = cfg["mounts"]
    lay = (layout or ml["active"])
    _gf = pathlib.Path(os.environ.get("P8A_GENLAYOUTS", pathlib.Path(__file__).resolve().parents[2] / "configs" / "gap_layouts_T45.json"))
    gspec = lay if lay.startswith("gen:") else (json.load(open(_gf)).get(lay) if _gf.exists() else None)       # alias -> "gen:..." spec (aliases keep case-dir names free of ':' for the container mounts)
    if gspec:
        lay0, lay = lay, gspec
    if lay.startswith("gen:"):     # GAP lever generated layout
        pads = []
        for part in lay[4:].split(";"):        # groups "[s:]<y_frac list>[@<tube digits>]" ; s: = snubber (normal-only)
            snub = part.startswith("s:"); part = part[2:] if snub else part
            ys, _, tt = part.partition("@")
            for y in ys.split(","):
                for tb in [int(c) for c in (tt or "0123")]:
                    pads.append(dict(tube=tb, y_frac=float(y), dofs=[3] if snub else [1, 2, 3], **({"snub": True} if snub else {})))
    else:
        pads = ml["layouts"][lay]["pads"]
    pad_len = float(os.environ.get("P8A_PADLEN", ml["pad_len_m"])); inset = float(os.environ.get("P8A_INSET", ml["end_inset_m"]))
    xyz = np.array(m.xyz)
    pad_sets = []
    for pd in pads:
        yc = inset + pd["y_frac"] * (L - 2 * inset)
        sel = np.where((np.abs(xyz[:, 0] - xc[pd["tube"]]) < 1e-9) & (np.abs(xyz[:, 2] + hc) < 1e-9)       # centre line of the bottom face only: constraining the knot nodes at the tube corners leaks reaction in CalculiX shell-knot MPCs
                       & (np.abs(xyz[:, 1] - yc) <= pad_len / 2 + 1e-9))[0] + 1
        pad_sets.append(dict(tube=pd["tube"], y_m=yc, dofs=pd["dofs"], nodes=[int(i) for i in sel], snub=bool(pd.get("snub", False))))
    return dict(mesh=m, W=W, L=L, a=a, w=w, hc=hc, xc=xc, rho_eff=rho_eff, mass_el=mass_el, struct_kg=struct, sheet_kg=sheet_kg, lump_kg=lump,
                overhead_kg=overhead, sheet_scale=k_sheet, extra_metal_kg=struct - struct_nom, rib_kg=rib_kg, edgek=EDGEK, edgew=EDGEW, tkf=TKF, tkw=TKW, tube_scale=TUBE_SCALE, sigma_kg_m2=sigma, total_kg=sum(mass_el), pads=pad_sets, layout=(lay0 if gspec else lay), rho=rho)


def write_inp(mdl, path, cfg=None, steps=("grav_x", "grav_y", "grav_z"), extra_steps=""):
    """Write the CalculiX input: model + the given steps (default: three unit 1 g gravity load cases for linear superposition)."""
    cfg = cfg or load_cfg()
    mat = cfg["material"]
    m = mdl["mesh"]
    with open(path, "w") as f:
        f.write("*NODE\n")
        for i, p in enumerate(m.xyz, 1):
            f.write(f"{i}, {p[0]:.9e}, {p[1]:.9e}, {p[2]:.9e}\n")
        f.write("*ELEMENT, TYPE=S8R, ELSET=EALL\n")
        for i, e in enumerate(m.elems, 1):
            f.write(f"{i}, " + ", ".join(map(str, e[0])) + "\n")
        groups = {}
        for i, e in enumerate(m.elems, 1):
            key = (round(e[2] * 1e9), round(mdl["rho_eff"][i - 1], 3))
            groups.setdefault(key, []).append(i)
        for g, (key, els) in enumerate(sorted(groups.items())):
            f.write(f"*ELSET, ELSET=G{g}\n")
            for k in range(0, len(els), 12):
                f.write(", ".join(map(str, els[k:k + 12])) + ",\n")
            f.write(f"*MATERIAL, NAME=M{g}\n*ELASTIC\n{float(mat['E_Pa'])}, {float(mat['nu'])}\n*DENSITY\n{key[1]}\n")
            f.write(f"*SHELL SECTION, ELSET=G{g}, MATERIAL=M{g}\n{key[0] * 1e-9:.9e}\n")
        allpad = set()
        for k, p in enumerate(mdl["pads"]):
            f.write(f"*NSET, NSET=PAD{k}\n" + ",\n".join(map(str, p["nodes"])) + "\n")
            allpad.update(p["nodes"])
        f.write("*NSET, NSET=PADS\n" + ",\n".join(f"PAD{k}" for k in range(len(mdl["pads"]))) + "\n")
        f.write("*BOUNDARY\n")
        for k, p in enumerate(mdl["pads"]):
            for dof in p["dofs"]:
                f.write(f"PAD{k}, {dof}, {dof}\n")
        dirs = dict(grav_x=(1, 0, 0), grav_y=(0, 1, 0), grav_z=(0, 0, 1))
        for s in steps:
            dx = dirs[s]
            f.write(f"*STEP\n*STATIC\n*DLOAD, OP=NEW\nEALL, GRAV, {G0}, {dx[0]}, {dx[1]}, {dx[2]}\n")
            for k in range(len(mdl["pads"])):
                f.write(f"*NODE PRINT, NSET=PAD{k}, TOTALS=ONLY\nRF\n")
            f.write("*EL PRINT, ELSET=EALL\nS\n*END STEP\n")
        f.write(extra_steps)
    return path


def parse_static(dat, n_el):
    """Return (S[step][n_el, 8, 6] Pa, RF[step][set name] = [fx, fy, fz] N) from a .dat with one stress block per step."""
    S, RF = [], []
    cur, mode, name = None, None, None
    for line in open(dat):
        if "S T E P" in line:
            RF.append({}); continue
        if line.startswith(" stresses (elem"):
            cur = np.zeros((n_el, 8, 6)); S.append(cur); mode = "S"; continue
        if "total force (fx,fy,fz)" in line:
            mode, name = "T", line.split(" for set ")[1].split()[0]; continue
        a = line.split()
        if mode == "S" and len(a) >= 8 and a[0].isdigit() and a[1].isdigit():
            cur[int(a[0]) - 1, int(a[1]) - 1] = [float(x) for x in a[2:8]]
        elif mode == "T" and len(a) == 3:
            try:
                RF[-1][name] = [float(x) for x in a]; mode = None
            except ValueError:
                pass
    return S, RF


def element_normals(m):
    """Shell normal per element (patches are axis-aligned): z for SHEET/TTOP/TBOT, x for TWEB."""
    n = np.zeros((len(m.elems), 3))
    for i, e in enumerate(m.elems):
        n[i, 0 if e[1] == "TWEB" else 2] = 1.0
    return n


def surface_stress(S, normals):
    """S[n_el, 8, 6] Gauss-point stresses (global axes) -> surface stresses on the two shell faces (points 0-3 one face, 4-7 the other).
    Surface value = mid + sqrt(3) (gauss - mid). The through-thickness-normal and transverse-shear components are then removed
    (P s P with P = I - n n^T): shell theory has sigma_nn = 0 at the faces, and the small value CalculiX prints comes from the expanded brick element."""
    lo, hi = S[..., :4, :], S[..., 4:, :]
    mid = 0.5 * (lo + hi)
    out = np.concatenate([mid + (lo - mid) * SQ3, mid + (hi - mid) * SQ3], axis=-2)
    T = np.zeros(out.shape[:-1] + (3, 3))
    for k, (i, j) in enumerate([(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]):
        T[..., i, j] = out[..., k]; T[..., j, i] = out[..., k]
    P = np.eye(3)[None] - normals[:, :, None] * normals[:, None, :]            # [n_el,3,3]
    T = np.einsum("eab,epbc,ecd->epad", P, T, P)
    return np.stack([T[..., 0, 0], T[..., 1, 1], T[..., 2, 2], T[..., 0, 1], T[..., 0, 2], T[..., 1, 2]], axis=-1)


def von_mises(s):
    sx, sy, sz, txy, txz, tyz = (s[..., i] for i in range(6))
    return np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy ** 2 + txz ** 2 + tyz ** 2))
