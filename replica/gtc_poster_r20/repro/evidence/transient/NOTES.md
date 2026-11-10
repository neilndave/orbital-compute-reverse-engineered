# Transient check: 30-min 250 kW peak, August design (diagnostic only, nothing adopted)

Run on the box CPU (numpy explicit time integration, dt 0.5 s), Mon Nov 9 2026 ~11:00 PM PT (Tue Nov 10 ~3:00 PM Taipei). GB10 not used.
Files: `transient_peak.py`, `TRANSIENT_PEAK.json`, `transient_peak.png`, `upper_bound.txt`, `run.log`.
Model code imported from a read-only copy (`native_copy/`) of `gtc_r17_candidate/repro/native`; sources untouched.
Re-running `thermal_spin1.py` in the copy reproduces THERMAL_SPIN1.json exactly (August T1 peak inlet 391.941 K, nominal 361.453 K).

## Method
- Same equations as `thermal_spin1.operating()` (MPG40 case): radiator flux 2·ee·σ·(T⁴−Ts⁴)·η_fin(T) from the selected AL6061_V3_AUG table,
  same effective emissivity/sink (ee 0.8827, Ts 186.1 K), 149.8 m², 0.44 K margin, Gnielinski film (h 2,379 / 4,402 W/m²K), heat in = (IT + 2 kW aux + pump)/0.92,
  flow = IT/(cp·20 K) (pumps step to the peak flow with the load), IT heat enters the racks, aux/pump/PMAD heat enters between racks and radiator.
- Loop discretised along the flow: 10 rack cells → hot trunk → 40 radiator cells (headers+panels+fins) → cold trunk (+pumps) → racks (upwind advection).
- One emission calibration factor 1.0076 so the cell-resolved steady 250 kW inlet equals 391.94 K (the steady model uses a Simpson/linear profile;
  uncalibrated the cell model was +0.7 K warm). Check: steady 175 kW then gives 361.59 K inlet (steady model 361.45 K), supply 339.41 K (339.27 K).
- Chips quasi-steady (seconds) above the local rack-mean coolant: screening GPU = mean + 1.7·load·14.22, HBM = mean + 18·load;
  Rubin estimate = device_thermal_recheck central row (1650 W package at 175 kW, HBM 20 %, R_die 0.0072, R_HBM 0.02 K/W, map factor 1) with package power and branch flow scaled with load
  (2,357 W, 1.83 L/min at 250 kW, inside the digitised map range). The recheck itself has no 250 kW row; this scaling is ours.

## Heat capacities (J/K) — brackets
Inventory from the steady model's own sizing at the 250 kW cap: fluid 321 kg (rack 74.3, trunk 6.5, headers 131.8, panels 108.6); radiator dry Al fins+tubes 180.3 kg
(ledger radiator 290.5 kg = wet, incl. panel fluid); header walls 84.3 kg; pumps/valves/piping/column modules 95.2 kg; rack 640.4 kg.
| bracket | fluid mass | Al cp | header wall | pump hw | rack fraction × cp | other | C total | τ = C/G |
|---|---|---|---|---|---|---|---|---|
| low | ×0.85 | 900 | 50 % | 0 | 25 % × 500 | – | 1.35 MJ/K | 8.5 min |
| mid | ×1.00 | 930 | 100 % | 50 % ×500 | 50 % × 650 | – | 1.73 MJ/K | 10.9 min |
| high | ×1.15 | 960 | 100 % | 100 % ×500 | 75 % × 800 | ½ power electronics | 2.15 MJ/K | 13.5 min |
G (rejected-heat change per K of supply, from the two steady points) = 2.66 kW/K. Simulated e-fold of the radiator inlet: 8.5 / 11.0 / 13.8 min.
The fluid (≈1.26 MJ/K) dominates; the 180 kg aluminium radiator is only ≈0.17 MJ/K.
NOTE: the brief's "3,026 kg radiator" is the whole spacecraft mass (sc_mass_kg 3026.2). A non-physical upper bound that puts the entire spacecraft
on the radiator node as aluminium (4.46 MJ/K, τ 27.9 min) still gives inlet 381.7 K and screening HBM 387.7 K (> 378 K from 12 min) at 30 min.

## Results (low / mid / high capacity)
| quantity | steady 175 kW | t = 0+ | end of 30 min | steady 250 kW |
|---|---|---|---|---|
| radiator inlet (max over event) | 361.6 | 361.6 | 391.4 / 390.5 / 389.2 | 391.9 |
| rack return | 359.4 | 359.4 | 389.2 / 388.2 / 386.8 | 389.9 |
| cold-plate supply | 339.4 | 339.4 | 369.2 / 368.3 / 367.0 | 369.9 |
| GPU screening | 366.3 | 373.6 | 403.4 / 402.4 / 401.1 | 404.1 |
| HBM screening | 362.0 | 367.4 | 397.2 / 396.2 / 394.9 | 397.9 |
| GPU Rubin est. | 370.9 | 379.2 | 409.0 / 408.0 / 406.7 | 409.7 |
| HBM Rubin est. | 372.7 | 381.8 | 411.6 / 410.7 / 409.3 | 412.3 |
- Steady state over-predicts the 30-min peak by only 0.5–2.8 K (mid 1.7 K) — 30 min is ≈2.7 time constants.
- GPU > 370 K: immediately (both models) — the chip offset follows the power step within seconds (+7.3 K screening, +8.3 K Rubin est.).
- HBM > 378 K: screening after 3.7 / 4.7 / 5.8 min; Rubin estimate immediately (381.8 K at t = 0+).
- Radiator inlet within 1 K of the steady 391.9 K after 27 / 35 / 44 min of peak (within 0.5 K: 33 / 42 / 52 min). So a peak longer than ~30–45 min is effectively steady.
- After the peak, back within 1 K of the nominal inlet in 33 / 42 / 51 min.
- To keep screening HBM ≤ 378 K for a full 30 min, τ would need to be ≈70 min (C ≈ 11 MJ/K, ≈6.5× mid). No capacity keeps screening GPU ≤ 370 K at 250 kW: the 7.3 K instant chip offset alone puts it at 373.6 K.

## Limits of this check
Lumped/1-D only; no pump or valve control dynamics (flow assumed to step with load), constant cp for storage, no MMOD bumper coupling,
no orbital sink variation over the 30 min, chip models are the existing screening and conditional Rubin estimates (not qualified junction temperatures).
