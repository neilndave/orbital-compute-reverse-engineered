#!/bin/bash
# Newton replica deployment job: for each replica point, the repo's 21-hinge Z-fold Newton 1.7.0 Featherstone vs Warp cross-check (motor tdep 300 s, dt 1 ms, tend 330 s, latch K 5e5 zeta 0.3)
# -- the same case as t410 -- on an overlay tree whose input JSONs hold the replica array mass / area / wing length. Scripts in each overlay are unchanged copies of the repo's.
# usage: run_newton.sh [id ...]   default order: J8_C1 J8_C2 A4_C1 A4_C2 J8_MID A4_MID.   Resumable (a case with a DONE file is skipped; a failed case leaves a FAILED file and is retried next launch). Stops between cases if ../PAUSE exists.
# Runs inside ~/gb10_work only; never kills anything.  GPU 5 s samples are logged per case.
B=$(cd "$(dirname "$0")/.." && pwd); N=$B/newton; PY=${NEWTON_PY:-$HOME/rack_two_skies/venv_newton/bin/python}; OUT=$B/results/newton; mkdir -p "$OUT" "$B/logs"
IDS=("$@"); [ ${#IDS[@]} -eq 0 ] && IDS=(J8_C1 J8_C2 A4_C1 A4_C2 J8_MID A4_MID)
pt() { TZ=America/Los_Angeles date '+%F %T'; }; say() { echo "$(pt) PT  [newton] $*" | tee -a "$OUT/job.log"; }
for ID in "${IDS[@]}"; do
  [ -f "$B/PAUSE" ] && { say "PAUSE file present: stopping before $ID"; exit 0; }
  [ -f "$OUT/$ID.DONE" ] && { say "$ID already DONE, skipping"; continue; }
  OV=$N/overlay_$ID; [ -d "$OV" ] || { say "no overlay $OV"; exit 2; }
  G0=$(date +%s); say "start $ID (motor tdep 300 s, dt 1 ms, tend 330 s, latch K 5e5 zeta 0.3)"
  nvidia-smi --query-gpu=timestamp,temperature.gpu,utilization.gpu,power.draw,clocks.sm,clocks.mem,memory.used --format=csv,noheader,nounits -l 5 > "$OUT/gpu_samples_$ID.csv" 2>/dev/null & SAMP=$!
  ( cd "$OV/experiments/phase2" && RTS_TAG=_T45 "$PY" -u newton_xcheck_T45.py motor 300 1e-3 --tend 330 --tag _gtc_$ID ) > "$OUT/run_$ID.log" 2>&1; RC=$?
  G1=$(date +%s); kill $SAMP 2>/dev/null; say "$ID rc=$RC wall=$((G1-G0)) s"
  for f in "$OV"/results/phase2_T45/xcheck_*_gtc_$ID.*; do [ -f "$f" ] && cp -p "$f" "$OUT/"; done
  "$PY" - "$OUT" "$ID" "$RC" "$G0" "$G1" <<'PY'
import sys, json, glob
out, ID, rc, g0, g1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
S = dict(id=ID, rc=rc, wall_s=g1 - g0)
try: S["xcheck"] = json.load(open(glob.glob(out + "/xcheck_motor_tdep300*_gtc_%s.json" % ID)[0]))
except Exception as e: S["xcheck_error"] = str(e)
json.dump(S, open(out + "/summary_%s.json" % ID, "w"), indent=1)
PY
  if [ $RC -eq 0 ]; then echo "$(pt) PT rc=0" > "$OUT/$ID.DONE"; else echo "$(pt) PT rc=$RC" > "$OUT/$ID.FAILED"; say "$ID FAILED rc=$RC, see run_$ID.log; continuing with the next case"; fi
done
say "all requested cases processed"
