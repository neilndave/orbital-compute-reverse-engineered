#!/bin/bash
set -eu
cd ${WORK:?set WORK to the unpacked evidence dir}
PY=${PY:-python3}
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 LOCK_KLAT=5000 LOCK_DAMP_CAP=1 LOCK_SETTLE_SECONDS=30 LOCK_ROOT_SECONDS=60 LOCK_MAIN_SECONDS=600
for d in control corrected; do
 (cd newton/$d/lock/dynamics; "$PY" -u run_final_newton.py radiator 660 .01 > radiator.log 2>&1; "$PY" -u run_warp_convergence.py radiator 660 .005 > half_step.log 2>&1)
 echo "$d RADIATOR_COMPLETE"
done
(cd newton/corrected/lock/dynamics; "$PY" -u check_actual_traces.py > clearance.log 2>&1)
echo NEWTON_SUITE_COMPLETE
