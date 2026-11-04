import sys, os, json
sys.path.insert(0, os.getcwd())
import numpy as np
import fleet_kin_T45 as K
fl=K.Fleet(); s=int(sys.argv[1]); sa=fl.sats[s]; ng=len(sa.n_cols)
bs=K.PLAN[str(s)]["bodies"]; old=[bs[ng+2+w]["t1"] for w in (0,1)]
fin=[np.array(bs[ng+2+w]["wps"][-1][0]) for w in (0,1)]
for w in (0,1): bs[ng+2+w]["t1"]=-1.0
for tau in [16.6,25,29,29.6,30,32,34,36,36.3,40,50]:
    fl.local(sa,tau); y=sa._yoke[0]
    print(tau, [round(float(np.abs(y[w]+sa.fD-fin[w]).max()),4) for w in (0,1)])
print(old)
