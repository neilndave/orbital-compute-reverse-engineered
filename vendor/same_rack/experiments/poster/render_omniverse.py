"""P9-OMNI: photoreal RTX render of the deployed F4 spacecraft with Isaac Sim 6.0 (headless, aarch64, GB10 desktop).
Geometry: results/omniverse/deployed_meshes.npz = the CAD build used for the earlier 3-D hero renders (experiments/poster/export_deployed_mesh.py;
radiator panels, solar array leaves, bus, rack envelope, mast, trunks; mm). NOT the Newton deploy USD (that is rigid boxes of a stalled array study).
Run (venv_isaac): OMNI_KIT_ACCEPT_EULA=YES python experiments/poster/render_omniverse.py [spp] [width] [height] [views...]
c17 (v3): NASA Blue Marble Earth on a UV-mapped sphere mesh (credit in results/omniverse/assets/CREDITS.md) plus a procedural cloud layer, solar-cell grid texture, gold insulation crinkle normal map, Mitsuba-matched cameras, true path tracing.
Run it through a launcher that pins start-up to 4 CPUs (logs/c17_run.sh): unpinned Kit start-up hangs about half of the time on this aarch64 box.
IDEALIZED model, illustrative sun direction and Earth backdrop (real Blue Marble texture, illustrative position). DRAFT on the pre-freeze 264-panel mesh. Not a flight design."""
import os
import sys
import time

os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")   # the author Dave accepted the NVIDIA Omniverse licence terms (2026-10-30 11:39 Taipei)
import pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "figures" / "poster" / "native"
OUT.mkdir(parents=True, exist_ok=True)
SPP = int(sys.argv[1]) if len(sys.argv) > 1 else 64
W = int(sys.argv[2]) if len(sys.argv) > 2 else 3600
H = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
VIEWS = sys.argv[4:] or ["wide", "bus", "array"]
T0 = time.time()

from isaacsim import SimulationApp  # noqa: E402
app = SimulationApp({"headless": True, "width": W, "height": H, "renderer": "RaytracedLighting"}, experience=os.environ.get("OMNI_EXPERIENCE", ""))   # P14: OMNI_EXPERIENCE = a lean .kit when the pip install lacks the full extension set
print(f"app up {time.time() - T0:.0f} s", flush=True)
def widen():   # c17: the launcher pins start-up to 4 CPUs (avoids the Kit start-up race); afterwards every thread may use all CPUs again
    allc = set(range(os.cpu_count()))
    for t in os.listdir("/proc/self/task"):
        try: os.sched_setaffinity(int(t), allc)
        except Exception: pass
widen()

import carb  # noqa: E402
import omni.usd  # noqa: E402
import omni.replicator.core as rep  # noqa: E402
from pxr import Usd, UsdGeom, UsdShade, Gf, Sdf, Vt, UsdLux  # noqa: E402
from PIL import Image  # noqa: E402

from rack_two_skies import design_tag as DT   # P14: RTS_TAG=_T45 -> 45 C baseline meshes and "_T45" file names
M = np.load(ROOT / "results" / "omniverse" / f"deployed_meshes{DT.TAG}.npz")
S = 1e-3   # mm -> m
ctx = omni.usd.get_context()
ctx.new_stage()
stage = ctx.get_stage()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)
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
    radiator_sheet=material("rad_white", (0.86, 0.87, 0.86), rough=0.55),              # Z-93-like white thermal paint (illustrative albedo)
    radiator_tubes=material("tube_al", (0.78, 0.79, 0.82), rough=0.28, metal=1.0),     # aluminium tubes
    radiator_headers=material("hdr_al", (0.62, 0.64, 0.68), rough=0.35, metal=1.0),
    radiator_stubs=material("stub_al", (0.66, 0.68, 0.72), rough=0.35, metal=1.0),
    array=material("cells", (0.02, 0.05, 0.24), rough=0.16, metal=0.15, coat=0.9, diffuse_tex=CELL_TEX),   # cell grid texture under glass-like clearcoat
    bus=material("bus_mli", (1.0, 0.77, 0.34), rough=0.5, metal=1.0, normal_tex=MLI_NRM, normal_scale=float(os.environ.get("OMNI_CRINKLE", "1.0"))),   # gold (Au F0) + crinkle normal map
    rack=material("rack", (0.12, 0.55, 0.30), rough=0.4),
    mast=material("mast", (0.7, 0.7, 0.72), rough=0.3, metal=1.0),
    trunks=material("trunk", (0.72, 0.74, 0.78), rough=0.3, metal=1.0),
)


