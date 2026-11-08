"""August frozen-artifact/arithmetic verifier, optional real study replay.
Fresh runtime timings are observations, never required to match reference timings.
"""
from pathlib import Path
import json,hashlib,sys,subprocess,tempfile,shutil,os
import numpy as np
R=Path(__file__).resolve().parent;J=lambda p:json.load(open(R/p));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=J('MANIFEST.json');bad=[p for p,h in m.items() if sha(R/p)!=h];assert not bad,bad
C=J('RESULTS_CANONICAL.json');A=C['August'];req=C['requirements'];V=lambda x,k:x[k]['value'];checks=[]
def ck(name,b):checks.append(dict(check=name,passed=bool(b)));assert b,name
ck('Frozen-file manifest',not bad);sc=V(A,'sc_mass_kg');lm=V(A,'launch_mass_kg');n=V(A,'spacecraft_count');res=req['launch_budget_kg']-lm
ck('Mass ledger',abs(sum(A['ledger_kg']['value'].values())-sc)<1e-5);ck('Launch+dispenser',abs(lm-n*sc-req['dispenser_kg'])<1e-3);ck('Mass budget',lm<=req['launch_budget_kg']);ck('Reserve/sc',abs(V(A,'reserve_kg_per_sc')-res/n)<1e-4);ck('Reserve/launch',abs(V(A,'reserve_t_per_launch')-res/1000)<1e-5)
ck('Installed compute',n*V(A,'installed_peak_per_sc_kW')/1000==req['installed_peak_per_launch_MW']);ck('Nominal GPU cap',V(A,'GPU_nominal_K')<=req['nominal_GPU_cap_K']);ck('Peak inlet cap at specified BOL optics',V(A,'coolant_radiator_inlet_peak_K')<=req['radiator_inlet_peak_cap_K']);ck('Peak battery/recharge absent',A['battery']['total_kg']['value']==0 and A['array_v3']['recharge_heat_W']['value']==0);ck('Safe-mode retained',A['battery']['safe_mode_kg']==31.25)
if '--cpu-studies' in sys.argv or '--cuda-studies' in sys.argv:
 device='cuda:0' if '--cuda-studies' in sys.argv else 'cpu';label='REPLAY_GPU' if device=='cuda:0' else 'REPLAY_CPU'
 with tempfile.TemporaryDirectory(prefix='gtc_august_') as temp:
  work=Path(temp)/'tools';shutil.copytree(R/'tools',work);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
  for stage in ['sweep','mc','opt']:subprocess.run([sys.executable,'run_tools.py',stage,'--device',device,'--label',label],cwd=work,env=env,check=True)
  for stage in ['SWEEP','MC']:
   ref=np.load(work/f'{stage}_PARITY_GB10_GPU.npz')['values'];new=np.load(work/f'{stage}_PARITY_{label}.npz')['values'];ck(stage+' replay numerical parity',np.max(abs(ref-new))<1e-6)
  ref=json.load(open(work/('OPT_GB10_GPU.json' if device=='cuda:0' else 'OPT_BOX_CPU.json')));new=json.load(open(work/f'OPT_{label}.json'));ck('Tape optimum replay',abs(ref['best_relaxed']['radiator_mass_kg']-new['best_relaxed']['radiator_mass_kg'])<1e-5)
print(json.dumps(dict(passed=all(q['passed'] for q in checks),public_canonical_sha256=sha(R/'RESULTS_CANONICAL.json'),source_canonical_sha256=C['source_canonical_sha256'],checks=checks,scope='Frozen point/tools verification, not hardware qualification. Runtime timings are not hash reproducibility targets.'),indent=2))
