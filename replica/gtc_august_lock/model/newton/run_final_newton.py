"""Rerun existing Newton Featherstone + Warp reference on final masses and spans.
Rigid panels, fixed bus; mirror-pair reactions cancel by ideal symmetry only. No Newton
contact claim: independent finite-box geometry checks are mandatory. Model setup fixes:
full sc mass, actual 4.1366-m bus-axis root, 140-panel loading, finite hinge/COM offsets, root-first motor sequence, 5-kNm/rad damped latches, motor disabled after lock, latch damping sized to bounded outboard inertia, graph batch 100.
"""
import os,sys,json,math,time,importlib,hashlib
from pathlib import Path
import numpy as np
import warp as wp
import newton
B=Path(__file__).resolve().parent;G=json.load(open(B/'FINAL_GEOMETRY.json'));base=B/'experiments';sys.path[:0]=[str(base/'newton_array'),str(base/'phase2')];os.environ['RTS_TAG']='_T45'
import run_array as A
kind=sys.argv[1];tdep=float(sys.argv[2]) if len(sys.argv)>2 else 300.;dt=float(sys.argv[3]) if len(sys.argv)>3 else .002
A.M_BUS_TOTAL=G['mass_sc_kg'];A.BX=.7;A.BY=2.;A.STANDOFF=.15
if kind=='solar':
 A.ARRAY_KG_TOTAL=G['ledger_kg']['array'];A.A_TOTAL=G['solar_area_m2'];A.W_LEAF=14.;A.WING_L=G['array_wing_length_m'];A.YOKE_L=G['array_root_m']-(A.BX/2+A.STANDOFF);A.N_LEAF=20;A.M_YOKE=4.1;A.M_LEAF=A.ARRAY_KG_TOTAL/2/20
else:
 A.N_LEAF=10;A.W_LEAF=G['radiator']['panel_width_m'];A.WING_L=10*(G['radiator']['panel_length_m']+.004);A.YOKE_L=1.06-(A.BX/2+A.STANDOFF);A.M_YOKE=1.5;A.M_LEAF=G['ledger_kg']['radiator']/140+1.1831331157142857;A.ARRAY_KG_TOTAL=2*A.N_LEAF*A.M_LEAF
A.L_LEAF=A.WING_L/A.N_LEAF;A.N_HINGE=A.N_LEAF+1;A.STROKE=np.array([math.pi/2]+[math.pi]*A.N_LEAF);A.SIGN=np.array([1. if i%2==0 else -1. for i in range(A.N_HINGE)]);A.LEN=np.array([A.YOKE_L]+[A.L_LEAF]*A.N_LEAF);A.MASS=np.array([A.M_YOKE]+[A.M_LEAF]*A.N_LEAF);A.I_OUT=A.outboard_I();A.I_LEAF_HINGE=A.MASS*A.LEN**2/3
if kind!='solar':
 # The final geometry anchors the first radiator panel at Y=1.06 m, already
 # aligned +Y. Delete the legacy fictitious root boom + 90-degree root sweep.
 A.BX=1.82;A.N_LEAF=10;A.N_HINGE=10
 A.LEN=np.full(10,G['radiator']['panel_length_m']+.004);A.MASS=np.full(10,G['ledger_kg']['radiator']/140+1.1831331157142857)
 A.MASS[0]+=1.5 # inherited root support mass, conservatively spread on first panel
 A.STROKE=np.array([0.]+[math.pi]*9);A.SIGN=np.array([1. if i%2==0 else -1. for i in range(10)])
 A.I_OUT=A.outboard_I();A.I_LEAF_HINGE=A.MASS*A.LEN**2/3
A.CHILD_OFF=np.zeros(A.N_HINGE); A.COM_OFF=np.zeros(A.N_HINGE)
if kind=='solar':
 A.CHILD_OFF[1]=.015
 for i in range(2,A.N_HINGE):A.CHILD_OFF[i]=.015 if (i-2)%2==0 else -.021
 A.COM_OFF[0]=.09;A.COM_OFF[1:]=-.003
