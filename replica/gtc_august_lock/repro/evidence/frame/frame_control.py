"""Scope t771 control reproduction: inherited assumed-box full-mass beam screen, not internal packaging validation."""
from pathlib import Path
import types,json,os
D=Path(__file__).resolve().parent
src=Path(__file__).resolve().parent/'rackgen.py';R=types.ModuleType('frame_control');exec(compile(src.read_text(),str(src),'exec'),R.__dict__)
os.environ['OMP_NUM_THREADS']='2'
d=R.design(H=.9372146118721462,n_tray=4,m_equip=0,post=(.12,.12,.003),rail=(.08,.06,.002),xrail=(.08,.08,.002),brace=(.008,.001))
f=R.build(d,1)['frame_kg'];d['m_equip']=640.38-f
wd=D/'frame_control_n16';wd.mkdir(exist_ok=True)
r=R.analyse(d,16,str(wd),nmodes=8,buckle=True)
r['scope']='CONTROL REPRODUCTION ONLY: t771 assumed box/allocation; inherited rigid4level frame, equipment smeared on side rails, not the separate67module trial. This cannot rescue the failed MPC mass-location calculation.'
r['frame_design']=d;r['frame_plus25pct_fittings_assumption_kg']=f*1.25;r['remaining_electronics_if25pct_fittings_kg']=640.38-f*1.25
(D/'FRAME_CONTROL_REPRODUCTION.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True)
