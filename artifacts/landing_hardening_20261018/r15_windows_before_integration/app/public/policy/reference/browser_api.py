"""Faithful native RadioRobustRuntime boundary; neural FP32 executes on GPU."""
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
