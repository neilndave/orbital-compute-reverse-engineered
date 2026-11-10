#!/bin/bash
# r11 end-to-end replication on any Linux x86_64/aarch64 box (CPU only). GB10 CUDA results are committed in gb10_out/
# (re-run them with sweep/run_gb10_r11.sh on a GB10); this script re-derives everything else and checks box-vs-GB10 identity.
# Env: PY_NATIVE (python with native_requirements.txt). The r11 poster was removed; the poster is built in ../../gtc_poster_r20/repro.
set -euo pipefail
export R11_ROOT=$(cd "$(dirname "$0")" && pwd); cd "$R11_ROOT"
PYN=${PY_NATIVE:-python3}
echo "[1/6] native corrected-MPG40 chain";            PY=$PYN native/run_r11_native.sh
echo "[2/6] sweep inputs from native outputs";       (cd sweep && GTCFC_ROOT=$R11_ROOT/native PYTHONDONTWRITEBYTECODE=1 $PYN make_sweep_inputs.py)
echo "[3/6] box CPU frozen-control sweep";           PY=$PYN sweep/run_sweep_case.sh sweep/FROZEN_CONTROL_SWEEP_INPUTS.json work/box_frozen_control cpu BOX_CPU sweep
echo "[4/6] box CPU r11 sweep + scenarios";          PY=$PYN sweep/run_sweep_case.sh sweep/SWEEP_INPUTS.json work/box_r11 cpu BOX_CPU sweep mc
echo "[5/6] device thermal sensitivity";             $PYN evidence/device/device_thermal_recheck.py > /dev/null
echo "[6/6] poster numbers + r10/r11 trace";         $PYN numbers/derive_numbers.py gb10_out && $PYN numbers/make_number_trace.py
$PYN tools/candidate_hash.py
