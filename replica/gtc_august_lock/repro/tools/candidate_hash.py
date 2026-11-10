"""r11 candidate snapshot: numeric content only (no timestamps/paths), so its SHA256 is reproducible from a clean copy."""
import os,json,hashlib
from pathlib import Path
R=Path(os.environ['R11_ROOT']).resolve();J=lambda p:json.loads((R/p).read_text());sha=lambda p:hashlib.sha256((R/p).read_bytes()).hexdigest()
F=J('native/final/GTC_FINAL_CANDIDATE.json')['fleets'][1];NC=J('native/r11_out/NATIVE_CHECKS.json');SW=J('gb10_out/r11/SWEEP_GB10_GPU.json');BX=J('work/box_r11/SWEEP_BOX_CPU.json');FC=J('work/box_frozen_control/SWEEP_BOX_CPU.json')
# The r11 poster (PDF, generator, gates) was removed from the repository after r20 became the poster. Its PDF hash and gate
# counts are part of the locked r11 snapshot, so they are read from the committed record when the r11 poster outputs are absent;
# every other field is re-derived. With the r11 poster outputs present (older checkouts) the behaviour is unchanged.
_REC=J('out/R11_CANDIDATE.json') if (R/'out/R11_CANDIDATE.json').exists() else None
G=J('out/poster/GATES_R11.json') if (R/'out/poster/GATES_R11.json').exists() else {'passed':_REC['gates']['passed'],'n_predicates':_REC['gates']['n'],'n_failed':_REC['gates']['failed']}
_PDF=sha('out/poster/GTC_POSTER_R11_CANDIDATE_DRAFT.pdf') if (R/'out/poster/GTC_POSTER_R11_CANDIDATE_DRAFT.pdf').exists() else _REC['hashes']['poster_draft_pdf']
snap=dict(revision='r11_candidate',adopted=False,
 decisions=dict(payload='one Vera Rubin NVL72: 72 GPUs + 36 CPUs; 640.38 kg allocation and 600x1200x937 mm box assumed',peak_power_acceptance_W=J('sweep/SWEEP_INPUTS.json')['peak_power_acceptance_W'],device_nominal_target_K=370,coolant_chemistry_on_poster=False),
 poster_numbers={k:v['raw'] for k,v in J('out/POSTER_NUMBERS_R11.json')['numbers'].items()},
 native=dict(sc_mass_kg=F['sc_mass_kg']['value'],reserve_t=F['reserve_t_per_launch']['value'],max_payload_BOL_kW=NC['solar']['maximum_feasible_payload_BOL_kW'],peak_pump_W=NC['states']['peak']['pump_electric_W'],nominal_pump_W=NC['states']['nominal']['pump_electric_W']),
 search=dict(hard=SW['hard_feasible_count'],design=SW['design_margin_feasible_count'],selected=SW['selected'],box_cpu_identical=(BX['hard_feasible_count'],BX['design_margin_feasible_count'],BX['selected']['index'])==(SW['hard_feasible_count'],SW['design_margin_feasible_count'],SW['selected']['index']),frozen_control=(FC['hard_feasible_count'],FC['design_margin_feasible_count'],FC['selected']['index'])),
 hashes=dict(sweep_inputs=sha('sweep/SWEEP_INPUTS.json'),kernel=sha('sweep/gpu_core.py'),numbers=sha('out/POSTER_NUMBERS_R11.json'),poster_draft_pdf=_PDF),
 gates=dict(passed=G['passed'],n=G['n_predicates'],failed=G['n_failed']))
b=(json.dumps(snap,indent=2,sort_keys=True)+'\n').encode();(R/'out/R11_CANDIDATE.json').write_bytes(b);h=hashlib.sha256(b).hexdigest();(R/'out/R11_CANDIDATE.sha256').write_text(h+'  R11_CANDIDATE.json\n');print('R11_CANDIDATE sha256',h)
