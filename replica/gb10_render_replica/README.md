# gb10_render_replica: derisk gate + the two replica renders (prepared by t438/t440; NOTHING here has been launched on the GB10)

> STATUS (Nov 4 ~14:10 Taipei = Nov 3 10:10 PM PT, t441): ADAPTER_DONE=1. Own-sat `col_wing` fixed in the Aug stage plans (see section 5); R2 scene fixed (shared scale, camera, no column, replica caption); R1 fleet-fit camera added; Newton width-fold script rebuilt for n blocks. NOTHING here has been launched on the GB10 by this bundle; GB10 previews must be re-run with this bundle (section 5).
Final configs: Jun J8_C1 (leaf 6 mm, fold 5, 10 mm radiator pitch, 46 per Starship, 70.4 kW/t). Aug A4_C1 config E (leaf 6, fold 6, 30 per Starship, 76.5 kW/t). ESTIMATES; see GTC_REPLICA_PLAN.md section 3c/3d.
**Render 1** = August only, the full sequence Starship release -> unfold, 30 satellites, frames 0..815 of the adopted clip (816 frames, 34 s at 24 fps).
**Render 2** = June and August single satellites unfolding side by side (no fleet, no release), frames 340..815 per satellite (476 frames, 19.8 s), composed by `compose_render2.sh`.
The June fleet render is dropped. One Isaac / Newton job at a time on the GB10 (check `nvidia-smi` first; the earlier GTC bundle may still be running). Full renders only after the gate below passes.

## 1. Exact command order for the author
```
export REPO=~/gb10_work/repo_replica_src   # read-only (copy of t359b_work/repo + results/omniverse); overlays are built by copy under ./work (new dirs ov_Aug_r3 / ov1_<B>_r3, so stale overlays are never reused)
export PYV=<venv_newton>/bin/python            # = 'venv_newton python' (numpy RNEA run_wfold, clearance checker, make_r2_shared)
export PY=$PYV
export ISAAC_PY=<isaac python, e.g. <base>/venv_isaac2/bin/python>
export ADAPTER_DONE=1
tar xzf gb10_render_replica.tgz && cd gb10_render_replica
# (a) Newton second-stage fold, Jun n=5 and Aug n=6, W0 = 0.10 / 0.17 / 0.25 (6 short runs), then the gate summary
bash run_derisk_gb10.sh newton ; python3 check_gate.py work
python3 apply_wfold_timing.py Aug work ; python3 apply_wfold_timing.py Jun work      # REPORTS the Newton width-fold times; keeps the 14 s the stage plans were clearance-checked with (--apply overrides, then re-plan)
# (d) previews: clearance checker first, then sparse frames at 960x540, 16 and 32 spp (s/frame calibrates the full renders)
# R2 needs scene/R2_shared_dist.json (shipped; regenerate only if the layout changes):  $PYV make_r2_shared.py work/ov1_Jun_r3 work/ov1_Aug_r3 scene/R2_shared_dist.json   (after the first preview built the overlays)
bash run_preview_render.sh R1 Aug                    # 20 frames of the fleet
bash run_preview_render.sh R2 Jun ; bash run_preview_render.sh R2 Aug      # 8 frames each
python3 render_budget.py <R1 s/fr @16spp> <R1 @32> <R2 s/fr @16> <R2 @32>    # picks resolution / spp and prints the latest start
# the full renders (resumable; re-run the same command after any interruption)
bash run_replica_render.sh R1 Aug work/out_R1_Aug 128 1280 720
bash run_replica_render.sh R2 Jun work/out_R2_Jun 128 1280 720
bash run_replica_render.sh R2 Aug work/out_R2_Aug 128 1280 720
bash compose_render2.sh work/out_R2_Jun work/out_R2_Aug work/render2_side_by_side.mp4
ffmpeg -framerate 24 -i work/out_R1_Aug/f_%05d.png -c:v libx264 -crf 16 -pix_fmt yuv420p work/render1_aug_fleet.mp4
```
`run_replica_render.sh` picks up `work/wfold_timing_<B>.env` automatically if it exists (override with `WFOLD_ENV=`); it prints which timing it uses. `render_budget.py prior` prints the pre-preview estimate.
Look at: `work/newton_wfold_*.log`, `results/newton_array/wfold_n<N>_w<W0>.json` (t_all_latched, peak latch torque, sync error). Fold time ~ 1/W0; W0 ~ 0.17 is ~14 s. Pass = all latch, sync error small, peak latch torque below the blanket-hinge limit (`derisk/blanket_check.json`). `newton_wfold/run_wfold.py` is an ASSUMED analog of the repo `run_array.py` and has not been run anywhere: expect a first-run fix.

