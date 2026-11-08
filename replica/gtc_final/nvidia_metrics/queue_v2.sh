#!/bin/bash
# GB10 serial queue after bench_v2 run 1: validation, SciPy-reference rerun (tight Newton), end-to-end timings, then marker.
cd <gb10-work>/gtc_final_v2_metrics/nvidia_metrics; PYV=<gb10-work>/venv_repo/bin/python
while pgrep -f "bench_v2.py BENCH_GB10.json" > /dev/null; do sleep 20; done
echo "bench1 done $(date)" >> queue.log
$PYV validate_v2.py VALIDATE_GB10.json > validate_gb10.log 2>&1; echo "validate rc $? $(date)" >> queue.log
BENCH_ONLY=scipy HOST_LABEL=GB10 V2_CFG_DIR=cfg $PYV bench_v2.py BENCH_GB10_SCIPY.json > bench_gb10_scipy.log 2>&1; echo "scipy rc $? $(date)" >> queue.log
PY=$PYV ./e2e_v2.sh /tmp/v2_pipeline.tgz E2E_GB10 gpu > e2e_gb10.out 2>&1; echo "e2e rc $? $(date)" >> queue.log
echo "GTC final v2 benchmark/timing runs finished $(date '+%F %T %Z'); GPU free for the surrogate worker." > <gb10-home>/gtc_final_v2_bench_DONE
