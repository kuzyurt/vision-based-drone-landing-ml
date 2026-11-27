"""Companion side of the ESP32 radio bridge serial protocol (see firmware include/protocol.h)."""
from __future__ import annotations

import struct
from dataclasses import dataclass

FRAME_BEACON, FRAME_HEARTBEAT, FRAME_TX_DONE, FRAME_STATUS, FRAME_PING = 0x01, 0x02, 0x03, 0x10, 0x11
BEACON_SIZE = 32


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def cobs_encode(data: bytes) -> bytes:
    out, block = bytearray(), bytearray()
    for byte in data:
        if byte == 0:
            out += bytes([len(block) + 1]) + block
            block.clear()
        else:
            block.append(byte)
            if len(block) == 254:
                out += b'\xff' + block
                block.clear()
    out += bytes([len(block) + 1]) + block
    return bytes(out)


def cobs_decode(data: bytes) -> bytes | None:
    out, index = bytearray(), 0
    while index < len(data):
        code = data[index]
        if code == 0 or index + code > len(data):
            return None
        block = data[index + 1:index + code]
        if 0 in block:
            return None
        out += block
        index += code
        if code != 0xFF and index < len(data):
            out.append(0)
    return bytes(out)


def frame(frame_type: int, payload: bytes = b'') -> bytes:
    plain = bytes([frame_type]) + payload
    return cobs_encode(plain + struct.pack('>H', crc16_ccitt(plain))) + b'\x00'


@dataclass
class BoatFix:
    """One boat beacon as received on the drone."""
    sequence: int
    boat_time_s: float
    position_enu_m: tuple
    velocity_enu_m_s: tuple
    dock_ready: bool
    dock_status_valid: bool
    position_sigma_m: float
    rssi_dbm: float
    snr_db: float
    radio_rx_time_s: float      # ESP32 clock when RxDone fired


def encode_beacon(sequence, boat_time_s, position_enu_m, velocity_enu_m_s, dock_ready=True,
                  dock_status_valid=True, position_sigma_m=0.25) -> bytes:
    """What the boat transmitter sends (used by the simulation's boat and by tests)."""
    e, n, u = (int(round(v * 100)) for v in position_enu_m)
    ve, vn, vu = (max(-32768, min(32767, int(round(v * 100)))) for v in velocity_enu_m_s)
    flags = (1 if dock_ready else 0) | (2 if dock_status_valid else 0)
    body = (b'BT' + bytes([1]) + struct.pack('<HIiiihhhBH', sequence & 0xFFFF,
                                             int(boat_time_s * 1000) & 0xFFFFFFFF, e, n, u, ve, vn, vu,
                                             flags, min(65535, int(round(position_sigma_m * 100)))))
    return body + struct.pack('<H', crc16_ccitt(body))


def decode_beacon(raw: bytes):
    if len(raw) != BEACON_SIZE or raw[:3] != b'BT\x01':
        return None
    if crc16_ccitt(raw[:30]) != struct.unpack('<H', raw[30:32])[0]:
        return None
    seq, t_ms, e, n, u, ve, vn, vu, flags, sigma = struct.unpack('<HIiiihhhBH', raw[3:30])
    return dict(sequence=seq, boat_time_s=t_ms / 1000, position_enu_m=(e / 100, n / 100, u / 100),
                velocity_enu_m_s=(ve / 100, vn / 100, vu / 100), dock_ready=bool(flags & 1),
                dock_status_valid=bool(flags & 2), position_sigma_m=sigma / 100)


class RadioLink:
    """Byte-stream parser for frames coming from the radio bridge."""

    def __init__(self):
        self._buffer = bytearray()
        self.errors = 0
        self.heartbeat = None
        self.tx_done = []

    def feed(self, data: bytes):
        fixes = []
        for byte in data:
            if byte:
                self._buffer.append(byte)
                if len(self._buffer) > 200:
                    self._buffer.clear()
                    self.errors += 1
                continue
            decoded = cobs_decode(bytes(self._buffer)) if self._buffer else None
            self._buffer.clear()
            if not decoded or len(decoded) < 3:
                continue
            body, crc = decoded[:-2], struct.unpack('>H', decoded[-2:])[0]
            if crc16_ccitt(body) != crc:
                self.errors += 1
                continue
            kind, payload = body[0], body[1:]
            if kind == FRAME_BEACON and len(payload) == BEACON_SIZE + 7:
                beacon = decode_beacon(payload[:BEACON_SIZE])
                if beacon is None:
                    self.errors += 1
                    continue
                rssi, snr, rx_ms = struct.unpack('<hbI', payload[BEACON_SIZE:])
                fixes.append(BoatFix(rssi_dbm=rssi / 10, snr_db=snr / 4, radio_rx_time_s=rx_ms / 1000,
                                     **beacon))
            elif kind == FRAME_HEARTBEAT and len(payload) == 17:
                up, ok, bad, done = struct.unpack('<IIII', payload[:16])
                self.heartbeat = dict(uptime_s=up / 1000, rx_ok=ok, rx_bad=bad, tx_done=done, mode=payload[16])
            elif kind == FRAME_TX_DONE and len(payload) == 2:
                self.tx_done.append(struct.unpack('<H', payload)[0])
        return fixes

    @staticmethod
    def status_frame(payload: bytes) -> bytes:
        if len(payload) > 32:
            raise ValueError('status payload is limited to 32 bytes')
        return frame(FRAME_STATUS, payload)
