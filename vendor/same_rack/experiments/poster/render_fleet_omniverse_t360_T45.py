"""[t337 COPY of render_fleet_omniverse_sync_T45.py for the ADOPTED design (A6L radiators 228 panels / 490 m2, 13 satellites per launch, component pod, panel mesh lengthened by FLEET_LSCALE). Original unchanged.]  [t310u COPY of render_fleet_omniverse_hide13_T45.py: cable-synchronised accordion (FLEET_SYNC=1), yoke boom (FLEET_YOKE=1), sequence + deck-graze fix switches read by fleet_kin_T45; overlay text updated. Original scripts unchanged.]  [ COPY with FLEET_HIDE13 option; original render_fleet_omniverse.py unchanged]  FLEET-DEPLOY clip render (Nov 1 2026, []): 14 O5 satellites (229 radiator panels each) released from a SCHEMATIC dispenser bay and unfolded, rendered with Isaac Sim 6.0 (headless, GB10 desktop).
Poses come from fleet_kin_T45.py (kinematic/analytic, array accordion = Newton replay; every release and hinge parameter ASSUMED / ESTIMATE, see docs/FLEET_DEPLOY_RENDER_T45.md). Look = render_omniverse.py (Blue Marble Earth, credit in CREDITS.md).
Run through run_fleet_render.sh (start-up pinned to 4 CPUs): python render_fleet_omniverse.py spp W H frame0 frame1 outdir
Resumable: frames whose PNG exists are skipped. Pre-flight design study, NOT a flight design, NOT a statement of how any launch provider would deploy."""
import os, sys, time, json
os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")   # the author accepted the NVIDIA Omniverse licence terms (2026-10-30 11:39 Taipei)
import pathlib
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
SPP = int(sys.argv[1]); W = int(sys.argv[2]); H = int(sys.argv[3]); F0 = int(sys.argv[4]); F1 = int(sys.argv[5]); OUTD = pathlib.Path(sys.argv[6]); OUTD.mkdir(parents=True, exist_ok=True)
T0 = time.time()
from isaacsim import SimulationApp  # noqa: E402
app = SimulationApp({"headless": True, "width": W, "height": H, "renderer": "RaytracedLighting"}, experience=os.environ.get("OMNI_EXPERIENCE", ""))
print(f"app up {time.time() - T0:.0f} s", flush=True)
def widen():
    allc = set(range(os.cpu_count()))
    for t in os.listdir("/proc/self/task"):
        try: os.sched_setaffinity(int(t), allc)
        except Exception: pass
widen()
import carb  # noqa: E402
import omni.usd  # noqa: E402
import omni.replicator.core as rep  # noqa: E402
from pxr import Usd, UsdGeom, UsdShade, Gf, Sdf, Vt, UsdLux  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import fleet_kin_T45 as K  # noqa: E402
# [t361] OPT-IN simplified-geometry test flags (all default OFF = identical to the t360 render): FLEET_SIMPLE_POD=1 plain pod box (no 6 coloured blocks); FLEET_NO_STUBHDR=1 radiator stub + header meshes off (sheet + tubes kept); FLEET_RAIL_FADE=1 dispenser rails drawn faint (opacity FLEET_RAIL_OP, default 0.35) while stowed and faded to 0 after release instead of retract + abrupt hide (fade frames FLEET_RAIL_FADE_F0/F1, default 4/40)
SIMPLE_POD = os.environ.get("FLEET_SIMPLE_POD", "0") == "1"; NO_STUBHDR = os.environ.get("FLEET_NO_STUBHDR", "0") == "1"; RAIL_FADE = os.environ.get("FLEET_RAIL_FADE", "0") == "1"; NO_RAILS = os.environ.get("FLEET_NO_RAILS", "0") == "1"   # FLEET_NO_RAILS=1: the 4 ASSUMED schematic dispenser rails are not created at all (the author, Nov 2 2026 7:41 PM PST)
GEOM = {}
S = 1e-3
ctx = omni.usd.get_context(); ctx.new_stage(); stage = ctx.get_stage()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z); UsdGeom.SetStageMetersPerUnit(stage, 1.0)
root = UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(root.GetPrim())

ASSETS = ROOT / "results" / "omniverse" / "assets"
TEXDIR = ROOT / "results" / "omniverse"


def tex_input(sh, name, path, out_type, srgb=True, scale=None, bias=None, uvs=1.0):
    rd = UsdShade.Shader.Define(stage, f"{sh.GetPath()}_{name}"); rd.CreateIdAttr("UsdUVTexture")
    rd.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(str(path))
    rd.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB" if srgb else "raw")
    rd.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat"); rd.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
    if scale is not None: rd.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(*scale))
    if bias is not None: rd.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(*bias))
    rdr = UsdShade.Shader.Define(stage, f"{sh.GetPath()}_{name}_st"); rdr.CreateIdAttr("UsdPrimvarReader_float2")
    rdr.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st"); rdr.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    rd.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(rdr.ConnectableAPI(), "result")
    o = rd.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    return rd, o


def _ef(n, d): return float(os.environ.get(n, d))   # [t365] opt-in material toning knobs (all default to the previous values)
_RA = _ef("OMNI_RAD_ALBEDO", 0.86); _TS = _ef("OMNI_TUBE_SCALE", 1.0)
def material(name, color, rough=0.5, metal=0.0, emissive=None, opacity=1.0, coat=0.0, diffuse_tex=None, normal_tex=None, normal_scale=1.0):
    mat = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
    sh = UsdShade.Shader.Define(stage, f"/World/Looks/{name}/Shader")
    sh.CreateIdAttr("UsdPreviewSurface")
    d_in = sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
    if diffuse_tex is None:
        d_in.Set(Gf.Vec3f(*color))
    else:
        _, o = tex_input(sh, "diff", diffuse_tex, "rgb", srgb=True); d_in.ConnectToSource(o)
    if normal_tex is not None:
        k = normal_scale
        _, o = tex_input(sh, "nrm", normal_tex, "rgb", srgb=False, scale=(2 * k, 2 * k, 2 * k, 1), bias=(-k, -k, -k, 0))
        sh.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(o)
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(rough)
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metal)
    sh.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(coat)
    sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
    if emissive is not None:
        sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emissive))
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    return mat


