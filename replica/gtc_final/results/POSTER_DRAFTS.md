# Poster drafts (from GTC_FINAL_CANDIDATE.json sha256 a57a4a1e2f3631481f2b3f494d0f36daad1d55935e57db9523884c6c54f848c1)

## Poster numbers table

| Quantity | Unit | June J8_C1 | August A4_C1 |
|---|---|---|---|
| Spacecraft per launch |  | 46 | 30 |
| Installed peak compute per spacecraft | kW | 150 | 250 |
| Installed peak compute per launch | MW | 6.9 | 7.5 |
| Nominal IT per launch | MW | 5.52 | 5.25 |
| Spacecraft mass (0 % minimum reserve) | kg | 1,963.5 | 3,057.3 |
| Specific power (peak / mass) | kW/t | 76.4 | 81.8 |
| Launch mass incl. 2 t dispenser | t | 92.32 | 93.72 |
| Reserve per spacecraft (unused mass under 100 t) | kg | 166.9 | 209.3 |
| Reserve per launch (% of 100 t) | t (%) | 7.68 (7.68 %) | 6.28 (6.28 %) |
| GPU nominal / peak | K | 389.7 / 415.5 | 376.0 / 416.2 |
| HBM nominal / peak | K | 384.7 / 409.3 | 371.7 / 410.0 |
| Coolant supply (nominal) | K | 360.3 | 349.1 |
| Radiator inlet nominal / peak | K | 382.6 / 403.4 | 371.3 / 404.1 |
| Rack rise / radiator rise (nominal) | K | 20 / 22.3 | 20 / 22.2 |
| Radiator effective area / panels | m² / - | 81.6 / 77 | 136.0 / 128 |
| Radiator fin |  | Al 6061-T6, 26 mm / 0.225 mm, 60 mm pitch, no bondline | Al 6061-T6, 26 mm / 0.225 mm, 60 mm pitch, no bondline |
| Coolant |  | MPG40, liquidus 252.05 K | MPG40, liquidus 252.05 K |
| Peak battery (30 min/orbit) | kWh / kg | 9.78 / 120 | 13.33 / 164 |
| Freeze/restart hardware vs allocation | kg | 65.7 / 60 | 85.5 / 90 |
| Restart after eclipse (cold, 40 W/m) | min | 4.84 | 4.81 |
| Added downtime | h/yr (%) | 112 (1.28 %) | 112 (1.27 %) |
| Trunk Whipple shields | kg | 6.55 | 8.73 |
| Open-item allocations (deploy / MMOD+spares / life) | kg | 70 / 80 / 50 | 120 / 140 / 80 |

Orbit: 600 km dawn-dusk SSO; longest eclipse 21.2 min, 1391 eclipsed orbits/yr, 393 h/yr in shadow (compute paused, 4.48 %).
Labels: compute/count = STATEMENT targets; everything else = ESTIMATE from the pipeline; NOT vendor-qualified.

## Draft GTC takeaway

“On one NVIDIA GB10 desktop we reverse-engineered an AI1-inspired orbital-compute satellite. NVIDIA Warp solved the radiator-fin table behind every coolant and chip temperature and re-verified the final configuration in fp64 on the GB10 (max difference 1.44e-10); Warp FEA and NVIDIA Newton checked the frame and bounded fold-out dynamics; Omniverse RTX rendered the fleet release and unfold. The June/August concepts carry 6.9/7.5 MW of installed peak compute per launch at 92.3/93.7 t including a 2 t dispenser and a 30-minute peak-power battery, glycol (MPG40) coolant that tolerates partial freezing with pumps off in eclipse and restarts in about 4.8 minutes, and shielded coolant trunks, with all-aluminium (6061-T6) radiator fins, at 0 % minimum weight reserve (7.68/6.28 t listed as reserve). At 120/175 kW nominal the model predicts GPU 390/376 K and HBM 385/372 K; restarting after each eclipse costs about 1.3 % of the year. Radiator-header debris protection, glycol peak temperature (403/404 K vs a 393 K fluid rating), June freeze hardware over its 60 kg allocation, the 6061 braze process, tube debris exposure, spares, deployment hardware, sustained end-of-life peak power and launcher interfaces remain open. The QR code links to the reproducible pipeline.”
