"""Causal camera/operator disturbances for evaluation; no simulator truth."""
import numpy as np

class CameraFault:
    def __init__(self,setting):
        self.setting=setting;self.start=None;self.trigger_clearance=None;self.active=False
        self.end=None;self.frames=0
    def before(self,rgb,observation):
        now=float(observation['image_delivery_time_s'])
        self.active=self.start is not None and self.start<=now<self.end
        if self.active:
            self.frames+=1
            if self.setting.get('kind')=='central_occluder':
                # Fixed foreground rectangle, not a truth-guided target mask.
                rgb[60:300,100:540]=[22,24,25]
            elif self.setting.get('kind')=='camera_unavailable':
                rgb[:]=0;observation['image_valid']=False
    def after(self,action,diag,observation):
        now=float(observation['image_delivery_time_s'])
        if self.setting and self.start is None and diag.get('metric_confirmed') and diag.get('pose_valid') and diag.get('estimated_clearance_m',99)<float(self.setting.get('trigger_clearance_m',1.2)):
            self.start=now+float(observation['decision_dt_s']);self.end=self.start+float(self.setting.get('duration_s',1.2))
            self.trigger_clearance=float(diag['estimated_clearance_m'])
        if self.active and self.setting.get('kind')=='gimbal_pan':
            action=np.asarray(action,dtype=float).copy();diag['fault_original_action']=action.tolist()
            action[4]=float(self.setting.get('pan_rate_rad_s',.6981317008));action[5]=0.
        diag.update(evaluation_camera_fault=self.setting.get('kind'),evaluation_fault_active=self.active,
                    evaluation_fault_triggered=self.start is not None,evaluation_fault_start_s=self.start,
                    evaluation_fault_frames=self.frames,evaluation_fault_trigger_clearance_m=self.trigger_clearance)
        return action,diag
