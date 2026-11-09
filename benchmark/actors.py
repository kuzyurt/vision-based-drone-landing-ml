"""The privileged reference is explicit; student runtimes never receive this API."""
import math
import numpy as np


class LegacyMetricAdapter:
    """The old controller's metric_valid already means an accepted marker fit.

    Preserve explicit modern confirmation, and expose the equivalent legacy
    acceptance flag to the shared mission guard. No pose/confidence is invented.
    """
    def __init__(self, actor):
        self.actor=actor

    def __getattr__(self, name):
        return getattr(self.actor,name)

    def reset(self):
        self.actor.reset()

    def act(self, rgb, observation):
        action, diagnostics=self.actor.act(rgb,observation)
        diagnostics=dict(diagnostics)
        if 'metric_confirmed' not in diagnostics and 'metric_valid' in diagnostics:
            diagnostics['metric_confirmed']=bool(diagnostics['metric_valid'])
            diagnostics['metric_confirmation_source']='legacy accepted metric fit'
        return action,diagnostics


class PrivilegedReference:
    def __init__(self, env, px4, renderer, groups):
        self.env, self.px4, self.renderer, self.groups = env, px4, renderer, groups
        self.reset()

    def reset(self):
        from landing_training.privileged_teacher import PrivilegedTeacher, VisibleBoatOracle
        self.teacher = PrivilegedTeacher(self.env)
        self.oracle = VisibleBoatOracle(self.env, self.groups)

    def act(self, rgb, observation):
        # Re-render the identical RGB scene without advancing physics. The
        # instance labels and simulator API are private to this teacher actor.
        camera = self.renderer.onboard
        camera.enable_segmentation_rendering()
        try:
            segmentation = camera.render().copy()
        finally:
            camera.disable_segmentation_rendering()
        views = self.oracle.observe(segmentation)
        action, diagnostics = self.teacher.act(self.px4, observation, views)
        diagnostics['privileged_reference'] = True
        diagnostics['metric_valid'] = diagnostics['metric_confirmed']
        selected = diagnostics.get('selected')
        diagnostics['expert_intent'] = dict(selected_track=selected)
        diagnostics['expert_visual_tracks'] = [dict(track_id=v.key,
            range_interval_m=[max(0., v.range_m-.01), v.range_m+.01]) for v in views if v.detectable]
        if diagnostics['metric_confirmed']:
            own = observation['px4']
            yaw = math.pi/2-own['attitude_ned_rad'][2]
            c, s = math.cos(yaw), math.sin(yaw)
            rotation = np.array([[c,-s,0],[s,c,0],[0,0,1.]])
            relative = self.env.pad_position-np.asarray(own['position_enu_m'])
            diagnostics.update(estimated_relative_position=((rotation.T@relative)*[1,-1,-1]).tolist(),
                estimated_clearance_m=float(self.env.clearance),
                estimated_lateral_error_m=float(np.linalg.norm((self.env.pad_rotation.T@
                    (self.env.drone.position-self.env.pad_position))[:2])))
        return action, diagnostics
