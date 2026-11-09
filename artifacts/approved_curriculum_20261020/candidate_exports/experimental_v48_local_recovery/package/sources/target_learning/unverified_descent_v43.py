"""Observable sustained landing on an UNVERIFIED object; not oracle identity."""
class UnverifiedDescent:
    def __init__(self):self.reset()
    def reset(self):self.first_height=None;self.started=None;self.threshold_since=None;self.last_capture=None;self.last_stamp=None;self.captures=0;self.evidence={}
    def step(self,e,context):
        o=context['observation'];p=o['px4'];ld=context['learner'];action=context['action'];age=ld.get('metric_age_s');fresh=bool(e.image_valid and e.image_age_s<=.25 and e.own_state_valid);airborne=bool(p.get('armed')and not p.get('landed'));metric=bool(ld.get('metric_confirmed')and age is not None and age<=.16)
        if e.target_confirmed or not fresh or not airborne or not metric:self.reset();return False
        if e.frame_id==self.last_capture:return False
        stamp=e.frame_id/1e6
        if self.last_stamp is not None and stamp-self.last_stamp>.25:self.reset()
        self.last_capture=e.frame_id;self.last_stamp=stamp
        moving_down=bool(action is not None and float(action[2])>.02 and context['own_vertical_speed']<-.10)
        if not moving_down:self.first_height=None;self.started=None;self.threshold_since=None;self.captures=0;return False
        now=e.time_s;height=context['own_height']
        if self.started is None:self.started=now;self.first_height=height
        self.captures+=1;drop=max(0.,self.first_height-height)
        qualifying=drop>=1.0 and now-self.started>=3.0 and self.captures>=10
        self.threshold_since=(now if self.threshold_since is None else self.threshold_since)if qualifying else None
        duration=0. if self.threshold_since is None else now-self.threshold_since
        self.evidence=dict(reason='sustained_actual_descent_without_target_identity',actual_height_loss_m=drop,observed_descent_s=now-self.started,distinct_capture_count=self.captures,after_one_metre_threshold_s=duration,learner_geometry_fresh=True,teacher_design_identity_confirmed=False,actual_own_vertical_speed=context['own_vertical_speed'],requested_down_m_s=float(action[2]),does_not_claim_wrong_identity=True)
        return duration>=2.0
