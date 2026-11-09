"""Evaluation-only repeatable optical disturbances, triggered by public evidence."""
import numpy as np
class CameraFault:
 def __init__(self,setting):
  self.setting=setting;self.start=None;self.end=None;self.trigger_clearance=None;self.active=False;self.frames=0;self.trigger_history=[]
  self.repeat_count=int(setting.get('repeat_count',1));assert 1<=self.repeat_count<=3
 def before(self,rgb,observation):
  now=float(observation['image_delivery_time_s']);self.active=self.start is not None and self.start<=now<self.end
  if self.active:
   self.frames+=1
   if self.setting.get('kind')=='central_occluder':rgb[60:300,100:540]=[22,24,25]
   elif self.setting.get('kind')=='camera_unavailable':rgb[:]=0;observation['image_valid']=False
 def after(self,action,diag,observation):
  now=float(observation['image_delivery_time_s'])
  can_repeat=self.start is None or (len(self.trigger_history)<self.repeat_count and now>=self.end+float(self.setting.get('minimum_gap_s',.6)))
  if self.setting and can_repeat and diag.get('metric_confirmed') and diag.get('pose_valid') and diag.get('estimated_clearance_m',99)<float(self.setting.get('trigger_clearance_m',1.2)):
   self.start=now+float(observation['decision_dt_s']);self.end=self.start+float(self.setting.get('duration_s',1.2));self.trigger_clearance=float(diag['estimated_clearance_m'])
   self.trigger_history.append(dict(start_s=self.start,end_s=self.end,public_estimated_clearance_m=self.trigger_clearance))
  if self.active and self.setting.get('kind')=='gimbal_pan':
   action=np.asarray(action,dtype=float).copy();diag['fault_original_action']=action.tolist();action[4]=float(self.setting.get('pan_rate_rad_s',.6981317008));action[5]=0.
  diag.update(evaluation_camera_fault=self.setting.get('kind'),evaluation_fault_active=self.active,evaluation_fault_triggered=self.start is not None,evaluation_fault_start_s=self.start,evaluation_fault_frames=self.frames,evaluation_fault_trigger_clearance_m=self.trigger_clearance,evaluation_fault_trigger_count=len(self.trigger_history))
  return action,diag
