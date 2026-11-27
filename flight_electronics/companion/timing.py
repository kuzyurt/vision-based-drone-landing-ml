"""Compute-time model of the RK3588S for one 25 Hz decision.

The network runs on the NPU while the CPU runs the control code of the previous
frame (two-stage pipeline). Latency is NPU + CPU; throughput is limited by the
slower stage. The numbers and their sources are in hardware/design.py TIMING.
Replace them with on-board measurements (tools/benchmark_board.py) when the
board exists.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..hardware import design as D


@dataclass
class StepTiming:
    npu_s: float
    cpu_s: float
    latency_s: float
    stage_limit_s: float
    deadline_met: bool


class Rk3588Timing:
    def __init__(self, rng: np.random.Generator | None = None, native_marker_kernel=True, timing=D.TIMING):
        self.t = timing
        self.rng = rng or np.random.default_rng(0)
        self.native = native_marker_kernel
        self.period = 1 / timing['control_hz']

    def step(self, marker: str = 'cold') -> StepTiming:
        """marker: 'none' (no pad in view), 'cold' (first registration) or 'tracked'."""
        t = self.t
        npu = t['npu_inference_s'] + abs(self.rng.normal(0, t['npu_jitter_s']))
        if marker == 'cold':
            marker = t['marker_cold_s'] if self.native else t['marker_cold_python_s']
        elif marker == 'tracked':
            marker = t['marker_tracked_s']
        else:
            marker = 0.0
        cpu = t['cpu_scale'] * (t['control_code_s'] + marker) * (1 + abs(self.rng.normal(0, 0.05)))
        cpu += t['decode_scale_s']
        stage = max(npu, cpu)
        return StepTiming(npu, cpu, npu + cpu, stage, stage <= self.period)
