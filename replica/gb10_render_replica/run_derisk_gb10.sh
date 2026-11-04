#!/usr/bin/env bash
# PRE-RENDER DERISK GATE, GPU parts.  PREPARED, NOT LAUNCHED (t438).  the author runs this on the GB10.
# One Isaac/Newton GPU job at a time (repo rule: never two Isaac jobs on one GPU).  Check `nvidia-smi` for other jobs first.
# usage: REPO=<repo root on the GB10> bash run_derisk_gb10.sh [newton|preview|all]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO=${REPO:?set REPO to the repo root}; WORK=${WORK:-$HERE/work}; MODE=${1:-newton}
PY=${PY:-python}                                   # the repo's Newton/Isaac python env
mkdir -p "$WORK"
for B in Jun Aug; do [ -d "$WORK/ov_$B" ] || bash "$HERE/make_overlay.sh" $B "$REPO" "$WORK/ov_$B"; done
if [ "$MODE" = newton ] || [ "$MODE" = all ]; then
  # (a) Newton second-stage fold chain: n=5 (Jun) and n=6 (Aug), hinge-stiffness scan W0 (fold time ~ 1/W0; W0~0.17 ~ 14 s).  ASSUMED analog of repo run_array.py, UNTESTED (no Newton on the box).
  for spec in "Jun 5" "Aug 6"; do set -- $spec
    for W0 in 0.10 0.17 0.25; do
      ( cd "$WORK/ov_$1" && RTS_TAG=_T45 RUN_ARRAY_DIR="$WORK/ov_$1/experiments/newton_array" $PY "$HERE/newton_wfold/run_wfold.py" $2 $W0 60 1e-3 ) 2>&1 | tee "$WORK/newton_wfold_$1_n$2_w$W0.log"
    done
  done
  $PY "$HERE/check_gate.py" "$WORK" || true
fi
if [ "$MODE" = preview ] || [ "$MODE" = all ]; then
  # (d) ONLY after the adapter's open items (README section 3) are closed and `check_gate.py` shows (a)-(c) pass.
  echo "preview (d) is gated: run  bash $HERE/run_preview_render.sh Jun  (and Aug)  after the adapter is complete"; fi
