"""SPICE netlists for the carrier board, generated from hardware/design.py.

Three levels of detail:

* ``buck_switching`` / ``boost_switching``: cycle-by-cycle models with real
  switches, diode, inductor, capacitors with ESR and a peak-current-mode
  controller built from behavioral sources (clock, slope compensation,
  transconductance error amplifier, SR latch). Used to check ripple, start-up
  and load steps against the data-sheet design targets.
* ``input_surge``: the input protection (reverse FET, TVS, LC filter) hit by a
  battery-line voltage spike, to check the 20 V absolute maximum of the boost.
* ``power_system``: the averaged whole-aircraft supply for long simulations in
  lockstep with code: battery with state of charge, wiring, propulsion,
  avionics, both regulators with dropout/UVLO/efficiency and constant-power
  loads whose demand comes from Python each control step.
"""
from __future__ import annotations

from ...hardware import design as D

SCHOTTKY = '.model DSCH d(is=1e-5 rs=0.02 n=1.1 cjo=300p bv=60)'


def scope_ripple(time, values, start, stop, dt=5e-9, average=10):
    """Peak-to-peak ripple as a 20 MHz oscilloscope sees it.

    The ideal switches make nanosecond spikes at every edge that a real probe
    and real parasitics would not show; a uniform resample and a 50 ns moving
    average remove them, as the bandwidth limit of a scope does.
    """
    import numpy as np
    grid = np.arange(start, stop, dt)
    trace = np.convolve(np.interp(grid, time, values), np.ones(average) / average, 'valid')
    return float(np.ptp(trace))
BODY = '.model DBODY d(is=1e-9 rs=0.005 n=1.3 bv=40)'


def buck_switching(vin=14.8, i_low=1.25, i_high=3.75, t_step=3.0e-3, t_end=4.5e-3, p=D.BUCK_5V):
    period = 1 / p['fsw_hz']
    ea_limit = p['ea_current_a'] / p['gm_ea']
    ro = p['ea_gain'] / p['gm_ea']
    # Slope compensation: 1.2x half the inductor down-slope over one period.
    slope_a = 1.2 * 0.5 * p['vout'] / p['L'] * period
    return f"""
* TPS54560B 5 V buck, cycle-by-cycle (peak current mode)
Vin vin 0 {vin}
Rsrc vin vinc 0.01
Cin vinc 0 {p['cin']}
Cbulk vinc nb 47u
Rbulk nb 0 0.08
S1 vinc swn q 0 SWH
.model SWH sw vt=0.5 vh=0.01 ron={p['ron_ohm']} roff=1e6
Vsense swn sw 0
D1 0 sw DSCH
{SCHOTTKY}
L1 sw lx {p['L']} ic=0
Rdcr lx out {p['L_dcr']}
Cout out no {p['cout']}
Resr no 0 {p['cout_esr']}
Rmin out 0 1k
Iload out 0 PWL(0 0 0.1m 0 0.2m {i_low} {t_step} {i_low} {t_step + 2e-6} {i_high})
Rtop out fb {p['r_top']}
Rbot fb 0 {p['r_bottom']}
Vss ref 0 PWL(0 0 {p['soft_start_s']} {p['vref']})
Bea 0 comp I={p['gm_ea']}*max(min(V(ref)-V(fb),{ea_limit}),-{ea_limit})
Rea comp 0 {ro}
Rc comp cz {p['rc']}
Cc cz 0 {p['cc']}
Cp comp 0 {p['cp']}
Vclk clk 0 PULSE(0 1 0 1n 1n 25n {period})
Vramp ramp 0 PULSE(0 1 0 {period - 2e-9} 1n 1n {period})
Br r 0 V=(i(Vsense)+{slope_a}*V(ramp) > {p['gm_ps']}*(V(comp)-0.7)) ? 1 : 0
Bq qr 0 V=(V(clk)>0.5) ? 1 : ((V(r)>0.5) ? 0 : ((V(q)>0.5) ? 1 : 0))
Rq qr q 1
Cq q 0 2n
.ic V(q)=0 V(out)=0 V(comp)=0
.options method=gear reltol=1e-3 abstol=1e-6 vntol=1e-5
.tran 20n {t_end} 0 20n uic
.end
"""


