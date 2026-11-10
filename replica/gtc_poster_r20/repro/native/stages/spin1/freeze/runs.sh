#!/bin/bash
# FINAL: design eclipse = 600-km grid max (ECLIPSE_600KM.json); mean-eclipse and 550-km t590 max (21.66 min) kept as sensitivities.
PY=${PY:-python3}
E=$($PY -c 'import json;e=json.load(open("../../orbit/ECLIPSE_600KM.json"));print(e["max_shadow_min"],e["mean_shadow_min_when_eclipsed"])')
EMAX=$(echo $E | cut -d' ' -f1); EMEAN=$(echo $E | cut -d' ' -f2)
run(){ $PY nbf_spin1.py scen_$1.json "$2" out_$1_$3.json > log_$1_$3.txt 2>&1 & }
for t in J8 A4; do for s in table cold; do
 run ${t}_MPG40_${s} "{\"fluid\":\"MPG40\",\"ecl_min\":$EMAX,\"q_t\":40.0,\"q_h\":0.0,\"QLOSS\":500.0}" qt40
 run ${t}_water_${s} "{\"fluid\":\"water\",\"ecl_min\":$EMAX,\"q_t\":40.0,\"q_h\":0.0,\"QLOSS\":500.0}" qt40
done
 run ${t}_MPG40_cold "{\"fluid\":\"MPG40\",\"ecl_min\":$EMAX,\"q_t\":40.0,\"q_h\":0.0,\"QLOSS\":1500.0}" qt40_ql1500
 run ${t}_MPG40_cold "{\"fluid\":\"MPG40\",\"ecl_min\":$EMAX,\"q_t\":60.0,\"q_h\":0.0,\"QLOSS\":500.0}" qt60
 run ${t}_MPG40_table "{\"fluid\":\"MPG40\",\"ecl_min\":$EMEAN,\"q_t\":40.0,\"q_h\":0.0,\"QLOSS\":500.0}" qt40_emean
 run ${t}_MPG40_cold "{\"fluid\":\"MPG40\",\"ecl_min\":21.66,\"q_t\":40.0,\"q_h\":0.0,\"QLOSS\":500.0}" qt40_e550max
done
wait
