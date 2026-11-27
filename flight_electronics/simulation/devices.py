"""Device models between the world and the companion computer: camera stream, GCU, PX4 link."""
from __future__ import annotations

import io
import math
from collections import deque

import numpy as np

from ..companion import gcu, mavlink
from ..hardware import design as D


class CameraStream:
    """D-80Pro -> H.264 RTSP -> Ethernet -> hardware decode. Frames arrive late, some never."""

    BOOT_S = 25.0   # assumption: pod + encoder boot time after power returns

    def __init__(self, rng, latency_s=D.TIMING['camera_latency_s'], jitter_s=D.TIMING['camera_jitter_s'],
                 jpeg_quality: int | None = 80, drop_probability=0.002):
        self.rng, self.latency, self.jitter = rng, latency_s, jitter_s
        self.quality, self.drop = jpeg_quality, drop_probability
        self.queue = deque()
        self.powered_since = 0.0
        self.powered = True

    def power(self, on: bool, t: float):
        if on and not self.powered:
            self.powered_since = t
        if not on:
            self.queue.clear()
        self.powered = on

    def _compress(self, rgb):
        if self.quality is None:
            return rgb
        from PIL import Image
        buffer = io.BytesIO()
        Image.fromarray(rgb).save(buffer, 'JPEG', quality=self.quality)
        buffer.seek(0)
        return np.asarray(Image.open(buffer).convert('RGB'))

    def capture(self, rgb, t: float):
        if rgb is None or not self.powered or t - self.powered_since < (self.BOOT_S if self.powered_since else 0):
            return
        if self.rng.random() < self.drop:
            return
        arrive = t + self.latency + abs(self.rng.normal(0, self.jitter))
        self.queue.append((arrive, t, rgb))

    def newest(self, t: float):
        """Newest frame that has arrived by t: (rgb, capture_time) or (None, None)."""
        best = None
        while self.queue and self.queue[0][0] <= t:
            best = self.queue.popleft()
        if best is not None:
            self._last = (self._compress(best[2]), best[1])
        return getattr(self, '_last', (None, None))


class SimulatedGcu:
    """The gimbal control unit: speaks the private protocol, enforces the gimbal limits."""

    def __init__(self):
        self.mode = gcu.MODE_HEAD_LOCK
        self.yaw_rate = 0.0
        self.pitch_rate = 0.0
        self.packets = 0

    def receive(self, packet: bytes):
        """Accept a host packet; returns False when it is rejected (CRC, header)."""
        if len(packet) < 72 or packet[:2] != gcu.HOST_HEADER:
            return False
        if gcu.crc16(packet[:-2]) != int.from_bytes(packet[-2:], 'big'):
            return False
        import struct
        _, pitch, yaw, status = struct.unpack('<hhhB', packet[5:12])
        if packet[69] in (gcu.MODE_HEAD_LOCK, gcu.MODE_HEAD_FOLLOW, gcu.MODE_ANGLE, gcu.MODE_EULER):
            self.mode = packet[69]
        if status & 0x04 and self.mode in (gcu.MODE_HEAD_LOCK, gcu.MODE_HEAD_FOLLOW):
            limit = D.CAMERA['gimbal_rate_deg_s']
            self.pitch_rate = max(-limit, min(limit, pitch / 10))
            self.yaw_rate = max(-limit, min(limit, yaw / 10))
        self.packets += 1
        return True

    def reply(self, true_pan_rad, true_tilt_rad) -> bytes:
        yaw, pitch = gcu.tilt_pan_to_gcu(true_pan_rad, true_tilt_rad)
        yaw = (yaw + 180) % 360 - 180
        return gcu.gcu_packet(self.mode, (0.0, pitch, yaw), (0.0, pitch, yaw % 360),
                              (0.0, self.pitch_rate, self.yaw_rate))

    def realized_rates_rad_s(self, true_tilt_rad):
        """(pan_rate, tilt_rate) the gimbal will actually execute in project convention."""
        tilt_rate = -math.radians(self.pitch_rate)
        low, high = (-math.radians(D.CAMERA['gimbal_pitch_deg'][1]), -math.radians(D.CAMERA['gimbal_pitch_deg'][0]))
        if (true_tilt_rad <= low and tilt_rate < 0) or (true_tilt_rad >= high and tilt_rate > 0):
            tilt_rate = 0.0
        return math.radians(self.yaw_rate), tilt_rate


class Px4Link:
    """PX4 -> MAVLink 2 over TELEM2 (921600 baud) -> companion parser, and the setpoint path back."""

    def __init__(self, latency_s=D.TIMING['mavlink_latency_s']):
        self.encoder = mavlink.Encoder(system=1, component=1)
        self.parser = mavlink.Parser()
        self.companion_encoder = mavlink.Encoder(system=191, component=191)
        self.autopilot_parser = mavlink.Parser()
        self.latency = latency_s
        self.bytes_up = 0
        self.bytes_down = 0

    def telemetry(self, vehicle: dict, t: float) -> dict:
        ms = int(t * 1000)
        roll, pitch, yaw = vehicle['attitude_ned_rad']
        p, q, r = vehicle.get('angular_rate_frd_rad_s', (0, 0, 0))
        e, n, u = vehicle['position_enu_m']
        ve, vn, vu = vehicle['velocity_enu_m_s']
        stream = (self.encoder.encode(30, time_boot_ms=ms, roll=roll, pitch=pitch, yaw=yaw, rollspeed=p,
                                      pitchspeed=q, yawspeed=r) +
                  self.encoder.encode(32, time_boot_ms=ms, x=n, y=e, z=-u, vx=vn, vy=ve, vz=-vu) +
                  self.encoder.encode(245, vtol_state=0, landed_state=1 if vehicle.get('landed') else 2))
        self.bytes_up += len(stream)
        msgs = {m['_msgid']: m for m in self.parser.feed(stream)}
        att, pos, ext = msgs[30], msgs[32], msgs[245]
        return dict(valid=bool(vehicle.get('valid', True)),
                    position_enu_m=[pos['y'], pos['x'], -pos['z']],
                    velocity_enu_m_s=[pos['vy'], pos['vx'], -pos['vz']],
                    attitude_ned_rad=[att['roll'], att['pitch'], att['yaw']],
                    angular_rate_frd_rad_s=[att['rollspeed'], att['pitchspeed'], att['yawspeed']],
                    position_age_s=self.latency, attitude_age_s=self.latency,
                    armed=bool(vehicle.get('armed', True)), landed=ext['landed_state'] == 1)

    def setpoint(self, action, yaw_rad: float, t: float):
        """Encode the velocity setpoint and decode it on the autopilot side (what PX4 gets)."""
        frame = mavlink.velocity_setpoint(self.companion_encoder, action, yaw_rad, int(t * 1000))
        self.bytes_down += len(frame)
        message = self.autopilot_parser.feed(frame)[0]
        c, s = math.cos(yaw_rad), math.sin(yaw_rad)
        vn, ve = message['vx'], message['vy']
        return [vn * c + ve * s, -vn * s + ve * c, message['vz'], message['yaw_rate']]
