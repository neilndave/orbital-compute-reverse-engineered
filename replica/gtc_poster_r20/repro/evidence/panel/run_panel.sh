#!/bin/bash
set -eu
cd ${WORK:?set WORK to the unpacked evidence dir}/panel/modal_convergence
run_case() {
 d=$1
 python3 - "$d" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])/'panel.inp';s=p.read_text().replace('*FREQUENCY\n','*FREQUENCY,SOLVER=MATRIXSTORAGE\n');a=s.index('*NODE PRINT,NSET=NSHEET');b=s.index('*END STEP',a);s=s[:a]+s[b:];p.write_text(s)
PY
 docker run --rm -e OMP_NUM_THREADS=4 -v "$PWD/$d:/w" -w /w rack2skies-ccx:2.21 -i panel > $d/solver.log 2>&1
 docker run --rm -e OMP_NUM_THREADS=4 -e OPENBLAS_NUM_THREADS=4 -e ORDER=MMD_AT_PLUS_A -v "$PWD:/r" -w /r nvcr.io/nvidia/physicsnemo/physicsnemo:26.08 python eig_scipy.py "$d" 12 > $d/eig.log 2>&1
 echo "$d COMPLETE"
}
run_case PAD20 & p1=$!
run_case PAD30 & p2=$!
run_case PAD40 & p3=$!
wait $p1; wait $p2; wait $p3
echo PANEL_SUITE_COMPLETE
