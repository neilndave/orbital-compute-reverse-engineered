"""r11 panel-2 ALL-CORE CPU baseline (20 cores: 10 Cortex-X925 + 10 Cortex-A725 on GB10).
Same fp64 Warp CPU code path as speed_bench.py. Warp's 'cpu' device runs a launch on one thread, so we
use 20 worker processes, each pinned to one distinct core (os.sched_setaffinity), each running the Warp CPU kernel.
 - mc:    the UNMODIFIED gpu_core.mc kernel, launched per chunk on row-slices of the identical 1,048,576x14 draw array (seed 20261107).
 - sweep: gpu_core.sweep body is index-based (i = wp.tid()), so a chunk wrapper kernel 'sweep_off' is the verbatim sweep
          body with i = wp.tid() + offset and out[i - offset] written to a chunk view; every physics call is the same
          gpu_core @wp.func (temperatures, mass, radiator_mass).
Work distribution: dynamic (shared atomic chunk counter, CHUNK rows per grab) so the slower A725 cores don't bottleneck.
Timing: per repetition a fresh process pool; each worker does Warp init, module load and a 512-thread warm-up launch
(JIT excluded, like the baseline), then waits at a barrier. Timed window = barrier release -> last worker finished its last
chunk (time.perf_counter = CLOCK_MONOTONIC, system-wide). Results are written straight into shared memory (no copy).
Setup, process spawn, warm-up and post-processing excluded, as in the 1-core/GPU baseline. Median of 3 repetitions.
Verification: outputs compared element-wise vs. the GPU (cuda:0) and 1-core Warp-CPU outputs of the same kernels."""
import os,sys,json,time,hashlib,platform,subprocess
from pathlib import Path
import numpy as np
from multiprocessing import get_context, shared_memory
R=Path(__file__).resolve().parent.parent  # ~/gtc_r11_variants
sys.path.insert(0,str(R))
NW=int(os.environ.get('NW','20')); CHUNK=int(os.environ.get('CHUNK','8192'))
NS=49*9*64*64; NM=2**20

def common(dev):
    import warp as wp, gpu_core as K
    P=json.load(open(R/'SWEEP_INPUTS.json'));T=np.load(R/'SURROGATE_TABLE.npz');L=P['base_ledger']
    pvals=[P['static_mass_kg'],P['base_sum_kg'],P['core0_kg'],P['ram0_m2'],P['prop0_kg'],P['original_rad_area_m2'],P['original_array_area_m2'],P['array_ram_factor'],P['drag_numerator'],P['dv0_m_s'],P['isp_g'],P['array_areal_kg_m2'],L['harness'],L['power_electronics'],L['structure_mech'],L['deployment_mechanisms'],P['BOL_W_m2'],P['pump_peak_W'],P['pump_nominal_W'],P['env_q_W_m2'],P['yoke_scale'],P['tube_block_multiplier'],P['safe_mode_kg'],P['switching_kg'],P['heater_strips_plus_harness_kg_ref'],P['swivel_kg_per_panel'],P['insert_plugs_kg_per_panel'],P['acc_kg_per_L'],P['specific_expansion_L_kg'],P['rack_trunk_fluid_kg'],P['header_fluid_kg_per_panel'],P['packing_verified_max_array_m2'],P['design_GPU_K'],P['design_inlet_K'],P['packing_verified_max_panels'],P['nominal_film_props']['cp'],P['nominal_film_props']['mu'],P['nominal_film_props']['k'],P['peak_film_props']['cp'],P['peak_film_props']['mu'],P['peak_film_props']['k'],P['env_ir_unit_W_m2'],P['env_albedo_W_m2'],P['peak_power_acceptance_W']]
    p=wp.array(pvals,dtype=wp.float64,device=dev);fe=wp.array(P['fe_by_n'],dtype=wp.float64,device=dev);cool=wp.array(P['coolant_by_n'],dtype=wp.float64,device=dev);tab=wp.array(T['eta'].ravel(),dtype=wp.float64,device=dev)
    return wp,K,p,fe,cool,tab

def mc_inputs():
    sel=json.load(open(R/'SELECTED.json'));u=np.random.Generator(np.random.PCG64(20261107)).random((NM,14))
    z=[sel['radiator_panels'],sel['half_fin_m'],sel['fin_thickness_m'],sel['array_area_m2']];return u,z

