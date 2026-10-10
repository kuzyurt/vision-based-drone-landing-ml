"""Check review videos against their raw observation/action recordings."""
from . import paths
import argparse
import json
from pathlib import Path
import subprocess
import h5py
import numpy as np
from usv.procedural_world import World
from .recording import numeric_observation
from .gate import source_fingerprint,safe_review_outcome

def audit_episode(directory,require_landing=True):
    directory=Path(directory)
    summary=json.loads((directory/'summary.json').read_text())
    records=[json.loads(line) for line in (directory/'steps.jsonl').read_text().splitlines()]
    if not records or len(records)!=summary['records']:raise ValueError('Record count mismatch')
    if summary['failure'] or summary['role']!='review' or summary['training_eligible']:raise ValueError('Invalid review role or failed episode')
    if summary.get('preparation_water_clearance_m',0)<5:raise ValueError('Preparation path was not verified over clear water')
    if summary['runtime_source_sha256']!=source_fingerprint(runtime_only=True):raise ValueError('Stale episode runtime')
    if not records[-1].get('terminal'):raise ValueError('Missing terminal observation')
    if require_landing and summary['outcome']!='landed':raise ValueError('Review flight did not land')
    if records[0]['privileged']['vertical_clearance_m']<1.2 or not records[0]['observation']['px4']['armed']:raise ValueError('Recording did not begin airborne')
    if summary['outcome'] not in ('landed','water_strike','collision_failure','abort','timeout','contact_only'):raise ValueError('Unknown terminal outcome')
    if summary['outcome']=='landed' and (records[-1]['observation']['px4']['armed'] or not records[-1]['observation']['px4']['landed']):raise ValueError('Final PX4 state is not landed/disarmed')
    if any(records[-1]['output']['executed_action']) or records[-1]['output']['action_supervision_valid']:raise ValueError('Terminal command is not masked')
    with h5py.File(directory/'observations.h5') as data:
        if data.attrs['role']!='review' or data.attrs['training_eligible']:raise ValueError('Review data incorrectly eligible for training')
        if data['rgb'].shape!=(len(records),360,640,3):raise ValueError('RGB count or shape mismatch')
        for index,row in enumerate(records):
            if json.loads(data['steps'][index])!=row:raise ValueError('HDF5 and JSONL rows differ')
            if row['frame_index']!=index or row['role']!='review':raise ValueError('Frame order/role mismatch')
            if not np.isfinite(numeric_observation(row)).all():raise ValueError('Non-finite policy input')
            action=np.array(row['output']['executed_action'])
            if not np.isfinite(action).all() or np.linalg.norm(action[:2])>2.00001:raise ValueError('Invalid flight command')
            if not -1.00001<=action[2]<=.70001 or abs(action[3])>.50001 or abs(action[4])>np.radians(50)+1e-5 or abs(action[5])>np.radians(40)+1e-5:raise ValueError('Command outside limits')
            if np.max(np.abs(np.array(row['privileged']['dock_joint_m'])-[.4,.46,.46]))>.008:raise ValueError('Dock was not open/raised')
            observation=row['observation']
            if abs(observation['image_delivery_time_s']-observation['image_capture_time_s']-observation['image_age_s'])>1e-6:raise ValueError('Camera timestamp mismatch')
            if index and abs(row['time_s']-records[index-1]['time_s']-.04)>1e-6:raise ValueError('Decision clock is not 25 Hz')
    probe=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_frames','-of','json',str(directory/'review.mp4')],text=True)
    stream=json.loads(probe)['streams'][0]
    if (stream['width'],stream['height'],stream['r_frame_rate'],int(stream['nb_frames']))!=(1280,720,'25/1',len(records)):raise ValueError('Video differs from recording frame count/rate')
    scenario=summary['scenario'];angle=np.radians(scenario['world_rotation_deg'])
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    coast=World(scenario['kind'],scenario['world_seed']).coast@rotation.T
    pad=np.array(records[0]['privileged']['pad_position_enu_m'])[:2]
    nearest=coast[np.argmin(np.linalg.norm(coast-pad,axis=1))]-pad
    forward=np.array(records[0]['privileged']['pad_rotation'])[:2,0]
    signed=forward[0]*nearest[1]-forward[1]*nearest[0]
    if abs(signed)<1:raise ValueError('Coastal side is ambiguous')
    return {'name':summary['scenario']['name'],'passed':True,'frames':len(records),'seconds':len(records)/25,'outcome':summary['outcome'],'phases':summary['phase_counts'],'max_dock_error_m':summary['max_dock_error_m'],'coast_side_relative_to_boat_forward':'left' if signed>0 else 'right','video_matches_records':True,'review_excluded_from_training':True}

def audit_bundle(bundle,allow_fault_outcomes=False):
    bundle=Path(bundle)
    directories=sorted(p.parent for p in bundle.glob('*/summary.json'))
    if len(directories)<10:raise ValueError('At least ten complete review flights are required')
    scenarios=[json.loads((p/'scenario.json').read_text()) for p in directories]
    if {s['kind'] for s in scenarios}!={'island','beach','city','gravel','rock'}:raise ValueError('Five map families required')
    for kind in {s['kind'] for s in scenarios}:
        paired=[s for s in scenarios if s['kind']==kind]
        if {s['reverse'] for s in paired}!={False,True}:raise ValueError('Both route directions required')
        if len({(s['world_seed'],s['path_seed']) for s in paired})!=1:raise ValueError('Route pair uses different map geometry')
    episodes=[]
    for directory in directories:
        summary=json.loads((directory/'summary.json').read_text())
        if allow_fault_outcomes and not safe_review_outcome(summary):
            raise ValueError('Nominal landing failure or unsafe fault outcome: '+directory.name)
        episodes.append(audit_episode(directory,require_landing=not allow_fault_outcomes or summary['outcome']=='landed'))
    report={'passed':True,'scope':'video, serialized records, timing, actuator bounds, airborne start, dock invariants, native PX4 terminal state and map/direction coverage','allow_safe_fault_outcomes':allow_fault_outcomes,'episodes':episodes}
    by_name={e['name']:e for e in report['episodes']}
    for kind in {s['kind'] for s in scenarios}:
        sides={by_name[s['name']]['coast_side_relative_to_boat_forward'] for s in scenarios if s['kind']==kind}
        if sides!={'left','right'}:raise ValueError('Reversed traversal did not change coastal side: '+kind)
    (bundle/'recording_audit.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('bundle');args=parser.parse_args()
    print(json.dumps(audit_bundle(args.bundle),indent=2))
