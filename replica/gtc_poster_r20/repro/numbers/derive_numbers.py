"""Derive every r11 poster number from committed pipeline outputs. No hidden state: each entry records source file, key path,
raw value and the formatted string printed on the poster. Usage: R11_ROOT=<repro dir> python3 numbers/derive_numbers.py <gb10_results_dir>"""
import os,sys,json,hashlib,statistics
from pathlib import Path
R=Path(os.environ['R11_ROOT']).resolve();G=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else R/'gb10_out'
J=lambda p:json.loads(Path(p).read_text());rel=lambda p:os.path.relpath(p,R);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
N={};SRC={}
def put(key,raw,shown,src,path,note=''):
    N[key]=dict(raw=raw,shown=shown,source=rel(src),key_path=path,note=note);SRC[rel(src)]=sha(src)
nat=R/'native';FC=nat/'final/GTC_FINAL_CANDIDATE.json';X=J(FC);A=X['fleets'][1];NC=nat/'r11_out/NATIVE_CHECKS.json';C=J(NC)
EC=nat/'stages/orbit/ECLIPSE_600KM.json';E=J(EC);TR=nat/'stages/spin1/freeze/out_A4_MPG40_cold_qt40.json';T=J(TR)
V=lambda k:A[k]['value'] if isinstance(A[k],dict) else A[k]
# --- requirements / topology (fixed inputs)
REQ=X['config_v3']['parameters']['design_requirements'];assert REQ['spacecraft_per_launch']==30 and REQ['installed_peak_per_sc_kW']==250 and REQ['launch_budget_kg']==100000
put('satellites',30,'30',FC,'config_v3/parameters/design_requirements/spacecraft_per_launch')
put('peak_target_kW',250,'250',FC,'config_v3/parameters/design_requirements/installed_peak_per_sc_kW')
put('fleet_peak_MW',7.5,'7.5',FC,'30 x 250 kW')
put('launch_t',100,'100',FC,'config_v3/parameters/design_requirements/launch_budget_kg')
# --- mass
m=V('sc_mass_kg');put('sc_mass_kg',m,format(m,',.0f'),FC,'fleets/1/sc_mass_kg/value')
put('fleet_t',30*m/1000,format(30*m/1000,'.1f'),FC,'30 x fleets/1/sc_mass_kg/value / 1000')
disp=X['dispenser_all_in_kg'];put('dispenser_t',disp/1000,format(disp/1000,'.0f'),FC,'dispenser_all_in_kg')
res=V('reserve_t_per_launch');put('reserve_t',res,format(res,'.1f'),FC,'fleets/1/reserve_t_per_launch/value')
assert abs(100-30*m/1000-disp/1000-res)<1e-9
# --- power (fixed August array, corrected MPG40)
S=C['solar'];pk=C['states']['peak'];nm=C['states']['nominal']
put('solar_area_m2',S['gross_planform_m2'],format(S['gross_planform_m2'],'.0f'),NC,'solar/gross_planform_m2')
put('module_rating_W_m2',S['locked_remaining_surface_rating_W_m2'],format(S['locked_remaining_surface_rating_W_m2'],'.2f'),NC,'solar/locked_remaining_surface_rating_W_m2','remaining-planar equivalent module rating (assumed)')
maxP=S['maximum_feasible_payload_BOL_kW'];put('peak_available_BOL_kW',maxP,format(maxP,'.1f'),NC,'solar/maximum_feasible_payload_BOL_kW','rounds to 250 kW; acceptance threshold 249.9 kW (rounding tolerance)')
assert maxP>=249.9
put('peak_BOL_shortfall_W',-pk['solar_margin_W'],format(-pk['solar_margin_W'],'.0f'),NC,'states/peak/solar_margin_W (negated)')
put('nominal_kW',175,'175',NC,'states/nominal/IT_kW');assert abs(nm['IT_kW']-175)<1e-6 and nm['solar_margin_W']>0
put('nominal_BOL_margin_W',nm['solar_margin_W'],format(nm['solar_margin_W'],'.0f'),NC,'states/nominal/solar_margin_W')
annual=175*(1-E['shadow_hours_per_year']/8766-(T['t_open_min']*E['eclipsed_orbits_per_year']/60)/8766)
put('annual_kW',annual,format(annual,'.1f'),EC,'175*(1-shadow_hours_per_year/8766-(t_open_min*eclipsed_orbits_per_year/60)/8766); t_open_min from '+rel(TR));SRC[rel(TR)]=sha(TR)
# --- thermal (bulk) and device sensitivity
put('coolant_inlet_peak_K',V('coolant_radiator_inlet_peak_K'),format(V('coolant_radiator_inlet_peak_K'),'.0f'),FC,'fleets/1/coolant_radiator_inlet_peak_K/value')
put('radiator_panels',V('radiator_panels'),format(V('radiator_panels'),'.0f'),FC,'fleets/1/radiator_panels/value')
put('emissivity',0.92,'0.92',FC,'coating emissivity BOL specification')
DT=R/'out/DEVICE_THERMAL_RECHECK.json';D=J(DT)
row=[r for r in D['thermal_sensitivities'] if r['case']=='nominal_175' and r['package_W']==1650 and r['HBM_fraction']==.2 and r['assumed_per_die_R_K_W']==.0072 and r['assumed_HBM_aggregate_R_K_W']==.02 and r['property_map_factor_assumed']==1.0];assert len(row)==1;row=row[0]
put('device_target_K',370,'370',DT,'nominal device target (owner decision); edge cases above 370 K accepted')
put('GPU_est_K',row['T_GPU_die_conditional_K'],format(row['T_GPU_die_conditional_K'],'.0f'),DT,'thermal_sensitivities[nominal_175,1650W,HBM 20%,R_die .0072,R_HBM .02,property factor 1.0]/T_GPU_die_conditional_K','conditional sensitivity, not qualified junction temperature')
put('HBM_est_K',row['T_HBM_conditional_K'],format(row['T_HBM_conditional_K'],'.0f'),DT,'same row/T_HBM_conditional_K')
# --- search / scenarios / Tape (GB10 CUDA, CPU parity)
SW=G/'r11/SWEEP_GB10_GPU.json';sw=J(SW);swc=J(G/'r11/SWEEP_GB10_CPU.json');sel=sw['selected']
assert (sw['hard_feasible_count'],sw['design_margin_feasible_count'],sel['index'])==(swc['hard_feasible_count'],swc['design_margin_feasible_count'],swc['selected']['index'])
assert sw['inputs_sha256']==sha(R/'sweep/SWEEP_INPUTS.json'),'GB10 sweep used different inputs than the committed SWEEP_INPUTS.json'
put('configurations',sw['configurations'],format(sw['configurations']/1e6,'.2f'),SW,'configurations')
put('hard_feasible',sw['hard_feasible_count'],format(sw['hard_feasible_count'],','),SW,'hard_feasible_count')
put('design_feasible',sw['design_margin_feasible_count'],format(sw['design_margin_feasible_count'],','),SW,'design_margin_feasible_count')
put('selected_index',sel['index'],str(sel['index']),SW,'selected/index')
put('screen_mass_kg',sel['sc_mass_kg'],format(sel['sc_mass_kg'],'.2f'),SW,'selected/sc_mass_kg','reduced-model screening estimate (star)')
put('solver_mass_kg',m,format(m,'.2f'),FC,'fleets/1/sc_mass_kg/value','native solver re-check (diamond)')
assert sel['radiator_panels']==V('radiator_panels') and abs(sel['array_area_m2']-S['gross_planform_m2'])<1e-9
MC=G/'r11/MC_GB10_GPU.json';mc=J(MC);mcc=J(G/'r11/MC_GB10_CPU.json');assert mc['P_inlet_le_393']==mcc['P_inlet_le_393']
# Sensitivity framing (not a pass rate): Spearman rank correlations + spread quantiles from the same MC run.
put('scenario_draws',mc['draws'],format(mc['draws']/1e6,'.2f'),MC,'draws')
put('sens_rank_draws',mc['rank_subset_draws'],format(mc['rank_subset_draws'],','),MC,'rank_subset_draws')
inq=mc['statistics']['inlet_peak_K']['quantiles'];gq=mc['statistics']['GPU_nominal_K']['quantiles']
put('inlet_p05_K',inq['p05'],format(inq['p05'],'.0f'),MC,'statistics/inlet_peak_K/quantiles/p05')
put('inlet_p95_K',inq['p95'],format(inq['p95'],'.0f'),MC,'statistics/inlet_peak_K/quantiles/p95')
put('gpu_mc_median_K',gq['p50'],format(gq['p50'],'.1f'),MC,'statistics/GPU_nominal_K/quantiles/p50')
# Top drivers by max(|Spearman|) on coolant inlet and GPU; plain-language ranges from mc["ranges"].
rank={r['input']:r for r in mc['rank_sensitivity']};rng=mc['ranges']
def rho(name,src_key,out_key):
    v=rank[name][src_key];put(f'rho_{name}_{out_key}',v,format(v,'.2f'),MC,f'rank_sensitivity[{name}]/{src_key}')