# ---- c17: procedural textures (solar-cell grid, gold insulation crinkle normal map) ----
def make_cell_tex(path, n=1024, cells=4):
    """Tile of cells x cells silicon cells: dark-blue cell face, thin silver fingers + 3 bus bars, light gaps between cells (4 x 4 cells = 0.8 m at the 0.2 m pitch used below)."""
    im = np.zeros((n, n, 3), np.float32); pitch = n // cells
    yy, xx = np.mgrid[0:n, 0:n]
    lx = (xx % pitch) / pitch; ly = (yy % pitch) / pitch
    base = np.array([0.020, 0.045, 0.19], np.float32)
    im[:] = base * (0.92 + 0.16 * (1 - ly))[..., None]      # slight gradient across each cell
    fingers = (np.abs(((lx * 40) % 1.0) - 0.5) > 0.47)       # fine grid fingers
    im[fingers] = im[fingers] * 0.55 + np.array([0.30, 0.32, 0.38]) * 0.45
    for bx in (0.2, 0.5, 0.8):                               # 3 bus bars
        m = np.abs(lx - bx) < 0.012; im[m] = np.array([0.62, 0.64, 0.70])
    gap = (lx < 0.012) | (lx > 0.988) | (ly < 0.012) | (ly > 0.988)   # inter-cell gaps (backing sheet)
    im[gap] = np.array([0.50, 0.52, 0.55])
    cell_id = (xx // pitch) + (yy // pitch) * cells          # per-cell tint variation
    rr = np.random.default_rng(3).random(cells * cells).astype(np.float32)
    im *= (0.93 + 0.14 * rr[cell_id])[..., None]
    Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).save(path)


def make_crinkle_normal(path, n=1024):
    """Gold MLI crinkle: sum of random-direction ridged waves + low-frequency bumps -> height -> tangent-space normal map (tileable)."""
    r = np.random.default_rng(11)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    h = np.zeros((n, n), np.float32)
    for _ in range(60):
        kx, ky = r.integers(-14, 15, 2); 
        if kx == 0 and ky == 0: continue
        ph = r.random() * 6.28; amp = r.random() ** 2 / (1 + 0.15 * np.hypot(kx, ky))
        w = np.sin(2 * np.pi * (kx * xx + ky * yy) + ph)
        h += amp * (1 - np.abs(w))                            # ridged
    for _ in range(40):
        kx, ky = r.integers(-40, 41, 2); ph = r.random() * 6.28
        h += 0.05 * np.sin(2 * np.pi * (kx * xx + ky * yy) + ph)
    h = (h - h.mean()) / (h.std() + 1e-6)
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * n / 40; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * n / 40
    nz = 1.0 / np.sqrt(1 + gx ** 2 + gy ** 2); nx = -gx * nz; ny = -gy * nz
    Image.fromarray(((np.stack([nx, ny, nz], -1) * 0.5 + 0.5) * 255).astype(np.uint8)).save(path)


CELL_TEX = TEXDIR / "solar_cells_v3.png"; CELL_TILE_M = 0.8
MLI_NRM = TEXDIR / "mli_crinkle_normal_v3.png"; MLI_TILE_M = 1.0
make_cell_tex(CELL_TEX); make_crinkle_normal(MLI_NRM)

MAT = dict(
    radiator_sheet=material("rad_white", tuple(_RA * c / 0.86 for c in (0.86, 0.87, 0.86)), rough=_ef("OMNI_RAD_ROUGH", 0.55)),   # [t365] OMNI_RAD_ALBEDO (default 0.86 = unchanged) tones the white thermal paint to light grey              # Z-93-like white thermal paint (illustrative albedo)
    radiator_tubes=material("tube_al", tuple(_TS * c for c in (0.78, 0.79, 0.82)), rough=_ef("OMNI_TUBE_ROUGH", 0.28), metal=1.0),     # aluminium tubes
    radiator_headers=material("hdr_al", (0.62, 0.64, 0.68), rough=0.35, metal=1.0),
    radiator_stubs=material("stub_al", (0.66, 0.68, 0.72), rough=0.35, metal=1.0),
    array=material("cells", (0.02, 0.05, 0.24), rough=_ef("OMNI_ARR_ROUGH", 0.16), metal=0.15, coat=_ef("OMNI_ARR_COAT", 0.9), diffuse_tex=CELL_TEX),   # cell grid texture under glass-like clearcoat
    bus=material("bus_mli", (1.0, 0.77, 0.34), rough=0.5, metal=1.0, normal_tex=MLI_NRM, normal_scale=float(os.environ.get("OMNI_CRINKLE", "1.0"))),   # gold (Au F0) + crinkle normal map
    rack=material("rack", (0.12, 0.55, 0.30), rough=0.4),
    mast=material("mast", (0.7, 0.7, 0.72), rough=0.3, metal=1.0),
    trunks=material("trunk", (0.72, 0.74, 0.78), rough=0.3, metal=1.0),
)


# ================================================================= fleet scene
A = np.load(ROOT / "results" / "fleet" / "fleet_assets_T45.npz")
LS_ = float(os.environ.get("FLEET_LSCALE", "1.0"))   # [t337] A6L: every radiator panel 0.43 % longer (panel local y = length)
def PV(k):
    v = A[f"panel_{k}_V"].astype(np.float64).copy(); v[:, 1] *= LS_; return v
