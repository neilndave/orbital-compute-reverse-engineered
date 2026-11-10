from pathlib import Path
import json,hashlib
import numpy as np
import torch,physicsnemo
from physicsnemo.models.mlp import FullyConnected
r=Path(__file__).resolve().parent;d=np.load(r/'FIN_DATASET.npz');old=np.load(r/'SURROGATE_VALIDATION.npz');saved=torch.load(r/'PHYSICSNEMO_SURROGATE.pt',map_location='cuda',weights_only=False);x=d['x'];vi=d['heldout_index'];ti=d['train_index'];z=torch.tensor((x-saved['mu'])/saved['sd'],dtype=torch.float32,device='cuda');model=FullyConnected(in_features=2,out_features=1,layer_size=48,num_layers=3,activation_fn='silu').cuda();model.load_state_dict(saved['state']);model.eval()
a=np.exp(x[:,0]);base=np.tanh(np.sqrt(4*a))/np.sqrt(4*a)
with torch.no_grad():pred=base+model(z).flatten().cpu().numpy()/100
err=np.abs(pred[vi]-d['eta'][vi]);j=dict(diagnostic_only=True,training_rerun=False,inference_rerun=True,native_labels_rerun=True,training_labels=len(ti),heldout_labels=len(vi),heldout_max_abs_eta=float(err.max()),heldout_RMSE=float(np.sqrt(np.mean(err**2))),max_difference_from_frozen_predictions=float(np.max(abs(pred[vi]-old['prediction']))),torch=torch.__version__,physicsnemo=physicsnemo.__version__,checkpoint_sha256=hashlib.sha256((r/'PHYSICSNEMO_SURROGATE.pt').read_bytes()).hexdigest(),passed=bool(err.max()<.003),scope='Inference and independently regenerated native labels; not training rerun and not Rubin hardware qualification.')
(r/'FIT_REVALIDATION.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
