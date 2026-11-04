#!/bin/bash
# usage: cls_r2.sh <Aug|Jun> : yokehold + own-sat 0.02 s scan (tau 0-75) of the single-sat R2 plan
B=$1; OV=/tmp/t445/ov1_$B; source /tmp/t445/work/wfold_timing_$B.env; export FLEET_TAU_W FLEET_TAU_N0 NPROC=${NPROC:-2}
IN=${PLANIN:-/tmp/t445/r2/plan_r2_$B.json}
cd $OV/experiments/poster; source ./fleet_replica_env.sh >/dev/null; export RTS_TAG=_T45 FLEET_ODD_SPEED=2.6 FLEET_TAU_W FLEET_TAU_N0
FLEET_STAGEPLAN=$IN python replica/gb10_render_replica/yokehold_plan.py $IN /tmp/t445/r2/plan_r2_${B}${SUF}_yh.json || exit 1
bash /tmp/t441/fullscan2.sh $OV /tmp/t445/r2/plan_r2_${B}${SUF}_yh.json r2$B$SUF 0 0 75 0.02
