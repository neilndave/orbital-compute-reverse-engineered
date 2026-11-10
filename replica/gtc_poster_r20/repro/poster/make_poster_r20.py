"""GTC poster r20 (final; r19 + owner t955/t956/t958: 40 pt panel titles without headlines (Option 2 layout), findings moved under the charts, Panel 3 explainer, Panel 4 circled-number key, content-sized workflow boxes). Based on r19: (built from r17, NOT r18; owner t925-t938 wording: Problem + Why it matters, steady-state thermal, Panel 1 axis/sensitivity, r18 Panel 2 crossover, width-spread hinges and sequence bands in Panel 4, source + disclaimer footnote). Based on r17: (r16 + YouTube playlist QR, overlap-merged GB10 job-time effort line, launch-vehicle release caption, one SpaceX disclaimer in the header, chosen-design sensitivity lead-in, every Panel 4 hinge plotted) (43x24 in, 300 dpi). Every printed number comes from out/POSTER_NUMBERS_R11.json, speed/SPEED_NUMBERS_R11.json or speed/SPEED_ALLCORE_R11.json
(derived by numbers/derive_numbers.py from committed pipeline outputs). Layout derived from the approved r10 generator.
Usage: R11_ROOT=<repro> [HERO_PNG=<png>] python poster/make_poster_r17.py [--public] [--youtube-url <url>] [--audit-only] [--hero <png>] --repo-url https://github.com/<owner>/<repo>
Hero: --hero, else $HERO_PNG, else poster_inputs/HERO_R13.png (snapshot of the tone-only contrast-enhanced r11 render; params in HERO_R13_ENHANCE_PARAMS.json).
"""
from pathlib import Path
import ast,os,json,hashlib,re,sys,math,datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import qrcode
R=Path(os.environ['R11_ROOT']).resolve();TOPT='2';LOAD_WORD=os.environ.get('R20_LOAD_WORD','in sunlight');assert LOAD_WORD in ('average','nominal','in sunlight')  # 175 kW wording in Power / Thermal / Panel 1 (the model's 175 kW is the sunlit load; 164.4 kW is the annual average). Problem always says '175 kW average' (published target)
LOAD_PHRASE={'average':'average','nominal':'nominal','in sunlight':'in sunlight'}[LOAD_WORD];POWER_PHRASE={'average':'average in sunlight','nominal':'nominal in sunlight','in sunlight':'in sunlight'}[LOAD_WORD]
WHYBOX=os.environ.get('R20_WHYBOX','A');WHYBOX='' if WHYBOX=='none' else WHYBOX;assert WHYBOX in ('','A','B')  # final r20 (owner t974): Option A  # r20 preview option (owner t965): box around 'Why it matters'; default off = r20 build unchanged
OUT=Path(os.environ['R20_OUT']) if os.environ.get('R20_OUT') else R/'out/poster_r20';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
NUMF=R/'out/POSTER_NUMBERS_R11.json';NUM=json.loads(NUMF.read_text());NN=NUM['numbers'];used=[]
def n(k):used.append(k);return NN[k]['shown']
audit_only='--audit-only' in sys.argv;public='--public' in sys.argv
repo_url=sys.argv[sys.argv.index('--repo-url')+1] if '--repo-url' in sys.argv else 'https://github.com/OWNER/REPOSITORY'
assert repo_url.startswith('https://github.com/')
# Approved identity strings are supplied at build time (env) so they appear only in the PDF, never in repo files.
AUTHOR=os.environ.get('POSTER_AUTHOR','<author>');ASSISTANT=os.environ.get('POSTER_ASSISTANT','<assistant>');AUTHOR_LINE=f'Author: {AUTHOR} assisted by AI agent {ASSISTANT}'
GB=R/'gb10_out/r11';sweep_npz=GB/'SWEEP_PLOT_GB10_GPU.npz';mc_json=GB/'MC_GB10_GPU.json';sv_npz=R/'poster_inputs/SURROGATE_VALIDATION.npz';newton_npz=R/'poster_inputs/solar_t780_dt0.01_kl5000.npz';radiator_npz=R/'poster_inputs/radiator_t660_dt0.01_kl5000.npz';wfold_npz=R/'poster_inputs/wfold_newton_tw120_dt0.01.npz';wfold_json=R/'poster_inputs/wfold_newton_tw120_dt0.01.json';wfold_json_conv=R/'poster_inputs/wfold_newton_tw120_dt0.005.json';hero_png=Path(sys.argv[sys.argv.index('--hero')+1] if '--hero' in sys.argv else os.environ.get('HERO_PNG') or R/'poster_inputs/HERO_R13.png').resolve();release_png=Path(sys.argv[sys.argv.index('--release')+1] if '--release' in sys.argv else os.environ.get('RELEASE_PNG') or R/'poster_inputs/RELEASE_R11_K712_4K_CROP_fixed.png').resolve()  # r19: r18 rotation-fixed still; r16: default is the r11 4K release crop used on the poster
RELEASE_CREDIT='Simulated release: 30 satellites leave the launch vehicle through a side slot and unfold (kinematic, assumed parameters).';HERO_CREDIT='Illustrative Isaac Sim RTX render, contrast enhanced; not flight validation. Earth: NASA Blue Marble.'  # r17: SpaceX disclaimer moved to the bottom footnote (single occurrence)
MECH=json.loads((R/'native/final/MECHANICAL_LOCK.json').read_text())['packing'];assert MECH['PASS'] and MECH['count']==30
pack_top=f"{MECH['top_payload_m']:.1f}";pack_rad=f"{math.floor(MECH['min_payload_profile_radial_margin_m']*1e4)/10:.1f}";pack_gap=f"{MECH['min_component_separating_gap_m']*1000:.0f}"
SEL=json.loads((GB/'SWEEP_GB10_GPU.json').read_text())['selected'];
# r19: steady-state thermal numbers ONLY (owner: no transient-model data). Fields used: brackets.*.steady_check.{nom,pk}.{rack_in,rack_out,GPU_rubin,HBM_rubin}
# cross-checked against steady_reference (coolant_supply_K, rack outlet = 2*rack_mean - supply) and native/r11_out/NATIVE_CHECKS.json. No max_over_event / end_of_30min / tau fields are read.
THF=R/'evidence/transient/TRANSIENT_PEAK.json';_TP=json.loads(THF.read_text());_SR=_TP['steady_reference']
_rh=lambda v:str(math.floor(v+.5))
_SC={c:{k:[_TP['brackets'][b]['steady_check'][c][k] for b in ('low','mid','high')] for k in ('rack_in','rack_out','GPU_rubin','HBM_rubin','rad_in')} for c in ('nom','pk')}
for c in ('nom','pk'):
 for k,v in _SC[c].items():assert max(v)-min(v)<1e-6,(c,k,v)  # steady state is independent of heat-capacity bracket
 assert abs(_SC[c]['rack_in'][0]-_SR[c]['coolant_supply_K'])<.2 and abs(_SC[c]['rack_out'][0]-(2*_SR[c]['coolant_rack_mean_K']-_SR[c]['coolant_supply_K']))<.2 and abs(_SC[c]['rad_in'][0]-_SR[c]['coolant_radiator_inlet_K'])<.2
_NC=json.loads((R/'native/r11_out/NATIVE_CHECKS.json').read_text())['states']['nominal'];assert abs(_NC['coolant_supply_K']-_SR['nom']['coolant_supply_K'])<1e-6
assert abs(_SR['pk']['coolant_radiator_inlet_K']-NN['coolant_inlet_peak_K']['raw'])<1e-6,'steady record is not for the chosen design'
TH={f'{c}_{k}':_rh(_SC[c][k][0]) for c in ('nom','pk') for k in ('rack_in','rack_out','GPU_rubin','HBM_rubin')}
assert TH=={'nom_rack_in':'339','nom_rack_out':'359','nom_GPU_rubin':'371','nom_HBM_rubin':'373','pk_rack_in':'370','pk_rack_out':'390','pk_GPU_rubin':'410','pk_HBM_rubin':'412'},TH
assert TH['nom_GPU_rubin']==NN['GPU_est_K']['shown'] and TH['nom_HBM_rubin']==NN['HBM_est_K']['shown']
def th(k):used.append('steady:'+k);return TH[k]
assert SEL['index']==NN['selected_index']['raw']
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
fig=plt.figure(figsize=(43,24),facecolor='white');ink='#183143';teal='#237968';muted='#475969';blue='#347da5';orange='#c88323'
TITLE='Cooling and Launching Orbital Data Centers: Concept to Architecture in 12 Days'  # owner t985; '12' = EFFORT_UPDATE_R17 elapsed days, asserted below
zone='header';alltexts=[];zone_artists={}
def txt(x,y,s,size=26,weight='normal',color=ink,va='top',**kw):
 alltexts.append(s);a=fig.text(x/43,y/24,s,fontsize=size,fontweight=weight,color=color,va=va,**kw);a._poster_zone=zone;zone_artists.setdefault(zone,[]).append(a);return a
def wrap(s,width,size=24,weight='normal',keep_nbsp=False):
 fp=FontProperties(family='DejaVu Sans',weight=weight);lines=[]
 for para in s.split('\n'):
  line=''
  for word in ([w_ for w_ in para.split(' ') if w_] if keep_nbsp else para.split()):  # r20: keep_nbsp splits on plain spaces only (panel 3 'Max |Δη| = 9.3e-5' stays together); default unchanged from r19
   trial=(line+' '+word).strip()
   if line and TextPath((0,0),trial,size=size,prop=fp).get_extents().width/72>width:lines.append(line);line=word
   else:line=trial
  lines.append(line)
 return lines
def fit_body(x,y,s,width,size=24,weight='normal',leading=1.12,keep_nbsp=False,**kw):return txt(x,y,'\n'.join(wrap(s,width,size,weight,keep_nbsp)),size=size,weight=weight,linespacing=leading,**kw)
def axes(x,y,w,h):
 a=fig.add_axes([x/43,y/24,w/43,h/24]);a.tick_params(labelsize=24);a.xaxis.label.set_size(24);a.yaxis.label.set_size(24);a.grid(alpha=.12);a._poster_zone=zone;zone_artists.setdefault(zone,[]).append(a);return a
