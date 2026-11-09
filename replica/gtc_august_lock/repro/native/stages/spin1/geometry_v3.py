"""Explicit v3 geometry proposal, separate from preserved battery-only v3a."""
import os
import json,math,copy,os
from pathlib import Path
ROOT=Path(os.environ.get("GTCFC_ROOT",os.environ["GTCFC_ROOT"]+""))
CFG=json.load(open(ROOT/"CONFIG_V3.json"))
BASE_PANEL_FLUID=None
def apply(mo,nm):
 global BASE_PANEL_FLUID
 import sys
 M=sys.modules['model_t549']
 if BASE_PANEL_FLUID is None: BASE_PANEL_FLUID=M.C13.PANEL_FLUID
 M.C13.PANEL_FLUID=BASE_PANEL_FLUID
 if nm=='August' and CFG.get('august_radiator'):
  a=CFG['august_radiator'];mo.plan=a['panel_width_m']*a['panel_length_m'];mo.v3_fin=a
  M.C13.PANEL_FLUID=a['NT']*math.pi*a['tube_ID_m']**2/4*a['panel_length_m']*978.
 n=CFG.get("radiator_panels",{}).get(nm,mo.npan0)
 mo.A0=mo.plan*n;mo.npan0=n;mo.ncol0=math.ceil(n/10)
 return mo
def layout(g,n):
 g=copy.deepcopy(g);nc=math.ceil(n/10);w0=math.ceil(nc/2);b=n//nc;extra=n-b*nc
 g["panels_per_column"]=[b+(j<extra) for j in range(nc)];g["wing0_cols"]=w0
 g["wing_width_mm"]=w0*(g["panel_W_mm"]+g["gap_mm"])-g["gap_mm"]
 g["source"]="v3 proposed radiator count; same strip width, panel length and max ten panels/column; wider deployed radiator wing"
 return g
