"""Physical-PDF layout audit + repaired legacy gate predicates for the r11 candidate (no predicate weakened; stale literal
headings replaced by semantic checks of the same requirement). Usage: R11_ROOT=<repro> python poster/audit_r11.py <box_results_dir>"""
import os,sys,json,re,hashlib,subprocess,statistics
from pathlib import Path
import numpy as np
import pymupdf
R=Path(os.environ['R11_ROOT']).resolve();BOX=Path(sys.argv[1]).resolve();O=R/'out/poster';G=R/'gb10_out/r11'
J=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
NUMF=R/'out/POSTER_NUMBERS_R11.json';NUM=J(NUMF);NN=NUM['numbers'];TR=J(O/'POSTER_PDF_TRACE.json');TRP=J(O/'POSTER_PDF_PUBLIC_TRACE.json')
res=[]
def check(gate,name,ok,detail=''):res.append(dict(gate=gate,predicate=name,passed=bool(ok),detail=detail))
# ---------------- physical PDF audit (M4) ----------------
layout={}
for fn in ['GTC_POSTER_R11_CANDIDATE_DRAFT.pdf','GTC_POSTER_R11_CANDIDATE_PUBLIC.pdf']:
 doc=pymupdf.open(O/fn);pg=doc[0];W,H=pg.rect.width/72,pg.rect.height/72;spans=[];imgs=[];draws=[]
 for b in pg.get_text('dict')['blocks']:
  if b['type']==0:
   for l in b['lines']:
    for s in l['spans']:
     if s['text'].strip():spans.append(dict(text=s['text'],size=s['size'],font=s['font'],bbox=[v/72 for v in s['bbox']]))
 for info in pg.get_image_info(xrefs=True):
  x0,y0,x1,y1=[v/72 for v in info['bbox']];imgs.append(dict(px=[info['width'],info['height']],bbox=[x0,y0,x1,y1],dpi=[info['width']/(x1-x0),info['height']/(y1-y0)]))
 for d in pg.get_drawings():
  r=d['rect'];bb=[r.x0/72,r.y0/72,r.x1/72,r.y1/72]
  if bb[2]-bb[0]>=W-1e-3 and bb[3]-bb[1]>=H-1e-3:continue  # page background
  draws.append(bb)
 # poppler word boxes (independent extractor; this is the extractor that exposed the r10 0.8684 in title)
 xml=subprocess.run(['pdftotext','-bbox',str(O/fn),'-'],capture_output=True,text=True,check=True).stdout
 words=[(float(a)/72,float(b)/72,float(c)/72,float(d)/72,w) for a,b,c,d,w in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',xml)]
 def outside(bb):return bb[0]<1-1e-4 or bb[1]<1-1e-4 or bb[2]>W-1+1e-4 or bb[3]>H-1+1e-4
 viol=[('span',s['text'][:40],s['bbox']) for s in spans if outside(s['bbox'])]+[('word',w[4],list(w[:4])) for w in words if outside(w[:4])]+[('image',i['px'],i['bbox']) for i in imgs if outside(i['bbox'])]+[('drawing','',d) for d in draws if outside(d)]
 ext=dict(text_top_in=min(min(s['bbox'][1] for s in spans),min(w[1] for w in words)),text_bottom_from_top_in=max(max(s['bbox'][3] for s in spans),max(w[3] for w in words)),left_in=min(min(s['bbox'][0] for s in spans),min(w[0] for w in words)),right_in=max(max(s['bbox'][2] for s in spans),max(w[2] for w in words)))
 layout[fn]=dict(page_inches=[W,H],text_spans=len(spans),poppler_words=len(words),min_font_pt=min(s['size'] for s in spans),images=imgs,drawings=len(draws),extents=ext,violations=viol,pdf_sha256=sha(O/fn))
 g=fn.split('_')[-1][:-4]
 check('M4',f'{g}: page is 43x24 in',abs(W-43)<1e-6 and abs(H-24)<1e-6,[W,H])
 check('M4',f'{g}: every text span, poppler word, image and drawing inside 1-in margins (physical PDF)',not viol,viol[:5] or ext)
 check('M4',f'{g}: minimum font >= 24 pt',min(s['size'] for s in spans)>=24-1e-6,min(s['size'] for s in spans))
 check('M4',f'{g}: every raster image >= 300 dpi (0.1 dpi pixel-quantization rounding)',all(round(min(i['dpi']),1)>=300 for i in imgs),[[round(v,1) for v in i['dpi']] for i in imgs])
 # QR caption directly under QR
 qr=[i for i in imgs if i['px'][0]==i['px'][1]];cap=[s for s in spans if s['text'].strip()=='Full repo (GitHub)']
 ok=len(qr)==1 and len(cap)==1 and cap[0]['bbox'][1]>=qr[0]['bbox'][3]-1e-6 and cap[0]['bbox'][1]-qr[0]['bbox'][3]<.25 and abs((cap[0]['bbox'][0]+cap[0]['bbox'][2])/2-(qr[0]['bbox'][0]+qr[0]['bbox'][2])/2)<.1
 check('M4',f'{g}: QR caption "Full repo (GitHub)" directly under the QR code',ok,dict(qr=qr[0]['bbox'] if qr else None,caption=cap[0]['bbox'] if cap else None))
 AL=f"Author: {os.environ['POSTER_AUTHOR']} assisted by AI agent {os.environ['POSTER_ASSISTANT']}";auth=[s for s in spans if s['text'].strip()==AL]
 check('M6',f'{g}: approved author line is bold and on its own line',len(auth)==1 and 'Bold' in auth[0]['font'],auth[0]['font'] if auth else None)
 txt=pg.get_text();layout[fn]['text']=txt
 lowest=max(s['bbox'][3] for s in spans);foot=[s['text'] for s in spans if s['bbox'][3]>lowest-.45]
 check('M4',f'{g}: no footer (lowest text is the effort footnote, no reference/repo footer)',all(t.startswith('*CPU') or 'Marble' in t or t.startswith('Illustrative') or 'definition' in t or 'not GPU-hours' in t for t in foot),foot)
D=layout['GTC_POSTER_R11_CANDIDATE_DRAFT.pdf'];P=layout['GTC_POSTER_R11_CANDIDATE_PUBLIC.pdf'];T=D['text'];Tflat=re.sub(r'\s+',' ',T)
check('M4','DRAFT and PUBLIC text identical',D['text']==P['text'])
# ---------------- semantic content predicates (repaired M1-M3, M5-M8) ----------------
has=lambda s:s in Tflat
check('M1','sunlit nominal vs eclipse-included annual disclosed with traced values',has(f"{NN['nominal_kW']['shown']} kW nominal in sunlight") and has(f"{NN['annual_kW']['shown']} kW annual average, including eclipse") and NN['annual_kW']['raw']<NN['nominal_kW']['raw'])
for s in ['Simulation study, not flight qualification','not flight validation','junction temperatures not yet qualified','Assumed 640.38 kg payload allocation','not flight reliability','not hardware validation','Flexible hardware and force-step convergence remain open','not adopted hardware or a global optimum','not GPU-hours']:
 check('M2',f'scope/limit disclosed: "{s}"',has(s))
B=[J(G/f'BENCH_CPU_{i}.json') for i in (1,2,3)]
check('M3','PDF records 1 CPU core / 1 thread and every CPU benchmark ran pinned to one core with 1 thread',has('1 core / 1 thread') and has('1 Cortex-X925 core / 1 thread') and all(len(b['cpu_affinity'])==1 and all(v=='1' for v in b['thread_environment'].values()) for b in B),[b['cpu_affinity'] for b in B])
check('M5','problem states published targets, fp64 benchmark spec and primary source line',has("SpaceX's published targets of 250 kW peak per satellite and 75 kW per ton") and has('fp64') and has('Source: spacex.com/spacexai/starmind'))
check('M7','coating emissivity 0.92 BOL specification printed and traced',has(f"coating emissivity {NN['emissivity']['shown']}") and NN['emissivity']['raw']==.92)
NC=J(R/'native/r11_out/NATIVE_CHECKS.json')['solar'];calc=NC['remaining_planar_active_surface_m2']*NC['locked_remaining_surface_rating_W_m2']
check('M8','module rating labelled as assumed remaining-planar rating; arithmetic closes; no active-cell claim',has(f"assumed module rating {NN['module_rating_W_m2']['shown']} W/m² on its remaining planar area") and not re.search('active cells',Tflat) and abs(calc-NC['output_W_at_full_precision_locked_rating'])<1e-6,calc)
check('C','decision 4: one Vera Rubin NVL72, 72 GPUs + 36 CPUs; 30 satellites explicit',has('one Vera Rubin NVL72 (72 GPUs + 36 CPUs)') and has('30 satellites'))
check('C','decision 1: 250 kW peak at beginning of life; available peak >= 249.9 kW acceptance',has('250 kW peak at beginning of life') and NN['peak_available_BOL_kW']['raw']>=249.9)
check('C','decision 2: 370 K nominal target wording, estimates from traced sensitivity',has(f"≈370 K nominal target (est. {NN['GPU_est_K']['shown']}–{NN['HBM_est_K']['shown']} K), higher in edge cases"))
check('C','decision 3 + standing rules: no coolant-chemistry/vendor/process-history/gate claims',not re.search(r'aluminum compat|aluminium|wetted|inhibitor|\bDow|chemistry|2 passed|release gates|gates A|79 GPUs|lightweighted|native verification|leaner teams|Grace|Rubin junction temperatures 3|366 K|362 K|June|design history',Tflat,re.I))
check('C','effort strip keeps ≈11 days and ≥44.1 h',has('≈11 days recorded span') and has('≥44.1 h GB10 computer-job time*'))
check('C','no NVIDIA logo: only images are the QR code, the render and the charts are vector',len(D['images'])==2,[i['px'] for i in D['images']])
L=J(O/'LAYOUT_R11_MPL_AUDIT.json');check('C','NVIDIA content >= 55% of live area',L['nvidia_area_percent']>=55,L['nvidia_area_percent'])
# ---------------- every printed number traces (V4B) ----------------
tok=lambda s:set(re.findall(r'\d+(?:[.,]\d+)*',s))
derived=set();[derived.update(tok(v['shown'])) for v in NN.values()]
derived|=tok(f"{NN['configurations']['raw']:,}")
CONST={'75':'SpaceX published kW/ton','640.38':'accepted payload allocation (assumption)','600':'box mm (assumption)','1200':'box mm (assumption)','937':'box mm (assumption)','640':'payload allocation rounded','6':'axial g load case','2':'lateral g / workflow index','1.25':'factor of safety','35':'Falcon frequency reference','393':'coolant inlet cap (requirement)','72':'NVL72 topology GPUs','36':'NVL72 topology CPUs','1':'one core / one thread / panel 1','3':'median of 3 runs / panel 3 / workflow','4':'panel / workflow index','5':'workflow index','10':'GB10 product name','64':'fp64','925':'Cortex-X925 core name','256':'SHA256','2.0':'Apache-2.0 license','1.18.0':'Warp version on CUDA (Newton line)'}
claims=TR['claim_texts'];unexplained=[]
for c in claims:
 for t in tok(c):
  if t not in derived and t not in CONST:unexplained.append((t,c[:60]))
check('V4B','every numeric token in claim text is a traced derived number or a documented constant',not unexplained,unexplained[:10])
ticks=set();[ticks.update(tok(t)) for t in TR['axis_tick_labels']]
pdf_extra=sorted(tok(T)-set().union(*[tok(c) for c in claims])-ticks)
check('V4B','every numeric token in the actual PDF comes from a checked claim string or an axis tick',not pdf_extra,pdf_extra)
# ---------------- helper-source hashes (repaired: hashes recorded at run time must match committed sources) ----------------
sw=J(G/'SWEEP_GB10_GPU.json')
check('HASH','GB10 sweep kernel hash == committed sweep/gpu_core.py',sw['kernel_sha256']==sha(R/'sweep/gpu_core.py'))
check('HASH','GB10 sweep inputs hash == committed sweep/SWEEP_INPUTS.json',sw['inputs_sha256']==sha(R/'sweep/SWEEP_INPUTS.json'))
check('HASH','SWEEP_INPUTS generator hash recorded == committed make_sweep_inputs.py',J(R/'sweep/SWEEP_INPUTS.json')['script_sha256']==sha(R/'sweep/make_sweep_inputs.py'))
check('HASH','numbers derive-script hash == committed numbers/derive_numbers.py',NUM['derive_script_sha256']==sha(R/'numbers/derive_numbers.py'))
check('HASH','every numbers source file hash still matches',all(sha(R/k)==v for k,v in NUM['source_sha256'].items()),[k for k,v in NUM['source_sha256'].items() if sha(R/k)!=v])
check('HASH','poster trace generator/numbers/PDF hashes match committed files',TR['generator_sha256']==sha(R/'poster/make_poster_r11.py')==TRP['generator_sha256'] and TR['numbers_sha256']==sha(NUMF) and TR['pdf_sha256']==sha(O/TR['file']) and TRP['pdf_sha256']==sha(O/TRP['file']))
check('HASH','poster chart inputs hashes match',all(sha(R/k)==v for k,v in TR['chart_inputs'].items()))
# ---------------- box vs GB10 identity (repaired V3A: fresh independent host results at the same revision) ----------------
bs=J(BOX/'SWEEP_BOX_CPU.json');bm=J(BOX/'MC_BOX_CPU.json');gc=J(G/'SWEEP_GB10_CPU.json');gm=J(G/'MC_GB10_GPU.json')
same=lambda a:(a['hard_feasible_count'],a['design_margin_feasible_count'],a['selected']['index'])
check('V3A','box CPU, GB10 CPU and GB10 CUDA sweeps agree on counts and selected index',same(bs)==same(sw)==same(gc),[same(bs),same(sw),same(gc)])
check('V3A','box/GB10 sweeps used identical inputs and kernel',bs['inputs_sha256']==sw['inputs_sha256'] and bs['kernel_sha256']==sw['kernel_sha256'])
sel_diff=max(abs(bs['selected'][k]-sw['selected'][k])/max(1,abs(sw['selected'][k])) for k in sw['selected'] if isinstance(sw['selected'][k],float))
check('V3A','selected design values agree box vs GB10 CUDA (rel <= 1e-9)',sel_diff<=1e-9,sel_diff)
pa=np.load(BOX/'SWEEP_PARITY_BOX_CPU.npz');pb=np.load(G/'SWEEP_PARITY_GB10_GPU.npz');ok=np.array_equal(pa['index'],pb['index']);d=float(np.max(np.abs(pa['values']-pb['values'])/np.maximum(1,np.abs(pb['values'])))) if ok else None
check('V3A','sampled sweep parity box CPU vs GB10 CUDA (rel <= 1e-9)',ok and d<=1e-9,d)
check('V3A','scenario fraction identical box CPU vs GB10 CUDA',bm['P_inlet_le_393']==gm['P_inlet_le_393'],[bm['P_inlet_le_393'],gm['P_inlet_le_393']])
ma=np.load(BOX/'MC_PARITY_BOX_CPU.npz');mb=np.load(G/'MC_PARITY_GB10_GPU.npz');d2=float(np.max(np.abs(ma['values']-mb['values'])/np.maximum(1,np.abs(mb['values']))))
check('V3A','sampled MC parity box CPU vs GB10 CUDA (rel <= 1e-9)',d2<=1e-9,d2)
out=dict(revision='r11_candidate',adopted=False,passed=all(r['passed'] for r in res),n_predicates=len(res),n_failed=sum(not r['passed'] for r in res),predicates=res)
(O/'GATES_R11.json').write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str)+'\n')
for v in layout.values():v.pop('text')
(O/'LAYOUT_R11_AUDIT.json').write_text(json.dumps(dict(revision='r11_candidate',matplotlib_audit=L,pdf=layout),indent=2,ensure_ascii=False,default=str)+'\n')
print('GATES',out['passed'],out['n_predicates'],'failed',out['n_failed'])
for r in res:
 if not r['passed']:print('FAIL',r['gate'],r['predicate'],r['detail'])