def merge(keys):
    Vs = []; Fs = []; o = 0
    for k in keys: v = A[f"panel_{k}_V"].astype(np.float64); f = A[f"panel_{k}_F"]; Vs.append(v); Fs.append(f + o); o += len(v)
    return np.concatenate(Vs), np.concatenate(Fs)
def add_mesh_at(path, V, F, mat, uv=False, uv_tile=1.0):
    p = UsdGeom.Mesh.Define(stage, path)
    p.CreatePointsAttr(Vt.Vec3fArray.FromNumpy((V * S).astype(np.float32))); p.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(F), 3, np.int32)))
    p.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(F.reshape(-1).astype(np.int32))); p.CreateSubdivisionSchemeAttr("none"); p.CreateDoubleSidedAttr(True)
    if uv:
        P = (V[F] * S); nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); ax = np.abs(nrm).argmax(1)
        u = np.where((ax == 0)[:, None], P[..., 1], P[..., 0]); v = np.where((ax == 2)[:, None], P[..., 1], P[..., 2])
        pv = UsdGeom.PrimvarsAPI(p).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying); pv.Set(Vt.Vec2fArray.FromNumpy((np.stack([u, v], -1).reshape(-1, 2) / uv_tile).astype(np.float32)))
    UsdShade.MaterialBindingAPI.Apply(p.GetPrim()).Bind(mat); return p
def box_mesh(sx, sy, sz):   # centred box, mm
    c = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]) * np.array([sx, sy, sz])
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    F = np.array([t for a in q for t in ((a[0], a[1], a[2]), (a[0], a[2], a[3]))], np.int32); return c, F
def instancer(name, protos_paths, n, vis_extent=3000.0):
    pi = UsdGeom.PointInstancer.Define(stage, f"/World/{name}")
    pi.CreatePrototypesRel().SetTargets([Sdf.Path(p) for p in protos_paths])
    pi.CreateProtoIndicesAttr(Vt.IntArray.FromNumpy(np.zeros(n, np.int32)))
    pi.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(-vis_extent, -vis_extent, -vis_extent), Gf.Vec3f(vis_extent, vis_extent, vis_extent)]))
    return pi
NS = K.Fleet().n   # [t337] 13 satellites per launch (was 14)
NPAN, NPLT, NBUS = K.NPAN_TOT * NS, 2 * K.NLEAF * K.NSEC * NS, NS
for n_ in ("inst_panel", "inst_plate", "inst_bus", "inst_yoke", "inst_pod"): UsdGeom.PointInstancer.Define(stage, f"/World/{n_}")
Vs, Fs = PV("sheet"), A["panel_sheet_F"]
UsdGeom.Xform.Define(stage, "/World/inst_panel/panel")
add_mesh_at("/World/inst_panel/panel/sheet", Vs, Fs, MAT["radiator_sheet"])
GEOM["panel_sheet_tris"] = len(A["panel_sheet_F"])
for k, mk in (("tubes", "radiator_tubes"), ("headers", "radiator_headers"), ("stubs", "radiator_stubs")):
    if NO_STUBHDR and k in ("headers", "stubs"): GEOM[f"panel_{k}_tris"] = 0; continue   # [t361] opt-in
    GEOM[f"panel_{k}_tris"] = len(A[f"panel_{k}_F"])
    add_mesh_at(f"/World/inst_panel/panel/{k}", (K.trim_stub_V(PV(k)) if k == "stubs" else PV(k)), A[f"panel_{k}_F"], MAT[mk])     # [t316u] FLEET_STUBTRIM
UsdGeom.Xform.Define(stage, "/World/inst_plate/plate"); V_, F_ = box_mesh(K.LEAF * 1e3, K.SECW * 1e3, K.TH_ARR * 1e3)
add_mesh_at("/World/inst_plate/plate/m", V_, F_, MAT["array"], uv=True, uv_tile=CELL_TILE_M)
UsdGeom.Xform.Define(stage, "/World/inst_bus/bus"); V_, F_ = box_mesh(*(K.BUS * 1e3))
add_mesh_at("/World/inst_bus/bus/m", V_, F_, MAT["bus"], uv=True, uv_tile=MLI_TILE_M)
UsdGeom.Xform.Define(stage, "/World/inst_yoke/yoke"); V_, F_ = box_mesh(*(K.YOKE_BOX * 1e3))   # [t310u] yoke boom, ASSUMED 0.25 x 0.10 m visual only
add_mesh_at("/World/inst_yoke/yoke/m", V_, F_, MAT["mast"])
# [t337] component pod (ASSUMED, illustrative): rigid box on the bus anti-Sun face; body drawn 5 mm inside the pod envelope, 3 + 3 illustrative component blocks flush with the +-x faces (labelled in the overlay)
POD_DIMS = np.array(K.Fleet().sats[0].pod_box) * 1e3
UsdGeom.Xform.Define(stage, "/World/inst_pod/pod"); V_, F_ = box_mesh(*(POD_DIMS - 10.0)); add_mesh_at("/World/inst_pod/pod/body", V_, F_, MAT["mast"])
POD_BLK = {"podblk_a": material("podblk_a", (0.85, 0.35, 0.10), rough=0.45), "podblk_b": material("podblk_b", (0.15, 0.55, 0.85), rough=0.45), "podblk_c": material("podblk_c", (0.80, 0.80, 0.20), rough=0.45)}
GEOM["pod_body_tris"] = 12; GEOM["pod_block_tris"] = 0 if SIMPLE_POD else 6 * 12
for _sx in ((-1, 1) if not SIMPLE_POD else ()):   # [t361] FLEET_SIMPLE_POD=1: plain pod box, no coloured blocks
    for _j, (_nm, _dy, _dz, _cy, _cz) in enumerate([("podblk_a", 0.30, 0.50, -0.24, 0.30), ("podblk_b", 0.30, 0.50, 0.24, 0.30), ("podblk_c", 0.62, 0.40, 0.0, -0.36)]):
        V_, F_ = box_mesh(8.0, _dy * 1e3, _dz * 1e3); V_ = V_ + np.array([_sx * (POD_DIMS[0] / 2 - 4.0), _cy * 1e3, _cz * 1e3])
        add_mesh_at(f"/World/inst_pod/pod/blk_{'p' if _sx > 0 else 'm'}{_j}", V_, F_, POD_BLK[_nm])
