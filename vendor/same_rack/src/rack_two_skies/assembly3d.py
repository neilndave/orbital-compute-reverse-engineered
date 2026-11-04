"""Idealized 3-D assembly of the co-designed rack satellite: radiator wings, solar-array wings, bus and rack envelope, deployed and stowed
in the Starship payload envelope (docs/CAD_3D.md).

Set BY THE OPTIMISER (read from results/codesign/best_design.json, never copied): panel size, tube count, thickness field (so the panel solids),
continuous panel count N, the 4.2 kg per face-m2 overhead (m_overhead / A_face), array mass, IT power.
Set by configs/assembly3d.yaml (all ESTIMATE unless tagged C or D there): wing layout, array area from a power density, stack pitches, bus and rack boxes,
the Starship envelope (C, 2020 guide, pre-V3).
Mass accounting (what the 1 % check compares, see ``reconcile``):
  * radiator metal and tubes   = volume of the CAD solids x density (a real geometric number, equals the optimiser's per-panel mass by construction of cad.py);
  * radiator overhead          = the optimiser's lumped 4.2 kg per face-m2 x CAD face area (no geometry exists for it);
  * array                      = areal density (optimiser array mass / area that the power density implies) x CAD leaf area;
  * bus, rack, mast, trunks    = geometry only, NO mass (the optimiser does not carry them).
So the check proves the bookkeeping and the panel count and area are consistent. It is not an independent mass estimate.
Units: millimetres in the CAD (as cad.py), metres in the YAML.
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
ASSEMBLY_CONFIG = ROOT / "configs" / "assembly3d.yaml"
BEST_DESIGN = ROOT / "results" / "codesign" / "best_design.json"


# --------------------------------------------------------------------------------------------- P1: parameters
def load_params(path=ASSEMBLY_CONFIG) -> dict:
    """Flat dict ``section.name -> value`` of the assembly YAML (every leaf is tag/source-checked by the tests)."""
    c = yaml.safe_load(open(path))
    out = {}
    for sec, body in c.items():
        if sec == "meta":
            continue
        for k, leaf in body.items():
            out[f"{sec}.{k}"] = leaf["value"]
    return out


def optimiser_inputs(design: dict, base_cfg: dict | None = None) -> dict:
    """Everything the optimiser decides, taken from best_design.json (plus eta_pmad and f_eol from the default baseline)."""
    from .config import load_config
    base = base_cfg or load_config()
    d = design["design"]
    p_bol_kw = d["P_IT_kW"] / (base["eta_pmad"] * base["f_eol"])         # array beginning-of-life power the optimiser sized (D: power chain)
    return dict(
        n_panels_cont=d["N_panels"], A_face_m2=d["A_face_m2"], width_mm=design["width_m"] * 1e3, length_mm=design["length_m"] * 1e3,
        m_panel_metal_kg=design["per_panel"]["m_metal_kg"], m_panel_tube_kg=design["per_panel"]["m_tube_kg"],
        m_overhead_kg=d["m_overhead_kg"], overhead_kg_per_face_m2=d["m_overhead_kg"] / d["A_face_m2"],
        m_radiator_kg=d["m_radiator_kg"], m_array_kg=d["m_array_kg"], m_total_kg=d["m_total_kg"],
        P_IT_kW=d["P_IT_kW"], P_array_bol_kW=p_bol_kw, SP_implied_W_per_kg=p_bol_kw * 1e3 / d["m_array_kg"], rho=design["rho_kg_m3"],
    )


# --------------------------------------------------------------------------------------------- layout numbers (no CAD needed)
def radiator_layout(opt: dict, prm: dict) -> dict:
    wings, across = prm["radiator.wings"], prm["radiator.panels_across_wing"]
    per_wing_cont = opt["n_panels_cont"] / wings
    along = math.ceil(per_wing_cont / across)
    n_built = wings * across * along
    gap = prm["radiator.panel_gap_m"] * 1e3
    return dict(wings=wings, across=across, along=along, n_built=n_built, n_cont=opt["n_panels_cont"], extra_panels_pct=(n_built / opt["n_panels_cont"] - 1) * 100,
                gap_mm=gap, wing_width_mm=across * (opt["width_mm"] + gap) - gap, wing_length_mm=along * (opt["length_mm"] + gap) - gap)


def array_layout(opt: dict, prm: dict) -> dict:
    wings, leaves, width = prm["array.wings"], prm["array.leaves_per_wing"], prm["array.wing_width_m"] * 1e3
    area_total = opt["P_array_bol_kW"] * 1e3 / prm["array.bol_power_density_W_m2"]
    area_wing = area_total / wings
    leaf_len_mm = area_wing / (width * 1e-3) / leaves * 1e3
    fold = prm["array.fold_across_width"]
    return dict(wings=wings, leaves=leaves, width_mm=width, leaf_len_mm=leaf_len_mm, area_total_m2=area_total, area_wing_m2=area_wing,
                wing_len_mm=leaves * leaf_len_mm, areal_density_kg_m2=opt["m_array_kg"] / area_total, fold=fold, stack_pitch_mm=prm["array.stack_pitch_m"] * 1e3,
                stowed_block_mm=(width / fold, leaf_len_mm, leaves * fold * prm["array.stack_pitch_m"] * 1e3))


# --------------------------------------------------------------------------------------------- P2: panel builder
def build_lite_panel(design: dict) -> dict:
    """Radiator panel for assembly use. Tubes, headers and stubs are exactly cad.build_panel's solids (same count, wall solved to the optimiser's tube mass).
    The stepped sheet (many boxes) is replaced by one uniform strip between each pair of tubes whose volume equals the stepped sheet's, so mass is unchanged
    and the STEP stays small. Returns parts, info (mm, kg), and the detailed result for reference."""
    from build123d import Box, Compound, Pos

    from . import cad
    R = cad.build_panel(design, rho=design["rho_kg_m3"])
    info = R["info"]
    nx, W, L = design["nx"], info["width_mm"], info["length_mm"]
    h = W / nx
    edges = [0] + [x for lohi in R["tubes"] for x in lohi] + [nx]
    spans = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2) if edges[i + 1] > edges[i]]
    free_area = sum((b - a) * h * L for a, b in spans)
    t_eq = info["volume_mm3"]["sheet"] / free_area
    strips = [Pos((a + b) / 2 * h, L / 2, 0) * Box((b - a) * h, L, t_eq) for a, b in spans]
    parts = dict(sheet=Compound(strips, label="sheet"), tubes=R["parts"]["tubes"], headers=R["parts"]["headers"], stubs=R["parts"]["stubs"])
    vol = {k: v.volume for k, v in parts.items()}
    bb = Compound(list(parts.values())).bounding_box()
    info2 = dict(t_equivalent_sheet_mm=t_eq, n_sheet_strips=len(strips), volume_mm3=vol, mass_kg={k: v * 1e-9 * design["rho_kg_m3"] for k, v in vol.items()},
                 mass_total_kg=sum(vol.values()) * 1e-9 * design["rho_kg_m3"], width_mm=W, length_mm=L,
                 bbox_mm=dict(x=(bb.min.X, bb.max.X), y=(bb.min.Y, bb.max.Y), z=(bb.min.Z, bb.max.Z)),
                 planform_mm2=sum((b - a) * h * L for a, b in spans) + sum((hi - lo) * h * L for lo, hi in R["tubes"]))
    return dict(parts=parts, info=info2, detailed=R)


# --------------------------------------------------------------------------------------------- transforms
def mat(R=np.eye(3), t=(0, 0, 0)):
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = t
    return M


def rot_y(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def to_location(M):
    from build123d import Location
    from OCP.gp import gp_Trsf
    from OCP.TopLoc import TopLoc_Location
    t = gp_Trsf()
    t.SetValues(*[float(M[i, j]) for i in range(3) for j in range(4)])
    return Location(TopLoc_Location(t))


def place(shape, M):
    """Rigid copy of ``shape`` (shares the underlying geometry, so repeated panels cost almost nothing)."""
    return shape.moved(to_location(M))


# --------------------------------------------------------------------------------------------- P3: deployed layout
def deployed_layout(opt: dict, prm: dict, rl: dict, al: dict, panel_bbox: dict) -> dict:
    """Deployed frame (mm): z toward the Sun, x along the array wings, y along the radiator wings, origin at the bus centre.
    Radiator panels lie in the plane x = 0 (plane contains nadir and the orbit normal; panel normal along x = the along-track direction. [t359 wording fix] The Sun is NOT exactly in this plane: it is out of the plane by up to 90 deg - beta (31 deg at beta 59), see docs/CAD_3D.md and env_leo.direct_sun_g; dawn-dusk orbit, Sun near the orbit normal, within 7.6 to 31 deg). Panel local x -> world z, local y -> world y (outward), local z -> world -x."""
    bx, by, bz = [v * 1e3 for v in prm["bus.size_xyz_m"]]
    W, L, gap = opt["width_mm"], opt["length_mm"], rl["gap_mm"]
    z_lo = -rl["wing_width_mm"] / 2
    y0 = by / 2 + 60.0                                        # 60 mm standoff from the bus wall (ESTIMATE)
    z_top = z_lo + rl["wing_width_mm"]
    panels = []
    for wing, sgn in enumerate((+1, -1)):
        Rw = rot_y(-90.0) if sgn > 0 else rot_z(180.0) @ rot_y(-90.0)
        for j in range(rl["along"]):
            for i in range(rl["across"]):
                y = y0 + j * (L + gap)
                z = z_lo + i * (W + gap)
                panels.append(dict(wing=wing, i=i, j=j, M=mat(Rw, (0.0, sgn * y, z))))
    z_arr = z_top + 250.0 + prm["array.thickness_deployed_m"] * 1e3 / 2
    leaves = []
    root = 250.0                                              # array root offset from the mast axis (ESTIMATE)
    for wing, sgn in enumerate((+1, -1)):
        for k in range(al["leaves"]):
            xc = sgn * (root + (k + 0.5) * al["leaf_len_mm"])
            leaves.append(dict(wing=wing, k=k, center=(xc, 0.0, z_arr), size=(al["leaf_len_mm"], al["width_mm"], prm["array.thickness_deployed_m"] * 1e3)))
    return dict(bus=dict(size=(bx, by, bz)), rack=dict(size=tuple(v * 1e3 for v in prm["bus.rack_size_xyz_m"])), panels=panels, leaves=leaves,
                y0=y0, z_top=z_top, z_arr=z_arr, mast=dict(od=200.0, z0=bz / 2, z1=z_arr),
                trunk=dict(od=prm["radiator.trunk_od_m"] * 1e3, length=rl["wing_length_mm"], y0=y0, zs=(z_lo - 40.0, z_top + 40.0)),
                span_array_mm=2 * (root + al["wing_len_mm"]), height_mm=z_arr + 5.0 - (-max(bz / 2, abs(z_lo))), radiator_span_y_mm=2 * (y0 + rl["wing_length_mm"]))


# --------------------------------------------------------------------------------------------- P4: stowed layout and envelope
def envelope_profile(prm: dict):
    """(station, radius) polyline in metres: cylinder to the end of its height, then the cited ogive table."""
    R0, H0 = prm["launch_vehicle.payload_envelope_diameter_m"] / 2, prm["launch_vehicle.payload_envelope_cylinder_height_m"]
    og = [tuple(p) for p in prm["launch_vehicle.payload_envelope_ogive"]]
    return [(0.0, R0), (H0, R0)] + [p for p in og if p[0] > H0]


def envelope_radius(s_m, prof):
    """Envelope radius (m) at station s (m); 0 outside [0, top]. Radius is non-increasing in s."""
    st, r = zip(*prof)
    return float(np.interp(s_m, st, r)) if 0 <= s_m <= st[-1] else 0.0


def envelope_volume_m3(prof, n=4000):
    st, r = zip(*prof)
    s = np.linspace(0, st[-1], n + 1)
    rr = np.interp(s, st, r)
    return float(np.trapezoid(np.pi * rr ** 2, s))


def stowed_layout(opt: dict, prm: dict, rl: dict, al: dict, panel_bbox: dict, cols: int = 8, top_tier: int = 0) -> dict:
    """Stowed items, stacked along the vehicle axis (z, mm from the payload interface plane). Every item is a box in the vehicle frame (x, y, z).
    ``top_tier`` (P19/C1a, default 0 = unchanged): that many radiator stacks are taken out of the grid and laid side by side on the centre line above it, one clearance higher.
    It is the fix for the corner stacks of a full grid that miss the 8 m cylinder by a few mm when the stack top passes station 8 m (the ogive starts)."""
    clr = prm["launch_vehicle.clearance_m"] * 1e3
    pitch = prm["radiator.stack_pitch_m"] * 1e3
    items = []
    bx, by, bz = [v * 1e3 for v in prm["bus.size_xyz_m"]]
    z = 300.0                                                  # 0.3 m adapter and separation-system allowance (ESTIMATE)
    items.append(dict(name="bus", kind="bus", lo=(-bx / 2, -by / 2, z), hi=(bx / 2, by / 2, z + bz)))
    z += bz + clr
    # array blocks: stowed leaf = half the leaf width (fold across width), stacked at the array pitch
    sbw, sbl, sbt = al["stowed_block_mm"]
    for wing in range(al["wings"]):
        items.append(dict(name=f"array_wing_{wing}", kind="array", lo=(-sbw / 2, -sbl / 2, z), hi=(sbw / 2, sbl / 2, z + sbt)))
        z += sbt + clr
    # radiator stacks: one accordion string of `along` panels per block, panel footprint from the CAD bounding box
    px = panel_bbox["x"][1] - panel_bbox["x"][0]
    py = panel_bbox["y"][1] - panel_bbox["y"][0]
    pt = panel_bbox["z"][1] - panel_bbox["z"][0]
    th = (rl["along"] - 1) * pitch + pt
    n_blocks = rl["wings"] * rl["across"]
    n_main = n_blocks - int(top_tier)
    rows = math.ceil(n_main / cols)
    gx, gy = px + 10.0, py + 10.0                              # 10 mm between neighbouring stacks (ESTIMATE)
    x0, y0 = -(cols * gx) / 2, -(rows * gy) / 2
    for b in range(n_main):
        r_, c_ = divmod(b, cols)
        lo = (x0 + c_ * gx + 5.0, y0 + r_ * gy + 5.0, z)
        items.append(dict(name=f"rad_stack_{b:02d}", kind="radiator", lo=lo, hi=(lo[0] + px, lo[1] + py, z + th), panel_origin=(lo[0] - panel_bbox["x"][0], lo[1] - panel_bbox["y"][0]),
                          z_first=z - panel_bbox["z"][0]))
    z += th
    if top_tier:
        z += clr
        xt0 = -(top_tier * gx) / 2
        for j in range(int(top_tier)):
            b = n_main + j
            lo = (xt0 + j * gx + 5.0, -py / 2, z)
            items.append(dict(name=f"rad_stack_{b:02d}", kind="radiator", lo=lo, hi=(lo[0] + px, lo[1] + py, z + th), panel_origin=(lo[0] - panel_bbox["x"][0], lo[1] - panel_bbox["y"][0]),
                              z_first=z - panel_bbox["z"][0]))
        z += th
    return dict(items=items, top_mm=z, pitch=pitch, panel_thickness=pt, stack_thickness=th)


FIT_TOL_M = 1e-9                                       # a box placed exactly on the limit may miss it by floating-point round-off (4e-16 m); 1 nm is no physical slack


def fit_checks(layout: dict, prm: dict) -> dict:
    """Analytic fit of every stowed box in the shrunk envelope. Radius is non-increasing, so a box fits iff its top corners do."""
    clr = prm["launch_vehicle.clearance_m"]
    prof = envelope_profile(prm)
    top = prof[-1][0]
    rows = []
    for it in layout["items"]:
        lo, hi = [np.array(v) * 1e-3 for v in (it["lo"], it["hi"])]
        rmax = math.hypot(max(abs(lo[0]), abs(hi[0])), max(abs(lo[1]), abs(hi[1])))
        r_allow = envelope_radius(hi[2], prof) - clr
        rows.append(dict(name=it["name"], kind=it["kind"], r_corner_m=rmax, r_allowed_m=r_allow, radial_margin_m=r_allow - rmax,
                         axial_margin_top_m=top - clr - hi[2], axial_margin_bottom_m=lo[2] - clr, size_m=tuple(hi - lo)))
    return dict(rows=rows, min_radial_margin_m=min(r["radial_margin_m"] for r in rows), min_axial_margin_m=min(min(r["axial_margin_top_m"], r["axial_margin_bottom_m"]) for r in rows),
                fits=all(r["radial_margin_m"] >= -FIT_TOL_M and r["axial_margin_top_m"] >= -FIT_TOL_M and r["axial_margin_bottom_m"] >= -FIT_TOL_M for r in rows))


def pair_gaps(layout: dict) -> dict:
    """Smallest axis-aligned separation between any two stowed boxes (mm); negative means overlap."""
    its = layout["items"]
    lo = np.array([i["lo"] for i in its])
    hi = np.array([i["hi"] for i in its])
    n = len(its)
    worst = (1e18, None)
    for a in range(n):
        for b in range(a + 1, n):
            sep = np.maximum(lo[a] - hi[b], lo[b] - hi[a])         # per-axis separation; the pair is apart if any axis is positive
            g = float(sep.max())
            if g < worst[0]:
                worst = (g, (its[a]["name"], its[b]["name"]))
    return dict(min_gap_mm=worst[0], pair=worst[1])


def slot_check(layout: dict, prm: dict) -> dict:
    """Secondary, UNOFFICIAL check against the third-party dispenser-slot numbers (0.8 x 7.3 m, V2-era, ESTIMATE): for each item, can some orientation pass
    the slot (smallest dimension <= slot height, middle dimension <= slot width)?"""
    sh, sw = prm["launch_vehicle.slot_height_m"], prm["launch_vehicle.slot_width_m"]
    rows = []
    for it in layout["items"]:
        d = sorted((np.array(it["hi"]) - np.array(it["lo"])) * 1e-3)
        rows.append(dict(name=it["name"], kind=it["kind"], dims_m=tuple(d), passes=bool(d[0] <= sh and d[1] <= sw)))
    kinds = {}
    for r in rows:
        k = kinds.setdefault(r["kind"], dict(passes=True, thinnest_m=1e9))
        k["passes"] &= r["passes"]
        k["thinnest_m"] = min(k["thinnest_m"], r["dims_m"][0])
    return dict(rows=rows, by_kind=kinds, slot_h_m=sh, slot_w_m=sw, all_pass=all(r["passes"] for r in rows))


# --------------------------------------------------------------------------------------------- P5: mass reconciliation
def reconcile(opt: dict, prm: dict, rl: dict, al: dict, panel: dict, n_panels_cad: int, leaf_area_cad_m2: float) -> dict:
    """CAD-side mass from CAD quantities (counted solids, their volumes and areas) vs the optimiser's mass lines."""
    rho = opt["rho"]
    m_panels = n_panels_cad * panel["info"]["mass_total_kg"]
    face_area_m2 = n_panels_cad * 2 * panel["info"]["planform_mm2"] * 1e-6          # both faces of every panel's radiating planform
    m_overhead = opt["overhead_kg_per_face_m2"] * face_area_m2
    m_array = al["areal_density_kg_m2"] * leaf_area_cad_m2
    cad_rad, cad_arr = m_panels + m_overhead, m_array
    tol = prm["reconcile.mass_tolerance"]
    rows = [("radiator metal + tubes", m_panels, opt["m_radiator_kg"] - opt["m_overhead_kg"]), ("radiator overhead allowance", m_overhead, opt["m_overhead_kg"]),
            ("radiator total", cad_rad, opt["m_radiator_kg"]), ("array", cad_arr, opt["m_array_kg"]), ("total (radiator + array)", cad_rad + cad_arr, opt["m_total_kg"])]
    out = [dict(line=n, cad_kg=c, optimiser_kg=o, diff_pct=(c / o - 1) * 100) for n, c, o in rows]
    return dict(rows=out, total_diff_pct=out[-1]["diff_pct"], within_tolerance=abs(out[-1]["diff_pct"]) <= tol * 100, tolerance_pct=tol * 100,
                face_area_m2=face_area_m2, n_panels_cad=n_panels_cad, leaf_area_m2=leaf_area_cad_m2,
                geometric_metal_share_of_radiator=m_panels / cad_rad)


