"""GTC poster r11 candidate (43x24 in, 300 dpi). Every printed number comes from out/POSTER_NUMBERS_R11.json
(derived by numbers/derive_numbers.py from committed pipeline outputs). Layout derived from the approved r10 generator.
Usage: R11_ROOT=<repro> python poster/make_poster_r11.py [--public] [--audit-only] --repo-url https://github.com/<owner>/<repo>
"""
from pathlib import Path
import os,json,hashlib,re,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import qrcode
R=Path(os.environ['R11_ROOT']).resolve();OUT=R/'out/poster';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
NUMF=R/'out/POSTER_NUMBERS_R11.json';NUM=json.loads(NUMF.read_text());NN=NUM['numbers'];used=[]
def n(k):used.append(k);return NN[k]['shown']
audit_only='--audit-only' in sys.argv;public='--public' in sys.argv
repo_url=sys.argv[sys.argv.index('--repo-url')+1] if '--repo-url' in sys.argv else 'https://github.com/OWNER/REPOSITORY'
assert repo_url.startswith('https://github.com/')
# Approved identity strings are supplied at build time (env) so they appear only in the PDF, never in repo files.
AUTHOR=os.environ.get('POSTER_AUTHOR','<author>');ASSISTANT=os.environ.get('POSTER_ASSISTANT','<assistant>');AUTHOR_LINE=f'Author: {AUTHOR} assisted by AI agent {ASSISTANT}'
GB=R/'gb10_out/r11';sweep_npz=GB/'SWEEP_PLOT_GB10_GPU.npz';mc_npz=GB/'MC_PLOT_GB10_GPU.npz';sv_npz=R/'poster_inputs/SURROGATE_VALIDATION.npz';newton_npz=R/'poster_inputs/solar_t780_dt0.01_kl5000.npz';hero_png=R/'poster_inputs/v3_lock_hero.png'
SEL=json.loads((GB/'SWEEP_GB10_GPU.json').read_text())['selected'];assert SEL['index']==NN['selected_index']['raw']
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
fig=plt.figure(figsize=(43,24),facecolor='white');ink='#183143';teal='#237968';muted='#475969';blue='#347da5';orange='#c88323'
TITLE='Accelerating AI compute satellite engineering with an AI agent and GPU simulation'
zone='header';alltexts=[];zone_artists={}
def txt(x,y,s,size=26,weight='normal',color=ink,va='top',**kw):
 alltexts.append(s);a=fig.text(x/43,y/24,s,fontsize=size,fontweight=weight,color=color,va=va,**kw);a._poster_zone=zone;zone_artists.setdefault(zone,[]).append(a);return a
def wrap(s,width,size=24,weight='normal'):
 fp=FontProperties(family='DejaVu Sans',weight=weight);lines=[]
 for para in s.split('\n'):
  line=''
  for word in para.split():
   trial=(line+' '+word).strip()
   if line and TextPath((0,0),trial,size=size,prop=fp).get_extents().width/72>width:lines.append(line);line=word
   else:line=trial
  lines.append(line)
 return lines
def fit_body(x,y,s,width,size=24,weight='normal',leading=1.12,**kw):return txt(x,y,'\n'.join(wrap(s,width,size,weight)),size=size,weight=weight,linespacing=leading,**kw)
def axes(x,y,w,h):
 a=fig.add_axes([x/43,y/24,w/43,h/24]);a.tick_params(labelsize=24);a.xaxis.label.set_size(24);a.yaxis.label.set_size(24);a.grid(alpha=.12);a._poster_zone=zone;zone_artists.setdefault(zone,[]).append(a);return a
panels={'m1':[12.25,11.825,14.75,8.575],'m2':[27.25,11.825,14.75,8.575],'m3':[12.25,3.0,14.75,8.575],'m4':[27.25,3.0,14.75,8.575]}
def panel(key,title):
 global zone
 zone=key;x,y,w,h=panels[key]
 fig.add_artist(Rectangle(((x+.008)/43,(y+.008)/24),(w-.016)/43,(h-.016)/24,transform=fig.transFigure,facecolor='white',edgecolor='#c1d6d1',lw=1,zorder=-2))
 fig.add_artist(Rectangle((x/43,(y+h-.60)/24),w/43,.60/24,transform=fig.transFigure,facecolor=teal,edgecolor='none'))
 txt(x+.18,y+h-.09,title,size=32,weight='bold',color='white')
