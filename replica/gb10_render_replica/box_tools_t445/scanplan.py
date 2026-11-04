"""fine tau scan of own-sat clearance: scanplan.py <sats comma> <t0> <t1> <dt>  (env FLEET_STAGEPLAN=...)  -> per-sat min per category + offending taus"""
import sys, os
sys.path.insert(0,os.getcwd())
import numpy as np
from multiprocessing import Pool
_a=sys.argv; sys.argv=[_a[0],"/tmp/x.npz","1"]
import fleet_full_clearance_T45 as F
sys.argv=_a
SATS=[int(x) for x in _a[1].split(",")]; t0=float(_a[2]); t1=float(_a[3]); dt=float(_a[4])
def work(tau):
    out=[]
    for s in SATS:
        sa=F.fl.sats[s]; P=F.fl.poses(sa.Tu+tau); out.append(F.own_frame(P,s))
    return tau,np.array(out)
if __name__=="__main__":
    taus=np.arange(t0,t1+1e-9,dt)
    with Pool(int(os.environ.get("NPROC","8")),initializer=F.init) as p: res=p.map(work,taus,chunksize=4)
    G=np.stack([r[1] for r in res])   # (ntau,nsat,ncat)
    for k,s in enumerate(SATS):
        mn=G[:,k,:].min(0); bad=[(F.CATS[c],round(float(mn[c]),4),round(float(taus[G[:,k,c].argmin()]),2)) for c in range(len(mn)) if mn[c]<=0.0]
        print("sat",s,"min",{F.CATS[c]:round(float(mn[c]),4) for c in range(len(mn)) if F.CATS[c]!="yoke_yoke"},"FAIL" if bad else "PASS",bad)
    np.savez_compressed(os.environ.get("SCAN_OUT","/tmp/t441/scan_last.npz"),taus=taus,G=G,sats=np.array(SATS),cats=np.array(F.CATS))
