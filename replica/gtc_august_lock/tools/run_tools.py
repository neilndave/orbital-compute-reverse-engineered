"""Run the same frozen surrogate-backed Warp model on CUDA, GB10 Arm CPU or box CPU.
Timings distinguish compilation, warm kernel, and measured cached-model time to answer.
"""
import os,sys,json,time,hashlib,platform,argparse
from pathlib import Path
import numpy as np
import warp as wp
import gpu_core as K
from scipy.stats import spearmanr
R=Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['sweep','mc','opt']);ap.add_argument('--device',default='cuda:0');ap.add_argument('--label',default='GB10_GPU');ap.add_argument('--design',default='SELECTED.json');a=ap.parse_args();wp.init();dev=a.device
if dev.startswith('cuda'):assert wp.get_cuda_device_count()>0
P=json.load(open(R/'SWEEP_INPUTS.json'));T=np.load(R/'SURROGATE_TABLE.npz');L=P['base_ledger'];pvals=[P['static_mass_kg'],P['base_sum_kg'],P['core0_kg'],P['ram0_m2'],P['prop0_kg'],P['original_rad_area_m2'],P['original_array_area_m2'],P['array_ram_factor'],P['drag_numerator'],P['dv0_m_s'],P['isp_g'],P['array_areal_kg_m2'],L['harness'],L['power_electronics'],L['structure_mech'],L['deployment_mechanisms'],P['BOL_W_m2'],P['pump_peak_W'],P['pump_nominal_W'],P['env_q_W_m2'],P['yoke_scale'],P['tube_block_multiplier'],P['safe_mode_kg'],P['switching_kg'],P['heater_strips_plus_harness_kg_ref'],P['swivel_kg_per_panel'],P['insert_plugs_kg_per_panel'],P['acc_kg_per_L'],P['specific_expansion_L_kg'],P['rack_trunk_fluid_kg'],P['header_fluid_kg_per_panel'],P['packing_verified_max_array_m2'],P['design_GPU_K'],P['design_inlet_K'],P['packing_verified_max_panels'],P['nominal_film_props']['cp'],P['nominal_film_props']['mu'],P['nominal_film_props']['k'],P['peak_film_props']['cp'],P['peak_film_props']['mu'],P['peak_film_props']['k'],P['env_ir_unit_W_m2'],P['env_albedo_W_m2']]
p=wp.array(pvals,dtype=wp.float64,device=dev);fe=wp.array(P['fe_by_n'],dtype=wp.float64,device=dev);cool=wp.array(P['coolant_by_n'],dtype=wp.float64,device=dev);tab=wp.array(T['eta'].ravel(),dtype=wp.float64,device=dev)
out=dict(stage=a.stage,label=a.label,device=str(wp.get_device(dev)),machine=platform.machine(),tool='NVIDIA Warp',warp=wp.__version__,numpy=np.__version__,precision='fp64',model_scope=K.__doc__,surrogate_sha256=hashlib.sha256((R/'SURROGATE_TABLE.npz').read_bytes()).hexdigest(),inputs_sha256=hashlib.sha256((R/'SWEEP_INPUTS.json').read_bytes()).hexdigest(),kernel_sha256=hashlib.sha256((R/'gpu_core.py').read_bytes()).hexdigest(),compilation_excluded_from_warm_kernel=True)
sync=lambda:wp.synchronize_device(dev)
if a.stage=='sweep':
 n=49*9*64*64;O=wp.zeros((n,12),dtype=wp.float64,device=dev);st=time.perf_counter();wp.launch(K.sweep,dim=512,inputs=[p,fe,cool,tab,O],device=dev);sync();out['compile_and_warmup_seconds']=time.perf_counter()-st
 st=time.perf_counter();wp.launch(K.sweep,dim=n,inputs=[p,fe,cool,tab,O],device=dev);sync();kt=time.perf_counter()-st;post=time.perf_counter();v=O.numpy();good=np.flatnonzero(v[:,10]>.5);hard=np.flatnonzero(v[:,9]>.5)
 assert len(hard)>0,'No design satisfies the modeled hard constraints; do not invent one'
 adopted=good if len(good) else hard;chosen=int(adopted[np.argmin(v[adopted,0])]);row=v[chosen];minrad=int(adopted[np.argmin(v[adopted,11])]);columns=['sc_mass_kg','GPU_nominal_K','HBM_nominal_K','inlet_peak_K','radiator_panels','tubes_per_panel','half_fin_m','fin_thickness_m','array_area_m2','hard_feasible','design_margin_feasible','radiator_mass_kg']
 selected=dict(zip(columns,map(float,row)));selected.update(index=chosen,reserve_t_per_launch=98-.03*float(row[0]),launch_t=2+.03*float(row[0]),reserve_pct_of_100t=98-.03*float(row[0]),peak_kW_per_sc=250.,nominal_kW_per_sc=175.,spacecraft_count=30,compute_MW_per_launch=7.5)
 out.update(configurations=n,grid=dict(panel_count=[112,160,49],tubes=[6,14,9],fin_thickness_mm=[.1,.5,64],array_growth_fraction=[0.,.04,64]),hard_feasible_count=len(hard),design_margin_feasible_count=len(good),selected=selected,radiator_objective_grid_best=dict(zip(columns,map(float,v[minrad]))),selection_rule='minimum full-spacecraft mass within a conservative verified packing subset, plus 1-K deterministic design margin if feasible; native Warp fin/table and full pipeline must validate selected design',packing_scope=P['packing_scope'],kernel_seconds=kt,throughput_configs_per_second=n/kt,postprocess_seconds=time.perf_counter()-post,cached_model_time_to_answer_seconds=kt+time.perf_counter()-post,passed=True)
 sample=np.unique(np.r_[np.linspace(0,n-1,2048,dtype=int),chosen,minrad]);np.savez_compressed(R/f'SWEEP_PARITY_{a.label}.npz',index=sample,values=v[sample]);sub=v[::64];np.savez_compressed(R/f'SWEEP_PLOT_{a.label}.npz',values=sub,columns=np.array(columns))
 if a.label=='GB10_GPU':(R/'SELECTED.json').write_text(json.dumps(selected,indent=2)+'\n')
 ranking=adopted[np.argsort(v[adopted,0])[:64]];out['top64']=[dict(zip(columns,map(float,v[j]))) for j in ranking]
