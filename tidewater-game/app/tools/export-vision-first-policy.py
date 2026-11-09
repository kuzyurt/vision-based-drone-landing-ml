"""Export the preserved vision-first fusion candidate and exact R8 controller.

Only the neural execution boundary and native fitter binding are adapted. No
training, quantization, touchdown relaxation or boat-state control shortcut.
"""
import ast, copy, hashlib, importlib, json, shutil, sys, types
from pathlib import Path
import numpy as np
import onnxruntime as ort
import torch
from torch import nn
from torch.nn import functional as F
sys.dont_write_bytecode=True

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'artifacts/vision_first_fusion_20261017/vision_first_fusion_delivery/candidate'
OUT=ROOT/'tidewater-game/app/public/policy'
FIXTURES=ROOT/'tidewater-game/simulation/runtime/ml-fixtures'
GOLD=ROOT/'artifacts/tidewater_policy_20261017/native-fixtures'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def package():
    p=types.ModuleType('vision_first_export');p.__path__=[str(BUNDLE/'code/landing_training')];sys.modules[p.__name__]=p
    # Export needs the original vector builder, not its optional HDF5 recorder.
    tree=ast.parse((BUNDLE/'code/landing_training/recording.py').read_text())
    numeric=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='numeric_observation')
    recording=types.ModuleType(p.__name__+'.recording')
    exec('import math\nimport numpy as np\n'+ast.unparse(numeric),recording.__dict__)
    sys.modules[recording.__name__]=recording
    return p.__name__+'.radio_robust_20261015'

class SpatialMean(nn.Module):
    def forward(self,value):
        n,c,h,w=value.shape
        return value.reshape(n,c,h*w).mean(-1).reshape(n,c,1,1)

def parallel_means(module):
    for name,child in list(module.named_children()):
        if isinstance(child,nn.AdaptiveAvgPool2d) and child.output_size in (1,(1,1)):setattr(module,name,SpatialMean())
        else:parallel_means(child)