# --------------------------------------------------------------------------------------------- build the CAD solids and meshes
def _tess(shape, tol=0.05):
    v, f = shape.tessellate(tol, 0.2)
    return np.array([[p.X, p.Y, p.Z] for p in v], float), np.array(f, int)


def panel_meshes(panel: dict) -> dict:
    """Local-frame triangle meshes of the four panel parts (tessellated once, reused for every instance)."""
    return {k: _tess(v) for k, v in panel["parts"].items()}


def build_envelope_solid(prm: dict, shrink_m: float = 0.0):
    """Revolved Starship payload envelope (mm), radius reduced by ``shrink_m`` and trimmed by the same amount at both ends."""
    from build123d import Axis, BuildLine, BuildPart, BuildSketch, Plane, Polyline, make_face, revolve
    prof = envelope_profile(prm)
    top = prof[-1][0]
    s0, s1 = shrink_m, top - shrink_m
    inner = [(r - shrink_m, s) for s, r in prof if s0 < s < s1]
    pts = [(0.0, s0), (envelope_radius(s0, prof) - shrink_m, s0)] + inner + [(envelope_radius(s1, prof) - shrink_m, s1), (0.0, s1)]
    pts = [(r * 1e3, s * 1e3) for r, s in pts]
    with BuildPart() as bp:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        revolve(axis=Axis.Z)
    return bp.part