# Header. r11: title lowered so actual PDF glyph boxes respect the 1-in top margin.
title_artist=txt(1,22.80,TITLE,size=54,weight='bold')
author_artist=txt(1,22.03,AUTHOR_LINE,size=24,weight='bold')
subtitle_artist=txt(1,21.66,'Engineers set the requirements. An AI agent runs the analysis. Physics solvers check the selected design.',size=24,color=muted)
workflow=[];workflow_boxes=[];x=1.0;workflow_gap=.35
workflow_size_labels=['Human requirements /\ndesign decisions','AI agent (closed source)','Open analysis scripts\nApache-2.0','GPU: Warp 1–3; PhysicsNeMo 4; Newton 5\n4: train → infer; CPU: CalculiX FEA; speed 6','Solver checks','Human review /\napproval']
workflow_labels=workflow_size_labels.copy();workflow_labels[3]='GPU: Warp, PhysicsNeMo, Newton\nCPU: CalculiX FEA'
fp=FontProperties(family='DejaVu Sans');widths=[max(TextPath((0,0),l,size=24,prop=fp).get_extents().width/72 for l in label.split('\n'))+.34 for label in workflow_size_labels]
for i,(w,label) in enumerate(zip(widths,workflow_labels)):
 box=Rectangle((x/43,20.46/24),w/43,.84/24,transform=fig.transFigure,facecolor='#edf5f2',edgecolor=teal,lw=1.1);fig.add_artist(box);workflow_boxes.append(box)
 workflow.append(txt(x+.13,21.25 if '\n' in label else 21.05,label,size=24,linespacing=1.12))
 if i<5:fig.add_artist(FancyArrowPatch(((x+w+.025)/43,20.88/24),((x+w+workflow_gap-.025)/43,20.88/24),transform=fig.transFigure,arrowstyle='-|>',mutation_scale=13,color=teal,lw=1.6))
 x+=w+workflow_gap