PI = {"pod": instancer("inst_pod", ["/World/inst_pod/pod"], NS), "yoke": instancer("inst_yoke", ["/World/inst_yoke/yoke"], 2 * NS), "panel": instancer("inst_panel", ["/World/inst_panel/panel"], NPAN), "plate": instancer("inst_plate", ["/World/inst_plate/plate"], NPLT), "bus": instancer("inst_bus", ["/World/inst_bus/bus"], NBUS)}
# [t362] opt-in (default off): FLEET_HERO_SATS="3,8" keeps those satellites in full colour; every other satellite is drawn with ONE uniform "ghost" material
# (FLEET_GHOST_STYLE = grey | dark | glass | pale), so gold-on-gold / white-on-gold merging between non-hero satellites disappears. Kinematics untouched.
HERO = [int(x) for x in os.environ.get("FLEET_HERO_SATS", "").split(",") if x.strip()]
if HERO:
    _gs = os.environ.get("FLEET_GHOST_STYLE", "grey")
    _GS = dict(grey=((0.55, 0.57, 0.62), 0.85, 1.0), pale=((0.80, 0.82, 0.86), 0.9, 1.0), dark=((0.16, 0.17, 0.20), 0.8, 1.0), glass=((0.62, 0.66, 0.74), 0.7, 0.28))[_gs]
    _gm = material("ghost_mat", _GS[0], rough=_GS[1], opacity=_GS[2])
    # [t364] opt-in FLEET_FADE_TABLE=<json {"frames": {"<output frame>": {"<sat>": alpha}}}>: ghost sats fade out/in (8 opacity levels as extra prototypes, level 8 = invisible); default off
    FADE = None; _NLV = 8; _gms = [_gm]
    if os.environ.get("FLEET_FADE_TABLE"):
        FADE = json.load(open(os.environ["FLEET_FADE_TABLE"]))["frames"]; _gms += [material(f"ghost_mat_l{_l}", _GS[0], rough=_GS[1], opacity=_GS[2] * (1.0 - _l / _NLV)) for _l in range(1, _NLV)]
    _prot = {}
    def _gp_(k, parts):
        for _l, _m in enumerate(_gms):
            _sfx = "_g" if _l == 0 else f"_g{_l}"; UsdGeom.Xform.Define(stage, f"/World/inst_{k}/{k}{_sfx}")
            for nm, (V, F) in parts.items(): add_mesh_at(f"/World/inst_{k}/{k}{_sfx}/{nm}", V, F, _m)
        _prot[k] = (f"/World/inst_{k}/{k}", [f"/World/inst_{k}/{k}_g"] + [f"/World/inst_{k}/{k}_g{_l}" for _l in range(1, len(_gms))])
    _gp_("panel", dict(sheet=(Vs, A["panel_sheet_F"]), tubes=(PV("tubes"), A["panel_tubes_F"])))
    _gp_("plate", dict(m=box_mesh(K.LEAF * 1e3, K.SECW * 1e3, K.TH_ARR * 1e3)))
    _gp_("bus", dict(m=box_mesh(*(K.BUS * 1e3))))
    _gp_("yoke", dict(m=box_mesh(*(K.YOKE_BOX * 1e3))))
    _gp_("pod", dict(m=box_mesh(*(POD_DIMS - 10.0))))
    _per = dict(panel=K.NPAN_TOT, plate=2 * K.NLEAF * K.NSEC, bus=1, yoke=2, pod=1)
    for k, (p0, p1) in _prot.items():
        _idx = np.ones(NS * _per[k], np.int32)
        for h in HERO: _idx[h * _per[k]:(h + 1) * _per[k]] = 0
        PI[k].GetPrototypesRel().SetTargets([Sdf.Path(p0)] + [Sdf.Path(x) for x in p1]); PI[k].GetProtoIndicesAttr().Set(Vt.IntArray.FromNumpy(_idx))
    print("HERO sats", HERO, "ghost style", _gs, "fade table", bool(FADE), flush=True)
    def set_fade(n):   # [t364] per-output-frame ghost opacity from the precomputed table (deterministic); sats absent from the table stay opaque
        al = FADE.get(str(n), {}) if FADE else {}
        for k, (p0, p1) in _prot.items():
            idx = np.ones(NS * _per[k], np.int32); inv = []
            for h in HERO: idx[h * _per[k]:(h + 1) * _per[k]] = 0
            for sat, a in al.items():
                sat = int(sat)
                if sat in HERO: continue
                lv = int(round((1.0 - float(a)) * _NLV)); sl = slice(sat * _per[k], (sat + 1) * _per[k])
                if lv >= _NLV: inv += list(range(sl.start, sl.stop))
                else: idx[sl] = 1 + lv
            PI[k].GetProtoIndicesAttr().Set(Vt.IntArray.FromNumpy(idx)); PI[k].CreateInvisibleIdsAttr(Vt.Int64Array(inv))
