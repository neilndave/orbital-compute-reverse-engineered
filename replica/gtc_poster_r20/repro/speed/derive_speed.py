"""Derive every panel-2 variant number from the committed GB10 speed-suite results (speed/results/) plus the locked r11 benchmark
(gb10_out/r11/BENCH_*). Medians of 3 separate-process repetitions. Writes speed/SPEED_NUMBERS_R11.json (shown string, raw value,
source files, and how it was computed). Usage: R11_ROOT=<root> python speed/derive_speed.py"""
import os,json,hashlib,statistics as st
from pathlib import Path
R=Path(os.environ['R11_ROOT']).resolve();S=R/'speed/results';G=R/'gb10_out/r11'
J=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();med=st.median
src=set();N={}
def put(k,raw,shown,files,how):
 for f in files:src.add(str(Path(f).relative_to(R)))
 N[k]=dict(raw=raw,shown=shown,sources=[str(Path(f).relative_to(R)) for f in files],how=how)
f3=lambda pat:[S/pat.format(i) for i in (1,2,3)]
# locked benchmark (same values as the r11 poster headline)
bg=[J(G/f'BENCH_GPU_{i}.json')['kernel_seconds'] for i in (1,2,3)];bc=[J(G/f'BENCH_CPU_{i}.json')['kernel_seconds'] for i in (1,2,3)];BF=[G/f'BENCH_{d}_{i}.json' for d in ('GPU','CPU') for i in (1,2,3)]
g,c=med(bg),med(bc);put('sweep_gpu_s',g,f'{g:.3f}',BF,'median kernel_seconds, locked benchmark');put('sweep_cpu_s',c,f'{c:.2f}',BF,'median kernel_seconds, locked benchmark');put('speedup_x',c/g,f'{c/g:.1f}',BF,'ratio of medians')
# scaling run
SG=[J(f)['rows'] for f in f3('SCALE_GPU_{}.json')];SC=[J(f)['rows'] for f in f3('SCALE_CPU_{}.json')];SF=f3('SCALE_GPU_{}.json')+f3('SCALE_CPU_{}.json')
for r in SG+SC:assert r[-1]['hard_feasible']==3048 and r[-1]['design_feasible']==2347 and r[-1]['selected_index']==1037888
rows=[]
for j,r0 in enumerate(SG[0]):
 n=r0['designs'];gg=med(r[j]['kernel_seconds'] for r in SG);cc=med(r[j]['kernel_seconds'] for r in SC);rows.append(dict(designs=n,gpu_s=gg,cpu_s=cc,ratio=cc/gg))
