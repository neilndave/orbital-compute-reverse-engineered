#!/bin/bash
# GTC final candidate: full pipeline from the vendored inputs. Run from a clean copy at /tmp/gtcfc_root (canonical root; scripts use absolute paths under it).
set -euo pipefail
export GTCFC_ROOT=/tmp/gtcfc_root; cd $GTCFC_ROOT
export PY=${PY:-python3}; export PYTHONDONTWRITEBYTECODE=1; export PYTHONHASHSEED=0; export PYTHONPYCACHEPREFIX=$GTCFC_ROOT/.nopycache   # never read stale __pycache__ next to sources
export PYTHONPATH=$GTCFC_ROOT/tools/trace:$GTCFC_ROOT/inputs/repo/src:$GTCFC_ROOT/stages/spin1
mkdir -p trace; rm -f trace/*.jsonl
st(){ export GTCFC_STAGE=$1; shift; ( cd "$1" && shift && "$@" ) ; }
st s00_t600_screen       stages/t600       $PY baseline_plus_deletions.py > logs_s00.txt
st s01_baseline_freeze   stages/baseline   $PY freeze_scoped_baseline.py > logs_s01.txt
st s02_eclipse_600km     stages/orbit      $PY eclipse_600km.py > logs_s02.txt
st s03_power             stages/spin1      $PY power_spin1.py > logs_s03.txt
st s04_mmod              stages/spin1      $PY mmod_spin1.py > logs_s04.txt
st s05_mmod_grid         stages/spin1      $PY mmod_grid_spin1.py > logs_s05.txt
st s06_mmod_trunk        stages/spin1      $PY mmod_trunk_alloc_spin1.py MMOD_TRUNK_ALLOC_SPIN1.json > logs_s06.txt
st s07_thermal_inputs    stages/spin1      $PY gen_thermal_inputs_spin1.py > logs_s07.txt
st s08_thermal           stages/spin1      $PY thermal_spin1.py THERMAL_INPUTS_SPIN1.json THERMAL_SPIN1.json > logs_s08.txt
st s09_freeze_scen       stages/spin1/freeze $PY build_scen.py > logs_s09.txt
st s10_freeze_transients stages/spin1/freeze ./runs.sh
st s11_water_keepwarm    stages/spin1/freeze $PY water_keepwarm.py > logs_s11.txt
st s12_freeze_mass       stages/spin1/freeze $PY freeze_mass_spin1.py > logs_s12.txt
st s13_assemble_spin1    stages/spin1      $PY assemble_spin1.py > logs_s13.txt
st s14_build_final       final             $PY build_final.py > logs_s14.txt
st s15_verify_arith      final             $PY verify_arith.py > logs_s15.txt
unset GTCFC_STAGE
( cd final && $PY canonical.py )
