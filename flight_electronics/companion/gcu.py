"""ALLXF GCU private protocol V2.0.6 (D-80Pro gimbal control unit).

Host packet: A8 E5, u16 length, u8 version, 32-byte main frame, 32-byte sub
frame, u8 order, parameters, u16 CRC (high byte first). GCU packet: 8A 5E with
the same layout plus an execution state. Little-endian except the CRC.
UART: 115200/250000/500000/1000000 8N1, 30-50 Hz recommended. UDP: GCU source
port 2337, host port 2338.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass

HOST_HEADER = b'\xa8\xe5'
GCU_HEADER = b'\x8a\x5e'
VERSION = 0x02

MODE_ANGLE, MODE_HEAD_LOCK, MODE_HEAD_FOLLOW, MODE_ORTHOVIEW, MODE_EULER = 0x10, 0x11, 0x12, 0x13, 0x14
ORDER_NULL = 0x00

_CRC_TABLE = (0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
              0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef)


def crc16(data: bytes) -> int:
    """CalculateCrc16 from the protocol document (nibble table, CRC-16/XMODEM)."""
    crc = 0
    for byte in data:
        da = crc >> 12
        crc = ((crc << 4) & 0xFFFF) ^ _CRC_TABLE[da ^ (byte >> 4)]
        da = crc >> 12
        crc = ((crc << 4) & 0xFFFF) ^ _CRC_TABLE[da ^ (byte & 0x0F)]
    return crc


def _clip16(value, low=-32768, high=32767):
    return max(low, min(high, int(round(value))))


@dataclass
class CarrierState:
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    accel_neu: tuple = (0.0, 0.0, 0.0)       # m/s^2 north, east, up
    velocity_neu: tuple = (0.0, 0.0, 0.0)    # m/s north, east, up
    ins_valid: bool = True


def host_packet(roll_ctrl=0.0, pitch_ctrl=0.0, yaw_ctrl=0.0, control_valid=True, carrier=CarrierState(),
                order=ORDER_NULL, parameters=b'', sub_request=0x01, sub_frame: bytes | None = None,
                raw_control=False) -> bytes:
    """Build a host->GCU packet.

    Control values: angular velocity in deg/s (resolution 0.1 deg/s at 1x zoom)
    in head-lock/head-follow modes, or angles in deg (0.01 deg) in angle modes.
    raw_control=True passes the integers straight through (used by the doc test).
    """
    scale = 1 if raw_control else 10
    status = (0x04 if control_valid else 0) | (0x01 if carrier.ins_valid else 0)
    main = struct.pack('<hhhBhhHhhhhhhB6x',
                       _clip16(roll_ctrl * scale), _clip16(pitch_ctrl * scale), _clip16(yaw_ctrl * scale), status,
                       _clip16(carrier.roll_deg * 100, -18000, 17999), _clip16(carrier.pitch_deg * 100, -9000, 9000),
                       int(round(carrier.yaw_deg * 100)) % 36000,
                       *(_clip16(a * 100) for a in carrier.accel_neu), *(_clip16(v * 10) for v in carrier.velocity_neu),
                       sub_request)
    sub = sub_frame if sub_frame is not None else bytes(32)
    assert len(main) == 32 and len(sub) == 32
    body_len = 2 + 2 + 1 + 32 + 32 + 1 + len(parameters) + 2
    packet = HOST_HEADER + struct.pack('<HB', body_len, VERSION) + main + sub + bytes([order]) + parameters
    return packet + struct.pack('>H', crc16(packet))


def head_lock_rates(pitch_rate_deg_s: float, yaw_rate_deg_s: float, carrier=CarrierState()) -> bytes:
    """Rate command in head-lock mode (pitch and yaw angular velocity; roll invalid)."""
    limit = 150.0  # [-1500, 1500] x 0.1 deg/s at 1x zoom
    return host_packet(0.0, max(-limit, min(limit, pitch_rate_deg_s)),
                       max(-limit, min(limit, yaw_rate_deg_s)), True, carrier)


def mode_packet(mode: int, carrier=CarrierState()) -> bytes:
    return host_packet(0, 0, 0, False, carrier, order=mode)


@dataclass
class GimbalState:
    mode: int
    relative_deg: tuple          # X (roll), Y (pitch), Z (yaw) relative to the carrier, from encoders
    absolute_deg: tuple          # roll, pitch, yaw (depend on the carrier INS data)
    rates_deg_s: tuple
    order: int
    execution: bytes
    sub: dict


def parse_gcu(packet: bytes) -> GimbalState | None:
    if len(packet) < 72 or packet[:2] != GCU_HEADER:
        return None
    length = struct.unpack('<H', packet[2:4])[0]
    if length != len(packet):
        return None
    if crc16(packet[:-2]) != struct.unpack('>H', packet[-2:])[0]:
        return None
    main = packet[5:37]
    mode = main[0]
    rel = struct.unpack('<hhh', main[7:13])
    roll_abs, pitch_abs, yaw_abs = struct.unpack('<hhH', main[13:19])
    rates = struct.unpack('<hhh', main[19:25])
    sub = packet[37:69]
    sub_info = {}
    if sub[0] == 0x01:
        hw, fw, code, err = struct.unpack('<BBBH', sub[1:6])
        distance, = struct.unpack('<i', sub[6:10])
        zoom1, zoom2 = struct.unpack('<HH', sub[22:26])
        sub_info = dict(hardware=hw, firmware=fw, pod_code=code, error=err, distance_m=distance / 10,
                        zoom=zoom1 / 10, zoom2=zoom2 / 10, time_zone=struct.unpack('<b', sub[29:30])[0])
    return GimbalState(mode=mode, relative_deg=tuple(v / 100 for v in rel),
                       absolute_deg=(roll_abs / 100, pitch_abs / 100, yaw_abs / 100),
                       rates_deg_s=tuple(v / 100 for v in rates), order=packet[69],
                       execution=bytes(packet[70:-2]), sub=sub_info)


def gcu_packet(mode, relative_deg, absolute_deg=(0, 0, 0), rates_deg_s=(0, 0, 0), order=0,
               execution=b'', sub: bytes | None = None) -> bytes:
    """GCU->host packet (used by the simulated GCU and by tests)."""
    main = struct.pack('<BHhhhhhhhHhhh7x', mode, 0, 0, 0,
                       *(_clip16(a * 100, -18000, 17999) for a in relative_deg),
                       _clip16(absolute_deg[0] * 100), _clip16(absolute_deg[1] * 100),
                       int(round(absolute_deg[2] * 100)) % 36000, *(_clip16(r * 100) for r in rates_deg_s))
    sub = sub if sub is not None else bytes(32)
    length = 2 + 2 + 1 + 32 + 32 + 1 + len(execution) + 2
    packet = GCU_HEADER + struct.pack('<HB', length, VERSION) + main + sub + bytes([order]) + execution
    return packet + struct.pack('>H', crc16(packet))


def tilt_pan_to_gcu(pan_rad, tilt_rad):
    """Project convention (pan, tilt; tilt +90 deg looks straight down) to GCU yaw/pitch (deg).

    The D-80Pro is mounted downward; its pitch is negative looking down. The sign
    of yaw must be confirmed on the bench (protocol Appendix 4).
    """
    return math.degrees(pan_rad), -math.degrees(tilt_rad)


def gcu_to_tilt_pan(yaw_deg, pitch_deg):
    return math.radians(yaw_deg), -math.radians(pitch_deg)
