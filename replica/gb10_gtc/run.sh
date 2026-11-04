#!/bin/bash
# GTC replica bundle launcher (GB10 desktop).  Everything stays inside this folder (copy it to ~/gb10_work/gtc_replica).  No sudo.  Never kills anything.
# usage: ./run.sh <mode>   modes:  smoke | thermal | newton | newton_must | all | status | pause | resume
#   smoke        ~1 min tiny thermal run on CPU, checks the install       thermal  full replica thermal MC + area sizing (2 builds, fin tables cached)
#   newton       all 6 Newton cases (sequential)                          newton_must  the 4 must-have cases (C1 and C2, Jun and Aug)
#   all          thermal, then newton_must                                 status / pause / resume  as named
# Set FORCE=1 to launch even if another GPU process is running (default: refuse, so any render are never disturbed).
B=$(cd "$(dirname "$0")" && pwd); MODE=${1:-status}; mkdir -p "$B/logs" "$B/results"
RT=$HOME/rack_two_skies; PYR=${AI1_PY:-$RT/venv_repo/bin/python}; export NEWTON_PY=${NEWTON_PY:-$RT/venv_newton/bin/python}
export GTC_BUILDS_JSON=$B/params/thermal_builds.json
pt() { TZ=America/Los_Angeles date '+%F %T'; }
gpu_busy() { nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader 2>/dev/null | grep -v "^$"; }
guard() { if [ -z "$FORCE" ] && [ -n "$(gpu_busy)" ]; then echo "GPU is in use by:"; gpu_busy; echo "Refusing to start (set FORCE=1 to override, or wait)."; exit 3; fi; }
case "$MODE" in
  smoke) cd "$B/thermal" && "$PYR" -u runner.py --profile tiny --device cpu --root "$B/smoke" --phases G0,G1,G2,G3,G4 2>&1 | tail -5; ;;
  thermal) guard; rm -f "$B/PAUSE" "$B/thermal/PAUSE"; LOG="$B/logs/thermal_$(TZ=America/Los_Angeles date +%Y%m%d_%H%M%S).log"
    for a in 1 2 3; do DEV=auto; [ $a -ge 3 ] && DEV=cpu; echo "$(pt) thermal attempt $a device=$DEV" >> "$LOG"
      "$PYR" -u "$B/thermal/runner.py" --profile full --device $DEV --root "$B/thermal" --phases G0,G2,G3,G4 >> "$LOG" 2>&1 && break; sleep 20; done; echo "$(pt) thermal done (see $LOG)";;
  newton) guard; rm -f "$B/PAUSE" "$B/thermal/PAUSE"; "$B/newton/run_newton.sh";;
  newton_must) guard; rm -f "$B/PAUSE" "$B/thermal/PAUSE"; "$B/newton/run_newton.sh" J8_C1 J8_C2 A4_C1 A4_C2;;
  all) "$0" thermal && "$0" newton_must;;
  status) echo "now: $(pt) PT"; [ -f "$B/PAUSE" ] && echo "PAUSE file: PRESENT"; pgrep -af "[g]tc_replica.*(runner.py|run_newton|newton_xcheck)" | cut -c1-160 || echo "no replica process";
    [ -f "$B/thermal/state/status.json" ] && { echo "--- thermal:"; cat "$B/thermal/state/status.json"; echo; }
    echo "--- newton cases:"; ls "$B/results/newton/"*.DONE 2>/dev/null | xargs -rn1 basename; tail -3 "$B/results/newton/job.log" 2>/dev/null
    echo "--- GPU:"; nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,power.draw,memory.used --format=csv,noheader; echo "--- other GPU procs:"; gpu_busy | cut -c1-120;;
  pause) touch "$B/PAUSE" "$B/thermal/PAUSE"; echo "PAUSE set $(pt) PT: thermal stops at the next chunk (seconds); newton stops after the current case (up to ~45 min) -- finished work is kept. ./run.sh resume to continue";;
  resume) rm -f "$B/PAUSE" "$B/thermal/PAUSE"; setsid nohup "$0" all > "$B/logs/resume_$(TZ=America/Los_Angeles date +%Y%m%d_%H%M%S).out" 2>&1 < /dev/null & echo "relaunched detached (thermal chunks and newton cases already done are skipped)";;
  *) echo "unknown mode $MODE"; sed -n 2,8p "$0"; exit 1;;
esac
