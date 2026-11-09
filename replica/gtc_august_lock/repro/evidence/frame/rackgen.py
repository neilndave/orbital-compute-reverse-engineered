"""Coarse CalculiX screening model of the lightweighted NVL72-based compute rack (SCREENING ONLY).
Beam-frame model, quadratic B32R elements (3-node quadratic beams, expanded by ccx to 20-node bricks).
All geometry/section choices are ASSUMED; see README.md. Equipment mass is smeared on the tray side rails.
"""
import math, json, os, re, subprocess, time, itertools
import numpy as np
CCX = os.environ.get('CCX', 'ccx')
G0 = 9.80665
# Al 7075-T6 (project post material, point_A4_C1.json item1 'posts': Al7075-T6). Handbook values, ASSUMED.
E, NU, RHO, FTY = 71.7e9, 0.33, 2810.0, 503e6
# Load corners exactly as the locked FEA (lock/fea/run_final_fea.py line 80): (axial g, lateral g)
CORNERS = dict(max_axial=(6.0, 0.5), max_lateral=(3.5, 2.0), tension_lat=(-1.5, 2.0), max_tension=(-2.0, 0.5))
FS_Y = 1.25          # lock/fea/run_final_fea.py: FS1p25_yield_margin
FIT = 1.5            # joint factor 1.5 (gtc_final_v2 REPLICA_PLAN.md adapter row), reported as an extra conservative margin
ANGLES = list(range(0, 360, 45))

def design(**kw):
    d = dict(W=0.6, D=1.2, H=2.296, n_tray=12, m_equip=640.38,
             post=(0.060, 0.060, 0.003),   # BOX a,b,t
             rail=(0.040, 0.030, 0.002),   # side rails (y-dir) carrying trays: BOX
             xrail=(0.030, 0.030, 0.0015), # front/back cross rails (x-dir): BOX
             brace=(0.010, 0.0015),        # diagonals: PIPE r_out, t
             top_brace=True, back_brace=True, side_brace=True, front_brace=False, top_tie=False)
    d.update(kw); return d

def box_area(a, b, t): return a*b - (a-2*t)*(b-2*t)
def pipe_area(r, t): return math.pi*(r*r-(r-t)**2)

def build(d, n):
    """n = quadratic elements per member segment. Returns deck pieces and bookkeeping."""
    W, D, H, nt = d['W'], d['D'], d['H'], d['n_tray']
    pa = d['post'][0]
    xs = [-(W/2 - pa/2), (W/2 - pa/2)]; ys = [pa/2, D - pa/2]
    zl = [0.0] + [H*(k)/(nt+1) for k in range(1, nt+1)] + [H - pa/2]   # base, trays, top
    nodes = {}; coords = []
    def node(p):
        key = tuple(round(c, 9) for c in p)
        if key not in nodes:
            coords.append(key); nodes[key] = len(coords)
        return nodes[key]
    elsets = {}; elems = []
    def member(p, q, eset):
        p = np.array(p); q = np.array(q)
        ids = [node(p + (q-p)*i/(2*n)) for i in range(2*n+1)]
        for e in range(n):
            elems.append((ids[2*e], ids[2*e+1], ids[2*e+2], eset))
            elsets.setdefault(eset, []).append(len(elems))
        return ids
    L = {}
    def add_len(k, p, q): L[k] = L.get(k, 0) + float(np.linalg.norm(np.array(q)-np.array(p)))
    # posts
    for x in xs:
        for y in ys:
            for k in range(len(zl)-1):
                p, q = (x, y, zl[k]), (x, y, zl[k+1]); member(p, q, 'POST'); add_len('POST', p, q)
    for k, z in enumerate(zl):
        tray = 1 <= k <= nt
        for x in xs:   # side rails along y
            p, q = (x, ys[0], z), (x, ys[1], z); es = 'RAILT' if tray else 'RAIL'; member(p, q, es); add_len(es, p, q)
        for y in ys:   # cross rails along x
            p, q = (xs[0], y, z), (xs[1], y, z); member(p, q, 'XRAIL'); add_len('XRAIL', p, q)
    for k in range(len(zl)-1):
        z0, z1 = zl[k], zl[k+1]
        if d['side_brace']:
            for x in xs:
                p, q = ((x, ys[0], z0), (x, ys[1], z1)) if k % 2 == 0 else ((x, ys[1], z0), (x, ys[0], z1))
                member(p, q, 'BRS'); add_len('BRS', p, q)
        if d['back_brace']:
            y = ys[1]
            p, q = ((xs[0], y, z0), (xs[1], y, z1)) if k % 2 == 0 else ((xs[1], y, z0), (xs[0], y, z1))
            member(p, q, 'BRB'); add_len('BRB', p, q)
        if d['front_brace']:   # ASSUMED removable bolted front diagonals (front is the tray-insertion face)
            y = ys[0]
            p, q = ((xs[0], y, z0), (xs[1], y, z1)) if k % 2 == 0 else ((xs[1], y, z0), (xs[0], y, z1))
            member(p, q, 'BRF'); add_len('BRF', p, q)
    if d['top_brace']:
        z = zl[-1]; p, q = (xs[0], ys[0], z), (xs[1], ys[1], z); member(p, q, 'BRT'); add_len('BRT', p, q)
    fix = [nodes[tuple(round(c, 9) for c in (x, y, 0.0))] for x in xs for y in ys]
    top = [nodes[tuple(round(c, 9) for c in (x, y, zl[-1]))] for x in xs for y in ys]
    # masses
    A = dict(POST=box_area(*d['post']), RAIL=box_area(*d['rail']), RAILT=box_area(*d['rail']), XRAIL=box_area(*d['xrail']),
             BRS=pipe_area(*d['brace']), BRB=pipe_area(*d['brace']), BRF=pipe_area(*d['brace']), BRT=pipe_area(*d['brace']))
    frame_kg = sum(RHO*A[k]*L[k] for k in L)
    rho_rt = RHO + d['m_equip']/(A['RAILT']*L['RAILT'])     # equipment smeared on tray side rails
    return dict(coords=coords, elems=elems, elsets=elsets, fix=fix, top=top, frame_kg=frame_kg, rho_rt=rho_rt, L=L, A=A, zl=zl)

