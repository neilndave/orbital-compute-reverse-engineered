"""GTC FINAL v2 radiator fin (t619 adoption of GTC_FINAL_AL option (b)): Al 6061-T6 integral/brazed fins, half-length 26 mm, thickness 0.225 mm,
NO bondline, same 77/128-panel footprint and the same emissivity coating.  Replaces K13D70 30/0.20 bonded fins (table F3_L40_t0p5 / K13D_AREA_FACTOR 0.9913).
Thermal: the fin's own NVIDIA Warp eta_cell table (GB10 cuda:0, Warp 1.18.0 fp64, t410 format/grid, nx 320 x ny 8; fin_al.py) with area factor 1.0.
Mass: radiator line = inherited K13D wet radiator line x FIN_MASS_REL, FIN_MASS_REL = Al cell areal / (K13D cell areal + t479 bond 7.61 kg / 81.628 m2)
(Warp fin screen screen_al_fine.json, OD 8 mm tube cell; t548 convention).  Material: k 167 W/mK, rho 2700 kg/m3 (ASM/MatWeb 6061-T6, AA typical).  ESTIMATE."""
import json, os
import numpy as np
from scipy.interpolate import RegularGridInterpolator
FIN = dict(id="AL6061_L26_t0p225", alloy="Al 6061-T6", half_length_m=0.026, thickness_m=0.000225, k_W_mK=167.0, rho_kg_m3=2700.0, bondline=False, tube_pitch_mm=60.0)
TABLE_REL = "inputs/ai1_replica/gb10_final_al/table_AL6061_L26_t0p225.json"
AREA_FACTOR = 1.0
AREAL_AL_KG_M2 = 1.7526374327573164; AREAL_K13D_KG_M2 = 1.417180087727044; BOND_KG_M2 = 7.61 / 81.62815837399465
FIN_MASS_REL = AREAL_AL_KG_M2 / (AREAL_K13D_KG_M2 + BOND_KG_M2)
FREEZE_GEOM = dict(NT=6, tf_m=0.000225)   # tubes per 363.4 mm panel at 60 mm pitch; Al fin sheet thickness (freeze/restart transient)
def table_path(root): return os.path.join(root, TABLE_REL)
def register(M, root):
    """add the Al table to model_t549.TABS (same RegularGridInterpolator/clamping as model_t549._load)"""
    t = json.load(open(table_path(root))); eta = np.array(t["eta"]).reshape(t["ntb"], t["nee"], t["nts"])
    tb = t["tb0"] + t["dtb"] * np.arange(t["ntb"]); ea = t["ee0"] + t["dee"] * np.arange(t["nee"]); ta = t["ts0"] + t["dts"] * np.arange(t["nts"])
    g = RegularGridInterpolator((tb, ea, ta), eta, bounds_error=False, fill_value=None)
    M.TABS[FIN["id"]] = lambda Tb, e_, Ts_: float(g([[min(max(Tb, tb[0]), tb[-1]), min(max(e_, ea[0]), ea[-1]), min(max(Ts_, ta[0]), ta[-1])]])[0])
    return FIN["id"]

def register_selected(M,root,fin):
    t=json.load(open(os.path.join(root,fin['table_rel'])))
    eta=np.array(t['eta']).reshape(t['ntb'],t['nee'],t['nts'])
    tb=t['tb0']+t['dtb']*np.arange(t['ntb']);ea=t['ee0']+t['dee']*np.arange(t['nee']);ta=t['ts0']+t['dts']*np.arange(t['nts'])
    g=RegularGridInterpolator((tb,ea,ta),eta,bounds_error=False,fill_value=None)
    M.TABS[fin['fin_id']]=lambda Tb,e_,Ts_:float(g([[np.clip(Tb,tb[0],tb[-1]),np.clip(e_,ea[0],ea[-1]),np.clip(Ts_,ta[0],ta[-1])]])[0])
    return fin['fin_id']
