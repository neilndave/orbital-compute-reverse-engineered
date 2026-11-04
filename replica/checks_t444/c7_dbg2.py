from c7_ccx import *
m,h,ms=build("Jun","t440"); A,p,Mab=size(m,h,ms); F=Frame(m,h,ms,A,p,0)
for nm in (6,12,24):
    write("dbg",F,[16,19],nu=-0.95,nmode=nm); print(nm,[round(x,2) for x in freqs("dbg")[:12]])
