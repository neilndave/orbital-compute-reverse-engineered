"""Native NVIDIA Warp CUDA fp64 parity for the GTC FINAL CANDIDATE (independent GPU re-solve of every poster temperature root and the mass rollup). Derived from SPIN1: same inherited fin-table thermal root as the frozen baseline parity kernel, plus explicit extra radiator heat
(battery-recharge loss), film dR, and the SPIN1 rollup ledger. Cases: T2 recommended nominal (MPG40 + recharge heat), T1 MPG40 peak, T4 header-protected sensitivity. Not qualification."""
from pathlib import Path
import json,hashlib,time,platform
import numpy as np
import warp as wp
wp.init()
@wp.func
def eta(T:wp.float64,E:wp.float64,S:wp.float64,a:wp.array(dtype=wp.float64)):
 z=(wp.clamp(T,wp.float64(320.0),wp.float64(440.0))-wp.float64(320.0))/wp.float64(10.0)
 y=(wp.clamp(E,wp.float64(.6),wp.float64(1.0))-wp.float64(.6))/wp.float64(.05)
 x=(wp.clamp(S,wp.float64(150.0),wp.float64(250.0))-wp.float64(150.0))/wp.float64(25.0)
 i=wp.min(wp.int32(wp.floor(z)),11);j=wp.min(wp.int32(wp.floor(y)),7);k=wp.min(wp.int32(wp.floor(x)),3)
 f=z-wp.float64(i);g=y-wp.float64(j);h=x-wp.float64(k);v=wp.float64(0.0)
 for di in range(2):
  for dj in range(2):
   for dk in range(2):
    w1=wp.float64(1.0)-f
    if di==1:w1=f
    w2=wp.float64(1.0)-g
    if dj==1:w2=g
    w3=wp.float64(1.0)-h
    if dk==1:w3=h
    v+=w1*w2*w3*a[((i+di)*9+(j+dj))*5+k+dk]
 return v
@wp.func
def flux(T:wp.float64,E:wp.float64,S:wp.float64,a:wp.array(dtype=wp.float64)):
 return wp.float64(2.0)*E*wp.float64(5.670374419e-8)*(T*T*T*T-S*S*S*S)*eta(T,E,S,a)
@wp.kernel
def solve(x:wp.array2d(dtype=wp.float64),mass:wp.array2d(dtype=wp.float64),tab:wp.array(dtype=wp.float64),out:wp.array2d(dtype=wp.float64)):
 i=wp.tid();P=x[i,0];pump=x[i,1];Q=(P+wp.float64(2000.0)+pump)/wp.float64(.92)+x[i,8]
 rise=wp.float64(20.0)*Q/P;lo=wp.float64(250.0);hi=wp.float64(450.0);E=x[i,4];S=x[i,5]
 for s in range(70):
  mid=(lo+hi)*wp.float64(.5)
  q=x[i,2]/x[i,3]*(flux(mid,E,S,tab)+wp.float64(4.0)*flux(mid+rise*wp.float64(.5),E,S,tab)+flux(mid+rise,E,S,tab))/wp.float64(6.0)
  if q<Q:lo=mid
  else:hi=mid
 supply=(lo+hi)*wp.float64(.5)+wp.float64(.44);ref=supply+wp.float64(10.0);load=x[i,6]
 m=wp.float64(0.0)
 for j in range(mass.shape[1]):m+=mass[i,j]
 out[i,0]=Q;out[i,1]=rise;out[i,2]=supply;out[i,3]=ref;out[i,4]=ref+wp.float64(1.7)*load*(wp.float64(14.22)+x[i,9]);out[i,5]=ref+wp.float64(18.0)*load;out[i,6]=supply+rise;out[i,7]=m;out[i,8]=x[i,7]*m+wp.float64(2000.0)
 out[i,9]=Q-(P+wp.float64(2000.0)+pump)/wp.float64(.92)-x[i,8]
