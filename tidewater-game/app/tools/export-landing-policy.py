"""Export the verified frozen v5 checkpoint and its numerical controller for browser use."""
import ast, copy, hashlib, importlib, json, shutil, sys, types
from pathlib import Path
import numpy as np
import torch
import onnxruntime as ort
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'artifacts/marker_iteration_20261011/local_bundle_v5/policy_bundle_v5'
OUT=ROOT/'tidewater-game/app/public/policy'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def reference_package():
    package=types.ModuleType('frozen_landing');package.__path__=[str(BUNDLE/'code')];sys.modules['frozen_landing']=package
    return importlib.import_module('frozen_landing.marker_policy')

def allow_visual_radio_dropout(tree, kind):
    """Browser integration: absent radio is zero input, not an action inhibit.

    Preserve the trained bundle, visual confidence/registration checks, command
    bounds and non-radio safety guards. Connected-radio behavior is unchanged.
    """
    class Dropout(ast.NodeTransformer):
        def visit_Call(self, node):
            text=ast.unparse(node)
            if text=="b.get('dock_ready', False)":
                return ast.parse("(not b.get('valid', False) or b.get('dock_ready', False))",mode='eval').body
            return self.generic_visit(node)
        def visit_Assign(self, node):
            if kind=='marker' and any(isinstance(t,ast.Name) and t.id=='trusted' for t in node.targets):
                class OptionalFresh(ast.NodeTransformer):
                    def visit_Name(self, name):
                        return ast.parse("(fresh or not observation['beacon'].get('valid', False))",mode='eval').body if name.id=='fresh' else name
                node.value=OptionalFresh().visit(node.value)
            return self.generic_visit(node)
        def visit_If(self, node):
            text=ast.unparse(node.test)
            if kind=='supervision' and text=="not observation['beacon'].get('dock_ready', False) and (not state.get('landed', False))":
                node.test=ast.BoolOp(op=ast.And(),values=[ast.parse("observation['beacon'].get('valid', False)",mode='eval').body,node.test])
            if kind=='marker' and 'now - self.contact_started <= 8.0 and fresh' in text:
                class OptionalContactFresh(ast.NodeTransformer):
                    def visit_Name(self, name):
                        return ast.parse("(fresh or not observation['beacon'].get('valid', False))",mode='eval').body if name.id=='fresh' else name
                node.test=OptionalContactFresh().visit(node.test)
            if kind=='marker' and text=='fresh' and node.body and ast.unparse(node.body[0]).startswith('boat ='):
                assert not node.orelse
                node.orelse=ast.parse("self.boat_velocity_enu=self.visual_velocity_enu if self.visual_boat_sample is not None and now-self.visual_boat_sample[0]<.5 else None").body
            return self.generic_visit(node)
        def visit_FunctionDef(self, node):
            if kind=='marker' and node.name in ('__init__','reset'):
                node.body+=ast.parse('self.visual_boat_sample=None\nself.visual_velocity_enu=None').body
            if kind=='marker' and node.name=='accept_metric':
                cold=next(n for n in node.body if isinstance(n,ast.If) and ast.unparse(n.test)=='cold or reacquiring')
                assert ast.unparse(cold.body[0])=="beacon = observation['beacon']"
                cold.body[1:1]=ast.parse("if not beacon.get('valid', False):\n return (True, 'reacquired' if reacquiring else 'acquired')").body
            if kind=='marker' and node.name=='act' and any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pose_at_capture' for t in n.targets) for n in node.body):
                for i,n in enumerate(node.body):
                    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fit' for t in n.targets):
                        node.body[i:i]=ast.parse("pose_at_capture['_image_pixel']=(p[12:14]+1)*[320.,180.]").body
                        break
                for i,n in enumerate(node.body):
                    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='metric_age' for t in n.targets):
                        node.body[i:i]=ast.parse('current=visual_motion(self,current,observation,now,fit)').body
                        break
                for i,n in enumerate(node.body):
                    if isinstance(n,ast.If) and ast.unparse(n.test).startswith('not trusted and self.track is not None'):
                        node.body[i]=ast.If(test=ast.parse("not observation['beacon'].get('valid',False) and not trusted and self.controller.contact_started is None and observation['px4'].get('armed',False) and not observation['px4'].get('landed',False)",mode='eval').body,
                          body=ast.parse("action,diag=acquire_visual(self.controller,dict(current,visibility=probability),observation,p)").body,orelse=[n])
                        break
            return self.generic_visit(node)
    return ast.fix_missing_locations(Dropout().visit(tree))

