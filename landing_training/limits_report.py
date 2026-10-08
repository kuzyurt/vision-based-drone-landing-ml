"""Summarize measured review trials without converting them to training data."""
from . import paths
from collections import defaultdict
from pathlib import Path
import argparse
import json
from .gate import source_fingerprint
from .scene import ROOT

def build_report(destination,calm_speed,combined_speed,period=4.5):
    runtime=source_fingerprint(runtime_only=True);trials=[]
    transition=json.loads((ROOT/'build/visual_only_transition.json').read_text())
    controller_physics=source_fingerprint(runtime_only=True,include_rendering=False)
    if transition['controller_physics_sha256']!=controller_physics or transition['current_runtime_source_sha256']!=runtime:raise RuntimeError('Unverified control/physics change since benchmarking')
    directories=('speed_limits','speed_confirmation','maximum_speed_confirmation','maximum_speed_confirmation_v2','weather_limits','weather_extended','stress_preflight')
    for directory in directories:
        for path in sorted((ROOT/'outputs'/directory).glob('*.json')):
            result=json.loads(path.read_text())
            compatible=[runtime,*transition.get('compatible_headless_runtime_source_sha256',[])]
            if result.get('runtime_source_sha256') not in compatible:raise RuntimeError('Stale benchmark '+str(path))
            trials.append({'stage':directory,'evidence':str(path.relative_to(ROOT)),**result})
    confirmation=[t for t in trials if t['stage']=='maximum_speed_confirmation_v2' and t['scenario']['boat_speed']==calm_speed]
    if len(confirmation)!=30 or not all(t['passed'] for t in confirmation):raise RuntimeError('Selected speed needs 30 successful independent confirmation cases')
    if not all(t.get('speed_hold_valid',False) for t in confirmation):raise RuntimeError('Boat slowed down below the requested speed')
    selected_weather=[t for t in trials if t['scenario']['wave_height']==.5 and t['scenario']['wave_period']==period and t['scenario']['wind_mean_m_s']==8 and t['scenario']['boat_speed']==combined_speed and t['passed']]
    if not selected_weather:raise RuntimeError('Combined speed/weather was not successfully tested')
    groups=defaultdict(list)
    for t in trials:
        if t['stage']=='speed_limits':groups[t['scenario']['boat_speed']].append(t)
    screening=[]
    for speed,group in sorted(groups.items()):
        screening.append({'target_m_s':speed,'trials':len(group),'landings':sum(t['passed'] for t in group),'outcomes':[t['outcome'] for t in group],'actual_terminal_speed_m_s':[t['terminal_speed_mean_m_s'] for t in group]})
    report={'schema':'aerodock.landing.limits-review.v1','role':'review_benchmark','training_eligible':False,
            'runtime_source_sha256':runtime,'source_sha256':source_fingerprint(),
            'controller_physics_sha256':controller_physics,'verified_visual_only_transition':transition,
            'selected_calm_target_m_s':calm_speed,'selected_calm_target_km_h':calm_speed*3.6,
            'selected_combined_target_m_s':combined_speed,'confirmation_trials':len(confirmation),
            'confirmation_landings':sum(t['passed'] for t in confirmation),
            'actual_terminal_speed_range_m_s':[min(t['terminal_speed_mean_m_s'] for t in confirmation),max(t['terminal_speed_mean_m_s'] for t in confirmation)],
            'confirmation_scope':{'maps':sorted({t['scenario']['kind'] for t in confirmation}),
                                  'route_directions':['forward','reverse'],
                                  'distance_m':sorted({t['scenario']['distance'] for t in confirmation}),
                                  'height_m':sorted({t['scenario']['height'] for t in confirmation}),
                                  'wind':'calm','waves':0.,'distinct_world_seeds':len({t['scenario']['world_seed'] for t in confirmation})},
            'unchanged_limits':{'horizontal_action_m_s':2.,'px4_LNDMC_XY_VEL_MAX_m_s':1.5,'forced_disarm':False},
            'weather':{'wave_height':.5,'wave_period':period,'wind_mean_m_s':8.,'wind_profile':'gusty',
                       'wave_parameter_note':'Bounded multi-component parameter; instantaneous surface lies within +/-0.25 m. Not significant wave height.',
                       'observed_wind_peak_m_s':max(s['wind_speed_m_s'] for t in selected_weather for s in t['samples'])},
            'screening':screening,'trials':trials,
            'limitations':['Highest confirmed operating setting for this simulator/controller and the stated cases; not the physical maximum of the real drone.',
                           '30/30 specified seeded cases is an observed result, not a guarantee for untested cases or real hardware.',
                           'Actual boat speeds vary with acceleration, path following, wind and waves; target speed alone is not evidence.',
                           'Strong-weather model remains the original moderate-wave approximation; no slamming, added mass, wakes or rotor-water interaction.',
                           'Pilot collection ranges remain unchanged and user verification is still required before collection or training.',
                           'Earlier camera-ray prototypes are retained separately and excluded from this current-runtime report.']}
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--calm-speed',type=float,required=True);parser.add_argument('--combined-speed',type=float,required=True)
    parser.add_argument('--period',type=float,default=4.5);args=parser.parse_args()
    build_report(args.output,args.calm_speed,args.combined_speed,args.period)
