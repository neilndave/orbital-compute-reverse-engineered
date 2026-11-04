# usage: fullscan2.sh <overlay> <plan.json> <tag> [sats] [t0] [t1] [dt]
cd $1/experiments/poster; source ./fleet_replica_env.sh >/dev/null; export RTS_TAG=_T45 FLEET_ODD_SPEED=2.6 NPROC=${NPROC:-8}
FLEET_STAGEPLAN=$2 SCAN_OUT=/tmp/t441/fs_$3.npz python /tmp/t441/scanplan.py ${4:-0} ${5:-0} ${6:-75} ${7:-0.02} 2>&1 | cut -c1-600