workflow_width=x-workflow_gap-1
qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=10,border=4);qr.add_data(repo_url);qr.make(fit=True);qa=fig.add_axes([39.5/43,20.90/24,1.92/43,1.92/24]);qa.imshow(np.asarray(qr.make_image(fill_color='black',back_color='white').convert('RGB')),interpolation='nearest');qa.axis('off')
qrlabel=txt(40.46,20.80,'Full repo (GitHub)',size=24,ha='center',color=muted)
# Left column
zone='left'
renderer=fig.canvas.get_renderer()
def bottom(a):return a.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted()).y0
problem=f"Putting AI data centers in orbit can ease power generation concerns on Earth, but the satellites must be mass- and volume-efficient to meet launch and radiative cooling needs. SpaceX's published targets of {n('peak_target_kW')} kW peak per satellite and 75 kW per ton imply {n('satellites')} satellites × {n('peak_target_kW')} kW = {n('fleet_peak_MW')} MW installed peak per {n('launch_t')} t Starship launch. An engineer and an AI agent explored the design space and selected a high-level architecture to meet that target."
txt(1.12,20.25,'PROBLEM',size=30,weight='bold',color=teal)
pa=fit_body(1.12,19.70,problem,10.6,24,leading=1.04)
src=fit_body(1.12,bottom(pa)-.08,'Source: spacex.com/spacexai/starmind',10.6,24,color=muted,leading=1.0)
ay=bottom(src)-.20
archhead=txt(1.12,ay,'DESIGN ARCHITECTURE (PER SATELLITE)',size=30,weight='bold',color=teal)
ay=bottom(archhead)-.15
architecture=[
('Compute:', f"one Vera Rubin NVL72 (72 GPUs + 36 CPUs); {n('peak_target_kW')} kW peak at beginning of life. Assumed 640.38 kg payload allocation in a 600 × 1200 × 937 mm box."),
('Mass:', f"{n('sc_mass_kg')} kg per satellite; all {n('satellites')} satellites fit one {n('launch_t')} t Starship at {n('fleet_t')} t, leaving {n('dispenser_t')} t for the dispenser and a {n('reserve_t')} t reserve."),
('Power:', f"{n('solar_area_m2')} m² solar array; assumed module rating {n('module_rating_W_m2')} W/m² on its remaining planar area; {n('nominal_kW')} kW nominal in sunlight and a {n('annual_kW')} kW annual average, including eclipse."),
('Thermal:', f"Rubin GPU/HBM ≈{n('device_target_K')} K nominal target (est. {n('GPU_est_K')}–{n('HBM_est_K')} K), higher in edge cases; junction temperatures not yet qualified. Coolant inlet peaks at {n('coolant_inlet_peak_K')} K. {n('radiator_panels')} radiator panels; coating emissivity {n('emissivity')}. Fins and tubes selected by search; modeled glycol-water loop."),
('Rack structure:', f"Compute rack screening (CalculiX beam model, 6 g axial / 2 g lateral, FS 1.25): a {n('frame_kg')} kg aluminum frame inside the 640 kg allocation reaches {n('frame_f1_Hz')} Hz (Falcon reference) with large strength margins."),
('Panel vibration:', f"Stowed radiator-panel first mode {n('panel_f1_min_Hz')}–{n('panel_f1_max_Hz')} Hz across support-pad assumptions (≈{n('panel_f1_nominal_Hz')} Hz nominal), well above the 35 Hz reference."),
('Folding and deployment:', f"{n('hinge_locks')}/{n('hinge_locks')} representative hinge locks latch in Newton rigid simulation; sampled clearance passes.")]
def labelled(label,content,y):
 l=txt(1.12,y,label,size=24,weight='bold');lw=l.get_window_extent(renderer).width/fig.dpi+.09
 words=content.split();lines=[];line='';first=True;fp=FontProperties(family='DejaVu Sans')
 for word in words:
  trial=(line+' '+word).strip();width=10.6-lw if first else 10.6
  if line and TextPath((0,0),trial,size=24,prop=fp).get_extents().width/72>width-.05:lines.append(line);line=word;first=False
  else:line=trial
 lines.append(line);a=txt(1.12+lw,y,lines[0],size=24);low=min(bottom(l),bottom(a))
 if len(lines)>1:a=txt(1.12,y-.35,'\n'.join(lines[1:]),size=24,linespacing=1.04);low=bottom(a)
 return low-.13
