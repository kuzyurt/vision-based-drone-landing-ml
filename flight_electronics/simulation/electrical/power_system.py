"""Lockstep electrical co-simulation of the whole aircraft supply.

The averaged SPICE netlist (circuits.power_system) is solved by ngspice while
the caller advances time. Each step the caller states what every consumer is
doing (propulsion power, SoC load, radio mode, camera load, camera enable);
the circuit returns the voltages those consumers actually get. Brown-outs are
decided from those voltages, not assumed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ...hardware import design as D
from . import circuits
from .ngspice import Spice

SOC_BROWNOUT_V = 4.75      # Orange Pi 5 needs 5 V; below 4.75 V treat as reset
RADIO_BROWNOUT_V = 4.0     # XIAO 5 V input -> 3.3 V LDO
CAMERA_MIN_V = D.CAMERA['input_v'][0]


@dataclass
class PowerDemand:
    propulsion_w: float = 0.0
    avionics_w: float = D.AVIONICS_W['pixhawk_gps_telemetry']
    soc_w: float = D.SOC_POWER['idle_w']
    radio_w: float = 0.25
    camera_w: float = D.CAMERA['pod_avg_w'] + D.CAMERA['gcu_w']
    camera_enable: bool = True


@dataclass
class PowerState:
    time_s: float
    battery_v: float
    bus_v: float
    rail_5v: float
    camera_v: float
    state_of_charge: float
    battery_a: float
    soc_powered: bool
    radio_powered: bool
    camera_powered: bool
    events: list = field(default_factory=list)


class PowerSystem:
    def __init__(self, variant='carrier', state_of_charge=1.0):
        self.variant = variant
        self.spice = Spice()
        self.spice.load(circuits.power_system(variant, soc0=state_of_charge))
        self.time = 0.0
        self.history: list[PowerState] = []
        self._camera_was = True    # everything is expected to be powered at the start
        self._soc_was = True

    def close(self):
        self.spice.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def step(self, until_s: float, demand: PowerDemand) -> PowerState:
        self.spice.set_external(vprop_w=demand.propulsion_w, vavio_w=demand.avionics_w,
                                vsoc_w=demand.soc_w, vrad_w=demand.radio_w,
                                vcam_w=demand.camera_w, vcam_en=1.0 if demand.camera_enable else 0.0)
        last = self.spice.advance(until_s)
        self.time = until_s
        cam_node = 'camin'
        state = PowerState(
            time_s=until_s, battery_v=last['bat'], bus_v=last['bus'], rail_5v=last['v5'],
            camera_v=last[cam_node], state_of_charge=last['soc'], battery_a=last['vbat#branch'],
            soc_powered=last['socin'] >= SOC_BROWNOUT_V, radio_powered=last['radin'] >= RADIO_BROWNOUT_V,
            camera_powered=last[cam_node] >= CAMERA_MIN_V)
        if state.camera_powered != self._camera_was:
            state.events.append('camera_power_on' if state.camera_powered else 'camera_brownout')
        if state.soc_powered != self._soc_was:
            state.events.append('soc_power_on' if state.soc_powered else 'soc_brownout')
        self._camera_was, self._soc_was = state.camera_powered, state.soc_powered
        self.history.append(state)
        return state

    def table(self):
        keys = ('time_s', 'battery_v', 'bus_v', 'rail_5v', 'camera_v', 'state_of_charge', 'battery_a')
        return {k: np.array([getattr(s, k) for s in self.history]) for k in keys}


def propulsion_power_w(total_thrust_n: float, battery_v: float = 16.0) -> float:
    """Electrical propulsion power from the 16 V bench table (equal thrust per motor)."""
    table = D.MOTOR_TABLE_16V
    per_motor = max(0.0, total_thrust_n) / table['motors']
    current = float(np.interp(per_motor, table['thrust_n'], table['current_a']))
    if per_motor > table['thrust_n'][-1]:
        current = table['current_a'][-1]
    return table['motors'] * current * table['bench_voltage_v']