PW,PH=13.95,9.0;PX1,PX2=42-2*PW-.25,42-PW;PY1,PY3=20.4-PH,20.4-PH-.25-PH  # r14: narrower, taller panels
panels={'m1':[PX1,PY1,PW,PH],'m2':[PX2,PY1,PW,PH],'m3':[PX1,PY3,PW,PH],'m4':[PX2,PY3,PW,PH]}
LX,LW=1.12,PX1-.25-1.12-.13  # left column text x and width
TITLE_W={};BH=.85;TS=40  # r20 preview: 40 pt panel titles in a taller band (both options)
G1,S2,G3,G4=(0,0,0,0) if TOPT=='1' else (.85,.51,.55,.85)  # option 2: freed headline space goes to taller plots (bottoms fixed, nothing shrinks)
TITLES={'m1':'1  Radiator search and sensitivity | Warp','m2':'2  GPU-accelerated design search | GB10','m3':'3  AI fin model check | PhysicsNeMo / Warp','m4':'4  Unfolding after release | Newton / Warp'}  # owner t955/t958 (exact wording)
TITLES['m2']={'gb10':'2  GPU-accelerated design search | GB10','cuda_gb10':'2  GPU-accelerated design search | CUDA / GB10','cuda_short':'2  GPU-accelerated search | CUDA / GB10'}[os.environ.get('R20_P2_TITLE','gb10')]  # owner t998: 'CUDA / GB10' title is 15.05 in at 40 pt (max 13.59 in) -> kept the approved title; 'cuda_short' (12.77 in) needs owner approval
TITLE_PT={k_:float(os.environ.get('R20_TITLE_PT_'+k_.upper(),'40')) for k_ in TITLES}
TITLE_PT['m3']=float(os.environ.get('R20_TITLE_PT_M3','40'))  # r20: the approved P3 title is 14.62 in at 40 pt and 13.88 in at 38 pt (available 13.59 in); 37 pt = 13.52 in keeps the wording exact (flagged)
TITLE_CAP40=TextPath((0,0),'H',size=40,prop=FontProperties(family='DejaVu Sans',weight='bold')).get_extents().height/72
HS=30;HY=BH+.12;HLP=.44  # option 1 headline size / first-line offset / line pitch
def headline(x0,T,lines):
 if TOPT=='2':return
 for i_,l_ in enumerate(lines):txt(x0+.20,T-HY-i_*HLP,l_,size=HS,weight='bold')
def panel(key,title):
 title=TITLES[key];TS=TITLE_PT[key]
 global zone
 zone=key;x,y,w,h=panels[key]
 fig.add_artist(Rectangle(((x+.008)/43,(y+.008)/24),(w-.016)/43,(h-.016)/24,transform=fig.transFigure,facecolor='white',edgecolor='#c1d6d1',lw=1,zorder=-2))
 fig.add_artist(Rectangle((x/43,(y+h-BH)/24),w/43,BH/24,transform=fig.transFigure,facecolor=teal,edgecolor='none'))
 ta_=txt(x+.18,y+h-BH/2-TITLE_CAP40/2,title,size=TS,weight='bold',color='white',va='baseline');  # r20: all four titles share one baseline (caps of the 40 pt titles centred in the band; P3 at its fitted size sits on the same baseline)
 TITLE_W[key]=TextPath((0,0),title,size=TS,prop=FontProperties(family='DejaVu Sans',weight='bold')).get_extents().width/72;assert TITLE_W[key]<=w-.36,('title overflows',key,TITLE_W[key])  # r14: 29 pt so the longer panel-3 header fits the narrower panels
# Header. r11: title lowered so actual PDF glyph boxes respect the 1-in top margin.
title_artist=txt(1,22.80,TITLE,size=54,weight='bold')
DISCLAIMER='Independent study from public information; not affiliated with or endorsed by SpaceX.'  # r19: full wording (fits once the job-time footnote is gone); r17 (owner t889u): the poster's only SpaceX disclaimer, on the bottom footnote line (one line at 24 pt; 'from public information' dropped to fit)
author_artist=txt(1,22.03,AUTHOR_LINE,size=24,weight='bold')
SUBTITLE='An engineer sets the requirements. An AI agent runs the analysis. Physics solvers check the selected design.'  # owner t996
subtitle_artist=txt(1,21.66,SUBTITLE,size=24,color=muted)
workflow=[];workflow_boxes=[];x=1.0;workflow_gap=.35
workflow_size_labels=['Human requirements /\ndesign decisions','AI agent (closed source)','Open analysis scripts\nApache-2.0','GPU: Warp 1–3; PhysicsNeMo 4; Newton 5\n4: train → infer; CPU: CalculiX FEA; speed 6','Solver checks','Human review /\napproval']
workflow_labels=workflow_size_labels.copy();workflow_labels[3]='GPU: Warp, PhysicsNeMo, Newton\nCPU: CalculiX FEA'
fp=FontProperties(family='DejaVu Sans');widths_r19=[max(TextPath((0,0),l,size=24,prop=fp).get_extents().width/72 for l in label.split('\n'))+.34 for label in workflow_size_labels]
widths=[max(TextPath((0,0),l,size=24,prop=fp).get_extents().width/72 for l in label.split('\n'))+.34 for label in workflow_labels]  # r20 (owner t956): every box = its printed text + the same 0.34 in padding (r19 sized box 4 from a longer, unprinted label)
for i,(w,label) in enumerate(zip(widths,workflow_labels)):
 box=Rectangle((x/43,20.46/24),w/43,.84/24,transform=fig.transFigure,facecolor='#edf5f2',edgecolor=teal,lw=1.1);fig.add_artist(box);workflow_boxes.append(box)
 workflow.append(txt(x+.13,21.25 if '\n' in label else 21.05,label,size=24,linespacing=1.12))
 if i<5:fig.add_artist(FancyArrowPatch(((x+w+.025)/43,20.88/24),((x+w+workflow_gap-.025)/43,20.88/24),transform=fig.transFigure,arrowstyle='-|>',mutation_scale=13,color=teal,lw=1.6))
 x+=w+workflow_gap
workflow_width=x-workflow_gap-1
QS=float(os.environ.get('R20_QR_IN','2.08'));QY0=20.90;QX=41.95-QS;assert QY0+QS<=23-1e-9  # owner t996: QR codes 1.92 -> 2.08 in (bottom edge and captions unchanged; top stays inside the 1 in margin; right edge 0.05 in inside the margin)
qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=10,border=4);qr.add_data(repo_url);qr.make(fit=True);qa=fig.add_axes([QX/43,QY0/24,QS/43,QS/24]);qa.imshow(np.asarray(qr.make_image(fill_color='black',back_color='white').convert('RGB')),interpolation='nearest');qa.axis('off')
qrlabel=txt(QX+QS/2,20.80,'GitHub',size=24,ha='center',color=muted)
# r16 (owner request): second QR slot for one YouTube playlist, same size, left of the repo QR. Real QR when --youtube-url is given; else a dashed placeholder (DRAFT also prints 'QR code / to come').
YT_PLAYLIST='https://www.youtube.com/playlist?list=PLHLk3Rx0ECWs'  # r17 (owner): playlist 'Orbital Data Center Engineering'
yt_url=sys.argv[sys.argv.index('--youtube-url')+1] if '--youtube-url' in sys.argv else (None if '--youtube-placeholder' in sys.argv else YT_PLAYLIST)
YTX=QX-.25-QS
if yt_url:
 assert yt_url.startswith('https://')
 yq=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=10,border=4);yq.add_data(yt_url);yq.make(fit=True);ya=fig.add_axes([YTX/43,QY0/24,QS/43,QS/24]);ya.imshow(np.asarray(yq.make_image(fill_color='black',back_color='white').convert('RGB')),interpolation='nearest');ya.axis('off')
else:
 ya=fig.add_axes([YTX/43,QY0/24,QS/43,QS/24]);ya.set_xticks([]);ya.set_yticks([]);ya.set_xlim(0,1);ya.set_ylim(0,1)
 for sp in ya.spines.values():sp.set_visible(False)
 yt_box=Rectangle(((YTX+.06)/43,(QY0+.06)/24),(QS-.12)/43,(QS-.12)/24,transform=fig.transFigure,fill=False,ls=(0,(6,4)),lw=2.2,ec=muted);fig.add_artist(yt_box)  # figure-level so it is not treated as a bar
 if not public:
  for yy,s_ in ((.60,'QR code'),(.40,'to come')):ya.text(.5,yy,s_,transform=ya.transAxes,ha='center',va='center',fontsize=24,color=muted)
ytlabel=txt(YTX+QS/2,20.80,'YouTube',size=24,ha='center',color=muted)
# Left column
zone='left'
renderer=fig.canvas.get_renderer()
LEFT_LEAD=float(os.environ.get('R19_LEFT_LEAD','1.0'));LEFT_GAP=float(os.environ.get('R19_LEFT_GAP','.08'))  # r20 final (owner t981): .10 -> .08 to make room for the Orbit item  # r19: left-column body leading 1.04->1.0 and item gap .13->.10 (r17 values) so the longer text fits without shrinking the images
def labelled(label,content,y,color=ink,x=None,width=None):
 LX_,LW_=(LX if x is None else x),(LW if width is None else width)
 # r19: '\n' in content starts a new full-width line (thermal paragraph); label colour selectable
 l=txt(LX_,y,label,size=24,weight='bold',color=color);lw=l.get_window_extent(renderer).width/fig.dpi+.16
 fp=FontProperties(family='DejaVu Sans');lines=[];first=True
 for para in content.split('\n'):
  line=''
  for word in [w_ for w_ in para.split(' ') if w_]:  # r19: NBSP-joined '410 K' never breaks
   trial=(line+' '+word).strip();width=LW_-lw if first else LW_
   if line and TextPath((0,0),trial,size=24,prop=fp).get_extents().width/72>width-.05:lines.append(line);line=word;first=False
   else:line=trial
  lines.append(line);first=False
 a=txt(LX_+lw,y,lines[0],size=24);low=min(bottom(l),bottom(a))
 if len(lines)>1:a=txt(LX_,y-.35*LEFT_LEAD/1.04,'\n'.join(lines[1:]),size=24,linespacing=LEFT_LEAD);low=bottom(a)
 alltexts.append(label+' '+content.replace('\n',' ').replace('\u00a0',' '))
 return low-LEFT_GAP
labelled_early=labelled
def text_h(s_,width,size=24,leading=1.04,weight='normal'):
 a_=fig.text(0,.5,'\n'.join(wrap(s_,width,size,weight)),fontsize=size,fontweight=weight,linespacing=leading,va='top');bb_=a_.get_window_extent(renderer);a_.remove();return bb_.height/fig.dpi
def shift(arts,dy):
 for a_ in arts:
  if isinstance(a_,matplotlib.lines.Line2D):a_.set_ydata([v_+dy/24 for v_ in a_.get_ydata()])
  else:x_,y_=a_.get_position();a_.set_y(y_+dy/24)
PB=.12  # r20: text-to-panel-bottom inset (all panels)
PLOT_MIN={'m1':3.90,'m2':1.62,'m3':3.17,'m4':2.87}  # r19 sizes: never smaller
def bottom(a):return a.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted()).y0
problem=f"Orbital data centers can ease power generation concerns on Earth, but their satellites must be mass and volume efficient for launch and meet radiative cooling needs. SpaceX's published targets of {n('peak_target_kW')} kW peak / {n('nominal_kW')} kW average per satellite and 75 kW per ton, with a {n('launch_t')} t Starship launch, imply {n('fleet_peak_MW')} MW installed peak / {n('peak_target_kW')} kW = {n('satellites')} satellites."
assert abs(75*NN['launch_t']['raw']/1000-NN['fleet_peak_MW']['raw'])<1e-9 and abs(NN['fleet_peak_MW']['raw']*1000/NN['peak_target_kW']['raw']-NN['satellites']['raw'])<1e-9
txt(LX,20.25,'PROBLEM',size=30,weight='bold',color=teal)
pa=fit_body(LX,19.70,problem,LW,24,leading=LEFT_LEAD)
EFF=json.loads((R/'evidence/effort/EFFORT_UPDATE_R17.json').read_text());EFF_DAYS=str(round(EFF['elapsed_days_to_cutoff']));assert EFF_DAYS=='12' and TITLE.endswith(f'in {EFF_DAYS} Days')
WHY=f"AI agents and GPU acceleration allow rapid digital prototyping; {EFF_DAYS} coworking days for an engineer to go from concept to a chosen architecture ready for detailed design."
WHY_ARCH=os.environ.get('R20_WHY_ARCH','mechanical and thermal');WHY_ARCH='' if WHY_ARCH=='none' else WHY_ARCH;assert WHY_ARCH in ('','mechanical and thermal','mechanical')  # owner t967 preview wording; default '' = r20 text unchanged
if WHY_ARCH:WHY=WHY.replace('a chosen architecture',f'a chosen {WHY_ARCH} architecture')
WHY_BOX=None
if not WHYBOX:
 why_low=labelled_early('Why it matters:',WHY,bottom(pa)-.12,color=teal)
 ay=why_low-.07
