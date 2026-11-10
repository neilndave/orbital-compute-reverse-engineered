"""PhysicsNeMo surrogate inference stage: the frozen checkpoint (PHYSICSNEMO_SURROGATE.pt) evaluated on the 513 x 129 = 66,177-point
dimensionless query grid that builds SURROGATE_TABLE.npz (same construction as train_surrogate.py). Model load, tensor creation and
host<->device copies excluded; warm-up forward pass excluded; timed = one no_grad forward pass, synchronized (CUDA) . CPU: torch.set_num_threads(1),
pinned to one core by taskset. Repetitions are separate processes. Also checks the rebuilt table against SURROGATE_TABLE.npz."""
import sys,json,time,hashlib,os
from pathlib import Path
import numpy as np,torch,physicsnemo
from physicsnemo.models.mlp import FullyConnected
R=Path(__file__).resolve().parent;dev=sys.argv[1];label=sys.argv[2]
if dev=='cpu':torch.set_num_threads(1);torch.set_num_interop_threads(1)
s=torch.load(R/'PHYSICSNEMO_SURROGATE.pt',map_location=dev,weights_only=False);m=FullyConnected(in_features=2,out_features=1,layer_size=48,num_layers=3,activation_fn='silu').to(dev);m.load_state_dict(s['state']);m.eval()
def base(a):
 z=np.sqrt(4*a);return np.tanh(z)/z
ag=np.linspace(np.log(.0005),np.log(1.5),513);bg=np.linspace(.30,.76,129);xx,bb=np.meshgrid(ag,bg,indexing='ij');q=np.stack([xx.ravel(),bb.ravel()],1);qc=q.copy();qc[:,0]=np.maximum(qc[:,0],np.log(.008))
X=torch.tensor((qc-s['mu'])/s['sd'],dtype=torch.float32,device=dev);sync=(torch.cuda.synchronize if dev.startswith('cuda') else (lambda:None))
with torch.no_grad():
 st=time.perf_counter();m(X[:512]);sync();warm=time.perf_counter()-st
 st=time.perf_counter();y=m(X);sync();kt=time.perf_counter()-st
res=y.flatten().cpu().numpy()/100;low=np.minimum(1,np.exp(q[:,0])/.008)**2;lin=base(np.exp(q[:,0]));vals=np.clip(lin+res*low,lin,1.).reshape(513,129)
ref=np.load(R/'SURROGATE_TABLE.npz')['eta']
out=dict(stage='surrogate_inference',label=label,device=dev,torch=torch.__version__,physicsnemo=physicsnemo.__version__,threads=torch.get_num_threads(),cpu_affinity=sorted(os.sched_getaffinity(0)),queries=int(X.shape[0]),warmup_seconds=warm,kernel_seconds=kt,max_abs_diff_vs_table=float(np.abs(vals-ref).max()),checkpoint_sha256=hashlib.sha256((R/'PHYSICSNEMO_SURROGATE.pt').read_bytes()).hexdigest(),method=__doc__)
(R/'results').mkdir(exist_ok=True);(R/'results'/f'SURR_{label}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['label','kernel_seconds','max_abs_diff_vs_table']}),flush=True)
