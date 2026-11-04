"""Parametric CAD model (build123d, Apache-2.0) of the co-designed radiator panel, driven by the co-design optimiser output.

Set BY THE OPTIMISER (read from results/codesign/best_design.json):  tube count n, panel width and length, the sheet thickness field t(x, y)
(16 x 8 log-thickness control grid), tube width (7.8 mm = 2 grid cells), tube pitch (W / n), minimum gauge, coolant temperatures.
NOT set by the optimiser (ESTIMATE, labelled in ESTIMATE_GEOMETRY and in every render):
  * tube section: square hollow, height = width (the 2-D model only has the tube footprint);
  * tube wall thickness: SOLVED so that tubes + headers + stubs weigh exactly the optimiser's tube-and-header mass
    (0.129 kg per m of tube, ESTIMATE), common wall for all of them. The result is a visibly thick wall: the 0.129 kg/m figure is heavy;
  * header section 14 x 14 mm square hollow, one at each end of the tubes, outside the 0.5 x 1.0 m radiating sheet;
  * inlet / outlet stubs: round, 10 mm OD, 30 mm long, on the outer ends of the two headers;
  * everything that is not in the 2-D model (MMOD shield, deployment hinges, brackets: the 4.2 kg/face-m2 overhead of codesign.yaml) has NO geometry.
The sheet is represented by tile-averaged thickness steps (one box per tile-and-gap segment): volume, hence mass, equals the optimiser's cell sum exactly,
the smooth thickness field is approximated by steps. Units: metres in the optimiser, millimetres in the CAD.
"""
from __future__ import annotations

import json

import numpy as np

ESTIMATE_GEOMETRY = {
    "tube_section": "square hollow, height = width (ESTIMATE; the 2-D model only fixes the 7.8 mm footprint)",
    "tube_wall": "solved so tubes + headers + stubs = the optimiser's 0.129 kg/m tube-and-header mass (ESTIMATE)",
    "header": "14 x 14 mm square hollow, one at each tube end, outside the radiating sheet (ESTIMATE)",
    "stubs": "round 10 mm OD x 30 mm long inlet/outlet stubs (ESTIMATE)",
    "not_modelled": "MMOD shield, hinges, brackets, fluid (the 4.2 kg/face-m2 overhead has no geometry)",
}
HEADER_MM, STUB_OD_MM, STUB_LEN_MM = 14.0, 10.0, 30.0


def _interp_matrix(n, c):
    x = np.linspace(0.0, c - 1.0, n)
    i0 = np.minimum(np.floor(x).astype(int), c - 2)
    w = x - i0
    M = np.zeros((n, c))
    M[np.arange(n), i0] = 1.0 - w
    M[np.arange(n), i0 + 1] = w
    return M


def tube_columns(nx, n, tw):
    """Cell columns covered by tubes (same rule as panel2d.layout: centres (i+0.5) nx/n, tw cells wide). Returns list of (lo, hi) per tube."""
    out = []
    for i in range(n):
        c = (i + 0.5) * nx / n
        lo = int(np.floor(c - tw / 2.0 + 0.5))
        out.append((max(lo, 0), min(lo + tw, nx)))
    return out


def thickness_field(p, nx, ny, ctrl):
    cy, cx = ctrl
    return np.exp(_interp_matrix(ny, cy) @ np.asarray(p, float).reshape(cy, cx) @ _interp_matrix(nx, cx).T)


def load_design(path):
    return json.load(open(path))


def sheet_segments(t, tubes, nx, ny, ctrl):
    """Boxes of the sheet: for every control-grid row and every run of tube-free cells inside a control-grid column: (i0, i1, j0, j1, mean t [m])."""
    cy, cx = ctrl
    edges_j = np.linspace(0, ny, cy * 0 + 17).astype(int)           # 16 rows of cells, as the control grid
    edges_i = np.linspace(0, nx, 9).astype(int)                      # 8 columns of cells
    tube = np.zeros(nx, bool)
    for lo, hi in tubes:
        tube[lo:hi] = True
    segs = []
    for a in range(len(edges_j) - 1):
        j0, j1 = edges_j[a], edges_j[a + 1]
        for b in range(len(edges_i) - 1):
            i0, i1 = edges_i[b], edges_i[b + 1]
            i = i0
            while i < i1:
                if tube[i]:
                    i += 1
                    continue
                k = i
                while k < i1 and not tube[k]:
                    k += 1
                segs.append((i, k, j0, j1, float(t[j0:j1, i:k].mean())))
                i = k
    return segs


