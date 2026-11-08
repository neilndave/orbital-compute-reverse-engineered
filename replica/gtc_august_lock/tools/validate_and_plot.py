"""Independent NumPy/SciPy study validation and 300-dpi data figures (not spacecraft renders)."""
from pathlib import Path
import json,math,time,hashlib
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;OUT=R.parent/'figs';OUT.mkdir(exist_ok=True)
J=lambda p:json.loads((R/p).read_text())
P=J('SWEEP_INPUTS.json');SW=J('SWEEP_GB10_GPU.json');MC=J('MC_GB10_GPU.json');OP=J('OPT_GB10_GPU.json');S=SW['selected'];checks=[]
for stage in ('SWEEP','MC'):
 ref=np.load(R/f'{stage}_PARITY_GB10_GPU.npz')
 for lab in ('GB10_ARM_CPU','BOX_CPU'):
  z=np.load(R/f'{stage}_PARITY_{lab}.npz');d=float(np.max(np.abs(ref['values']-z['values'])))
  checks.append(dict(check=stage+' CUDA vs '+lab,samples=len(z['values']),max_abs_difference=d,passed=d<1e-6))
# Independently bracket the roots in NumPy/SciPy, rather than reuse Warp Newton code.
tab=np.load(R/'SURROGATE_TABLE.npz');interp=RegularGridInterpolator((tab['log_a'],tab['b']),tab['eta'])
sig=5.670374419e-8;n=S['radiator_panels'];L=S['half_fin_m'];th=S['fin_thickness_m'];area=n*P['panel_width_m']*P['panel_length_m'];nt=P['panel_width_m']/(2*L+.008)
def independent(u):
 eps,rr,hh,pm,dt,film,sol,env,view,pump,kk,hf,cps,mus=[lo+(hi-lo)*v for (lo,hi),v in zip(P['ranges'].values(),u)]
 E=eps*np.interp(n,np.arange(112,161),P['fe_by_n'])*P['yoke_scale']*P['tube_block_multiplier']*view
 sink=((P['env_ir_unit_W_m2']*eps+P['env_albedo_W_m2'])*env/(E*sig))**.25
 def q(T):
  a=2*E*sig*L*L*T**3/(kk*th);b=sink/T
  ef=float(interp([[np.clip(math.log(a),tab['log_a'][0],tab['log_a'][-1]),np.clip(b,tab['b'][0],tab['b'][-1])]])[0]);eta=(L*ef+.004)/(L+.004)
  return 2*E*sig*(T**4-sink**4)*eta
 values=[];qpeak=0.
 for it,pump0,props in [(175000.,P['pump_nominal_W'],P['nominal_film_props']),(250000.,P['pump_peak_W'],P['peak_film_props'])]:
  Q=(it+2000+pump0*pump*(20/dt)**2)/pm;rise=dt*Q/it
  root=brentq(lambda T:area*(q(T)+4*q(T+rise/2)+q(T+rise))/6-Q,280,440,xtol=1e-11)+.44
  cp=props['cp']*cps;mu=props['mu']*mus;kf=props['k'];md=it/(cp*dt);Re=4*md/(math.ceil(n/10)*nt*math.pi*.007*mu);Pr=cp*mu/kf;rt=max(Re,3000);f=(.79*math.log(rt)-1.64)**-2
  nut=f/8*(rt-1000)*Pr/(1+12.7*math.sqrt(f/8)*(Pr**(2/3)-1));blend=np.clip((Re-2300)/700,0,1);Nu=3.66*(1-blend)+nut*blend
  delta=Q/(n*nt*math.pi*.007*P['panel_length_m']*(Nu*kf/.007*hf));values.append((root+delta,rise));qpeak=Q
 supply=values[0][0];return np.array([supply+dt/2+1.19*rr*(.5+.5/film),supply+dt/2+.7*hh,values[1][0]+values[1][1],S['array_area_m2']*sol-qpeak])
sample=np.load(R/'MC_PLOT_GB10_GPU.npz');st=time.perf_counter();actual=np.array([independent(u) for u in sample['u'][:32]]);diff=float(np.max(abs(actual-sample['values'][:32])))
checks.append(dict(check='MC independent SciPy brentq / NumPy roots and film arithmetic',samples=32,max_abs_difference=diff,wall_seconds=time.perf_counter()-st,passed=diff<1e-6))
for label,p in [('BOX_CPU',R/'TABLE_BOX_CPU.json'),('GB10_ARM_CPU',R/'TABLE_GB10_ARM_CPU.json')]:
 a=json.loads((R/'TABLE_GB10_GPU.json').read_text());b=json.loads(p.read_text());d=float(max(abs(np.array(a['eta'])-b['eta'])));checks.append(dict(check='Selected native 585-point fin table CUDA vs '+label,max_abs_eta=d,passed=d<1e-10))