def write_common(f, d, m):
    f.write('*HEADING\nrack screening (ASSUMED geometry)\n*NODE,NSET=NALL\n')
    for i, c in enumerate(m['coords'], 1): f.write(f'{i},{c[0]:.9e},{c[1]:.9e},{c[2]:.9e}\n')
    for es, ids in m['elsets'].items():
        f.write(f'*ELEMENT,TYPE=B32R,ELSET={es}\n')
        for i in ids:
            a, b, c, _ = m['elems'][i-1]; f.write(f'{i},{a},{b},{c}\n')
    f.write('*ELSET,ELSET=EALL\n' + ''.join(f'{es},\n' for es in m['elsets']))
    f.write('*NSET,NSET=NFIX\n' + ''.join(f'{i},\n' for i in m['fix']))
    for mat, rho in (('AL', RHO), ('ALEQ', m['rho_rt'])):
        f.write(f'*MATERIAL,NAME={mat}\n*ELASTIC\n{E:.6e},{NU}\n*DENSITY\n{rho:.6e}\n')
    def nvec(es):
        # orientation vector (local 1 direction), never parallel to member
        return {'POST': (1,0,0), 'RAIL': (0,0,1), 'RAILT': (0,0,1), 'XRAIL': (0,0,1), 'BRS': (1,0,0), 'BRB': (0,1,0), 'BRF': (0,1,0), 'BRT': (0,0,1)}[es]
    for es in m['elsets']:
        mat = 'ALEQ' if es == 'RAILT' else 'AL'; v = nvec(es)
        if es in ('POST', 'RAIL', 'RAILT', 'XRAIL'):
            key = {'POST': 'post', 'RAIL': 'rail', 'RAILT': 'rail', 'XRAIL': 'xrail'}[es]; a, b, t = d[key]
            f.write(f'*BEAM SECTION,ELSET={es},MATERIAL={mat},SECTION=BOX\n{a},{b},{t},{t},{t},{t}\n{v[0]},{v[1]},{v[2]}\n')
        else:
            r, t = d['brace']
            f.write(f'*BEAM SECTION,ELSET={es},MATERIAL={mat},SECTION=PIPE\n{r},{t}\n{v[0]},{v[1]},{v[2]}\n')
    f.write('*BOUNDARY\nNFIX,1,6\n')
    if d['top_tie']:   # ASSUMED lateral-only tie of the rack top to bus structure (x,y translation held; axial free)
        f.write('*NSET,NSET=NTOP\n' + ''.join(f'{i},\n' for i in m['top']) + '*BOUNDARY\nNTOP,1,2\n')

def run(job, cwd):
    t0 = time.time()
    r = subprocess.run([CCX, '-i', job], cwd=cwd, capture_output=True, text=True, env=dict(os.environ, OMP_NUM_THREADS='2'))
    open(os.path.join(cwd, job + '.log'), 'w').write(r.stdout + r.stderr)
    if r.returncode != 0 or 'ERROR' in r.stdout: raise RuntimeError(f'ccx failed {cwd}/{job}: ' + r.stdout[-2000:])
    return time.time() - t0

def parse_freq(dat):
    txt = open(dat).read(); fr = []
    blk = txt.split('E I G E N V A L U E   O U T P U T')[1].split('P A R T I C I P A T I O N')[0]
    for line in blk.splitlines():
        s = line.split()
        if len(s) == 5 and s[0].isdigit(): fr.append(float(s[3]))
    return fr