_gp = GEOM["panel_sheet_tris"] + GEOM["panel_tubes_tris"] + GEOM["panel_headers_tris"] + GEOM["panel_stubs_tris"]
print(f"GEOMCOUNT simple_pod={int(SIMPLE_POD)} no_stubhdr={int(NO_STUBHDR)} rail_fade={int(RAIL_FADE)} no_rails={int(NO_RAILS)} tris_per_panel sheet={GEOM['panel_sheet_tris']} tubes={GEOM['panel_tubes_tris']} headers={GEOM['panel_headers_tris']} stubs={GEOM['panel_stubs_tris']} total={_gp} panel_instances={NPAN} plate_instances={NPLT} bus_instances={NBUS} pod_instances={NS} yoke_instances={2 * NS} pod_tris_per_sat={GEOM['pod_body_tris'] + GEOM['pod_block_tris']} scene_instanced_tris={_gp * NPAN + 12 * NPLT + 12 * NBUS + 12 * 2 * NS + (GEOM['pod_body_tris'] + GEOM['pod_block_tris']) * NS}", flush=True)
# [] option FLEET_HIDE13=1: hide the 10th panel of the 13 thick chains (render then shows 216 of the 229 panels; wing ends become flush)
HIDE13 = os.environ.get("FLEET_HIDE13", "0") == "1"
OV_T337 = f"Fold and release: kinematic.  Array accordion: cable-sync model (ESTIMATE).  Yoke, component pod and blocks: ASSUMED, illustrative.  {K.NPAN_TOT} radiator panels each."   # [t365] count comes from the loaded layout/pack (K.NPAN_TOT), not hardcoded
OV_ORIG = os.environ.get("FLEET_OVERLAY", "new") == "orig"   # [t310u] frames 59-69 (deck-graze fix) keep the ORIGINAL overlay text so they match the unchanged neighbouring frames
if HIDE13:
    _ids = []; _FLh = K.Fleet()
    for _si, _sa in enumerate(_FLh.sats):
        _off = _si * K.NPAN_TOT
        for _wc in _sa.n_cols:
            _n = K.NPAN[_wc]
            if _n > K.ALONG: _ids.append(_off + _n - 1)
            _off += _n
    assert len(_ids) == 13 * 14, len(_ids)
    PI["panel"].CreateInvisibleIdsAttr(Vt.Int64Array(_ids)); print("hidden panel instances:", len(_ids), flush=True)
HAS_F = hasattr(UsdGeom.PointInstancer, "CreateOrientationsfAttr")
print("orientationsf available:", HAS_F, flush=True)
ATTR = {}
for k, pi in PI.items():
    ATTR[k] = (pi.CreatePositionsAttr(), pi.CreateOrientationsfAttr() if HAS_F else pi.CreateOrientationsAttr())
def set_inst(k, pos, R):
    q = K.R_to_quat_wxyz(R).astype(np.float32)
    pa, oa = ATTR[k]; pa.Set(Vt.Vec3fArray.FromNumpy(pos.astype(np.float32)))
    if HAS_F: oa.Set(Vt.QuatfArray([Gf.Quatf(float(a), float(b), float(c), float(d)) for a, b, c, d in q]))
    else: oa.Set(Vt.QuatHArray([Gf.Quath(float(a), float(b), float(c), float(d)) for a, b, c, d in q]))

# schematic dispenser bay (ASSUMED, not a Starship model): ship hull below z=0, deck, 4 rails, no ring frames
def cyl(path, r, h, c, mat):
    cy = UsdGeom.Cylinder.Define(stage, path); cy.CreateRadiusAttr(r); cy.CreateHeightAttr(h); cy.CreateAxisAttr("Z"); UsdGeom.Xformable(cy).AddTranslateOp().Set(Gf.Vec3d(*c)); UsdShade.MaterialBindingAPI.Apply(cy.GetPrim()).Bind(mat)
def _rgb(env, dflt): return tuple(float(x) for x in os.environ.get(env, dflt).split(","))
HULL = material("hull", _rgb("OMNI_HULL_RGB", "0.55,0.56,0.58"), rough=float(os.environ.get("OMNI_HULL_ROUGH", "0.35")), metal=float(os.environ.get("OMNI_HULL_METAL", "1.0"))); RAILM = material("rail", _rgb("OMNI_RAIL_RGB", "0.30,0.31,0.33"), rough=0.4, metal=1.0)   # [t360] env-gated colours (defaults = t337)
DECKM = material("deck", _rgb("OMNI_DECK_RGB", "0.30,0.31,0.33"), rough=0.4, metal=1.0)
DD = float(os.environ.get("OMNI_DECKDROP", "0"))   # [t360] render-only: hull+deck lowered by DD m (deck stand-off below the stowed stack); satellite kinematics untouched
cyl("/World/Ship/hull", 4.5, 60.0, (0, 0, -30.3 - DD), HULL); cyl("/World/Ship/deck", 4.5, 0.3, (0, 0, -0.15 - DD), DECKM)
for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)] if not NO_RAILS else []): cyl(f"/World/Ship/rail{i}", 0.08, 18.5 + DD, (sx * 3.3, sy * 3.3, 8.95 - DD / 2), RAILM)
# [t360] optional rail retraction, env FLEET_RAILRETRACT JSON {"f0":4,"f1":20}: rail tops lower into the deck (smoothstep f0->f1) and the rails are hidden afterwards (schematic: guide rails fold away at release)
_RR = os.environ.get("FLEET_RAILRETRACT", ""); RAILOPS = []
if _RR and not RAIL_FADE and not NO_RAILS:   # [t361] fade mode replaces retraction
    _rr = json.loads(_RR)
    for i in range(4):
        pr = stage.GetPrimAtPath(f"/World/Ship/rail{i}"); xf = UsdGeom.Xformable(pr); top = xf.GetOrderedXformOps()[0]; sc = xf.AddScaleOp(); RAILOPS.append((pr, top, sc, top.Get()))
_RAIL_OP = float(os.environ.get("FLEET_RAIL_OP", "0.35")); _RF0 = float(os.environ.get("FLEET_RAIL_FADE_F0", "4")); _RF1 = float(os.environ.get("FLEET_RAIL_FADE_F1", "40"))
if RAIL_FADE and not NO_RAILS:   # [t361] translucent rail material (opacity animated per frame)
    _rail_op_in = UsdShade.Shader(stage.GetPrimAtPath("/World/Looks/rail/Shader")).GetInput("opacity")
