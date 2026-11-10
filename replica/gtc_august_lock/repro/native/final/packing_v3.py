"""Packing delta check: unchanged inherited greedy heightmap + layer DP.
Uses old footprint candidates as a constructive lower-bound, not a new optimum claim.
Finite mechanisms, launcher interfaces and CG remain NOT DESIGNED.
"""
import os
import json,math,functools,os,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter
ROOT=Path(os.environ.get('GTCFC_ROOT',os.environ['GTCFC_ROOT']+''))
RES=.01;items=[];_PC={};GAP=.05
PROFILE=[(0.,4.),(8.,4.),(9.,3.85),(10.,3.68),(11.,3.49),(12.,3.27),(13.,3.04),(14.,2.78),(15.,2.51),(16.,2.2),(17.24,1.8)]
def radius(z): return float(np.interp(z,*np.asarray(PROFILE).T))-.05
class V:
 @staticmethod
 def profile(mode):
  assert mode=='std'
  return radius,17.24
def cells(x): return int(math.ceil(round(x / RES, 6)))
def orients(dims, flat):
    a, b, c = dims
    if flat:   # thin axis (smallest dimension) stays vertical
        thin = min(dims); rest = [x for x in dims]; rest.remove(thin)
        return {(rest[0], rest[1], thin), (rest[1], rest[0], thin)}
    return {(x, y, z) for x, y, z in ((a, b, c), (b, a, c), (a, c, b), (c, a, b), (b, c, a), (c, b, a))}

def pack(X, Y, flat):
    key = (X, Y, flat)
    if key in _PC: return _PC[key]
    r = _pack(X, Y, flat); _PC[key] = r; return r

