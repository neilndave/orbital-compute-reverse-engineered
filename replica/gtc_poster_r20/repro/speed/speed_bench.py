"""r11 panel-2 speed study. Unmodified r11 fp64 Warp kernels (gpu_core.py sha cb07f775...), same inputs as the locked sweep.
Timing method identical to sweep/run_benchmark.py: one process per repetition, 512-thread warm-up launch (JIT/module load excluded),
then wp.launch + wp.synchronize_device inside a perf_counter window; setup, host->device copies, readback and postprocess excluded.
stage 'scale': sweep kernel launched with dim=N over the first N points of the 1,806,336-point grid (prefix of the same grid).
stage 'mc'   : the 1,048,576-draw scenario kernel at the selected design (seed 20261107), as in run_tools.py mc.
Readback+postprocess time is recorded separately (not part of the kernel time)."""
import os,sys,json,time,hashlib,platform,argparse
from pathlib import Path
import numpy as np, warp as wp
import gpu_core as K
R=Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['scale','mc']);ap.add_argument('--device',default='cuda:0');ap.add_argument('--label',required=True);a=ap.parse_args();wp.init();dev=a.device
P=json.load(open(R/'SWEEP_INPUTS.json'));T=np.load(R/'SURROGATE_TABLE.npz');L=P['base_ledger']
pvals=[P['static_mass_kg'],P['base_sum_kg'],P['core0_kg'],P['ram0_m2'],P['prop0_kg'],P['original_rad_area_m2'],P['original_array_area_m2'],P['array_ram_factor'],P['drag_numerator'],P['dv0_m_s'],P['isp_g'],P['array_areal_kg_m2'],L['harness'],L['power_electronics'],L['structure_mech'],L['deployment_mechanisms'],P['BOL_W_m2'],P['pump_peak_W'],P['pump_nominal_W'],P['env_q_W_m2'],P['yoke_scale'],P['tube_block_multiplier'],P['safe_mode_kg'],P['switching_kg'],P['heater_strips_plus_harness_kg_ref'],P['swivel_kg_per_panel'],P['insert_plugs_kg_per_panel'],P['acc_kg_per_L'],P['specific_expansion_L_kg'],P['rack_trunk_fluid_kg'],P['header_fluid_kg_per_panel'],P['packing_verified_max_array_m2'],P['design_GPU_K'],P['design_inlet_K'],P['packing_verified_max_panels'],P['nominal_film_props']['cp'],P['nominal_film_props']['mu'],P['nominal_film_props']['k'],P['peak_film_props']['cp'],P['peak_film_props']['mu'],P['peak_film_props']['k'],P['env_ir_unit_W_m2'],P['env_albedo_W_m2'],P['peak_power_acceptance_W']]
p=wp.array(pvals,dtype=wp.float64,device=dev);fe=wp.array(P['fe_by_n'],dtype=wp.float64,device=dev);cool=wp.array(P['coolant_by_n'],dtype=wp.float64,device=dev);tab=wp.array(T['eta'].ravel(),dtype=wp.float64,device=dev)
sync=lambda:wp.synchronize_device(dev);sha=lambda f:hashlib.sha256((R/f).read_bytes()).hexdigest()
out=dict(stage=a.stage,label=a.label,device=str(wp.get_device(dev)),machine=platform.machine(),warp=wp.__version__,numpy=np.__version__,precision='fp64',kernel_sha256=sha('gpu_core.py'),inputs_sha256=sha('SWEEP_INPUTS.json'),surrogate_sha256=sha('SURROGATE_TABLE.npz'),cpu_affinity=sorted(os.sched_getaffinity(0)),thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},method=__doc__)
if a.stage=='scale':
 n=49*9*64*64;O=wp.zeros((n,12),dtype=wp.float64,device=dev)
 st=time.perf_counter();wp.launch(K.sweep,dim=512,inputs=[p,fe,cool,tab,O],device=dev);sync();out['compile_and_warmup_seconds']=time.perf_counter()-st
 rows=[]
 for N in [64,256,1024,4096,16384,65536,262144,1048576,1806336]:
  st=time.perf_counter();wp.launch(K.sweep,dim=N,inputs=[p,fe,cool,tab,O],device=dev);sync();kt=time.perf_counter()-st
  r=dict(designs=N,kernel_seconds=kt)
  if N==n:
   pt=time.perf_counter();v=O.numpy();hard=np.flatnonzero(v[:,9]>.5);good=np.flatnonzero(v[:,10]>.5);sel=int(good[np.argmin(v[good,0])]);r.update(readback_postprocess_seconds=time.perf_counter()-pt,hard_feasible=len(hard),design_feasible=len(good),selected_index=sel)
  rows.append(r);print(json.dumps(r),flush=True)
 out['rows']=rows
else:
 sel=json.load(open(R/'SELECTED.json'));n=2**20;u=np.random.Generator(np.random.PCG64(20261107)).random((n,14));U=wp.array(u,dtype=wp.float64,device=dev)
 Z=wp.array([sel['radiator_panels'],sel['half_fin_m'],sel['fin_thickness_m'],sel['array_area_m2']],dtype=wp.float64,device=dev);O=wp.zeros((n,4),dtype=wp.float64,device=dev)
 st=time.perf_counter();wp.launch(K.mc,dim=512,inputs=[U,Z,p,fe,tab,O],device=dev);sync();out['compile_and_warmup_seconds']=time.perf_counter()-st
 st=time.perf_counter();wp.launch(K.mc,dim=n,inputs=[U,Z,p,fe,tab,O],device=dev);sync();kt=time.perf_counter()-st
 pt=time.perf_counter();v=O.numpy();pin=float(np.mean(v[:,2]<=393));out.update(draws=n,seed=20261107,kernel_seconds=kt,readback_postprocess_seconds=time.perf_counter()-pt,P_inlet_le_393=pin,selected_sha256=sha('SELECTED.json'))
 print(json.dumps(dict(kernel_seconds=kt,P=pin)),flush=True)
(R/'results').mkdir(exist_ok=True);(R/'results'/f'{a.stage.upper()}_{a.label}.json').write_text(json.dumps(out,indent=2)+'\n')
