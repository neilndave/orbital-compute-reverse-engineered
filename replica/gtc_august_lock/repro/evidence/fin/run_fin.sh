#!/bin/bash
set -eu
cd ${WORK:?set WORK to the unpacked evidence dir}/fin
PY=${PY:-python3}
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -u make_fin_dataset.py > labels.log 2>&1
docker run --rm --gpus all -v "$PWD:/study" -w /study nvcr.io/nvidia/physicsnemo/physicsnemo:26.08 python evaluate_checkpoint.py > checkpoint.log 2>&1
export AL_TABLES=$("$PY" -c 'import json;s=json.load(open("SELECTED.json"));print(json.dumps([["AL6061_V3_AUG",167.,s["half_fin_m"],s["fin_thickness_m"]]]))')
WARP_DEVICE=cuda:0 "$PY" -u fin_al_benchmark.py table > table_GPU.log 2>&1
cp results/table_AL6061_V3_AUG.json TABLE_RERUN_GPU.json
WARP_DEVICE=cpu taskset -c 5 "$PY" -u fin_al_benchmark.py table > table_CPU.log 2>&1
cp results/table_AL6061_V3_AUG.json TABLE_RERUN_CPU.json
echo FIN_SUITE_COMPLETE
