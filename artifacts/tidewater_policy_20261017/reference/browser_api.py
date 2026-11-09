import json, math
import numpy as np
from .marker_policy import MarkerPosePolicy
from .recording import numeric_observation
from .supervision import supervise_action
def bounded(action):
    a = np.asarray(action, dtype=float).copy()
    length = np.linalg.norm(a[:2])
    if length > 2:
        a[:2] *= 2 / length
    a[2] = np.clip(a[2], -1, 0.7)
    a[3] = np.clip(a[3], -0.5, 0.5)
    a[4] = np.clip(a[4], -math.radians(50), math.radians(50))
    a[5] = np.clip(a[5], -math.radians(40), math.radians(40))
    return a
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
