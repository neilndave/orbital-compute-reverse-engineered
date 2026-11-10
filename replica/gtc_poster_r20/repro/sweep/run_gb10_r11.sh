#!/bin/bash
# GB10 run for r11: frozen-control sweep (CUDA) + corrected r11 sweep/MC/Tape on CUDA and one X925 core, then 3x controlled benchmark.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); OUT=${OUT:-$HERE/../../gb10_out}; export PY=${PY:-python3} CPU_CORE=${CPU_CORE:-5}
mkdir -p "$OUT"; nvidia-smi > "$OUT/GPU_BEFORE.txt"; lscpu -e > "$OUT/CPU_TOPOLOGY.txt"
"$HERE/run_sweep_case.sh" "$HERE/FROZEN_CONTROL_SWEEP_INPUTS.json" "$OUT/frozen_control" cuda:0 GB10_GPU sweep
"$HERE/run_sweep_case.sh" "$HERE/SWEEP_INPUTS.json" "$OUT/r11" cuda:0 GB10_GPU sweep mc opt
"$HERE/run_sweep_case.sh" "$HERE/SWEEP_INPUTS.json" "$OUT/r11" cpu GB10_CPU sweep mc
"$HERE/run_sweep_case.sh" "$HERE/SWEEP_INPUTS.json" "$OUT/r11" cuda:0 BENCH bench
nvidia-smi > "$OUT/GPU_AFTER.txt"; echo SUITE_COMPLETE
