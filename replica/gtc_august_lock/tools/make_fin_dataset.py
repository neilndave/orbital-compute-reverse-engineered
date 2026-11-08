"""Warp fp64 fin labels in two dimensionless groups a,b; independent held-out and grid checks."""
import json,time,hashlib,platform,os
from pathlib import Path
import numpy as np
from scipy.stats import qmc
import warp as wp
import warp_fin_ref as WF
wp.init();assert wp.get_cuda_device_count()>0
R=Path(__file__).resolve().parent;start=time.perf_counter();uv=qmc.Sobol(2,scramble=True,seed=20261107).random_base2(9)
a=np.exp(np.log(.008)+uv[:,0]*np.log(1.5/.008));b=.32+uv[:,1]*.40
K=167.;E=.89;T=390.;L=.026;sig=5.670374419e-8;eta=[];raw=[]
def solve(l,t,T,E,S,nx=160):
 f=WF.Fin(nx,8,l,l*8/nx,K,E,T,S,device='cuda:0');f.t.fill_(t);res=f.solve(tol=1e-9)
 return f.Q()/(2*E*sig*(T**4-S**4)*l*(f.h*8)),f.ncg,float(res)
for i,(aa,bb) in enumerate(zip(a,b)):
 t=2*E*sig*L**2*T**3/(K*aa);z,n,res=solve(L,t,T,E,bb*T);eta.append(z);raw.append((L,t,T,E,bb*T,n,res))
 if i%64==0:print('labels',i,'wall_s',time.perf_counter()-start,flush=True)
par=[]
for i in range(0,128,8):
 j=384+i;l2=.016+.002*(i%12);T2=355.+(i%4)*15;E2=.86;t2=2*E2*sig*l2*l2*T2**3/(K*a[j]);z,_,_=solve(l2,t2,T2,E2,b[j]*T2,320)
 par.append(dict(index=j,eta_grid160=eta[j],eta_actual_shape_grid320=z,abs_diff=abs(z-eta[j])))
np.savez_compressed(R/'FIN_DATASET.npz',x=np.stack([np.log(a),b],axis=1),eta=np.array(eta),raw=np.array(raw),train_index=np.arange(384),heldout_index=np.arange(384,512))
out=dict(tool='NVIDIA Warp',version=wp.__version__,device='cuda:0',device_name=wp.get_device('cuda:0').name,precision='fp64',samples=512,training=384,heldout=128,nx=160,ny=8,independent_check_nx=320,dimensionless_equation='u_xx=a*(u^4-b^4), a=2*epsilon*sigma*L^2*Tb^3/(k*t), b=Ts/Tb; eta_fin is invariant under the mapped physical geometry',max_dimensionless_grid_parity_abs=max(z['abs_diff'] for z in par),parity=par,passed=bool(max(z['abs_diff'] for z in par)<2e-4),wall_seconds=time.perf_counter()-start,dataset_sha256=hashlib.sha256((R/'FIN_DATASET.npz').read_bytes()).hexdigest(),seed=20261107)
(R/'FIN_DATASET_RESULT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True);assert out['passed']