class BrowserModel(nn.Module):
    def __init__(self,model,spatial):super().__init__();self.model=model;self.spatial=spatial
    def forward(self,image,numeric,hidden):
        b=self.model.backbone;n=numeric[...,:32];uncertainty=numeric[...,32:34]
        x=image.reshape(1,3,360,640)/255.;x=(x-b.image_mean)/b.image_std
        for i,layer in enumerate(b.encoder):
            x=layer(x)
            if i==3:fine=x
            if i==8:context=x
        channels,height,width=x.shape[1:];probability=x.reshape(1,channels,-1).softmax(-1)
        yy,xx=torch.meshgrid(torch.linspace(-1,1,height),torch.linspace(-1,1,width),indexing='ij')
        features=torch.stack(((probability*xx.flatten()).sum(-1),(probability*yy.flatten()).sum(-1),x.mean((2,3))),-1).reshape(1,1,-1)
        # Exactly the parent's missing-radio visual recurrence, independent of
        # actual radio coordinates, validity, age, status and reported quality.
        visual=n* n.new_tensor([0. if i in (*range(11,17),19,21,22) else 1. for i in range(32)])
        visual=visual+torch.cat((torch.zeros_like(n[...,:19]),torch.full_like(n[...,19:20],3.1),torch.zeros_like(n[...,20:22]),b.observation_mean[22:23].reshape(1,1,1),torch.zeros_like(n[...,23:])),dim=-1)
        angles=torch.cat((visual[...,5:6],visual[...,9:11]),-1)
        trig=torch.stack((angles.sin(),angles.cos()),-1).reshape(1,1,6)
        represented=visual*visual.new_tensor([0. if i in (5,9,10,24,25,26,27,28,29) else 1. for i in range(32)])+torch.cat((torch.zeros_like(n[...,:24]),trig,torch.zeros_like(n[...,30:])),dim=-1)
        normalized=(represented-b.observation_mean)/b.observation_std
        normalized=torch.cat((normalized[...,:11],torch.zeros_like(n[...,11:17]),normalized[...,17:19],normalized[...,19:20].clamp(-10.,10.),normalized[...,20:21],-torch.ones_like(n[...,21:22]),normalized[...,22:]),-1)
        state=b.telemetry(normalized)+self.model.quality(torch.log1p(n.new_tensor([100.,10.]))-torch.log1p(n.new_tensor([.25,.025])))
        gi=F.linear(torch.cat((b.visual(features),state),-1),b.gru.weight_ih_l0,b.gru.bias_ih_l0)
        gh=F.linear(hidden,b.gru.weight_hh_l0,b.gru.bias_hh_l0)
        reset=(gi[...,:128]+gh[...,:128]).sigmoid();update=(gi[...,128:256]+gh[...,128:256]).sigmoid()
        next_hidden=(1-update)*torch.tanh(gi[...,256:]+reset*gh[...,256:])+update*hidden
        raw=b.auxiliary(next_hidden);absolute=self.model.visual_absolute(next_hidden)
        visual_pose=torch.cat((raw[...,:1],absolute[...,:3],absolute[...,3:6]-n[...,:3],F.normalize(raw[...,7:9],dim=-1,eps=1e-6),F.normalize(raw[...,9:12]+raw.new_tensor([0.,0.,-1.]),dim=-1,eps=1e-6),raw[...,12:15]),-1)
        position=n[...,11:14]+n[...,14:17]*n[...,19:20].clamp(0.,3.)
        velocity=n[...,14:17]-n[...,:3];dp=position-visual_pose[...,1:4];dv=velocity-visual_pose[...,4:7]
        gate_input=torch.cat((dp/5.,dv,torch.log1p(uncertainty.clamp(0.,1000.)),n[...,19:20].clamp(0.,3.)/3.,visual_pose[...,:1].sigmoid(),dp.norm(dim=-1,keepdim=True)/5.,dv.norm(dim=-1,keepdim=True),torch.log1p(visual_pose[...,1:4].norm(dim=-1,keepdim=True))/4.),-1)
        # Python validates finite packet coordinates/uncertainty before export's
        # boundary; missing packets carry an explicit zero validity flag.
        available=(n[...,21:22]>.5).to(n.dtype)*(n[...,19:20]<3.).to(n.dtype)
        weights=self.model.fusion_gate(gate_input).sigmoid()*.35*available
        prediction=torch.cat((visual_pose[...,:1],visual_pose[...,1:4]+weights[...,:1]*dp,visual_pose[...,4:7]+weights[...,1:2]*dv,visual_pose[...,7:]),-1)
        heat,offset,presence=self.spatial(fine,context);h,w=heat.shape[-2:]
        index=heat.flatten(1).argmax(1)
        # Gather the floating-point coordinates directly. WebGPU supports the
        # ArgMax int64 index as Gather input, but cannot cast that index to f32.
        rows,cols=torch.meshgrid(torch.arange(h,dtype=torch.float32),torch.arange(w,dtype=torch.float32),indexing='ij')
        centers=torch.stack(((cols+.5+offset[:,0])*2/w-1.,(rows+.5+offset[:,1])*2/h-1.),1).reshape(1,2,-1)
        center=torch.index_select(centers,2,index).reshape(1,1,2)
        return torch.cat((prediction,presence.reshape(1,1,1),center,weights),-1),next_hidden

