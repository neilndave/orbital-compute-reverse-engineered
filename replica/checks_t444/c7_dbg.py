from c7_ccx import *
m,h,ms=build("Jun","t440"); A,p,Mab=size(m,h,ms); F=Frame(m,h,ms,A,p,0)
for tn in ([16,19],[13,16,19],[10,13,16,19],[4,7,10,13,16,19]):
    write("dbg",F,tn,nu=-0.95,nmode=6); print(tn,[round(x,2) for x in freqs("dbg")[:5]])
print("warp")
for tn in ([16,19],[13,16,19],[4,7,10,13,16,19]):
    F=Frame(m,h,ms,A,p,0); F.tie=np.array([ (i+2) in tn for i in range(F.L)])
    F.kax=E*m*A/p; Ka=np.zeros((F.L,F.L))
    for e in range(F.L):
        Ka[e,e]+=F.kax[e]
        if e>0: Ka[e-1,e-1]+=F.kax[e]; Ka[e,e-1]-=F.kax[e]; Ka[e-1,e]-=F.kax[e]
    F.Ka=Ka; fa,fl=F.freqs(); print(tn,fa.round(2),fl.round(2))