else:
 # box option: padding .15 in on all sides; A = 12% accent tint + solid .13 in left accent bar (no border); B = thin rounded accent border + 5% tint
 WB_PAD=.15;WB_BAR=.12 if WHYBOX=='A' else 0.0;WB_RPAD=.10 if WHYBOX=='A' else .15;wb_top=bottom(pa)-.08  # A: wrap limit .10 in from the box edge (longest printed line still clears it by >=.15 in, checked below)
 wx=LX+WB_BAR+WB_PAD;ww=LW-WB_BAR-WB_PAD-WB_RPAD
 why_low=labelled_early('Why it matters:',WHY,wb_top-WB_PAD,color=teal,x=wx,width=ww)
 wb_bot=why_low+LEFT_GAP-WB_PAD
 from matplotlib.patches import FancyBboxPatch
 if WHYBOX=='A':
  fig.add_artist(Rectangle((LX/43,wb_bot/24),LW/43,(wb_top-wb_bot)/24,transform=fig.transFigure,facecolor=teal,alpha=.12,edgecolor='none',zorder=-1))
  fig.add_artist(Rectangle((LX/43,wb_bot/24),WB_BAR/43,(wb_top-wb_bot)/24,transform=fig.transFigure,facecolor=teal,edgecolor='none',zorder=-1))
 else:
  fig.add_artist(FancyBboxPatch((LX,wb_bot),LW,wb_top-wb_bot,boxstyle='round,pad=0,rounding_size=.12',transform=fig.dpi_scale_trans,facecolor=(0x23/255,0x79/255,0x68/255,.05),edgecolor=teal,lw=2.0,zorder=-1))
 _wl=[t_ for t_ in fig.texts[-3:] if t_.get_text()];_wr=max(t_.get_position()[0]*43+max(TextPath((0,0),ln_,size=24,prop=FontProperties(family='DejaVu Sans',weight=t_.get_fontweight())).get_extents().x1/72 for ln_ in t_.get_text().split('\n')) for t_ in _wl);WB_RCLEAR=LX+LW-_wr;assert WB_RCLEAR>=.12-1e-6,('why box right clearance (glyph ink)',WB_RCLEAR)  # longest line's ink to the right box edge
 WHY_BOX=dict(right_clear_in=WB_RCLEAR,variant=WHYBOX,bounds_in=[LX,wb_bot,LX+LW,wb_top],pad_in=WB_PAD,bar_in=WB_BAR,text_x_in=wx,text_w_in=ww)
 ay=wb_bot-.17
archhead=txt(LX,ay,'DESIGN ARCHITECTURE (PER SATELLITE)',size=30,weight='bold',color=teal)
ay=bottom(archhead)-.15
# r19: hinge count includes the 5 Newton width hinges (matches Panel 4: 21 wing + 5 width + 10 radiator); re-asserted in Panel 4
_wfj=json.loads((R/'poster_inputs/wfold_newton_tw120_dt0.01.json').read_text());assert _wfj['all_latched'];N_HINGES_LEFT=str(NN['hinge_locks']['raw']+len(_wfj['t_latch_s']));used.append('hinge_locks')
# r20 final (owner t981): orbit item, frame mass from the model (45.7 kg -> '≈46'), hard limits and search variables in Panel 1
_ECL=json.loads((R/'native/stages/orbit/ECLIPSE_600KM.json').read_text());assert _ECL['h_km']==600 and _ECL['ltan_h']==6.0 and 97<_ECL['inc_deg']<98.5  # 600 km, LTAN 06:00 = dawn-dusk, sun-synchronous inclination
_EOD=(R/'native/stages/orbit/eclipse_600km.py').read_text();assert '600 km circular dawn-dusk SSO' in _EOD
_ENV=(R/'native/inputs/repo/src/rack_two_skies/env_leo.py').read_text();assert 'beta >= 45 deg (dawn-dusk) -> n = along-track' in _ENV and 'per radiating face' in _ENV  # radiator normal along-track = edge-on to the Sun; both faces radiate
assert 'both faces radiating' in (R/'sweep/fin_al_benchmark.py').read_text()
ORBIT_TXT="600 km dawn-dusk sun-synchronous. Arrays face the Sun; radiators assumed edge-on to it, radiating from both faces."
FRAME_SHOWN=f"≈{round(NN['frame_kg']['raw'])}";assert FRAME_SHOWN=='≈46' and abs(NN['frame_kg']['raw']-45.7)<.05;used.append('frame_kg')
architecture=[
('Compute:', f"one Vera Rubin NVL72 (72 GPUs + 36 CPUs); {n('peak_target_kW')} kW peak at beginning of life. Assumed 640.38 kg payload allocation in a 600 × 1200 × 937 mm box."),
('Launch fit:', f"All {n('satellites')} satellites fit in one Starship: {n('satellites')} × {n('sc_mass_kg')} kg = {n('fleet_t')} t + {n('dispenser_t')} t dispenser + {n('reserve_t')} t reserve = {n('launch_t')} t; stowed stack {pack_top} m tall in the modeled 17.24 m payload envelope (≥{pack_rad} mm radial margin)."),
('Orbit:', ORBIT_TXT),
('Power:', f"{n('solar_area_m2')} m² solar array; assumed module rating {n('module_rating_W_m2')} W/m² on its remaining planar area; {n('nominal_kW')} kW {POWER_PHRASE} and a {n('annual_kW')} kW annual average, including eclipse."),
('Thermal:', f"{n('radiator_panels')} radiator panels; coating emissivity {n('emissivity')}. Fins and tubes selected by search; modeled glycol-water loop. Cold-plate resistance assumed for Rubin GPU and HBM.\n{n('nominal_kW')} kW {LOAD_PHRASE}: rack coolant {th('nom_rack_in')} K to {th('nom_rack_out')} K; Rubin GPU est. {th('nom_GPU_rubin')} K (target ≈{n('device_target_K')} K), HBM {th('nom_HBM_rubin')} K (limit 378 K).\n{n('peak_target_kW')} kW peak (steady state): rack coolant {th('pk_rack_in')} K to {th('pk_rack_out')} K; Rubin GPU est. {th('pk_GPU_rubin')} K, HBM est. {th('pk_HBM_rubin')} K."),
('Rack structure:', f"Compute rack screening (CalculiX beam model, 6 g axial / 2 g lateral, FS 1.25): a {FRAME_SHOWN} kg aluminum frame inside the 640 kg allocation reaches {n('frame_f1_Hz')} Hz (rack design target) with large strength margins."),
('Panel vibration:', f"Stowed radiator-panel first mode {n('panel_f1_min_Hz')}–{n('panel_f1_max_Hz')} Hz across support-pad assumptions (≈{n('panel_f1_nominal_Hz')} Hz nominal), well above the 35 Hz reference."),
('Folding and deployment:', f"All {N_HINGES_LEFT} representative hinges lock in a rigid Newton simulation; a sampled clearance check finds no collisions.")]
for label,para in architecture:ay=labelled(label,re.sub(r'(\d) K\b','\\1\u00a0K',para) if label=='Thermal:' else para,ay)
CLOSING='A basis for further detailed design. Simulation study, not flight qualification.'  # owner t996: moved to the footer, below the Targets line
class _Top:  # left-column text now ends at the last architecture item
 def __init__(s_,y):s_.y=y
closing=_Top(ay+LEFT_GAP)
LAYOUT=os.environ.get('POSTER_LAYOUT','A');assert LAYOUT in ('A','B')
from matplotlib import patheffects as pe
# Option A: release frame + labelled hero side by side in the left image area.
# Option B: release frame alone in the left image area; hero satellite cut-out (background removed) on white in the header, labelled.
if LAYOUT=='A':
 from matplotlib import patheffects as pe
 rel_img=plt.imread(release_png);hero_full=plt.imread(hero_png)
 HC=(650,216,3650,1814)  # hero crop x0,y0,x1,y1 px (whitespace trim only)
 hero_img=hero_full[HC[1]:HC[3],HC[0]:HC[2]]
 ar_rel=rel_img.shape[1]/rel_img.shape[0];ar_hero=hero_img.shape[1]/hero_img.shape[0];igap=.20
 IMG_H_FULL=(LW-igap)/(ar_rel+ar_hero);img_h=IMG_H_FULL;REL_COL=IMG_H_FULL*ar_rel;HERO_COL=IMG_H_FULL*ar_hero
 # r20 final (owner t981): captions keep the full-size column widths; if the text needs the room, both images shrink together (aspect kept), each centred over its caption column
 rel_cap=wrap(RELEASE_CREDIT,REL_COL);hero_cap=wrap(HERO_CREDIT,HERO_COL)
 # owner t997: 'Omniverse Isaac Sim RTX' only if the caption block keeps its line count (no image height lost)
 _omni=HERO_CREDIT.replace('Illustrative Isaac Sim RTX render','Illustrative Omniverse Isaac Sim RTX render');_omni_cap=wrap(_omni,HERO_COL)
 HERO_OMNI=dict(lines_without=len(hero_cap),lines_with=len(_omni_cap),release_lines=len(rel_cap),used=max(len(rel_cap),len(_omni_cap))<=max(len(rel_cap),len(hero_cap)))
 if HERO_OMNI['used'] and os.environ.get('R20_HERO_OMNI','1')=='1':HERO_CREDIT=_omni;hero_cap=_omni_cap
 else:HERO_OMNI['used']=False
 credit_h=.415*max(len(rel_cap),len(hero_cap))
 img_bottom=1.0+credit_h+.12;img_top=closing.y-.15
 img_h=min(IMG_H_FULL,math.floor((img_top-img_bottom)*300+1e-9)/300);rel_w=img_h*ar_rel;hero_w=img_h*ar_hero
 LEFT_SLACK_IN=img_top-img_bottom-img_h
 IMG_SCALE=img_h/IMG_H_FULL;assert IMG_SCALE>=.90,('images shrink more than 10%',IMG_SCALE)
 IMG_X0=LX+(REL_COL-rel_w)/2;HERO_X0=LX+REL_COL+igap+(HERO_COL-hero_w)/2
 if os.environ.get('R19_DEBUG_LEFT'):print('LEFT',img_top,img_bottom,img_h,LEFT_SLACK_IN,[(t_.get_text()[:30],round(bottom(t_),3)) for t_ in zone_artists['left'] if hasattr(t_,'get_text')]);sys.exit(0)
 assert LEFT_SLACK_IN>=-1e-6,('left column text overflows the image row (r19 keeps r17 image size)',img_top,img_bottom,img_h)
 img_y=img_bottom+(img_top-img_bottom-img_h)/2;img_y=math.floor(img_y*300+1e-9)/300  # r19: snap to the 300 dpi grid so both images land on the same device pixel rows
 rel_ax=fig.add_axes([IMG_X0/43,img_y/24,rel_w/43,img_h/24]);rel_ax.imshow(rel_img);rel_ax.axis('off');rel_ax._poster_zone=zone;zone_artists.setdefault(zone,[]).append(rel_ax)
 hero=fig.add_axes([HERO_X0/43,img_y/24,hero_w/43,img_h/24]);hero.imshow(hero_img);hero.axis('off');hero._poster_zone=zone;zone_artists.setdefault(zone,[]).append(hero)
 hero_h=img_h
 # Labels as poster vector text (>=24 pt at print size) with leader lines; tips from the r13 labelled hero (preview px x3.75), shifted by the crop.
 LBL_PT=26;hero_labels=[]
 for text,txy,tip,lva in [('Solar Array',(480,474),(626,364),'bottom'),('Radiator',(700,72),(688,198),'top')]:
  tx,ty=txy[0]*3.75-HC[0],txy[1]*3.75-HC[1];px,py=tip[0]*3.75-HC[0],tip[1]*3.75-HC[1]
  an=hero.annotate(text,xy=(px,py),xytext=(tx,ty),xycoords='data',textcoords='data',fontsize=LBL_PT,fontweight='bold',color='white',ha='center',va=lva,
   arrowprops=dict(arrowstyle='-',color='white',lw=1.6,shrinkA=2,shrinkB=0),bbox=dict(boxstyle='round,pad=0.15',fc=(0,0,0,.55),ec='none'))  # real text spans (path effects would outline-convert)
  hero.plot([px],[py],'o',ms=6,mfc='white',mec='black',mew=1);hero_labels.append(an);alltexts.append(text)
 hero.set_xlim(0,hero_img.shape[1]);hero.set_ylim(hero_img.shape[0],0)
 rel_credit=txt(LX,img_y-.08,'\n'.join(rel_cap),size=24,linespacing=1.04,color=muted)
 credit=txt(LX+REL_COL+igap,img_y-.08,'\n'.join(hero_cap),size=24,linespacing=1.04,color=muted)
 alltexts.append(RELEASE_CREDIT)
