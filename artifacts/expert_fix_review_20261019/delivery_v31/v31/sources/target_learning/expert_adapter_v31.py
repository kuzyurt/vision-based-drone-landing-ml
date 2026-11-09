"""Experimental RGB/own-state expert using a separately validated recognizer.

No simulator/environment object is accepted. Requires a declared static search
corridor and a measured recognizer gate. Must pass real runtime/flight previews
before collecting teacher trajectories. This is not a production policy.
"""
from collections import deque
from dataclasses import asdict
from pathlib import Path
import copy,importlib,json,math,sys,types
import numpy as np
import torch
from .protocol import PublicState,wrap
from .protocol_memory_repair import SearchProtocol
from .camera_axis_continuity import install as install_camera_continuity
from .tracks import TrackBank
from .metric_candidate_continuity import compatible as metric_candidate_compatible
from .local_downlook_v22 import camera_only_downlook
from .inspection_feedback_v25 import InspectionFeedback


def load_parent(bundle,name):
    pkg=types.ModuleType(name);pkg.__path__=[str(Path(bundle)/'code/landing_training')];sys.modules[name]=pkg
    return importlib.import_module(name+'.radio_robust_20261015.runtime')


class IdentityExpert:
    def __init__(self,bundle,checkpoint,*,device='cuda',package_name='observable_identity_expert',review_only=False):
        self.bundle=Path(bundle);self.config=json.loads((self.bundle/'policy.json').read_text())
        saved=torch.load(checkpoint,map_location=device,weights_only=False)
        if saved['schema'] not in ['mujoco.target_discriminator.v1','mujoco.target_discriminator.v5','mujoco.target_discriminator.v7','mujoco.target_discriminator.v10','mujoco.target_discriminator.v11','mujoco.target_discriminator.v12']:raise ValueError('Wrong recognizer schema')
        gate=saved['validation']
        self.review_only=bool(review_only)
        if not gate['expert_gate_passed']:
            if not self.review_only:raise PermissionError('Recognition qualification gate not passed')
            point=gate.get('selected_operating_point')
            if point is None or point['identity']<.98 or point['target_recall']<.4 or gate['object_recall']<.65:
                raise PermissionError('No conservative development-review operating point')
            if any(point[k]!=0 for k in ['wrong_object_acceptances','ambiguous_acceptances','background_acceptances']):
                raise PermissionError('Review pilot cannot admit known false target assertions')
        self.qualification_gate_passed=bool(gate['expert_gate_passed'])
        op=gate['selected_operating_point'];self.support_threshold=float(op.get('support',0.))
        self.presence_threshold=float(op.get('heat',.7));self.threshold=float(op.get('identity',op.get('threshold',.98)))
        self.marker_threshold=float(gate.get('selected_marker_operating_point',{}).get('threshold',.8))
        if saved['schema']in ['mujoco.target_discriminator.v5','mujoco.target_discriminator.v7','mujoco.target_discriminator.v10','mujoco.target_discriminator.v11','mujoco.target_discriminator.v12']:
            from .discriminator_v5 import Discriminator,decode
        else:
            from .discriminator import Discriminator,decode
        self.decode_candidates=decode
        self.parent=load_parent(bundle,package_name)
        self.runtime=self.parent.RadioRobustRuntime(self.bundle/'pose.pt',self.config['calibration'],self.config['slew_limits'],device,allow_visual_landing=True)
        self.pad_head=self.runtime.acquisition
        self.pad_decoder=self.runtime.decode_spatial
        self.head=Discriminator().to(device);self.head.load_state_dict(saved['model'],strict=True);self.head.eval()
        self.verifier=None
        self.verify_candidates=None
        if saved['schema']=='mujoco.target_discriminator.v7':
            from .object_verifier import ObjectVerifier,verify
            self.verifier=ObjectVerifier().to(device);self.verifier.load_state_dict(saved['verifier'],strict=True);self.verifier.eval()
            self.verify_candidates=verify
        elif saved['schema']=='mujoco.target_discriminator.v10':
            from .object_verifier_v10 import ObjectVerifier,verify
            self.verifier=ObjectVerifier().to(device);self.verifier.load_state_dict(saved['verifier'],strict=True);self.verifier.eval()
            self.verify_candidates=verify
        elif saved['schema']=='mujoco.target_discriminator.v11':
            from .object_verifier_v11 import ObjectVerifier,verify
            self.verifier=ObjectVerifier().to(device);self.verifier.load_state_dict(saved['verifier'],strict=True);self.verifier.eval()
            self.verify_candidates=verify
        elif saved['schema']=='mujoco.target_discriminator.v12':
            from .object_verifier_v12 import ObjectVerifier,verify
            self.verifier=ObjectVerifier(mode=saved['verifier_mode']).to(device);self.verifier.load_state_dict(saved['verifier'],strict=True);self.verifier.eval()
            self.verify_candidates=verify
        self.raw_rgb_verifier=saved['schema']in ['mujoco.target_discriminator.v11','mujoco.target_discriminator.v12']
        self.camera_geometry=importlib.import_module(self.parent.__package__+'.controller.visual_acquisition').camera_geometry
        guard=importlib.import_module(self.parent.__package__+'.controller.action_guard')
        self.final_guard=guard.ActionGuard(guard.GuardConfig(slew_limits=tuple(self.config['slew_limits'])))
        self.supervise=importlib.import_module(self.parent.__package__+'.controller.supervision').supervise_action
        owner=self
        class RecognizerProxy(torch.nn.Module):
            def forward(self,fine,context):
                output=owner.head(fine,context)
                if owner.verifier is not None:output.update(_fine=fine,_context=context)
                pad_heat,pad_offset,pad_presence=owner.pad_head(fine,context)
                output.update(_pad_heat=pad_heat,_pad_offset=pad_offset,_pad_presence=pad_presence)
                return output
        self.runtime.acquisition=RecognizerProxy();self.runtime.decode_spatial=self._decode
        self.reset()
        self.camera_fix_state=install_camera_continuity(self.runtime.controller)

    def reset(self):
        if hasattr(self,"camera_fix_state"):
            for key in self.camera_fix_state:self.camera_fix_state[key]=None
        self.runtime.reset();self.final_guard.reset()
        self.protocol=SearchProtocol(candidate_presence_threshold=self.presence_threshold)
        self.bank=TrackBank(target_threshold=self.threshold,support_threshold=self.support_threshold,presence_threshold=self.presence_threshold)
        self.history=deque(maxlen=64);self.last_seed=None;self.current_candidates=[]
        self.inspection_feedback=InspectionFeedback()
        self.capture_error=None;self.observation=None;self.current_camera_world=None
        self.start=None;self.last_near=None;self.pad_diagnostics={}

    def _mission(self,o):
        m=o.get('mission',{}).get('target_discrimination')
        required=['search_height_enu_m','maximum_height_enu_m','nominal_boat_plane_enu_m',
                  'plane_uncertainty_m','static_prior_no_dynamic_boat_state',
                  'search_corridor_valid','upward_corridor_valid']
        if not isinstance(m,dict)or not all(k in m for k in required):raise ValueError('Missing declared search mission prior')
        if not m['static_prior_no_dynamic_boat_state']:raise PermissionError('Dynamic truth in search prior')
        return m

    def _decode(self,output):
        self.pad_diagnostics={}
        o=self.observation;m=self._mission(o);now=float(o['image_delivery_time_s']);capture_time=float(o['image_capture_time_s'])
        stamp,capture=min(self.history,key=lambda t:abs(t[0]-capture_time));self.capture_error=abs(stamp-capture_time)
        pixel=[320.,180.];probability=1e-5
        yaw=math.pi/2-o['px4']['attitude_ned_rad'][2];R=self._heading(yaw);D=np.diag([1.,-1.,-1.])
        self.current_camera_world=np.array(o['px4']['position_enu_m'],dtype=float)
        if self.capture_error<=.021 and o['image_valid']and o['image_age_s']<=.25:
            rotation,origin,focal,_=self.camera_geometry(capture,self.config['calibration'])
            Rc=self._heading(math.pi/2-capture['px4']['attitude_ned_rad'][2])
            camera_world=np.asarray(capture['px4']['position_enu_m'])+Rc@D@origin
            self.current_camera_world=np.asarray(o['px4']['position_enu_m'])+R@D@origin
            decode_args=dict(minimum_presence=self.presence_threshold)
            if self.verifier is not None:decode_args['topk']=24  # Exact frozen verifier-validation proposal contract.
            frames=self.decode_candidates({k:v.detach().cpu()for k,v in output.items()if not k.startswith('_')},**decode_args)
            if self.verifier is not None:
                frames=self.verify_candidates(self.verifier,output['_fine'],output['_context'],frames,*([self.current_rgb]if self.raw_rgb_verifier else[]))
            detections=frames[0]
            # Coarse appearance comes only from the actual delivered RGB. It is
            # inspection-memory context, never a simulator identity or a vote.
            for detection in detections:
                center=np.asarray(detection['pixel']);half=.4*np.asarray(detection['size_px'])
                xs=np.clip(np.linspace(center[0]-half[0],center[0]+half[0],4).round().astype(int),0,639)
                ys=np.clip(np.linspace(center[1]-half[1],center[1]+half[1],4).round().astype(int),0,359)
                detection['appearance_descriptor']=(self.current_rgb[ys[:,None],xs[None,:],:]//8).reshape(-1).tolist()
            self.bank.observe(detections,capture_s=capture_time,frame_token=int(round(capture_time*1e6)),
                camera_world=camera_world,camera_to_world=Rc@D@rotation,focal_px=focal,
                plane_height_enu_m=float(m['nominal_boat_plane_enu_m']),plane_uncertainty_m=float(m['plane_uncertainty_m']))
            self.current_candidates=self.bank.candidates(now,self.current_camera_world)
            eligible=[t for t in self.bank.tracks.values()if now-t.measured_s<=.25 and self.bank._identity(t.detection)==1]
            previous=next((t for t in eligible if t.index==self.protocol.confirmed),None)
            metric_time=self.runtime.controller.metric_time
            metric_live=bool(metric_time is not None and now-metric_time<=.5 and self.last_seed==self.protocol.confirmed)
            selected=previous if metric_live else None
            if selected is None and eligible:selected=max(eligible,key=lambda t:t.detection['target_probability']*(.5+.5*t.detection.get('marker_probability',t.detection['pad_visibility_probability'])))
            if selected is not None:
                d=selected.detection
                # Keep the preserved b432 marker localizer, but constrain its
                # point to the recognized candidate's predicted image box.
                # No segmentation, target position or teacher action is used.
                heat=output['_pad_heat'];_,height,width=heat.shape
                yy,xx=torch.meshgrid(torch.arange(height,device=heat.device),torch.arange(width,device=heat.device),indexing='ij')
                cell_x=(xx+.5)*640/width;cell_y=(yy+.5)*360/height
                center=np.asarray(d['pixel']);half=.5*np.asarray(d['size_px'])
                box_mask=(cell_x>=center[0]-half[0])&(cell_x<=center[0]+half[0])&(cell_y>=center[1]-half[1])&(cell_y<=center[1]+half[1])
                if bool(box_mask.any()):
                    masked=heat.masked_fill(~box_mask[None],-1e9)
                    presence,pad=self.pad_decoder((masked,output['_pad_offset'],output['_pad_presence']))
                    proposed=pad[0].detach().cpu().numpy()
                    inside=bool(np.all(proposed>=center-half)and np.all(proposed<=center+half))
                    if inside:
                        pixel=proposed.tolist()
                        probability=float(presence[0].sigmoid().detach().cpu())*d['target_probability']*d.get('identity_support_probability',1.)
                    self.pad_diagnostics=dict(source='preserved b432 image marker localizer, masked to recognized predicted object box; original RGB paint registration still required',inside_predicted_identity_box=inside,pixel=proposed.tolist(),global_presence=float(presence[0].sigmoid().detach().cpu()),track_id=selected.index)
                metric_time=self.runtime.controller.metric_time
                live_metric=(self.protocol.confirmed is not None and self.last_seed==self.protocol.confirmed
                             and metric_time is not None and now-metric_time<=.5)
                changed=self.last_seed is not None and selected.index!=self.last_seed
                compatible=False
                if changed and not live_metric:
                    compatible=metric_candidate_compatible(self.runtime.controller.visual_memory.estimate(o),d,
                        camera_world=camera_world,camera_to_world=Rc@D@rotation,focal_px=focal,image_age_s=now-capture_time)
                    if not compatible:
                        self.runtime.controller.reset();self.runtime.hidden=None
                        for key in self.camera_fix_state:self.camera_fix_state[key]=None
                self.pad_diagnostics.update(proposal_changed=changed,metric_alias_compatible=compatible,
                    destructive_metric_reset=bool(changed and not live_metric and not compatible))
                if not live_metric:self.last_seed=selected.index
        else:self.current_candidates=self.bank.candidates(now,self.current_camera_world)
        device=output['heat'].device
        p=torch.tensor([probability],device=device).clamp(1e-5,1-1e-5)
        return torch.logit(p),torch.tensor([pixel],dtype=torch.float32,device=device)

    @staticmethod
    def _heading(yaw):
        c,s=math.cos(yaw),math.sin(yaw);return np.array([[c,-s,0],[s,c,0],[0,0,1.]])

    @property
    def controller(self):return self.runtime.controller

    def _public_state(self,o,diag):
        m=self._mission(o);p=o['px4'];now=float(o['image_delivery_time_s']);position=np.asarray(p['position_enu_m']);velocity=np.asarray(p['velocity_enu_m_s'])
        age=diag.get('metric_age_s');sigma=diag.get('metric_uncertainty_m');clearance=diag.get('estimated_clearance_m')
        geometry=bool(diag.get('metric_confirmed')and age is not None and age<=.16 and sigma is not None and sigma<=.15)
        if geometry and clearance is not None and clearance<1.:self.last_near=now
        near=self.last_near is not None and now-self.last_near<1.5
        identity_associated=bool(self.last_seed==self.protocol.confirmed and diag.get('metric_confirmed')and diag.get('metric_acceptance')=='tracked')
        return PublicState(now,int(round(float(o['image_capture_time_s'])*1e6)),math.pi/2-p['attitude_ned_rad'][2],
            float(position[2]),float(velocity[2]),*map(float,o['gimbal_rad']),
            bool(o['image_valid']and o['image_age_s']<=.25 and self.capture_error<=.021),
            bool(p.get('valid')and p.get('position_age_s',99)<=.25 and p.get('attitude_age_s',99)<=.25),
            bool(p.get('armed')and not p.get('landed')),bool(p.get('landed')),
            bool(m['upward_corridor_valid']or (self.protocol.confirmed is not None and diag.get('control_phase')=='recovery_climb'and diag.get('recovery_static_clearance_prior'))),bool(m['search_corridor_valid']),
            float(m['search_height_enu_m']),float(m['maximum_height_enu_m']),geometry,sigma,near,
            bool(np.linalg.norm(velocity)<.3),identity_associated,
            bool(diag.get('control_phase')=='touchdown_commit'and self.last_seed==self.protocol.confirmed))

    @torch.inference_mode()
    def act(self,rgb,observation):
        o=copy.deepcopy(observation);self._mission(o)
        # This experiment is specifically observation-only, no radio shortcut.
        o['beacon']=dict(valid=False,age_s=3.1,dock_ready=False,dock_status_valid=False)
        if np.asarray(rgb).shape!=(360,640,3):raise ValueError('Exact deployed image input required')
        self.current_rgb=np.asarray(rgb)
        now=float(o['image_delivery_time_s'])
        if self.start is None:self.start=now
        self.history.append((now,copy.deepcopy(o)));self.observation=o
        action,diag=self.runtime.act(rgb,o);s=self._public_state(o,diag)
        # Only camera-derived remembered points and own measured geometry.
        # This closes a visible-inspection loop; it never changes boat identity.
        remembered=self.bank.tracks.get(self.protocol.selected)
        rotation,origin,focal,_=self.camera_geometry(o,self.config['calibration'])
        R=self._heading(s.yaw_world_rad);D=np.diag([1.,-1.,-1.])
        feedback=self.inspection_feedback.observe(self.protocol,s,self.current_candidates,
            point_world=None if remembered is None else remembered.point_world,
            camera_world=np.asarray(o['px4']['position_enu_m'])+R@D@origin,
            camera_to_world=R@D@rotation,focal_px=focal,
            own_xy=np.asarray(o['px4']['position_enu_m'])[:2],
            fresh_detections=[t.detection for t in self.bank.tracks.values()if s.time_s-t.measured_s<=.25],
            own_angular_speed_rad_s=float(np.linalg.norm(o['px4']['angular_rate_frd_rad_s'])))
        diag['inspection_feedback']=feedback
        self.protocol.observe_visual_context(o['px4']['position_enu_m'],{
            track.index:dict(point=None if track.point_world is None else track.point_world.tolist(),
                range_interval=track.range_interval,appearance=track.detection.get('appearance_descriptor'))
            for track in self.bank.tracks.values()})
        intent=self.protocol.step(s,self.current_candidates)
        if intent.phase in ['target_align','target_contact_confirmation']:
            # Preserve native metric controller's final approach and strict
            # touchdown gates. Identity never manufactures a valid pad fit.
            pass
        elif intent.phase in ['local_downlook','recovery_climb','recovery_downlook']:
            if diag.get('recovery_active'):
                # Reuse the parent's current clearance/memory/age/camera and
                # bounded-following path. Do not replace it with XYhover plus
                # fixed downward tilt while a moving boat escapes the view.
                diag['expert_recovery_driver']='existing R15 visibility recovery, current guards unchanged'
            else:
                # A protocol request is not ascent permission. Without an
                # active guarded recovery, use bounded memory for camera aim
                # only and request no vertical movement.
                persistent=importlib.import_module(self.parent.__package__+'.controller.persistent_target')
                own=persistent.own_state(o);memory=self.runtime.controller.visual_memory.estimate(o)
                action=np.zeros(6)
                if own is not None:
                    aimed=self.runtime.controller.visibility_recovery._camera(self.runtime.controller,o,own,memory,now)
                    action[3:]=aimed[3:]
                    if (memory is None or not memory.get('local_aim_valid',False)) and intent.look_down:
                        # A local downlook must not become the generic horizon
                        # scan after target memory expires. Encoders only;
                        # preserve zero XY/Z and all existing ascent guards.
                        pan,tilt=o['gimbal_rad']
                        action[3]=0.
                        action[4]=float(np.clip(-3.*wrap(pan),-math.radians(50),math.radians(50)))
                        action[5]=float(np.clip(3.*(math.radians(80)-tilt),-math.radians(40),math.radians(40)))
                        diag['expert_expired_memory_downlook']=True
                action,extra=self.final_guard.apply(action,o,dict(control_phase='local_downlook',pad_visibility_probability=0.))
                action[2]=0.;diag['expert_override_guard']=extra
                diag['parent_control_phase']=diag['control_phase'];diag['control_phase']='local_downlook'
                diag['expert_recovery_driver']='memory camera only; no unguarded protocol ascent'
            action[2]=min(action[2],0.)
            # Apply in BOTH active-native-recovery and camera-only paths. V21
            # incorrectly placed this correction only in the inactive path.
            aim_memory=self.runtime.controller.visual_memory.estimate(o)
            action,downlook_applied=camera_only_downlook(action,o,aim_memory,intent.look_down)
            if downlook_applied:diag['expert_expired_memory_downlook']=True
        elif intent.phase=='ground_hold':
            # Preserve the parent's own-PX4 landed/armed contact-confirmation
            # behavior through ordinary disarm. Never start a search or climb
            # while the estimator reports landed.
            if not o['px4'].get('armed'):action[:4]=0.
        else:
            p=o['px4'];yaw=s.yaw_world_rad;R=self._heading(yaw);D=np.diag([1.,-1.,-1.])
            own_velocity=np.asarray(p['velocity_enu_m_s'],float)
            velocity=-.5*own_velocity
            velocity[2]=np.clip(.6*((intent.height_goal_enu_m if intent.height_goal_enu_m is not None else s.own_height_enu_m)-s.own_height_enu_m)-.3*own_velocity[2],-.2,.4)
            action=np.zeros(6);action[3]=intent.yaw_rate_rad_s
            pan,tilt=o['gimbal_rad'];desired_tilt=math.radians([30.,35.,45.][self.protocol.scan_band])
            chosen=next((c for c in self.current_candidates if c.track_id==intent.selected_track),None) if intent.phase in ['inspect_candidate','reorient_candidate','target_inspect','reject_overflight'] else None
            if chosen is not None:
                error=wrap(chosen.bearing_world_rad-yaw)
                action[3]=-float(np.clip(.8*error,-.35,.35))
                desired_tilt=math.radians(35.)
                t=self.bank.tracks[chosen.track_id]
                if t.point_world is not None:
                    vector=t.point_world-self.current_camera_world
                    desired_tilt=math.atan2(-vector[2],np.linalg.norm(vector[:2]))
                if intent.allow_approach and chosen.age_s<=.25 and abs(error)<math.radians(20):
                    # Existing2m/s envelope, conservative estimated stopping
                    # room, camera age and small near-object inspection speed.
                    if intent.phase=='reject_overflight' and chosen.range_interval_m:
                        speed=min(.5,.5*chosen.range_interval_m[0])
                    elif chosen.range_interval_m:
                        lower=chosen.range_interval_m[0]
                        stop_room=max(0.,lower-1.-2.*float(o['image_age_s']))
                        speed=min(2.,math.sqrt(stop_room),max(0.,lower-.7)*.6)
                    else:speed=.4
                    velocity[:2]=speed*np.array([math.cos(chosen.bearing_world_rad),math.sin(chosen.bearing_world_rad)])
            if intent.look_down:desired_tilt=math.radians(75.)
            action[:3]=D@R.T@velocity
            action[4]=3*wrap((wrap(chosen.bearing_world_rad-yaw) if chosen is not None else 0.)-pan)+float(p['angular_rate_frd_rad_s'][2])
            action[5]=3*(np.clip(desired_tilt,math.radians(-10),math.pi/2)-tilt)
            action[2]=min(action[2],0.)  # no unconfirmed/unknown-object descent
            # A separate guard is applied once to the actual override, using
            # recorded previous EXECUTED action rather than a fictional action.
            norm=np.linalg.norm(action[:2])
            if norm>2:action[:2]*=2/norm
            action[2]=np.clip(action[2],-1.,.7);action[3]=np.clip(action[3],-.5,.5)
            action,extra=self.final_guard.apply(action,o,dict(control_phase=intent.phase,pad_visibility_probability=diag.get('image_head_visibility',0)))
            diag['expert_override_guard']=extra
            if not intent.allow_descent:action[2]=min(action[2],0.)
            diag['parent_control_phase']=diag['control_phase'];diag['control_phase']=intent.phase
        action,intervention=self.supervise(action,o,now-self.start,float(o['mission']['budget_s']))
        diag.update(expert_inspected_view_count=len(self.protocol.inspected_views),expert_visit_events=self.protocol.visit_events[-4:],expert_search_exhausted=self.protocol.search_exhausted,expert_survey_epoch=self.protocol.survey_epoch,expert_scan_coverage_rad=self.protocol.scan_coverage,expert_empty_surveys=self.protocol.empty_surveys,expert_intent=asdict(intent),expert_visual_tracks=self.bank.diagnostics(),
            expert_source='RGB/own telemetry/encoders/declared static priors only',expert_intervention=intervention,
            expert_capture_history_error_s=self.capture_error,expert_observable_target_confirmed=self.protocol.confirmed is not None,
            expert_actual_flight_validated=False,expert_review_only=self.review_only,expert_recognition_qualification_passed=self.qualification_gate_passed,expert_marker_localizer=self.pad_diagnostics)
        return action,diag
