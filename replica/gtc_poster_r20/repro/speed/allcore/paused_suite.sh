#!/bin/bash
# Clean timing window: pause the render process group, run all timings, always resume (trap).
cd "$(dirname "$0")"; PY=${PY:?}; PG=${PG:?}
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD:$PWD/..
D=paused; mkdir -p $D
resume(){ kill -CONT -$PG 2>/dev/null; echo "RESUMED $(date '+%F %T %Z')" >> $D/WINDOW.txt; }
trap resume EXIT INT TERM HUP
ps -o pid,pgid,stat,args -g $PG | cut -c1-120 > $D/PG_BEFORE.txt
kill -STOP -$PG && echo "PAUSED $(date '+%F %T %Z')" > $D/WINDOW.txt
sleep 3; ps -o pid,stat -g $PG > $D/PG_PAUSED.txt; uptime > $D/LOAD_START.txt; nvidia-smi --query-gpu=utilization.gpu,clocks.sm --format=csv > $D/GPU_START.txt
ps -eo pid,pcpu,stat,args --sort=-pcpu --no-headers | head -8 | cut -c1-140 > $D/PS_START.txt
for r in 1 2 3; do for s in sweep mc; do
 "$PY" -u allcore_bench.py cuda:0 $s $D/GPU_${s}_$r.json > $D/GPU_${s}_$r.log 2>&1
 "$PY" -u allcore_bench.py allcore $s $D/ALLCORE_${s}_$r.json > $D/ALLCORE_${s}_$r.log 2>&1
done; done
for s in sweep mc; do "$PY" -u allcore_bench.py cpu $s $D/CPU1_${s}.json > $D/CPU1_${s}.log 2>&1; done
ps -eo pid,pcpu,stat,args --sort=-pcpu --no-headers | head -8 | cut -c1-140 > $D/PS_END.txt; uptime > $D/LOAD_END.txt
echo PAUSED_SUITE_DONE