def build_deployed(design: dict, prm: dict | None = None, panel: dict | None = None) -> dict:
    from build123d import Box, Compound, Cylinder, Pos, Rot
    prm = prm or load_params()
    opt = optimiser_inputs(design)
    rl, al = radiator_layout(opt, prm), array_layout(opt, prm)
    panel = panel or build_lite_panel(design)
    lay = deployed_layout(opt, prm, rl, al, panel["info"]["bbox_mm"])
    groups = []
    for wing in range(rl["wings"]):
        kids = []
        for q in lay["panels"]:
            if q["wing"] != wing:
                continue
            kids.append(Compound(children=[place(s, q["M"]) for s in panel["parts"].values()], label=f"panel_w{wing}_{q['i']:02d}_{q['j']:02d}"))
        groups.append(Compound(children=kids, label=f"radiator_wing_{wing}"))
    leaves = {w: [] for w in range(al["wings"])}
    for lf in lay["leaves"]:
        leaves[lf["wing"]].append(Pos(*lf["center"]) * Box(*lf["size"]))
    arr = [Compound(children=v, label=f"array_wing_{w}") for w, v in leaves.items()]
    bx, by, bz = lay["bus"]["size"]
    wall = 20.0
    bus = Box(bx, by, bz) - Box(bx - 2 * wall, by - 2 * wall, bz - 2 * wall)
    bus.label = "bus_shell_envelope"
    rack = Box(*lay["rack"]["size"])
    rack.label = "rack_envelope"
    mast = Pos(0, 0, (lay["mast"]["z0"] + lay["mast"]["z1"]) / 2) * Cylinder(lay["mast"]["od"] / 2, lay["mast"]["z1"] - lay["mast"]["z0"])
    mast.label = "mast"
    trunks = []
    for sgn in (1, -1):
        for zz in lay["trunk"]["zs"]:
            c = Pos(0, sgn * (lay["trunk"]["y0"] + lay["trunk"]["length"] / 2), zz) * (Rot(90, 0, 0) * Cylinder(lay["trunk"]["od"] / 2, lay["trunk"]["length"]))
            trunks.append(c)
    trunk = Compound(children=trunks, label="trunk_manifolds_illustration")
    comp = Compound(children=groups + arr + [bus, rack, mast, trunk], label="rack_satellite_deployed")
    leaf_area = sum(max(f.area for f in s.faces()) for g in arr for s in g.solids()) * 1e-6
    n_panels = sum(len(g.children) for g in groups)
    return dict(compound=comp, opt=opt, prm=prm, rl=rl, al=al, panel=panel, layout=lay, n_panels=n_panels, leaf_area_m2=leaf_area, groups=groups, array=arr,
                bus=bus, rack=rack, mast=mast, trunk=trunk)