def boost_switching(vin=12.0, i_low=1.0, i_high=2.0, t_step=7.0e-3, t_end=10.0e-3, p=D.BOOST_17V):
    """TPS55340 non-synchronous boost: internal low-side switch, B560C rectifier, current mode.

    Soft start as in the data sheet: a 6 uA source charges C_SS and the SS pin clamps COMP.
    Time 0 is the moment SS reaches the COMP level of zero switch current; before that
    (C_SS * comp_offset / I_SS, 7.8 ms with 47 nF) the converter does not switch and the
    output sits at the input through the diode, which the initial condition reproduces."""
    period = 1 / p['fsw_hz']
    ss_slope = p['i_ss'] / p['c_ss']                       # V/s
    ss_end = (1.8 - p['comp_offset']) / ss_slope
    slope_a = 1.2 * 0.5 * (p['vout'] - vin) / p['L'] * period + 0.2
    ea_limit = p['ea_current_a'] / p['gm_ea']
    return f"""
* TPS55340 17 V boost, cycle-by-cycle (peak current mode)
Vin vin 0 {vin}
Rsrc vin vinc 0.01
Cin vinc 0 {p['cin']}
L1 vinc lx {p['L']} ic=0
Rdcr lx sw {p['L_dcr']}
S1 sw swl q 0 SWL
.model SWL sw vt=0.5 vh=0.01 ron={p['ron_ls']} roff=1e6
Vsense swl 0 0
D1 sw out DSCH
{SCHOTTKY}
Cout out no {p['cout']}
Resr no 0 {p['cout_esr']}
Rmin out 0 2k
Iload out 0 PWL(0 0 0.8m 0 0.9m {i_low} {t_step} {i_low} {t_step + 2e-6} {i_high})
Rtop out fb {p['r_top']}
Rbot fb 0 {p['r_bottom']}
Vref ref 0 {p['vref']}
Vss ss 0 PWL(0 {p['comp_offset']} {ss_end} 1.8)
Bclamp comp 0 I=max(V(comp)-V(ss),0)*1
Bea 0 comp I={p['gm_ea']}*max(min(V(ref)-V(fb),{ea_limit}),-{ea_limit})
Rea comp 0 {p['ea_ro']}
Rc comp cz {p['rc']}
Cc cz 0 {p['cc']}
Cp comp 0 {p['cp']}
Vclk clk 0 PULSE(0 1 0 1n 1n 25n {period})
Vramp ramp 0 PULSE(0 1 0 {period - 2e-9} 1n 1n {period})
Br r 0 V=((i(Vsense)+{slope_a}*V(ramp) > {p['gcs']}*(V(comp)-{p['comp_offset']})) || (V(ramp)>0.92) || (i(Vsense)>{p['switch_limit_a']})) ? 1 : 0
Bq qr 0 V=(V(clk)>0.5) ? 1 : ((V(r)>0.5) ? 0 : ((V(q)>0.5) ? 1 : 0))
Rq qr q 1
Cq q 0 2n
.ic V(q)=0 V(out)={vin * 0.95} V(comp)={p['comp_offset']} V(cz)={p['comp_offset']}
.options method=gear reltol=1e-3 abstol=1e-6 vntol=1e-5
.tran 20n {t_end} 0 20n uic
.end
"""


def input_surge(v_batt=16.8, spike_v=8.0, spike_s=50e-6, with_filter=True, p=D.INPUT_PROTECTION):
    """A spike on the battery line (ESC braking) reaches the board through 15 cm of wire."""
    filt = (f"Lf prot boostin {p['filter_l']}\nRlf boostin boostin2 0.005\n"
            f"Cf boostin2 cf {p['filter_c']}\nRcf cf 0 {p['filter_c_esr']}\n"
            "Cfc boostin2 0 22u\nRboost boostin2 0 8.5" if with_filter else
            "Rjump prot boostin2 0.001\nCfc boostin2 0 22u\nRboost boostin2 0 8.5")
    return f"""
* Input protection against a battery-line spike
Vb vb 0 PWL(0 {v_batt} 100u {v_batt} 101u {v_batt + spike_v} {100e-6 + spike_s} {v_batt + spike_v} {101e-6 + spike_s} {v_batt})
Rwire vb w1 0.004
Lwire w1 bin 150n
Rfet bin prot 0.010
Dtvs 0 prot DTVS
.model DTVS d(is=1e-12 rs=0.35 n=1.0 bv=17.8 ibv=1m cjo=2n)
{filt}
.options method=gear
.tran 0.1u 400u 0 0.1u
.end
"""