for label,para in architecture:ay=labelled(label,para,ay)
closing=fit_body(1.12,ay,'A basis for further detailed design. Simulation study, not flight qualification.',10.6,24,leading=1.04)
# r11: enlarged render fills all remaining left-column space (credit line underneath, 1-in bottom margin).
credit_lines=wrap('Illustrative Isaac Sim RTX render, not flight validation. Earth: NASA Blue Marble.',10.6)
credit_h=.40*len(credit_lines)
hero_top=bottom(closing)-.15;hero_bottom=1.12+credit_h+.10;hero_h=min(hero_top-hero_bottom,10.6*9/16);hero_w=hero_h*16/9
assert hero_h>=3.0,hero_h
hero=fig.add_axes([(6.42-hero_w/2)/43,hero_bottom/24,hero_w/43,hero_h/24]);hero.imshow(plt.imread(hero_png));hero.axis('off');hero._poster_zone=zone;zone_artists.setdefault(zone,[]).append(hero)
credit=txt(1.12,hero_bottom-.08,'\n'.join(credit_lines),size=24,linespacing=1.0,color=muted)
# 1: search
panel('m1','1  What did the search find? | Warp')
txt(12.45,19.62,f"{n('configurations')}M designs; {n('hard_feasible')} feasible, lightest picked",size=34,weight='bold')
txt(13.40,19.00,'Screening candidates (color: panels)',size=24)
txt(22,19.00,'Stress scenarios',size=24)
a=axes(13.40,14.85,6.95,3.55);arr=np.load(sweep_npz)['values'];mask=(arr[:,5]==SEL['tubes_per_panel'])&(arr[:,4]<=SEL['radiator_panels']);a.scatter(arr[mask,0],arr[mask,3],c=arr[mask,4],cmap='viridis',s=10,alpha=.85);a.axhline(393,color='#a23a31',ls='--');a.scatter(NN['screen_mass_kg']['raw'],SEL['inlet_peak_K'],marker='*',s=240,color=orange,edgecolor=ink,label='Screen estimate',zorder=5);a.scatter(NN['solver_mass_kg']['raw'],NN['coolant_inlet_peak_K']['raw'],marker='D',s=90,color='#a23a31',edgecolor='white',label='Solver re-check',zorder=6);a.set(xlabel='Spacecraft mass (kg)',ylabel='Peak radiator inlet (K)');a.legend(fontsize=24,loc='lower left',framealpha=.85)
b=axes(22.0,14.85,4.50,3.55);samples=np.load(mc_npz)['values'];b.hist(samples[:,2],bins=45,density=True,color=blue);b.axvline(393,color='#a23a31',ls='--',lw=2);b.set(xlabel='Coolant inlet (K)',ylabel='Scenario density');b.set_xticks([380,393,405])
fit_body(12.45,13.65,f"Only {n('scenario_pass_pct')}% of assumed scenarios meet the 393 K coolant cap.",14.25,28,weight='bold')
fit_body(12.45,13.10,f"{n('scenario_draws')}M coating / power / sun-exposure scenarios; not flight reliability.",14.25,26)
fit_body(12.45,12.50,f"Star: screening estimate. Diamond: solver re-check, {n('solver_mass_kg')} kg / {n('radiator_panels')} panels.",14.25,24)
# 2: benchmark
panel('m2','2  What ran faster? | GB10 benchmark')
txt(27.45,19.62,f"{n('speedup_x')}× faster than one GB10 CPU core",size=36,weight='bold')
a=axes(29.0,15.20,11.60,3.30);vals=[NN['gpu_kernel_s']['raw'],NN['cpu_kernel_s']['raw']];a.bar([0,1],vals,color=[teal,'#798b96'],width=.5);a.set_ylim(0,8.7);a.set_xticks([0,1],['NVIDIA GB10 GPU','GB10 CPU\n1 core / 1 thread']);a.set_ylabel('Warm sweep seconds');a.set_yticks([0,2,4,6,8])
for i,k in enumerate(['gpu_kernel_s','cpu_kernel_s']):alltexts.append(n(k)+' s');a.text(i,vals[i]+.25,NN[k]['shown']+' s',ha='center',va='bottom',fontsize=30,fontweight='bold',color=ink)
fit_body(27.45,14.05,f"Same fp64 workload; warm kernel only; median of 3 runs. Warp {n('warp_version')}.\n{NN['configurations']['raw']:,} combinations; CPU: 1 Cortex-X925 core / 1 thread.\nDevice-synchronized timer; setup/JIT/readback excluded.",14.25,24,leading=1.15)
fit_body(27.45,12.25,f"{n('throughput_Mps')}M designs/s; input SHA256 {n('inputs_sha256')}… (full hash in repo).",14.25,24)
# 3: surrogate + Tape
panel('m3','3  Can we trust the search? | PhysicsNeMo / Tape')
txt(12.45,10.78,'Max |Δη| = '+n('surrogate_heldout_max_abs_eta')+' (held out)',size=34,weight='bold')
a=axes(13.60,6.10,11.90,3.90);sv=np.load(sv_npz);a.scatter(sv['true'],sv['prediction'],s=30,c=blue);lim=[min(sv['true']),max(sv['true'])];a.plot(lim,lim,color=ink,ls='--');a.set(xlabel='Warp solver fin efficiency η',ylabel='Surrogate prediction')
fit_body(12.45,5.10,f"PhysicsNeMo: {n('surrogate_train')} training / {n('surrogate_heldout')} held-out labels; η = fin efficiency.\nSelected fins re-solved with Warp; approximation is not flight validation.\nwarp.Tape: {n('tape_gap_pct')}% relaxed mass gap; gradient check {n('tape_gradient_max_rel_err')}.\nContinuous relaxation, not adopted hardware or a global optimum.",14.25,24,leading=1.15)
# 4: deployment
panel('m4','4  Does it deploy? | Newton / Warp')
txt(27.45,10.78,f"{n('hinge_locks')} / {n('hinge_locks')} modeled hinge locks",size=36,weight='bold')
a=axes(28.65,6.10,12.10,3.90);d=np.load(newton_npz);h=np.degrees(d['h_newton']);w=np.degrees(d['h_warp']);a.plot(d['t'],h[:,0],label='Root Newton',lw=2);a.plot(d['t'],np.max(abs(h[:,1:]),axis=1),label='Accordion max',lw=2);a.plot(d['t'],w[:,0],ls='--',label='Warp reference');a.set(xlabel='Simulated seconds',ylabel='Hinge angle (deg)');a.legend(fontsize=24,loc='upper right')
fit_body(27.45,5.10,f"Rigid panels / fixed bus; representative hinges, not full flight tests.\nIndependent sampled-clearance check passed; angle parity {n('angle_parity_deg')}°.\nNewton {n('newton_version')} and Warp 1.18.0 on CUDA; agreement is not hardware validation.\nFlexible hardware and force-step convergence remain open.",14.25,24,leading=1.15)
# Effort strip (no gate claim) + why it matters
zone='effort'
fit_body(12.45,2.72,f"{n('effort_days')} days recorded span | {n('effort_hours')} h GB10 computer-job time* | Why it matters: more checks before hardware, not just a faster kernel",29.1,28,weight='bold',color=teal,leading=1.0)
fit_body(12.45,2.16,'*CPU + GPU jobs, including rendering; not GPU-hours. Start: earliest-retained-input timestamp proxy, not verified first problem definition.',29.1,24,color=muted,leading=1.0)
# Wording rules
text='\n'.join(alltexts)
assert not re.search(r'(?-i:\bOPEN\b)|\bHonest\b|Dassault|Synopsys|native verification|leaner teams|June|J8|rerout|short.edge|79 GPUs|lightweighted|passed release gates|gates A|aluminum compat|Dow|Grace|366 K|362 K',text,re.I),'forbidden wording'
assert '30 satellites' in text and AUTHOR_LINE in text
fig.canvas.draw();renderer=fig.canvas.get_renderer()
def inchbox(a):return a.get_tightbbox(renderer).transformed(fig.dpi_scale_trans.inverted()) if isinstance(a,matplotlib.axes.Axes) and a.axison else a.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
bad=[]
for a in list(fig.texts)+list(fig.axes)+list(fig.artists):
 if not a.get_visible():continue
 bb=inchbox(a)
 if bb.x0<1-1e-5 or bb.y0<1-1e-5 or bb.x1>42+1e-5 or bb.y1>23+1e-5:bad.append({'kind':type(a).__name__,'bounds_inches':list(bb.extents)})
