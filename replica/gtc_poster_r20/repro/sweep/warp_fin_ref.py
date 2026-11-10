"""Differentiable 2-D conduction + radiation fin/panel solver in NVIDIA Warp (float64).
Steady state of  div(k t grad T) - 2 eps_eff sigma (T^4 - Ts^4) = 0  on a rectangular fin panel (half pitch L between tubes, length Ly),
tube edge x=0 Dirichlet Tb, other edges adiabatic (symmetry). Newton + Jacobi-PCG (matrix-free); gradients by adjoint:  J^T lam = dQ/dT, dQ/dt = lam . dR/dt with dR/dt from wp.Tape (autodiff)."""
import numpy as np
import warp as wp
wp.config.quiet = True
f64=wp.float64
SIG=5.670374e-8   # Stefan-Boltzmann constant [W/m^2/K^4] (CODATA 2018 exact-derived value)
@wp.func
def tf(a: f64, b: f64):
    return f64(2.0)*a*b/(a+b)
@wp.kernel
def residual(T: wp.array2d(dtype=f64), t: wp.array2d(dtype=f64), Tb: f64, k: f64, ee: f64, Ts: f64, h: f64, R: wp.array2d(dtype=f64)):
    j,i=wp.tid(); ny=T.shape[0]; nx=T.shape[1]
    Ti=T[j,i]; ti=t[j,i]; s=f64(0.0)
    if i==0:
        s+=f64(2.0)*k*ti*(Tb-Ti)
    else:
        s+=k*tf(ti,t[j,i-1])*(T[j,i-1]-Ti)
    if i<nx-1:
        s+=k*tf(ti,t[j,i+1])*(T[j,i+1]-Ti)
    if j>0:
        s+=k*tf(ti,t[j-1,i])*(T[j-1,i]-Ti)
    if j<ny-1:
        s+=k*tf(ti,t[j+1,i])*(T[j+1,i]-Ti)
    T2=Ti*Ti
    s-=f64(2.0)*ee*f64(5.670374e-8)*(T2*T2-Ts*Ts*Ts*Ts)*h*h
    R[j,i]=s
@wp.kernel
def jneg_apply(T: wp.array2d(dtype=f64), t: wp.array2d(dtype=f64), v: wp.array2d(dtype=f64), k: f64, ee: f64, h: f64, out: wp.array2d(dtype=f64)):
    j,i=wp.tid(); ny=T.shape[0]; nx=T.shape[1]
    vi=v[j,i]; ti=t[j,i]; s=f64(0.0)
    if i==0:
        s+=f64(2.0)*k*ti*vi
    else:
        s+=k*tf(ti,t[j,i-1])*(vi-v[j,i-1])
    if i<nx-1:
        s+=k*tf(ti,t[j,i+1])*(vi-v[j,i+1])
    if j>0:
        s+=k*tf(ti,t[j-1,i])*(vi-v[j-1,i])
    if j<ny-1:
        s+=k*tf(ti,t[j+1,i])*(vi-v[j+1,i])
    Ti=T[j,i]
    s+=f64(8.0)*ee*f64(5.670374e-8)*Ti*Ti*Ti*h*h*vi
    out[j,i]=s
@wp.kernel
def jneg_diag(T: wp.array2d(dtype=f64), t: wp.array2d(dtype=f64), k: f64, ee: f64, h: f64, d: wp.array2d(dtype=f64)):
    j,i=wp.tid(); ny=T.shape[0]; nx=T.shape[1]
    ti=t[j,i]; s=f64(0.0)
    if i==0:
        s+=f64(2.0)*k*ti
    else:
        s+=k*tf(ti,t[j,i-1])
    if i<nx-1:
        s+=k*tf(ti,t[j,i+1])
    if j>0:
        s+=k*tf(ti,t[j-1,i])
    if j<ny-1:
        s+=k*tf(ti,t[j+1,i])
    Ti=T[j,i]
    s+=f64(8.0)*ee*f64(5.670374e-8)*Ti*Ti*Ti*h*h
    d[j,i]=s
@wp.kernel
def rad_total(T: wp.array2d(dtype=f64), ee: f64, Ts: f64, h: f64, q: wp.array2d(dtype=f64)):
    j,i=wp.tid(); Ti=T[j,i]; T2=Ti*Ti
    q[j,i]=f64(2.0)*ee*f64(5.670374e-8)*(T2*T2-Ts*Ts*Ts*Ts)*h*h
@wp.kernel
def dq_dT(T: wp.array2d(dtype=f64), ee: f64, h: f64, g: wp.array2d(dtype=f64)):
    j,i=wp.tid(); Ti=T[j,i]
    g[j,i]=f64(8.0)*ee*f64(5.670374e-8)*Ti*Ti*Ti*h*h
@wp.kernel
def axpy(a: f64, x: wp.array2d(dtype=f64), y: wp.array2d(dtype=f64)):   # y += a x
    j,i=wp.tid(); y[j,i]=y[j,i]+a*x[j,i]
@wp.kernel
def xpay(a: f64, x: wp.array2d(dtype=f64), y: wp.array2d(dtype=f64)):   # y = x + a y
    j,i=wp.tid(); y[j,i]=x[j,i]+a*y[j,i]
@wp.kernel
def divd(r: wp.array2d(dtype=f64), d: wp.array2d(dtype=f64), z: wp.array2d(dtype=f64)):
    j,i=wp.tid(); z[j,i]=r[j,i]/d[j,i]
@wp.kernel
def copy2(x: wp.array2d(dtype=f64), y: wp.array2d(dtype=f64)):
    j,i=wp.tid(); y[j,i]=x[j,i]
