# Poster drafts (from GTC_FINAL_CANDIDATE.json sha256 b89c202f6372032f0337f4cb81888e99df3f5c7290745c26fac786c4f0a24d00)

## Poster numbers table

| Quantity | Unit | June J8_C1 | August A4_C1 |
|---|---|---|---|
| Spacecraft per launch |  | 46 | 30 |
| Installed peak compute per spacecraft | kW | 150 | 250 |
| Installed peak compute per launch | MW | 6.9 | 7.5 |
| Nominal IT per launch | MW | 5.52 | 5.25 |
| Spacecraft mass (0 % reserve) | kg | 1,937.8 | 3,024.1 |
| Specific power (peak / mass) | kW/t | 77.4 | 82.7 |
| Launch mass incl. 2 t dispenser | t | 91.14 | 92.72 |
| Headroom to 100 t | t | 8.86 | 7.28 |
| GPU nominal / peak | K | 389.8 / 415.8 | 376.1 / 416.5 |
| HBM nominal / peak | K | 384.9 / 409.6 | 371.7 / 410.3 |
| Coolant supply (nominal) | K | 360.5 | 349.1 |
| Radiator inlet nominal / peak | K | 382.8 / 403.8 | 371.3 / 404.4 |
| Rack rise / radiator rise (nominal) | K | 20 / 22.3 | 20 / 22.2 |
| Radiator effective area / panels | m² / - | 81.6 / 77 | 136.0 / 128 |
| Coolant |  | MPG40, liquidus 252.05 K | MPG40, liquidus 252.05 K |
| Peak battery (30 min/orbit) | kWh / kg | 9.78 / 120 | 13.33 / 164 |
| Freeze/restart hardware vs allocation | kg | 58.4 / 60 | 73.5 / 90 |
| Restart after eclipse (cold, 40 W/m) | min | 7.32 | 7.22 |
| Added downtime | h/yr (%) | 170 (1.94 %) | 167 (1.91 %) |
| Trunk Whipple shields | kg | 6.55 | 8.73 |
| Open-item allocations (deploy / MMOD+spares / life) | kg | 70 / 80 / 50 | 120 / 140 / 80 |

Orbit: 600 km dawn-dusk SSO; longest eclipse 21.2 min, 1391 eclipsed orbits/yr, 393 h/yr in shadow (compute paused, 4.48 %).
Labels: compute/count = STATEMENT targets; everything else = ESTIMATE from the pipeline; NOT vendor-qualified.

## Draft GTC takeaway

“On one NVIDIA GB10 desktop we reverse-engineered an AI1-inspired orbital-compute satellite. NVIDIA Warp solved the radiator-fin table behind every coolant and chip temperature and re-verified the final configuration in fp64 on the GB10 (max difference 9.16e-11); Warp FEA and NVIDIA Newton checked the frame and bounded fold-out dynamics; Omniverse RTX rendered the fleet release and unfold. The June/August concepts carry 6.9/7.5 MW of installed peak compute per launch at 91.1/92.7 t including a 2 t dispenser and a 30-minute peak-power battery, glycol (MPG40) coolant that tolerates partial freezing with pumps off in eclipse and restarts in about 7 minutes, and shielded coolant trunks, at 0 % weight reserve. At 120/175 kW nominal the model predicts GPU 390/376 K and HBM 385/372 K; restarting after each eclipse costs about 1.9 % of the year. Radiator-header debris protection, glycol peak temperature (404 K vs a 393 K fluid rating), spares, deployment hardware, sustained end-of-life peak power and launcher interfaces remain open. The QR code links to the reproducible pipeline.”
