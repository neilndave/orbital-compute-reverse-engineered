# t444 check 7b: static launch cases on the Warp frame model (Warp CG solves). ESTIMATE.
import json, sys, time, numpy as np
from c7_frame import *
t0=time.time(); out={}
def summarize(b, var, te, dpf_size=1.0, dpf_chk=1.0):
    m,h,ms=build(b,var); A,p,Mab=size(m,h,ms,dp_factor=dpf_size)
    F=Frame(m,h,ms,A,p,te)
    s6=F.static(6.0,0.0); sl=F.static(3.5,2.0); sl2=F.static(6.0,0.5)
    mA=F.m*F.A
    def ms_(s,key_ax):
        sig=(np.abs(s["N"])/mA+s["M_end"]/(mA*ARM/2)*dpf_chk)*FS
        return SIG/sig-1
    r=dict(L=int(F.L), A_base_cm2=float(F.A[0]*F.m[0]*1e4), 
      top_closure_6g_mm=s6["axial_u_top_mm"], max_level_closure_6g_mm=float(np.max(s6["axial_rel_closure_mm"])), sum_closure_corner2_mm=sl["axial_u_top_mm"],
      MS6_min=float(ms_(s6,0).min()), MS_35_2_min=float(ms_(sl,0).min()), MS_6_05_min=float(ms_(sl2,0).min()),
      lat_x_max_mm_2g=float(sl["lat_x_max_mm"]), lat_x_max_mm_0p5g=float(sl2["lat_x_max_mm"]), max_interlevel_lat_mm=float(np.abs(sl["lat_interlevel_mm"]).max()),
      base_shear_kN_corner=sl["base_shear_N"]/1e3, base_moment_MNm_corner=sl["base_moment_Nm"]/1e6,
      tie_lat_react_kN_max=(max(abs(x) for x in sl["tie_lateral_reaction_N"])/1e3 if sl["tie_lateral_reaction_N"] else 0.0),
      tie_ax_react_kN_max_6g=(max(abs(x) for x in s6["tie_axial_reaction_N"])/1e3 if s6["tie_axial_reaction_N"] else 0.0),
      base_axial_N_6g_kN=s6["base_axial_reaction_N"]/1e3)
    return r
for b in ("Jun","Aug"):
    for var in ("kept","t440"):
        for te in (0,3):
            for dps in (1.0,2.0):
                k=f"{b}_{var}_tie{te}_sizeDP{int(dps)}"; out[k]=summarize(b,var,te,dpf_size=dps,dpf_chk=1.0)
                r=out[k]; print(k, {a:(round(v,3) if isinstance(v,float) else v) for a,v in r.items()}, flush=True)
json.dump(out,open("c7_static.json","w"),indent=1); print("secs",time.time()-t0)
