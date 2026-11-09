"""Recorded sensor-boundary decisions only; no trajectory or flight claim."""
from pathlib import Path
import copy,hashlib,json,sys
from collections import deque
import numpy as np
ROOT=Path(__file__).resolve().parent
bundle=ROOT/'candidate_r12'
sys.path.insert(0,str(bundle/'code'))
from landing_training.radio_robust_20261015.controller.marker_policy import MarkerLandingController
from landing_training.radio_robust_20261015.controller.observable_acquisition import acquire_visual
c=json.loads((bundle/'policy.json').read_text())
cases=[]
for name,limit in [('freshD_city_05',6.4),('freshD_beach_10',20.)]:
    ctrl=MarkerLandingController(c['calibration'],c['slew_limits']);frames=[];history=deque(maxlen=256)
    source=ROOT/'r10_pilot4'/name/'steps.jsonl'
    for line in source.open():
        row=json.loads(line)
        if row.get('terminal') or row['task_time_s']>limit:continue
        d=row['output']['learner_diagnostics']
        if 'learned_center_px' not in d:continue
        obs=copy.deepcopy(row['observation'])
        history.append((obs['image_delivery_time_s'],copy.deepcopy(obs)))
        error,capture=min((abs(t-obs['image_capture_time_s']),o)for t,o in history)
        assert abs(error-d['capture_history_error_s'])<1e-8
        ctrl.bearing_capture_observation=copy.deepcopy(capture)
        prediction=np.zeros(15);prediction[12:14]=np.asarray(d['learned_center_px'])/[320.,180.]-1.
        probability=d['pad_visibility_probability']
        a,diag=acquire_visual(ctrl,{'visibility':probability},obs,prediction,finish_action=False)
        assert np.isfinite(a).all() and np.linalg.norm(a[:2])<=2.+1e-9 and a[2]==0.
        frames.append(dict(task_s=row['task_time_s'],observation=obs,capture_observation=capture,prediction=prediction.tolist(),probability=probability,action=a.tolist(),diagnostics={k:diag[k]for k in ['control_phase','view_alignment_required','coarse_horizontal_speed_m_s','observed_elevation_rate_rad_s','forecast_elevation_rate_rad_s','coarse_angular_rate_limited']}))
    cases.append(dict(name=name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),frames=frames))
assert any(f['diagnostics']['coarse_horizontal_speed_m_s'] is not None and f['diagnostics']['coarse_horizontal_speed_m_s']<0 for f in cases[0]['frames'])
assert any(f['diagnostics']['coarse_horizontal_speed_m_s']==2. for f in cases[1]['frames'])
out=dict(scope='Recorded RGB-head outputs and own observations; counterfactual raw decisions only, not simulated flight or neural inference parity.',candidate_sha256=hashlib.sha256((bundle/'policy.json').read_bytes()).hexdigest(),cases=cases)
p=ROOT/'r12_angular_rate_portability_fixtures.json';assert not p.exists();p.write_text(json.dumps(out,separators=(',',':'))+'\n')
print(json.dumps(dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),frames=[len(v['frames'])for v in cases])))
