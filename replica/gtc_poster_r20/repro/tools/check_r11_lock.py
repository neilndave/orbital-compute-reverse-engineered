"""r20 repro: check that this tree still reproduces the locked r11 August design.
The canonical r11 snapshot (out/R11_CANDIDATE.json, sha256 a3bd7328...) hashes the r11 number register and the r11 poster.
Later poster revisions only ADDED entries to out/POSTER_NUMBERS_R11.json, so the snapshot hash itself is reproduced in
../gtc_august_lock/repro (tools/candidate_hash.py). Here every re-derived design field is compared with that locked record:
decisions, native results, search counts/selection, kernel and sweep-input hashes, and every r11 poster number (raw value)."""
import os,json,hashlib
from pathlib import Path
R=Path(os.environ['R11_ROOT']).resolve();J=lambda p:json.loads((R/p).read_text());sha=lambda p:hashlib.sha256((R/p).read_bytes()).hexdigest()
LOCK='a3bd7328425085fa29ceb053c437740ccad7150112a57fbf6c34c5d15010374b'
assert sha('out/R11_CANDIDATE.json')==LOCK and (R/'out/R11_CANDIDATE.sha256').read_text().split()[0]==LOCK
REC=J('out/R11_CANDIDATE.json')
F=J('native/final/GTC_FINAL_CANDIDATE.json')['fleets'][1];NC=J('native/r11_out/NATIVE_CHECKS.json');SW=J('gb10_out/r11/SWEEP_GB10_GPU.json');BX=J('work/box_r11/SWEEP_BOX_CPU.json');FC=J('work/box_frozen_control/SWEEP_BOX_CPU.json')
now=dict(
 decisions=dict(payload='one Vera Rubin NVL72: 72 GPUs + 36 CPUs; 640.38 kg allocation and 600x1200x937 mm box assumed',peak_power_acceptance_W=J('sweep/SWEEP_INPUTS.json')['peak_power_acceptance_W'],device_nominal_target_K=370,coolant_chemistry_on_poster=False),
 native=dict(sc_mass_kg=F['sc_mass_kg']['value'],reserve_t=F['reserve_t_per_launch']['value'],max_payload_BOL_kW=NC['solar']['maximum_feasible_payload_BOL_kW'],peak_pump_W=NC['states']['peak']['pump_electric_W'],nominal_pump_W=NC['states']['nominal']['pump_electric_W']),
 search=dict(hard=SW['hard_feasible_count'],design=SW['design_margin_feasible_count'],selected=SW['selected'],box_cpu_identical=(BX['hard_feasible_count'],BX['design_margin_feasible_count'],BX['selected']['index'])==(SW['hard_feasible_count'],SW['design_margin_feasible_count'],SW['selected']['index']),frozen_control=(FC['hard_feasible_count'],FC['design_margin_feasible_count'],FC['selected']['index'])))
now=json.loads(json.dumps(now))
bad=[k for k in now if now[k]!=REC[k]]
bad+=[f'hashes.{k}' for k,p in (('kernel','sweep/gpu_core.py'),('sweep_inputs','sweep/SWEEP_INPUTS.json')) if sha(p)!=REC['hashes'][k]]
PN={k:v['raw'] for k,v in J('out/POSTER_NUMBERS_R11.json')['numbers'].items()}
# retired from the register (no longer printed); still checked against its source record
RETIRED={'scenario_pass_pct':100*J('gb10_out/r11/MC_GB10_GPU.json')['P_inlet_le_393']}
bad+=[f'poster_numbers.{k}' for k,v in REC['poster_numbers'].items() if (RETIRED[k] if k in RETIRED and k not in PN else PN.get(k))!=v]
assert not bad,('differs from the locked r11 record',bad)
print('r11 lock OK:',LOCK,'|',len(REC['poster_numbers']),'locked numbers unchanged (',len(RETIRED),'retired, checked against its source);',len(set(PN)-set(REC['poster_numbers'])),'added for later poster revisions')