## 2. Already done on the box (CPU), results in `derisk/`
- (b) `fea_panel_disp.json`: CalculiX, flat-header panel, 10 mm pitch: 0.849 mm (6 g axial), 0.522 mm (2 g lateral) vs 4.32 mm clearance. PASS (ESTIMATE).
- (c) `stack_modes.json`: first mode of the packed stack Jun 6.9 / 3.3 Hz, Aug 7.0 / 3.4 Hz (axial / lateral). Falcon Payload User's Guide >25 / >10 Hz (STATEMENT); Starship guide states none (applying it is an ASSUMPTION). OPEN RISK; t440 (`derisk/stack_stiffness.json`) gives the cheapest fix.
- `blanket_check.json`: blanket bend strain 0.42-1.28% at 6 mm pitch vs 3% assumed yield (ASSUMED). `margin_table.json`, `final_configs.json`.
- Scene adapter results and clearance logs: `derisk/adapter_*` (see GTC_REPLICA_PLAN.md 3d).

## 3. Render scene adapter: status (t440)
`make_overlay.sh <Jun|Aug> <REPO> <OUT>` builds a repo-shaped copy (`ONE_SAT=<index>` makes a single-satellite scene for Render 2) and applies `patch_fleet_kin.py` (replica column plan, NSEC = fold n, two-box body via the pod, rot90 satellites, array chain), `adapt_scene.py` (assets, y-lip scaling, release timing scaled from the layer pitch), and `patch_stage_plan.py` (count-generic planner). Shipped collision-planned staging plans: `scene/Aug/stage_plan_Aug30.json`, `scene/{Jun,Aug}/stage_plan_single_*.json`.
1. Two-box body: DONE (rack + equip as the bus/pod pair; stowed frame-0 minimum gap +6 mm). 2. Counts 46 / 30: no hard-coded 14 left. 3. Release plan: layer-stagger timing scaled to the replica pitch + the collision planner. 4. Yoke root: 4.137 m (repo `chain_params_T45.json`, because the Newton h(t) was solved with it; the 1.968 m was a stage-1 placeholder). 5. Width-fold: `FLEET_TAU_W` env, default 14 s placeholder, replaced by `apply_wfold_timing.py` after (a). 6. n = 5 / 6 Newton chain npz for replay: kinematic fold until (a) returns.
Camera: Render 1 uses the repo camera unchanged (hold + trailing hero sat 6; the framing for 30 satellites with the outward release is checked by `camera_extent_replica.py`, results in `derisk/adapter_camera_R1.log`; ESTIMATE, the preview must confirm). Render 2 uses the repo hero-fit camera (`FLEET_HERO_CAM`, `scene/R2_hero_cam.json`: hero = the single satellite, fill 0.72, speed 1.0 so frames map 1:1); the repo fleet camera is 240 m away and would show one satellite at ~15% of the frame. In the side-by-side each satellite is fitted to its own frame, so Jun and Aug are NOT at the same scale: say so in the caption, or fix `fill` per build after the preview. The patched `HERO` index is clamped to the satellite count (`FLEET_HERO_IDX`).

## 4. Schedule
Latest Render 1 launch Thu Nov 5 5 PM PT (Fri Nov 6 9 AM Taipei); last compute Fri Nov 6 5 PM PT (Sat Nov 7 9 AM Taipei). `render_budget.py prior` (ESTIMATE): Render 1 ~6.4 h and Render 2 (both satellites) ~1.6 h at 720p / 128 spp; the preview replaces the prior.