def build_stowed(design: dict, prm: dict | None = None, panel: dict | None = None) -> dict:
    from build123d import Box, Compound, Pos
    prm = prm or load_params()
    opt = optimiser_inputs(design)
    rl, al = radiator_layout(opt, prm), array_layout(opt, prm)
    panel = panel or build_lite_panel(design)
    sl = stowed_layout(opt, prm, rl, al, panel["info"]["bbox_mm"])
    solids, hulls, n_panels, leaf_area = [], {}, 0, 0.0
    for it in sl["items"]:
        lo, hi = np.array(it["lo"]), np.array(it["hi"])
        hull = Pos(*((lo + hi) / 2)) * Box(*(hi - lo))
        hull.label = it["name"] + "_hull"
        hulls[it["name"]] = hull
        if it["kind"] == "radiator":
            ox, oy = it["panel_origin"]
            kids = [Compound(children=[place(s, mat(np.eye(3), (ox, oy, it["z_first"] + k * sl["pitch"]))) for s in panel["parts"].values()], label=f"{it['name']}_p{k:02d}") for k in range(rl["along"])]
            n_panels += len(kids)
            solids.append(Compound(children=kids, label=it["name"]))
        elif it["kind"] == "array":
            sbw, sbl, sbt = al["stowed_block_mm"]
            nleaf = al["leaves"] * al["fold"]
            lv = [Pos((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + (k + 0.5) * al["stack_pitch_mm"]) * Box(sbw, sbl, prm["array.thickness_deployed_m"] * 1e3) for k in range(nleaf)]
            leaf_area += nleaf * sbw * sbl * 1e-6
            solids.append(Compound(children=lv, label=it["name"]))
        else:
            h = hulls[it["name"]]
            wall = 20.0
            sh = h - Pos(*((lo + hi) / 2)) * Box(*(hi - lo - 2 * wall))
            sh.label = "bus_shell_envelope"
            solids.append(sh)
    rack = Pos(0, 0, (sl["items"][0]["lo"][2] + sl["items"][0]["hi"][2]) / 2) * Box(*[v * 1e3 for v in prm["bus.rack_size_xyz_m"]])
    rack.label = "rack_envelope"
    comp = Compound(children=solids + [rack], label="rack_satellite_stowed")
    return dict(compound=comp, opt=opt, prm=prm, rl=rl, al=al, panel=panel, layout=sl, hulls=hulls, n_panels=n_panels, leaf_area_m2=leaf_area, rack=rack)


def _vol(x) -> float:
    """Volume of a boolean result, which build123d may return as a Shape, a ShapeList or None."""
    if x is None:
        return 0.0
    return float(sum(s.volume for s in x)) if isinstance(x, (list, tuple)) or hasattr(x, "__iter__") and not hasattr(x, "volume") else float(x.volume)


def cad_interference(stowed: dict, tol_mm3: float = 1.0) -> dict:
    """Boolean intersections between all stowed hulls (box per stack) plus the rack inside the bus shell. Returns the worst overlap volume (mm3)."""
    names = list(stowed["hulls"])
    worst, pair = 0.0, None
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            ha, hb = stowed["hulls"][names[a]], stowed["hulls"][names[b]]
            bba, bbb = ha.bounding_box(), hb.bounding_box()
            if bba.max.X < bbb.min.X or bbb.max.X < bba.min.X or bba.max.Y < bbb.min.Y or bbb.max.Y < bba.min.Y or bba.max.Z < bbb.min.Z or bbb.max.Z < bba.min.Z:
                continue
            vol = _vol(ha.intersect(hb))
            if vol > worst:
                worst, pair = vol, (names[a], names[b])
    return dict(worst_overlap_mm3=worst, pair=pair, ok=worst <= tol_mm3)


def cad_in_envelope(stowed: dict) -> dict:
    """CAD containment: every stowed hull lies inside the clearance-shrunk revolved envelope (volume of hull minus envelope is zero)."""
    env = build_envelope_solid(stowed["prm"], shrink_m=stowed["prm"]["launch_vehicle.clearance_m"])
    out = []
    for n, h in stowed["hulls"].items():
        out.append((n, h.volume - _vol(env.intersect(h))))
    worst = max(out, key=lambda r: r[1])
    return dict(worst_outside_mm3=worst[1], item=worst[0], ok=worst[1] <= 1.0, envelope_volume_m3=env.volume * 1e-9)


# --------------------------------------------------------------------------------------------- meshes (for renders, STL, GLB)
def _transform(V, M):
    return V @ M[:3, :3].T + M[:3, 3]


def _box_mesh(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    V = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return V, F


def _merge(parts):
    Vs, Fs, off = [], [], 0
    for V, F in parts:
        Vs.append(V)
        Fs.append(F + off)
        off += len(V)
    return np.vstack(Vs), np.vstack(Fs)


def pose_meshes(asm: dict, pose: str, plates_only: bool = False, panel_filter=None) -> list[dict]:
    """Merged triangle meshes of a built pose, grouped by kind. ``plates_only`` replaces each panel by its two-face plate (light STL)."""
    lay = asm["layout"]
    pm = panel_meshes(asm["panel"])
    out = []
    if pose == "deployed":
        mats = [q["M"] for q in lay["panels"] if panel_filter is None or panel_filter(q)]
    else:
        pitch, ths = lay["pitch"], asm["rl"]["along"]
        mats = [mat(np.eye(3), (it["panel_origin"][0], it["panel_origin"][1], it["z_first"] + k * pitch)) for it in lay["items"] if it["kind"] == "radiator" for k in range(ths)]
    bb = asm["panel"]["info"]["bbox_mm"]
    if plates_only:
        W, L = asm["panel"]["info"]["width_mm"], asm["panel"]["info"]["length_mm"]
        base = {"radiator_panels": _box_mesh((0, 0, -3.5), (W, L, 3.5))}
    else:
        base = {f"radiator_{k}": pm[k] for k in ("sheet", "tubes", "headers", "stubs")}
    for name, (V, F) in base.items():
        out.append(dict(name=name, kind="radiator", V=None, F=None, parts=[(_transform(V, M), F) for M in mats]))
    if pose == "deployed":
        leaf = [_box_mesh(np.array(lf["center"]) - np.array(lf["size"]) / 2, np.array(lf["center"]) + np.array(lf["size"]) / 2) for lf in lay["leaves"]]
        bx, by, bz = lay["bus"]["size"]
        out.append(dict(name="array", kind="array", parts=leaf))
        out.append(dict(name="bus", kind="bus", parts=[_box_mesh((-bx / 2, -by / 2, -bz / 2), (bx / 2, by / 2, bz / 2))]))
        rx, ry, rz = lay["rack"]["size"]
        out.append(dict(name="rack", kind="rack", parts=[_box_mesh((-rx / 2, -ry / 2, -rz / 2), (rx / 2, ry / 2, rz / 2))]))
        out.append(dict(name="mast", kind="mast", parts=[_tess(asm["mast"])]))
        out.append(dict(name="trunks", kind="trunk", parts=[_tess(s) for s in asm["trunk"].solids()]))
    else:
        al = asm["al"]
        lv = []
        for it in lay["items"]:
            if it["kind"] == "array":
                lo, hi = np.array(it["lo"]), np.array(it["hi"])
                for k in range(al["leaves"] * al["fold"]):
                    zc = lo[2] + (k + 0.5) * al["stack_pitch_mm"]
                    t = asm["prm"]["array.thickness_deployed_m"] * 1e3
                    lv.append(_box_mesh((lo[0], lo[1], zc - t / 2), (hi[0], hi[1], zc + t / 2)))
        out.append(dict(name="array", kind="array", parts=lv))
        bus = [it for it in lay["items"] if it["kind"] == "bus"][0]
        out.append(dict(name="bus", kind="bus", parts=[_box_mesh(bus["lo"], bus["hi"])]))
        out.append(dict(name="rack", kind="rack", parts=[_tess(asm["rack"])]))
    for o in out:
        o["V"], o["F"] = _merge(o.pop("parts"))
    return out
