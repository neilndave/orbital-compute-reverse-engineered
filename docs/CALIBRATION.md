# Calibration: calibrate a 'SpaceX-like' design to 70/75 kW/t and 46/30 per Starship - Nov 3 2026 4:49 PM PT / Nov 4 8:49 AM Taipei

> Public copy of the working plan, lightly edited for publication. "The repo" / "repo baseline" in this text means the sibling project *Same Rack, Earth vs. Orbit*, whose packer, panel FEA model and Newton chain are reused here (see `vendor/`). Scripts: `replica/t423g.py`, `replica/make_fig_t423g.py`; data `replica/results/t423g.json`; figure `results/figures/fig_t423g_calibrated.png`. Task tags (t434, t436, ...) are internal pass ids that match `replica/process_log/*.jsonl`. Labels: STATEMENT = from a public source; ESTIMATE = our calculation; INFERENCE = reasoned; ASSUMED = our input.

Public sources only. Labels: ESTIMATE unless noted. Script t423g.py, make_fig_t423g.py; data results/t423g.json; figure figures/fig_t423g_calibrated.png.
Method: first-principles stack (t423e) + explicit margin/redundancy knobs; "all-in" mass = loop mass + MMOD bumper + 62 kg adapter + growth margin (repo add-back layer). One free knob (rack kg/kW) is solved so all-in mass = min(budget, 98 t / 46 or 30) -> 2,130 kg (70.4 kW/t, 46 sats) Jun; 3,267 kg (76.5 kW/t, 30 sats) Aug. FCC 4 t / 200 m2 / 1,500 m2 all pass. Orbit 600 km LTAN 6 selected by the loop.
## Candidates (Jun | Aug)
| | C1 margin-forward | C2 compute-limited |
|---|---|---|
| Knobs | blanket 0.60 kg/m2, structure 8%, PCDU 3.0 kW/kg (dual-string), 2 spare pumps, 5% spare compute, growth 20.5% (repo policy), bumper + adapter | FP base blanket 0.25, structure 6%, PCDU 5.6, 1 spare pump, no spare compute, growth 10%, bumper + adapter |
| **Implied wing W/kg** | 332 | 523 |
| **Implied rack kg/kW** | **2.72 | 2.56** (HPE 7.8; t423d 3.8; FP 1.39) | **5.35 | 5.09** |
| Mass breakdown Jun, kg | rack 429, array 484, radiator 168 + coolant 99, PE 81 + harness 17, structure+deploy 107, prop/ADCS 132, avionics 68, bumper 138 + adapter 62, growth 345 | rack 802, array 308, radiator 168 + coolant 87, PE 58 + harness 17, structure 103, prop/ADCS 135, avionics 68, bumper 138 + adapter 62, growth 184 |
| Mass breakdown Aug, kg | rack 672, array 808, rad 281 + cool 163, PE 115 + harn 29, struct 153, prop 153, avion 68, bumper 230 + adapter 62, growth 535 (total 3,267) | rack 1,273, array 514, rad 281 + cool 144, PE 76 + harn 29, struct 149, prop 158, avion 68, bumper 230 + adapter 62, growth 286 |
| Core mass (no add-backs), Jun/Aug | 1,585 / 2,440 kg (core 94.6 / 102.5 kW/t) | 1,746 / 2,690 kg (85.9 / 92.9) |
Sats per Starship 46 / 30 at 98 t (46 / 30 at 100 t). Which is more plausible is not determinable from public data (INFERENCE): C1 needs a rack ~2.7x lighter than HPE and a ~330 W/kg wing; C2 needs a 523 W/kg wing and a 1.5x lighter rack.
## Which knobs explain 70/75 (everything else first-principles, full add-backs 20.5% + bumper + adapter)
- Rack alone: **4.36 (Jun) / 4.17 (Aug) kg/kW** (1.8x lighter than HPE).
- Blanket alone: n = 1.15 / 1.09 kg/m2 -> wing ~212 / ~215 W/kg (wing barely above the t423d 200/212 threshold; flown ROSA n = 1.9).
- Growth margin alone: would need 69% (implausible). Structure or PCDU alone: cannot reach it within any plausible range (PCDU 5.6 -> 1.0 kW/kg moves all-in kW/t only 71.4 -> 66.3 at C1).
- On a CORE basis (no add-backs) with all first-principles, the rack break-even is 7.8 kg/kW = the HPE rack (t423e).
INFERENCE: SpaceX's 70/75 is best explained by a rack in the 2.5-5 kg/kW range plus ~200-500 W/kg wing and ~10-20% margin; no single lever is enough. The iso-curve (figure B): rack 0.86-3.8 kg/kW for wing 205-523 W/kg at C1 margins (Jun; Aug similar -0.15).
## Sensitivity around C1 (all-in kW/t, Jun | Aug; range)
rack 1.4 -> 7.8 kg/kW: 80.9 -> 47.0 | 87.4 -> 49.1; blanket 0.25 -> 1.2: 78.8 -> 59.6 | 86.6 -> 63.9; growth 0 -> 30%: 84.0 -> 65.5 | 91.5 -> 71.1; PCDU 5.6 -> 1.0 kW/kg: 71.4 -> 66.3 | 77.7 -> 71.7; spare compute 0 -> 15%: 71.2 -> 68.8; structure 6 -> 10%: 71.1 -> 69.7; pump spares 1 -> 3: 70.9 -> 69.9; array degradation 0.15 -> 3%/yr: 70.9 -> 69.1. Ranking: rack > growth margin > blanket > PCDU > the rest.
## Volume re-check (do 46/30 fit?)  STATEMENT: Starship payload volume ~1,100 m3, 8 m dynamic envelope, 18 m high (Starship Users Guide / eoportal); third-party bay figures 614-684 m3 (repo, not STATEMENT). Analog: Starlink V3 ~2,000 kg, 7 x 3.5 m folded (press, Flight 14 coverage; thickness unknown), up to 60 per launch planned (press claim).
Model (ESTIMATE): rack 1.65 m3 per 188 kW (HPE rack 0.6 x 1.2 x 2.296 m, scaled by power) + array stowed 0.003/0.006/0.012 m3 per m2 (loose/central/tight) + radiator 0.008/0.012/0.020 m3 per planform m2 + remaining mass at 591 kg/m3 (repo item boxes).
Sat volume Jun C1 5.3 / 7.1 / 10.8 m3; Aug C1 8.4 / 11.5 / 17.6 m3 (C2 ~5% less). Required bay packing fraction to fit 46 / 30 in 1,100 m3: Jun 0.22 / 0.30 / 0.45; Aug 0.23 / 0.31 / 0.48 (loose / central / tight). In the 614 m3 third-party bay: central 0.53 / 0.56, tight 0.81 / 0.86. Equivalent to a flat satellite 0.29-0.44 m (Jun) and 0.47-0.72 m (Aug) thick on a V3-size 7 x 3.5 m footprint vs available 0.98 m (Jun) and 1.5 m (Aug) per slot at 100% packing.
Verdict (INFERENCE): by volume 46/30 fit in the 1,100 m3 bay at >= 50% packing even with poor stowage; they fail at 35% packing with tight stowage (Jun 35, Aug 21 fit) and do not fit a 614 m3 bay unless stowage is central-or-better. Mass binds first in the central case; volume is a secondary risk, not a CAD repack.