## 5. t441 changes (Nov 4): what to run, what changed
**R2 preview (GB10)** - ONE command per build; builds fresh overlays (`ov1_<B>_r3`), runs the checker, then 8 frames at 16 and 32 spp:
```
export REPO=~/gb10_work/repo_replica_src ISAAC_PY=<isaac python> PYV=<venv_newton>/bin/python
bash run_preview_render.sh R2 Jun ; bash run_preview_render.sh R2 Aug
```
(first call builds both overlays only as needed; if `scene/R2_shared_dist.json` is missing run `make_r2_shared.py` as above, it needs both `ov1_*_r3` overlays - run `bash make_overlay.sh Jun $REPO work/ov1_Jun_r3` with `ONE_SAT=44`, and `ONE_SAT=29` for Aug, if you want to regenerate it.)  **R1 preview:** `bash run_preview_render.sh R1 Aug`.
- Check the GB10 repo render script first: `grep -c FLEET_HERO_CAM $REPO/experiments/poster/render_fleet_omniverse_t360_T45.py` (0 = the old t359b copy: no hero-camera hook, which is why the earlier R2 preview showed a tiny satellite). `make_overlay.sh` now replaces the overlay's render script + hero module with the box-tested ones (`scene/box_scripts/`, `patch_render_replica.py`) so this no longer depends on the GB10 repo copy.
- R2 fixes (all env-driven from `run_replica_render.sh`): `FLEET_R2_SHARED` = one camera distance for June and August (same px/m; `fleet_hero_r2_shared.py`), `FLEET_HIDE_SHIP=1` (the grey column = the schematic Starship hull/deck/rails at 240 m, INFERENCE from the scene code: it is not part of the satellite), `REPLICA_BUILD`/`REPLICA_ONE_SAT` (caption: "SIMULATED - replica, not SpaceX's design - assumed parameters (ESTIMATES) - June|August build: 46|30 satellites per Starship (ESTIMATE)"; NASA Blue Marble credit unchanged), `FLEET_HERO_CAM` kept (q0=900,q1=901: no ease to a group fit). R1: `FLEET_FIT_CAM='{}'` (fleet-fit camera, all 30 satellites framed, frames 0..815) and the same caption.
- `compose_render2.sh`: labels moved to y=64 (below the caption band).
**Width-fold (Newton) rerun** - `newton_wfold/run_wfold.py` was rewritten (the repo `run_array.py` model latches only 1 of 21 hinges by itself, sync error ~2.1; the deployable model is the cable-synchronised `run_array_sync.py`, re-built for n blocks):
```
bash run_derisk_gb10.sh newton ; python3 check_gate.py work
# or one case:  cd work/ov_Aug && RTS_TAG=_T45 RUN_ARRAY_DIR=$PWD/experiments/newton_array $PYV ../../newton_wfold/run_wfold.py 6 0.17 60 5e-4
```
`RUN_ARRAY_DIR` must be set (run_derisk_gb10.sh does). dt: latch torque depends on dt (n6 W0=0.17: 7.8 kN m at 1e-3, 4.3 kN m at 5e-4, same latch time 16.55 s), so quote the 5e-4 value; the 5e-4 run takes ~330 s on the box CPU. Gate thresholds unchanged.
**col_wing fix** - `fix_col_wing_plan.py` (cause, shifts and windows in its docstring) applied to `scene/Aug/stage_plan_Aug30_singleplan.json` and `stage_plan_single_Aug.json` (originals `.bak_t441`). Jun single plan untouched.

### Open item: sat-sat checker in the release phase (ESTIMATE, AABB level, not a contact solve; box run Nov 4)
`fleet_clearance_T45.py` (does not read FLEET_STAGEPLAN, so the col_wing plan fix does not change it) reports 23 pairs with negative AABB gap and 1,816 real box-overlap events, all between T=0 and ~88 s (satellite pairs 0-1, 2-3 ... 22-23 and the sat-0-pack placeholder sats 24-29, which are ASSUMED positions). Worst: pair 24-27 -2.17 m at T=69 s. Pairs 0-2 and 1-3 -14/-8 mm at T=19 s. Rails min clearance +0.72 m. Not analysed or fixed: needs the release-phase layout (same-layer pairs and sats 20-29 pack) reviewed before the R1 launch. Own-sat release check (frames 0-340, new plan, stride 4) is clean.
