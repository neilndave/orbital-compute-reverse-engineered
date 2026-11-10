"""Constructive ideal stow audit with explicit resized radiator count, equipment volume and header depth.
All clearances are declared; no hinge/load qualification is implied. No density mass credit.
"""
import os
import json,math,os,sys,time
from pathlib import Path
import packing_core as P
R=Path(os.environ.get("GTCFC_ROOT",os.environ["GTCFC_ROOT"]+""));X=json.load(open(R/"final/GTC_FINAL_CANDIDATE.json"));cfg=json.load(open(R/"CONFIG_V3.json"))
# Baseline v3a evidence is vendored as an immutable comparison input.
A=json.load(open(R/"inputs/V3A_CONFIG.json"));PA=json.load(open(R/"inputs/V3A_PACKING.json"));out={"cases":{},"scope":__doc__,"passed":True};start=time.perf_counter()
for i,(nm,tag,ab) in enumerate([("June","J8","Jun"),("August","A4","Aug")]):
 if len(sys.argv)>1 and nm!=sys.argv[1]:continue
 f=X['fleets'][i];a=A['fleets'][i];pt=json.load(open(R/f'inputs/ai1_replica/gtc_params/point_{tag}_C1.json'));old=json.load(open(R/f'inputs/ai1_replica/checks_t454/c15_pack_{ab}_{77 if i==0 else 128}.json'));S=old['S'];N=int(f['radiator_panels']['value']);area=f['solar_area_m2']['value'];fold=S['fold']
 arr=[(f'array_{j}','array',(14/fold,area/(2*14*20),20*S['leaf']*fold)) for j in range(2)]
 VEQ0=(4.626-2.496)*.7*2.;power=pt['result']['P_IT_peak_kW'];veq=VEQ0*(.338+.662*power/188)*400/S['rho']
 L=f['ledger_kg']['value'];LA=a['ledger_kg']['value'];delta_nonarray_rad=sum(L.values())-sum(LA.values())-(L['array']-LA['array'])-(L['radiator']-LA['radiator'])
 added_eq_volume=max(0,delta_nonarray_rad)/S['rho'];veq+=added_eq_volume
 rh=pt['mass_lines_kg']['rack']/S['rho_rack']/(.6*1.2)
 centers={(z['X'],z['Y']) for z in PA['cases'][nm]['sequence']+old['res']['layers']['seq']}
 footprints=set(centers)
 for x,y in centers:
  for dx in [-.02,0,.02]:
   for dy in [-.02,0,.02]:
    xx,yy=round(x+dx,3),round(y+dy,3)
    if xx>=yy and math.hypot(xx,yy)/2<=P.radius(8):footprints.add((xx,yy))
 # Physical header OD max 21.6 mm; 23-mm stack pitch includes 1.4-mm clearance.
 pitch=float(cfg.get('radiator_stow_pitch_m',.023));outer=max(.003,pitch-.0014);best=None;trials=[]
 ns0=old['n_stacks'];ns_options=sorted({ns0,math.ceil(N/10),math.ceil(N/8),math.ceil(N/6)})
 for ex,ey in [(0.7,2.0),(1.0,1.4),(1.2,1.2)]:
  for ns in ns_options:
   b,e=divmod(N,ns);rad=[(f'rad_{j}','radiator',(.3634175776637853,2.9445579551660426,((b+(j<e))-1)*pitch+outer)) for j in range(ns)]
   P.items=arr+rad+[('rack','bus',(.6,1.2,rh)),('equip','bus',(ex,ey,veq/(ex*ey)+.2))];P._PC.clear()
   rows=[]
   for x,y in sorted(footprints):
    v=P._pack(x,y,False)
    if v:rows.append((x,y,v[0]))
   n,seq=P.dp2(rows,adapt=S['adapt'],gap=S['gap']);z=dict(constructive_count=n,stack_count=ns,equipment_xy_m=[ex,ey],sequence=seq,items=P.items,rows=rows,item_volume_m3=sum(math.prod(it[2]) for it in P.items))
   trials.append({k:v for k,v in z.items() if k not in ['items','rows','sequence']})
   if best is None or n>best['constructive_count']:best=z
   print(nm,'pitch',pitch,'stacks',ns,'equip',ex,ey,'count',n,flush=True)
   if n>=f['spacecraft_count']['value']:break
  if best['constructive_count']>=f['spacecraft_count']['value']:break
 best.update(required_count=int(f['spacecraft_count']['value']),passed=best['constructive_count']>=f['spacecraft_count']['value'],radiator_panels=N,radiator_stack_pitch_m=pitch,max_header_OD_m=.0216,added_nonradiator_equipment_volume_m3=added_eq_volume,additional_equipment_mass_proxy_kg=max(0,delta_nonarray_rad),trials=trials,method='same heightmap and exact layer-corner DP; explicit header depth and resized counts; conservative extra equipment volume at inherited density',scope='Constructive ideal envelopes only; finite hinges, articulated sweep, dispenser, CG and launcher loads remain unqualified')
 out['cases'][nm]=best;out['passed'] &= best['passed']
out['wall_seconds']=time.perf_counter()-start
p=R/('final/PACKING_GEOMETRY_'+sys.argv[1]+'.json' if len(sys.argv)>1 else 'final/PACKING_GEOMETRY.json');p.write_text(json.dumps(out,indent=2)+'\n');print('OUTPUT',str(p),'passed',out['passed'])