@wp.kernel
def fill2(a: f64, y: wp.array2d(dtype=f64)):
    j,i=wp.tid(); y[j,i]=a
@wp.kernel
def sumloss(q: wp.array2d(dtype=f64), out: wp.array(dtype=f64)):
    j,i=wp.tid(); wp.atomic_add(out,0,q[j,i])

def default_device():
    """'cuda:0' when Warp sees a GPU, otherwise 'cpu' (the solver is float64 and runs on both)."""
    wp.init()
    return 'cuda:0' if wp.get_cuda_device_count() > 0 else 'cpu'

class Fin:
    def __init__(s, nx, ny, L, Ly, k, ee, Tb, Ts, device=None):
        if device is None:
            device = default_device()
        s.nx,s.ny,s.L,s.Ly,s.k,s.ee,s.Tb,s.Ts=nx,ny,L,Ly,k,ee,Tb,Ts; s.h=L/nx; s.dev=device; s.shape=(ny,nx)
        z=lambda rg=False: wp.zeros(s.shape,dtype=f64,device=device,requires_grad=rg)
        s.T=z(); s.R=z(True); s.t=z(True); s.d=z(); s.r=z(); s.zv=z(); s.p=z(); s.Ap=z(); s.g=z(); s.lam=z(); s.q=z(); s.dT=z(); s.Tn=z(); s.Rn=z()
        s.tot=wp.zeros(1,dtype=f64,device=device)
        s.ncg=0
    def L2(s,a):  # inner product
        return float(wp.utils.array_inner(a,a,))
    def dot(s,a,b): return float(wp.utils.array_inner(a,b))
    def res(s,T,t,R): wp.launch(residual,s.shape,[T,t,f64(s.Tb),f64(s.k),f64(s.ee),f64(s.Ts),f64(s.h),R],device=s.dev)
    def pcg(s,b,x,tol=1e-10,maxit=60000):
        """solve Jneg x = b (Jneg SPD at current s.T, s.t); Jacobi preconditioner"""
        h,k,ee=f64(s.h),f64(s.k),f64(s.ee)
        wp.launch(jneg_diag,s.shape,[s.T,s.t,k,ee,h,s.d],device=s.dev)
        wp.launch(fill2,s.shape,[f64(0.0),x],device=s.dev)
        wp.launch(copy2,s.shape,[b,s.r],device=s.dev)
        wp.launch(divd,s.shape,[s.r,s.d,s.zv],device=s.dev); wp.launch(copy2,s.shape,[s.zv,s.p],device=s.dev)
        rz=s.dot(s.r,s.zv); b2=max(s.dot(b,b),1e-300); it=0
        while it<maxit:
            wp.launch(jneg_apply,s.shape,[s.T,s.t,s.p,k,ee,h,s.Ap],device=s.dev)
            a=rz/s.dot(s.p,s.Ap)
            wp.launch(axpy,s.shape,[f64(a),s.p,x],device=s.dev); wp.launch(axpy,s.shape,[f64(-a),s.Ap,s.r],device=s.dev)
            it+=1
            if s.dot(s.r,s.r)<tol*tol*b2: break
            wp.launch(divd,s.shape,[s.r,s.d,s.zv],device=s.dev); rzn=s.dot(s.r,s.zv)
            wp.launch(xpay,s.shape,[f64(rzn/rz),s.zv,s.p],device=s.dev); rz=rzn
        s.ncg+=it; return it
    def solve(s,tol=1e-10,maxnewton=40,verbose=False,cgtol=1e-10):
        wp.launch(fill2,s.shape,[f64(s.Tb),s.T],device=s.dev)
        s.ncg=0
        for n in range(maxnewton):
            s.res(s.T,s.t,s.R); r0=np.sqrt(s.L2(s.R))
            if n==0: rinit=r0
            if verbose: print('newton',n,r0)
            if n>0 and r0<tol*rinit: break
            s.pcg(s.R,s.dT,tol=cgtol)       # Jneg dT = R  (since J=-Jneg, J dT=-R)
            lam=1.0
            while True:
                wp.launch(copy2,s.shape,[s.T,s.Tn],device=s.dev); wp.launch(axpy,s.shape,[f64(lam),s.dT,s.Tn],device=s.dev)
                s.res(s.Tn,s.t,s.Rn); r1=np.sqrt(s.L2(s.Rn))
                if r1<r0 or lam<1e-4: break
                lam*=0.5
            wp.launch(copy2,s.shape,[s.Tn,s.T],device=s.dev)
        s.res(s.T,s.t,s.R); return np.sqrt(s.L2(s.R))
    def Q(s):
        wp.launch(rad_total,s.shape,[s.T,f64(s.ee),f64(s.Ts),f64(s.h),s.q],device=s.dev)
        s.tot.zero_(); wp.launch(sumloss,s.shape,[s.q,s.tot],device=s.dev); return float(s.tot.numpy()[0])
    def grad_Q_t(s):
        """dQ/dt (per cell) by adjoint: Jneg lam = dQ/dT ; dQ/dt = lam . dR/dt (tape backward)"""
        wp.launch(dq_dT,s.shape,[s.T,f64(s.ee),f64(s.h),s.g],device=s.dev)
        s.pcg(s.g,s.lam)
        tape=wp.Tape()
        s.t.grad.zero_()
        with tape: s.res(s.T,s.t,s.R)
        tape.backward(grads={s.R: s.lam}); 
        g=s.t.grad.numpy().copy(); tape.zero(); return g
    def mass(s,rho): return rho*s.h*s.h*float(s.t.numpy().sum())