def set_rails(f):
    if NO_RAILS: return
    if RAIL_FADE:
        q = min(max((f - _RF0) / (_RF1 - _RF0), 0.0), 1.0); q = q * q * (3 - 2 * q); op = _RAIL_OP * (1 - q)
        _rail_op_in.Set(float(max(op, 0.01)))
        for i in range(4): UsdGeom.Imageable(stage.GetPrimAtPath(f"/World/Ship/rail{i}")).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible if q >= 1.0 else UsdGeom.Tokens.inherited)
        return
    if not RAILOPS: return
    q = min(max((f - _rr["f0"]) / (_rr["f1"] - _rr["f0"]), 0.0), 1.0); q = q * q * (3 - 2 * q)
    for pr, top, sc, t0 in RAILOPS:
        UsdGeom.Imageable(pr).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible if q >= 1.0 else UsdGeom.Tokens.inherited)
        if q >= 1.0: continue
        H0 = 18.5 + DD; h = H0 * (1 - q) + 1e-3; zb = -0.3 - DD; top.Set(Gf.Vec3d(t0[0], t0[1], zb + h / 2)); sc.Set(Gf.Vec3f(1.0, 1.0, float(h / H0)))

# ---- Earth (as in render_omniverse.py) + lights: both identical to the P9 stills
# ---- Earth (c17): NASA Blue Marble on a UV-mapped sphere mesh; clouds are a procedural layer multiplied in (not NASA data) ----
R_E = 6.371e6; H_ORB = 550e3
LAT0, LON0, HEAD = float(os.environ.get("OMNI_LAT", "20")), float(os.environ.get("OMNI_LON", "-100")), float(os.environ.get("OMNI_HEAD", "200"))   # illustrative sub-spacecraft point
etex = TEXDIR / "earth_v3_tex.jpg"
if not etex.exists() or os.environ.get("OMNI_REMAKE_EARTH") == "1":
    base = Image.open(ASSETS / "bluemarble_8192.jpg").convert("RGB"); tw_, th_ = base.size
    rng = np.random.default_rng(7)
    def fbm(h, w, octs=7):
        out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
        for o in range(octs):
            n = 2 ** (o + 2)
            g = rng.random((n + 1, 2 * n + 1)).astype(np.float32)
            im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
            out += amp * np.asarray(im, np.float32) / 255; tot += amp; amp *= 0.5
        return out / tot
    cl = np.clip((fbm(th_, tw_) - 0.42) * 4.0, 0, 1)[..., None] * 0.9
    img = np.asarray(base, np.float32) / 255
    img = np.clip(img ** 0.72 * float(os.environ.get('OMNI_EARTH_GAIN', '1.7')), 0, 1)   # c17b: display-referred lift (Blue Marble oceans are very dark at orbital sun angles)
    img = img * (1 - cl) + 0.96 * cl
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(etex, quality=93)

def make_earth_mesh(nlon=720, nlat=360):
    lon = np.linspace(-np.pi, np.pi, nlon + 1); lat = np.linspace(-np.pi / 2, np.pi / 2, nlat + 1)
    LO, LA = np.meshgrid(lon, lat)
    p = np.stack([np.cos(LA) * np.cos(LO), np.cos(LA) * np.sin(LO), np.sin(LA)], -1)       # unit vectors, pole = +z
    uv = np.stack([(LO + np.pi) / (2 * np.pi), (LA + np.pi / 2) / np.pi], -1)
    l0, f0 = np.radians(LON0), np.radians(LAT0)
    east = np.array([-np.sin(l0), np.cos(l0), 0]); north = np.array([-np.sin(f0) * np.cos(l0), -np.sin(f0) * np.sin(l0), np.cos(f0)]); up = np.array([np.cos(f0) * np.cos(l0), np.cos(f0) * np.sin(l0), np.sin(f0)])
    h = np.radians(HEAD); e2 = np.cos(h) * east + np.sin(h) * north; n2 = -np.sin(h) * east + np.cos(h) * north
    loc = np.stack([p @ e2, p @ n2, p @ up], -1)                                            # sub-spacecraft point -> +z
    idx = np.arange((nlat + 1) * (nlon + 1)).reshape(nlat + 1, nlon + 1)
    q = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
    return loc.reshape(-1, 3), uv.reshape(-1, 2), q

EV, EUV, EQ = make_earth_mesh()
earth = UsdGeom.Mesh.Define(stage, "/World/Earth")
earth.CreatePointsAttr(Vt.Vec3fArray.FromNumpy((EV * R_E + np.array([0, 0, -(R_E + H_ORB)])).astype(np.float32)))
earth.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(EV.astype(np.float32))); earth.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
earth.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(EQ), 4, np.int32)))
earth.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(EQ.reshape(-1).astype(np.int32)))
earth.CreateSubdivisionSchemeAttr("none"); earth.CreateDoubleSidedAttr(False)
pv = UsdGeom.PrimvarsAPI(earth).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
pv.Set(Vt.Vec2fArray.FromNumpy(EUV.astype(np.float32)))
earth.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(-R_E, -R_E, -2 * R_E - H_ORB), Gf.Vec3f(R_E, R_E, -H_ORB)]))
em = material("earth", (0.3, 0.3, 0.3), rough=0.75, diffuse_tex=etex)
UsdShade.MaterialBindingAPI.Apply(earth.GetPrim()).Bind(em)

