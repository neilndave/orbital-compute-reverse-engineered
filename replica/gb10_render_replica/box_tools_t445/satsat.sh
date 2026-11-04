#!/bin/bash
cd /tmp/t442/ov_Aug/experiments/poster; source ./fleet_replica_env.sh >/dev/null; export RTS_TAG=_T45 FLEET_ODD_SPEED=2.6 FLEET_TAU_W=16.6 FLEET_TAU_N0=29.6
export FLEET_STAGEPLAN=${1:-/tmp/t445/stage_plan_Aug30_t445.json}
python fleet_clearance_t445.py
