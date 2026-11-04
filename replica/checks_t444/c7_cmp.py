import json, numpy as np
from c7_frame import *
ccx=json.load(open("c7_ccx_modes.json")); out={}
for k,v in ccx.items():
    b,var,lab=k.split("_"); m,h,ms=build(b,var); A,p,Mab=size(m,h,ms); F=Frame(m,h,ms,A,p,3 if lab=="tie3" else 0)
    F.kax=E*m*A/p; Ka=np.zeros((F.L,F.L))
    for e in range(F.L):
        Ka[e,e]+=F.kax[e]
        if e>0: Ka[e-1,e-1]+=F.kax[e]; Ka[e,e-1]-=F.kax[e]; Ka[e-1,e]-=F.kax[e]
    F.Ka=Ka; fa,fl=F.freqs(); allw=np.sort(np.concatenate([fa,fl]))
    out[k]=dict(ccx_beam=v["ccx_beam_all"][:6], warp_same_model=[round(float(x),2) for x in allw[:6]], warp_axial_pitchK=fa.round(2).tolist(), warp_lat=fl.round(2).tolist())
    print(k,out[k])
json.dump(out,open("c7_ccx_vs_warp.json","w"),indent=1)
