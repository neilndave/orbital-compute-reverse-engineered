#!/bin/bash
# usage: cls.sh <sat> [t1]  : yokehold (final env) + own-sat fine scan 0.02 s for one class representative
S=$1; T1=${2:-75}
cd /tmp/t442/ov_Aug/experiments/poster; source ./fleet_replica_env.sh >/dev/null; export RTS_TAG=_T45 FLEET_ODD_SPEED=2.6 FLEET_TAU_W=16.6 FLEET_TAU_N0=29.6 NPROC=${NPROC:-2}
IN=${PLANIN:-/tmp/t442/pl/plan_c$S.json}
FLEET_STAGEPLAN=$IN python replica/gb10_render_replica/yokehold_plan.py $IN /tmp/t445/plan_c${S}_yh.json
python3 - <<P
import json
d=json.load(open('/tmp/t445/plan_c${S}_yh.json')); json.dump({str(k):d['$S'] for k in range(30)},open('/tmp/t445/plan_c${S}_all.json','w'))
P
bash /tmp/t441/fullscan2.sh /tmp/t442/ov_Aug /tmp/t445/plan_c${S}_all.json c$S $S 0 $T1 0.02