def export_controller(config,mean22):
    source=BUNDLE/'code/landing_training/radio_robust_20261015/controller';dest=OUT/'reference';dest.mkdir(exist_ok=True)
    names=['action_guard.py','camera_geometry.py','camera_geometry_fast.py','marker_geometry.py','marker_geometry_fast.py','supervision.py','hybrid_policy.py','marker_policy.py','visual_acquisition.py','observable_acquisition.py','camera_obstruction_map.json']
    for name in names:shutil.copyfile(source/name,dest/name)
    (dest/'__init__.py').write_text('')
    tree=ast.parse((source/'recording.py').read_text());numeric=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='numeric_observation')
    (dest/'recording.py').write_text('import math\nimport numpy as np\n'+ast.unparse(numeric)+'\n')
    # These R8 modules already externalize neural execution. Preserve all their
    # control laws instead of applying the old v5 dropout source transforms.
    for name in ['hybrid_policy.py','marker_policy.py']:
        code=(dest/name).read_text();assert 'import torch' not in code,name
    with (dest/'marker_geometry.py').open('a') as f:
        f.write('''
marker_pose_reference=marker_pose
def marker_pose(rgb,observation,calibration,estimate):
    from js import marker_kernel
    from .marker_geometry_fast import marker_pose_fast
    if not observation['beacon'].get('valid',False) and not estimate.get('_tracked',False):
        from .visual_acquisition import paint_prior
        estimate=paint_prior(rgb,observation,calibration,estimate)
        if estimate is None:return None
    return marker_pose_fast(rgb,observation,calibration,estimate,marker_kernel)
''')
    fixes=(source.parent/'runtime_fixes.py').read_text().replace("package+'.controller.","package+'.").replace('from .controller.observable_acquisition','from .observable_acquisition')
    (dest/'runtime_fixes.py').write_text(fixes)
    (dest/'browser_api.py').write_text('''"""Faithful native RadioRobustRuntime boundary; neural FP32 executes on GPU."""
import copy, json, math
import numpy as np
from .marker_policy import MarkerPosePolicy
from .recording import numeric_observation
from .supervision import supervise_action
from . import runtime_fixes

policy=None
def initialize(configuration_json):
    global policy,config
    config=json.loads(configuration_json)
    runtime_fixes.install(__package__)
    policy=MarkerPosePolicy(None,config['calibration'],config['slew_limits'],'browser')
    policy.reset();policy.controller.visual_search_started=None

def prepare(observation):
    observation=copy.deepcopy(observation);b=observation.setdefault('beacon',{})
    b.setdefault('dock_ready',False)
    known=bool(b.get('dock_status_valid',b.get('valid',False)));ready=bool(b['dock_ready'])
    sp=float(b.get('position_sigma_m',1.));sv=float(b.get('velocity_sigma_m_s',.1))
    if not all(math.isfinite(v) and v>=0 for v in (sp,sv)):sp,sv=100.,10.
    available=bool(b.get('valid',False)) and float(b.get('age_s',math.inf))<3.
    available=available and all(np.asarray(b.get(k,[]),dtype=float).shape==(3,) and np.isfinite(b[k]).all() for k in ('relative_heading_m','velocity_heading_m_s'))
    if not available:
        b.update(valid=False,relative_heading_m=[0.,0.,0.],velocity_heading_m_s=[0.,0.,0.],age_s=3.1);sp,sv=100.,10.
    return observation,available,known,ready,sp,sv

def numeric(observation_json):
    o,available,known,ready,sp,sv=prepare(json.loads(observation_json))
    values=numeric_observation({'observation':o})
    if not known:values[22]=config['unknown_dock_observation_mean']
    values=np.concatenate((values,np.asarray([sp,sv],dtype=np.float32))).astype(np.float32)
    if not np.isfinite(values).all():raise ValueError('Non-finite policy sensor input')
    return values.tolist()

def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean(v) for v in value]
    if isinstance(value,np.generic):value=value.item()
    if isinstance(value,float) and not math.isfinite(value):return None
    return value

def step(rgb,prediction,observation_json,elapsed_s):
    o,available,known,ready,sp,sv=prepare(json.loads(observation_json))
    output=np.asarray(prediction,dtype=np.float32);p=output[:15].copy()
    original_center=p[12:14].copy();original_visibility=1./(1.+np.exp(-p[0]))
    override=policy.metric_time is None or float(o['image_delivery_time_s'])-policy.metric_time>.5
    if override:p[0]=output[15];p[12:14]=output[16:18]
    # Radio influences learned fusion only. No raw packet may steer the
    # acquisition, camera, fit acceptance, velocity or touchdown controller.
    controlled=copy.deepcopy(o)
    controlled['beacon'].update(valid=False,relative_heading_m=[0.,0.,0.],velocity_heading_m_s=[0.,0.,0.],age_s=3.1)
    image=None if rgb is None else np.asarray(rgb,dtype=np.uint8).reshape(360,640,3)
    action,diag=policy.act(image,controlled,p)
    action,intervention=supervise_action(action,controlled,float(elapsed_s),float(config['mission_budget_s']))
    if known and not ready:action[:4]=0.;intervention='dock_not_ready'
    elif not known and not config['allow_visual_landing'] and action[2]>0:action[2]=0.;intervention='visual_landing_authorization_required'
    diag.update(radio_position_fusion_weight=float(output[18]),radio_velocity_fusion_weight=float(output[19]),independent_visual_recurrence=True,direct_radio_controller_bypass_disabled=True,radio_position_available=available,radio_controller_trusted=False,radio_position_sigma_m=sp,radio_velocity_sigma_m_s=sv,radio_fallback='learned_vision_first_fusion' if available else 'visual',intervention=intervention,center_only_override=override,original_center_px=((original_center+1)*[320.,180.]).tolist(),image_only_center_px=((output[16:18]+1)*[320.,180.]).tolist(),original_model_visibility=float(original_visibility),image_head_visibility=float(1./(1.+np.exp(-output[15]))))
    return json.dumps(clean({'action':action,'diagnostics':diag,'intervention':intervention}),allow_nan=False)
''')
    return {name:digest(dest/name) for name in ['__init__.py','recording.py','runtime_fixes.py','browser_api.py',*names]}

