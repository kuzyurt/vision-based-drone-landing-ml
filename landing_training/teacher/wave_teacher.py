"""Wave-aware privileged teacher variant.

The frozen teacher keeps its original search and landing controller. This
module only changes the descent decision: the high-altitude gate is scaled by
clearance, and a bounded probe descent is allowed when the deck motion keeps
the strict hover gate from ever holding. The final metre remains tight.
"""
import math

from .privileged_teacher import PrivilegedTeacher
from .smooth_landing import SmoothLandingExpert


class WaveDescentGate:
    """Clearance-scaled descent gate with bounded probe windows.

    The original gate asks for 9 cm / 0.12 m/s / 5 deg / 8 deg for 0.6 s even
    several metres above a moving deck. Short waves move the hover point by
    more than that, so the gate never holds. This gate relaxes only the
    high-altitude entry and confirms the final metre with the original values.
    """

    def __init__(self):
        self.active = False
        self.settled_s = 0.0
        self.probe_s = 0.0
        self.cooldown_s = 0.0
        self.probes = 0
        self.probing = False
        self.force = False

    @staticmethod
    def limits(clearance):
        """entry, exit, speed_ready, speed_safe, heading_ready_deg,
        heading_safe_deg, tilt_ready_deg, tilt_safe_deg, dwell_s.

        The low window is deliberately wider than the original final-metre
        gate: a moving deck can leave a small lateral offset while the tight
        speed/tilt combination never holds. The final 18 cm is handled
        separately as a bounded terminal window below.
        """
        if clearance > 3.0:
            return 0.25, 0.40, 0.18, 0.30, 8.0, 12.0, 10.0, 12.0, 0.20
        if clearance > 1.0:
            return 0.15, 0.25, 0.15, 0.25, 6.0, 10.0, 9.0, 10.0, 0.40
        if clearance > 0.20:
            return 0.18, 0.30, 0.25, 0.40, 8.0, 12.0, 10.0, 12.0, 0.25
        entry = 0.06 if clearance < 0.8 else 0.09
        exit_ = 0.10 if clearance < 0.8 else 0.16
        return entry, exit_, 0.12, 0.28, 5.0, 12.0, 8.0, 10.0, 0.60

    def reset(self):
        self.active = False
        self.settled_s = 0.0
        self.probe_s = 0.0
        self.probing = False
        self.cooldown_s = 0.0

    def update(self, dt, error, speed, heading_error, tilt, visible, clearance):
        if not visible:
            self.reset()
            return False

        # Once the aircraft is within 18 cm, finish the physical descent
        # instead of oscillating on a strict hover gate. The target is already
        # identified and the camera/marker gate remains active; this is not a
        # search shortcut.
        if (clearance < 0.18 and error < 0.18 and speed < 0.35
                and abs(heading_error) < math.radians(12.0)
                and tilt < math.radians(12.0)):
            self.active = True
            self.probing = False
            return True

        entry, exit_, speed_ready, speed_safe, heading_ready, heading_safe, tilt_ready, tilt_safe, dwell = self.limits(clearance)
        safe = (error < exit_ and speed < speed_safe
                and abs(heading_error) < math.radians(heading_safe)
                and tilt < math.radians(tilt_safe))
        if not safe:
            self.active = False
            self.settled_s = 0.0
            self.probing = False
            self.probe_s = 0.0
            self.cooldown_s = max(0.0, self.cooldown_s - dt)
            return False

        # A probe already in progress is allowed to finish its short window as
        # long as the wider safe envelope still holds.
        if self.probing:
            self.probe_s += dt
            if self.probe_s <= 2.5:
                self.active = True
                return True
            self.probing = False
            self.probe_s = 0.0
            self.cooldown_s = 1.0
            self.probes += 1
            self.active = False
            return False

        ready = (error < entry and speed < speed_ready
                 and abs(heading_error) < math.radians(heading_ready)
                 and tilt < math.radians(tilt_ready))
        if ready:
            self.settled_s += dt
            if self.settled_s >= dwell:
                self.active = True
                return True
        else:
            self.settled_s = 0.0

        # High above the deck, a bounded probe converts a perfect-hover
        # requirement into a stepped descent. Below 1.2 m the original tight
        # gate owns the final approach.
        self.cooldown_s = max(0.0, self.cooldown_s - dt)
        probe_error = 0.40 if self.force else 0.25
        probe_speed = 0.35 if self.force else 0.30
        if (clearance > 0.20 and self.cooldown_s <= 0.0
                and error < probe_error and speed < probe_speed
                and abs(heading_error) < math.radians(12.0)
                and tilt < math.radians(12.0)):
            self.probing = True
            self.probe_s = dt
            self.active = True
            return True

        self.active = False
        return False


class WaveLandingExpert(SmoothLandingExpert):
    """The original landing controller with only the descent gate replaced."""

    def __init__(self, env):
        super().__init__(env)
        self.gate = WaveDescentGate()
        self._best_clearance = None
        self._progress_time = 0.0
        self._last_time = None

    def act(self, px4, beacon, visible):
        env = self.env
        now = float(env.data.time)
        if self._last_time is None:
            self._last_time = now
        dt = max(0.0, now - self._last_time)
        self._last_time = now

        # No-progress pressure: if the confirmed target is held but the
        # clearance has not improved by 0.5 m in 20 s, widen the probe
        # envelope enough to step down instead of hovering to the timeout.
        if self.landing_active and visible:
            clearance = float(env.vertical_clearance)
            if self._best_clearance is None or clearance < self._best_clearance - 0.5:
                self._best_clearance = clearance
                self._progress_time = now
            if now - self._progress_time > 20.0 and clearance > 1.2:
                self.gate.force = True
            else:
                self.gate.force = False

        return super().act(px4, beacon, visible)


class WavePrivilegedTeacher(PrivilegedTeacher):
    """The frozen teacher's search and visibility rules, wave-aware landing."""

    def __init__(self, env):
        super().__init__(env)
        self.pilot = WaveLandingExpert(env)