def power_system(variant='carrier', soc0=1.0, p=D):
    """Averaged aircraft supply. External sources carry power demands (W) from Python.

    variant='carrier': camera on the 17 V boost (this design).
    variant='camera_on_battery': camera wired straight to the pack (what the
    original parts list implies), for comparison.
    """
    b = p.BATTERY
    q = 3600 * b['capacity_ah']
    buck, boost = p.BUCK_5V, p.BOOST_17V
    cam_node = 'v17' if variant == 'carrier' else 'bus'
    boost_lines = '' if variant != 'carrier' else f"""
* 17 V boost (TPS55340): regulates while 2.9 V < Vin < 17 V. It has no output
* disconnect: disabled, the camera still sees the pack minus the Schottky drop.
Bv17 v17s 0 V=(V(cam_en)>0.5 && V(bus)>2.9) ? max({boost['vout']}, V(bus)-0.1) : max(V(bus)-0.4, 0)
Rv17 v17s v17 0.02
C17 v17 0 {boost['cout']}
Bin17 bus 0 I=V(cam_en)>0.5 && V(bus)>2.9 ? (V(v17)*i(Vcam17))/({boost['efficiency']}*max(V(bus),2.9)) : 0
Vcam17 v17 camin 0
"""
    cam_feed = 'Vcam17' if variant == 'carrier' else 'Vcamb'
    cam_extra = '' if variant == 'carrier' else 'Vcamb bus camin 0\n'
    return f"""
* Averaged aircraft power system ({variant})
* --- battery: OCV = 13.2 + 3.6*SoC, R = {b['internal_resistance_ohm']} ohm
Csoc soc 0 1 IC={soc0}
Bsoc 0 soc I=-i(Vbat)/{q}
Bocv ocv 0 V=13.2+3.6*max(min(V(soc),1),0)
Rint ocv bi {b['internal_resistance_ohm']}
Vbat bi bat 0
* --- pack to PDB to carrier board: wire, fuse, reverse FET
Rwire bat bus 0.012
Cbus bus 0 200u
* --- propulsion (ESCs) and avionics as constant-power loads from Python
Vprop_w prop_w 0 dc 0 external
Bprop bus 0 I=V(prop_w)/max(V(bus),6)
Vavio_w avio_w 0 dc 0 external
Bavio bus 0 I=V(avio_w)/max(V(bus),6)
* --- 5 V buck (TPS54560B): EN divider start 6.5 V / stop 5 V, 98 % max duty
Bv5 v5s 0 V=V(bus)>5.0 ? min({buck['vout']}, 0.98*V(bus)-0.4) : 0
Rv5 v5s v5 0.015
C5 v5 0 {buck['cout']}
Bin5 bus 0 I=V(bus)>5.0 ? (V(v5)*(i(Vsoc5)+i(Vrad5))+0.05)/({buck['efficiency']}*max(V(bus),5)) : 0
Vsoc5 v5 socin 0
Vsoc_w soc_w 0 dc 0 external
Bsoc5 socin 0 I=V(soc_w)/max(V(socin),1)
Vrad5 v5 radin 0
Vrad_w rad_w 0 dc 0 external
Brad5 radin 0 I=V(rad_w)/max(V(radin),1)
* --- camera enable (GPIO), camera as constant-power load
Vcam_en cam_en 0 dc 0 external
{boost_lines}{cam_extra}Vcam_w cam_w 0 dc 0 external
Bcam camin 0 I=V(camin)>{p.CAMERA['input_v'][0]} ? V(cam_w)/max(V(camin),1) : 0
.options method=gear reltol=1e-4
.tran 20m 100000 0 20m uic
.end
"""