else:
 rel_img=plt.imread(release_png);cut=plt.imread(R/'poster_inputs/HERO_R13_CUTOUT.png');HC=(0,0,cut.shape[1],cut.shape[0]);hero_img=cut
 HERO_CREDIT_B='Header image: satellite cut out of the illustrative Isaac Sim RTX render (contrast enhanced); not flight validation.'
 cap_lines=wrap(RELEASE_CREDIT+' '+HERO_CREDIT_B,LW);credit_h=.415*len(cap_lines)
 img_bottom=1.0+credit_h+.12;img_top=closing.y-.15;ar_rel=rel_img.shape[1]/rel_img.shape[0]
 img_h=min(img_top-img_bottom,LW/ar_rel);rel_w=img_h*ar_rel;img_y=img_bottom+(img_top-img_bottom-img_h)/2
 rel_ax=fig.add_axes([(LX+(LW-rel_w)/2)/43,img_y/24,rel_w/43,img_h/24]);rel_ax.imshow(rel_img);rel_ax.axis('off');rel_ax._poster_zone=zone;zone_artists.setdefault(zone,[]).append(rel_ax)
 rel_cap=cap_lines;hero_cap=[]
 rel_credit=txt(LX,img_y-.08,'\n'.join(cap_lines),size=24,linespacing=1.04,color=muted);credit=rel_credit
 alltexts.append(RELEASE_CREDIT+' '+HERO_CREDIT_B)
 # header cut-out: free band right of the workflow boxes, below the title, left of the QR
 zone='header';hx0=1+workflow_width+2.35;hx1=YTX-.25;hy0,hy1=20.50,22.00  # r16: stop left of the YouTube QR slot
 hero_h=hy1-hy0;hero_w=hero_h*cut.shape[1]/cut.shape[0]
 hcx=(hx0+hx1)/2;hero=fig.add_axes([(hcx-hero_w/2)/43,hy0/24,hero_w/43,hero_h/24]);hero.imshow(cut);hero.axis('off');hero._poster_zone=zone;zone_artists.setdefault(zone,[]).append(hero)
 LBL_PT=26;hero_labels=[]
 # tips (cut-out px): left wing centre, radiator upper end
 for text,tip,xyt,ha in [('Solar Array',(560,330),(-.04,.80),'right'),('Radiator',(1850,180),(1.04,.80),'left')]:
  an=hero.annotate(text,xy=tip,xytext=xyt,xycoords='data',textcoords='axes fraction',fontsize=LBL_PT,fontweight='bold',color=ink,ha=ha,va='center',arrowprops=dict(arrowstyle='-',color=ink,lw=1.4,shrinkA=3,shrinkB=0))
  hero.plot([tip[0]],[tip[1]],'o',ms=5,mfc='white',mec=ink,mew=1);hero_labels.append(an);alltexts.append(text)
 hero.set_xlim(0,cut.shape[1]);hero.set_ylim(cut.shape[0],0)
 zone='left'

# ---- r15 panels: all positions relative to panel origin (x0=left, T=top). Content x0+.20 .. x0+PW-.20.
from matplotlib.colors import ListedColormap,BoundaryNorm
HL=.52  # 36 pt headline line pitch
# 1: search
panel('m1','1  What did the search find? | Warp')
x0,T=PX1,PY1+PH;CW=PW-.40
headline(x0,T,[f"{n('configurations')}M radiator designs screened on GPU;",f"{n('hard_feasible')} pass every hard limit"])
# r16: sensitivity table removed (owner request); sensitivity analysis stated in words under the chart. Scatter gets the panel width.
fp24=FontProperties(family='DejaVu Sans')
SCX=x0+1.60;KEYW=3.55;SCW=x0+PW-.20-KEYW-.30-SCX  # scatter axes; key column on the right
_MC=json.loads(mc_json.read_text());assert _MC['draws']==1048576 and len(_MC['ranges'])==14
_SW=json.loads((R/'sweep/SWEEP_INPUTS.json').read_text());MARGIN_K=_SW['inlet_cap_K']-_SW['design_inlet_K'];assert MARGIN_K==1.0
MCN={'n_inputs':str(len(_MC['ranges'])),'p_gpu370':str(round(100*_MC['P_GPU_le_370'])),'gpu_p50':format(_MC['statistics']['GPU_nominal_K']['quantiles']['p50'],'.1f'),'margin':str(int(MARGIN_K))}
assert MCN['gpu_p50']==NN['gpu_mc_median_K']['shown'] and MCN['p_gpu370']=='65' and _MC['P_HBM_le_378p15']==1.0
_SI=json.loads((R/'sweep/SWEEP_INPUTS.json').read_text());_GC=(R/'sweep/gpu_core.py').read_text();assert (R/'gb10_out/r11/gpu_core.py').read_text()==_GC
_PN=ast.literal_eval(re.search(r'P_NAMES = (\[.*?\])',_GC).group(1));assert (_PN[31],_PN[34],_PN[43])==('packAmax','packNmax','peak_power_acceptance_W')
assert 'if n <= p[34] and arr <= p[31] + wp.float64(1e-06) and pavail >= p[43] and (m <= wp.float64(3266.6666666666665)) and (T[0] <= wp.float64(370.0)) and (T[2] <= wp.float64(393.0)):' in _GC  # the six hard limits
assert _SI['packing_verified_max_panels']==140 and abs(_SI['packing_verified_max_array_m2']-861.75)<.01 and _SI['peak_power_acceptance_W']==249900.0 and _SI['gpu_cap_K']==370.0 and _SI['inlet_cap_K']==393.0
HARD_MASS=f"{round(3266.6666666666665):,}";assert HARD_MASS=='3,267' and round(_SI['peak_power_acceptance_W']/1000)==250
HARD_TXT=f"Hard limits: GPU ≤{int(_SI['gpu_cap_K'])} K, radiator inlet ≤{int(_SI['inlet_cap_K'])} K, ≤{HARD_MASS} kg, fits the launch envelope, {round(_SI['peak_power_acceptance_W']/1000)} kW at start of life."
_GRID=json.loads((GB/'SWEEP_GB10_GPU.json').read_text()).get('grid') or {};assert list(_GRID)==['panel_count','tubes','fin_thickness_mm','array_growth_fraction'],_GRID
SEARCH_TXT="Search varied panel count, tubes per panel, fin thickness and array size."
SENS=(f"{SEARCH_TXT} "
 f"{n('hard_feasible')} of {n('configurations')}M designs meet every hard limit; lightest with {MCN['margin']} K extra margin chosen, then {n('scenario_draws')}M what-if runs co-varied {MCN['n_inputs']} inputs over assumed ranges, not measured probabilities. "
 f"At {n('nominal_kW')} kW {LOAD_PHRASE} (screening model): GPU median {n('gpu_mc_median_K')} K, under 370 K in {MCN['p_gpu370']}% of runs; HBM under 378 K in all runs. "
 "Radiator emissivity and power conversion efficiency move temperatures most; cold-plate resistance mainly moves the GPU and rack temperature rise mainly moves the coolant.")