regions={**panels,'left':[1,1,11,19.4],'header':[1,20.4,41,2.6],'effort':[12.25,1,29.75,2]}
for name,artists in zone_artists.items():
 x,y,w,h=regions[name]
 for a in artists:
  bb=inchbox(a)
  if bb.x0<x-1e-5 or bb.y0<y-1e-5 or bb.x1>x+w+1e-5 or bb.y1>y+h+1e-5:bad.append({'region':name,'kind':type(a).__name__,'bounds_inches':list(bb.extents),'text':a.get_text() if hasattr(a,'get_text') else 'plot'})
 for i,a in enumerate(artists):
  for b in artists[i+1:]:
   if inchbox(a).overlaps(inchbox(b)):bad.append({'region':name,'overlap':[(a.get_text() if hasattr(a,'get_text') else 'plot'),(b.get_text() if hasattr(b,'get_text') else 'plot')]})
if any(inchbox(t).overlaps(inchbox(qa)) for t in fig.texts):bad.append('QR/text overlap')
if not inchbox(qrlabel).y1<inchbox(qa).y0:bad.append('QR caption must be underneath code')
for t,b in zip(workflow,workflow_boxes):
 tb,bb=inchbox(t),inchbox(b)
 if not (bb.contains(tb.x0,tb.y0) and bb.contains(tb.x1,tb.y1)):bad.append('Workflow text exceeds box: '+t.get_text())
