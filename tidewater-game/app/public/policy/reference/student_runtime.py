"""Browser adapter for the frozen student search runtime.

Neural pose/search inference is external (ONNX/WebGPU).  This module keeps the
exact sensor-only search/identity/radio/pre360 decision logic from the training
runtime, using the checked-in reference landing controller as its base.
"""
from __future__ import annotations
from dataclasses import dataclass
import copy
import math
import numpy as np
from .search_decision import SearchDecision
from .recording import numeric_observation
from .supervision import supervise_action
from . import camera_geometry as visual_geometry
from . import visual_acquisition as visual_module
from . import action_guard as guard_module
from . import tidewater_guidance as guidance

# The search head was trained on views from 3-10 m. The search (scan, inspect,
# pre-check, radio approach) and any hand-back from the landing controller to a
# search-like phase work at least at this height; higher start heights are
# kept. 7 m (2026-11-14): the pre-check climbs here looking straight down, and
# a far boat sits further below the horizon than from 5 m.
MIN_SEARCH_HEIGHT_M = 7.0
# Landing-controller phases in which the pad is not seen and the camera is
# searching again (the pad finder handed control back to a search). These
# always work at the minimum search height, never at deck level.
SEARCH_PHASES = ('visual_search','recovery_scan','recovery_climb','local_recovery')

@dataclass
class EvidenceView:
    key: str
    evidence: str
    range_m: float
    pixel: tuple
    position: np.ndarray | None
    detectable: bool = True


class _ControllerProxy:
    """Expose the R15 nested-controller shape over MarkerLandingController."""
    def __init__(self, controller):
        object.__setattr__(self, '_controller', controller)
        object.__setattr__(self, 'controller', controller)
    def __getattr__(self, name):
        return getattr(self._controller, name)
    def __setattr__(self, name, value):
        if name in ('_controller', 'controller'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._controller, name, value)


class BrowserBase:
    """Landing-controller adapter; prediction and proposals are supplied by JS."""
    def __init__(self, policy, config):
        self.policy=policy
        self.config=config
        self.controller=_ControllerProxy(policy.controller)
        self.prediction=np.zeros(15,dtype=np.float32)
        self.start_time=None
    def reset(self):
        self.policy.reset()
        self.prediction=np.zeros(15,dtype=np.float32)
        self.start_time=None
    def set_prediction(self,prediction):
        self.prediction=np.asarray(prediction,dtype=np.float32).reshape(15)
    def act(self,rgb,observation):
        obs=copy.deepcopy(observation)
        # The landing controller is sensor-only.  Radio may steer acquisition
        # before handoff, but it must never enter the R15 fit/descent path.
        b=obs.setdefault('beacon',{})
        b.clear();b.update(valid=False,age_s=3.1,dock_ready=False,relative_heading_m=[0.,0.,0.],velocity_heading_m_s=[0.,0.,0.])
        known=False;ready=False
        image=None if rgb is None else np.asarray(rgb,dtype=np.uint8).reshape(360,640,3)
        action,diag=self.policy.act(image,obs,self.prediction)
        now=float(obs['image_delivery_time_s'])
        if self.start_time is None:self.start_time=now
        action,intervention=supervise_action(action,obs,now-self.start_time,float(obs['mission']['budget_s']))
        if known and not ready:
            action[:4]=0.;intervention='dock_not_ready'
        elif not known and not self.config.get('allow_visual_landing',True) and action[2]>0:
            action[2]=0.;intervention='visual_landing_authorization_required'
        diag['intervention']=intervention
        return action,diag