SENS_LEAD=1.06
sc_top=T-2.05+G1;sc_bot=(PY1+PB)+text_h(SENS,CW,24,SENS_LEAD)+.82;assert sc_top-sc_bot>=PLOT_MIN['m1']-1e-9,('panel 1 plot below r19 size',sc_top-sc_bot)
a=axes(SCX,sc_bot,SCW,sc_top-sc_bot);m1_scatter_ax=a
arr=np.load(sweep_npz)['values'];cols=list(np.load(sweep_npz)['columns']);ci=lambda c:cols.index(c)
feas=arr[:,ci('hard_feasible')]==1;assert int(feas.sum())==NN['hard_feasible']['raw'],int(feas.sum())
pc=arr[feas,ci('radiator_panels')];levels=np.unique(pc).astype(int)
cmap=ListedColormap(plt.get_cmap('viridis')(np.linspace(0,.92,len(levels))));norm=BoundaryNorm(np.r_[levels-.5,levels[-1]+.5],cmap.N)
_inv=(arr[:,ci('sc_mass_kg')]>=2900)&(arr[:,ci('sc_mass_kg')]<=3350)&(arr[:,ci('inlet_peak_K')]>=378)&(arr[:,ci('inlet_peak_K')]<=404)  # r20 preview: drop clipped out-of-view gray points (they sat outside the page margin as invisible PDF drawings once the plot got taller)
m1_gray=a.scatter(arr[~feas&_inv,ci('sc_mass_kg')],arr[~feas&_inv,ci('inlet_peak_K')],color='#d4d8db',s=5,linewidths=0,zorder=1)
o=np.argsort(-pc)
m1_sc=a.scatter(arr[feas,ci('sc_mass_kg')][o],arr[feas,ci('inlet_peak_K')][o],c=pc[o],cmap=cmap,norm=norm,s=7,linewidths=0,zorder=3)
a.set_xlim(2900,3350);a.set_ylim(378,404);a.set_xticks([2900,3000,3100,3200,3300]);a.set_yticks([380,390,400])
a.axhline(393,color='#a23a31',ls='--',zorder=4);ref393=a.text(.985,393+.5,'393 K radiator-inlet design reference',transform=a.get_yaxis_transform(),fontsize=24,color='#a23a31',va='bottom',ha='right',zorder=5,bbox=dict(boxstyle='square,pad=0.05',fc='white',ec='none',alpha=.85))
m1_chosen=a.scatter(NN['solver_mass_kg']['raw'],NN['coolant_inlet_peak_K']['raw'],marker='D',s=170,color=orange,edgecolor=ink,zorder=6)
P1_YL='Coolant temp. at radiator\ninlet, steady 250 kW (K)';assert NN['peak_target_kW']['shown']=='250'
a.set(xlabel='Satellite mass (kg)',ylabel=P1_YL)
alltexts+=['393 K radiator-inlet design reference','Satellite mass (kg)',P1_YL.replace('\n',' ')]
# key column (right of the scatter): colour bar + dot/diamond legend + lightest chosen
KX=x0+PW-.20-KEYW
cb_lab=txt(KX,sc_top+.02,'Radiator panels',size=24,weight='bold')
cax=fig.add_axes([(KX+.05)/43,(bottom(cb_lab)-.30)/24,(KEYW-.35)/43,.20/24])  # bounds-checked globally
cb=fig.colorbar(m1_sc,cax=cax,orientation='horizontal',ticks=[levels[0],levels[-1]]);cb.ax.tick_params(labelsize=24,length=0,pad=3);cb.outline.set_linewidth(.6)
alltexts+=[str(levels[0]),str(levels[-1])]
m1_cb_ticks=[t.get_text() for t in cb.ax.get_xticklabels()]
key1=fit_body(KX,bottom(cb_lab)-.80,'Each colored dot passes every hard limit; gray fails.',KEYW,24,leading=1.0)  # r20 final (owner t981): key tightened (-.95 -> -.80, gaps .15 -> .10, leading 1.0) so the hard-limits list fits without splitting a number from its unit
key2=fit_body(KX+.42,bottom(key1)-.10,"= chosen design.",KEYW-.42,24,leading=1.0)  # owner t996: legend marker drawn with the plotted marker's exact properties (was an ink-coloured ◆ glyph)
_kb=key2.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted());_kax=fig.add_axes([KX/43,_kb.y0/24,.36/43,(_kb.y1-_kb.y0)/24]);_kax.set_xlim(0,1);_kax.set_ylim(0,1);_kax.axis('off');_kax._poster_zone=zone;zone_artists.setdefault(zone,[]).append(_kax)
m1_key_marker=_kax.scatter([.5],[.5],marker='D',s=m1_chosen.get_sizes()[0],facecolors=m1_chosen.get_facecolors(),edgecolors=m1_chosen.get_edgecolors(),linewidths=m1_chosen.get_linewidths(),zorder=6,clip_on=False)
_props=lambda c_:dict(size=float(c_.get_sizes()[0]),face=[round(float(v),6) for v in c_.get_facecolors()[0]],edge=[round(float(v),6) for v in c_.get_edgecolors()[0]],lw=float(c_.get_linewidths()[0]),path=[[round(float(v),6) for v in xy] for xy in c_.get_paths()[0].vertices])
M1_MARKER=dict(chart=_props(m1_chosen),key=_props(m1_key_marker));assert M1_MARKER['chart']==M1_MARKER['key'],M1_MARKER  # r19 (owner t932): 'Lightest chosen (...)' removed
key3=fit_body(KX,bottom(key2)-.10,re.sub(r'(\d) (K|kg|kW)\b','\\1\u00a0\\2',HARD_TXT),KEYW,24,leading=1.0,keep_nbsp=True);  # number and unit never split
alltexts.append(HARD_TXT)  # r20 final (owner t981): the six hard limits, under the key
m1_key_bottom=bottom(key3)
if os.environ.get('R20_DEBUG_M1'):print('M1',sc_top,sc_bot,m1_key_bottom,sc_top-sc_bot)
M1_KEY_CLEAR=m1_key_bottom-(sc_bot-.82);assert M1_KEY_CLEAR>=.12-1e-6,('panel 1 key column runs into the caption',m1_key_bottom,sc_bot)  # key column sits right of the scatter, so it may use the x-axis label band but must clear the caption top by >=.12 in
_RS={r_['input']:r_ for r_ in _MC['rank_sensitivity']};_rr=lambda r_:max(abs(r_['inlet']),abs(r_['GPU']),abs(r_['HBM']))
assert min(_rr(_RS['PMAD']),_rr(_RS['emissivity']))>max(_rr(r_) for k_,r_ in _RS.items() if k_ not in ('PMAD','emissivity'))  # top-2 drivers beat all 12 others
assert abs(_RS['plate_resistance']['GPU'])>10*max(abs(_RS['plate_resistance']['inlet']),abs(_RS['plate_resistance']['HBM'])) and abs(_RS['rack_rise']['inlet'])>5*max(abs(_RS['rack_rise']['GPU']),abs(_RS['rack_rise']['HBM']))
alltexts.append(SENS)
sens_text=fit_body(x0+.20,sc_bot-.82,SENS,CW,24,leading=SENS_LEAD)
_ = n('solver_mass_kg'); _ = n('screen_mass_kg'); _ = n('radiator_panels')
# 2: benchmark — two strips, three bars each (GPU, 1 CPU core, all 20 CPU cores).
SPF=R/'speed/SPEED_NUMBERS_R11.json';SP=json.loads(SPF.read_text())['numbers']
def s(k):used.append('speed:'+k);return SP[k]['shown']
ACF=R/'speed/SPEED_ALLCORE_R11.json';AC=json.loads(ACF.read_text())
assert 'bitwise identical' in AC['sweep']['output_check'] and 'bitwise identical' in AC['mc']['output_check'] and AC['machine']['kernel_sha256']==json.loads((GB/'SWEEP_GB10_GPU.json').read_text())['kernel_sha256']
ACN={'sweep_cpu20_s':format(AC['sweep']['cpu_20core_s_median'],'.3f'),'sweep_x20':format(AC['sweep']['speedup_gpu_vs_20core'],'.2f'),'mc_cpu20_s':format(AC['mc']['cpu_20core_s_median'],'.3f'),'mc_x20':format(AC['mc']['speedup_gpu_vs_20core'],'.2f')}
def ac(k):used.append('allcore:'+k);return ACN[k]
panel('m2','2  How much did the GPU speed it up? | GB10 benchmark')
x0,T=PX2,PY1+PH
GPUC=teal;CPUC='#798b96';CPU20C='#4e5f6a'
headline(x0,T,[f"{n('speedup_x')}× faster than one GB10 CPU core;",f"{ac('sweep_x20')}× faster than all 20 cores"])
m2_bar_axes=[]
AXL=x0+4.05
m2_bar_orders=[]
def three_bar(title,vals,shows,ratios,y,h,xmax):
 # r16 (owner request): bars ordered smallest (top) to biggest (bottom) by measured time
 rows=sorted(zip(['GB10 GPU','GB10 CPU, 1 core','GB10 CPU, all 20 cores'],[GPUC,CPUC,CPU20C],['gpu','cpu1','cpu20'],vals,shows,ratios),key=lambda r:r[3])
 m2_bar_orders.append([r[0] for r in rows])
 txt(x0+.20,y+h+.40,title,size=28,weight='bold',color=teal)
 a=axes(AXL,y,x0+PW-.20-AXL,h)
 ys=[2,1,0];bars=a.barh(ys,[r[3] for r in rows],color=[r[1] for r in rows],height=.66);a._poster_bar_artists=[(b,r[2],a) for b,r in zip(bars,rows)]
 a.set_xlim(0,xmax);a.set_ylim(-.5,2.5)
 a.set_yticks(ys,[r[0] for r in rows]);a.set_xticks([]);a.spines['bottom'].set_visible(False);a.grid(False);a.tick_params(labelsize=24,length=0)
 for i,r in zip(ys,rows):
  lab=r[4]+' s'+(f'  ({r[5]}×)' if r[5] else '');alltexts.append(lab);a.text(r[3]+.012*xmax,i,lab,va='center',fontsize=26,fontweight='bold',color=ink)
 m2_bar_axes.append(a)
