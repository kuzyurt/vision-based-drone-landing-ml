"""Boat-to-drone LoRa link: radio channel model + the real firmware (host build)."""
from __future__ import annotations

import ctypes as C
import math
import platform
from pathlib import Path

import numpy as np

from ..hardware import design as D

_PREBUILT = Path(__file__).resolve().parents[1] / 'firmware' / 'prebuilt'


def load_firmware_library():
    from ..firmware import build_host
    try:
        path = build_host.build_library()
    except Exception:
        name = build_host.library_name()
        path = _PREBUILT / name
        if not path.exists():
            raise
    lib = C.CDLL(str(path))
    lib.fe_create.restype = C.c_void_p
    lib.fe_create.argtypes = [C.c_uint32, C.c_uint8, C.c_int8]
    lib.fe_destroy.argtypes = [C.c_void_p]
    lib.fe_run_until.argtypes = [C.c_void_p, C.c_uint32]
    lib.fe_radio_deliver.argtypes = [C.c_void_p, C.c_char_p, C.c_uint32, C.c_float, C.c_float, C.c_int]
    lib.fe_uart_read.argtypes = [C.c_void_p, C.c_char_p, C.c_uint32]
    lib.fe_uart_read.restype = C.c_uint32
    lib.fe_uart_write.argtypes = [C.c_void_p, C.c_char_p, C.c_uint32]
    lib.fe_radio_mode.argtypes = [C.c_void_p]
    lib.fe_radio_take_tx.argtypes = [C.c_void_p, C.c_char_p, C.c_uint32]
    lib.fe_radio_take_tx.restype = C.c_uint32
    lib.fe_counters.argtypes = [C.c_void_p, C.POINTER(C.c_uint32)]
    lib.fe_radio_frequency.argtypes = [C.c_void_p]
    lib.fe_radio_frequency.restype = C.c_uint32
    lib.fe_radio_power.argtypes = [C.c_void_p]
    lib.fe_time_on_air_us.argtypes = [C.c_uint8, C.c_uint32, C.c_uint8, C.c_uint16, C.c_uint32]
    lib.fe_time_on_air_us.restype = C.c_uint32
    return lib


class LoraChannel:
    """Log-distance path loss over water, SX1262 SF7 demodulation limit."""

    def __init__(self, rng=None, lora=D.LORA, exponent=2.3, antenna_gain_dbi=2.0, losses_db=2.0,
                 shadowing_db=3.0):
        self.rng = rng or np.random.default_rng(1)
        self.lora, self.n, self.g, self.loss, self.shadow = lora, exponent, antenna_gain_dbi, losses_db, shadowing_db
        self.noise_dbm = -174 + 10 * math.log10(lora['bandwidth_hz']) + 6.0   # 6 dB noise figure

    def rssi_dbm(self, distance_m: float) -> float:
        d = max(distance_m, 1.0)
        fspl_1m = 20 * math.log10(4 * math.pi * self.lora['frequency_hz'] / 3e8)
        path = fspl_1m + 10 * self.n * math.log10(d)
        return self.lora['tx_dbm'] + 2 * self.g - self.loss - path + self.rng.normal(0, self.shadow)

    def receive(self, distance_m: float):
        rssi = self.rssi_dbm(distance_m)
        snr = rssi - self.noise_dbm
        per = 1 / (1 + math.exp((snr + 7.5) / 0.7))          # SF7 limit -7.5 dB
        delivered = self.rng.random() >= per
        return delivered, max(rssi, -140.0), max(min(snr, 30.0), -20.0)


class RadioBridgeDevice:
    """The XIAO ESP32S3 + SX1262 running the real firmware sources."""

    def __init__(self, lora=D.LORA):
        self.lib = load_firmware_library()
        self.handle = self.lib.fe_create(lora['frequency_hz'], lora['sf'], lora['tx_dbm'])
        self.lora = lora
        self.clock_ms = 0
        self._pending = []   # (deliver_at_ms, bytes, rssi, snr, crc_ok)

    def close(self):
        if self.handle:
            self.lib.fe_destroy(self.handle)
            self.handle = None

    def __del__(self):
        self.close()

    def time_on_air_s(self, payload_len: int) -> float:
        return self.lib.fe_time_on_air_us(self.lora['sf'], self.lora['bandwidth_hz'], self.lora['coding_rate'],
                                          self.lora['preamble'], payload_len) / 1e6

    def on_air(self, payload: bytes, sent_at_s: float, rssi: float, snr: float, crc_ok=True):
        done = sent_at_s + self.time_on_air_s(len(payload))
        self._pending.append((int(math.ceil(done * 1000)), payload, rssi, snr, crc_ok))

    def run_until(self, t_s: float) -> bytes:
        target = int(t_s * 1000)
        self._pending.sort(key=lambda item: item[0])
        while self._pending and self._pending[0][0] <= target:
            at, payload, rssi, snr, ok = self._pending.pop(0)
            self.lib.fe_run_until(self.handle, at)
            self.lib.fe_radio_deliver(self.handle, payload, len(payload), rssi, snr, int(ok))
        self.lib.fe_run_until(self.handle, target)
        self.clock_ms = target
        out = C.create_string_buffer(4096)
        n = self.lib.fe_uart_read(self.handle, out, 4096)
        return out.raw[:n]

    def write_uart(self, data: bytes):
        self.lib.fe_uart_write(self.handle, data, len(data))

    def mode(self) -> int:
        return self.lib.fe_radio_mode(self.handle)

    def power_w(self) -> float:
        mode = self.mode()
        radio_ma = D.RADIO['tx_ma_22dbm'] if mode == 3 else D.RADIO['rx_ma'] if mode == 2 else 1.0
        return 5.0 * (D.RADIO['esp32_active_ma'] + radio_ma) / 1000

    def counters(self):
        values = (C.c_uint32 * 5)()
        self.lib.fe_counters(self.handle, values)
        return dict(zip(('rx_ok', 'rx_bad', 'tx_done', 'reinit', 'frames_from_companion'), values))
