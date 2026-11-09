"""Sensor-only multi-boat search and identity-gated handoff to frozen R15."""
from __future__ import annotations
from dataclasses import dataclass
import json
import math
from pathlib import Path
import numpy as np
import torch
from common import (R15, check_no_radio, config, configure_simulation_imports,
                    r15_module, sha)
from model import SearchHead, encode_maps, decode


@dataclass
class EvidenceView:
    key: str
    evidence: str
    range_m: float
    pixel: tuple
    position: np.ndarray | None
    detectable: bool = True


class SearchRuntime:
    def __init__(self, bundle, device='cpu'):
        bundle=Path(bundle)
        manifest=json.loads((bundle/'policy.json').read_text())
        if sha(bundle/manifest['checkpoint'])!=manifest['checkpoint_sha256']:
            raise ValueError('Search checkpoint checksum mismatch')
        saved=torch.load(bundle/manifest['checkpoint'],map_location='cpu',weights_only=False)
        self.c=config()
        if saved['schema']!='drone.search.transfer_head.v1':raise ValueError('Unknown search checkpoint')
        for which in ('pose','spatial'):
            if saved[which+'_sha256']!=self.c[which+'_sha256']:raise ValueError('Wrong base lineage')
        configure_simulation_imports()
        from windows_kernels import install
        install()
        cls=r15_module('radio_robust_20261015.runtime').RadioRobustRuntime
        calibration=json.loads((R15/'policy.json').read_text())
        if sha(bundle/'base/pose.pt')!=self.c['pose_sha256'] or sha(bundle/'base/spatial_acquisition.pt')!=self.c['spatial_sha256']:
            raise ValueError('Base weights changed')
        self.base=cls(bundle/'base/pose.pt',calibration['calibration'],calibration['slew_limits'],device,allow_visual_landing=True)
        self.head=SearchHead(initialize=False).to(device)
        self.head.load_state_dict(saved['model'],strict=True);self.head.eval()
        self.calibration=calibration['calibration'];self.device=device
        self.geometry=r15_module('radio_robust_20261015.controller.camera_geometry')
        self.visual=r15_module('radio_robust_20261015.controller.visual_acquisition')
        guard=r15_module('radio_robust_20261015.controller.action_guard')
        self.guard=guard.ActionGuard(guard.GuardConfig(slew_limits=tuple(calibration['slew_limits'])))
        self.supervise=r15_module('radio_robust_20261015.controller.supervision').supervise_action
        self.wrap=guard.wrap
        self.reset()

    def reset(self):
        # Reuse only the teacher's pure evidence-ordering state machine.
        # No oracle, BoatView, env handle, true label or teacher pilot is created.
        from landing_training.privileged_teacher import SearchDecision
        self.search=SearchDecision();self.base.reset();self.guard.reset()
        self.tracks={};self.sequence=0;self.height=None;self.last_point=None;self.last_seen=-100.
        self.selected=None;self.selected_since=0.;self.last_progress=0.;self.best_range=math.inf

    @torch.inference_mode()
    def act(self, rgb, observation):
        check_no_radio(observation)
        own=observation['px4'];t=float(observation['mission']['elapsed_s'])
        if not own.get('valid') or max(own.get('position_age_s',100),own.get('attitude_age_s',100))>.25:
            return np.zeros(6),dict(control_phase='estimator_hold',boat_radio=False)
        if not observation['image_valid'] or observation['image_age_s']>.25:
            return np.zeros(6),dict(control_phase='image_hold',boat_radio=False)
        if self.base.controller.controller.contact_started is not None:
            # Original R15 bounded contact continuation must survive camera occlusion.
            action,diag=self.base.act(rgb,observation)
            diag.update(search_identity_confirmed=True,boat_radio=False)
            return action,diag
        position=np.asarray(own['position_enu_m'],dtype=float)
        yaw=math.pi/2-own['attitude_ned_rad'][2]
        co,si=math.cos(yaw),math.sin(yaw)
        R=np.array([[co,-si,0],[si,co,0],[0,0,1.]])
        D=np.diag([1.,-1.,-1.])
        rotation,_,focal,_=self.visual.camera_geometry(observation,self.calibration)
        image=torch.from_numpy(np.asarray(rgb).copy()).permute(2,0,1)[None].to(self.device)
        fine,context=encode_maps(self.base.model,image)
        proposals=decode(self.head(fine,context))[0]
        views=[];used=set()
        for p in sorted(proposals,key=lambda p:p['pixel'][0]):
            pixel=p['pixel'];ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.])
            ray/=np.linalg.norm(ray);world=R@D@ray
            if ray[2]<=.02:continue
            options=[]
            for key,track in self.tracks.items():
                age=t-track['time']
                if key in used or age>(30. if track['position'] is not None else .6):continue
                expected=track['ray'] if track['position'] is None else track['position']-position
                expected=expected/max(np.linalg.norm(expected),1e-8)
                angle=math.acos(float(np.clip(expected@world,-1,1)))
                if angle<math.radians(12+min(18.,40*age)):options.append((angle,key))
            options.sort()
            ambiguous=len(options)>1 and options[1][0]-options[0][0]<math.radians(3)
            if options and not ambiguous:key=options[0][1]
            else:key=f'visual_{self.sequence}';self.sequence+=1
            used.add(key)
            relative=self.geometry.relative_from_pixel(pixel,position[2]-.45,observation,self.calibration)
            point=None if relative is None else position+R@D@relative
            self.tracks[key]=dict(ray=world,position=point,time=t)
            views.append(EvidenceView(key,'unknown_boat' if ambiguous else p['evidence'],
                math.inf if relative is None else float(np.linalg.norm(relative[:2])),tuple(pixel),point))
        self.tracks={k:v for k,v in self.tracks.items() if t-v['time']<30}
        pan,tilt=observation['gimbal_rad']
        selected=self.search.decide(t,views,yaw+pan,
            abs(pan)<math.radians(3) and abs(tilt-math.radians(6))<math.radians(3))
        live=next((v for v in views if v.key==selected),None)
        if selected!=self.selected:
            self.last_point=None;self.selected=selected;self.base.reset()
            self.selected_since=t;self.last_progress=t;self.best_range=math.inf
        if live:
            self.last_seen=t;self.last_point=live.position
            if live.range_m<self.best_range-.5:
                self.best_range=live.range_m;self.last_progress=t
        elif selected and t-self.last_seen>3:
            self.search.restart(t,'lost_sensor_track');self.selected=None;self.base.reset()
            selected=None
        if selected and not self.search.confirmed and (t-self.last_progress>12 or t-self.selected_since>90):
            self.search.restart(t,'unresolved_sensor_inspection');self.selected=None
            self.last_point=None;selected=None;live=None;self.base.reset()
        if self.height is None:self.height=float(position[2])
        action=np.zeros(6);action[2]=-float(np.clip(.8*(self.height-position[2]),-.5,.5))
        action[3]=.35 if abs(pan)<math.radians(3) and abs(tilt-math.radians(6))<math.radians(3) else 0.
        action[4:]=[-3*pan,3*(math.radians(6)-tilt)]
        phase='scan'
        if selected and self.last_point is not None:
            delta=self.last_point-position
            heading=math.atan2(delta[1],delta[0]);error=self.wrap(heading-yaw)
            body=D@R.T@delta
            action[3]=-error
            action[4:]=[3*self.wrap(math.atan2(-body[1],body[0])-pan),
                         3*(math.atan2(body[2],np.linalg.norm(body[:2]))-tilt)]
            if live:
                velocity=.65*delta[:2]*max(0.,math.cos(error))
                norm=np.linalg.norm(velocity)
                if norm>2:velocity*=2/norm
                action[:2]=(D@R.T@np.r_[velocity,0.])[:2]
            phase='inspect' if live else 'reacquire_last_sensor_view'
            if not live:action[2]=0.
        if self.search.confirmed and live:
            pixel=live.pixel
            # ROI comes from this selected visual track, not the global maximum.
            self.base.decode_spatial=lambda output:(output[2].new_tensor([4.6]),output[2].new_tensor([pixel]))
            candidate,diag=self.base.act(rgb,observation)
            if diag.get('metric_valid') or diag.get('metric_confirmed') or diag.get('control_phase') in ('touchdown_commit','touchdown','confirm','disarmed'):
                diag.update(search_identity_confirmed=True,boat_radio=False,selected_visual_track=selected)
                return candidate,diag
            phase='confirmed_target_approach'
        if self.search.confirmed and not live:action[2]=0.
        norm=np.linalg.norm(action[:2])
        if norm>2:action[:2]*=2/norm
        action[2]=np.clip(action[2],-1,.7);action[3]=np.clip(action[3],-.5,.5)
        action,extra=self.guard.apply(action,observation,dict(pad_visibility_probability=0.))
        # The frozen supervisor expects an explicit normalized missing beacon.
        controlled=dict(observation,beacon=dict(valid=False,age_s=3.1,dock_ready=False))
        action,intervention=self.supervise(action,controlled,t,observation['mission']['budget_s'])
        if own.get('landed') or not own.get('armed'):action[:4]=0.
        return action,dict(self.search.diagnostics(),control_phase=phase,boat_radio=False,
            search_identity_confirmed=self.search.confirmed,intervention=intervention,**extra)