else:
 for i in range(1,A.N_HINGE):A.CHILD_OFF[i]=-.005 if i%2 else .005
import fold_chain_T45 as F
import newton_xcheck_T45 as X
wp.init();wp.set_device('cuda:0')
# Soften only if an existing penalty-latch setup fails; each attempt explicitly identified.
F.KLAT=float(os.environ.get('LOCK_KLAT','20000'));F.ZLAT=float(os.environ.get('LOCK_ZLAT','.7'))
print('START',kind,tdep,dt,'geometry',A.LEN.tolist(),'mass',A.MASS.tolist(),flush=True)
settle=float(os.environ.get('LOCK_SETTLE_SECONDS','180'))
t0=time.perf_counter();rn=X.run('motor',tdep,dt,tend=tdep+settle,rec_every=max(2,int(round(1.0/dt))),klat_val=F.KLAT,zlat_val=F.ZLAT);compile_and_run=time.perf_counter()-t0
print('NEWTON',rn['wall'],'nan',rn['t_nan'],'latched',sum(rn['t_latch']>=0),flush=True)
rw=X.warp_ref('motor',tdep,dt,tend=tdep+settle);res=X.compare(rn,rw,f'lock_{kind}_{tdep:g}_{dt:g}');res.update(scope=__doc__,kind=kind,tdep_s=tdep,klat_Nm_rad=F.KLAT,newton_compile_and_run_s=compile_and_run,newton_version=getattr(newton,'__version__','unknown'),warp_version=wp.__version__,device='cuda:0',lengths_m=A.LEN.tolist(),masses_kg=A.MASS.tolist(),final_mass_sc_kg=G['mass_sc_kg'],all_latched=bool(np.all(rn['t_latch']>=0)),finite=rn['t_nan'] is None,geometry_SHA256=hashlib.sha256((B/'FINAL_GEOMETRY.json').read_bytes()).hexdigest())
# Independent Newton FK geometry consistency vs planar chain for recorded angles.
model=X.build();s=model.state();maxfk=0.
for q in rn['h'][::max(1,len(rn['h'])//32)]:
 s.joint_q.assign(np.asarray(q,np.float32));newton.eval_fk(model,s.joint_q,s.joint_qd,s)
 bodies=s.body_q.numpy()[1:,:2];angs=np.cumsum(q);start=np.array([A.BX/2+A.STANDOFF,0.]);pts=[]
 for i,(L,ang) in enumerate(zip(A.LEN,angs)):
  rot=np.array([[math.cos(ang),-math.sin(ang)],[math.sin(ang),math.cos(ang)]])
  pts.append(start+rot@np.array([L/2,-A.CHILD_OFF[i]]))
  dy=A.CHILD_OFF[i+1]-A.CHILD_OFF[i] if i+1<A.N_HINGE else 0.
  start=start+rot@np.array([L,dy])
 maxfk=max(maxfk,float(abs(bodies-np.array(pts)).max()))
res['Newton_FK_max_abs_m']=maxfk
res['peak_root_force_warp_N']=float(rw['pk_rootF'][0])
res['child_hinge_offsets_m']=A.CHILD_OFF.tolist();res['body_COM_offsets_m']=A.COM_OFF.tolist()
res['latch_damping_policy']=f"0.7 critical against min(outboard inertia, {os.environ.get('LOCK_DAMP_CAP','64')} times own hinge inertia); hardware qualification OPEN"
res['settle_seconds']=settle
res['control_root_seconds']=F.ROOT_T;res['control_main_seconds']=F.MAIN_T
out=B/'results_lock';out.mkdir(exist_ok=True);name=f'{kind}_t{tdep:g}_dt{dt:g}_kl{F.KLAT:g}';np.savez_compressed(out/f'{name}.npz',h_newton=rn['h'],h_warp=rw['hist'][0],t=np.arange(len(rn['h']))*1.0)
(out/f'{name}.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2),flush=True)
