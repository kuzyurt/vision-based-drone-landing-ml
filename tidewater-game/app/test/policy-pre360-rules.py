"""Pre360 and minimum-search-height rules of the browser policy (Python, needs numpy + scipy).

Run from anywhere:  python tidewater-game/app/test/policy-pre360-rules.py
"""
import json, math, sys
from pathlib import Path
POLICY = Path(__file__).resolve().parents[1] / 'public/policy'
sys.path.insert(0, str(POLICY))
sys.dont_write_bytecode = True
import numpy as np
from reference import student_api as api

manifest = (POLICY / 'manifest.json').read_text(encoding='utf-8')

def obs(t, z=2.0, yaw_ned=0.0, pan=0.0, tilt=0.0, beacon=None, prev=None):
    return dict(
        px4=dict(valid=True, position_enu_m=[0., 0., z], velocity_enu_m_s=[0., 0., 0.],
                 attitude_ned_rad=[0., 0., yaw_ned], angular_rate_frd_rad_s=[0., 0., 0.],
                 position_age_s=0., attitude_age_s=0., armed=True, landed=False,
                 gimbal_commanded_rad=[pan, tilt]),
        beacon=beacon or dict(valid=False), gimbal_rad=[pan, tilt],
        image_capture_time_s=t, image_delivery_time_s=t, image_age_s=0., image_valid=True,
        previous_executed_action=prev or [0.] * 6, decision_dt_s=.04,
        mission=dict(elapsed_s=t, budget_s=180, water_datum_enu_m=0, nominal_deck_height_above_water_m=.45,
                     recovery_clearance=dict(valid=False)))

def run(script, beacon=None, frames=600, z=2.0):
    api.initialize(manifest)
    rows = []
    yaw = 0.0; tilt = 0.0; prev = [0.] * 6
    for k in range(frames):
        t = k * .04
        props = script(t, rows[-1]['d'].get('control_phase') if rows else None)
        o = obs(t, z=z, yaw_ned=yaw, tilt=tilt, beacon=beacon, prev=prev)
        out = json.loads(api.step(np.zeros(640 * 360 * 3, np.uint8).tobytes(), [0.] * 15, json.dumps(props), json.dumps(o), t))
        a = out['action']; d = out['diagnostics']
        # crude plant: yaw-rate integrates (NED yaw), gimbal tilt rate integrates
        yaw += a[3] * .04; tilt = min(max(tilt + a[5] * .04, -0.17), math.pi / 2); prev = a
        z -= a[2] * .04  # action[2] is down-positive
        rows.append(dict(t=t, a=a, d=d))
        if d.get('handoff_latched') or d.get('control_phase') in ('inspect',):
            pass
    return rows

def phases(rows):
    seq = []
    for r in rows:
        p = r['d'].get('control_phase')
        if not seq or seq[-1][1] != p: seq.append((round(r['t'], 2), p))
    return seq

TOS = lambda conf=.9: [dict(pixel=[320., 300.], confidence=conf, evidence='target_or_similar', identity_target_probability=.5)]
TB = lambda conf=.4: [dict(pixel=[320., 300.], confidence=conf, evidence='target_boat', identity_target_probability=.9)]
UNK = [dict(pixel=[320., 300.], confidence=.9, evidence='unknown_boat', identity_target_probability=.01)]

# A: nothing seen -> pre-check climbs to 7 m looking straight down, then the
#    normal scan (no 360 deg look-around turn any more)
rows = run(lambda t, p: [], frames=520)
ph = phases(rows)
print('A', ph[:6], 'climb cmd', rows[5]['a'][2], 'height', rows[5]['d'].get('search_height_m'))
assert [p for _, p in ph[:2]] == ['pre360_nadir', 'scan'], ph
assert 'pre360_sweep' not in [p for _, p in ph]
assert rows[5]['a'][2] < 0, 'must climb towards the search height'
assert rows[5]['d'].get('search_height_m') == 7.0
nadir = [r for r in rows if r['d'].get('control_phase') == 'pre360_nadir']
assert all(r['a'][5] >= -1e-9 for r in nadir[10:]), 'camera keeps tilting down / holds straight down'
end = next(r['t'] for r in rows if r['d'].get('control_phase') == 'scan')
assert 2.0 <= end <= 15.1, end
# A2: already above 7 m -> no climb, ~2 s straight down, then scan
rows = run(lambda t, p: [], frames=200, z=9.0)
ph = phases(rows); print('A2', ph[:3])
end = next(r['t'] for r in rows if r['d'].get('control_phase') == 'scan')
assert 1.9 <= end <= 2.3 and rows[5]['a'][2] >= -1e-9, (end, rows[5]['a'][2])