checks.append(dict(check='PhysicsNeMo truly held-out native Warp labels',samples=128,max_abs_eta=J('SURROGATE_RESULT.json')['heldout_max_abs_eta'],passed=J('SURROGATE_RESULT.json')['passed']))
checks.append(dict(check='Tape gradients vs central finite differences',max_relative_error=max(z['relative_error'] for z in OP['gradient_check']),passed=all(z['passed'] for z in OP['gradient_check'])))
C=json.loads((R.parent/'RESULTS_CANONICAL.json').read_text());A=C['August'];delta={k:A[key]['value']-S[k] for k,key in [('GPU_nominal_K','GPU_nominal_K'),('HBM_nominal_K','HBM_nominal_K'),('inlet_peak_K','coolant_radiator_inlet_peak_K'),('sc_mass_kg','sc_mass_kg')]}
checks.append(dict(check='Selected surrogate design vs native full pipeline',native_minus_sweep=delta,temperature_tolerance_K=1.,relative_mass_tolerance=.005,passed=max(abs(delta[k]) for k in ['GPU_nominal_K','HBM_nominal_K','inlet_peak_K'])<1 and abs(delta['sc_mass_kg'])/S['sc_mass_kg']<.005 and A['coolant_radiator_inlet_peak_K']['value']<=393 and A['GPU_nominal_K']['value']<=370))
result=dict(passed=all(c['passed'] for c in checks),checks=checks,scope='Arithmetic/numerical agreement, not hardware or stochastic reliability qualification');result['validated_native_physical_projection']={k:A[k]['value'] for k in ['sc_mass_kg','solar_area_m2','radiator_panels','GPU_nominal_K','HBM_nominal_K','coolant_radiator_inlet_peak_K']};(R/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
# Comparable timing scopes: warmed kernels; cached model time-to-answer; explicit cold compile/training costs.
speed={}
for stage in ('SWEEP','MC','OPT'):
 speed[stage]={}
 for lab in ('GB10_GPU','GB10_ARM_CPU','BOX_CPU'):
  z=J(f'{stage}_{lab}.json');speed[stage][lab]={k:z[k] for k in ['kernel_seconds','cached_model_time_to_answer_seconds','compile_and_warmup_seconds','optimization_wall_seconds','compile_and_first_tape_seconds','cpu_baseline'] if k in z}
speed['fin_table']={lab:json.loads(p.read_text())['wall_s'] for lab,p in [('GB10_GPU',R/'TABLE_GB10_GPU.json'),('GB10_ARM_CPU',R/'TABLE_GB10_ARM_CPU.json'),('BOX_CPU',R/'TABLE_BOX_CPU.json')]};speed['setup']=dict(native_GPU_labels_seconds=J('FIN_DATASET_RESULT.json')['wall_seconds'],PhysicsNeMo_GPU_training_seconds=J('SURROGATE_RESULT.json')['training_wall_seconds'],scope='No CPU label-generation/training benchmark: do NOT claim full cold end-to-end GPU speedup. All warmed study kernels use a frozen trained surrogate. Tape optimization is serial/launch-bound and is slower on GPU.');(R/'SPEED_PANEL.json').write_text(json.dumps(speed,indent=2)+'\n')
plt.rcParams.update({'font.size':12,'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False})
v=np.load(R/'SWEEP_PLOT_GB10_GPU.npz')['values'];mask=(v[:,5]==7)&(v[:,4]<=140);vv=v[mask]
fig,ax=plt.subplots(figsize=(9,5.2));sc=ax.scatter(vv[:,0],vv[:,3],c=vv[:,4],s=11,cmap='viridis',alpha=.8);ax.axhline(393,c='firebrick',ls='--',label='393 K inlet cap');ax.scatter([S['sc_mass_kg']],[S['inlet_peak_K']],s=220,marker='*',c='#f59e0b',edgecolors='black',label='Selected manufacturable grid point');ax.set(xlabel='Full spacecraft mass (kg)',ylabel='Peak radiator inlet (K)',title=f"Warp + PhysicsNeMo: {SW['configurations']:,} designs in {SW['kernel_seconds']:.3f} s");ax.legend(fontsize=9);fig.colorbar(sc,ax=ax,label='Radiator panels');fig.tight_layout();fig.savefig(OUT/'v3_panel1_design_sweep.png',dpi=300);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5.2));vv=sample['values'][:,2];ax.hist(vv,bins=65,color='#347da5',alpha=.9,density=True);ax.axvline(393,c='firebrick',ls='--',lw=2);ax.set(xlabel='Peak radiator inlet (K)',ylabel='Scenario density',title=f"Warp UQ: {100*MC['P_inlet_le_393']:.2f}% of assumed scenarios meet 393 K");ax.text(.02,.95,'1,048,576 draws; illustrative independent bounded uniforms\nNot a measured reliability probability',transform=ax.transAxes,va='top',fontsize=10);fig.tight_layout();fig.savefig(OUT/'v3_panel2_uncertainty.png',dpi=300);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5.2))
for p in OP['paths']:ax.plot([z['step'] for z in p['path']],[z['radiator_kg'] for z in p['path']],label=f"Start {p['run']+1}",alpha=.8)
best=OP['best_relaxed'];ax.axhline(SW['radiator_objective_grid_best']['radiator_mass_kg'],c='black',ls='--',label='Best discrete grid radiator');ax.scatter(best['step'],best['radiator_mass_kg'],s=130,marker='*',c='#f59e0b',edgecolors='black',zorder=4);ax.set(xlabel='Projected Adam / Tape iteration',ylabel='Relaxed radiator wet mass (kg)',ylim=(280,480),title=f"warp.Tape: {100*abs(OP['sweep_cross_check']['relative_difference']):.2f}% below discrete radiator grid");ax.text(.98,.94,'Continuous tube-count/fin relaxation, not adopted hardware\nFinal manufacturable design comes from the full-mass sweep',ha='right',va='top',transform=ax.transAxes,fontsize=9);ax.legend(fontsize=9);fig.tight_layout();fig.savefig(OUT/'v3_panel3_differentiable.png',dpi=300);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5.2));labs=['1.8M sweep\nwarm kernel','1M UQ\nwarm kernel','Tape local\noptimization','585 native fins\ntable solve'];x=np.arange(4)
for j,lab in enumerate(('GB10_GPU','GB10_ARM_CPU','BOX_CPU')):
 values=[speed['SWEEP'][lab]['kernel_seconds'],speed['MC'][lab]['kernel_seconds'],speed['OPT'][lab]['optimization_wall_seconds'],speed['fin_table'][lab]];ax.bar(x+(j-1)*.24,values,width=.24,label={'GB10_ARM_CPU':'GB10 Arm CPU','GB10_GPU':'GB10 GPU','BOX_CPU':'Box CPU'}[lab])
