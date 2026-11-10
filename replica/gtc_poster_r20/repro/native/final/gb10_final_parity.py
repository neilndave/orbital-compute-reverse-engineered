"""Native NVIDIA Warp CUDA fp64 parity for the GTC FINAL CANDIDATE (independent GPU re-solve of every poster temperature root and the mass rollup). Derived from SPIN1: same inherited fin-table thermal root as the frozen baseline parity kernel, plus explicit extra radiator heat
(battery-recharge loss), film dR, and the SPIN1 rollup ledger. Final August adopted states only: T2 nominal (zero peak-recharge heat), T1 MPG40 peak. Legacy comparison/sensitivity states are excluded. Not qualification."""
import os
from pathlib import Path
import json,hashlib,time,platform
import numpy as np
import warp as wp
wp.init()
@wp.func
def eta(T:wp.float64,E:wp.float64,S:wp.float64,a:wp.array(dtype=wp.float64),offset:wp.int32):
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
    v+=w1*w2*w3*a[offset+((i+di)*9+(j+dj))*5+k+dk]
 return v
@wp.func
def flux(T:wp.float64,E:wp.float64,S:wp.float64,a:wp.array(dtype=wp.float64),offset:wp.int32):
 return wp.float64(2.0)*E*wp.float64(5.670374419e-8)*(T*T*T*T-S*S*S*S)*eta(T,E,S,a,offset)
@wp.kernel
def solve(x:wp.array2d(dtype=wp.float64),mass:wp.array2d(dtype=wp.float64),tab:wp.array(dtype=wp.float64),out:wp.array2d(dtype=wp.float64)):
 i=wp.tid();offset=wp.int32(x[i,10]);P=x[i,0];pump=x[i,1];Q=(P+wp.float64(2000.0)+pump)/wp.float64(.92)+x[i,8]
 rise=wp.float64(20.0)*Q/P;lo=wp.float64(250.0);hi=wp.float64(450.0);E=x[i,4];S=x[i,5]
 for s in range(70):
  mid=(lo+hi)*wp.float64(.5)
  q=x[i,2]/x[i,3]*(flux(mid,E,S,tab,offset)+wp.float64(4.0)*flux(mid+rise*wp.float64(.5),E,S,tab,offset)+flux(mid+rise,E,S,tab,offset))/wp.float64(6.0)
  if q<Q:lo=mid
  else:hi=mid
 film=wp.float64(0.0)
 if x[i,11]>wp.float64(0.0):
  md=P/(x[i,13]*wp.float64(20.0));Re=wp.float64(4.0)*md/(x[i,12]*x[i,11]*wp.float64(3.141592653589793)*wp.float64(.007)*x[i,14]);Pr=x[i,13]*x[i,14]/x[i,15]
  Rt=wp.max(Re,wp.float64(3000.0));ff=wp.pow(wp.float64(.79)*wp.log(Rt)-wp.float64(1.64),wp.float64(-2.0))
  Nut=ff/wp.float64(8.0)*(Rt-wp.float64(1000.0))*Pr/(wp.float64(1.0)+wp.float64(12.7)*wp.sqrt(ff/wp.float64(8.0))*(wp.pow(Pr,wp.float64(.6666666666666666))-wp.float64(1.0)))
  Nu=wp.float64(3.66)
  if Re>=wp.float64(3000.0):Nu=Nut
  elif Re>wp.float64(2300.0):Nu+= (Nut-wp.float64(3.66))*(Re-wp.float64(2300.0))/wp.float64(700.0)
  hh=Nu*x[i,15]/wp.float64(.007);AA=x[i,16]*x[i,11]*wp.float64(0.06475513609432353);film=Q/(hh*AA)
 supply=(lo+hi)*wp.float64(.5)+wp.float64(.44)+film;ref=supply+wp.float64(10.0);load=x[i,6]
 m=wp.float64(0.0)
 for j in range(mass.shape[1]):m+=mass[i,j]
 out[i,0]=Q;out[i,1]=rise;out[i,2]=supply;out[i,3]=ref;out[i,4]=ref+wp.float64(1.7)*load*(wp.float64(14.22)+x[i,9]);out[i,5]=ref+wp.float64(18.0)*load;out[i,6]=supply+rise;out[i,7]=m;out[i,8]=x[i,7]*m+wp.float64(2000.0)
 out[i,9]=Q-(P+wp.float64(2000.0)+pump)/wp.float64(.92)-x[i,8]
