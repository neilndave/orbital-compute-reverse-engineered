#!/usr/bin/env bash
# Replica renders on the GB10 (Isaac Sim).  PREPARED, NOT LAUNCHED.  Resumable: frames already on disk are skipped; crash / start-up hang -> restart (up to 12 attempts).
#   RENDER 1 : August fleet, 30 satellites, full sequence Starship release -> unfold, frames 0..815 of the adopted 816-frame clip (34 s @ 24 fps).
#   RENDER 2 : ONE satellite unfolding (Jun J8_C1 or Aug A4_C1), frames 340..815 (stowed hold -> fully unfolded); run it once per build, then compose_render2.sh puts them side by side.
# usage: REPO=<repo root> ISAAC_PY=<isaac python> bash run_replica_render.sh <R1|R2> <Jun|Aug> <OUTDIR> [spp] [W] [H]
#   defaults: R1 spp 128 1280x720 ;  R2 spp 128 1280x720 per satellite.  PREVIEW: set OMNI_FRAMES_LIST="0,60,120,..." (sparse list) and a low spp (e.g. 32) and W H 960 540.
#   optional env: WFOLD_ENV=<work/wfold_timing_<B>.env> (Newton width-fold timing, see README), NPROC, WORK (overlay dir parent), SPP quality knobs OMNI_DEN / OMNI_BOUNCES.
set -uo pipefail
MODE=${1:?R1|R2}; B=${2:?Jun|Aug}; OUT=${3:?outdir}; SPP=${4:-128}; W=${5:-1280}; H=${6:-720}
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO=${REPO:?repo root}; WORK=${WORK:-$HERE/work}; PY=${ISAAC_PY:?isaac python (e.g. <base>/venv_isaac2/bin/python)}
case $MODE in
  R1) [ "$B" = Aug ] || { echo "RENDER 1 is August only"; exit 2; }; OVN=ov_Aug_r3;  PLAN="$HERE/scene/Aug/stage_plan_Aug30_singleplan.json"; FRA=0; FRB=815 ;;
  R2) case $B in Jun) export ONE_SAT=44 ;; Aug) export ONE_SAT=29 ;; esac; OVN=ov1_${B}_r3; PLAN="$HERE/scene/$B/stage_plan_single_$B.json"; FRA=340; FRB=815 ;;
  *) echo "mode R1|R2"; exit 2 ;;
esac
OV="$WORK/$OVN"; [ -d "$OV" ] || bash "$HERE/make_overlay.sh" $B "$REPO" "$OV"
[ -f "$PLAN" ] || { echo "missing stage plan $PLAN"; exit 2; }
cd "$OV/experiments/poster"; unset PYTHONPATH; mkdir -p "$OUT" "$WORK/logs" "$WORK/tmp"
export OMNI_KIT_ACCEPT_EULA=YES TMPDIR="$WORK/tmp" RTS_TAG=_T45
[ -e /lib/aarch64-linux-gnu/libgomp.so.1 ] && export LD_PRELOAD=/lib/aarch64-linux-gnu/libgomp.so.1
[ -z "${WFOLD_ENV:-}" ] && [ -f "$WORK/wfold_timing_$B.env" ] && export WFOLD_ENV="$WORK/wfold_timing_$B.env"; echo "width-fold timing env: ${WFOLD_ENV:-none (14 s placeholder)}"
source ./fleet_replica_env.sh; export FLEET_STAGEPLAN="$PLAN" FLEET_OVERLAY=new
export REPLICA_BUILD=$B                                  # [t441] caption: June 46 / August 30 per Starship (ESTIMATE), 'replica, not SpaceX's design'
if [ "$MODE" = R2 ]; then
  export FLEET_HERO_CAM="$(cat "$HERE/scene/R2_hero_cam.json")" REPLICA_ONE_SAT=1 FLEET_HIDE_SHIP=1      # R2: hero-fit close-up on the single satellite; no hull/deck/rails (they are 240 m away, only a grey column in wide views)
  [ -f "$HERE/scene/R2_shared_dist.json" ] || { echo "missing scene/R2_shared_dist.json: run make_r2_shared.py (README step 3)"; exit 2; }
  export FLEET_R2_SHARED="$HERE/scene/R2_shared_dist.json"   # [t441] ONE shared camera distance for Jun and Aug = same true scale (px/m) in both clips
else
  export FLEET_FIT_CAM='{}'                                  # [t441] R1: fleet-fit camera, all 30 satellites framed through the unfold
fi
FR=${OMNI_FRAMES_LIST:-$(seq -s, $FRA $FRB)}; export OMNI_FRAMES=$FR; NEED=$(echo "$FR" | tr ',' '\n' | wc -l)
nfr() { ls "$OUT"/f_*.png 2>/dev/null | grep -v tmp | wc -l; }
for a in $(seq 1 12); do
  [ "$(nfr)" -ge $NEED ] && { echo "all frames present"; break; }
  LOG="$WORK/logs/replica_${MODE}_${B}_$(basename $OUT)_attempt$a.log"
  taskset -c 0-3 "$PY" -u render_fleet_omniverse_t360_T45.py $SPP $W $H 0 816 "$OUT" < /dev/null > "$LOG" 2>&1 &
  pid=$!
  for s in $(seq 1 90); do sleep 1; [ -s "$LOG" ] && break; done
  [ -s "$LOG" ] || { echo "attempt $a: start-up hung, killing own pid $pid"; kill $pid; sleep 1; kill -9 $pid 2>/dev/null; }
  wait $pid; rc=$?; echo "$(date +%F_%T) attempt $a rc=$rc frames=$(nfr)/$NEED"
  [ $rc -eq 0 ] && break
done
echo "$(date +%F_%T) finished frames=$(nfr)/$NEED"