# ---- lights: sun (distant, 0.53 deg disc) + faint blue earthshine from below; black sky ----
SUNDIR = np.array([0.45, -0.35, 0.82]); SUNDIR /= np.linalg.norm(SUNDIR)    # direction toward the sun, model axes (arrays face +z); illustrative
sun = UsdLux.DistantLight.Define(stage, "/World/Sun"); sun.CreateIntensityAttr(float(os.environ.get("OMNI_SUN", "2500")))   # c17: the c16 line swallowed the next two calls in a comment; fixed
sun.CreateAngleAttr(float(os.environ.get("OMNI_SUNANGLE", "1.0"))); sun.CreateColorAttr(Gf.Vec3f(1.0, 0.96, 0.9))   # 1.0 deg disc (physical sun is 0.53 deg): slightly widened for soft shadow edges, illustrative
z = -SUNDIR; ang = Gf.Rotation(Gf.Vec3d(0, 0, -1), Gf.Vec3d(*z))     # light shines along -Z of its frame
sx = UsdGeom.Xformable(sun); sx.AddOrientOp().Set(Gf.Quatf(ang.GetQuat()))
fill = UsdLux.DistantLight.Define(stage, "/World/Earthshine"); fill.CreateIntensityAttr(float(os.environ.get("OMNI_FILL", "60"))); fill.CreateAngleAttr(20.0); fill.CreateColorAttr(Gf.Vec3f(0.45, 0.65, 1.0))
fa = Gf.Rotation(Gf.Vec3d(0, 0, -1), Gf.Vec3d(0, 0, 1)); UsdGeom.Xformable(fill).AddOrientOp().Set(Gf.Quatf(fa.GetQuat()))
# [t360] optional rim/back light (env OMNI_RIM = intensity, OMNI_RIMDIR = x,y,z direction TOWARD the light): separates satellites from the hull behind them
if float(os.environ.get("OMNI_RIM", "0")) > 0:
    RD = np.array([float(x) for x in os.environ.get("OMNI_RIMDIR", "-0.6,0.5,0.4").split(",")]); RD /= np.linalg.norm(RD)
    rim = UsdLux.DistantLight.Define(stage, "/World/Rim"); rim.CreateIntensityAttr(float(os.environ["OMNI_RIM"])); rim.CreateAngleAttr(3.0); rim.CreateColorAttr(Gf.Vec3f(0.85, 0.92, 1.0))
    UsdGeom.Xformable(rim).AddOrientOp().Set(Gf.Quatf(Gf.Rotation(Gf.Vec3d(0, 0, -1), Gf.Vec3d(*(-RD))).GetQuat()))


# ---- camera (one moving camera per session) ----
cam = UsdGeom.Camera.Define(stage, "/World/cam"); cam.CreateHorizontalApertureAttr(36.0); cam.CreateVerticalApertureAttr(36.0 * H / W); cam.CreateClippingRangeAttr(Gf.Vec2f(0.1, 5e7)); cam.CreateFocalLengthAttr(24.0)
cam_op = UsdGeom.Xformable(cam).AddTransformOp()
def set_cam(eye, tgt, fov):
    cam.GetFocalLengthAttr().Set(float(18.0 / np.tan(np.radians(fov) / 2)))
    cam_op.Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*map(float, eye)), Gf.Vec3d(*map(float, tgt)), Gf.Vec3d(0, 0, 1)).GetInverse())
FL = K.Fleet()
# [t363] opt-in (default off): FLEET_HERO_CAM JSON -> hero close-up camera + unfold retime (module fleet_hero_t363_T45; playback/camera only, kinematics untouched). Frame index f is then an OUTPUT frame; args F0 F1 must span 0..HC.N_TOTAL
HC = None; SLOWTAG = ""
if os.environ.get("FLEET_HERO_CAM"):
    import fleet_hero_t363_T45 as HC
    print(f"HERO CAM on: hero {HC.HERO} output frames {HC.N_TOTAL} (unchanged clip 816)", flush=True)
def apply_pose(T, tc):
    P = FL.poses(T)
    set_inst("panel", P["panel_p"], P["panel_R"]); set_inst("plate", P["plate_p"], P["plate_R"]); set_inst("bus", P["bus_p"], P["bus_R"]); set_inst("yoke", P["yoke_p"], P["yoke_R"]); set_inst("pod", P["pod_p"], P["pod_R"])
    set_cam(*(HC.camera(tc * K.FPS, FL, T) if HC is not None else K.camera(tc, FL, T))); set_rails(tc * K.FPS)
apply_pose(0.0, 0.0)
PTMODE = os.environ.get("OMNI_PT", "1") == "1"; DEN = os.environ.get("OMNI_DEN", "1") == "1"; HDR = True
for _ in range(60): app.update()
rp = rep.create.render_product("/World/cam", (W, H))
ann = rep.AnnotatorRegistry.get_annotator("HdrColor"); ann.attach([rp])
for _ in range(10): app.update()
cs = carb.settings.get_settings(); cs.set("/rtx/post/histogram/enabled", False)
if PTMODE:
    SPP_SUB = min(SPP, 32); cs.set("/rtx/rendermode", "PathTracing"); cs.set("/rtx/pathtracing/spp", SPP_SUB); cs.set("/rtx/pathtracing/totalSpp", SPP)
    cs.set("/rtx/pathtracing/optixDenoiser/enabled", DEN); cs.set("/rtx/pathtracing/maxBounces", int(os.environ.get("OMNI_BOUNCES", "6")))
    print("render mode:", cs.get("/rtx/rendermode"), "spp", cs.get("/rtx/pathtracing/spp"), "total", cs.get("/rtx/pathtracing/totalSpp"), "denoiser", cs.get("/rtx/pathtracing/optixDenoiser/enabled"), flush=True)