import os
R=Path(os.environ.get('GTCFC_ROOT',os.environ['GTCFC_ROOT']+''));cfg=R/'final/GTC_FINAL_CANDIDATE.json';c=json.loads(cfg.read_text());th=json.loads((R/'stages/spin1/THERMAL_SPIN1.json').read_text())['cases']
tabp=R/'inputs/ai1_replica/gb10_final_al/table_AL6061_V3_AUG.json';t=json.loads(tabp.read_text());inp=[];m=[];expected=[];labels=[]
for i,f in enumerate(c['fleets']):
 nm=f['case'];
 if nm!='August':continue
 T=th[nm];A=f['radiator_effective_area_m2']['value'];fac=1.;N=f['spacecraft_count']['value']
 L=list(f['ledger_kg']['value'].values())
 rows=[('FINAL_nominal_T2',T['T2_rec_nominal_MPG40_plus_recharge'],L,f['sc_mass_kg']['value'],f['launch_mass_kg']['value']),('FINAL_peak_T1',T['T1_MPG40_peak'],L,f['sc_mass_kg']['value'],f['launch_mass_kg']['value'])]
 for lab,z,LL,scm,lm in rows:
  inp.append([z['IT_kW']*1000,z['pump_electric_W'],(A if lab.startswith('BASELINE') else f['radiator_effective_area_m2']['value']),fac,z['effective_emissivity'],z['effective_radiation_sink_K'],z['load_fraction'],N,z.get('extra_heat_W',0.0),z.get('dR_plate_KW',0.0),0,(c['config_v3']['parameters']['august_radiator']['NT'] if nm=='August' and not lab.startswith('BASELINE') else 0),T['geometry_v3']['radiator_columns'],z['fluid_props']['cp'],z['fluid_props']['mu'],z['fluid_props'].get('k',.6),f['radiator_panels']['value']])
  m.append(list(LL)+[0.0]*(20-len(LL)));expected.append([z['total_solar_power_and_rejected_heat_W'],z['radiator_delta_K'],z['coolant_supply_K'],z['coolant_rack_mean_K'],z['GPU_K'],z['HBM_K'],z['coolant_radiator_inlet_K'],scm,lm,0.]);labels.append(nm+'_'+lab)
n=len(inp);assert wp.get_cuda_device_count()>0;dev='cuda:0';X=wp.array(np.array(inp),dtype=wp.float64,device=dev);MA=wp.array(np.array(m),dtype=wp.float64,device=dev);TA=wp.array(np.array(t['eta']),dtype=wp.float64,device=dev);O=wp.zeros((n,10),dtype=wp.float64,device=dev)
start=time.time();wp.launch(solve,dim=n,inputs=[X,MA,TA,O],device=dev);wp.synchronize();v=O.numpy();err=np.max(np.abs(v-np.array(expected)),axis=1);ok=bool(max(err)<1e-6)
res=dict(label='Native NVIDIA Warp GB10 fp64 FINAL-CANDIDATE thermal-root and mass parity',scope=__doc__,machine=platform.machine(),device=str(wp.get_device(dev)),device_name=wp.get_device(dev).name,warp_version=wp.__version__,configuration_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),thermal_sha256=hashlib.sha256((R/'stages/spin1/THERMAL_SPIN1.json').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fin_lookup_sha256=hashlib.sha256(tabp.read_bytes()).hexdigest(),wall_seconds=time.time()-start,columns=['total_heat_W','radiator_delta_K','coolant_supply_K','coolant_rack_mean_K','GPU_K','HBM_K','coolant_radiator_inlet_K','sc_mass_kg','launch_kg','energy_residual_W'],rows=[dict(case=l,values=z.tolist(),max_absolute_box_difference=float(e)) for l,z,e in zip(labels,v,err)],max_abs_difference=float(max(err)),tolerance=1e-6,passed=ok,qualification_claim=False)
Path('GB10_FINAL_PARITY_RESULT.json').write_text(json.dumps(res,indent=2));print(json.dumps({k:res[k] for k in ('machine','device','device_name','warp_version','max_abs_difference','passed','configuration_sha256')}))

# v3 geometric exact view-factor parity, independent CUDA implementation vs NumPy contour.
import sys
sys.path.insert(0,str(R/'stages/spin1'))
from array_v3 import points,exact
from viewfactor_exact_warp import exact as warp_exact
G=json.load(open(R/'inputs/ARRAY_GEOMETRY_V3.json'));a=json.load(open(R/'stages/spin1/POWER_SPIN1.json'))['cases'];vr=[];geometry_start=time.perf_counter()
for nm in ('August',):
 aa=a[nm]['adopted_array'];gg=aa['layout_geometry'];yz,zr=points(gg);x0=gg['array_root_mm']/1000;length=aa['wing_length_m']
 vv=warp_exact(yz[:,0],yz[:,1],[[x0,x0+length,-7,7,zr]],device=dev)
 ref=exact(gg,length);d=float(np.max(np.abs(vv-ref)))
 vr.append(dict(case=nm,points=len(ref),max_abs_difference=d,passed=d<1e-12))
res['array_view_parity']=vr;res['passed']=res['passed'] and all(z['passed'] for z in vr)
Path('GB10_FINAL_PARITY_RESULT.json').write_text(json.dumps(res,indent=2));assert res['passed'],res
print('v3 array-view and thermal/mass parity',res['passed'])

res['geometry_wall_seconds']=time.perf_counter()-geometry_start
warm=[]
for repeat in range(5):
 wp.synchronize();st=time.perf_counter();wp.launch(solve,dim=n,inputs=[X,MA,TA,O],device=dev);wp.synchronize();warm.append(time.perf_counter()-st)
res['thermal_kernel_warm_seconds']=warm;res['thermal_kernel_warm_median_seconds']=float(np.median(warm))
res['tool_versions']=dict(warp=wp.__version__,numpy=np.__version__)
Path('GB10_FINAL_PARITY_RESULT.json').write_text(json.dumps(res,indent=2))
print('thermal_kernel_warm_median_seconds',res['thermal_kernel_warm_median_seconds'],'geometry_wall_seconds',res['geometry_wall_seconds'])
