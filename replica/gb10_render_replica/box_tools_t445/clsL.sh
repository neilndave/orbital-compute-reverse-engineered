#!/bin/bash
# usage: clsL.sh <sat> <planin> : yokehold(LATE aware) -> plan_c<S>_yh2.json, own-sat 0.02 s scan tau 0-75
S=$1; IN=$2
cd /tmp/t442/ov_Aug/experiments/poster; source ./fleet_replica_env.sh >/dev/null; export RTS_TAG=_T45 FLEET_ODD_SPEED=2.6 FLEET_TAU_W=16.6 FLEET_TAU_N0=29.6 NPROC=${NPROC:-2}
FLEET_STAGEPLAN=$IN python replica/gb10_render_replica/yokehold_plan.py $IN /tmp/t445/plan_c${S}_yh2.json || exit 1
python3 - <<P
import json
d=json.load(open('/tmp/t445/plan_c${S}_yh2.json')); json.dump({str(k):d['$S'] for k in range(30)},open('/tmp/t445/plan_c${S}_all2.json','w'))
P
bash /tmp/t441/fullscan2.sh /tmp/t442/ov_Aug /tmp/t445/plan_c${S}_all2.json c${S}L $S 0 75 0.02
