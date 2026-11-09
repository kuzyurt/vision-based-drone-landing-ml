"""SX1262 boat-position link: 1 Hz packets of the boat deck, with age and dropouts.

The v60 review harness used to hand the policy a permanently invalid beacon, so
no review flight ever exercised the radio.  This module is the missing channel:
it mirrors the R15 development radio model (evaluate_development.SweepRadio) --
1 Hz sampling of the boat deck position, zero-mean Gaussian error with an
explicitly reported sigma, truth used only to synthesise the sensor, and an age
that grows between packets so a stale link is visible to the runtime.

The packet is a *sensor* reading, never a scoring field: the runtime receives
only the measured position, the reported sigma and its age.
"""
import json
import math
from pathlib import Path

import numpy as np

DEFAULT_SEED = 74131004
DEFAULT_SIGMA_M = 0.25          # SX1262 deck fix, 1 sigma
DEFAULT_REPORTED_SIGMA_M = 0.25
DEFAULT_PERIOD_S = 1.0          # 1 Hz position packets
DEFAULT_LATENCY_S = 0.0         # capture == receive unless a delay is declared
STALE_AFTER_S = 3.0             # runtime refuses older fixes
DEFAULT_VELOCITY_SIGMA_M_S = 0.025


def rotation_z(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])


class Sx1262BoatLink:
    """Deterministic, seeded link.  One instance per flight."""

    def __init__(self, log_path=None, *, seed=DEFAULT_SEED, sigma_m=DEFAULT_SIGMA_M,
                 reported_sigma_m=DEFAULT_REPORTED_SIGMA_M, period_s=DEFAULT_PERIOD_S,
                 latency_s=DEFAULT_LATENCY_S, dropout_start_s=-1.0,
                 dropout_duration_s=0.0, dock_ready=True):
        self.rng = np.random.default_rng(int(seed))
        self.sigma_m = float(sigma_m)
        self.reported_sigma_m = float(reported_sigma_m)
        self.period_s = float(period_s)
        self.latency_s = float(latency_s)
        self.dropout = (float(dropout_start_s), float(dropout_duration_s))
        self.dock_ready_default = bool(dock_ready)
        self.log_path = Path(log_path) if log_path is not None else None
        self.last_capture = -math.inf
        self.sequence = 0
        self.packet = None
        self.sent = 0
        self.delivered = 0
        self.valid_frames = 0
        self.dropped = 0

    # -- internal ---------------------------------------------------------
    def _dropout(self, capture_s):
        start, duration = self.dropout
        return duration > 0 and start <= capture_s < start + duration

    def _emit(self, capture_s, pad_position, pad_velocity):
        self.sequence += 1
        self.sent += 1
        error = self.rng.normal(size=3) * self.sigma_m
        velocity_error = self.rng.normal(0., DEFAULT_VELOCITY_SIGMA_M_S, 3)
        self.packet = dict(
            sequence=self.sequence,
            capture_time_s=float(capture_s),
            received_time_s=float(capture_s) + self.latency_s,
            position_enu_m=(np.asarray(pad_position, float) + error).tolist(),
            velocity_enu_m_s=(np.asarray(pad_velocity, float) + velocity_error).tolist(),
            position_sigma_m=self.reported_sigma_m,
        )
        dropped = self._dropout(capture_s)
        self.dropped += int(dropped)
        if self.log_path is not None:
            with self.log_path.open("a") as f:
                f.write(json.dumps(dict(
                    capture_time_s=float(capture_s), sequence=self.sequence,
                    error_enu_m=error.tolist(), velocity_error_m_s=velocity_error.tolist(),
                    reported_sigma_m=self.reported_sigma_m, dropped=dropped)) + "\n")
        return not dropped

    # -- public -----------------------------------------------------------
    def sample(self, now, *, pad_position, pad_velocity, own, dock_ready=None):
        """Return the beacon the aircraft would have in hand at ``now``."""
        now = float(now)
        if self.packet is None or now - self.last_capture >= self.period_s:
            delivered = self._emit(now, pad_position, pad_velocity)
            self.last_capture = now
            if delivered:
                self.delivered += 1
            else:
                self.packet = None
        if self.packet is None:
            beacon = dict(valid=False, age_s=STALE_AFTER_S, sequence=0,
                          dock_ready=False, dock_status_valid=False)
        else:
            age = now - self.packet["received_time_s"]
            valid = bool(own.get("valid")) and 0. <= age < STALE_AFTER_S
            beacon = dict(valid=valid, age_s=float(max(age, 0.)),
                          sequence=int(self.packet["sequence"]),
                          dock_ready=bool(self.dock_ready_default if dock_ready is None else dock_ready),
                          dock_status_valid=valid)
            if valid:
                yaw = math.pi / 2. - float(own["attitude_ned_rad"][2])
                relative = rotation_z(yaw).T @ (
                    np.asarray(self.packet["position_enu_m"]) - np.asarray(own["position_enu_m"]))
                velocity = rotation_z(yaw).T @ np.asarray(self.packet["velocity_enu_m_s"])
                beacon["relative_heading_m"] = (relative * [1., -1., -1.]).tolist()
                beacon["velocity_heading_m_s"] = (velocity * [1., -1., -1.]).tolist()
                beacon["position_sigma_m"] = self.packet["position_sigma_m"]
                beacon["velocity_sigma_m_s"] = DEFAULT_VELOCITY_SIGMA_M_S
        self.valid_frames += int(beacon["valid"])
        return beacon

    def stats(self):
        return dict(mode="sx1262_1hz", packets_sent=self.sent, packets_delivered=self.delivered,
                    packets_dropped=self.dropped, valid_frames=self.valid_frames,
                    sigma_m=self.sigma_m, reported_sigma_m=self.reported_sigma_m,
                    period_s=self.period_s, latency_s=self.latency_s,
                    dropout_window_s=list(self.dropout))


def absent_beacon():
    """The radio-off beacon, byte-identical to the one every past flight used."""
    return dict(valid=False, age_s=3.1, sequence=0, dock_ready=False, dock_status_valid=False)
