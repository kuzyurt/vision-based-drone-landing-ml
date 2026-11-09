"""Read-only spatial audit of all 20 original held-out policy traces."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/domain_training_20261016T134939Z')
OUT = Path(__file__).resolve().parent


def clean(value):
    if isinstance(value, dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):return [clean(v) for v in value]
    if isinstance(value, (float,np.floating)) and not math.isfinite(value):return None
    return value


def stats(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    return dict(n=len(a), median=float(np.median(a)), p90=float(np.percentile(a,90)), max=float(a.max())) if len(a) else None


def rot(yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    return np.array([[c,-s,0],[s,c,0],[0,0,1.]])


def runs(rows, predicate):
    values=[]; start=None
    for i,row in enumerate(rows):
        if predicate(row):
            if start is None:start=i
        elif start is not None:
            values.append((rows[start]['task_time_s'],rows[i-1]['task_time_s']+.04,i-start));start=None
    if start is not None:values.append((rows[start]['task_time_s'],rows[-1]['task_time_s']+.04,len(rows)-start))
    return sorted(values,key=lambda v:v[1]-v[0],reverse=True)


def analyze(case):
    source=ROOT/'evaluation_heldout'/case['name']
    rows=[json.loads(line) for line in (source/'steps.jsonl').read_text().splitlines()]
    rows=[r for r in rows if not r.get('terminal',False)]
    scenario=json.loads((source/'scenario.json').read_text())
    path=[]; tracks=[]; accepted=[]; acquire=[]; gates=collections.Counter(); coarse=collections.Counter()
    motion=[]; acceptance=collections.Counter(); high=collections.Counter(); normals=[]
    D=np.diag([1.,-1.,-1.]); phases=collections.Counter(); transitions=[]; previous=None
    for row in rows:
        p=row['privileged'];o=row['observation'];diag=row['output']['learner_diagnostics'];phase=diag['control_phase']
        phases[phase]+=1;acceptance[diag['metric_acceptance']]+=1
        if phase!=previous:transitions.append(dict(t=round(row['task_time_s'],2),phase=phase));previous=phase
        R=rot(math.pi/2-o['px4']['attitude_ned_rad'][2])
        r=D@R.T@(np.array(p['pad_position_enu_m'])-p['drone_position_enu_m'])
        v=D@R.T@(np.array(p['pad_velocity_enu_m_s'])-p['drone_velocity_enu_m_s'])
        n=D@R.T@np.array(p['pad_rotation'])[:,2]
        true_lateral=float(np.linalg.norm(r-n*np.dot(r,n)))
        dist=float(np.linalg.norm(r[:2]))
        commands=np.array(row['output']['executed_action'])
        closing=float(np.dot(commands[:2],r[:2])/max(.001,dist))
        prob=diag['raw_model_visibility_probability'];visible=p['pad_visible']
        if prob>=.8:high['visible' if visible else 'pad_label_false']+=1
        pix=np.array(p['pad_keypoints_px'])
        projected_size=np.ptp(pix,axis=0) if visible else [np.nan,np.nan]
        item=dict(t=row['task_time_s'],phase=phase,dist=dist,true_lateral=true_lateral,
                  true_rel=r.tolist(),true_v=v.tolist(),true_normal=n.tolist(),
                  visible=bool(visible),prob=prob,metric=diag['metric_valid'],pose=diag.get('pose_valid',False),
                  vertical_clearance=p['vertical_clearance_m'],drone_xy=p['drone_position_enu_m'][:2],boat_xy=p['pad_position_enu_m'][:2],
                  pan=o['gimbal_rad'][0],tilt=o['gimbal_rad'][1],closing_command=closing,
                  age=o['image_age_s'],pad_size=list(map(float,projected_size)),
                  metric_age=diag['metric_age_s'],acceptance=diag['metric_acceptance'],
                  est_rel=None,est_v=None,position_error=None,velocity_error=None,blocked=[])
        if phase.startswith('visual_') and phase!='visual_approach':
            if np.linalg.norm(commands[:2])>.15:
                acquire.append(dict(t=item['t'],closing=closing,visible=visible,prob=prob,dist=dist))
        if 'estimated_relative_position' in diag:
            er=np.array(diag['estimated_relative_position']);ev=np.array(diag['estimated_relative_velocity'])
            error=float(np.linalg.norm(er-r));verror=float(np.linalg.norm(ev-v))
            item.update(est_rel=er.tolist(),est_v=ev.tolist(),position_error=error,velocity_error=verror,
                        estimated_lateral=diag['estimated_lateral_error_m'],estimated_clearance=diag['estimated_clearance_m'],
                        estimated_heading=diag['estimated_heading_error_deg'],estimated_tilt=diag['estimated_deck_tilt_deg'],
                        motion_ready=diag['visual_motion_ready'],motion_window=diag['visual_motion_window_s'])
            conditions=dict(motion=diag['visual_motion_ready'],
                            lateral=diag['estimated_lateral_error_m']+(diag['metric_uncertainty_m'] or 0)<.12,
                            relative_speed=np.linalg.norm(ev[:2])<.18,
                            heading=abs(diag['estimated_heading_error_deg'])<8,
                            deck_tilt=diag['estimated_deck_tilt_deg']<8)
            item['blocked']=[k for k,passed in conditions.items() if not passed]
            if phase not in ['descend','touchdown','touchdown_commit','confirm','disarmed']:
                gates.update(item['blocked'])
                coarse.update(k for k,passed in dict(motion=diag['visual_motion_ready'],
                    lateral=diag['estimated_lateral_error_m']+(diag['metric_uncertainty_m'] or 0)<.4,
                    relative_speed=np.linalg.norm(ev[:2])<.6,
                    heading=abs(diag['estimated_heading_error_deg'])<20,
                    deck_tilt=diag['estimated_deck_tilt_deg']<8,
                    fresh_pose=(diag['metric_age_s'] or 0)<.2,
                    high_clearance=diag['estimated_clearance_m']>2.5).items() if not passed)
            tracks.append(item.copy())
            if item['metric']:accepted.append(item.copy())
        path.append(item)
    longest_search=runs(rows,lambda r:r['output']['learner_diagnostics']['control_phase']=='visual_search')
    vis_runs=runs(rows,lambda r:r['privileged']['pad_visible'])
    fit_runs=runs(rows,lambda r:r['output']['learner_diagnostics']['metric_valid'])
    pose_runs=runs(rows,lambda r:r['output']['learner_diagnostics'].get('pose_valid',False))
    def error_stats(items,key):return stats([x[key] for x in items if x[key] is not None])
    worst=sorted(accepted,key=lambda a:a['position_error'],reverse=True)[:3]
    result=dict(name=case['source_case'],outcome=case['outcome'],frames=len(rows),
        scenario={k:scenario[k] for k in ['kind','distance','height','camera_delay_steps','initial_pan_deg','initial_tilt_deg','boat_speed','wind_profile']},
        initial_distance_m=path[0]['dist'],min_distance_m=min(x['dist'] for x in path),final_distance_m=path[-1]['dist'],
        min_vertical_clearance_m=min(x['vertical_clearance'] for x in path),
        first_pad_visible_s=next((x['t'] for x in path if x['visible']),None),pad_visible_frames=sum(x['visible'] for x in path),
        first_metric_s=next((x['t'] for x in path if x['metric']),None),fit_frames=sum(x['metric'] for x in path),pose_frames=len(tracks),
        accepted_poses_with_logged_position=len(accepted),
        fit_acceptance_counts=dict(acceptance),phases=dict(phases),
        longest_search_s=longest_search[0][1]-longest_search[0][0] if longest_search else 0,
        longest_pad_visible_runs=vis_runs[:4],longest_fit_runs=fit_runs[:4],longest_pose_runs=pose_runs[:4],
        position_error_m=error_stats(tracks,'position_error'),accepted_position_error_m=error_stats(accepted,'position_error'),
        velocity_error_m_s=error_stats(tracks,'velocity_error'),accepted_velocity_error_m_s=error_stats(accepted,'velocity_error'),
        high_score_pad_labels=dict(high),acquisition_moving_frames=len(acquire),
        acquisition_away_frames=sum(x['closing']<-.1 for x in acquire),
        acquisition_toward_frames=sum(x['closing']>.1 for x in acquire),
        acquisition_without_pad_label=sum(not x['visible'] for x in acquire),
        strict_gate_block_counts=dict(gates),coarse_gate_block_counts=dict(coarse),
        pad_pixel_width_when_visible=stats([x['pad_size'][0] for x in path if x['visible']]),
        pad_pixel_height_when_visible=stats([x['pad_size'][1] for x in path if x['visible']]),
        transitions=transitions,worst_accepted=worst,
        trace_sha256=hashlib.sha256((source/'steps.jsonl').read_bytes()).hexdigest())
    (OUT/(case['source_case']+'_series.json')).write_text(json.dumps(clean(path),allow_nan=False,separators=(',',':')))
    # These are diagnostic truth comparisons only, never controller/model inputs.
    return result


def main():
    report=json.loads((ROOT/'evaluation_heldout/report.json').read_text())
    results=[analyze(case) for case in report['scenarios']]
    result=dict(scope='offline original policy trace audit; no new flights, training or controller edits',
        checkpoint_sha256=report['checkpoint_sha256'],cases=results,
        limitations=['Truth r uses recorded body position and measured yaw; estimator origin/age errors contribute.',
                    'Pose error compares the controller-smoothed estimate at decision time with current truth.',
                    'Pad visibility is the original delayed probe label, not whole-boat visibility.',
                    'Raw neural pixels and rejected registration internals were not logged.',
                    'Block counts reconstruct logged conditions; unavailable heading-trust history is not inferred.'])
    (OUT/'audit.json').write_text(json.dumps(clean(result),indent=2,allow_nan=False))
    for case in results:
        print(json.dumps({k:case[k] for k in ['name','outcome','initial_distance_m','min_distance_m','final_distance_m','first_pad_visible_s','pad_visible_frames','first_metric_s','fit_frames','accepted_position_error_m','velocity_error_m_s','acquisition_moving_frames','acquisition_away_frames','strict_gate_block_counts','fit_acceptance_counts']}),flush=True)


if __name__=='__main__':main()