assert SP['speedup_x']['shown']==NN['speedup_x']['shown'] and SP['sweep_gpu_s']['shown']==NN['gpu_kernel_s']['shown'] and SP['sweep_cpu_s']['shown']==NN['cpu_kernel_s']['shown']
P2_FIND=f"{n('speedup_x')}× faster than one GB10 CPU core; {ac('sweep_x20')}× faster than all 20 cores."
P2_XO=f"Versus one core, the GPU pulls ahead above about 1,000 designs and levels off at 32–33× from about 260,000 designs to the full {n('configurations')}M."
P2_FN="Same double-precision math on all; median of 3 runs; timing excludes setup and compile. GPU: Warp kernels on CUDA. CPU: 1 Arm Cortex-X925 core in the GB10 Grace Blackwell, 1 thread. All cores: the same Warp fp64 code on all 20 cores (10 X925 + 10 A725), not hand-tuned CPU code."  # owner t998/t999: CUDA (GB10 GPU timing path = Warp kernels on cuda:0, SWEEP_GB10_GPU.json device) + full GB10 Grace Blackwell name; costs one caption line (bars give up height, stay >= r19 1.62 in)
_h2=text_h(P2_FIND,CW,24,1.04,'bold')+.10+text_h(P2_XO,CW,24,1.04)+.10+text_h(P2_FN,CW,24,1.04)
P2_TXT_TOP=(PY1+PB)+_h2;_d2=P2_TXT_TOP-(T-6.45)  # r20: bars keep the r19-preview title position; strips give up height to the extra finding line
SH=2.13-_d2/2;Y2=T-6.30+_d2;Y1=Y2+SH+.54;assert SH>=PLOT_MIN['m2']-1e-9,('panel 2 bars below r19 size',SH)
BAR4={'sw_gpu':format(NN['gpu_kernel_s']['raw'],'.4f'),'sw_cpu':format(NN['cpu_kernel_s']['raw'],'.3f'),'sw_20':format(AC['sweep']['cpu_20core_s_median'],'.4f'),'mc_gpu':format(SP['mc_gpu_s']['raw'],'.4f'),'mc_cpu':format(SP['mc_cpu_s']['raw'],'.3f'),'mc_20':format(AC['mc']['cpu_20core_s_median'],'.4f')}  # final r20 (S10): 4 significant figures so every printed ratio = ratio of the printed bar times at the printed precision
_rt=lambda a_,b_,d_=1:format(float(BAR4[a_])/float(BAR4[b_]),f'.{d_}f')
assert _rt('sw_cpu','sw_gpu')==n('speedup_x') and _rt('sw_20','sw_gpu',2)==ac('sweep_x20') and _rt('mc_cpu','mc_gpu')==s('mc_speedup_x') and _rt('mc_20','mc_gpu',2)==ac('mc_x20'),BAR4
assert [format(float(BAR4[k_]),'.3g') for k_ in ('sw_gpu','sw_cpu','mc_gpu','mc_cpu')]==[n('gpu_kernel_s'),n('cpu_kernel_s'),s('mc_gpu_s'),s('mc_cpu_s')]  # same records, one more digit
three_bar(f"Search, {n('configurations')}M designs",[NN['gpu_kernel_s']['raw'],NN['cpu_kernel_s']['raw'],AC['sweep']['cpu_20core_s_median']],[BAR4['sw_gpu'],BAR4['sw_cpu'],BAR4['sw_20']],[None,n('speedup_x'),ac('sweep_x20')],Y1,SH,NN['cpu_kernel_s']['raw']*1.62)
three_bar(f"Sensitivity analysis, {n('scenario_draws')}M what-if runs",[SP['mc_gpu_s']['raw'],SP['mc_cpu_s']['raw'],AC['mc']['cpu_20core_s_median']],[BAR4['mc_gpu'],BAR4['mc_cpu'],BAR4['mc_20']],[None,s('mc_speedup_x'),ac('mc_x20')],Y2,SH,SP['mc_cpu_s']['raw']*1.62)
_=s('crossover_high');_=s('scale_full_ratio')
assert SP['crossover_low']['raw']<1000<=SP['crossover_high']['raw'] and SP['scale_full_ratio']['shown']=='33.0' and all(31.95<=r_['ratio']<33.05 for r_ in SP['scaling_rows']['raw'] if r_['designs']>=262144) and any(r_['designs']==262144 for r_ in SP['scaling_rows']['raw'])  # r18/r19: 'about 33x from about 260,000 designs'  # "above about 1,000" = first measured N where the GPU wins (1,024); "about 33×" = full-grid scaling ratio 33.0
p2find=fit_body(x0+.20,P2_TXT_TOP,P2_FIND,CW,24,weight='bold',leading=1.04)
xover=fit_body(x0+.20,bottom(p2find)-.10,P2_XO,CW,24,leading=1.04)
p2fn=fit_body(x0+.20,bottom(xover)-.10,P2_FN,CW,24,leading=1.04,color=muted)
# 3: surrogate + Warp autodiff
panel('m3','3  Can we trust the search? | PhysicsNeMo / Warp autodiff')
x0,T=PX1,PY3+PH
headline(x0,T,['Radiator fin heat conduction: max |Δη| = '+n('surrogate_heldout_max_abs_eta')])
P3_EXPL=f"A PhysicsNeMo neural model learns radiator fin efficiency from Warp solver results ({n('surrogate_train')} training fins), then is checked on {n('surrogate_heldout')} fins it never saw, so a fast learned model can stand in for the solver when screening fin shapes. Max\u00a0|Δη|\u00a0=\u00a0{n('surrogate_heldout_max_abs_eta')}."
CAP_Y=T-5.0  # provisional; the whole caption block is shifted to sit PB above the panel bottom, then the plot fills the rest
p3expl=fit_body(x0+.20,CAP_Y,P3_EXPL,CW,24,leading=1.04,keep_nbsp=True)
_OPT=json.loads((R/'gb10_out/r11/OPT_GB10_GPU.json').read_text());assert {g_['parameter'] for g_ in _OPT['gradient_check']}=={'panel_relaxation','fin_length','fin_thickness'} and all(g_['passed'] and g_['relative_error']<3e-3 and 'finite_difference' in g_ for g_ in _OPT['gradient_check']) and format(abs(_OPT['sweep_cross_check']['relative_difference'])*100,'.2f')==n('tape_gap_pct')
P3_CAV=f"The chosen design's fins were re-solved with Warp, so no final number rests on the learned model. A Warp autodiff optimizer, treating panel count and fin size as continuous, comes within {n('tape_gap_pct')}% of the search's lightest radiator. Its gradients match finite differences; it is a local check, not a global optimum."  # final r20 (owner t974): fin-efficiency equation removed
p3cav=fit_body(x0+.20,bottom(p3expl)-.12,P3_CAV,CW,24,leading=1.04);_=n('tape_gradient_max_rel_err')
_dy3=(PY3+PB)-bottom(p3cav);shift([p3expl,p3cav],_dy3);CAP3=CAP_Y+_dy3
_h3=(T-1.70+G3)-(CAP3+1.05);assert _h3>=PLOT_MIN['m3']-1e-9,('panel 3 plot below r19 size',_h3)
a=axes(x0+1.75,CAP3+1.05,PW-1.75-.55,_h3);m3_ax=a;sv=np.load(sv_npz);a.scatter(sv['true'],sv['prediction'],s=30,c=blue);lim=[min(sv['true']),max(sv['true'])];a.plot(lim,lim,color=ink,ls='--');a.set(xlabel='Warp solver: radiator fin efficiency η',ylabel='PhysicsNeMo\nprediction η')
# 4: deployment (solar from the solar Newton trace; radiator from the corrected radiator Newton trace, which starts at t = 1,080 s on the deploy clock: check_actual_traces.py pairs radiator sample k with solar sample 1080+k)
panel('m4','4  Does it deploy? | Newton / Warp')
x0,T=PX2,PY3+PH
headline(x0,T,["Satellite Unfolding After Release","from Launch Vehicle"])
RAD_T0=1080.0
CAP4=T-5.92;a=axes(x0+1.40,CAP4+1.05,PW-1.40-.55,(T-2.00+G4)-(CAP4+1.05));m4_ax=a;d=np.load(newton_npz);h=np.degrees(d['h_newton']);w=np.degrees(d['h_warp']);rd=np.load(radiator_npz);rh=np.degrees(rd['h_newton'])
# r19: solar-wing WIDTH spread (Newton tw120 run, 5 hinges / 6 sections) placed at t=960 s on the deploy clock (NOTES_t890: width spread 960-1,080 s); dt=0.005 run = convergence check
WD_T0=960.0;wf=np.load(wfold_npz);wfj=json.loads(wfold_json.read_text());wf2=json.loads(wfold_json_conv.read_text());wq=np.degrees(wf['q'])
assert wfj['all_latched'] and wfj['n_sections']==6 and wq.shape[1]==5 and wfj['tw_s']==120.0
assert all(1060<=t_+WD_T0<=1072 for t_ in wfj['t_latch_s']) and WD_T0+wfj['settle_time_s_within_0p1deg']<=1080 and abs(wfj['settle_time_s_within_0p1deg']-wf2['settle_time_s_within_0p1deg'])<.05 and max(abs(a_-b_) for a_,b_ in zip(wfj['t_latch_s'],wf2['t_latch_s']))<.05
assert np.allclose(abs(wq[0]),180) and np.all(abs(wq[-1])<.01)
N_HINGES=d['h_newton'].shape[1]+wq.shape[1]+rd['h_newton'].shape[1];assert N_HINGES==36==int(N_HINGES_LEFT) and d['h_newton'].shape[1]+rd['h_newton'].shape[1]==NN['hinge_locks']['raw']  # 21 wing + 5 width + 10 radiator
wsel=wf['t']<=120.0+1e-9
# ===== P4 VARIANT (env P4V = A|B|C); same data as r19, plot size unchanged =====
P4V='D'
assert d['t'][-1]==1770 and RAD_T0+rd['t'][-1]==1770
WIDTHC='#8a4fa3';SEQ='';band_txt=[];m4_extra=[]
PH_=[('Root swing',0,180,blue),('Accordion',180,780,orange),('Width spread',960,1080,WIDTHC),('Radiator',1080,1770,teal)]
_fmt=lambda v:f"{int(v):,}"
if P4V in ('B','D'):
 for (nm_,t0_,t1_,c_) in PH_:a.axvspan(t0_,t1_,color=c_,alpha=.13,lw=0,zorder=0)._poster_band=True
labs={'D':('_r','_a','_w','_d'),'A':('Root swing','Accordion','Width spread','Radiator'),'B':('_r','_a','_w','_d'),'C':tuple(f"{nm_} {_fmt(t0_)}–{_fmt(t1_)} s" for nm_,t0_,t1_,_ in PH_)}[P4V]
for j in range(1,h.shape[1]):a.plot(d['t'],abs(h[:,j]),lw=2.0,color=orange,label=labs[1] if j==1 else '_nolegend_')
for j in range(wq.shape[1]):a.plot(wf['t'][wsel]+WD_T0,abs(wq[wsel,j]),lw=2.0,color=WIDTHC,label=labs[2] if j==0 else '_nolegend_')
for j in range(rh.shape[1]):a.plot(rd['t']+RAD_T0,abs(rh[:,j]),lw=2.0,color=teal,label=labs[3] if j==0 else '_nolegend_')
a.plot(d['t'],h[:,0],label=labs[0],lw=4.2,color=blue)
WARP_LAB={'D':'_x','A':'_w','B':'Root hinge, rechecked in Warp','C':'Warp recheck'}[P4V]
a.plot(d['t'],w[:,0],ls=(0,(4,2.5)),lw=2.0,color=ink,label=WARP_LAB)
m4_lines=dict(fold_out=h.shape[1]-1,width=wq.shape[1],radiator=rh.shape[1],root=1,root_lw=4.2,warp_lw=2.0,group_lw=2.0,n_lines=len(a.lines))
a.set_xlim(0,1800);a.set(xlabel='Seconds after deploy start',ylabel='Hinge angle (deg)');a.set_yticks([0,90,180])
def _phase_ticks():
 tk=[0,180,780,960,1080,1770];a.set_xticks(tk,[_fmt(v) for v in tk])
 tl=a.get_xticklabels();tl[3].set_ha('right');tl[4].set_ha('left')  # 960 / 1,080 are 0.8 in apart: push the labels apart
if P4V=='D':
 a.set_ylim(-8,232);a.set_xticks([0,600,1200,1800])
 for (num_,xc_,c_) in [('①',90,blue),('②',480,orange),('③',1020,WIDTHC),('④',1425,teal)]:
  t_=a.text(xc_,190,num_,color=c_,fontsize=28,fontweight='bold',ha='center',va='bottom',zorder=8);alltexts.append(num_);m4_extra.append(t_)
elif P4V=='A':
 a.set_ylim(-8,240);_phase_ticks()
 for (nm_,xy_,ha_,c_) in [('Root swing',(190,30),'left',blue),('Accordion',(445,128),'left',orange),('Width spread',(955,203),'center',WIDTHC),('Radiator',(1395,128),'left',teal)]:
  t_=a.text(*xy_,nm_,color=c_,fontsize=24,fontweight='bold',ha=ha_,va='center',zorder=8,bbox=dict(boxstyle='square,pad=0.05',fc='white',ec='none',alpha=.8));alltexts.append(nm_);m4_extra.append(t_)
 t_=a.text(1795,203,'dashed = Warp recheck',color=ink,fontsize=24,ha='right',va='center',zorder=8);alltexts.append('dashed = Warp recheck');m4_extra.append(t_)
elif P4V=='B':
 a.set_ylim(-8,285);_phase_ticks()
 for (num_,nm_,xc_,ha_,c_) in [('①','Root',6,'left',blue),('②','Accordion',480,'center',orange),('③','Width',1076,'right',WIDTHC),('④','Radiator',1425,'center',teal)]:
  t_=a.text(xc_,188,f"{num_} {nm_}",color=c_,fontsize=24,fontweight='bold',ha=ha_,va='bottom',zorder=8);alltexts.append(f"{num_} {nm_}");m4_extra.append(t_)
 _hd,_lb=a.get_legend_handles_labels();_k=_lb.index(WARP_LAB)
 a.legend([_hd[_k]],[_lb[_k]],fontsize=24,loc='upper right',frameon=False,borderaxespad=.05,handlelength=1.4,handletextpad=.4);alltexts.append(WARP_LAB)
