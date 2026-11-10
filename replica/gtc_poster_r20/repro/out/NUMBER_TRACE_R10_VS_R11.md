# r10 vs r11 candidate — every poster number

|Item|r10|r11|Δ%|>1%|Why|
|---|---|---|---:|---|---|
|Compute|NVL72-based, 79 GPUs|one Vera Rubin NVL72, 72 GPUs + 36 CPUs|-8.861|**YES**|Decision 4: exactly one NVL72 (primary-sourced topology)|
|Payload allocation|assumed 640 kg, lightweighted|assumed 640.38 kg allocation; 600×1200×937 mm box|0.059||Wording: explicit assumption; no lightweighting claim|
|Peak power per satellite|250 kW|250 kW peak at beginning of life|0.0||Decision 1: modeled available 249.9 kW rounds to 250; acceptance ≥249.9 kW|
|Satellites per launch|30|30|0.0|||
|Fleet installed peak|7.5 MW|7.5 MW|0.0|||
|Launch budget|100 t|100 t|0.0|||
|Satellite mass|3,022 kg|3,026 kg|0.132||MPG40 property fix: coolant loop +3.60, accumulator/freeze +0.06, propellant +0.07 kg|
|Fleet mass|90.7 t|90.8 t|0.11||30 × satellite mass|
|Dispenser|2 t|2 t|0.0|||
|Reserve|7.3 t|7.2 t|-1.37|**YES**|100 − fleet − dispenser|
|Solar array area|862 m²|862 m²|0.0||Unchanged August array (fixed)|
|Solar rating|324.55 W/m² on active cells|324.55 W/m² assumed module rating, remaining planar area|0.0||Wording only|
|Nominal sunlit power|175 kW|175 kW|0.0|||
|Annual average|164.4 kW|164.4 kW|0.0|||
|GPU temperature|366 K nominal|≈370 K nominal target (est. 371 K)|1.366|**YES**|Decision 2; 366 K was the 1.7 kW/offset model, unsupported for Rubin; estimate is a conditional sensitivity|
|HBM temperature|362 K nominal|est. 373 K, higher in edge cases; not yet qualified|3.039|**YES**|Decision 2|
|Coolant inlet peak|392 K|392 K|0.0||Bulk model; chemistry caveat omitted per decision 3|
|Radiator panels|140|140|0.0||Same selected geometry|
|Coating emissivity|0.92|0.92|0.0|||
|Rack frame mass|≈50 kg|≈50 kg (45.70 kg)|0.0||Rerun in t773 with full 640.38 kg; printed value unchanged|
|Rack frame mode|35 Hz|35 Hz (35.88 Hz)|0.0|||
|Panel first mode|128–153 Hz, ≈139 nominal|128–153 Hz, ≈139 nominal|0.0|||
|Designs screened|1.81M|1.81M|0.0|||
|Search result|"a mass-feasible trade point" (3,095 hard / 2,398 design-margin feasible)|3,048 hard / 2,347 design-margin feasible; lightest picked|-1.519|**YES**|Corrected MPG40 inputs; 249.9 kW acceptance; selected index unchanged (1037888)|
|Screen estimate (star)|(not printed) 3,020.89 kg|3024.60 kg|0.123||Reduced model, same index|
|Solver re-check (diamond)|3022.48 kg / 140 panels|3026.21 kg / 140 panels|0.123||Native pipeline|
|Scenario framing|42.08% pass fraction|(removed; sensitivity analysis instead)|||Owner decision: do not frame Monte Carlo as a pass rate|
|Scenario draws|1.05M|1.05M|0.0|||
|Sensitivity rank subset|(not printed)|65,536 draws|0.0||Spearman rank on 65,536-draw subset|
|Inlet p5–p95|(not printed)|388–400 K|||MC coolant inlet spread|
|GPU MC median|(not printed)|368.7 K|||MC GPU temperature median|
|Top ρ inlet (PMAD)|(not printed)|-0.66|||Spearman vs coolant inlet|
|Top ρ inlet (emissivity)|(not printed)|-0.62|||Spearman vs coolant inlet|
|GPU speedup|33.1×|32.9×|-0.604||Fresh median-of-3 rerun (kernel gained the explicit power check)|
|GPU warm sweep|0.213 s|0.214 s|0.469|||
|CPU warm sweep|7.04 s|7.02 s|-0.284|||
|Throughput|8.49M designs/s|8.46M designs/s|-0.353|||
|Input SHA256 prefix|619e2da5375d…|94e1b3ae978b…|||Single-source regenerated inputs|
|PhysicsNeMo held-out max |Δη||9.3e-5|9.3e-5|0.0|||
|PhysicsNeMo labels|384 / 128|384 / 128|0.0|||
|warp.Tape relaxed mass gap|0.82%|0.65%|-20.732|**YES**|Recomputed against the feasible discrete optimum (restored, new value)|
|Hinge locks|31 / 31|31 / 31|0.0|||
|Angle parity|0.0061°|0.0061°|0.0|||
|Newton / Warp versions|1.7.0 / 1.18.0|1.7.0 / 1.18.0||||
|Effort span|≈11 days|≈11 days|0.0|||
|GB10 job time|≥44.1 h|≥44.1 h|0.0|||
|Release gates|2 passed release gates|(removed)|||Claim dropped|