def parse_static(dat):
    """returns list per step of (max von Mises Pa, elem) and RF totals"""
    out = []; cur = None; mode = None; rf = []
    for line in open(dat):
        if line.strip().startswith('stresses'):
            cur = dict(vm=0.0, el=None); out.append(cur); mode = 'S'; continue
        if 'total force' in line: mode = 'RF'; continue
        if line.strip().startswith('displacements'): mode = 'U'; cur_u = dict(u=0.0); out.append(('U', cur_u)); continue
        s = line.split()
        if not s: continue
        if mode == 'S' and len(s) == 8:
            sx, sy, sz, txy, txz, tyz = map(float, s[2:])
            vm = math.sqrt(0.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)+3*(txy**2+txz**2+tyz**2))
            if vm > cur['vm']: cur['vm'] = vm; cur['el'] = int(s[0])
        elif mode == 'RF' and len(s) == 3:
            rf.append(tuple(map(float, s))); mode = None
        elif mode == 'U' and len(s) == 4:
            u = math.sqrt(sum(float(v)**2 for v in s[1:]))
            if u > cur_u['u']: cur_u['u'] = u
    S = [o for o in out if isinstance(o, dict)]; U = [o[1]['u'] for o in out if isinstance(o, tuple)]
    return S, U, rf

def analyse(d, n, wd, nmodes=8, buckle=True):
    os.makedirs(wd, exist_ok=True); m = build(d, n); timing = {}
    # modal
    with open(f'{wd}/modal.inp', 'w') as f:
        write_common(f, d, m); f.write(f'*STEP\n*FREQUENCY\n{nmodes}\n*END STEP\n')
    timing['modal_s'] = run('modal', wd); fr = parse_freq(f'{wd}/modal.dat')
    # statics: 1 g mass check + corners x angles
    steps = [('mass_1g', (0.0, 0.0, -1.0), G0)]
    for nm, (ax, lat) in CORNERS.items():
        for th in ANGLES:
            v = np.array([lat*math.cos(math.radians(th)), lat*math.sin(math.radians(th)), -ax]); mag = np.linalg.norm(v)
            steps.append((f'{nm}@{th}', tuple(v/mag), G0*mag))
    with open(f'{wd}/static.inp', 'w') as f:
        write_common(f, d, m)
        for nm, v, g in steps:
            f.write(f'** {nm}\n*STEP\n*STATIC\n*DLOAD,OP=NEW\nEALL,GRAV,{g:.6e},{v[0]:.9f},{v[1]:.9f},{v[2]:.9f}\n'
                    f'*NODE PRINT,NSET=NFIX,TOTALS=ONLY\nRF\n*NODE PRINT,NSET=NALL\nU\n*EL PRINT,ELSET=EALL\nS\n*END STEP\n')
    timing['static_s'] = run('static', wd); S, U, rf = parse_static(f'{wd}/static.dat')
    assert len(S) == len(steps) == len(U), (len(S), len(steps), len(U))
    model_kg = abs(rf[0][2])/G0
    res = {}
    for (nm, v, g), s, u in zip(steps[1:], S[1:], U[1:]):
        c, th = nm.split('@'); r = res.setdefault(c, dict(max_von_mises_MPa=0))
        if s['vm']/1e6 > r['max_von_mises_MPa']:
            r.update(max_von_mises_MPa=s['vm']/1e6, worst_angle_deg=int(th), elem=s['el'], max_disp_mm=u*1000)
    for r in res.values():
        r['MS_yield_FS1p25'] = FTY/(FS_Y*r['max_von_mises_MPa']*1e6) - 1
        r['MS_yield_FS1p25_x_fitting1p5'] = FTY/(FS_Y*FIT*r['max_von_mises_MPa']*1e6) - 1
    out = dict(n_per_member=n, n_nodes=len(m['coords']), n_beam_elements=len(m['elems']), frame_kg=m['frame_kg'],
               model_mass_from_1g_reaction_kg=model_kg, frequencies_Hz=fr, corners=res,
               min_MS_yield_FS1p25=min(r['MS_yield_FS1p25'] for r in res.values()),
               min_MS_with_fitting=min(r['MS_yield_FS1p25_x_fitting1p5'] for r in res.values()), timing=timing)
    if buckle:
        with open(f'{wd}/buckle.inp', 'w') as f:
            write_common(f, d, m)
            f.write(f'*STEP\n*BUCKLE\n3\n*DLOAD\nEALL,GRAV,{G0*6*FS_Y:.6e},0,0,-1\n*END STEP\n')
        timing['buckle_s'] = run('buckle', wd)
        txt = open(f'{wd}/buckle.dat').read()
        bf = [float(l.split()[1]) for l in txt.split('B U C K L I N G   F A C T O R   O U T P U T')[1].splitlines() if len(l.split()) == 2 and l.split()[0].isdigit()]
        out['buckling_factor_on_7p5g_axial'] = bf
    return out