def build_panel(design, rho=2700.0, header_mm=HEADER_MM):
    """Build the CAD parts. ``design``: dict from best_design.json. Returns dict(parts=dict name -> build123d solid/compound, info=...)."""
    from build123d import Align, Box, Compound, Cylinder, Location, Pos, Rot, Axis
    from scipy.optimize import brentq

    nx, ny = design["nx"], design["ny"]
    W, L = design["width_m"] * 1e3, design["length_m"] * 1e3
    n, tw = design["n_tubes"], max(int(design["tube_width_cells"]) * nx // 128, 1)
    h = W / nx
    hy = L / ny                                              # cell height along the length: equals h only for a 2:1 panel (the 2-D baseline); P6 panels are longer
    a = tw * h                                              # tube width = height (mm)
    t = thickness_field(design["p"], nx, ny, design["thickness_control"])
    tubes = tube_columns(nx, n, tw)
    segs = sheet_segments(t, tubes, nx, ny, design["thickness_control"])
    sheet = []
    for (i0, i1, j0, j1, tm) in segs:
        bx, by = (i1 - i0) * h, (j1 - j0) * hy
        sheet.append(Pos((i0 + i1) / 2 * h, (j0 + j1) / 2 * hy, 0) * Box(bx, by, tm * 1e3))
    b = header_mm

    def hollow_box(lx, ly, lz, w, bore_axis=None):
        o = Box(lx, ly, lz)
        inner = Box(lx - 2 * w if bore_axis != "x" else lx, ly - 2 * w if bore_axis != "y" else ly, lz - 2 * w)
        return o - inner

    def hw_parts(w):
        tube_solids, bores = [], []
        for (lo, hi) in tubes:
            xc = (lo + hi) / 2 * h
            outer = Pos(xc, L / 2, 0) * Box(a, L, a)
            inner = Pos(xc, L / 2, 0) * Box(a - 2 * w, L + 2, a - 2 * w)
            tube_solids.append(outer - inner)
        hdr = []
        for yc in (-b / 2, L + b / 2):
            outer = Pos(W / 2, yc, 0) * Box(W, b, b)
            inner = Pos(W / 2, yc, 0) * Box(W - 2 * w, b - 2 * w, b - 2 * w)
            solid = outer - inner
            # ports: open the header face the tubes attach to
            for (lo, hi) in tubes:
                xc = (lo + hi) / 2 * h
                solid = solid - Pos(xc, yc + (b / 2 - w / 2) * (1 if yc < 0 else -1), 0) * Box(a - 2 * w, 2 * w, a - 2 * w)
            xs = 0.0 if yc < 0 else W                      # stub end of this header: open its end wall to the stub bore
            solid = solid - Pos(xs + (w / 2 if yc < 0 else -w / 2), yc, 0) * (Rot(0, 90, 0) * Cylinder(STUB_OD_MM / 2 - w, 2 * w))
            hdr.append(solid)
        stubs = []
        for (xc, yc, sgn) in ((0.0, -b / 2, -1), (W, L + b / 2, 1)):
            od = STUB_OD_MM
            o = Pos(xc + sgn * STUB_LEN_MM / 2, yc, 0) * (Rot(0, 90, 0) * Cylinder(od / 2, STUB_LEN_MM))
            i_ = Pos(xc + sgn * STUB_LEN_MM / 2, yc, 0) * (Rot(0, 90, 0) * Cylinder(od / 2 - w, STUB_LEN_MM + 2))
            stubs.append(o - i_)
        return tube_solids, hdr, stubs

    def hw_volume(w):
        ts, hd, st = hw_parts(w)
        return sum(s.volume for s in ts + hd + st)

    lump_mm3 = design["tube_kg_per_m"] * n * (L / 1e3) / rho * 1e9               # tube + header metal volume the optimiser carries
    w = brentq(lambda w: hw_volume(w) - lump_mm3, 0.05, min(a, STUB_OD_MM) / 2 - 0.05, xtol=1e-9)
    ts, hd, st = hw_parts(w)
    parts = dict(sheet=Compound(sheet, label="sheet"), tubes=Compound(ts, label="tubes"), headers=Compound(hd, label="headers"), stubs=Compound(st, label="stubs"))
    vol = {k: v.volume for k, v in parts.items()}
    info = dict(n_tubes=n, width_mm=W, length_mm=L, tube_width_mm=a, tube_pitch_mm=W / n, tube_wall_mm=w, header_mm=b, stub_od_mm=STUB_OD_MM,
                t_min_mm=float(min(s[4] for s in segs) * 1e3), t_max_mm=float(max(s[4] for s in segs) * 1e3), n_sheet_boxes=len(segs),
                volume_mm3=vol, mass_kg={k: v * 1e-9 * rho for k, v in vol.items()}, mass_total_kg=sum(vol.values()) * 1e-9 * rho,
                lump_target_kg=lump_mm3 * 1e-9 * rho, estimate_geometry=ESTIMATE_GEOMETRY)
    return dict(parts=parts, info=info, t=t, tubes=tubes, segs=segs)


def export_step(parts, path):
    from build123d import Compound, export_step as _ex
    comp = Compound(list(parts.values()), label="radiator_panel")
    _ex(comp, str(path))
    return comp


def tile_map(segs, nx, ny):
    """(ny, nx) array of the sheet thickness [m] actually modelled (tile-averaged steps); NaN under the tubes."""
    m = np.full((ny, nx), np.nan)
    for (i0, i1, j0, j1, tm) in segs:
        m[j0:j1, i0:i1] = tm
    return m
