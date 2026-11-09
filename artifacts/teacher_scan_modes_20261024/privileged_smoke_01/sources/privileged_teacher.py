"""Simulator-assisted teacher with an explicit camera-observability boundary.

No learned detector is involved. Segmentation supplies exact *visible* boat
pixels, and truth supplies labels/ranges. Those annotations are not student
inputs. Hidden boats never reach the search controller. Identity supervision
is masked until the range, image size and sustained-view requirements pass.
"""
from dataclasses import asdict, dataclass
import math

import mujoco
import numpy as np

from .expert import Expert, camera_projection, pad_visibility, wrap


@dataclass(frozen=True)
class BoatView:
    key: str
    truth_class: str
    position: tuple
    range_m: float
    bbox: tuple
    pixels: int
    extent_px: float
    pad_visible: bool = False
    pad_extent_px: float = 0.

    @property
    def detectable(self):
        return self.pixels >= 24 and self.extent_px >= 8

    @property
    def evidence(self):
        # These are teaching rules, not probabilities from a neural network.
        if not self.detectable:
            return 'not_resolved'
        if self.range_m > 35 or self.pixels < 80 or self.extent_px < 24:
            return 'unknown_boat'
        if self.truth_class == 'false_boat_unsimilar':
            return 'different_boat'
        if self.range_m > 27:
            return 'target_or_similar'
        if self.truth_class == 'false_boat_similar':
            return 'different_boat'
        if self.pad_visible and self.pad_extent_px >= 6:
            return 'target_boat'
        return 'target_or_similar'

    def annotation(self):
        return dict(asdict(self), evidence=self.evidence,
                    boat_detection_valid=self.detectable,
                    identity_supervision_valid=self.evidence in ('different_boat', 'target_boat'))


class VisibleBoatOracle:
    """Exact instance pixels from the same rendered camera, including occlusion.

    The renderer must initialize ids on manually appended scenery/water. An
    object outside the image or fully hidden produces no BoatView at all.
    """
    def __init__(self, env, groups):
        self.env = env
        self.groups = groups

    def observe(self, segmentation):
        env = self.env
        ids = segmentation[:, :, 0]
        geom = segmentation[:, :, 1] == int(mujoco.mjtObj.mjOBJ_GEOM)
        views = []
        for key, gids in self.groups.items():
            ys, xs = np.where(geom & np.isin(ids, gids))
            if not len(xs):
                continue
            box = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            target = key == 'target'
            # A visible boat's reference point is permitted privileged geometry;
            # its identity remains masked by BoatView.evidence.
            point = env.pad_position if target else env.data.xpos[env.model.body(key).id] + [0, 0, .45]
            distance = float(np.linalg.norm(point[:2] - env.drone.position[:2]))
            visible, extent = False, 0.
            if target:
                visible, projected = pad_visibility(env)
                p = np.asarray(projected)
                extent = float(min(np.ptp(p[:, 0]), np.ptp(p[:, 1])))
            label = 'target_boat' if target else ('false_boat_unsimilar' if 'unsimilar' in key else 'false_boat_similar')
            views.append(BoatView(key, label, tuple(map(float, point)), distance, box,
                                  len(xs), float(max(box[2]-box[0], box[3]-box[1])), visible, extent))
        # Image order breaks simultaneous first-sighting ties, never true identity.
        return sorted(views, key=lambda v: v.bbox[0])


class SearchDecision:
    """Pure decision state; accepts current visible evidence, never the scene."""
    def __init__(self):
        self.mode = 'scan_1'
        self.selected = None
        self.confirmed = False
        self.rejected = set()
        self.first_seen = {}
        self.last_seen = {}
        self.support_start = {}
        self.coverage = 0.
        self.last_heading = None
        self.events = []
        self.phase = 'scan'

    def restart(self, t, reason):
        self.events.append(dict(time_s=t, event=reason, object=self.selected))
        self.selected = None
        self.confirmed = False
        self.mode = 'scan_1'
        self.coverage = 0.
        self.last_heading = None

    def decide(self, t, views, camera_heading, scan_settled):
        live = [v for v in views if v.detectable]
        for v in live:
            if t-self.last_seen.get(v.key, -100) > .12:
                self.support_start[v.key] = t
            self.last_seen[v.key] = t
            self.first_seen.setdefault(v.key, t)
        stable = [v for v in live if t-self.support_start[v.key] >= .16]
        for v in stable:
            if v.evidence == 'different_boat' and v.key not in self.rejected:
                self.rejected.add(v.key)
                self.events.append(dict(time_s=t, event='visually_rejected', object=v.key,
                                        range_m=v.range_m))
                if self.selected == v.key:
                    self.restart(t, 'inspection_rejected_restart_scan_1')
        eligible = [v for v in stable if v.key not in self.rejected]
        confirmed = next((v for v in eligible if v.evidence == 'target_boat'), None)
        ambiguous = next((v for v in eligible if v.evidence == 'target_or_similar'), None)
        chosen = confirmed or (ambiguous if not self.confirmed else None)
        # Mid-band evidence may interrupt a far unknown approach, but does not
        # make the teacher hop between equally plausible similar boats.
        current = next((v for v in eligible if v.key == self.selected), None)
        if chosen and (confirmed or self.selected is None or current is None or current.evidence == 'unknown_boat'):
            if self.selected != chosen.key:
                self.events.append(dict(time_s=t, event='visual_selection', object=chosen.key,
                                        evidence=chosen.evidence, mode=self.mode))
            self.selected = chosen.key
            self.confirmed = bool(confirmed)
        if self.selected is None:
            if self.mode == 'scan_2' and eligible:
                # First currently visible eligible boat. No hidden target ranking.
                chosen = min(eligible, key=lambda v: self.first_seen[v.key])
                self.selected = chosen.key
                self.events.append(dict(time_s=t, event='scan_2_first_boat', object=chosen.key))
            else:
                if scan_settled and self.last_heading is not None:
                    self.coverage += min(abs(wrap(camera_heading-self.last_heading)), .04)
                self.last_heading = camera_heading if scan_settled else None
                if self.coverage >= 2*math.pi:
                    self.mode = 'scan_2'
                    self.coverage = 0.
                    self.first_seen.clear()
                    self.events.append(dict(time_s=t, event='full_scan_1_enter_scan_2'))
        self.phase = 'target_land' if self.confirmed else ('inspect' if self.selected else 'scan')
        return self.selected

    def diagnostics(self):
        return dict(mode=self.mode, phase=self.phase, selected=self.selected,
                    confirmed=self.confirmed, coverage_deg=math.degrees(self.coverage),
                    rejected=sorted(self.rejected))


