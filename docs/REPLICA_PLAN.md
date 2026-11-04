# Replica plan and engineering log: the C1-to-C2 "SpaceX-like region"

> Public copy of the working plan, lightly edited for publication. "The repo" / "repo baseline" in this text means the sibling project *Same Rack, Earth vs. Orbit*, whose packer, panel FEA model and Newton chain are reused here (see `vendor/`). Paths are relative to `replica/`. Task tags (t434, t436, ...) are internal pass ids that match `replica/process_log/*.jsonl`. Labels: STATEMENT = from a public source; ESTIMATE = our calculation; INFERENCE = reasoned; ASSUMED = our input.


Written Tue Nov 3 2026 ~5:30 PM PT (= Wed Nov 4 9:30 AM Taipei). Taipei = PT + 16 h. Deadline Tue Nov 10 5 PM PT (= Wed Nov 11 9 AM Taipei). Content freeze Sun Nov 8 (PT).
Labels: STATEMENT = from a source; ESTIMATE = computed by us from stated inputs; INFERENCE = reasoned; ASSUMED = our choice. Task id t434;. Updated Tue Nov 3 2026 ~6 PM PT (= Wed Nov 4 ~10 AM Taipei) for the packing loop; backup `GTC_REPLICA_PLAN.md.bak_t436`).

## 1. The story and the points
The replica is two satellite designs that both reproduce SpaceX's stated 70 kW/t (Jun, 150 kW, 2,130 kg, 46 per Starship) and 75 kW/t (Aug, 250 kW, 3,270 kg, 30 per Starship) inside the FCC limits (4 t, 200 m2 radiator, 1,500 m2 array) (STATEMENT inputs; solve by t423g, ESTIMATE).
- C1 margin-forward: wing 332 W/kg, rack about 2.6-2.7 kg/kW, 20.5% growth.  C2 compute-limited: wing 523 W/kg, rack about 5.1-5.4 kg/kW, 10% growth.  MID is the point halfway along the line (ESTIMATE).
- Six points = {C1, MID, C2} x {Jun, Aug}. Files: `gtc_params/point_<J8|A4>_<C1|MID|C2>.json`. Figure: `figures/fig_t434_spacex_region.png`.

| point | mass kg | rack kg | array kg | wing W/kg | rack kg/kW | radiator face m2 | array m2 | panels (A6L) |
|---|---|---|---|---|---|---|---|---|
| J8_C1 | 2,130 | 408.5 | 484.5 | 332 | 2.72 | 81.63 | 503.9 | 77 |
| J8_MID | 2,130 | 593.4 | 396.4 | mid | mid | 81.63 | 503.9 | 77 |
| J8_C2 | 2,130 | 802.2 | 308.2 | 523 | 5.35 | 81.63 | 503.9 | 77 |
| A4_C1 | 3,267 | 640.4 | 807.6 | 332 | 2.56 | 136.05 | 839.8 | 128 |
| A4_MID | 3,267 | 937.8 | 660.6 | mid | mid | 136.05 | 839.8 | 128 |
| A4_C2 | 3,267 | 1,272.8 | 513.6 | 523 | 5.09 | 136.05 | 839.8 | 128 |
(All ESTIMATE; exact rack kg/kW and wing W/kg per point are in the JSONs.)

**Key efficiency fact (INFERENCE from the model, checked in the files).** Along C1 to C2 at fixed build, power, total mass, radiator area, array area, orbit and panel count do not change. Only the split of mass between rack and array changes. So thermal, area sizing, CAD envelope, packing, and the render geometry are **2 cases (one per build)**, not 6. Only mass-dependent checks (Newton deployment inertia, mass tables, reliability weights) see all 6.

## 2. Inventory: what was run for the adopted 254-panel baseline -> replica equivalent
Baseline numbers (STATEMENT from repo): 254 panels, 7,023 kg, 188 kW, 13 per Starship, 550 km LTAN 6.