def add_mesh(name, V, F, mat, smooth=False, uv=None, uv_tile=1.0):
    p = UsdGeom.Mesh.Define(stage, f"/World/{name}")
    p.CreatePointsAttr(Vt.Vec3fArray.FromNumpy((V * S).astype(np.float32)))
    p.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(F), 3, np.int32)))
    p.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(F.reshape(-1).astype(np.int32)))
    p.CreateSubdivisionSchemeAttr("none")
    p.CreateDoubleSidedAttr(True)
    if uv:   # c17: per-corner (faceVarying) UVs by planar projection along each triangle's dominant normal axis, metres / uv_tile
        P = (V[F] * S)                                              # (nF, 3, 3)
        nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); ax = np.abs(nrm).argmax(1)
        u = np.where((ax == 0)[:, None], P[..., 1], P[..., 0]); v = np.where((ax == 2)[:, None], P[..., 1], P[..., 2])
        st_arr = np.stack([u, v], -1).reshape(-1, 2) / uv_tile
        pv = UsdGeom.PrimvarsAPI(p).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        pv.Set(Vt.Vec2fArray.FromNumpy(st_arr.astype(np.float32)))
    UsdShade.MaterialBindingAPI.Apply(p.GetPrim()).Bind(mat)
    return p


for n in ["radiator_sheet", "radiator_tubes", "radiator_headers", "radiator_stubs", "array", "bus", "mast", "trunks"]:
    add_mesh(n, M[n + "_V"].astype(np.float64), M[n + "_F"], MAT[n], uv=(n in ("array", "bus")), uv_tile={"array": CELL_TILE_M, "bus": MLI_TILE_M}.get(n, 1.0))
# rack envelope sits inside the bus (opaque bus hides it); skipped on purpose.

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

# ---- cameras ----
def camera(name, pos, target, focal=24.0):
    cam = UsdGeom.Camera.Define(stage, f"/World/{name}")
    cam.CreateFocalLengthAttr(focal); cam.CreateHorizontalApertureAttr(36.0); cam.CreateVerticalApertureAttr(36.0 * H / W)
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.1, 5e7))
    eye = Gf.Vec3d(*pos); tgt = Gf.Vec3d(*target)
    m = Gf.Matrix4d().SetLookAt(eye, tgt, Gf.Vec3d(0, 0, 1)).GetInverse()
    UsdGeom.Xformable(cam).AddTransformOp().Set(m)
    return f"/World/{name}"

def fl_from_fov(fov_deg): return 18.0 / np.tan(np.radians(fov_deg) / 2)     # 36 mm aperture, horizontal fov
CAMS = {   # c17: same positions, targets and horizontal fov as render_mitsuba.py (fov 38 / 34 / 40 deg)
    "wide": ((70.0, -95.0, 38.0), (0, 0, 0), fl_from_fov(38.0)),
    "bus": ((9.5, -12.0, 5.5), (0, 0, 0.5), fl_from_fov(34.0)),
    "array": ((62.0, -40.0, 10.0), (-5.0, 0.0, 2.0), fl_from_fov(40.0)),
}
CAMP = {v: camera("cam_" + v, *CAMS[v]) for v in VIEWS}
PTMODE = os.environ.get("OMNI_PT", "1") == "1"
DEN = os.environ.get("OMNI_DEN", "1") == "1"
for _ in range(60):
    app.update()
rp = rep.create.render_product(CAMP[VIEWS[0]], (W, H))
HDR = os.environ.get("OMNI_HDR", "1") == "1"   # c17: capture linear HdrColor and tone-map like render_mitsuba.py (the RTX auto-exposure saturated the close views)
ann = rep.AnnotatorRegistry.get_annotator("HdrColor" if HDR else "rgb"); ann.attach([rp])
for _ in range(10):
    app.update()
cs = carb.settings.get_settings()
cs.set("/rtx/post/histogram/enabled", False)   # c17: fixed exposure (auto-exposure made the close views saturate and the wide view dark)
for kv in [x for x in os.environ.get("OMNI_SETS", "").split(";") if x]:   # c17: experiment knob, e.g. OMNI_SETS="/rtx/post/tonemap/filmIso=100;/rtx/post/tonemap/fStop=4"
    k_, v_ = kv.split("="); cs.set(k_, float(v_) if v_.replace(".", "", 1).replace("-", "", 1).isdigit() else (v_ == "true"))
