# Orbital Compute, Reverse-Engineered
### working back from SpaceX's published AI1 numbers

**Status: GTC final candidate.** The poster numbers come from one reproducible configuration in [`replica/gtc_final/`](replica/gtc_final/README.md) (scoped baseline + peak battery + MPG40 freeze/restart + trunk shields). Earlier documents in `docs/` and `replica/` describe the design history and use older configurations; where they differ, `replica/gtc_final/results/GTC_FINAL_CANDIDATE.json` wins. Renders are complete (Render 1: the August fleet from release to full unfold; Render 2: June and August single satellites side by side).

## The story
SpaceX has published headline figures for its AI1 orbital-compute satellites ([source](https://www.spacex.com/spacexai/starmind)): a June build of about 150 kW and 2,130 kg, 46 per Starship (about 70 kW/t), and an August build of about 250 kW and 3,270 kg, 30 per Starship (about 75 kW/t) (STATEMENT). This repo works backwards from those numbers. It does not use any non-public SpaceX information. We ask what a satellite would have to look like to hit them, using first-principles subsystem sizing and FCC-filing limits (4 t, 200 m² radiator, 1,500 m² array; STATEMENT). The answer is a band of designs, not a single point. It runs from **C1 "margin-forward"** (wing about 332 W/kg, rack about 2.6–2.7 kg/kW, 20.5 % growth margin) to **C2 "compute-limited"** (wing about 523 W/kg, rack about 5.1–5.4 kg/kW, 10 % growth) (ESTIMATE). We call this band the "SpaceX-like region". The poster designs are the C1 points: **June J8_C1, 46 per Starship, 70.4 kW/t** and **August A4_C1 (stow config E), 30 per Starship, 76.5 kW/t** (both ESTIMATE). We then check those designs with NVIDIA tools on one GB10 desktop (the final-candidate masses and specific power differ from these C1 points; see `replica/gtc_final/`):
- radiator fin and thermal Monte Carlo in **NVIDIA Warp**
- an exploratory **PhysicsNeMo** surrogate (not used by any final number)
- array deployment in **NVIDIA Newton**
- fleet renders in **Omniverse / Isaac Sim RTX**

Box-side checks cover stowed packing, stack stiffness and a CalculiX panel cross-check.

This is an independent analysis. SpaceX is named only as the source of the published numbers. Nothing here is endorsed by SpaceX or NVIDIA, and the repo contains no SpaceX imagery. Every figure is labelled STATEMENT (from a public source), ESTIMATE (our calculation), INFERENCE (reasoned) or ASSUMED (our input).

## What's in the repo
| Path | Contents |
|---|---|
| `docs/CALIBRATION.md` | How the C1/C2 designs are solved to 70/75 kW/t and 46/30 per Starship, the sensitivities, and the volume re-check |
| `docs/REPLICA_PLAN.md` | Plan and engineering log: tool inventory, packing loop, stow-assumption credibility, final configs, derisk gate, stack stiffness, render plan |
| `replica/` | All the code, in its working layout: calibration (`t423*.py`, `gen_params_t434.py`, `t434_region.py`), box checks (`box_gtc/`, `checks_t444/`), the GB10 Warp/Newton bundle (`gb10_gtc/`), the Omniverse render bundle (`gb10_render_replica/`), parameter sets (`gtc_params/`), GB10 outputs (`gb10_gtc_results/`) and per-pass logs (`process_log/`) |
| `results/figures/` | Small PNG figures (region, calibration, packing passes, stowed stack, final designs) |
| `scripts/` | `get_blue_marble.sh`: downloads the Earth texture for renders at run time |
| `vendor/same_rack/` | The few modules and inputs the replica code imports, plus the Omniverse / Isaac Sim render pipeline scripts the render bundle calls, reused from the sibling repo *Same Rack, Earth vs. Orbit* (provenance only; see `FILES.txt`) |

## How to reproduce
1. Use Python 3.11+ with numpy, scipy, matplotlib and pyyaml. Add build123d for the CAD envelope and CalculiX (`ccx` on PATH) for the panel cross-check.
2. Run from `replica/` with the vendored modules on the path: `export SAME_RACK_VENDOR=../vendor/same_rack`. Scripts refer to `vendor/same_rack`; you may need a symlink `replica/vendor -> ../vendor`.
3. Calibration and parameter sets: `python t423g.py && python gen_params_t434.py && python t434_region.py`. Figures: `python make_fig_t423g.py` and the other `make_fig_*.py` scripts.
4. Box checks (packing, stiffness, margins): the scripts in `box_gtc/` (`t438_loop.py`, `t440_stack.py`, `margin_table.py`, ...) and `checks_t444/check2_geometry.py`.
5. GPU work on a GB10 desktop: see `replica/gb10_gtc/README.md` (`./run.sh thermal`, `./run.sh newton`). For renders, see `replica/gb10_render_replica/README.md`. These need NVIDIA Warp and Newton, and Isaac Sim for the renders.

Not every pass is fully scripted end to end yet. The process logs record the inputs of each pass.

## Renders and Earth imagery
The NASA Blue Marble textures the render scripts expect are included, with credit, in `vendor/same_rack/results/omniverse/assets/`. `scripts/get_blue_marble.sh` is a fallback that re-downloads them from NASA Visible Earth. Earth imagery: NASA Visible Earth / Blue Marble. Use of NASA imagery does not imply NASA endorsement. See `CREDITS.md`.

## Licence
Apache-2.0. See `LICENSE`.