| # | Tool (NVIDIA?) | Baseline run (source) | Replica equivalent | Where | Runtime estimate (basis) | Needs | Priority |
|---|---|---|---|---|---|---|---|
| 1 | Region figure | t423g calibration | C1-C2 band, HPE 7.8, ROSA 71-124, baseline marked | box | done | - | DONE |
| 2 | Param sets | - | 6 JSONs + overlays (`gen_params_t434.py`) | box | seconds | t423g | DONE |
| 3 | Warp radiator fin + thermal MC (NVIDIA Warp) | t422 GB10 full run, 650 s (4 builds; `gb10_run_t410/`) | 2 builds (Jun, Aug), loop-sized areas 81.63 / 136.05 m2 (baseline run used SpaceX-stated 110 / 178.6 m2), phases G0,G2,G3,G4; fin tables cached | GB10 (`./run.sh thermal`) | 10-15 min (ESTIMATE: half the builds of a 650 s run). Box CPU tiny smoke passed | none | MUST |
| 4 | Newton 1.7.0 hinge deployment (NVIDIA Newton + Warp ref) | t410 case: motor 300 s, dt 1 ms, 21 hinges (t410 actual wall not recorded; predicted ~44 min; 2,077 s for 300 s at dt 2 ms measured earlier, RUNTIME_LOG 2026-10-31) | same case on overlay inputs with replica array mass / area / wing length; C1 and C2 x 2 builds = 4; MID x 2 optional | GB10 (`./run.sh newton_must`, `newton`) | 44-76 min per case (8 ms/step unshared to ~14 ms/step; up to ~105 min if the GPU is shared at 19 ms/step; RUNTIME_LOG). 4 cases 3-5 h; 6 cases 4.5-8 h | venv_newton, free GPU | MUST (4), nice (MID) |
| 5 | Stowed packing (repo p27 + DP) | K31/stowing_architectures; baseline = 14 per Starship at step 0.25 reproduced on box (adopted 13) | 2 builds (Jun, Aug), same item model scaled; plus equipment-volume sensitivity | box CPU | ~2-3 min per build per probe (measured 26-74 s per table at step 0.25) | done for C1 | MUST: done; probe running | **Now an iterative loop: section 3a.**
| 6 | CAD STEP envelope + FCC area check (build123d) | cad3d_full_T45 | idealised deployed envelope per build (`replica_geom.py`), measured array and radiator areas, FCC flags | box | <1 s per point | done | MUST: done for J8_C1, A4_C1 (shared geometry) |
| 7 | Fleet kinematics + hero render, Omniverse RTX / Isaac Sim 6.0 (NVIDIA) | hero2: 1,169 frames, ~6 h 44 min on GB10 (about 20.7 s per frame; STATEMENT from repo notes) | one replica fleet render per build, same camera path; geometry shared by C1/MID/C2 (the render cannot show the rack/array mass split) | scene adapter on box, render on GB10 | ~6-7 h per build IF frame count and scene complexity equal hero2 (ESTIMATE; Jun fleet has fewer panels, Aug similar). ~13 h for both | **needs a replica scene/layout adapter (fleet_kin, layout JSON, mesh export) not written yet: ~1 working day** | NICE-TO-HAVE, but strong visual for the poster. Option: 1 build only (Jun) | **GATED on the packing loop (section 3a): render starts only after packing has converged and the author has accepted the lever assumptions.**
| 8 | PhysicsNeMo thermal surrogate (NVIDIA) | spike: 11,000 Warp solves 1,522 s + MLP 105-113 s | retrain on replica fin grid | GB10 | ~30 min | spike data | NICE (not needed for the story) |
| 9 | Monte Carlo reliability (Warp) | P9 reliability set | rerun with replica panel counts (77 / 128) and masses | GB10/box | ~20-60 min (ESTIMATE; no blind estimate on record for P9) | adapter | NICE |
| 10 | Collision / clearance checker | fleet_*_clearance | not applicable until render adapter exists | box | - | #7 | NICE |
| 11 | CalculiX modal (not NVIDIA) | calculix_xcheck | skip | - | - | - | SKIP |