if PTMODE:   # c17 ROOT CAUSE of the black path-tracer frames: the mode must be switched AFTER the render product exists and a few frames have run
    SPP_SUB = min(SPP, 32)
    cs.set("/rtx/rendermode", "PathTracing")
    cs.set("/rtx/pathtracing/spp", SPP_SUB); cs.set("/rtx/pathtracing/totalSpp", SPP)
    cs.set("/rtx/pathtracing/optixDenoiser/enabled", DEN)
    cs.set("/rtx/pathtracing/maxBounces", int(os.environ.get("OMNI_BOUNCES", "6")))
    print("render mode:", cs.get("/rtx/rendermode"), "spp", cs.get("/rtx/pathtracing/spp"), "total", cs.get("/rtx/pathtracing/totalSpp"), "denoiser", cs.get("/rtx/pathtracing/optixDenoiser/enabled"), flush=True)
for _ in range(10):
    app.update()
STAR = np.random.default_rng(5)
# c17: STATEMENT (measured): within one session only the FIRST camera after the render-mode switch comes back at the display exposure; later cameras in the same session came back unexposed (about 1000x too bright)
# and the cause was not found, so the final renders are made ONE VIEW PER SESSION (see the loop in run_omniverse_v3.sh).
for v in VIEWS * int(os.environ.get('OMNI_PASSES', '1')):
    t1 = time.time()
    stage.GetPrimAtPath(rp.path).GetRelationship("camera").SetTargets([Sdf.Path(CAMP[v])])
    for _ in range(15):
        app.update()
    prev = None
    for k in range(14):   # c17: step until the frame mean is stable (the first frames after a mode or camera change come back at a different scale)
        rep.orchestrator.step(rt_subframes=max(2, SPP // max(1, min(SPP, 32)) if PTMODE else 4), delta_time=0.0, pause_timeline=False)
        data = ann.get_data()
        if data is None or not np.asarray(data).size:
            continue
        m = float(np.asarray(data)[..., :3].mean())
        if os.environ.get("OMNI_DEBUG") == "1": print(f"    {v} step {k}: mean {m:.4g} t {time.time() - t1:.1f}s mode {cs.get('/rtx/rendermode')}", flush=True)
        if os.environ.get('OMNI_DEBUG') != '1' and k >= 3 and m > (1e-4 if HDR else 0.5) and prev is not None and abs(m - prev) <= 0.01 * max(m, 1e-9):
            break
        prev = m
    print(f"  {v}: {k + 1} steps", flush=True)
    if HDR:
        arr = np.asarray(data)[..., :3].astype(np.float32)
        np.save(pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / f"omni_{v}_hdr.npy", arr)
        lin = np.clip(arr * float(os.environ.get("OMNI_CAL", "1.0")) * 1.15, 0, None); lin = lin / (1 + 0.25 * lin)       # same tone curve as render_mitsuba.py
        sr = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
        out = (np.clip(sr, 0, 1) * 255).astype(np.uint8)
        print(f"  hdr mean {arr.mean():.4g} p50 {np.percentile(arr, 50):.4g} p99 {np.percentile(arr, 99):.4g} max {arr.max():.4g}", flush=True)
    else:
        out = np.asarray(data)[..., :3].copy()
    if os.environ.get("OMNI_STARS", "1") == "1":   # c17: same star-field recipe as render_mitsuba.py (sparse points on background pixels only)
        bg = out.max(axis=2) < 6
        n = int(W * H * 4e-4); ys = STAR.integers(0, H, n); xs = STAR.integers(0, W, n); br = (STAR.random(n) ** 3 * 0.9 + 0.1) * 255
        for y, x, b_ in zip(ys, xs, br):
            if bg[y, x]: out[y, x] = np.maximum(out[y, x], int(b_))
    im = Image.fromarray(out)
    tag = os.environ.get("OMNI_TAG", "v3")
    fn = OUT / f"p9_omniverse{DT.TAG}_{tag}_{v}_{W}x{H}.png"
    im.save(fn)
    print(f"{v}: {time.time() - t1:.0f} s -> {fn} mean {np.asarray(im).mean():.1f}", flush=True)
stage.Export(str(ROOT / "results" / "omniverse" / f"deployed_scene{DT.TAG}.usd"))
print(f"total {time.time() - T0:.0f} s", flush=True)
app.close()
