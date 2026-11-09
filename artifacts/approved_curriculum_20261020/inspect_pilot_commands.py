"""Read-only audit of actual vertical commands versus physical sink motion."""
from pathlib import Path
import json
import h5py
import numpy as np

BASE = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020/semantic_pilots')
CASES = ('visible_start','search_near','search_mid','search_far','search_distractors','yaw_resync','tilt_loss','learner_struggle')

def owner(row):
    out=row.get('output',{})
    d=out.get('learner_diagnostics',{}) or {}
    return d.get('actual_command_owner', d.get('command_owner', 'unknown')), d

def main():
    for name in CASES:
        p=BASE/name/'observations.h5'
        if not p.exists():
            print(json.dumps({'case':name,'missing':True})); continue
        n=bad_cmd=down_vel=both=unknown_down=0
        metric_valid_count=geometry_count=confirmed_count=0
        zvals=[]; examples=[]; owners={}; dist_ids={}
        with h5py.File(p,'r') as h:
            for i, raw in enumerate(h['steps']):
                if isinstance(raw,bytes): raw=raw.decode()
                row=json.loads(raw); out=row.get('output',{}); obs=row.get('observation',{})
                if row.get('terminal'): continue
                a=np.asarray(out.get('executed_action') or [],dtype=float)
                if a.shape != (6,) or not np.isfinite(a).all(): continue
                owner_name,d=owner(row); owners[owner_name]=owners.get(owner_name,0)+1
                z=float(a[2]); zvals.append(z)
                vz=float(obs.get('px4',{}).get('velocity_enu_m_s',[0,0,0])[2])
                age=d.get('metric_age_s'); sigma=d.get('metric_uncertainty_m')
                metric=bool(d.get('metric_valid'))
                confirmed=bool(d.get('metric_confirmed'))
                geometry=bool(confirmed and age is not None and float(age)<=.16 and sigma is not None and float(sigma)<=.15)
                metric_valid_count+=int(metric);confirmed_count+=int(confirmed);geometry_count+=int(geometry)
                commit=bool(d.get('terminal_commit_active'))
                # Project action convention is [forward,right,down,yaw,pan,tilt].
                cmd_down=z>0.02 and not geometry and not commit
                vel_down=vz < -0.08 and not geometry and not commit
                n += 1; bad_cmd += int(cmd_down); down_vel += int(vel_down); both += int(cmd_down and vel_down)
                if vel_down and not cmd_down: unknown_down+=1
                if cmd_down and len(examples)<4:
                    examples.append({'frame':i,'task_s':row.get('task_time_s'),'owner':owner_name,
                      'phase':d.get('control_phase',row.get('phase')),'z_down_cmd':z,'vz_enu':vz,
                      'metric_valid':metric,'metric_confirmed':confirmed,'bounded_geometry':geometry,'metric_age_s':age,
                      'terminal_commit':commit,'clearance_m':row.get('privileged',{}).get('clearance_m'),
                      'guard_reasons':d.get('guard_reasons'),'intervention':out.get('intervention')})
        print(json.dumps({'case':name,'frames':n,'owners':owners,'metric_valid_rows':metric_valid_count,
          'metric_confirmed_rows':confirmed_count,'bounded_geometry_rows':geometry_count,
          'z_down_command_min_max_mean':([float(np.min(zvals)),float(np.max(zvals)),float(np.mean(zvals))] if zvals else None),
          'down_command_without_bounded_geometry':bad_cmd,'sink_velocity_without_bounded_geometry':down_vel,
          'both_command_and_sink':both,'sink_without_down_command':unknown_down,'examples':examples},separators=(',',':')))

if __name__=='__main__': main()
