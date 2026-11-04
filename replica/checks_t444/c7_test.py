import json, numpy as np
from c7_frame import *
pk=json.load(open(f"{SC}/Aug/fleet_pack_replica_Aug.json"))["layers"]
print([round(pk[i+1]["z0"]-pk[i]["z0"]-pk[i]["H"],3) for i in range(len(pk)-1)][:5])
for b in ("Jun","Aug"):
    for var in ("t440","kept"):
        m,h,ms=build(b,var); A,p,Mab=size(m,h,ms)
        for te in (0,3):
            F=Frame(m,h,ms,A,p,te); fa,fl=F.freqs(); print(b,var,"L",len(m),"tie",te,"fax",fa.round(2),"flat",fl.round(2),"A_base cm2",round(A[0]*1e4,1),"asm s",round(F.t_asm,2))
