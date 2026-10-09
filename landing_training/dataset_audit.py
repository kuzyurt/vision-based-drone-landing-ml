"""Inspect production labels, pilot coverage, outcomes, storage and elapsed time."""
import argparse
from collections import Counter
import json
from pathlib import Path
import h5py
import numpy as np
from .collect import planned_scenarios
from .collection_session import atomic_json
from .gate import file_hash
from .recording import numeric_observation

OUTCOMES={'landed','abort','timeout','contact_only','water_strike','collision_failure'}


def fault(scenario):
    return bool(scenario['camera_blind_seconds'] or scenario['beacon_dropout_duration_s'] or scenario['dock_unavailable_seconds'])


def inspect_episode(path,entry,expected):
    directory=path.parent;summary=json.loads((directory/'summary.json').read_text())
    if summary.get('failure'):raise ValueError('Episode execution failed: '+entry['name'])
    if summary.get('role')!=entry['role'] or not summary.get('training_eligible'):raise ValueError('Invalid summary recording eligibility')
    scenario=summary['scenario'];n=summary['records']
    if scenario!=expected['scenario'] or entry['role']!=expected['role']:raise ValueError('Scenario differs from reviewed plan: '+entry['name'])
    if summary['outcome']!=entry['outcome'] or entry['outcome'] not in OUTCOMES:raise ValueError('Outcome mismatch')
    if summary['max_dock_error_m']>.008 or summary['preparation_water_clearance_m']<5:raise ValueError('Dock/preparation invariant violated')
    valid=visible=contact=0;previous=None;first=None;last=None;supervisors=Counter()
    with h5py.File(path,'r') as data,(directory/'steps.jsonl').open() as lines:
        if n<2 or data['rgb'].shape!=(n,360,640,3) or data['steps'].shape!=(n,):raise ValueError('Incomplete episode arrays')
        if data.attrs.get('schema')!='aerodock.landing.v1' or data.attrs['role']!=entry['role'] or not data.attrs['training_eligible']:raise ValueError('Wrong recording eligibility')
        if json.loads(data.attrs['scenario'])!=scenario:raise ValueError('HDF5 scenario mismatch')
        for start in range(0,n,256):
            for index,encoded in enumerate(data['steps'][start:start+256],start):
                row=json.loads(encoded);line=lines.readline()
                if not line or json.loads(line)!=row:raise ValueError('HDF5/JSONL alignment failed')
                if row['frame_index']!=index or row['role']!=entry['role']:raise ValueError('Frame/role order failed')
                if not np.isfinite(numeric_observation(row)).all():raise ValueError('Nonfinite actor input')
                output=row['output'];action=np.asarray(output['executed_action']);teacher=np.asarray(output['expert_bounded_action'])
                for value in (action,teacher):
                    if value.shape!=(6,) or not np.isfinite(value).all() or np.linalg.norm(value[:2])>2.00001 or not -1.00001<=value[2]<=.70001 or abs(value[3])>.50001 or abs(value[4])>np.radians(50)+1e-5 or abs(value[5])>np.radians(40)+1e-5:raise ValueError('Invalid bounded command')
                observation=row['observation'];mission=observation['mission']
                if abs(mission['elapsed_s']-row['task_time_s'])>1e-6 or mission['budget_s']!=scenario['duration']:raise ValueError('Mission clock mismatch')
                if previous is not None:
                    if abs(row['time_s']-previous['time_s']-.04)>1e-6:raise ValueError('Decision clock mismatch')
                    if not np.allclose(observation['previous_executed_action'],previous['output']['executed_action'],rtol=0,atol=1e-8):raise ValueError('Previous-action alignment failed')
                if mission['supervisor']:
                    supervisors[mission['supervisor']]+=1
                    if output['action_supervision_valid']:raise ValueError('Supervisor command was an imitation target')
                if abs(observation['image_delivery_time_s']-observation['image_capture_time_s']-observation['image_age_s'])>1e-6:raise ValueError('Camera clock mismatch')
                if np.max(np.abs(np.asarray(row['privileged']['dock_joint_m'])-[.4,.46,.46]))>.008:raise ValueError('Dock closed/lowered during recording')
                valid+=int(output['action_supervision_valid'] and not row.get('terminal',False));visible+=int(row['privileged']['pad_visible'])
                contact+=int(row['outcome'] in ('stable_contact','landed'))
                if index==0:first=row
                previous=last=row
        if lines.readline():raise ValueError('Extra JSONL records')
    if first['privileged']['vertical_clearance_m']<1.2 or not first['observation']['px4']['armed']:raise ValueError('Episode did not start airborne')
    if not last.get('terminal') or last['outcome']!=entry['outcome'] or np.any(last['output']['executed_action']) or last['output']['action_supervision_valid']:raise ValueError('Terminal label/mask invalid')
    if entry['outcome']=='landed' and (last['observation']['px4']['armed'] or not last['observation']['px4']['landed']):raise ValueError('Landing not confirmed by PX4')
    delta=np.asarray(first['privileged']['pad_position_enu_m'])-first['privileged']['drone_position_enu_m']
    return {'name':entry['name'],'role':entry['role'],'outcome':entry['outcome'],'fault_case':fault(scenario),
            'world_seed':entry['world_seed'],'map':scenario['kind'],'distance_band':expected['distance_band'],
            'weather_group':expected['weather_group'],'reverse':scenario['reverse'],'initial_camera_aimed':scenario['initial_camera_target'],
            'boat_start_fraction':scenario['boat_start_fraction'],'boat_start_progress_m':summary['boat_start_progress_m'],
            'frames':n,'duration_s':last['task_time_s'],'supervised_steps':valid,'visible_steps':visible,'contact_steps':contact,
            'initial_horizontal_distance_m':float(np.linalg.norm(delta[:2])),'initial_marker_visible':first['privileged']['pad_visible'],
            'hdf5_bytes':path.stat().st_size,'supervisor_counts':dict(supervisors)}