ax.set_xticks(x,labs);ax.set_yscale('log');ax.set_ylabel('Measured seconds (log scale)');ax.set_title('Honest speed panel: batching wins; tiny/serial jobs do not');ax.legend();fig.tight_layout();fig.savefig(OUT/'v3_honest_speed.png',dpi=300);plt.close(fig)
sv=np.load(R/'SURROGATE_VALIDATION.npz');fig,ax=plt.subplots(figsize=(6,5.2));ax.scatter(sv['true'],sv['prediction'],s=15);lims=[min(sv['true']),max(sv['true'])];ax.plot(lims,lims,c='black',ls='--');ax.set(xlabel='Held-out native Warp fin efficiency',ylabel='PhysicsNeMo prediction',title=f"128 held-out points: max |Δη| = {J('SURROGATE_RESULT.json')['heldout_max_abs_eta']:.2g}");fig.tight_layout();fig.savefig(OUT/'v3_surrogate_validation.png',dpi=300);plt.close(fig)
sens=sorted(MC['rank_sensitivity'],key=lambda x:abs(x['inlet']),reverse=True);fig,ax=plt.subplots(figsize=(9,5.2));ax.barh([z['input'] for z in sens][::-1],[z['inlet'] for z in sens][::-1]);ax.set(xlabel='Spearman rank correlation with peak inlet',title='Which engineering assumptions drive the inlet?');fig.tight_layout();fig.savefig(OUT/'v3_uq_rank_sensitivity.png',dpi=300);plt.close(fig)
print(json.dumps(result,indent=2));assert result['passed']