## 3. Must-have vs nice-to-have
MUST: 1, 2, 3, 4 (C1 and C2, both builds), 5, 6. These support the poster sentence "the SpaceX-region design fits the same checks as ours" with replica numbers.
NICE: Newton MID points, one render per build, reliability MC, PhysicsNeMo.
Decision for the author on the render (numbered; all GATED on packing, section 3a): 1) Jun build only (about 7 h GPU + 1 day adapter work), 2) both builds (about 13 h GPU), 3) skip render and show the STEP-envelope image only. Recommendation: 1, extend to 2 if the Jun render lands by Fri Nov 6 PT.
Fallbacks if packing runs long or the author does not accept the lever assumptions (decide by Thu Nov 5 5 PM PT = Fri Nov 6 9 AM Taipei, the latest Jun launch that still finishes by the last compute deadline): a) Jun only (about 7 h); b) render the deployed fleet but label the stowed count honestly (the deployed render does not depend on the stow lever set, INFERENCE); c) reduced-frame render (about 1/3 of hero2's 1,169 frames, ~2.3 h, ESTIMATE from 20.7 s/frame); d) skip render, poster shows the STEP envelope and the stowed-stack image (`figures/fig_t436_stowed_stack.png`).

## 3a. Packing loop (task t436; GATE for the render)
**Why.** The repo packer gives 17 (Jun) / 12 (Aug) satellites per Starship against the mass-limited 46 / 30 (98 t / 2.13 t, 98 t / 3.267 t). the author: solve it iteratively; render waits for it.
**How.** `box_gtc/t436_loop.py` drives the repo packer (p27 skyline + layer DP; read-only) with changed stowing inputs, one pass at a time. Every pass is logged in `process_log/t436.jsonl` (variables, result, binding limit, what changed and why, rejected ideas, sources) and in `box_gtc/results/t436/passes.jsonl`. Held fixed: mass <= 98 t, FCC limits, C1/MID/C2 masses, bay envelope.
**Bay envelope.** STATEMENT (2020 Starship Users Guide Rev 1.0): 9 m fairing, 8 m dynamic-envelope cylinder, ogive to 17.24 m; the repo integrates ~678 m3 allowed volume (ESTIMATE). Third-party only, NOT used: ~1,100 m3 (eoportal), 614 m3 (Wikipedia); the extended 22 m height has no published profile (the repo rejected it).
**Passes so far (layers architecture, Jun / Aug per Starship, ESTIMATE):**
| pass | change (cumulative) | Jun / Aug | binding limit |
|---|---|---|---|
| 0 | replica as-is, step 0.25 | 17 / 12 | volume (one satellite per ~0.93 m level) |
| 1 | single levers alone (bus shrink, ROSA-class roll, stack1, radiator pitch alone) | all <= 23 / 16 | volume; rejected, see below |
| 2 | array leaf pitch 9 -> 4 mm | 23 / 16 | volume |
| 5 | + radiator pitch 20 -> 10 mm | 27 / 17 | volume |
| 3 | + rack boxed separately at the repo rack density, equipment at 800 kg/m3, adapter 0.15 m | 40 / 27 | volume |
| 3 | + adapter 0.10 m, gap 0.03 | 43 / 28 | volume |
| 2/3 | + adapter 0.05 m, gap 0.02 | **46 / 30** | **mass (98 t)**: the true ceiling |
Ablation (pass 3): remove any one of the four levers from the 46/30 set and Jun falls to 33-43, Aug to 22-28. Alternative routes (pass 4): adapter 0.10 m with leaf 3 mm + radiator pitch 7 mm gives 46 / 31; adapter 0.15 m with leaf 2 mm + pitch 5 mm gives 45 / 33 (books 50 / 35). The books architecture is +1 to +4 over layers.
**Rejected:** ROSA-class roll (no denser than the 9 mm Z-fold, 11 / 9); bus-only shrink (saturates 22 / 16); one satellite per level "stack1" (<= 20 / 19: per-level overhead x 46 exceeds 17.24 m); radiator pitch alone (dead end, also in the repo).
**Physics checks (ESTIMATE / INFERENCE).** Newton chain is a rigid planar Z-fold with no leaf-pitch term, so stow pitch does not change its inputs (the result holds only if thin leaves behave like the rigid ones; flexible blankets are not modelled). Thermal uses areas, which are unchanged; the 800 kg/m3 bay density has no thermal re-run. NOT sized: launch loads and the load path of a 0.05-0.15 m adapter (the replica carries 62 kg adapter mass per satellite), hold-down and clearance at 3-5 mm pitch, dispenser frame for a stack of up to 98 t. Third-party hint only: Starlink V3 flat-pack stacks of up to ~60 (Ars Technica, Tesla Oracle).
**Assumptions the author must accept (they are "what-ifs"):** leaf pitch <= 4 mm (repo 9 mm), radiator pitch <= 10 mm (repo 20 mm), rack+equipment packed at 800 kg/m3 as separate boxes, adapter <= 0.05-0.10 m. Aug at 30 has zero slack against the mass bound.
**Open:** step-0.1 refinement of the 46/30 combo (running on the box, ~10 min per job); plan item `gb10_gtc_v2/` is probably NOT needed since Newton and thermal inputs do not change. Figures: `figures/fig_t436_sats_vs_pass.png`, `figures/fig_t436_stowed_stack.png`.
**Gate.** Render (row 7) starts only after (i) the step-0.1 check agrees (>= 46 / 30, or the shortfall is stated), and (ii) the author accepts the lever set or picks an alternative route.

## 3b. Credibility check of the four stow assumptions (task t436b; log `process_log/t436b.jsonl`; script `box_gtc/t436b_checks.py`; figure `figures/fig_t436b_credibility.png`)
Labels: STATEMENT = public document; ESTIMATE = our calculation; INFERENCE = reasoned from third-party numbers; ASSUMED = our input. Vendor claims are third-party.
1. **Leaf pitch.** A rigid 2-4 mm sandwich leaf fails: 1.19-1.29 kg/m2 against the replica array 0.962 (C1) / 0.612 (C2), and it is ~500-3000x softer than the Newton latch (K 5e5 N m/rad); matching the latch would need a ~78 mm core (ESTIMATE). The credible form is a flexible Z-fold blanket. Public precedent as pitch equivalents: ROSA flown 40 kW/m3 = 7.4 mm (STATEMENT); Mega-ROSA >50 kW/m3 = 6.0 mm (claim); SOLAROSA 60-80 = 3.7-5.0 mm (claim/target). Replica C1 array: 4 mm = 74 kW/m3, 5 mm = 59.5, 6 mm = 49.6, 7.5 mm = 39.7 (ESTIMATE). Verdict: 6 mm credible (matches the Mega-ROSA claim), 5 mm at the edge of claims, 4 mm beyond them, 2-3 mm rejected. Stack pressure at fold 6 is ~7 kPa at 6 g (ESTIMATE). Newton stays a rigid-leaf mass/inertia proxy for slow deployment; blanket dynamics are not modelled (poster caveat).
2. **Radiator pitch.** Tube OD 5.68 mm (repo rule 2W/128 on the 0.363 m panel; the repo's F4 case gives 6.28 mm, STATEMENT). 10 mm pitch leaves 4.3 mm for headers: needs flat headers (34 x 7 mm), sag 1.4 mm at 6 g (2.9 at x2). 8 mm is marginal; 5-7 mm fails. Verdict: 10 mm credible with flat headers (not yet checked by repo FEA); routes that need 5-7 mm are rejected.
3. **Equipment density.** Public: GB200 NVL72 rack 949 kg/m3, HPE variant 921, DGX H100 847 (STATEMENT from vendor dimensions); Starlink V2 Mini-class ~289 (INFERENCE, third-party dims). Replica hardware is ~406 kg/m3 real or 827 if the margin is boxed too. 800 is a stretch, 600 comfortable. Rack at the public 949 costs ~2 satellites versus the repo rack shape.
4. **Adapter and load path.** Loads: Starship Users Guide Rev 1.0 axial up to +6 g, lateral +-2 g; Falcon guide 6 g, 25/10 Hz, x1.25 qualification (STATEMENT). 3 columns of 4 posts per level, tension rod, pins: base post ~26 cm2 each, 2.5 MN per column, stack shortening ~34 mm at 6 g for 46 satellites. Added mass ~19.8 kg/sat (Jun), 18.9 (Aug) = 912 / 566 kg (ESTIMATE). Fits in a 0.05 m adapter. If not absorbed the mass ceiling is 45 / 29; the margin lines absorb it (5.7% / 3.5%). At a volume count of 42 (Jun) there is 203 kg/sat of slack so no margin is needed. Lateral sway (~26 mm) and dispenser access are unverified.
**Replacement lever: array fold n (second-stage pleat across the 14 m width).** Fold 6 lifts every credible-leaf config by ~5-10 satellites. Not modelled in Newton.
**Counts per Starship (volume-limited, layers / books, ESTIMATE; rho 800, rack 949, radiator pitch 10 mm; step 0.1 m):**
| config | Jun | Aug |
|---|---|---|
| stretch t436 (leaf 4, no fold, repo rack) | 49 / 50 -> 46 (mass) | 30 / 32 -> 30 (mass) |
| D: leaf 5, fold 6, adapter 0.05 | 46 / 48 -> 46 (mass) | 33 / 33 -> 30 (mass) |
| **E: leaf 6, fold 6, adapter 0.05, gap 0.02 (recommended)** | **42 / 43** | **30 / 30** |
| F: E with adapter 0.10, gap 0.03 | 40 / 42 | 29 / 29 |
| G: leaf 7.5 (flown ROSA), fold 8 | 37 / 38 | 26 / 26 |
Cylinder-only probe (ogive treated as cylinder) gives 48-53 Jun but is an upper bound, not used.
**Recommendation for the render gate:** open it for the Jun build with config E: 42 per Starship (vs 46 quoted by SpaceX, 91%); Aug 30 (29 if load-path mass is not absorbed); config D is the 46 / 30 stretch at the edge of vendor claims. Leaf-pitch baseline: the packer default was 9 mm; the repo adopted L0 baseline is 12 mm leaf / 20 mm radiator pitch. `gb10_gtc_v2/` is NOT needed (Newton/thermal inputs unchanged).

## 3c. FINAL CONFIGS, RENDER GATE, DERISK GATE (task t438; log `process_log/t438.jsonl`; code `box_gtc/t438_loop.py`, `margin_table.py`, `blanket_check.py`, `stack_modes.py`, `fea_panel_disp.py`)
the author's rule: we MUST hit SpaceX's numbers: **Jun 46 and Aug 30 per Starship**, both at the SpaceX power densities (Jun 70.41 kW/t, Aug 76.53 kW/t). Labels: STATEMENT = public document; ESTIMATE = our calculation; INFERENCE = reasoned; ASSUMED = our input; CLAIM = vendor claim.
**Corrections to 3b (read first).** (1) "No fold" in 3b/t436 meant the packer default, which is **fold 4 (repo baseline, NSEC = 4 array sections)**. (2) t436/t436b used the C2 rack (conservative); t438 uses the C1 rack (the more public-credible array, 0.962 kg/m2). (3) Second-stage fold hinge mass was not charged before; it is now: (n-4) x 40 x f x 0.4 x 1.519 kg, f = P/188 (Jun fold 5 = 19.4 kg, Aug fold 6 = 64.6 kg). (4) The 3b load path used an idealised 3-column stack (16 / 10 levels); the real packed stacks are 19 levels / 17.0 m (Jun) and 18 levels / 16.5 m (Aug), so the load path is 24.1 / 36.2 kg per satellite, not ~19. The earlier "Aug stack is stiffer" claim is **withdrawn** (both ~7 Hz axial, ~3.4 Hz lateral).
### Final configs (packer p27 skyline + DP, step 0.1 m; layers = design count, books = upside)
| | **Jun (46 per Starship)** | **Aug (30 per Starship)** |
|---|---|---|
| Point on the line | C1 (J8_C1) | C1 (A4_C1) |
| Array leaf | 6 mm | 6 mm (config E, the author's decision) |
| Second-stage fold n | 5 | 6 (fold 5 also packs 33) |
| Radiator pitch / panels | 10 mm, flat headers, 77 panels | 10 mm, flat headers, 128 panels |
| Equipment / rack density | 800 / 949 kg/m3 | 800 / 949 kg/m3 |
| Adapter / gap | 0.05 / 0.02 m | 0.05 / 0.02 m |
| **Packed count (layers / books)** | **46 / 47 (zero slack)** | **31 / 31 (30 kept, +1 slack)** |
| kW/t | 70.41 (150 kW, 2130.43 kg) | 76.53 (250 kW, 3266.67 kg) |
| Mass margin line (C1) | 345.38 kg/sat; used 43.5 kg (12.6%) | 535.05 kg/sat; used 100.8 kg (18.8%) |
| 75 kW/t (Aug) and FCC 4 t | n/a / pass | **pass: the added mass sits inside the margin line, total stays 3266.67 kg; no fix needed** |
| Credibility | **Jun is the heroic build**: fold 5 and zero slack | stack fits with slack, but fails if leaf >= 7.5 mm, rho <= 600, or pitch 20 mm |
Margin used = load path (24.1 / 36.2) + fold hinges (19.4 / 64.6) + radiator hardware and the rest (explicit table in `box_gtc/results/t438/margin_table.json`). Counts are mass-capped at 98000 / N, so there is no free mass: every added kg comes out of the margin line.
**Jun levers tried (layers):** fold 4 (repo) 45 (one short); fold 5 **46**; fold 6 44; fold 7-8 worse (the packer is non-monotone in n); leaf 5.5 mm 46; leaf 5 mm (config D) 48; radiator flat headers vs round: no gain (40); adapter 0.10 gives 43; equipment density 700 gives 43. C1 vs MID vs C2: the array area, radiator area, power and total mass are identical along the line (only the rack/array mass split moves), and the count is 46 at C1, MID and C2 -> the point does not change the array area.
### Assumption credibility and precedent (what the poster must say)
| assumption | value | label | precedent / basis |
|---|---|---|---|
| Array leaf pitch | 6 mm (Jun and Aug) | CLAIM / edge of flown | flown ROSA 40 kW/m3 = 7.4 mm (STATEMENT); Mega-ROSA >50 kW/m3 = 6.0 mm (vendor claim); SOLAROSA 60-80 = 3.7-5.0 mm (claim / target). Replica array: 49.6 kW/m3 at 6 mm, 59.5 at 5 mm (ESTIMATE). |
| Second-stage fold n | Jun 5, Aug 6 | ASSUMED, no flown precedent found for a zig-zag fold of a 14 m blanket across its width | repo baseline is n = 4; Newton check (a) is prepared; blanket strain 0.42-1.28% at 6 mm pitch vs 3% assumed yield (ASSUMED values) |
| Radiator pitch | 10 mm, flat headers | ESTIMATE | panel FEA: peak sag 0.849 mm at 6 g vs 4.32 mm clearance (CalculiX, PASS); repo panel first mode 33.1 Hz |
| Rack density | 949 kg/m3 | STATEMENT | GB200 NVL72 vendor dimensions |
| Equipment density | 800 kg/m3 | ASSUMED stretch | DGX H100 847, GB200 949 (STATEMENT); 800 is 6% below DGX H100 |
| Adapter / gap | 0.05 / 0.02 m | ASSUMED, **sensitive** | 0.10 m costs 3 satellites (Jun 46 -> 43). Load factors: Starship Users Guide +6 g axial, +-2 g lateral (STATEMENT), FS 1.25, joint factor 1.5 |
**INFERENCE: what the June -> August change implies.** SpaceX moved from 46 smaller (150 kW) satellites to 30 larger (250 kW, +67% power, +53% mass) per Starship, at about the same kW/t (70 -> 77). In our replica both builds use the same leaf, density, pitch and adapter assumptions; what differs is that **June needs the extra fold-5 stage and has zero count slack, while August packs 31 (33 at fold 5) for a target of 30**, because fewer, longer-leaf (1.5 m vs 0.9 m) satellites stack with less dead space per level. That is consistent with the August update being a more credible stowing configuration, but only through count slack: August is **not** more robust (it fails at leaf >= 7.5 mm, rho <= 600 or 20 mm pitch), it spends more margin in absolute terms (100.8 kg, 18.8% vs 43.5 kg, 12.6%), and the stack stiffness is the same (~7 / ~3.4 Hz). We state it as inference, not as evidence of SpaceX's actual design.
### Render gate (the author, Nov 4 11:47 AM Taipei): Render 1 = August only, release -> unfold, 30 sats; Render 2 = June + August single satellites unfolding side by side
Final configs are in `box_gtc/results/t438/final_configs.json`; scene parameters are in `gb10_render_replica/scene/{Jun,Aug}`. **Nothing was launched on the GB10.** The June fleet render is dropped. Gate status is in the table below: **Render 2 can go once (a) and the preview pass; Render 1 is NOT ready (fleet clearance fails, see adapter status).**
### Pre-render DERISK GATE (the author, Nov 4 11:03 AM Taipei): full render only after all four pass
| # | check | where | status |
|---|---|---|---|
| (a) | Newton fold chain for the second-stage fold (Jun n = 5, Aug n = 6; W0 scan 0.10 / 0.17 / 0.25; hinge torque -> blanket check) | GB10: `run_derisk_gb10.sh newton` (prepared, untested: no Newton on the box) | **PREPARED, not run.** Box part done: blanket strain at 6 mm pitch 0.42-1.28% vs 3% assumed yield (ESTIMATE, ASSUMED yield). Width-fold timing is the 14 s placeholder (`FLEET_TAU_W`) until the author returns the GB10 numbers. |
| (b) | CalculiX FEA, flat-header radiator panel, 10 mm pitch, 6 g axial / 2 g lateral | box CPU, done | **PASS (ESTIMATE):** 0.849 mm peak at 6 g axial, 0.522 mm at 2 g lateral, vs 4.32 mm clearance |
| (c) | Stowed-stack first mode vs public requirement | box, done (t440) | **MEETS the assumed 25 / 10 Hz only with bay-wall ties every 3 levels** (section 3d). Untied 6.9 / 3.3 Hz (Jun), 7.0 / 3.4 Hz (Aug). Falcon's 25 / 10 Hz is STATEMENT for Falcon, ASSUMPTION for Starship; ties anchor to the bay wall (ASSUMED free). |
| (d) | Low-res preview + clearance checker on the new geometry | box part done, GB10 part pending | **Render 2 (single sats): own-sat clearance PASS** (Jun stride 6, Aug stride 1, frames 340-815; thinnest +2.5 mm Aug col_wing, +1 mm colcol_adj). **Render 1 (30-sat fleet): sat-sat PASS** (zero negative gaps, min +35.5 mm, release patch ODD_SPEED 2.6) **but own-sat FAIL** (below). |
### Render scene adapter: status (Nov 4 ~12:30 Taipei)
DONE: two-box body via the pod (stowed min +6 mm Jun and Aug); counts 46 / 30, no hard-coded 14; yoke root resolved at **4.1366 m** (repo `chain_params_T45.json` LEN[0], `DERISK_PHASE2_T45.md` 4.2, because the Newton h(t) was solved with it; the replica stage-1 1.968 m was a placeholder, difference ~4 kg/sat, INFERENCE); width-fold timing keyed to `FLEET_TAU_W` (14 s placeholder) via `apply_wfold_timing.py`; release plan = scaled T_STAG / T_UST / V_Z + outward release (off-centre sats exit outward, odd layers 2.6x faster, centre sats delayed 25 s) + collision-planned staging per pack-signature class; R2 hero-fit camera (0 frames outside the safe box, both builds).
Single-satellite plans (Render 2): `scene/Jun/stage_plan_single_Jun.json`, `scene/Aug/stage_plan_single_Aug.json` (plates1 start moved 18.6 -> 16.75 s to clear a pod/plate collision of -0.148 m). Known: plates0/plates1 staged-final overlap -5 mm flagged by the planner.
**OPEN for Render 1 (the 30-sat fleet), own-sat clearance of the planned unfold fails (derisk/adapter_ownsat_fleet_Aug30_PARTIAL_FAIL.log, stride 2, frames 340-815):** yoke_bus min -0.39 m (sats 0-28), pod_own min -0.34 m (all), col_wing -0.19 m (sats 0-19, frames 350-426). Shifting yoke, plate or pod start times did not remove yoke_bus. Only sat 29 (the Aug single-sat class) is nearly clean (pod_own -0.07 before the plates1 fix). Likely cause: the per-class planner models the yoke and pod differently from the checker for the multi-pack classes; the planner also cannot plan sats 24-26 (class 24 deadlocks on plates0, its own stowed model reports -0.17 m overlaps; four ordering variants in `derisk/planner_c24_*.log`; the merged `scene/Aug/stage_plan_Aug30.json` uses variant v1 for 24-26 and is UNVERIFIED). Not fixed in the time box. Options in the report.
R1 camera (`derisk/adapter_camera_R1.log`, repo fleet camera, ESTIMATE): all 30 sats stay inside the safe box through frame ~96 (release), 20-47% of corners fall outside at frames 168-300 (coast), and 97% (about 29 of 30 sats) are outside from the unfold start (frame 346) because the outward release leaves odd layers ~620 m and even layers ~240 m from the camera target. The hero satellite itself is not separately measured. Fix options: switch to the hero-fit camera (`FLEET_HERO_CAM`, as in Render 2) for the unfold half of Render 1, or cut the release speed (more sat-sat risk).
### Render plan (ESTIMATE, from `render_budget.py prior`; the preview calibrates; box has no Isaac)
| Setting | Render 1 (Aug, 816 frames) | Render 2 (Jun + Aug, 476 frames each) | Both x1.5 safety |
|---|---|---|---|
| 720p, 64 spp | 24.8 s/fr = 5.6 h | 4.5 s/fr = 1.2 h | 10.2 h |
| 720p, 128 spp (recommended) | 28.1 s/fr = 6.4 h | 6.1 s/fr = 1.6 h | 12.0 h |
| 720p, 256 spp | 34.8 s/fr = 7.9 h | 9.2 s/fr = 2.4 h | 15.5 h |
Run Render 2 first if Render 1 is still blocked (it is short and already clean); Render 1 must start by Thu Nov 5 5 PM PT (Fri Nov 6 9 AM Taipei) to keep a buffer before the last compute (Fri Nov 6 5 PM PT = Sat Nov 7 9 AM Taipei). Latest compute-limit start for Render 1 at 720p / 128 spp is about Fri Nov 6 5 AM PT (9 PM Taipei) but with no buffer.

Bundle: `gb10_render_replica/` (README.md has the run order). Figures: `figures/fig_t438_final_designs.png`, `figures/fig_t438_stowed_stack_final.png`, `figures/fig_t436b_credibility.png` (regenerated: "Maga-ROSA" typo fixed, "no fold" -> "fold 4 (repo)"; old copy `.bak_t438`).

## 3d. STACK STIFFNESS LOOP (task t440; log `process_log/t440.jsonl`; code `box_gtc/t440_stack.py`, `t440_loop.py`; data `gb10_render_replica/derisk/stack_stiffness.json`)
Requirement (ASSUMED for Starship): first mode >25 Hz axial, >10 Hz lateral (Falcon Payload User's Guide, STATEMENT for Falcon). Loads +6 g axial, +-2 g lateral. Frequencies are upper bounds (rigid base and bodies).
| Case | Jun (46 sats, 19 levels) axial / lateral | Aug (30 sats, 18 levels) axial / lateral |
|---|---|---|
| No ties | 6.9 / 3.3 Hz | 7.0 / 3.4 Hz |
| Tie every 12 levels | 11.2 / 9.9 | 11.8 / 11.3 |
| Tie every 8 levels | 16.4 / 26.8 | 19.2 / 34.3 |
| Tie every 6 levels | 25.4 / 58.9 | 21.2 / 53.9 (fails axial) |
| **Tie every 3 levels (6 ties), rigid bay wall** | **25.4 axial, passes** | **33.3 axial, passes** |
| same, wall 10x / 3x compliance | 24.8 / 23.4 (marginal / short) | 32.0 / 28.8 |
Cheapest path that meets 25 / 10: bay-wall ties every 3 levels. Cost: Jun +7.6 kg/sat (+10.6 with a 3x-compliant wall, post upsizing 1.14), Aug +12.3 kg/sat; both inside the margins (345 kg and 535 kg), so counts 46 / 30 and 70.4 / 76.5 kW/t are unchanged (ESTIMATE). Volume: Jun 46 holds with zero slack (45 layers), Aug stays at 31-32 >= 30. Post-only stiffening reaches only ~10.7 / 5 Hz at +31 kg/sat (25 / 10 Hz would cost +260 kg/sat Jun, +382 kg/sat Aug); inter-satellite shear ties do not help.
Caveats: ties need anchor points on the dispenser bay wall (placement ASSUMED free); Jun only just meets 25 Hz (25.4 rigid, 24.8 at 10x wall compliance, 23.4 at 3x); the model assumes a rigid base. Poster wording: "With bay-wall tie-downs every third level, the stack's first mode is ~25 Hz (Jun) / ~33 Hz (Aug) (ESTIMATE; Falcon's 25 / 10 Hz applied to Starship by assumption; ties assume wall anchors). Untied, it is ~7 / 3.4 Hz."

## 4. Schedule (PT / Taipei) with buffer (re-dated for the packing gate)
| When PT | When Taipei | What |
|---|---|---|
| Tue Nov 3 5:30 PM | Wed Nov 4 9:30 AM | Plan, figure, 6 param sets, box packer + CAD, GB10 bundle ready (done); the author's GB10 smoke passed 5:27 PM |
| Tue Nov 3 5:40-6:00 PM | Wed Nov 4 9:40-10:00 AM | Packing loop passes 0-5 done: 46 / 30 reachable with four assumptions (section 3a) |
| Tue Nov 3 evening to Wed Nov 4 ~9 AM | Wed Nov 4 10 AM to Thu Nov 5 1 AM | GB10 `./run.sh all` running (thermal ~15 min, then 4 Newton cases, 3-5 h; worst ~11 AM PT if shared GPU) |
| Wed Nov 4 AM | Wed Nov 4 evening | Step-0.1 packer check; the author accepts or changes the lever set (numbered options in the report) = packing gate decision |
| Wed Nov 4 - Thu Nov 5 (day) | Thu Nov 5 | Box: analysis tables/figures; render scene adapter (about 1 day, runs in parallel with the loop); optional packing re-passes if the author changes the levers |
| Thu Nov 5 4:00 AM | Thu Nov 5 8:00 PM | `./run.sh newton` adds the 2 MID cases (1.5-2.5 h) |
| Thu Nov 5 by 5 PM | Fri Nov 6 by 9 AM | LATEST Render 1 launch (Aug, 30 sats, release -> unfold; ~6.4 h at 720p / 128 spp, ESTIMATE; needs the fleet clearance fix) |
| Fri Nov 6 up to 5 PM | Sat Nov 7 up to 9 AM | Render 2 (Jun + Aug single satellites side by side, ~1.6 h ESTIMATE; can run first as it is clean) and last compute deadline |
| Sat Nov 7 | Sun Nov 8 | Poster integration of figures/tables/render stills; text pass |
| Sun Nov 8 | Mon Nov 9 | Content freeze |
| Sun Nov 8 - Tue Nov 10 5 PM PT | Mon Nov 9 - Wed Nov 11 9 AM | Buffer (2 days compute-free), submission hygiene scan, PR (the author merges) |
Slack: with the gate decided by Wed Nov 4 night, Jun render launch is possible Thu Nov 5, leaving about 1.5 days between last compute and freeze plus 2 days after. If the GPU is shared (19 ms/step) Newton must-have takes ~7 h instead of 3-5 h, still inside the plan. If the packing gate slips past Thu Nov 5 5 PM PT, the render drops to fallbacks a-d and the poster integration is unaffected.

## 5. Risks and findings so far
1. **Packing gap (ESTIMATE, important; being solved in section 3a).** At repo defaults the replica packs 17 (Jun) / 12 (Aug) per Starship against the mass-limited 46 / 30 (STATEMENT). The loop reaches 46 / 30 (the mass bound, so the true ceiling is mass) only with four unsized what-ifs: leaf pitch 4 mm, radiator pitch 10 mm, rack+equipment boxed at 800 kg/m3, adapter 0.05 m. Loads and hold-down are not sized. Poster wording must say "stowed volume is feasible if these stow assumptions hold", not "proven". If the author does not accept them, the honest statement is the earlier one: mass says 46 / 30, our repo-default stow says 17 / 12.
2. Packer step 0.25 m is coarse (conservative vs finer grid by a few %): step-0.1 check of the 46/30 combo is running (section 3a).
3. Newton t410 actual runtime was never recorded; our per-case estimate is 44-76 min, shared GPU worse.
4. Render needs an adapter that does not exist; schedule risk on option 1/2.
5. The replica radiator/array architecture is ASSUMED to match the adopted baseline's panel (A6L 0.3634 x 2.9446 m) and 14 m x 20-leaf Z-fold array; SpaceX has not stated either.
6. Region figure: the adopted baseline sits outside the C1-C2 band (wing 194 W/kg vs C1 332): state this plainly on the poster.

## 6. Status of box jobs (details in `box_gtc/`)
- `results/t434_region.json`, figure: done.  `gtc_params/` 6 files: done.
- Packer (step 0.25, fold 2/4 x 3 architectures): `box_gtc/results/pack_{BASE254,J8_C1,A4_C1}_step0.25.json`. Layers/fold4: BASE254 14, J8 17, A4 12.
- Sensitivity probe VEQ_SCALE: see `box_gtc/results/pack_*_veq*.json` (appended as it finishes).
- CAD: `box_gtc/results/step/replica_{J8_C1,A4_C1}_deployed.step`, `geom_*.json`: arrays 493.8 / 823.0 m2 (<1,500), radiator 82.4 / 137.0 m2 (<200; panel count rounding up from 81.63 / 136.05), mass < 4,000 kg: FCC flags pass. Bbox of the radiator block is an artefact; do not quote.
- GB10 bundle: `gb10_gtc/` and `gtc_replica_bundle.tgz`, README inside.
- Packing loop (t436): `box_gtc/t436_loop.py`, `box_gtc/results/t436/passes.jsonl`, `box_gtc/logs/t436_P*.log`, `make_fig_t436_path.py`, `make_fig_t436_stack.py`. The running GB10 bundle is untouched.

### UPDATE Nov 4 ~12:29 Taipei (Nov 3 8:29 PM PT) - Render 1 own-sat clearance
- INFERENCE: the earlier yoke_bus -0.39 m / pod_own -0.34 m failures came from the per-class merged plan (yokes handed to the kinematic pose before the satellite was ready). The single-satellite Aug plan applied to all 30 sats removes them: yoke_bus +50 mm, pod_own +10 mm.
- OPEN: col_wing -64 mm at worst (sats 8-28, one short window each, frames 340-815 stride 4). Unresolved; rank-dependent. R1 default plan is now scene/Aug/stage_plan_Aug30_singleplan.json. Logs: derisk/adapter_ownsat_fleet_Aug30_singleplan_PARTIAL.log.
- R1 camera loss of the fleet at unfold start is still OPEN. Render 2 remains clean and ready.

### UPDATE Nov 4 ~14:50 Taipei (Nov 3 ~10:50 PM PT) - render adapter fixes (t441)
- (a) R1 col_wing FIXED on the box (INFERENCE, kinematic model, 0.02 s scans): Aug plans (stage_plan_Aug30_singleplan.json, stage_plan_single_Aug.json) regenerated from the .bak_t441 originals with col1_00 +1.0 s, plates1 +0.37 s, pod +0.40 s (fix_col_wing_plan.py). All 30 sats, tau 16-24: PASS, min margins col_wing +8.2 mm, pod_own +9.1 mm (colcol_adj +1.0 mm same as baseline). Stride-4 frames 340-815: all categories > 0, smallest col_wing +4.8 mm (frame 448, sat 14). Windows are narrow (plates1 ~0.33-0.42, pod ~0.35-0.42): re-scan at 0.02 s after any planner/layout/timing change.
- (c) Release frames 0-340 own-sat, new plan, stride 4: all 13 categories > 0 (min col_wing +8.9 mm, wing_wing +10.4 mm, colcol_adj +13.6 mm, pod_own +10.0 mm). Sat-sat checker: see README section 5 / final report (AABB-level, not a contact solve).
- (b) R1 fleet-fit camera (fleet_fit_cam_replica.py): 0/204 frames (stride 4, 0-815) outside the safe box. One satellite is ~37 px wide at fleet scale.
- (d)/(f) R2: camera fits from frame 340, grey column hidden, replica caption, shared scale identical Jun/Aug in 119/119 sampled frames, 0 outside safe box (scene/R2_shared_dist.json).
- (e) Newton width-fold: run_wfold.py rebuilt for n blocks (ASSUMED analog, not validated; latch torque depends on dt, quote dt 5e-4). GB10 rerun pending.
- Bundle: gb10_render_replica.tgz rebuilt (old copies .bak_t441, .bak_t441b). Read README STATUS block for the exact commands.
- OPEN (c): sat-sat checker (AABB, release phase T 0-88 s): 23 negative pair gaps, min -2.17 m (pair 24-27, T=69 s), 1,816 box-overlap events in pairs (2k,2k+1) and sats 24-29 (ASSUMED placeholder pack). Rail clearance +0.72 m. Not analysed. Own-sat release check is clean.