def worker(stage,core,shm_name,ctr,lock,barrier,times,wi):
    os.sched_setaffinity(0,{core})
    import allcore_kern as AK
    wp,K,p,fe,cool,tab=common('cpu'); dev='cpu'
    ncol=12 if stage=='sweep' else 4; N=NS if stage=='sweep' else NM
    shm=shared_memory.SharedMemory(name=shm_name);O=np.ndarray((N,ncol),dtype=np.float64,buffer=shm.buf)
    if stage=='mc':
        u,z=mc_inputs();Z=wp.array(z,dtype=wp.float64,device=dev)
        Uall=wp.array(u,dtype=wp.float64,device=dev)
    W=wp.zeros((512,ncol),dtype=wp.float64,device=dev)
    if stage=='sweep': wp.launch(AK.sweep_off,dim=512,inputs=[p,fe,cool,tab,W,0],device=dev)
    else: wp.launch(K.mc,dim=512,inputs=[Uall[0:512],Z,p,fe,tab,W],device=dev)
    wp.synchronize_device(dev)
    barrier.wait(); t0=time.perf_counter(); nchunks=0
    while True:
        with lock:
            s=ctr.value; ctr.value=s+CHUNK
        if s>=N: break
        e=min(N,s+CHUNK); out=wp.array(O[s:e],dtype=wp.float64,device=dev,copy=False)
        if stage=='sweep': wp.launch(AK.sweep_off,dim=e-s,inputs=[p,fe,cool,tab,out,s],device=dev)
        else: wp.launch(K.mc,dim=e-s,inputs=[Uall[s:e],Z,p,fe,tab,out],device=dev)
        wp.synchronize_device(dev); nchunks+=1
    t1=time.perf_counter(); times[3*wi]=t0; times[3*wi+1]=t1; times[3*wi+2]=nchunks
    del out; shm.close()

def run_allcore(stage):
    ctx=get_context('spawn'); ncol=12 if stage=='sweep' else 4; N=NS if stage=='sweep' else NM
    shm=shared_memory.SharedMemory(create=True,size=N*ncol*8); O=np.ndarray((N,ncol),dtype=np.float64,buffer=shm.buf); O[:]=np.nan
    ctr=ctx.Value('q',0,lock=False);lock=ctx.Lock();barrier=ctx.Barrier(NW);times=ctx.Array('d',3*NW,lock=False)
    cores=sorted(os.sched_getaffinity(0))[:NW]
    ps=[ctx.Process(target=worker,args=(stage,c,shm.name,ctr,lock,barrier,times,i)) for i,c in enumerate(cores)]
    [q.start() for q in ps];[q.join() for q in ps]
    assert all(q.exitcode==0 for q in ps),[q.exitcode for q in ps]
    t=np.array(times[:]).reshape(NW,3); wall=float(t[:,1].max()-t[:,0].min())
    res=O.copy(); shm.close(); shm.unlink()
    return wall,res,dict(cores=cores,per_worker_busy_s=[float(x) for x in t[:,1]-t[:,0]],per_worker_chunks=[int(x) for x in t[:,2]])

def run_single(stage,dev):
    import allcore_kern as AK
    wp,K,p,fe,cool,tab=common(dev)
    if stage=='sweep':
        O=wp.zeros((NS,12),dtype=wp.float64,device=dev);wp.launch(K.sweep,dim=512,inputs=[p,fe,cool,tab,O],device=dev);wp.synchronize_device(dev)
        st=time.perf_counter();wp.launch(K.sweep,dim=NS,inputs=[p,fe,cool,tab,O],device=dev);wp.synchronize_device(dev);kt=time.perf_counter()-st
    else:
        u,z=mc_inputs();U=wp.array(u,dtype=wp.float64,device=dev);Z=wp.array(z,dtype=wp.float64,device=dev);O=wp.zeros((NM,4),dtype=wp.float64,device=dev)
        wp.launch(K.mc,dim=512,inputs=[U,Z,p,fe,tab,O],device=dev);wp.synchronize_device(dev)
        st=time.perf_counter();wp.launch(K.mc,dim=NM,inputs=[U,Z,p,fe,tab,O],device=dev);wp.synchronize_device(dev);kt=time.perf_counter()-st
    return kt,O.numpy()

def summarize(stage,v):
    if stage=='sweep':
        hard=np.flatnonzero(v[:,9]>.5);good=np.flatnonzero(v[:,10]>.5);return dict(hard_feasible=int(len(hard)),design_feasible=int(len(good)),selected_index=int(good[np.argmin(v[good,0])]))
    return dict(P_inlet_le_393=float(np.mean(v[:,2]<=393)))

def cmp(a,b): d=np.abs(a-b); return dict(max_abs_diff=float(np.nanmax(d)),n_nan=int(np.isnan(a).sum()+np.isnan(b).sum()),bitwise_identical=bool(np.array_equal(a,b)))

if __name__=='__main__':
    import warp as wp; wp.config.quiet=True
    mode=sys.argv[1]; stage=sys.argv[2]; outp=Path(sys.argv[3])
    if mode=='allcore':
        wall,res,info=run_allcore(stage); np.save(outp.with_suffix('.npy'),res)
        r=dict(stage=stage,mode='allcore',workers=NW,chunk_rows=CHUNK,kernel_wall_seconds=wall,**info,**summarize(stage,res))
    else:
        dev=mode; os.sched_setaffinity(0,{5}) if dev=='cpu' else None
        kt,res=run_single(stage,dev); np.save(outp.with_suffix('.npy'),res)
        r=dict(stage=stage,mode=dev,kernel_seconds=kt,cpu_affinity=sorted(os.sched_getaffinity(0)),**summarize(stage,res))
    r.update(warp=wp.__version__,numpy=np.__version__,machine=platform.machine(),kernel_sha256=hashlib.sha256((R/'gpu_core.py').read_bytes()).hexdigest(),time_unix=time.time())
    outp.write_text(json.dumps(r,indent=1)); print(json.dumps({k:v for k,v in r.items() if 'per_worker' not in k}),flush=True)
