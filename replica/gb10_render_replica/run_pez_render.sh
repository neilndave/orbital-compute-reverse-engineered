#!/usr/bin/env bash
# [t460] RENDER 1 with the INDEXED PEZ release (Aug, 30 sats).  PREPARED, NOT LAUNCHED.  Separate from run_replica_render.sh (kept untouched = the Option-3 fallback).
#   960 frames @ 24 fps = 40 s: release time-lapse (clip 0-20 s, labelled 'time-compressed; real gaps ~30-70 s') -> unfold (clip 20-40 s, unchanged 160 s sim window).
# usage: REPO=<repo root> ISAAC_PY=<isaac python> bash run_pez_render.sh <OUTDIR> [spp] [W] [H]       PREVIEW: OMNI_FRAMES_LIST="0,60,..." and spp 32, 960 540
# [t483] 2.0 m/s push (INFERENCE), chase camera, 960 frames = 40 s. Measured on the GB10 (preview): 640x360 spp 8 every 2nd frame (OMNI_FRAMES_LIST=$(seq -s, 0 2 958)) = 480 frames, 385 s wall, 0.7 s/frame. Full-quality test frames: OMNI_FRAMES_LIST=60,300,700 with 128 1280 720. Each Isaac start-up also builds the camera table (~1-2 min).
# Resumable (frames on disk are skipped; crash / start-up hang -> restart, up to 12 attempts).  Optional env as run_replica_render.sh (WFOLD_ENV, NPROC, WORK, OMNI_DEN, OMNI_BOUNCES).
set -uo pipefail
B=Aug; OUT=${1:?outdir}; SPP=${2:-128}; W=${3:-1280}; H=${4:-720}
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO=${REPO:?repo root}; WORK=${WORK:-$HERE/work}; PY=${ISAAC_PY:?isaac python (e.g. <base>/venv_isaac2/bin/python)}
OVN=ov_Aug_pez; PLAN="$HERE/scene/Aug/stage_plan_Aug30_singleplan_n0s.json"   # [t460] plan for sats 27-29 re-handed over with their accordion start delayed (FLEET_N0_SAT below); the t445 singleplan FAILS yoke_bus -0.42 m for 27-29 at the render timing N0=29.6; FRA=0; FRB=959
OV="$WORK/$OVN"; [ -d "$OV" ] || FLEET_PEZ_BUILD=1 bash "$HERE/make_overlay.sh" $B "$REPO" "$OV"
[ -f "$OV/experiments/poster/pez_release.py" ] || { echo "overlay $OV was not built with FLEET_PEZ_BUILD=1 (no pez_release.py)"; exit 2; }
[ -f "$PLAN" ] || { echo "missing stage plan $PLAN"; exit 2; }
cd "$OV/experiments/poster"; unset PYTHONPATH; mkdir -p "$OUT" "$WORK/logs" "$WORK/tmp"
export OMNI_KIT_ACCEPT_EULA=YES TMPDIR="$WORK/tmp" RTS_TAG=_T45
[ -e /lib/aarch64-linux-gnu/libgomp.so.1 ] && export LD_PRELOAD=/lib/aarch64-linux-gnu/libgomp.so.1
[ -z "${WFOLD_ENV:-}" ] && [ -f "$WORK/wfold_timing_$B.env" ] && export WFOLD_ENV="$WORK/wfold_timing_$B.env"; echo "width-fold timing env: ${WFOLD_ENV:-none (14 s placeholder)}"
source ./fleet_replica_env.sh; export FLEET_STAGEPLAN="$PLAN" FLEET_OVERLAY=new REPLICA_BUILD=$B
export FLEET_N0_SAT="${FLEET_N0_SAT:-27:36.55,28:36.55,29:36.75}"   # [t460] per-sat accordion start N0_s = plan t_ready + 0.5 s (sats 27,28: 36.05; 29: 36.25)
export FLEET_PEZ=1 FLEET_PEZ_CAM='{}' FLEET_NO_RAILS=1 FLEET_HIDE_SHIP=${FLEET_HIDE_SHIP:-0}     # PEZ: slotted horizontal hull is built by pez_ship_usd (old hull/deck/rails hidden); slot camera -> fleet-fit
FR=${OMNI_FRAMES_LIST:-$(seq -s, $FRA $FRB)}; export OMNI_FRAMES=$FR; NEED=$(echo "$FR" | tr ',' '\n' | wc -l)
nfr() { ls "$OUT"/f_*.png 2>/dev/null | grep -v tmp | wc -l; }
for a in $(seq 1 12); do
  [ "$(nfr)" -ge $NEED ] && { echo "all frames present"; break; }
  LOG="$WORK/logs/pez_R1_${B}_$(basename $OUT)_attempt$a.log"
  taskset -c 0-3 "$PY" -u render_fleet_omniverse_t360_T45.py $SPP $W $H 0 960 "$OUT" < /dev/null > "$LOG" 2>&1 &
  pid=$!
  for s in $(seq 1 90); do sleep 1; [ -s "$LOG" ] && break; done
  [ -s "$LOG" ] || { echo "attempt $a: start-up hung, killing own pid $pid"; kill $pid; sleep 1; kill -9 $pid 2>/dev/null; }
  wait $pid; rc=$?; echo "$(date +%F_%T) attempt $a rc=$rc frames=$(nfr)/$NEED"
  [ $rc -eq 0 ] && break
done
echo "$(date +%F_%T) finished frames=$(nfr)/$NEED"
