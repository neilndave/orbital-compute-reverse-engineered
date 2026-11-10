"""Run the same frozen surrogate-backed Warp model on CUDA, Grace CPU or box CPU.
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
P=json.load(open(R/'SWEEP_INPUTS.json'));T=np.load(R/'SURROGATE_TABLE.npz');L=P['base_ledger'];pvals=[P['static_mass_kg'],P['base_sum_kg'],P['core0_kg'],P['ram0_m2'],P['prop0_kg'],P['original_rad_area_m2'],P['original_array_area_m2'],P['array_ram_factor'],P['drag_numerator'],P['dv0_m_s'],P['isp_g'],P['array_areal_kg_m2'],L['harness'],L['power_electronics'],L['structure_mech'],L['deployment_mechanisms'],P['BOL_W_m2'],P['pump_peak_W'],P['pump_nominal_W'],P['env_q_W_m2'],P['yoke_scale'],P['tube_block_multiplier'],P['safe_mode_kg'],P['switching_kg'],P['heater_strips_plus_harness_kg_ref'],P['swivel_kg_per_panel'],P['insert_plugs_kg_per_panel'],P['acc_kg_per_L'],P['specific_expansion_L_kg'],P['rack_trunk_fluid_kg'],P['header_fluid_kg_per_panel'],P['packing_verified_max_array_m2'],P['design_GPU_K'],P['design_inlet_K'],P['packing_verified_max_panels'],P['nominal_film_props']['cp'],P['nominal_film_props']['mu'],P['nominal_film_props']['k'],P['peak_film_props']['cp'],P['peak_film_props']['mu'],P['peak_film_props']['k'],P['env_ir_unit_W_m2'],P['env_albedo_W_m2'],P['peak_power_acceptance_W']]
p=wp.array(pvals,dtype=wp.float64,device=dev);fe=wp.array(P['fe_by_n'],dtype=wp.float64,device=dev);cool=wp.array(P['coolant_by_n'],dtype=wp.float64,device=dev);tab=wp.array(T['eta'].ravel(),dtype=wp.float64,device=dev)
out=dict(stage=a.stage,label=a.label,device=str(wp.get_device(dev)),machine=platform.machine(),tool='NVIDIA Warp',warp=wp.__version__,numpy=np.__version__,precision='fp64',model_scope=K.__doc__,surrogate_sha256=hashlib.sha256((R/'SURROGATE_TABLE.npz').read_bytes()).hexdigest(),inputs_sha256=hashlib.sha256((R/'SWEEP_INPUTS.json').read_bytes()).hexdigest(),kernel_sha256=hashlib.sha256((R/'gpu_core.py').read_bytes()).hexdigest(),compilation_excluded_from_warm_kernel=True)
sync=lambda:wp.synchronize_device(dev)

n=49*9*64*64;O=wp.zeros((n,12),dtype=wp.float64,device=dev)
st=time.perf_counter();wp.launch(K.sweep,dim=512,inputs=[p,fe,cool,tab,O],device=dev);sync();out['compile_and_warmup_seconds']=time.perf_counter()-st
st=time.perf_counter();wp.launch(K.sweep,dim=n,inputs=[p,fe,cool,tab,O],device=dev);sync();kt=time.perf_counter()-st
post=time.perf_counter();v=O.numpy();hard=np.flatnonzero(v[:,9]>.5);good=np.flatnonzero(v[:,10]>.5);eligible=good if len(good) else hard;chosen=None if not len(eligible) else int(eligible[np.argmin(v[eligible,0])])
out.update(configurations=n,kernel_seconds=kt,throughput_configs_per_second=n/kt,hard_feasible_count=len(hard),design_margin_feasible_count=len(good),selected_index=chosen,status='FEASIBLE' if len(hard) else 'NO_FEASIBLE_CONFIGURATION',physical_feasibility_passed=bool(len(hard)),measurement_completed=True,minimum_required_array_m2=float(v[:,8].min()),packing_maximum_array_m2=P['packing_verified_max_array_m2'],postprocess_seconds=time.perf_counter()-post,cpu_affinity=sorted(os.sched_getaffinity(0)),thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},timer_scope='512-warmup then full frozen fp64 Warp kernel; synchronize; exclude setup,JIT,readback,postprocess. Reporting adapter only; numerical kernel unchanged.')
ix=np.unique(np.r_[np.linspace(0,n-1,2048,dtype=int),1037888]);np.savez_compressed(R/f'PARITY_{a.label}.npz',index=ix,values=v[ix]);np.savez_compressed(R/f'PLOT_{a.label}.npz',values=v[::64])
(R/f'BENCH_{a.label}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2),flush=True)
