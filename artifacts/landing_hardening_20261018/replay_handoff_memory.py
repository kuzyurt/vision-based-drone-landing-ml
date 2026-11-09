"""Read-only causal replay. Physical truth is scored AFTER policy.act only."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import importlib,json,math,sys,types,time
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;bundle=ROOT/'candidate_r4';out=ROOT/'replay_r4_handoff_memory.json';assert not out.exists()
pkg=types.ModuleType('memory_replay');pkg.__path__=[str(bundle/'code/landing_training')];sys.modules[pkg.__name__]=pkg
runtime=importlib.import_module(pkg.__name__+'.radio_robust_20261015.runtime');memory_module=importlib.import_module(pkg.__name__+'.radio_robust_20261015.controller.persistent_target')
c=json.loads((bundle/'policy.json').read_text());torch.set_num_threads(1);policy=runtime.RadioRobustRuntime(bundle/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
source=ROOT/'r4_extended8_development/near_low_camera_handoff';rows=[json.loads(l) for l in (source/'steps.jsonl').open()];details=[];start=time.monotonic();phase_matches=0
with h5py.File(source/'observations.h5') as h:
 for i,f in enumerate(rows):
  if f['task_time_s']>34.4 or f.get('terminal'):break
  observation=f['observation'];action,diag=policy.act(np.asarray(h['rgb'][i],dtype=np.uint8),observation)
  phase_matches+=diag['control_phase']==f['output']['learner_diagnostics']['control_phase']
  state=policy.controller.visual_memory;estimate=state.estimate(observation)
  if f['task_time_s']>=29. and (i%5==0 or diag.get('metric_valid')):
   own=memory_module.own_state(observation);truth=f['privileged'];truth_relative=np.asarray(truth['pad_position_enu_m'])-np.asarray(truth['drone_position_enu_m'])
   relative_error=None if estimate is None else float(np.linalg.norm(estimate['position_world']-own[0]-truth_relative))
   velocity_error=None if estimate is None else float(np.linalg.norm(estimate['velocity_world']-np.asarray(truth['pad_velocity_enu_m_s'])))
   details.append(dict(frame=i,task_s=f['task_time_s'],phase=diag['control_phase'],recorded_phase=f['output']['learner_diagnostics']['control_phase'],metric_acceptance=diag.get('metric_acceptance'),metric_innovation_m=diag.get('metric_innovation_m'),memory_accepted=state.accepted,memory_rejected=state.rejected,memory_age_s=estimate['measurement_age_s'] if estimate else None,memory_sigma_m=estimate['position_sigma_m'] if estimate else None,relative_world_error_for_scoring_m=relative_error,velocity_error_for_scoring_m_s=velocity_error,memory_relative_position=estimate['relative_position'].tolist() if estimate else None,memory_velocity_world=estimate['velocity_world'].tolist() if estimate else None,actual_pad_velocity_for_scoring=truth['pad_velocity_enu_m_s'],neural_pixel=diag.get('learned_center_px'),metric_rms=diag.get('marker_fit_rms_px')))
value=dict(scope='Read-only actual RGB/public-telemetry replay, truth only AFTER action for audit; no new flight/training',frames=i,phase_matches=phase_matches,wall_s=time.monotonic()-start,details=details)
out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({k:v for k,v in value.items() if k!='details'}));print(json.dumps(details[-6:],indent=2))
