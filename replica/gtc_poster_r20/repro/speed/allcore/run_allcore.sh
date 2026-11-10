#!/bin/bash
# order: reference outputs (GPU, 1-core CPU) once, then 3 reps of all-core for each workload, interleaved with GPU reps
set -eu
cd "$(dirname "$0")"; PY=${PY:?}
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD:$PWD/..
mkdir -p out; lscpu > out/CPU_TOPOLOGY.txt; nproc > out/NPROC.txt; uptime > out/LOAD_BEFORE.txt; nvidia-smi > out/GPU_BEFORE.txt 2>&1; ps aux --sort=-%cpu | head -15 > out/PS_BEFORE.txt
for s in sweep mc; do
 "$PY" -u allcore_bench.py cuda:0 $s out/REF_GPU_$s.json
 "$PY" -u allcore_bench.py cpu $s out/REF_CPU1_$s.json
done
for r in 1 2 3; do for s in sweep mc; do
 uptime > out/LOAD_${s}_$r.txt
 "$PY" -u allcore_bench.py allcore $s out/ALLCORE_${s}_$r.json
done; done
ps aux --sort=-%cpu | head -15 > out/PS_AFTER.txt; uptime > out/LOAD_AFTER.txt
echo ALLCORE_DONE
