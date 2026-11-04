# GTC replica bundle (GB10 desktop)

Runs the NVIDIA-tool checks for the SpaceX-region replica (C1 margin-forward to C2 compute-limited; Jun 150 kW / 2,130 kg and Aug 250 kW / 3,270 kg builds).
Everything stays inside this folder. No sudo. Nothing is killed. Other GPU processes are never touched: `run.sh` refuses to start while another GPU process is running unless you set `FORCE=1`.

## Install (one time, on the GB10 desktop)
Copy this folder to `~/gb10_work/gtc_replica` (the status check looks for that folder name), then:

    cd ~/gb10_work/gtc_replica && chmod +x run.sh newton/run_newton.sh
    ./run.sh smoke        # ~1 min, tiny CPU run; the last lines should say "FINISHED all chunks"
    ./run.sh status

## Run
    ./run.sh thermal      # thermal Monte Carlo + area sizing, 2 builds (Jun, Aug), fin tables cached. ESTIMATE 10-15 min
    ./run.sh newton_must  # Newton 21-hinge deployment, C1 and C2 x Jun and Aug (4 cases). ESTIMATE 3-5 h, up to ~7 h if the GPU is shared
    ./run.sh newton       # all 6 cases (adds the MID points)
    ./run.sh all          # thermal, then newton_must
    ./run.sh status | pause | resume

Python environments: thermal uses `~/gb10_work/venv_repo` (override `AI1_PY=`), Newton uses `~/gb10_work/venv_newton` (override `NEWTON_PY=`).
Pause stops the thermal runner within a chunk and Newton after the current case. Finished chunks/cases are kept and skipped on resume.

## What is in here
- `params/point_<build>_<C1|MID|C2>.json` -- the 6 design points (J8 = Jun 150 kW, A4 = Aug 250 kW); `params/thermal_builds.json` -- loop-sized radiator areas used by the thermal runner (identical for C1/MID/C2: thermal does not see rack or array mass).
- `thermal/` -- the t422 runner with a `GTC_BUILDS_JSON` override of the builds (everything else unchanged), seeded with the cached fin tables.
- `newton/overlay_<id>/` -- unchanged copies of the repo's Newton scripts plus replica input JSONs (array mass, array area, wing length) under the baseline file names, so `RTS_TAG=_T45` reads replica values inside the overlay only. Same case as t410: motor tdep 300 s, dt 1 ms, tend 330 s, latch K 5e5, zeta 0.3.
- Results land in `thermal/results`, `thermal/metrics`, `results/newton`, logs in `logs/`.

## Copy results back
Copy the whole `gtc_replica/results`, `gtc_replica/thermal/results`, `gtc_replica/thermal/metrics` and `gtc_replica/logs` folders back to the box (`replica/gb10_gtc_results/`) when the status shows all cases done.

Labels: every number from these runs is an ESTIMATE of a replica design; the inputs (panel/array architecture, hinge parameters) are ASSUMED to be the adopted baseline's.
