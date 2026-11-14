"""Pure evidence-ordering search state used by the browser student."""
import math
import numpy as np

def wrap(angle):
    return (float(angle)+math.pi) % (2*math.pi)-math.pi

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
        self.diff_start = {}
        self.positive_frames = {}
        self.diff_frames = {}
        self.coverage = 0.
        self.sweep_angle = 0.
        self.last_heading = None
        self.events = []
        self.phase = 'scan'
        self.warning = None
        self.warning_time_s = None
        self.scan_passes_completed = 0

    def restart(self, t, reason):
        self.events.append(dict(time_s=t, event=reason, object=self.selected))
        self.selected = None
        self.confirmed = False
        # Do not revert to scan_1 (which ignores unknown_boat for a full 360 deg)
        # once the mission is underway or a pass was already completed.
        if self.scan_passes_completed >= 1 or float(t) >= 18.:
            self.mode = 'scan_2'
        else:
            self.mode = 'scan_1'
        self.coverage = 0.
        self.sweep_angle = 0.
        self.last_heading = None

    def decide(self, t, views, camera_heading, scan_settled):
        live = [v for v in views if v.detectable]
        for v in live:
            if t-self.last_seen.get(v.key, -100) > .20:
                self.support_start[v.key] = t
                self.diff_start.pop(v.key, None)
            self.last_seen[v.key] = t
            self.first_seen.setdefault(v.key, t)
            if v.evidence in ('target_boat', 'target_or_similar'):
                self.positive_frames[v.key] = self.positive_frames.get(v.key, 0) + 1
                self.diff_start.pop(v.key, None)
            elif v.evidence == 'different_boat':
                self.diff_frames[v.key] = self.diff_frames.get(v.key, 0) + 1
                self.diff_start.setdefault(v.key, t)
            else:
                self.diff_start.pop(v.key, None)

        stable = [v for v in live if t-self.support_start[v.key] >= .12]
        for v in stable:
            if v.evidence == 'different_boat' and v.key not in self.rejected:
                diff_dur = t - self.diff_start.get(v.key, t)
                pos_cnt = self.positive_frames.get(v.key, 0)
                dif_cnt = self.diff_frames.get(v.key, 0)
                # Require sustained 'different_boat' evidence (>= 0.60s) and more
                # negative than positive frames before rejecting an inspected boat.
                required_dur = .60 if self.selected == v.key else .28
                if diff_dur >= required_dur and dif_cnt > pos_cnt + 4:
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
            can_pick_unknown = (self.mode in ('scan_2', 'scan_3')
                                or self.coverage >= .75 * math.pi
                                or float(t) >= 18.)
            if can_pick_unknown and eligible:
                # Prefer nearest/earliest currently visible eligible boat.
                chosen = min(eligible, key=lambda v: (self.first_seen[v.key], v.range_m))
                self.selected = chosen.key
                self.events.append(dict(time_s=t, event=self.mode+'_first_boat', object=chosen.key))
            else:
                if scan_settled and self.last_heading is not None:
                    self.sweep_angle += float(np.clip(wrap(camera_heading-self.last_heading), -.04, .04))
                    self.coverage = abs(self.sweep_angle)
                self.last_heading = camera_heading if scan_settled else None
                if self.coverage >= 2*math.pi:
                    completed = self.mode
                    self.scan_passes_completed += 1
                    if completed == 'scan_1':
                        self.mode = 'scan_2'
                    elif completed == 'scan_2':
                        self.mode = 'scan_3'
                    elif self.warning is None:
                        self.warning = 'boat_search_exhausted'
                        self.warning_time_s = float(t)
                        self.events.append(dict(time_s=t, event=self.warning,
                                                severity='warning', terminal=False,
                                                completed_passes=3))
                    self.coverage = 0.
                    self.sweep_angle = 0.
                    self.first_seen.clear()
                    self.events.append(dict(time_s=t, event='full_'+completed,
                                            next_mode=self.mode))
        self.phase = 'target_land' if self.confirmed else ('inspect' if self.selected else 'scan')
        return self.selected

    def diagnostics(self):
        return dict(mode=self.mode, phase=self.phase, selected=self.selected,
                    confirmed=self.confirmed, coverage_deg=math.degrees(self.coverage),
                    rejected=sorted(self.rejected), warning_code=self.warning,
                    warning_time_s=self.warning_time_s, warning_terminal=False,
                    scan_passes_completed=self.scan_passes_completed)



