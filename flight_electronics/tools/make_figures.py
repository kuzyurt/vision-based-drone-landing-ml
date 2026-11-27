"""Run the electrical and timing simulations and draw the README figures.

    python -m flight_electronics.tools.make_figures

Writes PNGs to flight_electronics/media and the numbers to media/simulation_results.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..companion.timing import Rk3588Timing  # noqa: E402
from ..hardware import design as D  # noqa: E402
from ..simulation.electrical import circuits  # noqa: E402
from ..simulation.electrical.ngspice import Spice  # noqa: E402
from ..simulation.electrical.power_system import PowerDemand, PowerSystem, propulsion_power_w  # noqa: E402

MEDIA = Path(__file__).resolve().parents[1] / 'media'
BLUE, ORANGE, AQUA, YELLOW, RED = '#257de0', '#f47230', '#00b894', '#f2a600', '#dc3c3d'
TEXT, MUTED, GRID = '#191919', '#666666', '#e6e6e6'

plt.rcParams.update({
    'font.size': 10, 'axes.edgecolor': MUTED, 'axes.labelcolor': TEXT, 'xtick.color': MUTED,
    'ytick.color': MUTED, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.8,
    'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 150, 'lines.linewidth': 1.6,
    'axes.titleweight': 'bold', 'axes.titlesize': 11, 'axes.titlelocation': 'left'})


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(MEDIA / name, facecolor='white')
    plt.close(fig)


def converter(kind):
    if kind == 'buck':
        net, out, t_step, target = circuits.buck_switching(), 5.0, 3.0e-3, D.BUCK_5V
        steady = (2.2e-3, 2.9e-3)
        after = (3.9e-3, 4.4e-3)
    else:
        net, out, t_step, target = circuits.boost_switching(), D.BOOST_17V['vout'], 2.5e-3, D.BOOST_17V
        steady = (1.9e-3, 2.45e-3)
        after = (3.4e-3, 3.95e-3)
    with Spice() as spice:
        v = spice.run(net)
    t, vout = v['time'], v['out']
    il = v['l1#branch']

    def window(a, b):
        m = (t > a) & (t < b)
        return vout[m]

    pre, post = window(*steady), window(*after)
    step = window(t_step, t_step + 0.6e-3)
    result = dict(mean_v_before=float(pre.mean()), ripple_mv_before=float(np.ptp(pre) * 1000),
                  mean_v_after=float(post.mean()), ripple_mv_after=float(np.ptp(post) * 1000),
                  step_dip_mv=float((pre.mean() - step.min()) * 1000),
                  step_dip_percent=float((pre.mean() - step.min()) / out * 100))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True, gridspec_kw=dict(height_ratios=[3, 2]))
    a1.plot(t * 1e3, vout, color=BLUE)
    a1.axhline(out, color=MUTED, lw=0.8, ls='--')
    a1.set_ylabel('Output (V)')
    title = ('5 V buck (TPS54560B): start-up and load step 1.25 → 3.75 A' if kind == 'buck'
             else '17 V camera boost (TPS61288) at 12 V input: start-up and load step 1 → 2.5 A')
    a1.set_title(title)
    a1.set_ylim(out * 0.6 if kind == 'buck' else 10, out * 1.08)
    a2.plot(t * 1e3, il, color=ORANGE, lw=0.8)
    a2.set_ylabel('Inductor (A)')
    a2.set_xlabel('Time (ms)')
    _save(fig, f'sim_{kind}.png')
    return result


def surge():
    out = {}
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for label, filt, color in (('without the LC filter', False, ORANGE), ('with the 1 µH + 100 µF filter', True, BLUE)):
        with Spice() as spice:
            v = spice.run(circuits.input_surge(with_filter=filt))
        t, vin = v['time'], v['boostin2']
        out[label] = float(vin.max())
        ax.plot(t * 1e6, vin, color=color, label=f'boost input, {label}')
    ax.axhline(D.BOOST_17V['vin_abs_max'], color=RED, lw=1, ls='--')
    ax.text(5, D.BOOST_17V['vin_abs_max'] + 0.25, 'TPS61288 absolute maximum 20 V', color=TEXT, fontsize=9)
    ax.set_title('8 V / 50 µs spike on a full 4S battery line (ESC braking)')
    ax.set_xlabel('Time (µs)')
    ax.set_ylabel('Volts')
    ax.legend(frameon=False, loc='lower right')
    _save(fig, 'sim_surge.png')
    return out


def flight(minutes=22.0):
    """Hover with manoeuvres from full to empty, both wirings, same propulsion profile."""
    rng = np.random.default_rng(3)
    steps = int(minutes * 60 / 0.5)
    profile = []
    for k in range(steps):
        t = (k + 1) * 0.5
        burst = 1.45 if (t % 90) < 6 else 1.0
        profile.append((t, burst * (1 + 0.04 * rng.standard_normal())))
    hover = propulsion_power_w(2.12 * 9.80665)
    results, traces = {}, {}
    for variant in ('carrier', 'camera_on_battery'):
        with PowerSystem(variant, state_of_charge=1.0) as ps:
            first_off = None
            for t, factor in profile:
                s = ps.step(t, PowerDemand(propulsion_w=hover * factor, soc_w=D.SOC_POWER['inference_w']))
                if not s.camera_powered and first_off is None:
                    first_off = (t, s.state_of_charge, s.battery_v)
            traces[variant] = ps.table()
        results[variant] = dict(camera_first_off_s=None if first_off is None else first_off[0],
                                state_of_charge_at_off=None if first_off is None else first_off[1],
                                battery_v_at_off=None if first_off is None else first_off[2],
                                camera_v_min=float(traces[variant]['camera_v'].min()),
                                rail_5v_min=float(traces[variant]['rail_5v'].min()))
    results['hover_power_w'] = hover
    fig, ax = plt.subplots(figsize=(8, 4))
    c, b = traces['carrier'], traces['camera_on_battery']
    ax.plot(c['time_s'] / 60, c['camera_v'], color=BLUE, label='camera on the 17 V boost (this board)')
    ax.plot(b['time_s'] / 60, b['camera_v'], color=ORANGE, label='camera straight on the battery')
    ax.axhline(D.CAMERA['input_v'][0], color=RED, lw=1, ls='--')
    ax.text(0.2, D.CAMERA['input_v'][0] + 0.15, 'camera minimum 14 V', color=TEXT, fontsize=9)
    off = results['camera_on_battery']['camera_first_off_s']
    if off:
        ax.axvline(off / 60, color=MUTED, lw=0.8, ls=':')
        ax.text(off / 60 + 0.2, 12.4, f'camera off after {off / 60:.1f} min\n'
                f'({results["camera_on_battery"]["state_of_charge_at_off"] * 100:.0f} % charge left)',
                color=TEXT, fontsize=9)
    ax.set_title('Camera supply over a full battery (hover, a climb burst every 90 s)')
    ax.set_xlabel('Flight time (min)')
    ax.set_ylabel('Camera input (V)')
    ax.set_ylim(11.5, 18)
    ax.legend(frameon=False, loc='lower left')
    _save(fig, 'sim_flight_power.png')
    return results


def timing():
    rng = np.random.default_rng(0)
    rows = []
    for label, mode, native in (('Pad not in view (search)', 'none', True),
                                ('Pad tracked', 'tracked', True),
                                ('First pad registration, C++ kernel', 'cold', True),
                                ('First pad registration, pure Python', 'cold', False)):
        model = Rk3588Timing(rng, native_marker_kernel=native)
        samples = [model.step(mode) for _ in range(400)]
        npu = float(np.median([s.npu_s for s in samples]) * 1000)
        cpu = float(np.median([s.cpu_s for s in samples]) * 1000)
        rows.append((label, npu, cpu))
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for i, (label, npu, cpu) in enumerate(rows):
        ax.barh(i, npu, color=BLUE, height=0.5, edgecolor='white', linewidth=2)
        ax.barh(i, min(cpu, 70 - npu), left=npu, color=ORANGE, height=0.5, edgecolor='white', linewidth=2)
        total = npu + cpu
        ax.text(min(total, 70) + 0.8, i, f'{total:.0f} ms' + ('  (off scale)' if total > 70 else ''),
                va='center', color=TEXT, fontsize=9)
    ax.axvline(40, color=RED, lw=1, ls='--')
    ax.text(40.5, 3.45, '40 ms = one 25 Hz tick', color=TEXT, fontsize=9)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 80)
    ax.set_xlabel('Milliseconds per decision on the RK3588S (model)')
    ax.set_title('Decision latency: network on the NPU (blue) + control code on one A76 core (orange)')
    ax.grid(axis='y', visible=False)
    _save(fig, 'sim_timing.png')
    return {r[0]: dict(npu_ms=r[1], cpu_ms=r[2], total_ms=r[1] + r[2]) for r in rows}


def main():
    MEDIA.mkdir(exist_ok=True)
    results = dict(buck=converter('buck'), boost=converter('boost'), surge=surge(), flight=flight(), timing=timing())
    (MEDIA / 'simulation_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
