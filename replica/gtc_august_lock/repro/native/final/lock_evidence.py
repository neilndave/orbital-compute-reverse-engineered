"""Deterministically attach frozen measured final-geometry evidence.
Measured timings stay declared common inputs, never live host-dependent pipeline output.
Core power/mass/thermal/freeze arithmetic is still recomputed by preceding stages.
"""
import os
import os,json,hashlib
from pathlib import Path
R=Path(os.environ.get('GTCFC_ROOT',os.environ['GTCFC_ROOT']+''));J=lambda p:json.loads((R/p).read_text());f=J('final/GTC_FINAL_CANDIDATE.json')['fleets'][1];e=J('inputs/LOCK_MECHANICS_V3.json');g=e['geometry'];checks=[]
def ck(n,b):checks.append(dict(check=n,passed=bool(b)));assert b,n
ck('Native total spacecraft mass matches tested geometry',abs(f['sc_mass_kg']['value']-g['mass_sc_kg'])<1e-6)
ck('Native array matches tested geometry',abs(f['solar_area_m2']['value']-g['solar_area_m2'])<1e-6)
ck('Native radiator matches tested geometry',f['radiator_panels']['value']==g['radiator_panels']==140)
ck('Header reroute abandoned',not e['header']['adopted'])
ck('Constructive ideal-envelope packing at least 30',e['packing']['PASS'] and e['packing']['count']>=30)
ck('Measured representative Newton paths finite and captured',all(z['finite'] and z['all_latched'] for z in e['newton']['cases']))
ck('Actual recorded finite-body paths have no sampled intersections',e['trace_clearance']['passed'])
ck('Local supported-panel load screen positive',all(z.get('min_yield_margin',1)>0 for z in e['fea']['results']))
ck('Local 10-mm fold gap load screen positive',all(z.get('two_adjacent_worst_case_gap_margin_mm',1)>0 for z in e['fea']['results']))
ck('No main-radiator recharge heat after battery deletion',f['array_v3']['recharge_heat_W']['value']==0)
ck('Nominal chip / peak fluid concept caps',f['GPU_nominal_K']['value']<=370 and f['coolant_radiator_inlet_peak_K']['value']<=393)
v=J('inputs/NVIDIA_TOOL_EVIDENCE_V3.json')['validation']['validated_native_physical_projection'];ck('Fresh complete pipeline matches the physical point verified by the NVIDIA studies',all(float(f"{f[k]['value']:.10g}")==v[k] for k in v))
if (R/'inputs/LOCK_NATIVE_PARITY.json').exists():
 native=J('inputs/LOCK_NATIVE_PARITY.json')
 for row,mode in zip(native['rows'],['nominal','peak']):
  values=row['values'];pairs=[(4,'GPU_'+mode+'_K'),(5,'HBM_'+mode+'_K'),(6,'coolant_radiator_inlet_'+mode+'_K'),(7,'sc_mass_kg'),(8,'launch_mass_kg')]
  ck('Frozen CUDA physical point matches final '+mode,all(abs(values[i]-f[k]['value'])<1e-6 for i,k in pairs))
e['pipeline_consistency_checks']=checks;e['scope']='Approved high-level first-iteration lock, not flight/hardware qualification. Whole-wing flexibility, actual Starship loads, connected finite stow/interfaces, headers/MMOD and full-peak chip temperatures remain OPEN. Freeze hardware fails the reference allocation but is charged in full.'
for name,data in [('MECHANICAL_LOCK.json',e)]:Path(name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
for src,dst in [('LOCK_NATIVE_PARITY.json','NATIVE_PARITY_LOCK.json'),('LOCK_FIN_STATES.json','FIN_STATES_LOCK.json'),('LOCK_RENDER.json','RENDER_LOCK.json')]:
 p=R/'inputs'/src
 if p.exists():Path(dst).write_text(json.dumps(json.loads(p.read_text()),sort_keys=True,indent=2)+'\n')
print('Lock consistency checks',len(checks),'PASS')
