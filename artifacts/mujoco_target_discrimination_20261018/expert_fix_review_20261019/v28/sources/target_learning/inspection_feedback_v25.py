"""Bounded negative visual evidence for stale hypotheses; never identity truth."""
from dataclasses import dataclass
import math
import numpy as np

@dataclass
class EvidenceWindow:
    first_s:float
    last_capture:int
    count:int
    own_xy:np.ndarray

class InspectionFeedback:
    def __init__(self):
        self.windows={};self.last_forward=None;self.last_time=None
        self.complete_scan_s=None;self.complete_scan_xy=None;self.events=[]

    def observe(self,protocol,state,candidates,*,point_world,camera_world,camera_to_world,focal_px,
                own_xy,fresh_detections,own_angular_speed_rad_s):
        """Consume only camera-derived estimates and own measured geometry."""
        own_xy=np.asarray(own_xy,float);C=np.asarray(camera_to_world,float);origin=np.asarray(camera_world,float)
        forward=C@np.array([0.,0.,-1.]);dt=None if self.last_time is None else state.time_s-self.last_time
        camera_rate=math.inf
        if self.last_forward is not None and dt is not None and dt>0:
            camera_rate=math.acos(float(np.clip(np.dot(forward,self.last_forward),-1.,1.)))/dt
        self.last_forward=forward;self.last_time=state.time_s
        if protocol.scan_coverage>=2*math.pi-.08 and self.complete_scan_s is None:
            self.complete_scan_s=state.time_s;self.complete_scan_xy=own_xy.copy()
        if protocol.scan_coverage<2*math.pi-.08:
            self.complete_scan_s=None;self.complete_scan_xy=None
        selected=protocol.selected
        candidate=next((c for c in candidates if c.track_id==selected),None)
        info=dict(retired=False,source='fresh visual absence at own calibrated remembered bearing',identity_label_changed=False)
        if (protocol.phase!='reorient_candidate'or selected is None or candidate is None or candidate.age_s<=.25
            or point_world is None or not state.image_fresh or not state.own_state_fresh or not state.airborne
            or state.landed or not state.own_motion_settled or camera_rate>.15 or own_angular_speed_rad_s>.15):
            self.windows.clear();return info
        ray=C.T@(np.asarray(point_world,float)-origin)
        if not np.isfinite(ray).all()or ray[2]>=-.01:
            self.windows.pop(selected,None);return info
        pixel=np.array([320+focal_px*ray[0]/-ray[2],180-focal_px*ray[1]/-ray[2]])
        info['predicted_pixel']=pixel.tolist();info['camera_rate_rad_s']=camera_rate
        if not(160<=pixel[0]<=480 and 90<=pixel[1]<=270):
            self.windows.pop(selected,None);return info
        for detection in fresh_detections:
            center=np.asarray(detection['pixel']);half=np.asarray(detection['size_px'])/2+24.
            if np.all(np.abs(pixel-center)<=half):
                self.windows.pop(selected,None);info['fresh_overlapping_object']=True;return info
        window=self.windows.get(selected)
        if window is None:
            window=EvidenceWindow(state.time_s,state.frame_id,1,own_xy.copy());self.windows={selected:window}
        elif np.linalg.norm(own_xy-window.own_xy)>.5:
            self.windows.clear();return info
        elif state.frame_id!=window.last_capture:
            window.count+=1;window.last_capture=state.frame_id
        info.update(distinct_negative_captures=window.count,negative_view_s=state.time_s-window.first_s)
        if window.count<10 or state.time_s-window.first_s<1.:return info
        retain=bool(self.complete_scan_s is not None and state.time_s-self.complete_scan_s<=25.
            and np.linalg.norm(own_xy-self.complete_scan_xy)<=.5)
        protocol.rejected[selected]=state.time_s
        protocol.cooldown_reasons[selected]='remembered_ray_unresolved_after_fresh_centered_inspection'
        protocol.selected=None;protocol.inspection_id=None
        if not retain:
            protocol.scan_seen.clear();protocol.scan_coverage=0.;protocol.scan_yaw=None
        self.windows.clear();info.update(retired=True,track_id=selected,completed_scan_retained=retain)
        self.events.append(dict(time_s=state.time_s,**info));return info