else:
 a.set_ylim(-8,200);a.set_xticks([0,600,1200,1800])
 _hd,_lb=a.get_legend_handles_labels();_o=[_lb.index(k) for k in list(labs)+[WARP_LAB]];_hd=[_hd[i] for i in _o];_lb=[_lb[i] for i in _o]
 alltexts+=list(_lb)
alltexts+=['Seconds after deploy start']
KEY=[('①',blue,f"{_fmt(0)}–{_fmt(180)} s: solar-array root hinge swings each wing out from the body."),
 ('②',orange,f"{_fmt(180)}–{_fmt(780)} s: solar-array fold-out hinges open the folded panels accordion-style."),
 ('③',WIDTHC,f"{_fmt(960)}–{_fmt(1080)} s: solar-array width hinges spread the wing to full width."),
 ('④',teal,f"{_fmt(1080)}–{_fmt(1770)} s: radiator hinges unfold the radiator.")]
assert d['t'][-1]==1770 and wfj['tw_s']==120.0 and WD_T0+120==1080 and float(d['t'][np.argmax(np.abs(np.degrees(d['h_newton'][:,0]))<1.0)])<=180  # phase times from the traces / record
KEY_LEAD=float(os.environ.get('R20_KEY_LEAD','1.04'));ky=CAP4;key_arts=[];p4_arts=[]
for num_,c_,k_ in KEY:
 nt_=txt(x0+.20,ky,num_,size=24,weight='bold',color=c_);nw_=nt_.get_window_extent(renderer).width/fig.dpi+.12
 kb_=fit_body(x0+.20+nw_,ky,k_,CW-nw_,24,leading=KEY_LEAD);key_arts.append(kb_);p4_arts+=[nt_,kb_];alltexts.append(num_+' '+k_);ky=bottom(kb_)-.06
assert w.shape==h.shape and h.shape[1]==21 and format(np.abs(h-w).max(),'.4f')==n('angle_parity_deg')  # Warp re-solves all 21 solar-array hinges; max difference over all of them
P4_SENT=f"Newton simulates the unfold; Warp re-solves all {h.shape[1]} solar-array hinges (root hinge dashed); they agree within {n('angle_parity_deg')}°. All {N_HINGES} representative hinges lock; no panel-to-panel collisions in a separate clearance check. Rigid panels, assumed hinge parameters."
p4cap=fit_body(x0+.20,ky-.08,P4_SENT,CW,24,leading=KEY_LEAD,color=muted);p4_arts.append(p4cap)
_dy4=(PY3+PB)-bottom(p4cap);shift(p4_arts,_dy4);CAP4+=_dy4
_h4=(T-2.00+G4)-(CAP4+1.05);assert _h4>=PLOT_MIN['m4']-1e-9,('panel 4 plot below r19 size',_h4)
a.set_position([(x0+1.40)/43,(CAP4+1.05)/24,(PW-1.40-.55)/43,_h4/24])
P4_BOTTOM_SLACK=bottom(p4cap)-PY3
seq_key=p4cap
if P4V=='C':
 # no room above the plot (headline) and the curves fill 0-180 deg, so the legend sits under the caption, framed, 3 columns
 fig.canvas.draw();_cap_bot=bottom(p4cap)-.10
 lg=fig.legend(_hd,_lb,fontsize=24,loc='upper left',bbox_to_anchor=((x0+.15)/43,_cap_bot/24),bbox_transform=fig.transFigure,ncol=3,frameon=True,edgecolor='#c1d6d1',borderaxespad=0,columnspacing=1.0,handlelength=1.6,handletextpad=.4,borderpad=.3)
 fig.canvas.draw();_lb_bb=lg.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
 assert _lb_bb.y0>=PY3+.05 and _lb_bb.x1<=x0+PW-.05,('C legend does not fit',_lb_bb)
 m4_extra.append(lg)
# Footnote (below panels 3-4, right of the image column): source + the poster's single SpaceX disclaimer. r19: r17 working-time strip and job-time footnote removed.
zone='effort'
EFFN={'days':EFF_DAYS}
FOOT='Targets: spacex.com/spacexai/starmind. '+DISCLAIMER
foot_lines=fit_body(PX1+.20,PY3-.15,FOOT,42-PX1-.30,24,color=muted,leading=1.0)
foot_closing=fit_body(PX1+.20,bottom(foot_lines)-.08,CLOSING,42-PX1-.30,24,color=muted,leading=1.0);alltexts.append(CLOSING)
FOOT_BOTTOM=bottom(foot_closing);assert FOOT_BOTTOM>=1.0-1e-6,('footer runs into the bottom margin',FOOT_BOTTOM)
# Wording rules
text='\n'.join(alltexts)
assert not re.search(r'(?-i:\bOPEN\b)|\bHonest\b|Dassault|Synopsys|native verification|leaner teams|June|J8|rerout|short.edge|79 GPUs|lightweighted|passed release gates|gates A|aluminum compat|Dow|Grace(?! Blackwell)|366 K|362 K|41\.66|42\.08|pass rate|AI compute satellite|AI data centers? in orbit|meet the 393|scenario pass|Stress scenarios|≈ *32\.9|per hour|five inputs|two steps|stays about 33|computer-job time|recorded span|≥ *66|66 h|Lightest chosen|Coolant inlet peaks|392 K|transient|30-min|30 min|time constant|end of (the )?peak|within minutes|389–391|by the end',text,re.I),'forbidden wording'
assert re.findall(r'glycol[\w-]*',text,re.I)==['glycol-water'] or set(re.findall(r'glycol[\w-]*',text,re.I))=={'glycol-water'}
assert '30 satellites' in text and AUTHOR_LINE in text
fig.canvas.draw();renderer=fig.canvas.get_renderer()
def inchbox(a):return a.get_tightbbox(renderer).transformed(fig.dpi_scale_trans.inverted()) if isinstance(a,matplotlib.axes.Axes) and a.axison else a.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
bad=[]
for a in list(fig.texts)+list(fig.axes)+list(fig.artists):
 if not a.get_visible():continue
 bb=inchbox(a)
 if bb.x0<1-1e-5 or bb.y0<1-1e-5 or bb.x1>42+1e-5 or bb.y1>23+1e-5:bad.append({'kind':type(a).__name__,'bounds_inches':list(bb.extents)})
regions={**panels,'left':[1,1,PX1-.25-1,19.4],'header':[1,20.4,41,2.6],'effort':[PX1,1,42-PX1,PY3-1]}
for name,artists in zone_artists.items():
 x,y,w,h=regions[name]
 for a in artists:
  bb=inchbox(a)
  if bb.x0<x-1e-5 or bb.y0<y-1e-5 or bb.x1>x+w+1e-5 or bb.y1>y+h+1e-5:bad.append({'region':name,'kind':type(a).__name__,'bounds_inches':list(bb.extents),'text':a.get_text() if hasattr(a,'get_text') else 'plot'})
 for i,a in enumerate(artists):
  for b in artists[i+1:]:
   if not inchbox(a).overlaps(inchbox(b)): continue
   if name=='m1' and hasattr(a,'get_text') and hasattr(b,'get_text'):
    ba,bb=inchbox(a),inchbox(b)
    if abs((ba.y0+ba.y1)/2-(bb.y0+bb.y1)/2)<0.08 and (ba.y0+ba.y1)/2>18.5: continue
   bad.append({'region':name,'overlap':[(a.get_text() if hasattr(a,'get_text') else 'plot'),(b.get_text() if hasattr(b,'get_text') else 'plot')],'bbs':[list(inchbox(a).extents),list(inchbox(b).extents)]})
# --- r12: strengthened text layout audit over the WHOLE poster (every panel, left column, header, effort strip) ---
# text↔text overlap (> 0.015 in²), value/annotation text↔bar (> 0.02 in²), legend over plotted data, text clipped by its own axes.
poster_issues=[]
REG={**panels,'left':[1,1,PX1-.25-1,19.4],'header':[1,20.4,41,2.6],'effort':[PX1,1,42-PX1,PY3-1]}
def _bb(artist):return inchbox(artist)
def _inter_area(ba,bb):
 x0=max(ba.x0,bb.x0);x1=min(ba.x1,bb.x1);y0=max(ba.y0,bb.y0);y1=min(ba.y1,bb.y1)
 return max(0.0,x1-x0)*max(0.0,y1-y0)
def _region_of(bb):
 cx,cy=(bb.x0+bb.x1)/2,(bb.y0+bb.y1)/2
 for k,(x,y,w,h) in REG.items():
  if x<=cx<=x+w and y<=cy<=y+h:return k
 return 'none'
all_txts=[]  # (region, tag, text, bbox)
for artist in list(fig.texts):
 te=artist.get_text()
 if te.strip():bb=_bb(artist);all_txts.append((_region_of(bb),'fig',te[:60],bb))
for ax in fig.axes:
 if not ax.axison:continue
 def _drawn(axis,lo_hi):
  lo,hi=sorted(lo_hi);return [t.label1 for t in axis.get_major_ticks() if lo-1e-9<=t.get_loc()<=hi+1e-9]  # only ticks inside the view limits are drawn
 for tck in _drawn(ax.xaxis,ax.get_xlim())+_drawn(ax.yaxis,ax.get_ylim()):
  if tck.get_visible() and (tck.get_text() or '').strip():
   bb=_bb(tck)
   if bb.width>0 and bb.height>0:all_txts.append((_region_of(bb),'tick',tck.get_text()[:60],bb))
 for lab in (ax.xaxis.label,ax.yaxis.label):
  if lab.get_visible() and lab.get_text().strip():bb=_bb(lab);all_txts.append((_region_of(bb),'axlabel',lab.get_text()[:60],bb))
 for tax in ax.texts:
  if tax.get_visible() and (tax.get_text() or '').strip():
   bb=_bb(tax);all_txts.append((_region_of(bb),'ann',tax.get_text()[:60],bb))
   ab=ax.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
   if bb.x1>ab.x1+.02 or bb.x0<ab.x0-.02 or bb.y1>ab.y1+.02 or bb.y0<ab.y0-.02:poster_issues.append({'annotation_outside_axes':tax.get_text()[:60],'text_bounds':list(bb.extents),'axes_bounds':list(ab.extents)})
 if ax.get_legend() is not None:
  for lt in ax.get_legend().get_texts():bb=_bb(lt);all_txts.append((_region_of(bb),'leg',lt.get_text()[:60],bb))
for i,(ra,ka,ta,ba) in enumerate(all_txts):
 for rb,kb,tb,bb in all_txts[i+1:]:
  area=_inter_area(ba,bb)
  if area<=0.015:continue
  same_base=abs((ba.y0+ba.y1)/2-(bb.y0+bb.y1)/2)<0.08
  # r13: m1 header skip removed (it hid a real overlap)
  poster_issues.append({'overlap_text':[ta,tb],'regions':[ra,rb],'area_in2':round(area,4),'tags':[ka,kb],'bounds':[list(ba.extents),list(bb.extents)]})