def export_controller(configuration):
    destination=OUT/'reference';destination.mkdir(parents=True,exist_ok=True)
    (destination/'__init__.py').write_text('')
    for name in ['action_guard.py','camera_geometry.py','marker_geometry.py','supervision.py']:
        shutil.copyfile(BUNDLE/'code'/name,destination/name)
    supervision=allow_visual_radio_dropout(ast.parse((destination/'supervision.py').read_text()),'supervision')
    (destination/'supervision.py').write_text(ast.unparse(supervision)+'\n')
    shutil.copyfile(Path(__file__).with_name('camera_geometry_fast.py'),destination/'camera_geometry_fast.py')
    with (destination/'camera_geometry.py').open('a') as stream:
        stream.write('''\n# Static calibrated transforms and exact encoder prefixes are bounded caches.
camera_body_transform_reference=camera_body_transform
from .camera_geometry_fast import camera_body_transform_fast
camera_body_transform=camera_body_transform_fast
''')
    shutil.copyfile(Path(__file__).with_name('marker_geometry_fast.py'),destination/'marker_geometry_fast.py')
    shutil.copyfile(Path(__file__).with_name('visual_acquisition.py'),destination/'visual_acquisition.py')
    with (destination/'marker_geometry.py').open('a') as stream:
        stream.write('''\n# Keep the frozen implementation callable for numerical parity tests.
marker_pose_reference=marker_pose
def marker_pose(rgb,observation,calibration,estimate):
    try:
        from js import marker_kernel
    except ImportError:
        if not observation['beacon'].get('valid',False) and not estimate.get('_tracked',False):
            from .visual_acquisition import paint_prior
            seed=paint_prior(rgb,observation,calibration,estimate)
            return None if seed is None else marker_pose_reference(rgb,observation,calibration,seed)
        return marker_pose_reference(rgb,observation,calibration,estimate)
    from .marker_geometry_fast import marker_pose_fast
    if not observation['beacon'].get('valid',False) and not estimate.get('_tracked',False):
        from .visual_acquisition import paint_prior
        seed=paint_prior(rgb,observation,calibration,estimate)
        if seed is None:return None
        return marker_pose_fast(rgb,observation,calibration,seed,marker_kernel)
    return marker_pose_fast(rgb,observation,calibration,estimate,marker_kernel)
''')
    recording=ast.parse((BUNDLE/'code/recording.py').read_text())
    numeric=next(n for n in recording.body if isinstance(n,ast.FunctionDef) and n.name=='numeric_observation')
    (destination/'recording.py').write_text('import math\nimport numpy as np\n'+ast.unparse(numeric)+'\n')
    hybrid=ast.parse((BUNDLE/'code/hybrid_policy.py').read_text())
    hybrid.body=[n for n in hybrid.body if not (isinstance(n,ast.Import) and any(a.name=='torch' for a in n.names)) and not (isinstance(n,ast.ImportFrom) and n.module=='pose_model')]
    base=next(n for n in hybrid.body if isinstance(n,ast.ClassDef) and n.name=='HybridPosePolicy')
    # Neural execution is externalized to ONNX; all numerical controller/tracker
    # methods retain the source action laws/registration; radio dropout gates
    # are adapted explicitly for the browser's zero-input behavior below.
    base.body=[n for n in base.body if not isinstance(n,ast.FunctionDef) or n.name!='act']
    init=next(n for n in base.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    init.body=ast.parse("""
self.calibration=calibration
self.controller=LandingController(calibration['foot_local_flu'],slew_limits)
self.metadata={}
self.history=deque(maxlen=16)
self.height=None
self.last_valid=None
self.last_valid_time=None
self.hidden=None
""").body
    (destination/'hybrid_policy.py').write_text(ast.unparse(allow_visual_radio_dropout(hybrid,'hybrid'))+'\n')
    marker=ast.parse((BUNDLE/'code/marker_policy.py').read_text())
    marker.body[:0]=ast.parse('from .visual_acquisition import acquire_visual, visual_motion').body
    marker.body=[n for n in marker.body if not (isinstance(n,ast.Import) and any(a.name=='torch' for a in n.names))]
    cls=next(n for n in marker.body if isinstance(n,ast.ClassDef) and n.name=='MarkerPosePolicy')
    act=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='act')
    assert len(act.body)>4 and ast.unparse(act.body[4]).startswith('probability =')
    act.decorator_list=[];act.args.args.append(ast.arg(arg='prediction'))
    act.body=ast.parse('p=np.asarray(prediction,dtype=np.float32)').body+act.body[4:]
    (destination/'marker_policy.py').write_text(ast.unparse(allow_visual_radio_dropout(marker,'marker'))+'\n')
    # The vector builder and bounds remain original source contracts.
    expert=ast.parse((ROOT/'landing_training/expert.py').read_text())
    bound=next(n for n in next(n for n in expert.body if isinstance(n,ast.ClassDef) and n.name=='Expert').body if isinstance(n,ast.FunctionDef) and n.name=='bounded')
    bound.args.args=bound.args.args[1:]
    api='''import json, math\nimport numpy as np\nfrom .marker_policy import MarkerPosePolicy\nfrom .recording import numeric_observation\nfrom .supervision import supervise_action\n'''+ast.unparse(bound)+'''
policy=None
def initialize(configuration_json):
    global policy
    c=json.loads(configuration_json)
    policy=MarkerPosePolicy(None,c['calibration'],c['slew_limits'],'browser')
    policy.reset()
def numeric(observation_json):
    return numeric_observation({'observation':json.loads(observation_json)}).tolist()
def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean(v) for v in value]
    if isinstance(value,np.generic):value=value.item()
    if isinstance(value,float) and not math.isfinite(value):return None
    return value
def step(rgb,prediction,observation_json,elapsed_s):
    observation=json.loads(observation_json)
    image=None if rgb is None else np.asarray(rgb,dtype=np.uint8).reshape(360,640,3)
    action,diagnostics=policy.act(image,observation,np.asarray(prediction,dtype=np.float32))
    action=bounded(action)
    action,intervention=supervise_action(action,observation,float(elapsed_s),90.)
    return json.dumps(clean({'action':action,'diagnostics':diagnostics,'intervention':intervention}),allow_nan=False)
'''
    (destination/'browser_api.py').write_text(api)
    return {p.name:digest(p) for p in destination.glob('*.py')}

