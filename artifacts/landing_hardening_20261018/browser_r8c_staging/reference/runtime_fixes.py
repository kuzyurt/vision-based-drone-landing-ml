"""Observable approach/search improvements; final touchdown gates are retained."""
import importlib
import inspect
import math
import textwrap
import numpy as np

def install(package='landing_training.radio_robust_20261015'):
    policy=importlib.import_module(package+'.marker_policy')
    visual=importlib.import_module(package+'.visual_acquisition')
    guard=importlib.import_module(package+'.action_guard')
    cls=policy.MarkerLandingController
    if getattr(cls,'_domain_fixes_installed',False):return
    original=cls._tracked_act;source=textwrap.dedent(inspect.getsource(original))
    old='heading_error = wrap(self.heading_target - yaw)'
    assert old in source
    source=source.replace(old,old+"\n    window=estimate.get('visual_motion_window_s',getattr(self,'last_visual_motion_window_s',0.))\n    self.last_visual_motion_window_s=window\n    heading_trusted=fresh or window>=1.0\n    if not heading_trusted:\n        heading_error=0.\n        self.heading_target=yaw")
    source=source.replace("ready = estimate.get('motion_ready', True) and", "ready = heading_trusted and estimate.get('motion_ready', True) and")
    old='elif clearance < 1.2:'
    assert old in source
    source=source.replace(old,"elif clearance > 2.5 and heading_trusted and estimate.get('motion_ready',False) and lateral + estimate.get('metric_uncertainty_m',0.) < .4 and speed < .6 and abs(heading_error)<math.radians(20) and deck_tilt<math.radians(8) and estimate.get('metric_age_s',99)<.2:\n        phase='visual_approach'\n        action[2]=boat_velocity[2]+.22\n    "+old)
    namespace=dict(original.__globals__);exec(compile(source,__file__,'exec'),namespace);cls._tracked_act=namespace['_tracked_act']
    reset=cls.reset
    def reset_state(self):
        reset(self);self.last_visual_motion_window_s=0.;self.last_visual_bearing=None;self.observable_acquisition_state=None
    cls.reset=reset_state

    def acquire(controller,estimate,observation,prediction):
        controller.current_estimate=estimate;controller.stable_elapsed=0.;controller.relative=None
        action=np.zeros(6);now=float(observation['image_delivery_time_s'])
        pixel=(np.asarray(prediction[12:14])+1.)*[320.,180.]
        visible=(observation['image_valid'] and observation['image_age_s']<=.25 and estimate['visibility']>=.8
                 and np.isfinite(pixel).all() and 8<pixel[0]<632 and 8<pixel[1]<352)
        yaw=math.pi/2-observation['px4']['attitude_ned_rad'][2]
        c,s=math.cos(yaw),math.sin(yaw);R=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
        D=np.diag([1.,-1.,-1.]);rotation,_,focal,level=visual.camera_geometry(observation,controller.calibration)
        ray=None;history=False
        if visible:
            ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.]);ray/=np.linalg.norm(ray)
            controller.last_visual_bearing=(now,R@D@ray)
        else:
            previous=getattr(controller,'last_visual_bearing',None)
            if previous is not None and now-previous[0]<.6 and observation['image_valid']:
                ray=D@R.T@previous[1];history=True
        if ray is not None:
            controller.visual_search_started=None
            if ray[2]>.05:action[:2]=2.*ray[:2]
            body=level.T@ray;pan=math.atan2(-body[1],body[0]);tilt=math.atan2(body[2],np.linalg.norm(body[:2]))
            action[4]=3*guard.wrap(pan-observation['gimbal_rad'][0]);action[5]=3*(tilt-observation['gimbal_rad'][1])
        else:
            if getattr(controller,'visual_search_started',None) is None:controller.visual_search_started=now
            elapsed=now-controller.visual_search_started;target=math.radians([15.,35.,60.][int(elapsed/14)%3])
            action[4]=.45;action[5]=.8*(target-observation['gimbal_rad'][1])
        diag=dict(control_phase='visual_reacquire' if history else 'visual_acquire' if visible else 'visual_search',
                  pose_valid=False,pad_visibility_probability=float(estimate['visibility']),range_source='unavailable',
                  visual_bearing_only=True,bearing_history_used=history)
        return controller.finish(action,observation,diag)
    from .observable_acquisition import acquire_visual as observable_acquire
    policy.acquire_visual=observable_acquire;cls._domain_fixes_installed=True
    resolve=policy.MarkerPosePolicy.resolve_marker_heading
    source=textwrap.dedent(inspect.getsource(resolve))
    old="moving = self.boat_velocity_enu is not None and np.linalg.norm(self.boat_velocity_enu[:2]) > 0.1"
    assert old in source
    source=source.replace(old,"samples=getattr(self,'visual_motion_samples',[])\n    motion_confirmed=len(samples)>=20 and samples[-1][0]-samples[0][0]>=1.0\n    "+old+" and motion_confirmed")
    namespace=dict(resolve.__globals__);exec(compile(source,__file__,'exec'),namespace)
    policy.MarkerPosePolicy.resolve_marker_heading=namespace['resolve_marker_heading']