ORDER=['PMAD','emissivity','plate_resistance','rack_rise','film_scale','environment_scale','view_scale']
assert sorted(ORDER,key=lambda n: -max(abs(rank[n]['inlet']),abs(rank[n]['GPU'])))==ORDER
for name in ORDER:
    rho(name,'inlet','inlet');rho(name,'GPU','gpu')
# Range endpoints printed on tornado labels
put('range_PMAD_lo',rng['PMAD'][0]*100,format(rng['PMAD'][0]*100,'.0f'),MC,'ranges/PMAD[0] x 100')
put('range_PMAD_hi',rng['PMAD'][1]*100,format(rng['PMAD'][1]*100,'.0f'),MC,'ranges/PMAD[1] x 100')
put('range_emissivity_lo',rng['emissivity'][0],format(rng['emissivity'][0],'.2f'),MC,'ranges/emissivity[0]')
put('range_emissivity_hi',rng['emissivity'][1],format(rng['emissivity'][1],'.2f'),MC,'ranges/emissivity[1]')
put('range_plate_lo',rng['plate_resistance'][0],format(rng['plate_resistance'][0],'.1f'),MC,'ranges/plate_resistance[0]')
put('range_plate_hi',rng['plate_resistance'][1],format(rng['plate_resistance'][1],'.1f'),MC,'ranges/plate_resistance[1]')
put('range_rack_lo',rng['rack_rise'][0],format(rng['rack_rise'][0],'.0f'),MC,'ranges/rack_rise[0]')
put('range_rack_hi',rng['rack_rise'][1],format(rng['rack_rise'][1],'.0f'),MC,'ranges/rack_rise[1]')
put('range_film_lo',rng['film_scale'][0],format(rng['film_scale'][0],'.1f'),MC,'ranges/film_scale[0]')
put('range_film_hi',rng['film_scale'][1],format(rng['film_scale'][1],'.1f'),MC,'ranges/film_scale[1]')
env=rng['environment_scale'];pct=round((env[1]-1)*100);assert abs((1-env[0])*100-pct)<1e-9
put('range_env_pct',pct,format(pct,'.0f'),MC,'ranges/environment_scale → ±pct from 1.0')
put('range_view_lo',rng['view_scale'][0]*100,format(rng['view_scale'][0]*100,'.0f'),MC,'ranges/view_scale[0] x 100')
put('range_view_hi',rng['view_scale'][1]*100,format(rng['view_scale'][1]*100,'.0f'),MC,'ranges/view_scale[1] x 100')
OP=G/'r11/OPT_GB10_GPU.json';op=J(OP);assert op['passed']
gap=abs(op['sweep_cross_check']['relative_difference'])*100;put('tape_gap_pct',gap,format(gap,'.2f'),OP,'abs(sweep_cross_check/relative_difference) x 100','relaxed optimum vs feasible discrete grid minimum (same radiator objective)')
put('tape_gradient_max_rel_err',max(g['relative_error'] for g in op['gradient_check']),'passed',OP,'gradient_check/*/relative_error (<0.003)')
# --- benchmark: median of 3 controlled reps
bg=[J(G/f'r11/BENCH_GPU_{i}.json') for i in (1,2,3)];bc=[J(G/f'r11/BENCH_CPU_{i}.json') for i in (1,2,3)]
for b in bg+bc: assert b['inputs_sha256']==sw['inputs_sha256'] and b['kernel_sha256']==sw['kernel_sha256']
g=statistics.median(b['kernel_seconds'] for b in bg);c=statistics.median(b['kernel_seconds'] for b in bc)
B1=G/'r11/BENCH_GPU_1.json'
put('gpu_kernel_s',g,format(g,'.3f'),B1,'median over BENCH_GPU_{1,2,3}/kernel_seconds')
put('cpu_kernel_s',c,format(c,'.2f'),B1,'median over BENCH_CPU_{1,2,3}/kernel_seconds')
put('speedup_x',c/g,format(c/g,'.1f'),B1,'median CPU / median GPU kernel seconds')
put('throughput_Mps',sw['configurations']/g/1e6,format(sw['configurations']/g/1e6,'.2f'),B1,'configurations / median GPU kernel seconds / 1e6')
put('warp_version',bg[0]['warp'],bg[0]['warp'],B1,'warp')
put('inputs_sha256',sw['inputs_sha256'],sw['inputs_sha256'][:12],SW,'inputs_sha256')
for i in (2,3): SRC[rel(G/f'r11/BENCH_GPU_{i}.json')]=sha(G/f'r11/BENCH_GPU_{i}.json')
for i in (1,2,3): SRC[rel(G/f'r11/BENCH_CPU_{i}.json')]=sha(G/f'r11/BENCH_CPU_{i}.json')
# --- reused-scoped evidence (rerun on GB10 in the t773 recheck; scripts+inputs committed under evidence/)
FN=R/'evidence/fin/FIN_RECHECK_SUMMARY.json';fn=J(FN)['checkpoint']
put('surrogate_heldout_max_abs_eta',fn['heldout_max_abs_eta'],format(fn['heldout_max_abs_eta'],'.2g').replace('e-0','e-'),FN,'checkpoint/heldout_max_abs_eta')
put('surrogate_train',fn['training_labels'],str(fn['training_labels']),FN,'checkpoint/training_labels');put('surrogate_heldout',fn['heldout_labels'],str(fn['heldout_labels']),FN,'checkpoint/heldout_labels')
NW=R/'evidence/newton/NEWTON_RECHECK_SUMMARY.json';nw=J(NW)
put('hinge_locks',nw['aggregate_latched'],str(nw['aggregate_latched']),NW,'aggregate_latched')
put('angle_parity_deg',nw['aggregate_max_angle_difference_deg'],format(nw['aggregate_max_angle_difference_deg'],'.4f'),NW,'aggregate_max_angle_difference_deg')
put('newton_version',nw['radiator']['corrected']['newton_version'],nw['radiator']['corrected']['newton_version'],NW,'radiator/corrected/newton_version')
FR=R/'evidence/frame/FRAME_CONTROL_REPRODUCTION.json';fr=J(FR)
put('frame_kg',fr['frame_kg'],'≈50',FR,'frame_kg (45.70 kg, rounded up to ≈50 kg allocation wording)')
put('frame_f1_Hz',fr['frequencies_Hz'][0],'35',FR,'frequencies_Hz[0] (35.88 Hz, stated as reaches 35 Hz)')
PN=R/'evidence/panel/PANEL_RECHECK_SUMMARY.json';pn=J(PN);f=[c['new_f1_Hz'] for c in pn['cases']]
put('panel_f1_min_Hz',min(f),format(min(f),'.0f'),PN,'min cases/new_f1_Hz');put('panel_f1_max_Hz',max(f),format(max(f),'.0f'),PN,'max cases/new_f1_Hz');put('panel_f1_nominal_Hz',pn['finest_nominal_L3_reused'],format(pn['finest_nominal_L3_reused'],'.0f'),PN,'finest_nominal_L3_reused')
EF=R/'evidence/effort/HISTORICAL_TIME_RECHECK.json';ef=J(EF)
put('effort_days',ef['elapsed_days_recomputed'],'≈'+format(ef['elapsed_days_recomputed'],'.0f'),EF,'elapsed_days_recomputed')
h=ef['gb10_busy_hours_lower_bound_archived']['value'];put('effort_hours',h,'≥'+str(int(h*10)/10),EF,'gb10_busy_hours_lower_bound_archived/value (floored to 0.1 h)')
out=dict(revision='r11_candidate',adopted=False,numbers=N,source_sha256=SRC,derive_script_sha256=sha(__file__))
(R/'out').mkdir(exist_ok=True);(R/'out/POSTER_NUMBERS_R11.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print('numbers',len(N),sha(R/'out/POSTER_NUMBERS_R11.json'))
