#!/bin/bash
# r11 native corrected-MPG40 chain (deterministic). Re-runs every stage the MPG40 property fix touches:
# thermal -> freeze scenarios -> 6 August MPG40 transients -> water keep-warm -> freeze mass -> assemble -> final ledger -> fixed-array power check.
# Upstream stages s00-s07 (baseline, orbit/eclipse, frozen array geometry, MMOD, thermal inputs) are committed August inputs
# that the property fix does not touch; run ./run_pipeline.sh for those (note s03 power_spin1 would auto-resize the array; r11 keeps the August array fixed).
set -euo pipefail
export GTCFC_ROOT=${GTCFC_ROOT:-$(cd "$(dirname "$0")" && pwd)}; cd "$GTCFC_ROOT"
PY=${PY:-python3}
export AI1_ROOT=$GTCFC_ROOT/inputs/ai1_replica PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPYCACHEPREFIX=$GTCFC_ROOT/.nopycache
export PYTHONPATH=$GTCFC_ROOT/inputs/repo/src:$GTCFC_ROOT/stages/spin1
mkdir -p r11_out
L=$GTCFC_ROOT/r11_out
(cd stages/spin1 && $PY thermal_spin1.py THERMAL_INPUTS_SPIN1.json THERMAL_SPIN1.json > $L/thermal.log 2>&1)
(cd stages/spin1/freeze && $PY build_scen.py > $L/build_scen.log 2>&1)
EMAX=$($PY -c 'import json;print(json.load(open("stages/orbit/ECLIPSE_600KM.json"))["max_shadow_min"])')
EMEAN=$($PY -c 'import json;print(json.load(open("stages/orbit/ECLIPSE_600KM.json"))["mean_shadow_min_when_eclipsed"])')
run(){ (cd stages/spin1/freeze && $PY nbf_spin1.py scen_A4_MPG40_$1.json "{\"fluid\": \"MPG40\", \"ecl_min\": $3, \"q_t\": $4, \"q_h\": 0.0, \"QLOSS\": $5}" out_A4_MPG40_$1_$2.json > $L/transient_$1_$2.log 2>&1) & }
run cold qt40 $EMAX 40 500; run table qt40 $EMAX 40 500; run cold qt40_ql1500 $EMAX 40 1500; run cold qt60 $EMAX 60 500
wait
run table qt40_emean $EMEAN 40 500; run cold qt40_e550max 21.66 40 500
wait
for f in cold_qt40 table_qt40 cold_qt40_ql1500 cold_qt60 table_qt40_emean cold_qt40_e550max; do test -s stages/spin1/freeze/out_A4_MPG40_$f.json; done
(cd stages/spin1/freeze && $PY water_keepwarm.py > $L/water_keepwarm.log 2>&1)
(cd stages/spin1/freeze && $PY freeze_mass_spin1.py > $L/freeze_mass.log 2>&1)
(cd stages/spin1 && $PY assemble_spin1.py > $L/assemble.log 2>&1)
(cd final && $PY build_final.py > $L/build_final.log 2>&1)
$PY tools/r11/power_check.py > $L/power_check.log 2>&1
echo NATIVE_R11_COMPLETE
