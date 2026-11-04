#!/usr/bin/env bash
# PREVIEW for the replica renders (low res, low spp, sparse frames) + the clearance checker.  PREPARED, NOT LAUNCHED.  Calibrates s/frame for the full renders.
# usage: REPO=<repo> ISAAC_PY=<isaac python> bash run_preview_render.sh <R1|R2> <Jun|Aug>     (R1 = Aug fleet of 30; R2 = one satellite of that build)
set -euo pipefail
MODE=${1:?R1|R2}; B=${2:?Jun|Aug}; HERE="$(cd "$(dirname "$0")" && pwd)"; REPO=${REPO:?}; WORK=${WORK:-$HERE/work}; PY=${PYV:-python}
if [ $MODE = R1 ]; then OVN=ov_${B}_r3; FR=$(python3 -c "print(','.join(str(round(i*815/19)) for i in range(20)))")
else case $B in Jun) export ONE_SAT=44 ;; Aug) export ONE_SAT=29 ;; esac; OVN=ov1_${B}_r3; FR=$(python3 -c "print(','.join(str(340+round(i*475/7)) for i in range(8)))"); fi
OV="$WORK/$OVN"; [ -d "$OV" ] || bash "$HERE/make_overlay.sh" $B "$REPO" "$OV"
# 1) clearance checker with the render env (own-satellite, every 41st frame + the stowed frame 0) and, for R1, the satellite-vs-satellite checker.  PASS = no negative gap.
( cd "$OV/experiments/poster"; source ./fleet_replica_env.sh >/dev/null; export RTS_TAG=_T45 FLEET_STAGEPLAN="$HERE/scene/$B/$([ $MODE = R1 ] && echo stage_plan_Aug30_singleplan.json || echo stage_plan_single_$B.json)"
  NPROC=${NPROC:-6} $PY fleet_full_clearance_T45.py "$WORK/clr_${MODE}_${B}_stride41.npz" 41 | tee "$WORK/clr_${MODE}_${B}_stride41.log"
  [ $MODE = R1 ] && $PY fleet_clearance_T45.py | tee "$WORK/clr_${MODE}_${B}_satsat.log" || true )
# 2) the preview render itself (ONE Isaac job on the GPU): 960x540, sparse frames, at 16 spp and at 32 spp (two points -> fixed time and per-spp slope).  s/frame is printed in the logs.
for SPP in 16 32; do
  OMNI_FRAMES_LIST="$FR" bash "$HERE/run_replica_render.sh" $MODE $B "$WORK/preview_${MODE}_${B}_spp$SPP" $SPP 960 540 | tee "$WORK/preview_${MODE}_${B}_spp$SPP.log"
done
echo "Per-frame times: grep the timing lines in $WORK/logs/replica_${MODE}_${B}_preview*_attempt*.log (skip the first frame: scene load).  Then: python3 $HERE/render_budget.py <R1 s/fr @16> <R1 @32> <R2 s/fr @16> <R2 @32>"
