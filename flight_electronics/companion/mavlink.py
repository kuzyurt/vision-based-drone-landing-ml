"""Minimal MAVLink 2 for the companion <-> PX4 link (TELEM2, 921600 baud).

Only the messages this system uses. Byte layout and CRC_EXTRA values follow the
MAVLink common.xml definitions; the unit tests compare every message with
pymavlink when it is installed.
"""
from __future__ import annotations

import math
import struct

# msgid: (struct format with fields sorted by size as MAVLink requires, CRC_EXTRA, field names)
MESSAGES = {
    0: ('<IBBBBB', 50, ('custom_mode', 'type', 'autopilot', 'base_mode', 'system_status', 'mavlink_version')),
    30: ('<Iffffff', 39, ('time_boot_ms', 'roll', 'pitch', 'yaw', 'rollspeed', 'pitchspeed', 'yawspeed')),
    32: ('<Iffffff', 185, ('time_boot_ms', 'x', 'y', 'z', 'vx', 'vy', 'vz')),
    84: ('<IfffffffffffHBBB', 143, ('time_boot_ms', 'x', 'y', 'z', 'vx', 'vy', 'vz', 'afx', 'afy', 'afz',
                                    'yaw', 'yaw_rate', 'type_mask', 'target_system', 'target_component',
                                    'coordinate_frame')),
    245: ('<BB', 130, ('vtol_state', 'landed_state')),
}
NAMES = {0: 'HEARTBEAT', 30: 'ATTITUDE', 32: 'LOCAL_POSITION_NED', 84: 'SET_POSITION_TARGET_LOCAL_NED',
         245: 'EXTENDED_SYS_STATE'}
MAV_FRAME_LOCAL_NED = 1
# Use vx, vy, vz and yaw_rate; ignore position, acceleration and yaw.
VELOCITY_YAWRATE_MASK = 0b0000_0101_1100_0111
LANDED_ON_GROUND = 1


def x25(data: bytes, crc: int = 0xFFFF) -> int:
    for byte in data:
        tmp = byte ^ (crc & 0xFF)
        tmp = (tmp ^ (tmp << 4)) & 0xFF
        crc = ((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF
    return crc


class Encoder:
    def __init__(self, system=191, component=191):
        self.system, self.component, self.sequence = system, component, 0

    def encode(self, msgid: int, **fields) -> bytes:
        fmt, extra, names = MESSAGES[msgid]
        payload = struct.pack(fmt, *(fields[name] for name in names)).rstrip(b'\x00') or b'\x00'
        header = struct.pack('<BBBBBBB', len(payload), 0, 0, self.sequence & 0xFF, self.system, self.component,
                             msgid & 0xFF) + struct.pack('<H', msgid >> 8)
        self.sequence += 1
        crc = x25(header + payload)
        crc = x25(bytes([extra]), crc)
        return b'\xfd' + header + payload + struct.pack('<H', crc)


class Parser:
    def __init__(self):
        self.buffer = bytearray()
        self.errors = 0

    def feed(self, data: bytes):
        self.buffer += data
        out = []
        while True:
            start = self.buffer.find(b'\xfd')
            if start < 0:
                self.buffer.clear()
                return out
            del self.buffer[:start]
            if len(self.buffer) < 12:
                return out
            length = self.buffer[1]
            total = 12 + length
            if len(self.buffer) < total:
                return out
            frame = bytes(self.buffer[:total])
            msgid = frame[7] | (frame[8] << 8) | (frame[9] << 16)
            if msgid not in MESSAGES:
                del self.buffer[:1]
                continue
            fmt, extra, names = MESSAGES[msgid]
            crc = x25(bytes([extra]), x25(frame[1:10 + length]))
            if crc != struct.unpack('<H', frame[-2:])[0]:
                self.errors += 1
                del self.buffer[:1]
                continue
            del self.buffer[:total]
            payload = frame[10:10 + length].ljust(struct.calcsize(fmt), b'\x00')
            values = dict(zip(names, struct.unpack(fmt, payload)))
            values['_msgid'] = msgid
            values['_sysid'] = frame[5]
            out.append(values)


def velocity_setpoint(encoder: Encoder, action, yaw_rad: float, time_boot_ms: int, target=(1, 1)) -> bytes:
    """Policy action [forward, right, down, yaw_rate, ...] -> SET_POSITION_TARGET_LOCAL_NED."""
    forward, right, down, yaw_rate = (float(v) for v in action[:4])
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    return encoder.encode(84, time_boot_ms=time_boot_ms & 0xFFFFFFFF, x=0.0, y=0.0, z=0.0,
                          vx=forward * c - right * s, vy=forward * s + right * c, vz=down,
                          afx=0.0, afy=0.0, afz=0.0, yaw=0.0, yaw_rate=yaw_rate,
                          type_mask=VELOCITY_YAWRATE_MASK, target_system=target[0], target_component=target[1],
                          coordinate_frame=MAV_FRAME_LOCAL_NED)
