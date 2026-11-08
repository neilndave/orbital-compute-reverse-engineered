#!/bin/bash
# End-to-end timings on one machine for the v2 baseline (run AFTER bench_v2/validate_v2; nothing else heavy running).
#  E1: full pipeline s00-s15 from a clean copy at /tmp/gtcv2_root (CPU: numpy/scipy/CoolProp), 3 repeats, wall each + canonical sha.
#  E2: production Warp fin table AL6061_L26_t0p225 (585 fp64 solves, nx 320 x ny 8): GPU (cuda:0) and CPU (Warp CPU backend, CUDA hidden), max |d eta| vs vendored table.
#  E3: GB10 parity kernel (gb10_final_parity.py) wall incl. Warp init, 3 repeats (GPU only).
# usage: PY=python e2e_v2.sh <pipeline_tgz> <outdir> [gpu]
set -u; PY=${PY:-python3}; TGZ=$1; OUT=$2; GPU=${3:-}; mkdir -p $OUT; OUT=$(cd $OUT && pwd); HERE=$(cd $(dirname $0) && pwd)
el(){ $PY -c "import sys;print(round(float(sys.argv[2])-float(sys.argv[1]),3))" $1 $2; }
log(){ echo "$@" | tee -a $OUT/e2e.log; }
log "host_arch $(uname -m) python $($PY --version 2>&1) start $(date '+%F %T %Z')"
for r in 1 2 3; do
  rm -rf /tmp/gtcv2_root /tmp/v2e && mkdir /tmp/v2e && tar xzf $TGZ -C /tmp/v2e && mv /tmp/v2e/pipeline /tmp/gtcv2_root
  t0=$(date +%s.%N); (cd /tmp/gtcv2_root && PY=$PY ./run_pipeline.sh > $OUT/pipeline_run$r.log 2>&1); rc=$?; t1=$(date +%s.%N)
  log "E1 run $r rc $rc wall_s $(el $t0 $t1) $(tail -1 $OUT/pipeline_run$r.log)"
done
if [ -n "$GPU" ]; then
  for r in 1 2 3; do t0=$(date +%s.%N); (cd /tmp/gtcv2_root/final && $PY gb10_final_parity.py > $OUT/parity_run$r.log 2>&1); t1=$(date +%s.%N); log "E3 run $r wall_s $(el $t0 $t1) $(tail -1 $OUT/parity_run$r.log | cut -c1-200)"; done
fi
FD=/tmp/v2e_fin; rm -rf $FD; mkdir -p $FD; cp /tmp/gtcv2_root/inputs/ai1_replica/gb10_final_al/fin_al.py /tmp/gtcv2_root/inputs/ai1_replica/gb10_final_al/warp_fin_ref.py $FD/ 2>/dev/null || cp $HERE/warp_fin_ref.py $FD/
[ -f $FD/warp_fin_ref.py ] || cp $HERE/warp_fin_ref.py $FD/
export AL_TABLES='[["AL6061_L26_t0p225",167.0,0.026,0.000225]]'
for D in ${GPU:+gpu} cpu; do
  if [ $D = cpu ]; then export CUDA_VISIBLE_DEVICES=""; else unset CUDA_VISIBLE_DEVICES; fi
  t0=$(date +%s.%N); (cd $FD && $PY fin_al.py table > $OUT/table_$D.log 2>&1); t1=$(date +%s.%N); cp $FD/results/table_AL6061_L26_t0p225.json $OUT/table_$D.json
  log "E2 $D wall_s $(el $t0 $t1) $($PY -c "import json,numpy as n;a=json.load(open('$OUT/table_$D.json'));b=json.load(open('/tmp/gtcv2_root/inputs/ai1_replica/gb10_final_al/table_AL6061_L26_t0p225.json'));print('device',a['device'],'solver_wall_s',round(a['wall_s'],2),'max_abs_d_eta_vs_vendored',float(n.max(n.abs(n.array(a['eta'])-n.array(b['eta'])))))")"
done
unset CUDA_VISIBLE_DEVICES; log "end $(date '+%F %T %Z')"
