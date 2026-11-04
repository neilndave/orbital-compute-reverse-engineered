import numpy as np, glob, json, sys
d=sys.argv[1]; n=30; pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
fs=sorted(glob.glob(d+'/f*.npz')); T=[];G=[]
for f in fs:
    z=np.load(f); T.append(float(z['T'])); G.append(z['G'])
T=np.array(T);G=np.array(G)
print(len(fs),"frames, T",T.min(),T.max(), "nan frac",np.isnan(G).mean())
mn=np.nanmin(G,0); am=np.nanargmin(G,0)
out={f"{i}-{j}":[float(mn[k]),float(T[am[k]])] for k,(i,j) in enumerate(pairs)}
neg=sorted([(v[0],k,round(v[1],1)) for k,v in out.items() if v[0]<0])
print("neg pairs",len(neg)); [print(x) for x in neg]
print("global min",float(np.nanmin(G)), "n pairs",len(pairs))
# same-layer pair mins
print("(2k,2k+1) mins:",[round(out[f"{2*k}-{2*k+1}"][0],3) for k in range(12)])
print("sorted smallest positives:",[(round(v,4),k,t) for v,k,t in sorted((v[0],k,v[1]) for k,v in out.items() if v[0]>=0)[:8]])
json.dump({"per_pair_min_gap_T":out,"global_min":float(np.nanmin(G))},open(sys.argv[2],'w'))