put('scaling_rows',rows,'',SF,'per-N medians of 3 processes; first N designs of the same grid')
slow=[r['designs'] for r in rows if r['ratio']<1];fast=[r['designs'] for r in rows if r['ratio']>1]
lo,hi=max(slow),min(d for d in fast if d>max(slow));put('crossover_low',lo,f'{lo:,}',SF,'largest measured N where GPU kernel is slower');put('crossover_high',hi,f'{hi:,}',SF,'smallest measured N above it where GPU is faster')
flat=[r['gpu_s'] for r in rows if 256<=r['designs']<=4096];put('gpu_floor_ms',med(flat)*1e3,f"{med(flat)*1e3:.1f}",SF,'median GPU kernel time over N=256..4,096 (latency floor)')
put('flat_upto',4096,'4,096',SF,'largest N on the flat GPU floor');put('scale_full_ratio',rows[-1]['ratio'],f"{rows[-1]['ratio']:.1f}",SF,'scaling-run ratio at 1,806,336')
put('sat_from',262144,'262,144',SF,'N from which measured ratio is within 5% of the full-grid ratio');assert all(r['ratio']>=.95*rows[-1]['ratio'] for r in rows if r['designs']>=262144)
sat=[r['ratio'] for r in rows if r['designs']>=262144];put('sat_ratio_range',[min(sat),max(sat)],f"{min(sat):.0f}–{max(sat):.0f}",SF,'measured ratio range for N>=262,144 (rounded)')
# scenarios
MG=[J(f) for f in f3('MC_GPU_{}.json')];MC=[J(f) for f in f3('MC_CPU_{}.json')];MF=f3('MC_GPU_{}.json')+f3('MC_CPU_{}.json')
assert len({m['P_inlet_le_393'] for m in MG+MC})==1 and all(len(m['cpu_affinity'])==1 for m in MC)
mg,mc=med(m['kernel_seconds'] for m in MG),med(m['kernel_seconds'] for m in MC)
put('mc_gpu_s',mg,f'{mg:.3f}',MF,'median kernel_seconds, 1,048,576 draws');put('mc_cpu_s',mc,f'{mc:.2f}',MF,'median kernel_seconds');put('mc_speedup_x',mc/mg,f'{mc/mg:.1f}',MF,'ratio of medians')
put('both_gpu_s',g+mg,f'{g+mg:.2f}',BF+MF,'sweep median + scenario median');put('both_cpu_s',c+mc,f'{c+mc:.1f}',BF+MF,'sweep median + scenario median')
ph=lambda s:3600/s;put('per_hour_gpu',ph(g),f'≈{round(ph(g),-1):,.0f}',BF,'3,600 s / GPU sweep kernel median (kernel time only)');put('per_hour_cpu',ph(c),f'≈{ph(c):,.0f}',BF,'3,600 s / CPU sweep kernel median')
put('both_per_hour_gpu',ph(g+mg),f'≈{round(ph(g+mg),-1):,.0f}',BF+MF,'3,600 s / (sweep + scenarios), GPU');put('both_per_hour_cpu',ph(c+mc),f'≈{ph(c+mc):,.0f}',BF+MF,'3,600 s / (sweep + scenarios), CPU')
rb=med(r[-1]['readback_postprocess_seconds'] for r in SG);put('gpu_readback_s',rb,f'{rb:.2f}',f3('SCALE_GPU_{}.json'),'median readback+selection at 1.81M (excluded from kernel time)')
# surrogate inference
UG=[J(f) for f in f3('SURR_GPU_{}.json')];UC=[J(f) for f in f3('SURR_CPU_{}.json')];UF=f3('SURR_GPU_{}.json')+f3('SURR_CPU_{}.json')
assert all(u['threads']==1 and len(u['cpu_affinity'])==1 for u in UC) and all(u['max_abs_diff_vs_table']==0 for u in UG)
ug,uc=med(u['kernel_seconds'] for u in UG),med(u['kernel_seconds'] for u in UC)
put('surr_gpu_s',ug,f'{ug:.3f}',UF,'median forward pass, 66,177 queries');put('surr_cpu_s',uc,f'{uc:.3f}',UF,'median forward pass, 1 thread');put('surr_queries',UG[0]['queries'],f"{UG[0]['queries']:,}",UF,'query grid size')
put('surr_cpu_table_diff',max(u['max_abs_diff_vs_table'] for u in UC),f"{max(u['max_abs_diff_vs_table'] for u in UC):.1e}",UF,'fp32 CPU vs CUDA rounding vs committed table')
# Warp fin table
FG=[J(f) for f in f3('FIN_TABLE_GPU_{}.json')];FC=[J(f) for f in f3('FIN_TABLE_CPU_{}.json')];FF=f3('FIN_TABLE_GPU_{}.json')+f3('FIN_TABLE_CPU_{}.json')
import numpy as np;ref=np.array(FG[0]['eta']);assert all(np.max(np.abs(np.array(t['eta'])-ref))<1e-12 for t in FG+FC)
fg,fc=med(t['wall_s'] for t in FG),med(t['wall_s'] for t in FC)
put('fin_gpu_s',fg,f'{fg:.0f}',FF,'median wall_s of fin_al_benchmark.py table (585 fp64 fin solves, 320x8 grid each)');put('fin_cpu_s',fc,f'{fc:.0f}',FF,'median wall_s, CPU pinned to one core');put('fin_points',len(ref),f'{len(ref)}',FF,'table points');put('fin_grid',[FG[0]['nx'],FG[0]['ny']],f"{FG[0]['nx']}×{FG[0]['ny']}",FF,'fin solver grid');put('fin_ratio',fc/fg,f'{fc/fg:.2f}',FF,'CPU/GPU')
# Newton
NW=[J(f) for f in f3('NEWTON_GPU_{}.json')];NF=f3('NEWTON_GPU_{}.json');assert all(n['all_latched'] and n['finite'] for n in NW)
ng=med(n['newton_compile_and_run_s'] for n in NW);put('newton_gpu_s',ng,f'{ng:.0f}',NF,'median newton_compile_and_run_s, radiator wing 690 simulated s at dt 0.01 (CUDA graph path; no CPU path)')
tg=g+mg+ug+fg+ng;tc=c+mc+uc+fc
put('total_gpu_s',tg,f'{tg:.0f}',BF+MF+UF+FF+NF,'sum of GPU stage medians');put('total_cpu_measured_s',tc,f'{tc:.0f}',BF+MF+UF+FF,'sum of CPU stage medians (Newton not measured)')
put('common_gpu_s',tg-ng,f'{tg-ng:.0f}',BF+MF+UF+FF,'GPU sum over stages that have a CPU equivalent')
out=dict(numbers=N,source_sha256={k:sha(R/k) for k in sorted(src)},derive_script_sha256=sha(__file__))
(R/'speed/SPEED_NUMBERS_R11.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
for k,v in N.items():
 if k!='scaling_rows':print(k,v['shown'],round(v['raw'],6) if isinstance(v['raw'],float) else v['raw'])
