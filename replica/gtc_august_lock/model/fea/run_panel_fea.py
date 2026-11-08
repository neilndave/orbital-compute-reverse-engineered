"""Final circular-tube shell FEA, reusing historical P8a Mesh/write_inp/surface_stress.
6061-T6, wet panel mass, retained seven-station launch pads (all seven tubes).
Round shell represented by 16 facets; fin at tube mid-wall equator. NO stiffness from
headers/coolant/coating; their allocated mass is retained. Screening, not qualification.
"""
import os,sys,json,math,time,re,subprocess
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];O=Path(__file__).parent;sys.path.insert(0,str(O));import p8a_helpers as H
G=json.load(open(R/'model/FINAL_GEOMETRY.json'));A=G['radiator'];W=A['panel_width_m'];L=A['panel_length_m'];NT=A['NT'];rm=(A['tube_OD_m']+A['tube_ID_m'])/4;tw=(A['tube_OD_m']-A['tube_ID_m'])/2;t=A['thickness_m'];E=68.9e9;rho=2700.;wet=G['ledger_kg']['radiator']/140
CFG={'material':dict(E_Pa=E,nu=.33,rho_kg_m3=rho)}
# Header and strip-heater mass conservatively included as endpoint lumps in addition to wet panel.
# Entire old header mass stays in global bus for Newton; no structural stiffness credit taken.
can=json.load(open(R/'RESULTS_CANONICAL.json'));inv=can['native_thermal']['T2_rec_nominal_MPG40_plus_recharge']['inventory'];header_fluid_panel=inv['hdr_fluid']/140
# Existing coolant package carries header metal etc; 0.225 kg/panel historical header+stub is a declared screen, no new ledger mass.
header_lump=.225+header_fluid_panel

def model(ny,nfacet,layout):
 m=H.Mesh();centers=[(k+.5)*W/NT for k in range(NT)]
 spans=[(0,centers[0]-rm)]+[(centers[k]+rm,centers[k+1]-rm) for k in range(NT-1)]+[(centers[-1]+rm,W)]
 for lo,hi in spans:m.patch((lo,0,0),(hi-lo,0,0),(0,L,0),4,ny,'SHEET',lambda c:t)
 for x in centers:
  for j in range(nfacet):
   aa=2*math.pi*j/nfacet;bb=2*math.pi*(j+1)/nfacet
   p=np.array([x+rm*math.cos(aa),0,rm*math.sin(aa)]);q=np.array([x+rm*math.cos(bb),0,rm*math.sin(bb)])
   m.patch(p,q-p,(0,L,0),1,ny,'TUBE',lambda c:tw)
 struct=sum(e[2]*e[3]*rho for e in m.elems);ar=sum(e[3] for e in m.elems);extra=(wet-struct)/ar
 assert extra>0,(struct,wet)
 end=[i for i,e in enumerate(m.elems) if e[1]=='TUBE' and(e[4][1]<L/ny or e[4][1]>L-L/ny)]
 me=[e[2]*e[3]*rho+extra*e[3]+(header_lump/len(end) if i in end else 0.) for i,e in enumerate(m.elems)];reff=[q/(e[2]*e[3]) for q,e in zip(me,m.elems)];xyz=np.array(m.xyz)
 pads=[]
 if layout=='stack':
  for x in centers:
   for y in np.linspace(.04,L-.04,7):
    mask=(abs(xyz[:,0]-x)<1e-8)&(abs(xyz[:,2]+rm)<1e-8)&(abs(xyz[:,1]-y)<=.03)
    if not mask.any():mask=(abs(xyz[:,0]-x)<1e-8)&(abs(xyz[:,2]+rm)<1e-8)&(abs(xyz[:,1]-y)==min(abs(xyz[(abs(xyz[:,0]-x)<1e-8)&(abs(xyz[:,2]+rm)<1e-8),1]-y)))
    ids=np.where(mask)[0]+1;assert len(ids);pads.append(dict(nodes=ids.tolist(),dofs=[1,2,3]))
 else:
  # rigid latched root: shell endpoint clamped; upper-bound stiffness, no claim for a whole 29.446-m deployed column.
  ids=(np.where(abs(xyz[:,1])<1e-9)[0]+1).tolist();pads=[dict(nodes=ids,dofs=[1,2,3,4,5,6])]
 return dict(mesh=m,rho_eff=reff,pads=pads,total_kg=sum(me)),struct

def parse_U(path,nn):
 arr=[];cur=None
 for line in path.read_text().splitlines():
  if 'displacements (vx,vy,vz)' in line:cur=np.zeros((nn,3));arr.append(cur);continue
  a=line.split()
  if cur is not None and len(a)==4 and a[0].isdigit():cur[int(a[0])-1]=list(map(float,a[1:]))
 return arr