for _ in range(10): app.update()
print(f"scene ready {time.time() - T0:.0f} s", flush=True)
# fixed star field (stars at infinity: not moved with the camera)
rs_ = np.random.default_rng(5); NST = int(W * H * 4e-4); SY = rs_.integers(0, H, NST); SX = rs_.integers(0, W, NST); SB = ((rs_.random(NST) ** 3) * 0.9 + 0.1) * 255
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
fs = max(11, H // 54)
def overlay(im, T, rate):
    d = ImageDraw.Draw(im, "RGBA"); f1 = ImageFont.truetype(FB, int(fs * 1.05)); f2 = ImageFont.truetype(FONT, fs); m = int(fs * 0.9); BA = 255 if os.environ.get("FLEET_CAPBAND", "") == "opaque" else 120   # [t363] opt-in opaque caption bands (clear of all geometry)
    d.rectangle([0, 0, W, int(fs * 3.3)], fill=(0, 0, 0, BA)); d.text((m, int(fs * 0.5)), "SIMULATED \u2013 assumed dispenser and hinge parameters (ESTIMATES) \u2013 pre-flight design study, 13 satellites per launch", font=f1, fill=(255, 255, 255, 255))
    d.text((m, int(fs * 1.9)), "Radiator fold, array width fold and release: kinematic / analytic.  Array accordion: Newton solver replay.  Dispenser bay: schematic." if OV_ORIG else (OV_T337 if OV_T337 else "Fold and release: kinematic.  Array accordion: cable-synchronised model (ESTIMATE), yoke ASSUMED.  Dispenser bay: schematic.  Radiators: 216 of 229 panels drawn." if HIDE13 else "Fold and release: kinematic.  Array accordion: cable-synchronised model (ESTIMATE), yoke ASSUMED.  Dispenser bay: schematic."), font=f2, fill=(215, 215, 215, 255))
    d.rectangle([0, H - int(fs * 2.6), W, H], fill=(0, 0, 0, BA))
    lab = K.time_label(T); txt = f"sim clock {lab}"; d.text((m, H - int(fs * 2.0)), txt, font=f1, fill=(255, 255, 255, 255))
    d.text((m + int(fs * 12), H - int(fs * 2.0)), (f"time-lapse x{rate:,.0f}" if rate > 1.5 else "real time") + SLOWTAG, font=f1, fill=(255, 210, 120, 255))
    s = "Earth: NASA Blue Marble (illustrative position)"; tw = d.textlength(s, font=f2); d.text((W - tw - m, H - int(fs * 1.9)), s, font=f2, fill=(215, 215, 215, 255))
    return im
def tonemap(arr):
    lin = np.clip(arr * float(os.environ.get("OMNI_CAL", "1.0")) * 1.15, 0, None); lin = lin / (1 + 0.25 * lin)
    sr = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(lin, 1 / 2.4) - 0.055); return (np.clip(sr, 0, 1) * 255).astype(np.uint8)
means = []; tdone = []
apply_pose(K.sim_time(3.0), 3.0)   # warm-up at a different pose so frame 0 is rendered from scratch
for _w in range(2):   # warm-up: first frames of a session are not converged; discard
    rep.orchestrator.step(rt_subframes=4, delta_time=0.0, pause_timeline=False); ann.get_data()
NSUB = max(2, SPP // max(1, min(SPP, 32))) if PTMODE else 4
FRAMES = [int(x) for x in os.environ["OMNI_FRAMES"].split(",")] if os.environ.get("OMNI_FRAMES") else range(F0, F1)   # test knob: sparse list of frames
VIEWS = json.load(open(os.environ["FLEET_VIEWS"])) if os.environ.get("FLEET_VIEWS") else None   # [t361 crop_check] opt-in (default off): list of {name, frame, eye, tgt, fov}; renders each custom view to v_<name>.png (no overlay)
for f in (FRAMES if VIEWS is None else range(len(VIEWS))):
    VW = None if VIEWS is None else VIEWS[f]
    fn = OUTD / (f"f_{f:05d}.png" if VW is None else f"v_{VW['name']}.png")
    if fn.exists(): continue
    t1 = time.time(); ff = f if VW is None else int(VW["frame"]); tc = ff / K.FPS; T = K.sim_time(tc); rate = K.sim_rate(tc)
    if HC is not None and VW is None:      # [t363] output frame -> original (fractional) frame; label = sim seconds per OUTPUT second (truthful under the retime)
        fo = HC.orig_frame(f); tc = fo / K.FPS; T = K.sim_time(tc); rate = HC.rate_label(fo); SLOWTAG = "  (unfold replayed at half speed)" if HC.speed(fo) < 0.999 else ""
    apply_pose(T, tc)
    if HERO and FADE is not None and VW is None: set_fade(f)   # [t364]
    if VW is not None: set_cam(VW["eye"], VW["tgt"], VW["fov"])
    for _ in range(int(os.environ.get("OMNI_UPD", "3"))): app.update()
    for att in range(4):
        rep.orchestrator.step(rt_subframes=NSUB, delta_time=0.0, pause_timeline=False)
        data = ann.get_data()
        if data is None or not np.asarray(data).size: continue
        arr = np.asarray(data)[..., :3].astype(np.float32); m = float(arr.mean())
        if not means or 0.4 < m / np.median(means[-8:]) < 2.5 or att == 3: break
    means.append(m)
    out = tonemap(arr); bg = out.max(axis=2) < 6; ok = bg[SY, SX]; out[SY[ok], SX[ok]] = np.maximum(out[SY[ok], SX[ok]], SB[ok].astype(np.uint8)[:, None])
    im = Image.fromarray(out) if VW is not None else overlay(Image.fromarray(out), T, rate); im.save(str(fn) + ".tmp.png"); os.replace(str(fn) + ".tmp.png", fn)
    tdone.append(time.time() - t1)
    print(f"frame {f} tc {tc:.2f} T {T:.1f} att {att + 1} mean {m:.4g} {time.time() - t1:.1f}s (avg {np.mean(tdone):.1f}s) wall {time.time() - T0:.0f}s", flush=True)
print(f"done {F0}-{F1} total {time.time() - T0:.0f} s", flush=True)
app.close()
