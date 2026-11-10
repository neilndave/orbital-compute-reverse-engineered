"""Deep numeric compare of two JSON files. Strings are compared only if they contain no filesystem path; dict keys that are absolute paths are normalised to their basename."""
import json,sys,math,re
def norm(o):
    if isinstance(o,dict): return {(k.rsplit('/',1)[-1] if k.startswith('/') else k):norm(v) for k,v in o.items()}
    if isinstance(o,list): return [norm(v) for v in o]
    return o
def cmp(a,b,path,out,rtol,atol):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in set(a)|set(b):
            if k not in a or k not in b: out.append((path+'/'+str(k),'missing')); continue
            cmp(a[k],b[k],path+'/'+str(k),out,rtol,atol)
    elif isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b): out.append((path,'len')); return
        for i,(x,y) in enumerate(zip(a,b)): cmp(x,y,f'{path}[{i}]',out,rtol,atol)
    elif isinstance(a,bool) or isinstance(b,bool):
        if a!=b: out.append((path,a,b))
    elif isinstance(a,(int,float)) and isinstance(b,(int,float)):
        if not (a==b or (math.isnan(a) and math.isnan(b)) or abs(a-b)<=atol+rtol*abs(b)): out.append((path,a,b))
    elif isinstance(a,str) and isinstance(b,str):
        if a!=b and not re.search(r'/(workspace|home|tmp)/',a+b) and not re.fullmatch(r'[0-9a-f]{64}',a): out.append((path,a[:80],b[:80]))
    elif a!=b: out.append((path,str(a)[:80],str(b)[:80]))
if __name__=='__main__':
    a,b=[norm(json.load(open(f))) for f in sys.argv[1:3]];rtol=float(sys.argv[3]) if len(sys.argv)>3 else 1e-12;atol=float(sys.argv[4]) if len(sys.argv)>4 else 1e-9
    out=[];cmp(a,b,'',out,rtol,atol);print(sys.argv[1].split('/')[-1],'DIFFS',len(out));[print(' ',*d) for d in out[:15]];sys.exit(1 if out else 0)
