import json
from c7_frame import *
out={}
for b in ("Jun","Aug"):
    m,h,ms=build(b,"kept"); A,p,Mab=size(m,h,ms); L=len(m)
    post_mass=lambda A_: float((m*A_*p).sum()*2700*1.0)  # kg, post group volume m*A*pitch * rho(2700) (Al)  -- ASSUMED rho
    base=Frame(m,h,ms,A,p,3).freqs()[0][0]
    def f_for(kap, lo):
        A2=A.copy(); A2[lo:]*=kap; return Frame(m,h,ms,A2,p,3).freqs()[0][0]
    res=dict(f_axial_as_sized=float(base), post_mass_kg=post_mass(A))
    for lo in (0, L-4, L-7):
        lo_k=1.0; hi_k=8.0
        if f_for(hi_k,lo)<25: res[f"kappa_levels_{lo+1}_to_{L}"]=None; continue
        for _ in range(18):
            mid=(lo_k+hi_k)/2
            if f_for(mid,lo)>=25.0: hi_k=mid
            else: lo_k=mid
        A2=A.copy(); A2[lo:]*=hi_k
        res[f"kappa_levels_{lo+1}_to_{L}"]=dict(kappa=round(hi_k,3), extra_post_kg=round(post_mass(A2)-post_mass(A),1), extra_pct_of_stack=round((post_mass(A2)-post_mass(A))/(ms*m.sum())*100,3))
    out[b]=res; print(b,res,flush=True)
json.dump(out,open("c7_kappa.json","w"),indent=1)
