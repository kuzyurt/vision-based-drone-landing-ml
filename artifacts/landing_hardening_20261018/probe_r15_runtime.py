"""Read-only recorded RGB replay; truth scored only after task action."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import copy,importlib,json,sys,time,types
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;bundle=ROOT/'candidate_r15';out=ROOT/'r15_runtime_terminal_motion_probe.json';assert not out.exists()
pkg=types.ModuleType('close_motion_replay');pkg.__path__=[str(bundle/'code/landing_training')];sys.modules[pkg.__name__]=pkg
runtime=importlib.import_module(pkg.__name__+'.radio_robust_20261015.runtime')
marker=importlib.import_module(pkg.__name__+'.radio_robust_20261015.controller.marker_policy')
motion=importlib.import_module(pkg.__name__+'.radio_robust_20261015.controller.visual_acquisition')
memory=importlib.import_module(pkg.__name__+'.radio_robust_20261015.controller.persistent_target')
c=json.loads((bundle/'policy.json').read_text());torch.set_num_threads(1)
policy=runtime.RadioRobustRuntime(bundle/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
captured=None
original=marker.visual_motion
def observed_motion(policy,current,observation,now,fit,*,capture=None):
    global captured
    captured=None
    if fit is not None:
        own=memory.own_state(capture);captured=dict(capture_s=observation['image_capture_time_s'],position_world=(own[0]+own[2]@memory.D@fit['relative_position']).tolist(),fit_relative=fit['relative_position'].tolist(),normal=current['normal'].tolist(),fit_rms=fit['fit_rms_px'])
    return original(policy,current,observation,now,fit,capture=capture)
marker.visual_motion=observed_motion
source=ROOT/'r14_pilot5/freshD_gravel_05';rows=[json.loads(s)for s in (source/'steps.jsonl').open()]
details=[];start=time.monotonic();matched=0;frames=0;active=0;motion_veto=0;minimum_limit=1.;maximum_action_change=0.
with h5py.File(source/'observations.h5')as h:
    for row in rows:
        if row.get('terminal')or row['task_time_s']>54.5:break
        assert time.monotonic()-start<240,'Bounded read-only replay deadline'
        i=row['frame_index'];obs=copy.deepcopy(row['observation']);obs.pop('beacon',None)
        action,diag=policy.act(np.asarray(h['rgb'][i],dtype=np.uint8),obs)
        matched+=diag['control_phase']==row['output']['learner_diagnostics']['control_phase'];frames+=1
        active+=bool(diag.get('nearfield_persistent_velocity_used'))
        plan=diag.get('nearfield_visibility_plan',{})
        if 'visibility_speed_limit_m_s'in plan:
            minimum_limit=min(minimum_limit,plan['visibility_speed_limit_m_s'])
            motion_veto+=bool(plan['relative_speed_m_s']>plan['visibility_speed_limit_m_s'])
        maximum_action_change=max(maximum_action_change,float(np.max(np.abs(np.asarray(action)-row['output']['executed_action']))))
        if captured is not None:
            # Assessment data is appended only AFTER policy has returned.
            entry=dict(task_s=row['task_time_s'],measurement=captured,own_observation=row['observation'],existing_velocity_world=None if policy.controller.visual_velocity_enu is None else policy.controller.visual_velocity_enu.tolist(),memory_estimate=policy.controller.visual_memory.estimate(row['observation']),assessment_only_pad_velocity=row['privileged']['pad_velocity_enu_m_s'],assessment_only_pad_position=row['privileged']['pad_position_enu_m'],phase=diag['control_phase'])
            if entry['memory_estimate']is not None:entry['memory_estimate']={k:v.tolist()if isinstance(v,np.ndarray)else v for k,v in entry['memory_estimate'].items()}
            details.append(entry)
assert active>=150 and motion_veto>=12 and minimum_limit<.04,(active,motion_veto,minimum_limit,frames)
assert maximum_action_change>.005,maximum_action_change
result=dict(status='passed',scope='Actual full RadioRobustRuntime/NN on recorded RGB and own observations. Calibrated terminal-motion veto and persistent velocity branches exercised. Counterfactual decisions, not new flight.',frames=frames,phase_matches=matched,active_near_velocity_frames=active,actual_terminal_motion_veto_frames=motion_veto,minimum_speed_limit_m_s=minimum_limit,maximum_command_change_vs_recorded=maximum_action_change,wall_s=time.monotonic()-start,measurements=details)
out.write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in result.items()if k!='measurements'}))
