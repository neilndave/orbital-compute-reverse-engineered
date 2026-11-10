"""v3 exact array-view increment (NumPy Nusselt contour, independently CUDA-checked later).
Inherits c8 three points/panel and fixed bus blockage; array extends outward, not toward radiator.
"""
import json, math
import numpy as np

def points(g):
    W,L,gap=g['panel_W_mm'],g['panel_L_mm'],g['gap_mm'];zt=g['wing_width_mm']/2
    out=[];w0=g['wing0_cols']
    for ci,n in enumerate(g['panels_per_column']):
        z=-zt+(ci%max(w0,1) if ci<w0 else ci-w0)*(W+gap)+W/2
        for j in range(n):
            for s in (0.1667,0.5,0.8333):out.append(((g['y0_mm']+j*(L+gap)+s*L)/1000,z/1000))
    return np.asarray(out), (zt+255)/1000

def exact(g,length,width=14):
    yz,zr=points(g);py,pz=yz[:,0],yz[:,1];x0=g['array_root_mm']/1000
    verts=[np.stack([np.full_like(py,x),y-py,zr-pz],1) for x,y in ((x0,-width/2),(x0+length,-width/2),(x0+length,width/2),(x0,width/2))]
    s=0.0
    for a,b in zip(verts,verts[1:]+verts[:1]):
        cross=np.cross(a,b);cn=np.linalg.norm(cross,axis=1)
        s=s+np.arctan2(cn,(a*b).sum(1))*cross[:,0]/cn
    return np.abs(s)/(2*np.pi)
