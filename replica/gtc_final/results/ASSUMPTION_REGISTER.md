# Assumption register

| Item | Label | Value | Used in | Source |
|---|---|---|---|---|
| AI1 June/August 150/250 kW peak, 46/30 per Starship, ~2,130/3,270 kg | SOURCED | STATEMENT | targets, counts | https://www.spacex.com/spacexai/starmind |
| Nominal load 120/175 kW per spacecraft | ENGINEERING ASSUMPTION | 0.8/0.7 x peak | thermal nominal, battery | - |
| Launch payload budget 100 t incl. 2 t dispenser; 0 % minimum weight reserve; all unused mass listed as RESERVE | ENGINEERING ASSUMPTION (owner decision t602/t603) | 100000 / 2000 kg | launch mass, reserve | - (v2 Al baseline: reserve 166.9/209.3 kg per spacecraft, 7.68/6.28 t per launch (June/August)) |
| Orbit 600 km dawn-dusk SSO, LTAN 06:00; eclipse grid from skyfield DE421 | ENGINEERING ASSUMPTION (orbit); computed eclipse | max 21.17 min, 1391 orbits/yr | battery, freeze, downtime | - |
| Inclination 97.57 deg in model_t549 env (600-km SSO is ~97.79 deg) | FLAG (minor inconsistency) | 97.57 | model_t549 env only; eclipse uses own grid | - |
| 21.66-min / 17.41-min eclipse (550-km t590 values) | SENSITIVITY ONLY | 7.36/7.26 min restart | envelope | - |
| Cold-plate resistance 14.22 K/kW (from t583 Q378g1, DTL 8 K) | ENGINEERING ASSUMPTION (not vendor-sourced) | 14.22 K/kW | GPU temperature | - |
| GPU plate load 1.7 kW per GPU at nominal-load fraction | ENGINEERING ASSUMPTION | 1.7 x load | GPU temperature | - |
| HBM rise 18 K x load over supply+10 K | ENGINEERING ASSUMPTION (ASSUMED) | 18 K | HBM temperature | - |
| Rack coolant rise 20 K | ENGINEERING ASSUMPTION (design choice) | 20 K | mass flow, rack rise | - |
| PMAD/conversion efficiency 0.92 and 2 kW bus overhead | ENGINEERING ASSUMPTION | 0.92, 2000 W | rejected heat | - |
| Radiator fin performance table AL6061_L26_t0p225 (Al 6061-T6, 26 mm half-length, 0.225 mm, 60 mm pitch, no bondline; coating unchanged, 0.91 emissivity) | COMPUTED (NVIDIA Warp fp64, GB10, v2) on assumed optics; k=167 W/mK, rho=2700 kg/m3 (ASM/MatWeb AA typical) | table | all temperatures | - (replaces K13D F3_L40_t0p5 (owner decision t618/t619)) |
| Effective-area factor 1.0 (monolithic Al fin, no bondline); K13D 0.9913 factor dropped | ENGINEERING ASSUMPTION (owner decision t619) | 1.0 | thermal | - (MC margin 0.44 K inherited from t549 K13D MC; not re-run for Al (ESTIMATE)) |
| MPG40 properties (liquidus 252.05 K) | SOURCED | CoolProp INCOMP::MPG[0.4] | coolant, freeze | http://www.coolprop.org/fluid_properties/Incompressibles.html |
| Dow recommended max ~393 K for PG fluids | SOURCED | 393 K | OPEN item (peak inlet 404 K) | https://doccenter.dow.com/content/dam/internal/documents/180/180-01592-05-dowfrost-technical-data-sheet.pdf |
| Saft VES16 8s4p pack, LEO cycle life | SOURCED | cell/pack data | battery mass | https://www.satnow.com/products/batteries/saft/98-1277-ves16-8s4p-battery (also https://www.nasa.gov/wp-content/uploads/2024/01/saft-ves16-cell-life-test-performance-update.pdf) |
| Battery DoD 30 %, round-trip eta 0.93, 30-min peak window per orbit | ENGINEERING ASSUMPTION | 0.30, 0.93, 30 min | battery | - |
| Solar cells Spectrolab XTJ Prime / AZUR 4G32 BOL & EOL retention | SOURCED | datasheets | power, EOL deficit | https://www.spectrolab.com/photovoltaics/XTJ-Prime_Data_Sheet%20_07.27.22.pdf (https://www.azurspace.com/media/uploads/file_links/file/bdb_00010895-02-00_4g32-advanced_4x8.pdf) |
| Fin-root heater line power 40 W/m (60 W/m sensitivity); heater power from array at sunrise | ENGINEERING ASSUMPTION | 40 W/m | restart time, downtime | - |
| Restart window counted as downtime each eclipsed orbit | ENGINEERING ASSUMPTION (conservative) | t_open x 1391/yr | downtime | - |
| Whipple BLE (Christiansen NNO) | SOURCED | equations | trunk shields | https://ntrs.nasa.gov/citations/20030068423 (http://hdl.handle.net/2060/19920010826) |
| MMOD flux NASA90 debris + Gruen meteoroid, flux x3 | ENGINEERING ASSUMPTION (dated model) -> OPEN: rerun with ORDEM/MASTER | x3 | MMOD | https://www.spenvis.eu/help/background/metdeb/metdeb.html |
| Radiator header MMOD protection | OPEN ITEM | 193/495 kg for N<=1 | not in mass | - |
| Panel-spare coverage | OPEN ITEM | within 80/140 kg allocation | mass allocation | - |
| Deployment/capture/release/interlock hardware | OPEN ITEM (allocation) | 70/120 kg | mass | - |
| Life/hardening/compute provision | OPEN ITEM (allocation) | 50/80 kg | mass | - |
| Sustained / EOL peak power | OPEN ITEM | EOL deficit 14.5/22.7 kW | not covered by battery | - |
| Launcher same-orbit performance, packing/CG, qualification | OPEN ITEM | - | - | - |
| Mass lines rack/array/radiator/structure/etc. (t494/t523 C1 points) | INHERITED ESTIMATE (replica calibration) | ledger | mass | - |
| Radiator mass line scaled x1.16037 (Al 6061 fin areal mass / K13D fin) | COMPUTED (fin_v2 FIN_MASS_REL) | 141.89/236.45 kg | mass | - (same footprint) |
| 6061 braze process for the integral/brazed fin-tube panel (narrow braze window; post-braze re-age) not designed | OPEN RISK | - | risk register | - (fin-root joint assumed ideal in the Warp table) |
| +13 % tube length per m2 (60 vs 68 mm pitch) raises tube MMOD exposure; not re-screened | OPEN RISK | +13 % | risk register | - (geometric ratio; shielding not re-designed) |
| Freeze heater strips and harness scaled per tube x1.5 (6 tubes/panel vs 4) | ENGINEERING ASSUMPTION | x1.5 | freeze mass, restart | - (June freeze hardware 65.7 kg is within 66 kg allocation (owner decision t627u; August 85.5/90 kg unchanged). Allocation/compliance only; actual mass and reserve unchanged.) |