elif a.stage=='mc':
 sel=json.load(open(R/a.design));out['design_input']=a.design;out['design_input_sha256']=hashlib.sha256((R/a.design).read_bytes()).hexdigest();n=2**20;seed=20261107;prep=time.perf_counter();u=np.random.Generator(np.random.PCG64(seed)).random((n,14));U=wp.array(u,dtype=wp.float64,device=dev);zz=[sel['radiator_panels'],sel['half_fin_m'],sel['fin_thickness_m'],sel['array_area_m2']];Z=wp.array(zz,dtype=wp.float64,device=dev);O=wp.zeros((n,4),dtype=wp.float64,device=dev);prep=time.perf_counter()-prep
 st=time.perf_counter();wp.launch(K.mc,dim=512,inputs=[U,Z,p,fe,tab,O],device=dev);sync();out['compile_and_warmup_seconds']=time.perf_counter()-st
 st=time.perf_counter();wp.launch(K.mc,dim=n,inputs=[U,Z,p,fe,tab,O],device=dev);sync();kt=time.perf_counter()-st;post=time.perf_counter();v=O.numpy();names=['GPU_nominal_K','HBM_nominal_K','inlet_peak_K','BOL_peak_power_margin_W'];stats={}
 for j,name in enumerate(names):stats[name]=dict(mean=float(v[:,j].mean()),std=float(v[:,j].std()),quantiles=dict(zip(['p01','p05','p50','p95','p99'],map(float,np.quantile(v[:,j],[.01,.05,.5,.95,.99])))))
 ranks=np.array([[spearmanr(u[:65536,j],v[:65536,k]).statistic for k in range(3)] for j in range(14)]);sensitivity=[dict(input=name,GPU=float(z[0]),HBM=float(z[1]),inlet=float(z[2])) for name,z in zip(P['ranges'],ranks)]
 out.update(draws=n,seed=seed,distributions='Independent bounded uniform engineering scenario ranges, NOT measured risk probabilities; independence and ranges are assumptions',ranges=P['ranges'],film_policy='Plate resistance split 50% conduction / 50% film; film multiplier acts only on film half, avoiding full-R double counting',statistics=stats,P_inlet_le_393=float(np.mean(v[:,2]<=393)),P_GPU_le_370=float(np.mean(v[:,0]<=370)),P_HBM_le_378p15=float(np.mean(v[:,1]<=378.15)),P_BOL_full_peak_generation=float(np.mean(v[:,3]>=0)),rank_sensitivity=sensitivity,rank_subset_draws=65536,kernel_seconds=kt,throughput_draws_per_second=n/kt,input_generation_and_transfer_seconds=prep,postprocess_seconds=time.perf_counter()-post,cached_model_time_to_answer_seconds=prep+kt+time.perf_counter()-post,passed=bool(np.isfinite(v).all()))
 np.savez_compressed(R/f'MC_PLOT_{a.label}.npz',values=v[::64],u=u[::64]);np.savez_compressed(R/f'MC_PARITY_{a.label}.npz',values=v[np.linspace(0,n-1,2048,dtype=int)],input_digest=np.array(hashlib.sha256(u[:1024].tobytes()).hexdigest()))
