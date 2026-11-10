"""PhysicsNeMo residual surrogate of native Warp fin labels; held-out labels never train."""
import time,json,hashlib,platform
from pathlib import Path
import numpy as np
import torch,physicsnemo
from physicsnemo.models.mlp import FullyConnected
R=Path(__file__).resolve().parent;d=np.load(R/'FIN_DATASET.npz');torch.manual_seed(20261107);np.random.seed(20261107)
assert torch.cuda.is_available();device='cuda';rawx=d['x'];truth=d['eta'];ti=d['train_index'];vi=d['heldout_index'];mu=rawx[ti].mean(0);sd=rawx[ti].std(0)
def base(a):
 z=np.sqrt(4*a);return np.tanh(z)/z
baseline=base(np.exp(rawx[:,0]));xt=torch.tensor((rawx-mu)/sd,dtype=torch.float32,device=device);yt=torch.tensor((truth-baseline)*100,dtype=torch.float32,device=device).reshape(-1,1)
model=FullyConnected(in_features=2,out_features=1,layer_size=48,num_layers=3,activation_fn='silu').to(device)
opt=torch.optim.Adam(model.parameters(),lr=.003);start=time.perf_counter();losses=[]
for step in range(3500):
 opt.zero_grad(set_to_none=True);loss=((model(xt[ti])-yt[ti])**2).mean();loss.backward();opt.step()
 if step%350==0:losses.append([step,float(loss.item())]);print('train',losses[-1],flush=True)
opt2=torch.optim.LBFGS(model.parameters(),lr=.7,max_iter=400,tolerance_grad=1e-9,tolerance_change=1e-11,line_search_fn='strong_wolfe')
def closure():
 opt2.zero_grad();loss=((model(xt[ti])-yt[ti])**2).mean();loss.backward();return loss
opt2.step(closure);torch.cuda.synchronize();train_wall=time.perf_counter()-start
with torch.no_grad():pred=baseline+model(xt).flatten().cpu().numpy()/100
err=np.abs(pred[vi]-truth[vi]);agrid=np.linspace(np.log(.0005),np.log(1.5),513);bgrid=np.linspace(.30,.76,129);xx,bb=np.meshgrid(agrid,bgrid,indexing='ij');query=np.stack([xx.ravel(),bb.ravel()],1);qcl=query.copy();qcl[:,0]=np.maximum(qcl[:,0],np.log(.008))
with torch.no_grad():res=model(torch.tensor((qcl-mu)/sd,dtype=torch.float32,device=device)).flatten().cpu().numpy()/100
low=np.minimum(1,np.exp(query[:,0])/.008)**2;lin=base(np.exp(query[:,0]));vals=np.clip(lin+res*low,lin,1.)
np.savez_compressed(R/'SURROGATE_TABLE.npz',eta=vals.reshape(len(agrid),len(bgrid)),log_a=agrid,b=bgrid)
torch.save(dict(state=model.state_dict(),mu=mu,sd=sd),R/'PHYSICSNEMO_SURROGATE.pt')
np.savez_compressed(R/'SURROGATE_VALIDATION.npz',true=truth[vi],prediction=pred[vi],x=rawx[vi],train_true=truth[ti],train_pred=pred[ti])
out=dict(tool='NVIDIA PhysicsNeMo FullyConnected',physicsnemo=physicsnemo.__version__,torch=torch.__version__,device='cuda:0',architecture=dict(inputs=2,hidden=48,layers=3,output='eta_fin residual from tangent-linear fin solution'),training_labels=len(ti),heldout_labels=len(vi),heldout_max_abs_eta=float(err.max()),heldout_RMSE=float(np.sqrt(np.mean(err**2))),heldout_p99_abs_eta=float(np.quantile(err,.99)),passed=bool(err.max()<.003),training_wall_seconds=train_wall,table_shape=[len(agrid),len(bgrid)],training_loss=losses,label_source='Native fp64 Warp finite-volume Newton/PCG; held-out labels not used for training',seed=20261107,limits='Conditional deterministic surrogate, not flight validation. Table spans dimensionless groups; low-a tangent limit. Selected design must be re-solved with native Warp fin table.',table_sha256=hashlib.sha256((R/'SURROGATE_TABLE.npz').read_bytes()).hexdigest())
(R/'SURROGATE_RESULT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True);assert out['passed']
