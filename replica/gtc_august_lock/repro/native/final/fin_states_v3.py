"""CUDA fp64 fin solves at v3 adopted nominal/peak states. Fixed geometry; diagnostic only."""
import os
import os,sys,json,time,hashlib
from pathlib import Path
import numpy as np
import warp as wp
R=Path(os.environ.get('GTCFC_ROOT',os.environ['GTCFC_ROOT']+''))
sys.path.insert(0,str(R/'inputs/ai1_replica/gb10_final_al'))
sys.argv=['fin_al.py','table']
import fin_al as F
assert F.dev=='cuda:0'
T=json.load(open(R/'stages/spin1/THERMAL_SPIN1.json'))['cases'];rows=[];start=time.perf_counter()
for nm in ('August',):
 for key in ('T2_rec_nominal_MPG40_plus_recharge','T1_MPG40_peak'):
  z=T[nm][key];t=time.perf_counter();a=json.load(open(R/'CONFIG_V3.json')).get('august_radiator',{}) if nm=='August' else {};delta=z.get('radiator_film',{}).get('delta_K',0.);res=F.cell(167.,2700.,None,a.get('half_length_m',.026),a.get('thickness_m',.000225),(z['coolant_supply_K']-delta,z['coolant_radiator_inlet_K']-delta,z['effective_emissivity'],z['effective_radiation_sink_K']),nx=320,ny=8)
  wp.synchronize();rows.append(dict(case=nm,state=key,wall_seconds=time.perf_counter()-t,**res))
out=dict(tool='NVIDIA Warp',version=wp.__version__,device=str(wp.get_device(F.dev)),precision='fp64',grid=[320,8],fin_geometry_changed=True,rows=rows,wall_seconds=time.perf_counter()-start,configuration_sha256=hashlib.sha256((R/'final/GTC_FINAL_CANDIDATE.json').read_bytes()).hexdigest(),note='Selected August geometry and wall-temperature states re-solved with native fp64 Warp; explicit film drop removed from fluid temperatures before finite-volume fin solve. Only adopted August states are benchmarked here. Independent selected 585-point table also regenerated. Not qualification.')
json.dump(out,open('GB10_FIN_STATES_V3.json','w'),indent=2);print(json.dumps(out))