else:
 starts=[[1.,.1,.9],[1.,.35,.9],[.8,.05,.95]];paths=[];best=None;startwall=time.perf_counter();compile_wall=0.;gradient_check=[]
 def evaluate(zv,pen=1000.,gradient=False):
  z=wp.array(zv,dtype=wp.float64,device=dev,requires_grad=gradient);loss=wp.zeros(1,dtype=wp.float64,device=dev,requires_grad=gradient);metrics=wp.zeros(6,dtype=wp.float64,device=dev)
  if gradient:
   tape=wp.Tape()
   with tape:wp.launch(K.objective,dim=1,inputs=[z,p,fe,tab,wp.float64(pen),loss,metrics],device=dev)
   tape.backward(loss=loss);sync();g=z.grad.numpy().copy()
  else:wp.launch(K.objective,dim=1,inputs=[z,p,fe,tab,wp.float64(pen),loss,metrics],device=dev);sync();g=None
  return float(loss.numpy()[0]),metrics.numpy().copy(),g
 z0=np.array([.6,.3,.6]);st=time.perf_counter();base,_,grad=evaluate(z0,1000,True);compile_wall=time.perf_counter()-st
 for j in range(3):
  h=1e-5;zp=z0.copy();zm=z0.copy();zp[j]+=h;zm[j]-=h;fd=(evaluate(zp)[0]-evaluate(zm)[0])/(2*h);rel=abs(grad[j]-fd)/max(1.,abs(fd));gradient_check.append(dict(parameter=['panel_relaxation','fin_length','fin_thickness'][j],tape_gradient=float(grad[j]),finite_difference=float(fd),relative_error=float(rel),passed=bool(rel<.003)))
 for run,zv in enumerate(starts):
  z=np.array(zv);m=np.zeros(3);v2=np.zeros(3);path=[]
  for step in range(650):
   pen=100. if step<100 else 1000. if step<300 else 10000. if step<500 else 100000.
   loss,metrics,g=evaluate(z,pen,True);n,l,t,gpu,inlet,rad=metrics
   feasible=bool(gpu<=P['design_GPU_K'] and inlet<=P['design_inlet_K'])
   if feasible and (best is None or rad<best['radiator_mass_kg']):best=dict(radiator_mass_kg=float(rad),radiator_panels_relaxed=float(n),half_fin_m=float(l),fin_thickness_m=float(t),GPU_nominal_K=float(gpu),inlet_peak_K=float(inlet),run=run,step=step,z=z.tolist())
   if step%5==0:path.append(dict(step=step,panel_count=float(n),half_fin_mm=float(l*1000),thickness_mm=float(t*1000),GPU_K=float(gpu),inlet_K=float(inlet),radiator_kg=float(rad),loss=loss,penalty=pen,feasible=feasible))
   g=np.clip(g,-1e4,1e4);m=.9*m+.1*g;v2=.999*v2+.001*g*g;lr=.012 if step<500 else .002;z-=lr*(m/(1-.9**(step+1)))/(np.sqrt(v2/(1-.999**(step+1)))+1e-8);z=np.clip(z,0,1)
  paths.append(dict(run=run,path=path))
 out.update(optimization_wall_seconds=time.perf_counter()-startwall,compile_and_first_tape_seconds=compile_wall,gradient_check=gradient_check,starts=starts,iterations_per_start=650,objective='minimum radiator wet mass subject to design temperature goals; panel count, fin length and thickness continuously relaxed; full sweep uses full spacecraft mass',paths=paths,best_relaxed=best,passed=bool(best is not None and all(z['passed'] for z in gradient_check)),limitations='Local projected Adam penalty optimization, not a proof of global optimality. Discrete manufacturable point is selected by the grid and independently re-solved.')
 if best:
  sw=json.load(open(R/'SWEEP_GB10_GPU.json'))['radiator_objective_grid_best'];out['sweep_cross_check']=dict(grid_min_radiator_mass_kg=sw['radiator_mass_kg'],relaxed_best_kg=best['radiator_mass_kg'],relative_difference=(best['radiator_mass_kg']/sw['radiator_mass_kg']-1),note='Same radiator objective and temperature goals; continuous relaxation may be below discrete grid. The adopted minimum-spacecraft-mass choice may differ.')
out['cpu_baseline']=dict(backend='Warp CPU single-threaded' if str(dev)=='cpu' else 'CUDA',software_threads=1 if str(dev)=='cpu' else None,physical_cores_used=1 if str(dev)=='cpu' else None,host_logical_cpus=os.cpu_count(),process_cpu_affinity=sorted(os.sched_getaffinity(0)),thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']});path=R/f'{a.stage.upper()}_{a.label}.json';path.write_text(json.dumps(out,indent=2)+'\n');print(path.name,json.dumps({k:v for k,v in out.items() if k in ['configurations','draws','kernel_seconds','throughput_configs_per_second','throughput_draws_per_second','P_inlet_le_393','P_GPU_le_370','passed','selected','best_relaxed','gradient_check','sweep_cross_check']}),flush=True)