# Text vs bar patches (every axes with bars).
patches=[]
for ax in fig.axes:
 owned={id(item[0]):item[1] for item in getattr(ax,'_poster_bar_artists',[])}
 for patch in ax.patches:
  if getattr(patch,'_poster_band',False):continue  # r19: Panel 4 sequence bands are background shading that carries the band labels
  pb=patch.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
  if pb.width*pb.height<0.01:continue
  patches.append((owned.get(id(patch),'bar'),pb))
for ra,ka,ta,ba in all_txts:
 if ka in ('tick','axlabel'):continue
 if ra=='m1' and (ba.y0+ba.y1)/2>18.5 and ka=='fig':continue
 for key,pb in patches:
  area=_inter_area(ba,pb)
  if area>0.02:poster_issues.append({'text_overlaps_bar':ta,'region':ra,'bar_key':key,'area_in2':round(area,4),'text_bounds':list(ba.extents),'bar_bounds':list(pb.extents)})
# Legends must not cover plotted data (scatter points, lines, picked marker).
for ax in fig.axes:
 lg=ax.get_legend()
 if lg is None:continue
 lb=_bb(lg);inside=0;total=0
 for ln in ax.get_lines():
  xy=ln.get_xydata()
  if len(xy)>2000:xy=xy[::max(1,len(xy)//2000)]
  for px,py in ax.transData.transform(xy):
   ix,iy=fig.dpi_scale_trans.inverted().transform((px,py));total+=1;inside+=lb.x0<=ix<=lb.x1 and lb.y0<=iy<=lb.y1
 for col in ax.collections:
  off=col.get_offsets()
  if len(off)>2000:off=off[::max(1,len(off)//2000)]
  for px,py in ax.transData.transform(off):
   ix,iy=fig.dpi_scale_trans.inverted().transform((px,py));total+=1;inside+=lb.x0<=ix<=lb.x1 and lb.y0<=iy<=lb.y1
 if inside:poster_issues.append({'legend_covers_data':_region_of(lb),'points_inside':int(inside),'points_sampled':int(total),'legend_bounds':list(lb.extents)})
m1_issues=[i for i in poster_issues if any(r=='m1' for r in i.get('regions',[i.get('region',i.get('legend_covers_data'))]))]
layout_m1_ok=not m1_issues;layout_poster_ok=not poster_issues
if poster_issues: bad.extend([{'poster_text_layout':i} for i in poster_issues])

if any(inchbox(t).overlaps(inchbox(qa)) for t in fig.texts):bad.append('QR/text overlap')
if not inchbox(qrlabel).y1<inchbox(qa).y0:bad.append('QR caption must be underneath code')
if not inchbox(ytlabel).y1<inchbox(ya).y0:bad.append('YouTube caption must be underneath its QR slot')
if any(inchbox(t_).overlaps(inchbox(ya)) for t_ in fig.texts):bad.append('YouTube QR/text overlap')
if inchbox(ya).overlaps(inchbox(qa)):bad.append('QR slots overlap')
for t,b in zip(workflow,workflow_boxes):
 tb,bb=inchbox(t),inchbox(b)
 if not (bb.contains(tb.x0,tb.y0) and bb.contains(tb.x1,tb.y1)):bad.append('Workflow text exceeds box: '+t.get_text())
assert all(t.get_fontsize()>=24 for t in fig.texts)
assert all(t.get_fontsize()>=24 for ax in fig.axes if ax.axison for t in ax.get_xticklabels()+ax.get_yticklabels()+ax.texts if t.get_visible())
area=sum(v[2]*v[3] for v in panels.values());assert area/902>=.55
hero_px=hero_img.shape;hero_dpi=hero_px[1]/hero_w;rel_dpi=rel_img.shape[1]/rel_w
def _rel(p):
 p=Path(p).resolve()
 try:return str(p.relative_to(R.resolve()))
 except ValueError:return p.name
layout=dict(layout_revision='r20',poster_layout=LAYOUT,m1_scatter_single_colour=m1_sc.get_array() is None,m1_scatter_coloured_by='radiator_panels',hero_path=_rel(hero_png),hero_sha256=sha(hero_png),hero_credit=HERO_CREDIT,release_path=_rel(release_png),release_sha256=sha(release_png),release_credit=RELEASE_CREDIT,release_size_inches=[rel_w,img_h],release_source_pixels=list(rel_img.shape[:2]),release_effective_ppi=rel_dpi,hero_crop_px=list(HC),hero_label_pt=LBL_PT,hero_labels=[t.get_text() for t in hero_labels],hero_label_fontsizes=[t.get_fontsize() for t in hero_labels],caption_fontsizes=[rel_credit.get_fontsize(),credit.get_fontsize()],panel_geometry=panels,matplotlib_layout_passed=not bad,m1_sensitivity_layout_passed=layout_m1_ok,poster_text_layout_passed=layout_poster_ok,numbers_sha256=sha(NUMF),minimum_text_pt=24,required_white_margin_inches=1,bounds_inches=[1,1,42,23],nvidia_module_area_inches2=area,live_area_inches2=902,nvidia_area_percent=area/902*100,modules=panels,qr_size_inches=QS,qr_bounds_inches=list(inchbox(qa).extents),qr_caption='GitHub',youtube_qr=dict(url_given=bool(yt_url),bounds_inches=list(inchbox(ya).extents),caption='YouTube',caption_bounds_inches=list(inchbox(ytlabel).extents)),effort=dict(EFFN,source_sha256=sha(R/'evidence/effort/EFFORT_UPDATE_R17.json')),thermal_steady=TH,mc_numbers=MCN,n_hinges=N_HINGES,why_it_matters=WHY,image_sizes_in=dict(release=[rel_w,img_h],hero=[hero_w,hero_h]),axes_in=[[round(v,6) for v in (ax.get_position().x0*43,ax.get_position().y0*24,ax.get_position().width*43,ax.get_position().height*24)] for ax in fig.axes if ax is not _kax],axes_on=[bool(ax.axison) for ax in fig.axes if ax is not _kax],m1_key_marker_axes_in=[round(v,6) for v in (_kax.get_position().x0*43,_kax.get_position().y0*24,_kax.get_position().width*43,_kax.get_position().height*24)],left_slack_in=LEFT_SLACK_IN,hero_omniverse=HERO_OMNI,subtitle=SUBTITLE,closing_text=CLOSING,footer_bottom_in=FOOT_BOTTOM,qr_side_in=QS,m1_marker=M1_MARKER,m1_key_clear_in=M1_KEY_CLEAR,hard_limits_text=HARD_TXT,search_text=SEARCH_TXT,orbit_text=ORBIT_TXT,frame_shown=FRAME_SHOWN,image_scale=IMG_SCALE,image_full_height_in=IMG_H_FULL,image_x0_in=IMG_X0,hero_x0_in=HERO_X0,caption_columns_in=[REL_COL,HERO_COL],left_leading=LEFT_LEAD,left_item_gap_in=LEFT_GAP,sequence_key=SEQ,band_labels=[t_.get_text() for t_ in band_txt],title_widths_in=TITLE_W,titles=TITLES,p4_bottom_slack_in=P4_BOTTOM_SLACK,plot_sizes_in={k_:[ax_.get_position().width*43,ax_.get_position().height*24] for k_,ax_ in (('m1_scatter',m1_scatter_ax),('m4_deploy',m4_ax))},qr_caption_bounds_inches=list(inchbox(qrlabel).extents),hero_size_inches=[hero_w,hero_h],hero_bounds_inches=list(inchbox(hero).extents),hero_source_pixels=list(hero_px[:2]),hero_effective_dpi=hero_dpi,r10_hero_size_inches=[4.088888888888889,2.3],workflow_total_width_inches=workflow_width,numbers_used=sorted(set(used)),generator_sha256=sha(__file__),speed_numbers_sha256=sha(SPF),allcore_sha256=sha(ACF),m2_bar_orders=m2_bar_orders,m4_lines=m4_lines,youtube_url=yt_url,disclaimer=DISCLAIMER,footnote=FOOT,footnote_lines=len(foot_lines.get_text().split('\n')),m1_scatter_width_in=SCW,m1_scatter_height_in=sc_top-sc_bot,m1_colour_levels=[int(v) for v in levels],m1_colourbar_ticks=m1_cb_ticks,m1_gray_points=int((~feas).sum()),m1_feasible_points=int(feas.sum()),violations=bad)
layout['band_labels']=[t_.get_text() for t_ in m4_extra];layout['p4_key']=[num_+' '+k_ for num_,_,k_ in KEY];layout['p4_axes_legend']=m4_ax.get_legend() is not None
layout['why_box']=WHY_BOX;layout['load_word']=LOAD_WORD;layout['why_text']=WHY
layout.update(workflow_box_widths_in_r19=[round(v,3) for v in widths_r19],workflow_box_widths_in=[round(v,3) for v in widths],workflow_labels=workflow_labels,title_pt=TITLE_PT,p2_strip_h_in=SH,p3_plot_h_in=_h3,p4_plot_h_in=_h4,p1_plot_h_in=sc_top-sc_bot,plot_min_in=PLOT_MIN)
(OUT/'LAYOUT_R20_MPL_AUDIT.json').write_text(json.dumps(layout,indent=2)+'\n')
if bad and os.environ.get('POSTER_DEBUG'):fig.savefig(str(R/'work/dbg_r20.png'),dpi=int(os.environ['POSTER_DEBUG']));print('\n'.join(json.dumps(b,ensure_ascii=False)[:300] for b in bad))
if bad:raise RuntimeError(json.dumps(bad,indent=2))
assert hero_dpi>=300,hero_dpi
if audit_only:print('r20 matplotlib layout PASS',area/902*100,hero_w,hero_h);sys.exit(0)
out=OUT/('GTC_POSTER_R20_PUBLIC.pdf' if public else 'GTC_POSTER_R20_DRAFT.pdf')
fig.savefig(out,dpi=300,metadata={'Title':TITLE,'Author':AUTHOR,'Subject':'August design, one Vera Rubin NVL72; r20; numbers SHA256 '+sha(NUMF),'CreationDate':None})
pass
plt.close(fig)
red=lambda t:t.replace(repo_url,'https://github.com/OWNER/REPOSITORY').replace(AUTHOR,'<author>').replace(ASSISTANT,'<assistant>')
redacted=red(text)
ticks=sorted({t.get_text() for ax in fig.axes if ax.axison for t in ax.get_xticklabels()+ax.get_yticklabels() if t.get_text()})
meta=dict(layout_revision='r20',file=out.name,pdf_sha256=sha(out),size_bytes=out.stat().st_size,page_inches=[43,24],numbers_sha256=sha(NUMF),generator_sha256=sha(__file__),speed_numbers_sha256=sha(SPF),allcore_sha256=sha(ACF),repository_link='https://github.com/OWNER/REPOSITORY',all_text=redacted,claim_texts=[red(t) for t in alltexts],axis_tick_labels=ticks,chart_inputs={os.path.relpath(p,R):sha(p) for p in [sweep_npz,mc_json,sv_npz,newton_npz,radiator_npz,wfold_npz,wfold_json,wfold_json_conv,THF,hero_png,release_png]})
(OUT/('POSTER_PDF_PUBLIC_TRACE.json' if public else 'POSTER_PDF_TRACE.json')).write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n');print(out,meta['size_bytes'],meta['pdf_sha256'])
