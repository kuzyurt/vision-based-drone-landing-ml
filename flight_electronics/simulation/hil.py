"""Hardware simulation of the flight electronics, independent of any particular world.

A world simulator (or a replay) hands a ``WorldSample`` to ``sense`` each
control tick and gets back what the companion computer would really see. The
caller runs its policy on that view and hands the action to ``actuate``, which
returns what PX4 and the gimbal really receive, and when. In between:

* power: averaged SPICE model of the whole supply in lockstep (ngspice),
* camera: RTSP latency, jitter, compression, drops, brown-out and reboot,
* PX4 link: real MAVLink 2 bytes both ways,
* gimbal: real GCU private-protocol packets, GCU limits,
* boat radio: LoRa channel + the real ESP32 firmware (host build) + UART frames,
* compute: RK3588S NPU/CPU timing, deadline misses hold the previous command.

Nothing here imports or knows about a specific simulator.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..companion import gcu
from ..companion.radio_link import RadioLink, encode_beacon
from ..companion.timing import Rk3588Timing
from ..hardware import design as D
from .devices import CameraStream, Px4Link, SimulatedGcu
from .electrical.power_system import PowerDemand, PowerSystem, propulsion_power_w
from .radio import LoraChannel, RadioBridgeDevice

G = 9.80665


@dataclass
class HilConfig:
    seed: int = 0
    variant: str = 'carrier'             # 'carrier' or 'camera_on_battery'
    state_of_charge: float = 1.0
    mass_kg: float = 2.12                # 2.066 kg model + Orange Pi 5, heat sink, carrier board
    camera_latency_s: float = D.TIMING['camera_latency_s']
    jpeg_quality: int | None = 80
    native_marker_kernel: bool = True
    electrical: bool = True
    radio_firmware: bool = True


@dataclass
class WorldSample:
    time_s: float
    camera_rgb: np.ndarray | None
    vehicle: dict                        # flight-controller estimate (ENU position/velocity, NED attitude)
    gimbal_true_rad: tuple               # (pan, tilt) actual gimbal angles
    boat_packet: dict | None = None      # position_enu_m, velocity_enu_m_s, send_time_s, distance_m, ...
    total_thrust_n: float | None = None


@dataclass
class CompanionView:
    frame: np.ndarray | None
    observation: dict
    soc_running: bool
    diagnostics: dict = field(default_factory=dict)


@dataclass
class Actuation:
    action: np.ndarray                   # what PX4 + gimbal execute this tick (6 values)
    applied_from_this_tick: bool
    latency_s: float
    deadline_met: bool


class FlightElectronics:
    def __init__(self, config: HilConfig = HilConfig()):
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.camera = CameraStream(self.rng, latency_s=config.camera_latency_s, jpeg_quality=config.jpeg_quality)
        self.px4 = Px4Link()
        self.gcu = SimulatedGcu()
        self.timing = Rk3588Timing(self.rng, native_marker_kernel=config.native_marker_kernel)
        self.channel = LoraChannel(self.rng)
        self.radio = RadioBridgeDevice() if config.radio_firmware else None
        self.link = RadioLink()
        self.power = PowerSystem(config.variant, config.state_of_charge) if config.electrical else None
        self.previous_action = np.zeros(6)
        self.pending = None
        self.last_fix = None
        self.last_velocity = None
        self.last_time = None
        self.power_state = None
        self.log: list[dict] = []
        self.events: list[tuple] = []
        self._yaw = 0.0
        self._true_gimbal = (0.0, 0.0)
        self._soc_up = True

    def close(self):
        if self.power:
            self.power.close()
        if self.radio:
            self.radio.close()

    # ------------------------------------------------------------------ sense
    def _thrust(self, world: WorldSample) -> float:
        if world.total_thrust_n is not None:
            return world.total_thrust_n
        v = np.asarray(world.vehicle['velocity_enu_m_s'], float)
        accel = np.zeros(3)
        if self.last_velocity is not None and world.time_s > self.last_time:
            accel = (v - self.last_velocity) / (world.time_s - self.last_time)
        self.last_velocity, self.last_time = v, world.time_s
        if world.vehicle.get('landed'):
            return 0.0
        return self.config.mass_kg * float(np.linalg.norm(accel + [0, 0, G]))

    def _power(self, world: WorldSample, thrust: float):
        if not self.power:
            return None
        demand = PowerDemand(
            propulsion_w=propulsion_power_w(thrust) if world.vehicle.get('armed', True) else 0.0,
            soc_w=D.SOC_POWER['inference_w'] if self._soc_up else 0.5,
            radio_w=self.radio.power_w() if self.radio else 0.25,
            camera_w=D.CAMERA['pod_avg_w'] + D.CAMERA['gcu_w'] + 0.02 * (abs(self.gcu.yaw_rate) + abs(self.gcu.pitch_rate)))
        state = self.power.step(world.time_s, demand)
        for event in state.events:
            self.events.append((world.time_s, event))
        return state

    def sense(self, world: WorldSample) -> CompanionView:
        t = world.time_s
        self._true_gimbal = tuple(world.gimbal_true_rad)
        thrust = self._thrust(world)
        self.power_state = self._power(world, thrust)
        camera_ok = self.power_state.camera_powered if self.power_state else True
        self._soc_up = self.power_state.soc_powered if self.power_state else True
        self.camera.power(camera_ok, t)
        self.camera.capture(world.camera_rgb, t)
        frame, capture = self.camera.newest(t)
        px4 = self.px4.telemetry(world.vehicle, t)
        self._yaw = px4['attitude_ned_rad'][2]
        reply = gcu.parse_gcu(self.gcu.reply(*world.gimbal_true_rad))
        pan, tilt = gcu.gcu_to_tilt_pan(reply.relative_deg[2], reply.relative_deg[1])
        beacon = self._radio(world)
        valid = frame is not None and capture is not None and camera_ok
        observation = dict(
            px4=px4, gimbal_rad=[pan, tilt], gimbal_source='GCU private protocol encoder angles',
            image_capture_time_s=capture if valid else t, image_delivery_time_s=t,
            image_age_s=(t - capture) if valid else 10.0, image_valid=bool(valid),
            decision_dt_s=1 / D.TIMING['control_hz'], previous_executed_action=self.previous_action.tolist())
        if beacon is not None:
            observation['beacon'] = beacon
        diagnostics = dict(camera_powered=camera_ok, soc_powered=self._soc_up,
                           image_age_s=observation['image_age_s'], thrust_n=thrust)
        if self.power_state:
            diagnostics.update(battery_v=self.power_state.battery_v, rail_5v=self.power_state.rail_5v,
                               camera_v=self.power_state.camera_v, state_of_charge=self.power_state.state_of_charge)
        self._last_diag = diagnostics
        return CompanionView(frame if valid else None, observation, self._soc_up, diagnostics)

    def _radio(self, world: WorldSample):
        t = world.time_s
        packet = world.boat_packet
        if packet is not None and self.radio is not None:
            payload = encode_beacon(packet.get('sequence', 0), packet['send_time_s'], packet['position_enu_m'],
                                    packet['velocity_enu_m_s'], packet.get('dock_ready', True),
                                    packet.get('dock_status_valid', True), packet.get('position_sigma_m', .25))
            delivered, rssi, snr = self.channel.receive(packet.get('distance_m', 50.0))
            if delivered:
                self.radio.on_air(payload, packet['send_time_s'], rssi, snr)
        if self.radio is not None:
            for fix in self.link.feed(self.radio.run_until(t)):
                self.last_fix = fix
        elif packet is not None:
            self.last_fix = packet
        if self.last_fix is None:
            return None
        fix = self.last_fix
        if isinstance(fix, dict):
            return dict(valid=True, age_s=t - fix['send_time_s'], position_enu_m=list(fix['position_enu_m']),
                        velocity_enu_m_s=list(fix['velocity_enu_m_s']), position_sigma_m=.25,
                        dock_ready=True, dock_status_valid=True, rssi_dbm=None)
        return dict(valid=True, age_s=t - fix.boat_time_s, position_enu_m=list(fix.position_enu_m),
                    velocity_enu_m_s=list(fix.velocity_enu_m_s), position_sigma_m=fix.position_sigma_m,
                    dock_ready=fix.dock_ready, dock_status_valid=fix.dock_status_valid, rssi_dbm=fix.rssi_dbm)

    # ---------------------------------------------------------------- actuate
    def actuate(self, action, marker: str = 'cold') -> Actuation:
        """Pass the policy's action through compute timing, MAVLink and the GCU."""
        action = np.asarray(action, float)
        if not self._soc_up:
            held = np.zeros(6)   # companion down: PX4 offboard loss -> hold position
            self.previous_action = held
            return Actuation(held, False, float('inf'), False)
        timing = self.timing.step(marker)
        period = 1 / D.TIMING['control_hz']
        on_time = timing.latency_s + self.px4.latency <= period
        if on_time:
            chosen = action
        else:
            # This decision misses the tick: the previous command is still executing.
            chosen = self.pending if self.pending is not None else self.previous_action
            self.pending = action
        velocity = self.px4.setpoint(chosen, self._yaw, len(self.log) * period)
        carrier = gcu.CarrierState(*(math.degrees(a) for a in (0.0, 0.0, self._yaw)))
        pitch_cmd, yaw_cmd = -math.degrees(chosen[5]), math.degrees(chosen[4])
        self.gcu.receive(gcu.head_lock_rates(pitch_cmd, yaw_cmd, carrier))
        pan_rate, tilt_rate = self.gcu.realized_rates_rad_s(self._true_gimbal[1])
        executed = np.array([*velocity, pan_rate, tilt_rate])
        self.previous_action = executed
        record = dict(latency_s=timing.latency_s, deadline=timing.deadline_met, on_time=on_time,
                      **{k: v for k, v in self._last_diag.items() if isinstance(v, (int, float, bool))})
        self.log.append(record)
        return Actuation(executed, on_time, timing.latency_s, timing.deadline_met)

    def summary(self) -> dict:
        if not self.log:
            return {}
        latency = np.array([r['latency_s'] for r in self.log])
        ages = np.array([r['image_age_s'] for r in self.log if r.get('image_age_s', 10) < 10])
        out = dict(steps=len(self.log), latency_ms_median=float(np.median(latency) * 1000),
                   latency_ms_p95=float(np.percentile(latency, 95) * 1000),
                   late_decisions=int(sum(not r['on_time'] for r in self.log)),
                   image_age_ms_median=float(np.median(ages) * 1000) if len(ages) else None,
                   events=self.events)
        if self.power_state:
            v = [r['battery_v'] for r in self.log if 'battery_v' in r]
            out.update(battery_v_min=float(min(v)) if v else None, state_of_charge_end=self.power_state.state_of_charge,
                       camera_v_min=float(min(r['camera_v'] for r in self.log if 'camera_v' in r)))
        if self.radio:
            out['radio'] = self.radio.counters()
        return out
