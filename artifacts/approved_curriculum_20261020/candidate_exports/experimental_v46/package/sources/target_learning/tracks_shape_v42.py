"""Visual candidate identities and finite history using own motion compensation."""
from dataclasses import dataclass,field
import math
import numpy as np
from scipy.optimize import linear_sum_assignment
from .protocol import Candidate


@dataclass
class Track:
    index:int
    measured_s:float
    frame_token:int
    camera_world:np.ndarray
    ray_world:np.ndarray
    point_world:object
    range_interval:object
    detection:dict
    confirmations:int
    identity_run:int
    last_identity:int
    identity_votes:list=field(default_factory=list)


class TrackBank:
    """No dynamic world truth. Plane intersection is explicitly an estimate.

    Tracks do not make old measurements fresh. Target identity confirmation is
    reset by contradictory/unknown evidence; an episode planner can retain a
    previously established target for bounded local recovery separately.
    """
    def __init__(self,*,target_threshold,wrong_threshold=.02,minimum_identity_long_px=24,
                 max_age_s=45.,association_angle_rad=.18,support_threshold=0.,presence_threshold=.3):
        self.target_threshold=target_threshold;self.wrong_threshold=wrong_threshold
        self.minimum_identity_long_px=minimum_identity_long_px
        self.max_age_s=max_age_s;self.association_angle_rad=association_angle_rad
        self.support_threshold=support_threshold;self.presence_threshold=presence_threshold
        self.tracks={};self.next_id=1;self.last_capture=None;self.objectness_confirmed=set()

    def _identity(self,d):
        supported=(max(d['size_px'])>=self.minimum_identity_long_px
                   and d.get('identity_support_probability',1.)>=self.support_threshold)
        p=d['target_probability']
        if supported and p>=self.target_threshold:return 1
        wrong=d.get('wrong_object_probability',1-p)
        if supported and wrong>=1-self.wrong_threshold:return 0
        return -1

    def observe(self,detections,*,capture_s,frame_token,camera_world,camera_to_world,
                focal_px,plane_height_enu_m,plane_uncertainty_m):
        if self.last_capture is not None and capture_s<self.last_capture:
            raise ValueError('Out-of-order image; explicit history handling required')
        if self.last_capture==capture_s:return
        if not 0<plane_uncertainty_m or not math.isfinite(plane_uncertainty_m):
            raise ValueError('Plane estimate must declare nonzero uncertainty')
        self.last_capture=capture_s;camera_world=np.asarray(camera_world,dtype=float)
        self.tracks={k:v for k,v in self.tracks.items()if capture_s-v.measured_s<=self.max_age_s}
        new=[]
        for d in detections:
            if not d['boat'] or d['presence']<self.presence_threshold:continue
            use_pad=self._identity(d)==1 and d.get('pad_visibility_probability',0)>=.8
            x,y=d['pad_pixel']if use_pad else d['pixel']
            d=dict(d,bearing_pixel_source='learned_pad_point'if use_pad else'learned_boat_box_center')
            ray=np.asarray(camera_to_world)@np.array([(x-320)/focal_px,-(y-180)/focal_px,-1.])
            ray/=np.linalg.norm(ray)
            if ray[2]>=-.02:continue  # don't chase sky/horizon peaks
            distances=[(z-camera_world[2])/ray[2]for z in [plane_height_enu_m-plane_uncertainty_m,plane_height_enu_m+plane_uncertainty_m]]
            distances=sorted(distances);point=None;interval=None
            if distances[0]>0 and distances[1]<150.:
                # Horizontal range interval under a nominal boat-height prior.
                interval=tuple(float(v*np.linalg.norm(ray[:2]))for v in distances)
                point=camera_world+ray*float(np.mean(distances))
            new.append((d,ray,point,interval))
        old=list(self.tracks.values());cost=np.full((len(old),len(new)),1e6)
        for i,t in enumerate(old):
            predicted=t.ray_world if t.point_world is None else t.point_world-camera_world
            predicted=predicted/np.linalg.norm(predicted)
            for j,(_,ray,_,_)in enumerate(new):
                angle=math.acos(float(np.clip(np.dot(predicted,ray),-1,1)))
                if angle<=self.association_angle_rad:cost[i,j]=angle
        matches={}
        if len(old)and len(new):
            oi,nj=linear_sum_assignment(cost)
            matches={int(j):old[int(i)]for i,j in zip(oi,nj)if cost[i,j]<1e5}
        for j,(d,ray,point,interval)in enumerate(new):
            identity=self._identity(d);t=matches.get(j)
            if t is None:
                t=Track(self.next_id,capture_s,frame_token,camera_world.copy(),ray,point,interval,d.copy(),1,
                        1 if identity>=0 else 0,identity,[(capture_s,identity)]if identity>=0 else[])
                self.next_id+=1;self.tracks[t.index]=t
            else:
                consecutive=capture_s-t.measured_s<=.3
                t.confirmations=t.confirmations+1 if consecutive else 1
                # Uncertain classification is absence of positive identity
                # evidence, not a contradictory boat identity. Keep distinct
                # strong observations for a bounded0.8s evidence window.
                if not consecutive:t.identity_votes=[]
                t.identity_votes=[(stamp,value)for stamp,value in t.identity_votes if capture_s-stamp<=.8]
                if identity>=0:
                    if any(value!=identity for stamp,value in t.identity_votes):t.identity_votes=[]
                    t.identity_votes.append((capture_s,identity))
                t.identity_run=sum(value==identity for stamp,value in t.identity_votes)if identity>=0 else 0
                t.last_identity=identity;t.measured_s=capture_s;t.frame_token=frame_token
                t.camera_world=camera_world.copy();t.ray_world=ray;t.point_world=point;t.range_interval=interval;t.detection=d.copy()

    def candidates(self,now_s,own_camera_world):
        output=[];own=np.asarray(own_camera_world)
        self.objectness_confirmed.intersection_update(self.tracks)
        for t in self.tracks.values():
            if t.confirmations>=3:self.objectness_confirmed.add(t.index)
            if t.index not in self.objectness_confirmed:continue
            age=now_s-t.measured_s
            if age<0 or age>self.max_age_s:continue
            vector=t.ray_world if t.point_world is None else t.point_world-own
            if np.linalg.norm(vector[:2])<1e-6:continue
            identity=self._identity(t.detection)
            p=float(t.detection['target_probability'])
            output.append(Candidate(t.index,math.atan2(vector[1],vector[0]),float(t.detection['presence']),
                p,float(t.detection.get('wrong_object_probability',1-p)),identity>=0,t.identity_run,age,t.range_interval,
                float(t.detection.get('marker_probability',t.detection.get('pad_visibility_probability',0.)))))
        return output

    def diagnostics(self):
        return [dict(track_id=t.index,capture_s=t.measured_s,confirmations=t.confirmations,
                     objectness_confirmed=t.index in self.objectness_confirmed,identity_confirmations=t.identity_run,identity_evidence_window_s=.8,identity_evidence_capture_s=[stamp for stamp,value in t.identity_votes],range_interval_m=t.range_interval,
                     range_source='RGB bearing intersected with declared uncertain nominal boat-height plane',
                     measurement_age_is_not_reset_by_own_motion=True,**t.detection)for t in self.tracks.values()]
