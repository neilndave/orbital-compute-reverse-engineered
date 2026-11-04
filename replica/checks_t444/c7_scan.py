import numpy as np, scipy.linalg as sl
from c7_frame import *
def fax(F, tie):
    fa=[i for i in range(F.L) if not tie[i]]
    if not fa: return float("inf")
    w=sl.eigh(F.Ka[np.ix_(fa,fa)],np.diag(F.mass[fa]),eigvals_only=True); return np.sqrt(w[0])/2/np.pi
for b in ("Jun","Aug"):
    m,h,ms=build(b,"kept"); A,p,Mab=size(m,h,ms); F=Frame(m,h,ms,A,p,0); L=len(m)
    print(b,"m_k",m.astype(int).tolist())
    for s in (1,2,3,4):
        for off in range(s):
            for fromtop in (False,True):
                tie=np.zeros(L,bool)
                idx=[(L-1-off)-j*s for j in range(L)] if fromtop else [(off+s-1)+j*s for j in range(L)]
                for i in idx:
                    if 0<=i<L: tie[i]=True
                print(b,"s",s,"off",off,"fromtop",fromtop,"nties",int(tie.sum()),"f_ax",round(fax(F,tie),2))
