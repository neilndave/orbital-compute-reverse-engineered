"""r11 candidate snapshot: numeric content only (no timestamps/paths), so its SHA256 is reproducible from a clean copy."""
import os,json,hashlib
from pathlib import Path
R=Path(os.environ['R11_ROOT']).resolve();J=lambda p:json.loads((R/p).read_text());sha=lambda p:hashlib.sha256((R/p).read_bytes()).hexdigest()
F=J('native/final/GTC_FINAL_CANDIDATE.json')['fleets'][1];NC=J('native/r11_out/NATIVE_CHECKS.json');SW=J('gb10_out/r11/SWEEP_GB10_GPU.json');BX=J('work/box_r11/SWEEP_BOX_CPU.json');FC=J('work/box_frozen_control/SWEEP_BOX_CPU.json');G=J('out/poster/GATES_R11.json')
snap=dict(revision='r11_candidate',adopted=False,
 decisions=dict(payload='one Vera Rubin NVL72: 72 GPUs + 36 CPUs; 640.38 kg allocation and 600x1200x937 mm box assumed',peak_power_acceptance_W=J('sweep/SWEEP_INPUTS.json')['peak_power_acceptance_W'],device_nominal_target_K=370,coolant_chemistry_on_poster=False),
 poster_numbers={k:v['raw'] for k,v in J('out/POSTER_NUMBERS_R11.json')['numbers'].items()},
 native=dict(sc_mass_kg=F['sc_mass_kg']['value'],reserve_t=F['reserve_t_per_launch']['value'],max_payload_BOL_kW=NC['solar']['maximum_feasible_payload_BOL_kW'],peak_pump_W=NC['states']['peak']['pump_electric_W'],nominal_pump_W=NC['states']['nominal']['pump_electric_W']),
 search=dict(hard=SW['hard_feasible_count'],design=SW['design_margin_feasible_count'],selected=SW['selected'],box_cpu_identical=(BX['hard_feasible_count'],BX['design_margin_feasible_count'],BX['selected']['index'])==(SW['hard_feasible_count'],SW['design_margin_feasible_count'],SW['selected']['index']),frozen_control=(FC['hard_feasible_count'],FC['design_margin_feasible_count'],FC['selected']['index'])),
 hashes=dict(sweep_inputs=sha('sweep/SWEEP_INPUTS.json'),kernel=sha('sweep/gpu_core.py'),numbers=sha('out/POSTER_NUMBERS_R11.json'),poster_draft_pdf=sha('out/poster/GTC_POSTER_R11_CANDIDATE_DRAFT.pdf')),
 gates=dict(passed=G['passed'],n=G['n_predicates'],failed=G['n_failed']))
b=(json.dumps(snap,indent=2,sort_keys=True)+'\n').encode();(R/'out/R11_CANDIDATE.json').write_bytes(b);h=hashlib.sha256(b).hexdigest();(R/'out/R11_CANDIDATE.sha256').write_text(h+'  R11_CANDIDATE.json\n');print('R11_CANDIDATE sha256',h)