def main():
    torch.set_num_threads(1);prefix=package();config=json.loads((BUNDLE/'policy.json').read_text())
    assert digest(BUNDLE/'pose.pt')==config['checkpoint_sha256']
    for name,expected in config['file_hashes'].items():
        if '__pycache__' not in name:assert digest(BUNDLE/name)==expected,name
    saved=torch.load(BUNDLE/'pose.pt',map_location='cpu',weights_only=False)
    original=importlib.import_module(prefix+'.model').RadioRobustPoseModel();original.load_state_dict(saved['model'],strict=True);original.eval()
    spatial_module=importlib.import_module(prefix+'.spatial_acquisition');spatial=spatial_module.SpatialAcquisition();spatial.load_state_dict(torch.load(BUNDLE/'spatial_acquisition.pt',map_location='cpu',weights_only=False)['model']);spatial.eval()
    # Native hooks collect the same two intermediate tensors in a single pass.
    maps={}
    handles=[original.backbone.encoder[i].register_forward_hook(lambda module,args,value,key=key:maps.__setitem__(key,value)) for i,key in [(3,'fine'),(8,'context')]]
    exported=BrowserModel(copy.deepcopy(original),copy.deepcopy(spatial)).eval()
    for layer in exported.model.backbone.encoder.modules():layer._forward_hooks.clear()
    parallel_means(exported)
    example=(torch.zeros(1,1,3,360,640),torch.zeros(1,1,34),torch.zeros(1,1,128))
    torch.onnx.export(exported,example,str(OUT/'pose.onnx'),input_names=['image','numeric','hidden'],output_names=['prediction','next_hidden'],opset_version=17,dynamo=False)
    options=ort.SessionOptions();options.intra_op_num_threads=1
    session=ort.InferenceSession(str(OUT/'pose.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    config.update(algorithm_version='vision_first_fusion_v1',browser_schema='tidewater.vision_first_policy.browser.v2',unknown_dock_observation_mean=float(original.backbone.observation_mean[22]),mission_budget_s=180.,allow_visual_landing=True)
    adapters=export_controller(config,float(original.backbone.observation_mean[22]))
    manifest={**config,'model':'pose.onnx','model_sha256':digest(OUT/'pose.onnx'),'bundle_sha256':digest(BUNDLE/'policy.json'),'spatial_acquisition_sha256':digest(BUNDLE/'spatial_acquisition.pt'),'input_contract':{'image':[1,1,3,360,640],'numeric':[1,1,34],'hidden':[1,1,128],'prediction':[1,1,20],'numeric_fields':'original 32 sensors plus reported position/velocity uncertainty','prediction_fields':'fused pose[15], spatial presence logit[1], normalized spatial center[2], fusion weights[2]','image_dtype':'float32','image_value_range':[0,255]},'reference_adapter_sha256':adapters,'runtime':{'onnxruntime_web':'1.30.0','pyodide':'314.0.7'},'marker_kernel':'marker_kernel.wasm','marker_kernel_sha256':digest(OUT/'marker_kernel.wasm'),'marker_kernel_source_sha256':digest(ROOT/'tidewater-game/wasm/marker_kernel.cpp'),'marker_solver_source_sha256':digest(ROOT/'tidewater-game/wasm/marker_trf.h'),'mission_integration':{'fallback':'manual hold on mission deadline; no authorized static home in this boat-launch game','boat_control':'independent; 2.8m/s normal cruise exceeds policy 2m/s horizontal command bound','qualification':'native candidate had four targeted successful flights; browser port is not flight-qualified'}}
    # Read-only real camera fixtures and native golden predictions/commands.
    frames=json.loads((GOLD/'neural.json').read_text());recording=importlib.import_module(prefix+'.controller.recording')
    onnx_hidden=np.zeros((1,1,128),dtype=np.float32);reference_hidden=torch.zeros((1,1,128));errors=[]
    FIXTURES.mkdir(exist_ok=True)
    for i,frame in enumerate(frames):
        observation=frame['observation'];b=observation['beacon'];values=recording.numeric_observation({'observation':observation})
        if not b.get('dock_status_valid',b.get('valid',False)):values[22]=manifest['unknown_dock_observation_mean']
        values=np.concatenate((values,np.asarray([b.get('position_sigma_m',1.),b.get('velocity_sigma_m_s',.1)],dtype=np.float32))).astype(np.float32).reshape(1,1,34)
        planar=np.fromfile(GOLD/f'image-{i}.bin',dtype=np.uint8).reshape(1,1,3,360,640).astype(np.float32)
        with torch.inference_mode():
            p,_,reference_hidden=original(torch.from_numpy(planar),torch.from_numpy(values[...,:32]),reference_hidden,torch.from_numpy(values[...,32:]))
            presence,pixel=spatial_module.decode_spatial(spatial(maps['fine'],maps['context']))
            expected=torch.cat((p,presence.reshape(1,1,1),(pixel/pixel.new_tensor([320.,180.])-1.).reshape(1,1,2),original.last_fusion_weights),-1).numpy()
        assert np.max(abs(expected.flatten()-np.asarray(frame['prediction'])))<1e-4,'Native golden prediction mismatch'
        actual,onnx_hidden=session.run(None,{'image':planar,'numeric':values,'hidden':onnx_hidden})
        error=float(np.max(abs(expected-actual)));hidden_error=float(np.max(abs(reference_hidden.numpy()-onnx_hidden)))
        assert error<1e-4 and hidden_error<1e-4,(i,error,hidden_error)
        errors.append(dict(frame=i,prediction=error,hidden=hidden_error));frame['numeric']=values.flatten().tolist()
        for kind in ['rgb','image']:shutil.copyfile(GOLD/f'{kind}-{i}.bin',FIXTURES/f'{kind}-{i}.bin')
    manifest['export_parity']=errors
    (FIXTURES/'neural.json').write_text(json.dumps(frames))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(checkpoint=manifest['checkpoint_sha256'],onnx_bytes=(OUT/'pose.onnx').stat().st_size,parity=errors)))

if __name__=='__main__':main()
