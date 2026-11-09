"""RGB + public telemetry IPC. No simulation handle, boat truth or teacher."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import contextlib,hashlib,json,struct,sys
import numpy as np,torch
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2];bundle=ROOT/sys.argv[1]
sys.dont_write_bytecode=True;sys.path.insert(0,str(BASE))
import landing_training
landing_training.__path__.insert(0,str(bundle/'code/landing_training'))
from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
from landing_training.radio_robust_20261015.controller.supervision import supervise_action
config=json.loads((bundle/'policy.json').read_text())
for name,expected in config['file_hashes'].items():
 if '__pycache__' not in name:assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==expected,name
torch.set_num_threads(1)
with contextlib.redirect_stdout(sys.stderr):policy=RadioRobustRuntime(bundle/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
def clean(v):
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
 if isinstance(v,np.generic):v=v.item()
 if isinstance(v,float) and not np.isfinite(v):return None
 return v
def send(value):
 data=json.dumps(clean(value),allow_nan=False,separators=(',',':')).encode();sys.stdout.buffer.write(struct.pack('<I',len(data))+data);sys.stdout.buffer.flush()
def read(n):
 data=bytearray()
 while len(data)<n:
  part=sys.stdin.buffer.read(n-len(data))
  if not part:raise EOFError
  data.extend(part)
 return bytes(data)
send(dict(ready=True,checkpoint_sha256=config['checkpoint_sha256'],policy_sha256=hashlib.sha256((bundle/'policy.json').read_bytes()).hexdigest(),backend='Native PyTorch FP32 CUDA / native marker fitter; not browser ONNX parity evidence'))
while True:
 try:header=read(8)
 except EOFError:break
 json_size,rgb_size=struct.unpack('<II',header);assert 0<json_size<100000 and rgb_size==640*360*3
 request=json.loads(read(json_size));rgb=np.frombuffer(read(rgb_size),dtype=np.uint8).reshape(360,640,3)
 o=request['observation']
 with contextlib.redirect_stdout(sys.stderr):
  action,diag=policy.act(rgb,o);action,reason=supervise_action(action,o,float(request['elapsed']),180.)
 if diag.get('recovery_exhausted'):action=np.zeros(6);reason='bounded_recovery_exhausted'
 send(dict(action=action,diagnostics=diag,intervention=reason))
