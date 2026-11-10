#!/bin/bash
# r11 panel-2 speed suite on GB10. Usage: PY=<warp/newton python> CPU_CORE=5 ./run_speed_suite.sh
set -u
cd "$(dirname "$0")"; PY=${PY:?}; C=${CPU_CORE:-5}; IMG=nvcr.io/nvidia/physicsnemo/physicsnemo:26.08
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p results logs; nvidia-smi > results/GPU_BEFORE.txt 2>&1; lscpu > results/CPU_TOPOLOGY.txt
for r in 1 2 3; do
 "$PY" -u speed_bench.py scale --device cuda:0 --label GPU_$r > logs/scale_GPU_$r.log 2>&1
 taskset -c $C "$PY" -u speed_bench.py scale --device cpu --label CPU_$r > logs/scale_CPU_$r.log 2>&1
 "$PY" -u speed_bench.py mc --device cuda:0 --label GPU_$r > logs/mc_GPU_$r.log 2>&1
 taskset -c $C "$PY" -u speed_bench.py mc --device cpu --label CPU_$r > logs/mc_CPU_$r.log 2>&1
 docker run --rm --gpus all -v "$PWD:/study" -w /study $IMG python surrogate_bench.py cuda GPU_$r > logs/surr_GPU_$r.log 2>&1
 docker run --rm --gpus all --cpuset-cpus=$C -e OMP_NUM_THREADS=1 -v "$PWD:/study" -w /study $IMG python surrogate_bench.py cpu CPU_$r > logs/surr_CPU_$r.log 2>&1
done
echo CORE_STAGES_DONE
export AL_TABLES=$("$PY" -c 'import json;s=json.load(open("SELECTED.json"));print(json.dumps([["AL6061_V3_AUG",167.,s["half_fin_m"],s["fin_thickness_m"]]]))')
WARP_DEVICE=cuda:0 "$PY" -u fin_al_benchmark.py table --smoke > logs/fin_smoke_GPU.log 2>&1
WARP_DEVICE=cpu taskset -c $C "$PY" -u fin_al_benchmark.py table --smoke > logs/fin_smoke_CPU.log 2>&1
for r in 1 2 3; do
 for d in GPU CPU; do
  if [ $d = GPU ]; then WARP_DEVICE=cuda:0 "$PY" -u fin_al_benchmark.py table > logs/fin_${d}_$r.log 2>&1
  else WARP_DEVICE=cpu taskset -c $C "$PY" -u fin_al_benchmark.py table > logs/fin_${d}_$r.log 2>&1; fi
  cp results/table_AL6061_V3_AUG.json results/FIN_TABLE_${d}_$r.json
 done
done
echo FIN_DONE
export LOCK_KLAT=5000 LOCK_DAMP_CAP=1 LOCK_SETTLE_SECONDS=30 LOCK_ROOT_SECONDS=60 LOCK_MAIN_SECONDS=600
for r in 1 2 3; do
 (cd newton/corrected/lock/dynamics && "$PY" -u run_final_newton.py radiator 660 .01 > ../../../../logs/newton_GPU_$r.log 2>&1 && cp results_lock/radiator_t660_dt0.01_kl5000.json ../../../../results/NEWTON_GPU_$r.json)
done
nvidia-smi > results/GPU_AFTER.txt 2>&1
echo SPEED_SUITE_COMPLETE