class PrivilegedTeacher:
    """No-radio search teacher. Truth is accessed only through visible views.

    Exact pad tracking by the established landing Expert is authorized only
    while the identified target's marker is visible, or on physical touchdown.
    A lost view stops translation/descent; camera reacquisition uses the last
    observed point, not the boat's new hidden location.
    """
    def __init__(self, env):
        self.env = env
        self.pilot = Expert(env)
        self.search = SearchDecision()
        self.height = None
        self.last_point = None
        self.last_visible = -100.
        self.last_selection = None
        self.selected_since = 0.

    def act(self, px4, observation, views):
        t = float(self.env.data.time)-self.env.task_start_time
        own = observation['px4']
        position = np.asarray(own['position_enu_m'])
        yaw = math.pi/2-own['attitude_ned_rad'][2]
        pan, tilt = observation['gimbal_rad']
        if self.height is None:
            self.height = float(position[2])
        settled = abs(pan) < math.radians(3) and abs(tilt-math.radians(6)) < math.radians(3)
        selected = self.search.decide(t, views, yaw+pan, settled)
        if selected != self.last_selection:
            self.last_point = None
            self.selected_since = t
            self.last_selection = selected
        live = next((v for v in views if v.key == selected and v.detectable), None)
        if live:
            self.last_point = np.asarray(live.position)
            self.last_visible = t
        v = np.array([0., 0., np.clip(.8*(self.height-position[2]), -.5, .5)])
        camera = np.array([-3*pan, 3*(math.radians(6)-tilt)])
        yaw_rate = .35 if settled else 0.
        reason = None
        if selected and self.last_point is not None:
            delta = self.last_point-position
            heading = math.atan2(delta[1], delta[0])
            yaw_rate = -wrap(heading-yaw)
            camera = self.pilot.camera_action(self.last_point)
            if live:
                alignment = max(0., math.cos(wrap(heading-yaw)))
                v[:2] = .65*delta[:2]*alignment
            else:
                self.search.phase = 'reacquire_last_view'
                if t-self.last_visible > 3:
                    self.search.restart(t, 'lost_view_restart_scan_1')
            if self.search.confirmed and live and live.pad_visible:
                # Read fresh privileged landing geometry only behind this gate.
                _, action, reason = self.pilot.act(px4, dict(valid=False, age_s=3.1, dock_ready=True), True)
                self.search.phase = self.pilot.phase
            elif self.search.confirmed and self.env.first_contact is not None:
                _, action, reason = self.pilot.act(px4, dict(valid=False, age_s=3.1, dock_ready=True), False)
                self.search.phase = self.pilot.phase
            else:
                action = self.pilot.bounded(self.pilot.heading_action(v, px4, yaw_rate, camera))
        else:
            action = self.pilot.bounded(self.pilot.heading_action(v, px4, yaw_rate, camera))
        if not own.get('valid') or max(own.get('position_age_s', 100), own.get('attitude_age_s', 100)) > .25:
            action[:4] = 0
            reason = 'estimator_unavailable_or_stale'
        diag = self.search.diagnostics()
        diag.update(control_phase=self.search.phase, actual_command_owner='privileged_visibility_gated_teacher',
                    expert_scan_mode=self.search.mode, metric_confirmed=bool(live and live.pad_visible and self.search.confirmed),
                    selected_range_m=None if live is None else live.range_m,
                    selected_evidence=None if live is None else live.evidence,
                    neural_network_used=False, intervention=reason)
        return action, diag