def run(ny,nfacet,layout):
 w=O/f'{layout}_ny{ny}_f{nfacet}';w.mkdir(exist_ok=True);mdl,struct=model(ny,nfacet,layout);m=mdl['mesh'];nn=len(m.xyz)
 H.write_inp(mdl,w/'panel.inp',CFG,steps=())
 with (w/'panel.inp').open('a') as f:
  f.write(f'*NSET,NSET=NALL,GENERATE\n1,{nn},1\n')
  if layout=='stack':
   for dx in [(1,0,0),(0,1,0),(0,0,1)]:
    f.write(f'*STEP\n*STATIC\n*DLOAD,OP=NEW\nEALL,GRAV,{H.G0},{dx[0]},{dx[1]},{dx[2]}\n*NODE PRINT,NSET=NALL\nU\n*EL PRINT,ELSET=EALL\nS\n*END STEP\n')
  f.write('*STEP\n*FREQUENCY\n8\n*END STEP\n')
 env=dict(os.environ,OMP_NUM_THREADS='2',LD_LIBRARY_PATH=os.environ.get('LD_LIBRARY_PATH',''))
 if (w/'solver.log').exists() and 'Job finished' in (w/'solver.log').read_text():
  logs=(w/'solver.log').read_text();wall=float(re.search(r'Total CalculiX Time:\s*([0-9.]+)',logs).group(1));print('REUSE completed solve',w,wall,flush=True)
 else:
  t0=time.perf_counter();p=subprocess.run([os.environ.get('CCX','ccx'),'-i','panel'],cwd=w,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);wall=time.perf_counter()-t0;(w/'solver.log').write_text(p.stdout)
  if p.returncode:raise RuntimeError((w,p.returncode,p.stdout[-3000:]))
 text=(w/'panel.dat').read_text();freq=[];take=False
 for ln in text.splitlines():
  if 'E I G E N V A L U E' in ln:take=True;continue
  a=ln.split()
  if take and len(a)>=4 and a[0].isdigit():
   try:freq.append(float(a[3]));
   except ValueError:pass
   if len(freq)==8:break
 out=dict(layout=layout,ny=ny,tube_facets=nfacet,n_nodes=nn,n_elements=len(m.elems),panel_wet_kg=wet,header_lump_kg=header_lump,total_model_kg=mdl['total_kg'],structural_metal_kg=struct,wall_s=wall,frequencies_Hz=freq,solver='CalculiX 2.21, box CPU, 2 threads')
 if layout=='stack':
  U=parse_U(w/'panel.dat',nn)[:3];SS,_=H.parse_static(w/'panel.dat',len(m.elems));SS=SS[:3];assert len(U)==len(SS)==3,(len(U),len(SS));xyz=np.array(m.xyz);norm=[]
  for e in m.elems:
   p0,p1,p3=xyz[np.array(e[0][:4])-1][[0,1,3]];v=np.cross(p1-p0,p3-p0);norm.append(v/np.linalg.norm(v))
  surf=[H.surface_stress(s,np.array(norm)) for s in SS];corners={}
  for nm,(az,lat) in dict(max_axial=(6,.5),max_lateral=(3.5,2),tension_lat=(-1.5,2),max_tension=(-2,.5)).items():
   mx=0.;uz=0.;arg=None
   for th in range(0,360,15):
    c=math.cos(math.radians(th));s=math.sin(math.radians(th));stress=az*surf[2]+lat*(c*surf[0]+s*surf[1]);vm=H.von_mises(stress);val=float(vm.max());u=az*U[2]+lat*(c*U[0]+s*U[1]);uz=max(uz,float(abs(u[:,2]).max()))
    if val>mx:mx=val;arg=th
   corners[nm]=dict(max_von_mises_MPa=mx/1e6,FS1p25_yield_margin=241e6/(1.25*mx)-1,max_abs_uz_mm=uz*1000,worst_angle_deg=arg)
  out['launch_corners']=corners;out['min_yield_margin']=min(z['FS1p25_yield_margin'] for z in corners.values());out['max_abs_uz_mm']=max(z['max_abs_uz_mm'] for z in corners.values());out['geometric_gap_mm']=2.;out['two_adjacent_worst_case_gap_margin_mm']=2-2*out['max_abs_uz_mm'];out['modal_35Hz_reference_pass']=bool(freq and freq[0]>=35)
 (w/'RESULT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True);return out
if __name__=='__main__':
 rows=[]
 for ny,nfacet,layout in [(42,16,'stack'),(84,16,'stack'),(84,16,'deployed')]:rows.append(run(ny,nfacet,layout))
 out=dict(scope=__doc__,geometry=G,results=rows,qualification='OPEN: pad rail/contact/hardware, braze/re-age, whole-wing latch stiffness, launcher coupled loads. Falcon 35 Hz is a comparison reference, not an asserted Starship requirement.')
 (O/'FEA_FINAL.json').write_text(json.dumps(out,indent=2)+'\n')