assert all(t.get_fontsize()>=24 for t in fig.texts)
assert all(t.get_fontsize()>=24 for ax in fig.axes if ax.axison for t in ax.get_xticklabels()+ax.get_yticklabels()+ax.texts if t.get_visible())
area=sum(v[2]*v[3] for v in panels.values());assert area/902>=.55
hero_px=plt.imread(hero_png).shape;hero_dpi=hero_px[1]/hero_w
layout=dict(layout_revision='r11_candidate',matplotlib_layout_passed=not bad,numbers_sha256=sha(NUMF),minimum_text_pt=24,required_white_margin_inches=1,bounds_inches=[1,1,42,23],nvidia_module_area_inches2=area,live_area_inches2=902,nvidia_area_percent=area/902*100,modules=panels,qr_size_inches=1.92,qr_bounds_inches=list(inchbox(qa).extents),qr_caption='Full repo (GitHub)',qr_caption_bounds_inches=list(inchbox(qrlabel).extents),hero_size_inches=[hero_w,hero_h],hero_bounds_inches=list(inchbox(hero).extents),hero_source_pixels=list(hero_px[:2]),hero_effective_dpi=hero_dpi,r10_hero_size_inches=[4.088888888888889,2.3],workflow_total_width_inches=workflow_width,numbers_used=sorted(set(used)),generator_sha256=sha(__file__),violations=bad)
(OUT/'LAYOUT_R11_MPL_AUDIT.json').write_text(json.dumps(layout,indent=2)+'\n')
if bad:raise RuntimeError(json.dumps(bad,indent=2))
assert hero_dpi>=300,hero_dpi
if audit_only:print('r11 matplotlib layout PASS',area/902*100,hero_w,hero_h);sys.exit(0)
out=OUT/('GTC_POSTER_R11_CANDIDATE_PUBLIC.pdf' if public else 'GTC_POSTER_R11_CANDIDATE_DRAFT.pdf')
fig.savefig(out,dpi=300,metadata={'Title':TITLE,'Author':AUTHOR,'Subject':'August design, one Vera Rubin NVL72; r11 candidate (not adopted); numbers SHA256 '+sha(NUMF),'CreationDate':None})
if not public:fig.savefig(OUT/'POSTER_R11_PREVIEW.png',dpi=100)
plt.close(fig)
red=lambda t:t.replace(repo_url,'https://github.com/OWNER/REPOSITORY').replace(AUTHOR,'<author>').replace(ASSISTANT,'<assistant>')
redacted=red(text)
ticks=sorted({t.get_text() for ax in fig.axes if ax.axison for t in ax.get_xticklabels()+ax.get_yticklabels() if t.get_text()})
meta=dict(layout_revision='r11_candidate',file=out.name,pdf_sha256=sha(out),size_bytes=out.stat().st_size,page_inches=[43,24],numbers_sha256=sha(NUMF),generator_sha256=sha(__file__),repository_link='https://github.com/OWNER/REPOSITORY',all_text=redacted,claim_texts=[red(t) for t in alltexts],axis_tick_labels=ticks,chart_inputs={os.path.relpath(p,R):sha(p) for p in [sweep_npz,mc_npz,sv_npz,newton_npz,hero_png]})
(OUT/('POSTER_PDF_PUBLIC_TRACE.json' if public else 'POSTER_PDF_TRACE.json')).write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n');print(out,meta['size_bytes'],meta['pdf_sha256'])
