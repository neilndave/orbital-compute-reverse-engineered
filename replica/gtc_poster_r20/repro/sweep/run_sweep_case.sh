#!/bin/bash
# usage: run_sweep_case.sh <inputs.json> <workdir> <device cpu|cuda:0> <label> [stages: sweep mc opt]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); IN=$1; W=$2; DEV=$3; LABEL=$4; shift 4; STAGES=${*:-sweep}
PY=${PY:-python3}
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$W"; cp "$HERE"/{gpu_core.py,run_tools.py,run_benchmark.py,SURROGATE_TABLE.npz} "$W"/; cp "$IN" "$W"/SWEEP_INPUTS.json
cd "$W"
PIN=""; if [ "$DEV" = cpu ] && [ -n "${CPU_CORE:-}" ]; then PIN="taskset -c $CPU_CORE"; fi
for s in $STAGES; do
 case $s in
  sweep) $PIN $PY -u run_tools.py sweep --device $DEV --label $LABEL > sweep_$LABEL.log 2>&1 ;;
  mc)    [ -f "${MC_DESIGN:-SELECTED.json}" ] || $PY -c "import json;json.dump(json.load(open('SWEEP_$LABEL.json'))['selected'],open('SELECTED.json','w'),indent=2);open('SELECTED.json','a').write('\\n')"
         $PIN $PY -u run_tools.py mc --device $DEV --label $LABEL --design ${MC_DESIGN:-SELECTED.json} > mc_$LABEL.log 2>&1 ;;
  opt)   $PIN $PY -u run_tools.py opt --device $DEV --label $LABEL > opt_$LABEL.log 2>&1 ;;
  bench) for rep in 1 2 3; do $PY -u run_benchmark.py sweep --device cuda:0 --label GPU_$rep > benchmark_GPU_$rep.log 2>&1; taskset -c ${CPU_CORE:-5} $PY -u run_benchmark.py sweep --device cpu --label CPU_$rep > benchmark_CPU_$rep.log 2>&1; done ;;
 esac
done
echo "CASE_COMPLETE $LABEL $STAGES"