class SearchRuntime:
    def __init__(self, config, policy):
        self.c=config
        self.calibration=config['calibration']
        self.slew_limits=np.asarray(config['slew_limits'],dtype=float)
        self.geometry=visual_geometry
        self.visual=visual_module
        self.guard=guard_module.ActionGuard(guard_module.GuardConfig(slew_limits=tuple(config['slew_limits'])))
        self.supervise=supervise_action
        self.wrap=guard_module.wrap
        self.base=BrowserBase(policy,config)
        self.reset()
    def controller(self):
        # The common mission guard reads controller.calibration for its
        # coarse-range planning path. Expose the frozen R15 controller here
        # without changing the search policy or the base weights.
        return self.base.controller

    def _pose_policy(self):
        # The pose policy (MarkerPosePolicy) owns VisibilityRecovery and the
        # visual-motion state. In the benchmark runtime `base.controller` IS
        # that policy; in the browser `base.controller` is a proxy for the inner
        # landing controller, so these must be reached through `base.policy`.
        return self.base.policy

    def _harden_base_recovery(self):
        # Prevent R15's VisibilityRecovery from climbing to 8.5m-9.3m (where the
        # 0.26m cyan marker is 9.5m away and cannot be resolved by marker_pose)
        # or declaring recovery_exhausted=True (which aborts in MissionSafety).
        vr=getattr(self._pose_policy(),'visibility_recovery',None)
        if vr is not None:
            vr._climb=lambda *a,**kw:False
            vr.exhausted=False

    def _reset_guidance(self):
        # Radio context for the current frame (set by the radio layer), the
        # area being inspected, areas found to be glare, and near-deck state.
        self._radio_ctx=None;self.radio_hint=None
        self.inspect_area=None;self.suspect_areas=[];self.tb_since={};self._view_world={}
        self.proven_areas=[];self.latch_samples=[];self.latch_metric_seen=False
        self.pad_samples=[];self.hop=None;self.hops=0
        self.early_commit=None;self.early_commits=0;self.pause_since=None
        # Sun-glare zone (ephemeris sun direction; see tidewater_guidance).
        self._sun=None;self.track_hist={};self.zone_real={};self.glare_keys={}
        self._zone_now={};self.zone_last={};self.glare_active_until=-math.inf;self.last_glare_protocol=-math.inf
        self._glare_event=False;self.frame_times=[];self.horizon_hits=[];self.horizon_frames=[]
        self.g_log=dict(radio_blocked_views=0,glare_flags=0,last_gate=None,last_abort=None,
                        pause_respected_s=0.,unproven_target_boat=0,proven_areas=0,sidestep_s=0.,
                        unlatched=0,zone_spots=0,zone_glare=0,zone_real=0,zone_blocked=0,
                        zone_unproven_target_boat=0,glare_protocols=0,shallow_glare_skipped=0,
                        horizon_promoted_frames=0)

    def guidance_summary(self):
        """Running summary of the 2026-11-14 guidance decisions (for logs)."""
        sun=self._sun
        return dict(self.g_log,early_commits=self.early_commits,early_commit_active=self.early_commit is not None,
                    hops=self.hops,hop_active=self.hop is not None,suspect_areas=len(self.suspect_areas),
                    radio_context=self._radio_ctx is not None,
                    sun_elevation_deg=None if sun is None else round(math.degrees(math.asin(float(np.clip(sun[2]/max(np.linalg.norm(sun),1e-9),-1,1)))),1),
                    glare_active=self.glare_active_until>self.frame_times[-1] if self.frame_times else False,
                    zone_now=dict(self._zone_now))

    def reset(self):
        # Reuse only the teacher's pure evidence-ordering state machine.
        # No oracle, BoatView, env handle, true label or teacher pilot is created.
        self.search=SearchDecision();self.base.reset();self.guard.reset()
        self._harden_base_recovery()
        self.landing_latched=False
        self.tracks={};self.sequence=0;self.height=None;self.last_point=None;self.last_seen=-100.
        self.last_proposals=None;self.pending_proposals=[];self.pending_weak=[]
        self.selected=None;self.selected_since=0.;self.last_progress=0.;self.best_range=math.inf
        self.boat_velocity=np.zeros(2);self.last_track_point=None;self.last_track_time=None
        self.last_velocity=np.zeros(2);self.latched_since=None
        self._reset_guidance()

    def set_proposals(self, proposals):
        # Weak heat-map peaks (below the proposal threshold) come flagged;
        # they only feed the horizon accumulator, never the search directly.
        items=list(proposals or [])
        self.pending_proposals=[p for p in items if not p.get('weak')]
        self.pending_weak=[p for p in items if p.get('weak')]

    def _proposals(self, rgb, observation):
        return self.pending_proposals

    def _update_boat_kinematics(self, pt, t):
        if self.last_track_point is not None and self.last_track_time is not None:
            dt_obs=t-self.last_track_time
            if .08<=dt_obs<=2.0:
                inst_v=(pt[:2]-self.last_track_point[:2])/dt_obs
                speed=float(np.linalg.norm(inst_v))
                if speed<=2.5:
                    alpha=.25 if np.linalg.norm(self.boat_velocity)>1e-3 else .6
                    self.boat_velocity=(1.-alpha)*self.boat_velocity+alpha*inst_v
                self.last_track_point=pt.copy();self.last_track_time=t
        else:
            self.last_track_point=pt.copy();self.last_track_time=t
        self.last_point=pt.copy()

    def _visual_evidence_dict(self, position, t):
        key=self.selected or 'latched_target'
        est_range=3.0
        if self.last_point is not None:
            est_range=float(np.linalg.norm((self.last_point-position)[:2]))
        if self.landing_latched and self.latched_since is not None:
            # Ensure MissionSafety sees steady range closure while R15 transitions
            # from visual_acquire into metric confirmation.
            synth=max(0.5, 10.0 - 0.8 * max(0., t - self.latched_since))
            est_range=min(est_range, synth)
        margin=.2*max(est_range,.5)
        return dict(
            expert_intent=dict(selected_track=key),
            expert_visual_tracks=[dict(
                track_id=key,
                range_interval_m=[max(0.,est_range-margin),est_range+margin]
            )]
        )

    def _update_search(self, observation, position, yaw, R, D, rotation, focal, t):
        """Feed the current search-head proposals to the track/identity
        state machine and return (selected track key, live view). Shared
        by the normal search and the pre360 look-around so both use exactly
        the same evidence rules."""
        proposals=self.pending_proposals+self._horizon_candidates(position,R,D,rotation,focal,t)
        self.last_proposals=proposals
        # Build deduplicated candidate proposals for search & inspection
        cand_list=[]
        for p in sorted(proposals,key=lambda p:-p['confidence']):
            pixel=p['pixel'];ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.])
            ray/=np.linalg.norm(ray);world=R@D@ray
            if ray[2]<=.02:continue
            if any(math.acos(float(np.clip(world@c['world'],-1,1)))<math.radians(2.5) for c in cand_list):
                continue
            relative=self.geometry.relative_from_pixel(pixel,position[2]-.45,observation,self.calibration)
            point=None if relative is None else position+R@D@relative
            cand_list.append(dict(p=p,pixel=pixel,world=world,relative=relative,point=point))

        # SearchHead proposals are the complete sensor evidence.  The frozen
        # R15 pad registration takes over after identity handoff.
        views=[];used=set()
        self.suspect_areas=[a for a in self.suspect_areas if t<a['until']]
        self._zone_now={};self._glare_event=False
        # Sun direction from the solar ephemeris (mission clock + GNSS site).
        sun=(observation.get('ephemeris') or {}).get('sun_direction_enu')
        self._sun=None if sun is None else np.asarray(sun,dtype=float)
        self.frame_times.append(t);self.frame_times=[x for x in self.frame_times if t-x<=3.]
        for c in cand_list:
            p=c['p'];pixel=c['pixel'];world=c['world'];relative=c['relative'];point=c['point']
            options=[]
            for key,track in self.tracks.items():
                age=t-track['time']
                if key in used or age>(30. if track['position'] is not None else .6):continue
                expected=track['ray'] if track['position'] is None else track['position']-position
                expected=expected/max(np.linalg.norm(expected),1e-8)
                angle=math.acos(float(np.clip(expected@world,-1,1)))
                gate=math.radians(12+min(18.,40*age))
                if angle<gate:
                    score=angle-(math.radians(2.0) if key==self.selected else 0.)
                    options.append((score,angle,key))
            options.sort()
            if options:
                key=options[0][2]
            else:
                key=f'visual_{self.sequence}';self.sequence+=1
            used.add(key)
            self.tracks[key]=dict(ray=world,position=point,time=t)
            if p['evidence']=='target_boat':self.tb_since.setdefault(key,t)
            else:self.tb_since.pop(key,None)
            evidence=p['evidence']
            zone=self._zone_update(key,world,point,position,t)
            ctx=self._radio_ctx
            agrees=ctx is not None and guidance.agrees_with_radio(position[:2],ctx['target'][:2],world,
                None if point is None else point[:2],ctx['sigma'],ctx['speed'],ctx['age'])
            if zone is None:
                if evidence=='target_boat' and ctx is None and not self._proven(world,point,position,t):
                    # Without radio, the search head's "target boat" label alone is
                    # not enough (sun glare has been labelled target boat with
                    # identity 1.0): inspect it until the motion test shows it does
                    # not travel with the drone.
                    evidence='target_or_similar';self.g_log['unproven_target_boat']+=1
            elif zone!='real' and evidence=='target_boat' and not agrees:
                # Inside the sun-glare zone a "target boat" label confirms only
                # after the spot proved to be a steady object (or the radio agrees).
                evidence='target_or_similar';self.g_log['zone_unproven_target_boat']+=1
            views.append(EvidenceView(key,evidence,
                math.inf if relative is None else float(np.linalg.norm(relative[:2])),tuple(pixel),point,
                self._view_allowed(key,evidence,world,point,position,t,zone,agrees)))
            self._view_world[key]=world

        self.tracks={k:v for k,v in self.tracks.items() if t-v['time']<30}
        self.track_hist={k:v for k,v in self.track_hist.items() if k in self.tracks}
        self.tb_since={k:v for k,v in self.tb_since.items() if k in self.tracks}
        self._view_world={k:v for k,v in self._view_world.items() if k in used}
        pan,tilt=observation['gimbal_rad']
        selected=self.search.decide(t,views,yaw+pan,
            abs(pan)<math.radians(3) and abs(tilt-math.radians(6))<math.radians(3))
        live=next((v for v in views if v.key==selected and v.detectable),None)
        if (self._glare_event and self._radio_ctx is None and selected is not None
                and self.zone_last.get(selected) in ('glare','undecided') and t-self.last_glare_protocol>10.):
            # Sun-glare protocol: the drone was following a spot inside the
            # glare zone and glare has just been confirmed there. Drop it and
            # search again with the normal 360 deg scan; while glare is active,
            # unproven spots inside the zone may not start an inspection.
            self.last_glare_protocol=t;self.g_log['glare_protocols']+=1
            self.search.restart(t,'sun_glare_protocol');self.selected=None;self.inspect_area=None
            self.last_point=None;self.base.reset();self._harden_base_recovery()
            return None,None
        if selected!=self.selected:
            self.last_point=None;self.selected=selected;self.base.reset()
            self._harden_base_recovery()
            self.selected_since=t;self.last_progress=t;self.best_range=math.inf
            self.boat_velocity=np.zeros(2);self.last_track_point=None;self.last_track_time=None
        if live:
            self.last_seen=t
            if live.position is not None:
                self._update_boat_kinematics(live.position,t)
            if live.range_m<self.best_range-.5:
                self.best_range=live.range_m;self.last_progress=t
            if self._inspect_area_update(live,position,t):
                # The spot travels with the drone: a reflection, not a boat.
                # Ignore that direction for a while and search again.
                self.search.restart(t,'glare_follows_drone');self.selected=None
                self.last_point=None;selected=None;live=None;self.base.reset()
                self._harden_base_recovery()
                return selected,live
        elif selected and t-self.last_seen>4.5:
            self.search.restart(t,'lost_sensor_track');self.selected=None;self.base.reset()
            self._harden_base_recovery()
            selected=None
        # Progress is judged per inspected area, not per spot: a flickering
        # spot gets a new track name on every reappearance, which used to reset
        # the 16 s no-progress timer for ever.
        area=self.inspect_area
        last_progress=self.last_progress if area is None else area['last_progress']
        since=self.selected_since if area is None else area['since']
        if selected and not self.search.confirmed and (t-last_progress>16 or t-since>90):
            self.search.restart(t,'unresolved_sensor_inspection');self.selected=None
            self.last_point=None;selected=None;live=None;self.base.reset()
            self._harden_base_recovery()
            if area is not None:self._suspect(area['az'],t,'unresolved')
            self.inspect_area=None
        if not selected and area is not None and t-area['last_t']>5.:
            self.inspect_area=None
        return selected,live

    # ---------------------------------------------------------- guidance hooks
    def _suspect(self,az,t,reason,hold_s=30.):
        self.suspect_areas.append(dict(az=float(az),until=t+hold_s,reason=reason))

    def _proven(self,world,point,position,t):
        """Has this direction/place already passed the motion test? A match
        refreshes the entry, so a moving boat stays proven."""
        self.proven_areas=[a for a in self.proven_areas if t<a['until']]
        az=math.atan2(world[1],world[0])
        for a in self.proven_areas:
            near=(point is not None and a['point'] is not None
                  and float(np.linalg.norm(np.asarray(point[:2])-a['point']))<max(5.,.25*float(np.linalg.norm(np.asarray(point[:2])-position[:2]))))
            if near or abs(guidance.wrap(az-a['az']))<math.radians(15):
                a.update(az=az,until=t+60.)
                if point is not None:a['point']=np.asarray(point[:2],dtype=float).copy()
                return True
        return False

    def _needs_parallax(self,t):
        """Inspecting an unproven spot without radio while barely moving: the
        motion test cannot decide, so the drone should sidestep."""
        area=self.inspect_area
        if self._radio_ctx is not None or area is None or area.get('proven') or t-area['since']<1.5:
            return False
        recent=[s for s in area['samples'] if t-s[0]<=1.5]
        if len(recent)<2 or recent[-1][0]-recent[0][0]<1.:
            return True
        speed=float(np.linalg.norm(recent[-1][1]-recent[0][1]))/(recent[-1][0]-recent[0][0])
        return speed<1.

    def _latched_target_is_glare(self,t):
        """After a visual (not radio) hand-off and before any pad measurement:
        does the latched target travel with the drone?"""
        if self.latch_metric_seen or self.selected=='radio_target':return False
        return guidance.follows_drone(self.latch_samples,t,window_s=6.,min_move_m=2.) is True

    def _unlatch(self,position,t):
        az=None
        if self.last_point is not None:
            d=self.last_point[:2]-position[:2]
            if float(np.linalg.norm(d))>.5:az=math.atan2(d[1],d[0])
        self.landing_latched=False;self.latched_since=None;self.latch_samples=[]
        self.search.restart(t,'latched_target_follows_drone');self.selected=None;self.last_point=None
        self.base.reset();self._harden_base_recovery();self.inspect_area=None
        if az is not None:
            self._suspect(az,t,'latched_follows_drone')
            self.proven_areas=[a for a in self.proven_areas if abs(guidance.wrap(az-a['az']))>=math.radians(15)]
        self.g_log['unlatched']+=1;self.g_log['glare_flags']+=1

    # ---------------------------------------------------------- horizon evidence
    def _horizon_candidates(self,position,R,D,rotation,focal,t):
        """A boat near the horizon (about 30-280 m from 5-6 m height) often
        stays below the search head's reporting threshold, but its weak peak
        sits in the same direction frame after frame, while sea noise does not.
        Without radio, such a repeated direction (outside the sun-glare zone)
        is promoted to an "unknown boat" sighting; the normal search then
        inspects it and the search head names it as the drone gets closer."""
        if self._radio_ctx is not None:
            self.horizon_hits=[]
            return []
        centre=R@D@rotation@np.array([0.,0.,-1.])
        self.horizon_frames.append((t,math.atan2(centre[1],centre[0])))
        self.horizon_frames=[f for f in self.horizon_frames if t-f[0]<=3.]
        fresh=[]
        for p in self.pending_weak:
            px=p['pixel'];ray=rotation@np.array([(px[0]-320)/focal,-(px[1]-180)/focal,-1.])
            ray/=np.linalg.norm(ray);world=R@D@ray
            depression=math.degrees(math.asin(float(np.clip(-world[2],-1.,1.))))
            if not 1.2<=depression<=10. or guidance.in_glint_zone(world,self._sun):
                continue
            hit=(t,math.atan2(world[1],world[0]),depression,p)
            self.horizon_hits.append(hit);fresh.append(hit)
        self.horizon_hits=[h for h in self.horizon_hits if t-h[0]<=3.]
        out=[]
        for h in fresh:
            # Same spot (+-1 deg, a boat's peak stays within a few pixels),
            # for >= 1 s, and lit in >= 40% of the frames that looked that way
            # (shore and wave noise lights a given spot in ~5%).
            near=[x for x in self.horizon_hits if abs(guidance.wrap(x[1]-h[1]))<=math.radians(1.) and abs(x[2]-h[2])<=.6]
            frames=sorted({round(x[0],3) for x in near})
            if len(frames)<10 or frames[-1]-frames[0]<1.:
                continue
            looked=sum(1 for f in self.horizon_frames if f[0]>=frames[0] and abs(guidance.wrap(f[1]-h[1]))<math.radians(28.))
            if looked and len(frames)>=.4*looked:
                out.append(dict(pixel=h[3]['pixel'],confidence=float(h[3]['confidence']),evidence='unknown_boat',
                                identity_target_probability=0.,horizon=True))
        if out:self.g_log['horizon_promoted_frames']+=1
        return out[:1]

    # ---------------------------------------------------------- sun-glare zone
    def _zone_update(self,key,world,point,position,t):
        """Record this sighting and classify it against the sun-glare zone:
        None (outside the zone or no sun), 'real', 'glare' or 'undecided'."""
        depression=math.asin(float(np.clip(-world[2],-1.,1.)))
        hist=self.track_hist.setdefault(key,[])
        hist.append((t,np.asarray(position[:2],dtype=float).copy(),
                     None if point is None else np.asarray(point[:2],dtype=float).copy(),depression))
        if len(hist)>90 or t-hist[0][0]>3.:self.track_hist[key]=hist=[h for h in hist if t-h[0]<=3.][-90:]
        if not guidance.in_glint_zone(world,self._sun):
            self.zone_last.pop(key,None)
            return None
        self.g_log['zone_spots']+=1
        if t-self.zone_real.get(key,-math.inf)<60. or self._proven_point(point,position,t):
            state='real'
        elif t-self.glare_keys.get(key,-math.inf)<30.:
            state='glare'
        else:
            verdict=guidance.steady_sea_point(hist,t)
            if verdict is True:
                state='real';self.zone_real[key]=t;self.g_log['zone_real']+=1
                if point is not None:
                    self.proven_areas.append(dict(az=math.atan2(world[1],world[0]),until=t+60.,
                        point=np.asarray(point[:2],dtype=float).copy(),zone=True))
            elif verdict is False:
                state='glare';self._mark_glare(key,t)
            else:
                state='undecided'
        self._zone_now[key]=state;self.zone_last[key]=state
        return state

    def _mark_glare(self,key,t):
        self.glare_keys[key]=t;self.g_log['zone_glare']+=1;self.g_log['glare_flags']+=1
        self.glare_active_until=t+60.;self._glare_event=True
        self.zone_real.pop(key,None)

    def _persistent(self,key,t,window_s=1.5,share=.75):
        """Seen in most frames of the last 1.5 s: a boat is detected frame
        after frame, sun sparkles come and go."""
        frames=[x for x in self.frame_times if t-x<=window_s]
        seen=[h for h in self.track_hist.get(key,[]) if t-h[0]<=window_s]
        if len(frames)<10 or not seen or seen[-1][0]-seen[0][0]<.8*window_s:
            return False
        return len(seen)>=share*len(frames)

    def _proven_point(self,point,position,t):
        """Has a steady object been proven at this sea point? (point match
        only: inside the glare zone a direction match is not enough)"""
        if point is None:return False
        p=np.asarray(point[:2],dtype=float)
        rng=float(np.linalg.norm(p-np.asarray(position[:2],dtype=float)))
        for a in self.proven_areas:
            if t<a['until'] and a.get('point') is not None and float(np.linalg.norm(p-a['point']))<max(3.,.15*rng):
                a['point']=p.copy();a['until']=t+60.
                return True
        return False

    def _view_allowed(self,key,evidence,world,point,position,t,zone=None,agrees=False):
        """May the search act on this camera spot? (radio agreement + glare)"""
        az=math.atan2(world[1],world[0])
        suspect=any(abs(guidance.wrap(az-a['az']))<math.radians(12) for a in self.suspect_areas)
        ctx=self._radio_ctx
        if zone=='glare' and not agrees:
            self.g_log['zone_blocked']+=1
            return False
        if ctx is None:
            # Without radio, a direction found to be glare is ignored for a
            # while whatever the label (glare has been labelled target boat).
            if suspect:return False
            # While sun glare is active, an unproven spot inside the glare zone
            # may start/keep an inspection only if it is seen steadily (a boat
            # is detected frame after frame; sparkles flicker).
            if zone=='undecided' and t<self.glare_active_until and not self._persistent(key,t):
                self.g_log['zone_blocked']+=1
                return False
            return True
        if agrees:
            return True
        # A confirmed "target boat" that disagrees with the radio is only
        # believed after 3 s of steady sightings that do not travel with the
        # drone (radio fault rather than a misread reflection).
        if evidence=='target_boat' and not suspect and zone in (None,'real') and t-self.tb_since.get(key,t)>=3.:
            area=self.inspect_area
            if area is None or guidance.follows_drone(area['samples'],t) is not True:
                return True
        if evidence in ('target_boat','target_or_similar'):self.g_log['radio_blocked_views']+=1
        return False

    def _inspect_area_update(self,live,position,t):
        """Track the direction being inspected across track renames. Returns
        True when the inspected spot is shown to travel with the drone."""
        world=self._view_world.get(live.key)
        if world is None:return False
        az=math.atan2(world[1],world[0]);area=self.inspect_area
        if area is None or abs(guidance.wrap(az-area['az']))>math.radians(20) or t-area['last_t']>5.:
            area=self.inspect_area=dict(az=az,since=t,last_t=t,last_progress=t,best_range=math.inf,samples=[])
        area['az']=area['az']+.2*guidance.wrap(az-area['az']);area['last_t']=t
        if live.range_m<area['best_range']-.5:
            area['best_range']=live.range_m;area['last_progress']=t
        if live.position is not None:
            area['samples'].append((t,np.asarray(position[:2],dtype=float).copy(),np.asarray(live.position[:2],dtype=float).copy()))
            area['samples']=[s for s in area['samples'] if t-s[0]<=4.]
        depression=math.degrees(math.asin(float(np.clip(-world[2],-1.,1.))))
        zone=self._zone_now.get(live.key)
        verdict=guidance.follows_drone(area['samples'],t)
        if verdict is not None and depression<12.:
            # Distance from a shallow view is noise (a boat 3-4 deg below the
            # horizon jumps tens of metres between frames): this test cannot
            # judge it. A real boat 90 m away was once dropped as "glare".
            self.g_log['shallow_glare_skipped']+=verdict is True
            verdict=None
        if zone is not None:
            # Inside the sun-glare zone the zone test decides. A spot there that
            # clearly rides with the drone is glare; nothing here proves it real.
            if verdict is True and live.evidence!='target_boat':
                self._mark_glare(live.key,t)
                self._suspect(area['az'],t,'follows_drone');self.inspect_area=None
                return True
            return False
        if verdict is False and not area.get('proven'):
            # Real object: it stayed put (or moved on its own) while the drone
            # moved. From now on its "target boat" label may confirm it.
            area['proven']=True;self.g_log['proven_areas']+=1
            self.proven_areas.append(dict(az=area['az'],until=t+60.,
                point=None if live.position is None else np.asarray(live.position[:2],dtype=float).copy()))
        if live.evidence=='target_boat':return False
        if verdict is True:
            self._suspect(area['az'],t,'follows_drone');self.inspect_area=None
            self.g_log['glare_flags']+=1
            return True
        return False

    # ---------------------------------------------------------- near deck
    def _radio_velocity(self,t):
        hint=self.radio_hint
        if hint is None or t-hint['t']>1.5:return None
        return hint['velocity']

    def _record_pad_sample(self,diag,own,position,R,D,t):
        """Remember good pad fixes (pose valid and metric confirmed)."""
        if not (diag.get('pose_valid') and diag.get('metric_confirmed')):return
        r=diag.get('estimated_relative_position');v=diag.get('estimated_relative_velocity')
        clr=diag.get('estimated_clearance_m')
        if r is None or v is None or clr is None:return
        r=np.asarray(r,dtype=float);v=np.asarray(v,dtype=float)
        if r.shape!=(3,) or v.shape!=(3,) or not (np.isfinite(r).all() and np.isfinite(v).all()):return
        pad=position+R@D@r
        pad_velocity=np.asarray(own['velocity_enu_m_s'],dtype=float)+R@D@v
        self.pad_samples.append(dict(t=t,clearance=float(clr),
            lateral=float(diag.get('estimated_lateral_error_m',99.)),relative_speed=float(np.linalg.norm(v[:2])),
            heading_error_deg=float(diag.get('estimated_heading_error_deg',99.)),
            deck_tilt_deg=float(diag.get('estimated_deck_tilt_deg',99.)),
            deck_body_z=float(position[2]-float(clr)),pad_world=pad,pad_velocity=pad_velocity))
        self.pad_samples=[s for s in self.pad_samples if t-s['t']<=3.]

    def _near_deck_update(self,diag,own,position,t,now_img):
        """After a pad loss close to the deck: blind finish or a small hop."""
        if diag.get('pose_valid') and diag.get('metric_confirmed'):
            if self.hop is not None:diag['near_deck_hop_ended']='pad_back_in_view'
            self.hop=None;return
        last=self.pad_samples[-1] if self.pad_samples else None
        if (last is None or t-last['t']>guidance.NEAR_DECK_MEMORY_S
                or last['clearance']>guidance.NEAR_DECK_CLEARANCE_M or own.get('landed')):
            if self.hop is not None:diag['near_deck_hop_ended']='pad_fix_too_old'
            self.hop=None;return
        if self.hop is not None:return
        ctl=self.base.controller.controller
        if ctl.contact_started is not None:return
        if self.early_commits<2:
            roll,pitch,_=own['attitude_ned_rad']
            ok,reason=guidance.early_commit_gate(self.pad_samples,t,self._radio_velocity(t))
            if ok and max(abs(roll),abs(pitch))>math.radians(6):ok,reason=False,'drone_not_level'
            diag['early_commit_gate']=reason;self.g_log['last_gate']=reason
            if ok:
                # Deck heave is oscillatory: never extrapolate a momentary
                # vertical deck speed (it drifts the predicted deck height and
                # trips the controller's 0.25 m height-change bound at contact).
                velocity=np.asarray(last['pad_velocity'],dtype=float).copy();velocity[2]=0.
                pad=np.asarray(last['pad_world'],dtype=float)+velocity*(t-last['t'])
                ctl.contact_started=now_img
                ctl.commit_visual_reference=dict(time=now_img,pad_world=pad.copy(),
                    velocity_world=velocity,initial_relative_height=float(position[2]-pad[2]))
                self.early_commit=dict(start=t,start_z=float(position[2]),clearance=last['clearance'],
                    velocity=velocity[:2].copy(),ref=ctl.commit_visual_reference)
                self.early_commits+=1
                diag['early_commit_started']=True
                return
        if self.hops<4:
            self.hop=dict(since=t,deck_body_z=last['deck_body_z'],lost_clearance=last['clearance'])
            self.hops+=1
            diag['near_deck_hop_started']=True

    def _apply_hop(self,action,observation,position,dt,diag):
        target=self.hop['deck_body_z']+guidance.HOP_CLEARANCE_M
        prev=np.asarray(observation['previous_executed_action'],dtype=float)
        max_dz=self.slew_limits[2]*dt
        if position[2]<target-.05:desired=-float(np.clip(.8*(target-position[2]),.1,.4))
        else:desired=float(np.clip(action[2],-.1,0.))
        action[2]=float(np.clip(desired,prev[2]-max_dz,prev[2]+max_dz))
        diag.update(near_deck_hop=True,near_deck_hop_target_z=float(target),near_deck_hops=self.hops)

    def _failed_commit_bound(self,own,position,ec,now_img):
        """Which bound of the controller's touchdown commit failed (for logs).
        Mirrors MarkerLandingController.act's `bounded` test."""
        ref=ec.get('ref')
        if not ref:return 'unknown'
        vel=np.asarray(own['velocity_enu_m_s'],dtype=float)
        predicted=np.asarray(ref['pad_world'])+np.asarray(ref['velocity_world'])*(now_img-float(ref['time']))
        speed=float(np.linalg.norm(vel[:2]-np.asarray(ref['velocity_world'])[:2]))
        error=float(np.linalg.norm(predicted[:2]-position[:2]))
        height=abs((position[2]-predicted[2])-ref['initial_relative_height'])
        roll,pitch,_=own['attitude_ned_rad']
        parts=[]
        if speed>=.15:parts.append(f'speed={speed:.2f}')
        if max(abs(roll),abs(pitch))>=math.radians(8):parts.append('tilt')
        if error>=.18:parts.append(f'xy_error={error:.2f}')
        if height>=.25:parts.append(f'height_change={height:.2f}')
        return ','.join(parts) or f'other(speed={speed:.2f},err={error:.2f},dh={height:.2f})'

    def _monitor_early_commit(self,action,own,position,t,diag,now_img):
        """Abort the blind finish if it stops matching what was expected."""
        ec=self.early_commit
        if ec is None:return
        diag['early_commit']=True
        if own.get('landed') or not own.get('armed'):return
        ctl=self.base.controller.controller
        reason=None
        if ctl.contact_started is None:reason='commit_bounds_failed:'+self._failed_commit_bound(own,position,ec,now_img)
        elif position[2]<ec['start_z']-(max(0.,ec['clearance'])+.15):reason='deck_not_where_expected'
        elif t-ec['start']>8.:reason='no_contact'
        else:
            radio=self._radio_velocity(t)
            if radio is not None and float(np.linalg.norm(np.asarray(radio)-ec['velocity']))>.3:
                reason='radio_reports_boat_motion_change'
        if reason is None:return
        ctl.contact_started=None;ctl.commit_visual_reference=None;ctl.stable_elapsed=0.
        self.early_commit=None
        action[2]=min(0.,float(action[2]))
        diag['early_commit_aborted']=reason;self.g_log['last_abort']=reason
        last=self.pad_samples[-1] if self.pad_samples else None
        if last is not None and self.hops<4:
            self.hop=dict(since=t,deck_body_z=last['deck_body_z'],lost_clearance=last['clearance'])
            self.hops+=1

    def act(self, rgb, observation):
        self._harden_base_recovery()
        own=observation['px4'];t=float(observation['mission']['elapsed_s'])
        if not own.get('valid') or max(own.get('position_age_s',100),own.get('attitude_age_s',100))>.25:
            return np.zeros(6),dict(control_phase='estimator_hold',boat_radio=False)
        if not observation['image_valid'] or observation['image_age_s']>.25:
            return np.zeros(6),dict(control_phase='image_hold',boat_radio=False)
        position=np.asarray(own['position_enu_m'],dtype=float)
        if self.height is None:self.height=max(float(position[2]),MIN_SEARCH_HEIGHT_M)
        yaw=math.pi/2-own['attitude_ned_rad'][2]
        co,si=math.cos(yaw),math.sin(yaw)
        R=np.array([[co,-si,0],[si,co,0],[0,0,1.]])
        D=np.diag([1.,-1.,-1.])
        dt=float(observation.get('decision_dt_s',.04))

        if self.base.controller.controller.contact_started is not None:
            # Original R15 bounded contact continuation must survive camera occlusion.
            self.landing_latched=True
            if self.latched_since is None:self.latched_since=t
            action,diag=self.base.act(rgb,observation)
            action=np.asarray(action,dtype=float).copy()
            self._monitor_early_commit(action,own,position,t,diag,float(observation['image_delivery_time_s']))
            diag.update(self._visual_evidence_dict(position,t),
                        search_identity_confirmed=True,boat_radio=False,handoff_latched=True,
                        recovery_exhausted=False)
            return action,diag

        rotation,_,focal,_=self.visual.camera_geometry(observation,self.calibration)
        proposals=self.pending_proposals
        self.last_proposals=proposals

        # Propagate last_point with estimated boat velocity between measurements
        if self.last_point is not None and np.linalg.norm(self.boat_velocity)>1e-3:
            self.last_point=self.last_point+np.r_[self.boat_velocity*dt,0.]

        if self.landing_latched and self._latched_target_is_glare(t):
            # The latched target travels with the drone and the pad was never
            # measured: a reflection, not the boat. Search again.
            self._unlatch(position,t)
        if self.landing_latched:
            if self.latched_since is None:self.latched_since=t
            # Update last_point from search proposals if consistent
            for p in sorted(proposals,key=lambda p:-p['confidence']):
                rel=self.geometry.relative_from_pixel(p['pixel'],position[2]-.45,observation,self.calibration)
                if rel is not None:
                    pt=position+R@D@rel
                    if self.last_point is None or np.linalg.norm((pt-self.last_point)[:2])<6.:
                        self._update_boat_kinematics(pt,t)
                        if not self.latch_metric_seen:
                            self.latch_samples.append((t,np.asarray(position[:2],dtype=float).copy(),np.asarray(pt[:2],dtype=float).copy()))
                            self.latch_samples=[s for s in self.latch_samples if t-s[0]<=6.]
                        break

            now_img=float(observation['image_delivery_time_s'])
            pose_policy=self._pose_policy()
            # Pre-seed R15's visual boat velocity before its 10-frame fit window is ready
            if getattr(pose_policy,'visual_motion_time',None) is None and self.last_point is not None and np.linalg.norm(self.boat_velocity)>0.05:
                pose_policy.visual_velocity_enu=np.r_[self.boat_velocity,0.]
                pose_policy.visual_boat_sample=(now_img,self.last_point.copy())
            self.base.controller.controller.nearfield_visibility_hold_started=None
            if getattr(pose_policy,'visibility_recovery',None) is not None:
                pose_policy.visibility_recovery.exhausted=False

            action,diag=self.base.act(rgb,observation)
            action=np.asarray(action,dtype=float).copy()
            diag['recovery_exhausted']=False
            if getattr(pose_policy,'visibility_recovery',None) is not None:
                pose_policy.visibility_recovery.exhausted=False
            self._record_pad_sample(diag,own,position,R,D,t)
            self._near_deck_update(diag,own,position,t,now_img)

            # Also refine last_point from R15's spatial/image center when visible
            if not diag.get('metric_confirmed',False) and diag.get('image_head_visibility',0.)>=.55:
                img_px=diag.get('image_only_center_px')
                if img_px is not None:
                    rel=self.geometry.relative_from_pixel(img_px,position[2]-.45,observation,self.calibration)
                    if rel is not None:
                        pt=position+R@D@rel
                        if self.last_point is None or np.linalg.norm((pt-self.last_point)[:2])<6.:
                            self._update_boat_kinematics(pt,t)

            cphase=diag.get('control_phase','')
            metric_ok=bool(diag.get('metric_confirmed',False))
            if metric_ok:self.latch_metric_seen=True;self.latch_samples=[]
            paused=metric_ok and (bool(diag.get('nearfield_descent_paused')) or cphase=='visibility_align')
            if not paused:self.pause_since=None
            elif self.pause_since is None:self.pause_since=t
            if self.hop is not None:
                # Pad lost close to the deck: rise only to where the whole pad
                # fits in view again (~0.7 m), never back to search height.
                self._apply_hop(action,observation,position,dt,diag)
            elif not metric_ok and cphase in ('visual_acquire','visual_reacquire','visual_attention','visual_search','local_recovery','recovery_climb','recovery_scan','acquire','metric_recovery'):
                # 1. Hold altitude at ~5.4m ENU (~5.0m above deck) so 3D slant range
                # is short enough (<6.5m) for 0.26m cyan marker registration.
                target_z=min(self.height,5.4)
                desired_vz=-float(np.clip(.8*(target_z-position[2]),-.45,.45))
                # 2. Close horizontally all the way to 1.2m standoff with boat velocity
                # feedforward so fast boats (1.5 m/s) never stall at 7.0m and wind/wave
                # cases never oscillate at the 4.0m bearing_far boundary.
                if self.last_point is not None:
                    delta=self.last_point-position
                    dist_xy=float(np.linalg.norm(delta[:2]))
                    if dist_xy>0.8:
                        unit=delta[:2]/max(dist_xy,1e-6)
                        close_speed=float(np.clip(.75*(dist_xy-1.0),.45,1.8))
                        desired_world=self.boat_velocity+unit*close_speed
                        norm=float(np.linalg.norm(desired_world))
                        if norm>2.0:desired_world*=2.0/norm
                        body_vel=(D@R.T@np.r_[desired_world,0.])[:2]
                        prev=np.asarray(observation['previous_executed_action'],dtype=float)
                        max_d=self.slew_limits*dt
                        if body_vel[0]>action[0]:
                            action[0]=float(np.clip(body_vel[0],prev[0]-max_d[0],prev[0]+max_d[0]))
                            action[1]=float(np.clip(.6*body_vel[1]+.4*action[1],prev[1]-max_d[1],prev[1]+max_d[1]))
                        action[2]=float(np.clip(desired_vz,prev[2]-max_d[2],prev[2]+max_d[2]))
                if cphase in SEARCH_PHASES:
                    # Climb to (or hold) the search height whatever the distance
                    # to the last boat point; respect the mapped altitude ceiling.
                    prev=np.asarray(observation['previous_executed_action'],dtype=float)
                    max_dz=self.slew_limits[2]*dt
                    action[2]=float(np.clip(desired_vz,prev[2]-max_dz,prev[2]+max_dz))
                    clearance_map=observation.get('mission',{}).get('recovery_clearance',{}) or {}
                    top=clearance_map.get('max_altitude_enu_m') if clearance_map.get('valid') else None
                    if action[2]<0 and top is not None and math.isfinite(float(top)):
                        up=max(0.,float(own['velocity_enu_m_s'][2]))
                        if float(top)-float(position[2])<.25+up*up/(2*.5):action[2]=0.
                    diag['search_height_hold_m']=float(target_z)
            elif metric_ok and (diag.get('nearfield_descent_paused') or cphase in ('visibility_align','recover','match','descend')):
                clr=diag.get('estimated_clearance_m')
                lat=diag.get('estimated_lateral_error_m')
                # The base model pauses when the camera is not yet placed to
                # keep the pad in view to the end. Let it finish that for up to
                # 3 s; after that keep descending as before (a pause that never
                # ends in waves used to hover for 70 s).
                held=paused and t-self.pause_since<3.
                if held:
                    diag['nearfield_pause_respected_s']=float(t-self.pause_since)
                    self.g_log['pause_respected_s']=max(self.g_log['pause_respected_s'],float(t-self.pause_since))
                if not held and clr is not None and lat is not None and float(clr)<.85 and float(lat)<.16:
                    # Prevent 70s near-deck wave hover when clearance < 0.85m
                    prev=np.asarray(observation['previous_executed_action'],dtype=float)
                    max_dz=self.slew_limits[2]*dt
                    target_vz=.20 if float(clr)>.35 else .14
                    if action[2]<target_vz:
                        action[2]=float(np.clip(target_vz,prev[2]-max_dz,prev[2]+max_dz))

            diag.update(self._visual_evidence_dict(position,t),
                        search_identity_confirmed=True,boat_radio=False,handoff_latched=True,
                        selected_visual_track=self.selected)
            return action,diag

        selected,live=self._update_search(observation,position,yaw,R,D,rotation,focal,t)
        pan,tilt=observation['gimbal_rad']

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
                velocity=self.boat_velocity+.75*delta[:2]*max(0.,math.cos(error))
                norm=np.linalg.norm(velocity)
                if norm>2:velocity*=2/norm
                action[:2]=(D@R.T@np.r_[velocity,0.])[:2]
                self.last_velocity=velocity.copy()
                if self._needs_parallax(t):
                    # Sidestep ~1.2 m/s across the line of sight: a reflection
                    # moves with the drone, a real object does not.
                    action[1]=float(np.clip(action[1]+1.2,-2.,2.))
                    self.g_log['sidestep_s']+=dt
            phase='inspect' if live else 'reacquire_last_sensor_view'
            if not live:
                body_last=D@R.T@(self.last_point-position)
                action[4:]=[3*self.wrap(math.atan2(-body_last[1],body_last[0])-pan),
                            3*(math.atan2(body_last[2],np.linalg.norm(body_last[:2]))-tilt)]
                held=getattr(self,'last_velocity',None)
                if held is not None:
                    action[:2]=(D@R.T@np.r_[held*.85,0.])[:2]
                    action[2]=-float(np.clip(.4*(self.height-position[2]),-.5,.5))
                else:
                    action[2]=0.

        selected_visual_evidence={}
        if live is not None and selected==live.key and math.isfinite(float(live.range_m)):
            estimated_range=float(live.range_m)
            margin=.2*max(estimated_range,.5)
            selected_visual_evidence=dict(expert_intent=dict(selected_track=selected),
                expert_visual_tracks=[dict(track_id=selected,
                    range_interval_m=[max(0.,estimated_range-margin),estimated_range+margin])])
        elif selected and self.last_point is not None:
            selected_visual_evidence=self._visual_evidence_dict(position,t)

        if self.search.confirmed:
            self.landing_latched=True
            self.latched_since=t
            self.latch_samples=[];self.latch_metric_seen=False
            now_img=float(observation['image_delivery_time_s'])
            pose_policy=self._pose_policy()
            if getattr(pose_policy,'visual_motion_time',None) is None and self.last_point is not None and np.linalg.norm(self.boat_velocity)>0.05:
                pose_policy.visual_velocity_enu=np.r_[self.boat_velocity,0.]
                pose_policy.visual_boat_sample=(now_img,self.last_point.copy())
            candidate,diag=self.base.act(rgb,observation)
            diag['recovery_exhausted']=False
            diag.update(selected_visual_evidence or self._visual_evidence_dict(position,t),
                        search_identity_confirmed=True,boat_radio=False,
                        selected_visual_track=selected,handoff_latched=True)
            return candidate,diag

        if self.search.confirmed and not live:action[2]=0.
        norm=np.linalg.norm(action[:2])
        if norm>2:action[:2]*=2/norm
        action[2]=np.clip(action[2],-1,.7);action[3]=np.clip(action[3],-.5,.5)
        action,extra=self.guard.apply(action,observation,dict(pad_visibility_probability=0.))
        controlled=dict(observation,beacon=dict(valid=False,age_s=3.1,dock_ready=False))
        action,intervention=self.supervise(action,controlled,t,observation['mission']['budget_s'])
        if own.get('landed') or not own.get('armed'):action[:4]=0.
        return action,dict(self.search.diagnostics(),control_phase=phase,boat_radio=False,
            search_identity_confirmed=self.search.confirmed,intervention=intervention,
            **selected_visual_evidence,**extra)