def audit_dataset(manifest_path,expected_entries=None,allow_other_planned=False):
    path=Path(manifest_path).resolve();manifest=json.loads(path.read_text())
    if manifest.get('schema')!='aerodock.landing.dataset.v1' or manifest.get('role')!='dataset':raise ValueError('Production dataset manifest required')
    expected=expected_entries if expected_entries is not None else planned_scenarios()['episodes'];by_name={item['scenario']['name']:item for item in expected}
    full_names={item['scenario']['name'] for item in planned_scenarios()['episodes']} if allow_other_planned else set(by_name)
    seen=set();worlds={};rows=[]
    for entry in manifest['episodes']:
        name=entry['name'];artifact=(path.parent/entry['path']).resolve()
        if name not in full_names or not artifact.is_relative_to(path.parent):raise ValueError('Unplanned or escaped episode')
        if name not in by_name:continue
        if name in seen:raise ValueError('Duplicate episode')
        seen.add(name);item=by_name[name]
        if entry['world_seed']!=item['scenario']['world_seed'] or entry['path_seed']!=item['scenario']['path_seed']:raise ValueError('Wrong world/path provenance')
        group=entry['world_seed']
        if group in worlds and worlds[group]!=entry['role']:raise ValueError('World leaks between splits')
        worlds[group]=entry['role'];rows.append(inspect_episode(artifact,entry,item))
    unsafe=[r['name'] for r in rows if r['outcome'] in ('water_strike','collision_failure')]
    nominal_failures=[r['name'] for r in rows if not r['fault_case'] and r['outcome']!='landed']
    missing=sorted(set(by_name)-seen);coverage={}
    for role in ('training','validation','test'):
        subset=[r for r in rows if r['role']==role]
        coverage[role]={field:dict(Counter(str(r[field]) for r in subset)) for field in ('map','distance_band','weather_group','reverse','initial_camera_aimed','outcome')}
    frames=sum(r['frames'] for r in rows);seconds=sum(r['duration_s'] for r in rows)
    return {'schema':'aerodock.landing.dataset-audit.v1','passed':not missing and not unsafe and not nominal_failures,
            'dataset_manifest_sha256':file_hash(path),'review_manifest_sha256':manifest['review_manifest_sha256'],
            'episodes':rows,'episodes_total':len(rows),'frames_total':frames,'splits':dict(Counter(r['role'] for r in rows)),
            'outcomes':dict(Counter(r['outcome'] for r in rows)),'coverage':coverage,
            'missing_episodes':missing,'unsafe_expert_flights':unsafe,'nominal_expert_failures':nominal_failures,
            'mean_episode_seconds':seconds/len(rows) if rows else None,'indexed_hdf5_bytes':sum(r['hdf5_bytes'] for r in rows),
            'feature_cache_bytes':sum(r['frames'] for r in rows if r['role']!='test')*7108,
            'note':'Strict structure/label audit. Full HDF5 SHA256 integrity is checked by the trainer before optimizer work. '
                   'Nominal expert flights must land; fault flights may abort safely. This does not qualify a learned policy.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--pilot',action='store_true');args=parser.parse_args()
    plan=planned_scenarios();entries=plan['episodes'][:plan['pilot_first_episodes']] if args.pilot else plan['episodes']
    try:report=audit_dataset(args.manifest,entries,allow_other_planned=args.pilot)
    except Exception as exc:report={'passed':False,'error':f'{type(exc).__name__}: {exc}'}
    atomic_json(args.output,report);print(json.dumps({k:v for k,v in report.items() if k not in ('episodes','coverage')},indent=2),flush=True)
    raise SystemExit(0 if report['passed'] else 2)


if __name__=='__main__':main()