def _pack(X, Y, flat):
    """Return (H_m, placed list) for footprint X x Y m, or None if an item cannot fit the footprint."""
    nx, ny = cells(X), cells(Y); h = np.zeros((nx, ny)); placed = []
    for name, kind, dims in sorted(items, key=lambda t: -t[2][0] * t[2][1] * t[2][2]):
        best = None
        for (a, b, c) in orients(dims, flat and kind != "bus"):
            ca, cb, cc = cells(a + 0.01), cells(b + 0.01), cells(c + 0.01)
            if ca > nx or cb > ny: continue
            m = maximum_filter(h, size=(ca, cb), mode="constant", cval=0.0)
            base = m[ca // 2: ca // 2 + nx - ca + 1, cb // 2: cb // 2 + ny - cb + 1]
            top = base + cc
            i, j = np.unravel_index(np.argmin(top + 1e-9 * (np.arange(top.shape[0])[:, None] + np.arange(top.shape[1])[None, :])), top.shape)
            cand = (float(top[i, j]), float(base[i, j]), i, j, ca, cb, cc, (a, b, c))
            if best is None or cand[:2] < best[:2]: best = cand
        if best is None: return None
        t, bz, i, j, ca, cb, cc, o = best
        h[i:i + ca, j:j + cb] = t; placed.append(dict(name=name, kind=kind, orient_m=o, lo_m=(i * RES, j * RES, bz * RES)))
    return float(h.max()) * RES, placed

@functools.lru_cache(None)
def layer_cr2(m, X, Y, gap, maxrows, maxper):
    best = None
    def parts(rem, mx, k):
        if rem == 0: yield (); return
        if k == 0: return
        for a in range(min(rem, mx), 0, -1):
            for rest in parts(rem - a, a, k - 1): yield (a,) + rest
    for part in parts(m, maxper, maxrows):
        k = len(part)
        for (a, b) in ((X, Y), (Y, X)):
            Hh = k * b + (k - 1) * gap; cr = 0.0
            for j, nr in enumerate(part):
                wd = nr * a + (nr - 1) * gap; y0 = -Hh / 2 + j * (b + gap); y1 = y0 + b
                cr = max(cr, math.hypot(wd / 2, max(abs(y0), abs(y1))))
            if best is None or cr < best: best = cr
    return best
def dp2(rows, mmax=6, maxrows=3, maxper=3, gap=GAP, adapt=0.30, pmode="std"):
    rfun, ztop = V.profile(pmode); cands = []
    for X, Y, H in rows:
        for m in range(1, mmax + 1):
            cr = layer_cr2(m, X, Y, gap, maxrows, maxper)
            if cr is not None: cands.append((m, X, Y, H, cr))
    cands.sort(key=lambda c: c[3])
    @functools.lru_cache(None)
    def f(zc):
        z = zc / 100; best = (0, None)
        for m, X, Y, H, cr in cands:
            top = z + H
            if top > ztop + 1e-9: break
            if cr <= rfun(top) + 1e-9:
                v = m + f(int(round((top + gap + adapt) * 100)))[0]
                if v > best[0]: best = (v, (m, X, Y, H, z, cr))
        return best
    zc = int(round(adapt * 100)); seq = []; n = f(zc)[0]
    while True:
        v, c = f(zc)
        if c is None: break
        seq.append(dict(m=c[0], X=c[1], Y=c[2], H=round(c[3], 3), z0=round(c[4], 2), corner_r=round(c[5], 3))); zc = int(round((c[4] + c[3] + gap + adapt) * 100))
    return n, seq
x=json.load(open(ROOT/'final/GTC_FINAL_CANDIDATE.json'));out=dict(scope=__doc__,cases={},passed=True)
for i,(nm,tag,b) in enumerate([('June','J8','Jun'),('August','A4','Aug')]):
 if len(sys.argv)>1 and nm!=sys.argv[1]:continue
 f=x['fleets'][i];pt=json.load(open(ROOT/f'inputs/ai1_replica/gtc_params/point_{tag}_C1.json'))
 old=json.load(open(ROOT/f'inputs/ai1_replica/checks_t454/c15_pack_{b}_{77 if i==0 else 128}.json'))
 S=old['S'];fold=S['fold'];pitch=S['leaf'];npan=77 if i==0 else 128;ns=old['n_stacks']
 area=f['solar_area_m2']['value'];area0=pt['areas']['A_arr_m2'];w=area/(2*14*20)
 arr=[(f'array_{j}','array',(14/fold,w,20*pitch*fold)) for j in range(2)]
 base=npan//ns;extra=npan-base*ns
 rad=[(f'rad_{j}','radiator',(.3634175776637853,2.9445579551660426,((base+(1 if j<extra else 0))-1)*.010+.003)) for j in range(ns)]
 # Same bus/rack as inherited item model; array-only geometry change.
 BUSZ0=2.496; VEQ0=(4.626-BUSZ0)*.7*2.;power=pt['result']['P_IT_peak_kW'];veq=VEQ0*(.338+.662*power/188)*400/S['rho']
 rackkg=pt['mass_lines_kg']['rack'];rh=rackkg/S['rho_rack']/(.6*1.2)
 items=arr+rad+[('rack','bus',(.6,1.2,rh)),('equip','bus',(.7,2.,veq/(.7*2)+.2))]
 footprints=sorted({(z['X'],z['Y']) for z in old['res']['layers']['seq']})
 rows=[]
 for X,Y in footprints:
  result=_pack(X,Y,False)
  if result: rows.append((X,Y,result[0]))
 n,seq=dp2(rows,adapt=S['adapt'],gap=S['gap'])
 if n<f['spacecraft_count']['value']:
  print(nm,'constructive shortfall; full inherited 0.1-m footprint grid',flush=True)
  candidates=set();step=S['step'];rmax=radius(8.)
  xs=[1.5+step*k for k in range(int(round((7.75-1.5)/step))+1)]+[7.05,7.35,6.05,6.55,5.05,5.55]
  for X in xs:
   ys=[.75+step*k for k in range(int(round((X-.75)/step))+1)]+[X/2]
   for Y in ys:
    if Y<=X+1e-9 and math.hypot(X,Y)/2<=rmax+1e-9:candidates.add((round(X,3),round(Y,3)))
  rows=[]
  for X,Y in sorted(candidates):
   result=_pack(X,Y,False)
   if result:rows.append((X,Y,result[0]))
  n,seq=dp2(rows,adapt=S['adapt'],gap=S['gap'])
 required=f['spacecraft_count']['value'];ok=n>=required
 out['cases'][nm]=dict(required_count=required,constructive_count=n,passed=ok,method='inherited 0.1-m footprint grid, greedy heightmap, same layer DP',array_block_old_m=[14/fold,area0/(2*14*20),20*pitch*fold],array_block_new_m=list(arr[0][2]),item_volume_m3=sum(math.prod(it[2]) for it in items),old_item_volume_m3=old['item_vol_m3'],rows=rows,sequence=seq,items=items,launcher_clearance_m=.05,scope='idealized geometry only; finite dispenser/hinges/CG/load paths remain open')
 out['passed'] &= ok
 print(nm,n,'required',required,flush=True)
json.dump(out,open(ROOT/('final/PACKING_V3_'+sys.argv[1]+'.json' if len(sys.argv)>1 else 'final/PACKING_V3.json'),'w'),indent=2)