# B: target_or_similar seen during the pre-check -> same frame handover, then inspect (normal search)
rows = run(lambda t, p: TOS() if t >= 6.0 else [], frames=200)
ph = phases(rows); print('B', ph)
assert ('pre360_handover' in [p for _, p in ph]) and ph[-1][1] in ('inspect', 'reacquire_last_sensor_view')
hand = next(t for t, p in ph if p == 'pre360_handover'); assert 6.0 <= hand <= 6.2, hand  # normal rule: 0.12 s stable support

# C: low-confidence target_boat (0.40) during the pre-check, radio agrees (boat right
# below) -> confirmed by normal rules -> landing controller
NEAR = dict(valid=True, age_s=0.2, position_sigma_m=.25, velocity_sigma_m_s=.025, dock_ready=True,
            relative_heading_m=[0.5, 0., 2.], velocity_heading_m_s=[0., 0., 0.])
rows = run(lambda t, p: TB(.40) if t >= 6.0 else [], beacon=NEAR, frames=200)
ph = phases(rows); print('C', ph[:8])
assert any(r['d'].get('handoff_latched') for r in rows), 'normal rules must confirm target_boat'
# C2: the same without radio and without any drone movement: a "target boat"
# label alone is not proof (glare has been labelled target boat) -> inspected,
# not latched, and the drone is asked to sidestep for a parallax check.
rows = run(lambda t, p: TB(.40) if t >= 6.0 else [], frames=300)
ph = phases(rows); print('C2', ph[:8])
assert not any(r['d'].get('handoff_latched') for r in rows), 'unproven target_boat must not latch without radio'
assert any(p == 'inspect' for _, p in ph), ph
side = [r['a'][1] for r in rows if r['t'] > 8.5 and r['d'].get('control_phase') == 'inspect']
assert side and max(side) > .5, 'sidestep for the parallax check'

# D: unknown boat early (t<18 s) does not interrupt pre360 (same as normal scan_1 rule)
rows = run(lambda t, p: UNK if t >= 6.0 else [], frames=250)
ph = phases(rows); print('D', ph[:6])
assert 'pre360_handover' not in [p for _, p in ph]

# E: radio available + a target_or_similar spot that DISAGREES with the radio
# (radio: boat 40 m ahead; spot: right under the drone) -> no handover; the
# radio keeps authority (2026-11-14 glare fix; before, the camera took over).
beacon = dict(valid=True, age_s=0.2, position_sigma_m=.25, velocity_sigma_m_s=.025, dock_ready=True,
              relative_heading_m=[40., 0., 2.], velocity_heading_m_s=[0., 0., 0.])
rows = run(lambda t, p: TOS() if t >= 6.0 else [], beacon=beacon, frames=520)
ph = phases(rows); print('E', ph)
assert 'pre360_handover' not in [p for _, p in ph] and ph[-1][1] in ('radio_approach', 'radio_hold'), ph
# E2: radio available + a spot that AGREES with the radio (boat right below)
# -> same frame handover, visual search keeps authority (unchanged behaviour).
near = dict(beacon, relative_heading_m=[0.5, 0., 2.])
rows = run(lambda t, p: TOS() if t >= 6.0 else [], beacon=near, frames=200)
ph = phases(rows); print('E2', ph)
after = [p for t, p in ph if t > 6.05]
assert 'pre360_handover' in [p for _, p in ph], ph
assert after and all(p not in ('radio_approach', 'radio_hold') for p in after), after
# F: radio, nothing seen: radio approach after pre360 (unchanged behaviour)
rows = run(lambda t, p: [], beacon=beacon, frames=520)
ph = phases(rows); print('F', ph[-3:]); assert ph[-1][1] in ('radio_approach', 'radio_hold')
print('ALL PRE360 TESTS PASSED')

# G: after the landing controller has taken over but cannot see the pad, the
# search-like phases climb towards the minimum search height (drone at 2 m).
rows = run(lambda t, p: TB(.40) if 6.0 <= t < 6.4 else [], beacon=NEAR, frames=400)
late = [r for r in rows if r['t'] > 12 and r['d'].get('handoff_latched')]
print('G', phases(rows)[-3:], 'vertical command', round(late[-1]['a'][2], 3))
assert late and late[-1]['a'][2] < 0, 'hand-back to search phases must climb towards 5 m'
print('MIN HEIGHT HAND-BACK TEST PASSED')
