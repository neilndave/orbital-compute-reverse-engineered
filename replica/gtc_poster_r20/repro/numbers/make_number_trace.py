"""r10 vs r11 per-number trace. r10 values are the printed r10 poster values (read-only PDF extraction, t773 recheck);
r11 values come only from out/POSTER_NUMBERS_R11.json. Δ% compares PRINTED values (r10 printed vs r11 printed); exact raw values are in POSTER_NUMBERS_R11.json. Flags any printed move > 1%."""
import os,json,csv,re
from pathlib import Path
R=Path(os.environ['R11_ROOT']).resolve();NN=json.loads((R/'out/POSTER_NUMBERS_R11.json').read_text())['numbers']
pv=lambda k:float(re.sub(r'[^0-9.e-]','',NN[k]['shown']))
rows=[# label, r10 printed, r10 numeric (or None), r11 key(s)/text, why
('Compute','NVL72-based, 79 GPUs',79,'one Vera Rubin NVL72, 72 GPUs + 36 CPUs',72,'Decision 4: exactly one NVL72 (primary-sourced topology)'),
('Payload allocation','assumed 640 kg, lightweighted',640,'assumed 640.38 kg allocation; 600×1200×937 mm box',640.38,'Wording: explicit assumption; no lightweighting claim'),
('Peak power per satellite','250 kW',250,'250 kW peak at beginning of life',250,'Decision 1: modeled available {} kW rounds to 250; acceptance ≥249.9 kW'.format(NN['peak_available_BOL_kW']['shown'])),
('Satellites per launch','30',30,NN['satellites']['shown'],pv('satellites'),''),
('Fleet installed peak','7.5 MW',7.5,NN['fleet_peak_MW']['shown']+' MW',7.5,''),
('Launch budget','100 t',100,'100 t',100,''),
('Satellite mass','3,022 kg',3022,NN['sc_mass_kg']['shown']+' kg',pv('sc_mass_kg'),'MPG40 property fix: coolant loop +3.60, accumulator/freeze +0.06, propellant +0.07 kg'),
('Fleet mass','90.7 t',90.7,NN['fleet_t']['shown']+' t',pv('fleet_t'),'30 × satellite mass'),
('Dispenser','2 t',2,NN['dispenser_t']['shown']+' t',pv('dispenser_t'),''),
('Reserve','7.3 t',7.3,NN['reserve_t']['shown']+' t',pv('reserve_t'),'100 − fleet − dispenser'),
('Solar array area','862 m²',862,NN['solar_area_m2']['shown']+' m²',pv('solar_area_m2'),'Unchanged August array (fixed)'),
('Solar rating','324.55 W/m² on active cells',324.55,NN['module_rating_W_m2']['shown']+' W/m² assumed module rating, remaining planar area',pv('module_rating_W_m2'),'Wording only'),
('Nominal sunlit power','175 kW',175,NN['nominal_kW']['shown']+' kW',175,''),
('Annual average','164.4 kW',164.4,NN['annual_kW']['shown']+' kW',pv('annual_kW'),''),
('GPU temperature','366 K nominal',366,'≈370 K nominal target (est. {} K)'.format(NN['GPU_est_K']['shown']),pv('GPU_est_K'),'Decision 2; 366 K was the 1.7 kW/offset model, unsupported for Rubin; estimate is a conditional sensitivity'),
('HBM temperature','362 K nominal',362,'est. {} K, higher in edge cases; not yet qualified'.format(NN['HBM_est_K']['shown']),pv('HBM_est_K'),'Decision 2'),
('Coolant inlet peak','392 K',392,NN['coolant_inlet_peak_K']['shown']+' K',pv('coolant_inlet_peak_K'),'Bulk model; chemistry caveat omitted per decision 3'),
('Radiator panels','140',140,NN['radiator_panels']['shown'],pv('radiator_panels'),'Same selected geometry'),
('Coating emissivity','0.92',0.92,NN['emissivity']['shown'],0.92,''),
('Rack frame mass','≈50 kg',50,'≈50 kg (45.70 kg)',pv('frame_kg'),'Rerun in t773 with full 640.38 kg; printed value unchanged'),
('Rack frame mode','35 Hz',35,'35 Hz (35.88 Hz)',pv('frame_f1_Hz'),''),
('Panel first mode','128–153 Hz, ≈139 nominal',139,'{}–{} Hz, ≈{} nominal'.format(NN['panel_f1_min_Hz']['shown'],NN['panel_f1_max_Hz']['shown'],NN['panel_f1_nominal_Hz']['shown']),pv('panel_f1_nominal_Hz'),''),
('Designs screened','1.81M',1.81,NN['configurations']['shown']+'M',pv('configurations'),''),
('Search result','"a mass-feasible trade point" (3,095 hard / 2,398 design-margin feasible)',3095,'{} hard / {} design-margin feasible; lightest picked'.format(NN['hard_feasible']['shown'],NN['design_feasible']['shown']),pv('hard_feasible'),'Corrected MPG40 inputs; 249.9 kW acceptance; selected index unchanged ({})'.format(NN['selected_index']['shown'])),
('Screen estimate (star)','(not printed) 3,020.89 kg',3020.886550962454,NN['screen_mass_kg']['shown']+' kg',pv('screen_mass_kg'),'Reduced model, same index'),
('Solver re-check (diamond)','3022.48 kg / 140 panels',3022.48,NN['solver_mass_kg']['shown']+' kg / 140 panels',pv('solver_mass_kg'),'Native pipeline'),
('Scenario framing','42.08% pass fraction',42.08,'(removed; sensitivity analysis instead)',None,'Owner decision: do not frame Monte Carlo as a pass rate'),
('Scenario draws','1.05M',1.05,NN['scenario_draws']['shown']+'M',pv('scenario_draws'),''),
('Sensitivity rank subset','(not printed)',65536,NN['sens_rank_draws']['shown']+' draws',pv('sens_rank_draws'),'Spearman rank on 65,536-draw subset'),
('Inlet p5–p95','(not printed)',None,NN['inlet_p05_K']['shown']+'–'+NN['inlet_p95_K']['shown']+' K',None,'MC coolant inlet spread'),
('GPU MC median','(not printed)',None,NN['gpu_mc_median_K']['shown']+' K',pv('gpu_mc_median_K'),'MC GPU temperature median'),
('Top ρ inlet (PMAD)','(not printed)',None,NN['rho_PMAD_inlet']['shown'],pv('rho_PMAD_inlet'),'Spearman vs coolant inlet'),
('Top ρ inlet (emissivity)','(not printed)',None,NN['rho_emissivity_inlet']['shown'],pv('rho_emissivity_inlet'),'Spearman vs coolant inlet'),
('GPU speedup','33.1×',33.1,NN['speedup_x']['shown']+'×',pv('speedup_x'),'Fresh median-of-3 rerun (kernel gained the explicit power check)'),
('GPU warm sweep','0.213 s',0.213,NN['gpu_kernel_s']['shown']+' s',pv('gpu_kernel_s'),''),
('CPU warm sweep','7.04 s',7.04,NN['cpu_kernel_s']['shown']+' s',pv('cpu_kernel_s'),''),
('Throughput','8.49M designs/s',8.49,NN['throughput_Mps']['shown']+'M designs/s',pv('throughput_Mps'),''),
('Input SHA256 prefix','619e2da5375d…',None,NN['inputs_sha256']['shown']+'…',None,'Single-source regenerated inputs'),
('PhysicsNeMo held-out max |Δη|','9.3e-5',9.3e-5,NN['surrogate_heldout_max_abs_eta']['shown'],pv('surrogate_heldout_max_abs_eta'),''),
('PhysicsNeMo labels','384 / 128',384,'{} / {}'.format(NN['surrogate_train']['shown'],NN['surrogate_heldout']['shown']),384,''),
('warp.Tape relaxed mass gap','0.82%',0.82,NN['tape_gap_pct']['shown']+'%',pv('tape_gap_pct'),'Recomputed against the feasible discrete optimum (restored, new value)'),
('Hinge locks','31 / 31',31,'{0} / {0}'.format(NN['hinge_locks']['shown']),31,''),
('Angle parity','0.0061°',0.0061,NN['angle_parity_deg']['shown']+'°',pv('angle_parity_deg'),''),
('Newton / Warp versions','1.7.0 / 1.18.0',None,NN['newton_version']['shown']+' / '+NN['warp_version']['shown'],None,''),
('Effort span','≈11 days',11,NN['effort_days']['shown']+' days',pv('effort_days'),''),
('GB10 job time','≥44.1 h',44.1,NN['effort_hours']['shown']+' h',pv('effort_hours'),''),
('Release gates','2 passed release gates',2,'(removed)',None,'Claim dropped'),
]
out=[]
for lab,r10s,r10v,r11s,r11v,why in rows:
 pct=None if (r10v is None or r11v is None) else (r11v-r10v)/r10v*100
 changed=r10s.split(' (')[0]!=r11s.split(' (')[0]
 out.append(dict(item=lab,r10=r10s,r11=r11s,numeric_change_pct=None if pct is None else round(pct,3),moves_more_than_1pct=bool(pct is not None and abs(pct)>1),printed_text_changed=changed,why=why))
(R/'out/NUMBER_TRACE_R10_VS_R11.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
with open(R/'out/NUMBER_TRACE_R10_VS_R11.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
md=['# r10 vs r11 candidate — every poster number','','|Item|r10|r11|Δ%|>1%|Why|','|---|---|---|---:|---|---|']+[f"|{o['item']}|{o['r10']}|{o['r11']}|{'' if o['numeric_change_pct'] is None else o['numeric_change_pct']}|{'**YES**' if o['moves_more_than_1pct'] else ''}|{o['why']}|" for o in out]
(R/'out/NUMBER_TRACE_R10_VS_R11.md').write_text('\n'.join(md)+'\n');print('trace rows',len(out),'>1%:',[o['item'] for o in out if o['moves_more_than_1pct']])