def main():
    torch.set_num_threads(1);OUT.mkdir(parents=True,exist_ok=True)
    configuration=json.loads((BUNDLE/'policy.json').read_text())
    assert configuration['algorithm_version']=='metric_marker_v5'
    assert digest(BUNDLE/'pose.pt')==configuration['checkpoint_sha256']
    for name,expected in configuration['source_files_sha256'].items():assert digest(BUNDLE/'code'/name)==expected,name
    if '--controller-only' in sys.argv:
        manifest=json.loads((OUT/'manifest.json').read_text())
        assert digest(OUT/manifest['model'])==manifest['model_sha256']
        manifest['reference_adapter_sha256']=export_controller(configuration)
        manifest['marker_kernel_sha256']=digest(OUT/'marker_kernel.wasm')
        manifest['marker_kernel_source_sha256']=digest(ROOT/'tidewater-game/wasm/marker_kernel.cpp')
        manifest['marker_solver_source_sha256']=digest(ROOT/'tidewater-game/wasm/marker_trf.h')
        (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps({'unchanged_model_sha256':manifest['model_sha256'],'controller_files':list(manifest['reference_adapter_sha256'])}))
        return
    saved=torch.load(BUNDLE/'pose.pt',map_location='cpu',weights_only=False)
    assert saved['schema']=='aerodock.landing.pose.v1' and saved['dataset_sha256']==configuration['dataset_sha256']
    reference=reference_package();policy=reference.MarkerPosePolicy(BUNDLE/'pose.pt',configuration['calibration'],configuration['slew_limits'],'cpu')
    class Export(torch.nn.Module):
        def __init__(self,model):super().__init__();self.model=model
        def forward(self,image,numeric,hidden):
            # Same single-step PyTorch GRU equations and FP32 weights. Express
            # the recurrence using GPU-supported primitives rather than a GRU
            # operator which would force an execution-provider fallback.
            b=self.model.backbone;features=b.encode_images(image)
            mask=numeric.new_tensor([0. if i in (5,9,10,24,25,26,27,28,29) else 1. for i in range(32)])
            angles=torch.cat((numeric[...,5:6],numeric[...,9:11]),dim=-1)
            trig=torch.stack((torch.sin(angles),torch.cos(angles)),dim=-1).reshape(1,1,6)
            periodic=numeric*mask+torch.cat((torch.zeros_like(numeric[...,:24]),trig,torch.zeros_like(numeric[...,30:])),dim=-1)
            visual=b.visual(features);state=b.telemetry((periodic-b.observation_mean)/b.observation_std)
            gi=torch.nn.functional.linear(torch.cat((visual,state),dim=-1),b.gru.weight_ih_l0,b.gru.bias_ih_l0)
            gh=torch.nn.functional.linear(hidden,b.gru.weight_hh_l0,b.gru.bias_hh_l0)
            reset=torch.sigmoid(gi[...,:128]+gh[...,:128]);update=torch.sigmoid(gi[...,128:256]+gh[...,128:256])
            candidate=torch.tanh(gi[...,256:]+reset*gh[...,256:]);next_hidden=(1-update)*candidate+update*hidden
            raw=b.auxiliary(next_hidden)
            position=numeric[...,11:14]+raw[...,1:4].clamp(-5.,5.)
            velocity=numeric[...,14:17]-numeric[...,:3]+raw[...,4:7].clamp(-1.,1.)
            # Retain the singleton axis so boolean Unsqueeze cannot force a
            # CPU fallback. This is the original decode_pose algebra.
            vx,vy=numeric[...,14:15],numeric[...,15:16];speed_squared=vx*vx+vy*vy
            course=torch.cat((-2*vx*vy,vx*vx-vy*vy),dim=-1)/speed_squared.clamp_min(1e-6)
            prior=torch.where(speed_squared>.15**2,course,torch.zeros_like(course))
            heading=torch.nn.functional.normalize(raw[...,7:9]+prior,dim=-1,eps=1e-6)
            normal=torch.nn.functional.normalize(raw[...,9:12]+raw.new_tensor([0.,0.,-1.]),dim=-1,eps=1e-6)
            prediction=torch.cat((raw[...,:1],position,velocity,heading,normal,raw[...,12:15]),dim=-1)
            return prediction,next_hidden
    # The generic GlobalAveragePool GPU kernel sums a full spatial plane in
    # one invocation per channel. Flattening the plane expresses the same FP32
    # mean as a parallel GPU reduction, retaining every sample and every weight.
    class SpatialMean(torch.nn.Module):
        def forward(self,value):
            n,c,h,w=value.shape
            return value.reshape(n,c,h*w).mean(-1).reshape(n,c,1,1)
    def parallel_means(module):
        for name,child in list(module.named_children()):
            if isinstance(child,torch.nn.AdaptiveAvgPool2d) and child.output_size in (1,(1,1)):
                setattr(module,name,SpatialMean())
            else:parallel_means(child)
    exported_model=copy.deepcopy(policy.model);parallel_means(exported_model)
    model=Export(exported_model).eval()
    image=torch.zeros((1,1,3,360,640),dtype=torch.float32);numeric=torch.zeros((1,1,32));hidden=torch.zeros((1,1,128))
    torch.onnx.export(model,(image,numeric,hidden),str(OUT/'pose.onnx'),input_names=['image','numeric','hidden'],output_names=['prediction','next_hidden'],opset_version=17,dynamo=False)
    options=ort.SessionOptions();options.intra_op_num_threads=1
    session=ort.InferenceSession(str(OUT/'pose.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    rng=np.random.default_rng(8101);errors=[];fixtures=[];onnx_hidden=np.zeros((1,1,128),dtype=np.float32);torch_hidden=torch.zeros((1,1,128))
    fixture_root=ROOT/'tidewater-game/simulation/runtime/ml-fixtures';fixture_root.mkdir(parents=True,exist_ok=True)
    for i in range(8):
        rgb=rng.integers(0,256,(360,640,3),dtype=np.uint8) if i<4 else np.asarray(Image.open(ROOT/'tidewater-game/history/tidewater_20261011/moving_daylight_rgb_0100.png').convert('RGB'))
        assert rgb.shape==(360,640,3),rgb.shape
        observation={'px4':{'valid':True,'position_age_s':.008,'attitude_age_s':.004,'armed':True,'landed':False,'velocity_enu_m_s':[.1,.2,.01],'attitude_ned_rad':[.01,-.02,1.57],'angular_rate_frd_rad_s':[0.,.01,0.]},'beacon':{'valid':True,'age_s':i*.04,'relative_heading_m':[.15,.05,2.4],'velocity_heading_m_s':[.8,0.,0.],'dock_ready':True},'gimbal_rad':[0.,1.4],'image_capture_time_s':i*.04,'image_delivery_time_s':i*.04,'image_age_s':0.,'image_valid':True,'decision_dt_s':.04,'previous_executed_action':[0.]*6}
        inputs=np.asarray(importlib.import_module('frozen_landing.recording').numeric_observation({'observation':observation}))[None,None]
        planar=np.transpose(rgb,(2,0,1))[None,None].copy()
        with torch.inference_mode():expected,_,torch_hidden=policy.model(torch.from_numpy(planar),torch.from_numpy(inputs),torch_hidden)
        actual,onnx_hidden=session.run(None,{'image':planar.astype(np.float32),'numeric':inputs,'hidden':onnx_hidden})
        error=float(np.max(abs(expected.numpy()-actual)));hidden_error=float(np.max(abs(torch_hidden.numpy()-onnx_hidden)))
        assert error<1e-4 and hidden_error<1e-4,(error,hidden_error);errors.append({'prediction':error,'hidden':hidden_error})
        rgb.tofile(fixture_root/f'rgb-{i}.bin');planar.tofile(fixture_root/f'image-{i}.bin')
        reference_action,reference_diagnostics=policy.act(rgb,observation)
        fixtures.append({'observation':observation,'numeric':inputs.ravel().tolist(),'prediction':expected.numpy().ravel().tolist(),'next_hidden':torch_hidden.numpy().ravel().tolist(),'reference_action':reference_action.tolist(),'reference_phase':reference_diagnostics['control_phase'],'metric_valid':reference_diagnostics.get('metric_valid')})
    transformed=export_controller(configuration)
    manifest={**configuration,'browser_schema':'tidewater.marker_policy.browser.v1','model':'pose.onnx','model_sha256':digest(OUT/'pose.onnx'),'bundle_sha256':digest(BUNDLE/'policy.json'),'input_contract':{'image':[1,1,3,360,640],'numeric':[1,1,32],'hidden':[1,1,128],'image_dtype':'float32','image_value_range':[0,255],'prediction':[1,1,15]},'reference_adapter_sha256':transformed,'export_parity':errors,'runtime':{'onnxruntime_web':'1.30.0','pyodide':'314.0.7'},'boat_speed_m_s':.8}
    manifest.update(marker_kernel='marker_kernel.wasm',marker_kernel_sha256=digest(OUT/'marker_kernel.wasm'),marker_kernel_source_sha256=digest(ROOT/'tidewater-game/wasm/marker_kernel.cpp'))
    manifest['marker_solver_source_sha256']=digest(ROOT/'tidewater-game/wasm/marker_trf.h')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (fixture_root/'neural.json').write_text(json.dumps(fixtures))
    print(json.dumps({'verified_checkpoint':manifest['checkpoint_sha256'],'onnx_bytes':(OUT/'pose.onnx').stat().st_size,'max_export_error':max(v['prediction'] for v in errors),'controller_files':list(transformed)}))

if __name__=='__main__':main()
