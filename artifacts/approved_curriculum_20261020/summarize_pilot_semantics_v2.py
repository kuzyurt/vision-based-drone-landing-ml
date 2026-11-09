"""Compact read-only reconciliation for closed semantic-pilot traces."""
from pathlib import Path
import json
import h5py
import numpy as np

ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020/semantic_pilots')
NAMES=('visible_start','search_near','search_mid','search_far','search_distractors','yaw_resync','tilt_loss','learner_struggle')

def main():
  for name in NAMES:
    d=ROOT/name
    trace=[json.loads(x) for x in (d/'semantic_camera_trace.jsonl').read_text().splitlines()]
    ann_by={}
    for x in (d/'capture_annotations.jsonl').read_text().splitlines():
      a=json.loads(x);ann_by[round(float(a['capture_s'])*1e6)]=a
    initial=None; rows=[]; transitions=[]; prev=None; owners={}; phases={}; fault=[]
    with h5py.File(d/'observations.h5','r') as h:
      for i,b in enumerate(h['steps']):
        if isinstance(b,bytes):b=b.decode()
        r=json.loads(b);rows.append(r);o=r.get('output',{});g=o.get('learner_diagnostics') or {}
        own=g.get('actual_command_owner','missing')
        owners[own]=owners.get(own,0)+1
        phase=g.get('control_phase',r.get('phase','missing'));phases[phase]=phases.get(phase,0)+1
        if own!=prev and prev is not None:
          dg=g.get('dagger') or {}
          transitions.append({'frame':i,'task_s':r.get('task_time_s'),'from':prev,'to':own,
            'reason':g.get('expert_intervention') or g.get('intervention') or (g.get('dagger') or {}).get('takeover_reason'),
            'control_phase':phase,'metric_valid':g.get('metric_valid'),'metric_confirmed':g.get('metric_confirmed'),
            'metric_age_s':g.get('metric_age_s'),'recovery_active':g.get('recovery_active'),
            'intervention':g.get('intervention'),'expert_intervention':g.get('expert_intervention'),
            'dagger_keys':sorted(dg),'dagger_ownership':dg.get('ownership'),
            'dagger_reason':dg.get('handover_reason') or dg.get('takeover_reason') or dg.get('reason')})
        prev=own
        if own=='evaluation_fault':fault.append(i)
        ob=r.get('observation',{})
        if initial is None and ob.get('image_valid'):
          a=ann_by.get(round(float(ob['image_capture_time_s'])*1e6))
          if a is not None:
            inst=next((z for z in a.get('instances',[]) if z.get('annotation_instance')=='target'),None)
            initial={'frame':i,'capture_s':ob['image_capture_time_s'],'target_pixels':int(inst.get('pixels',0)) if inst else 0,
              'instance_present':inst is not None,'identity':None if inst is None else inst.get('identity'),'annotation_sha':a.get('rgb_sha256')}
    positives=[x for x in trace if int(x.get('target_pixels',0))>0]
    first=positives[0] if positives else None
    robust=next((x for x in positives if int(x.get('target_pixels',0))>=32),None)
    mx=max(trace,key=lambda x:int(x.get('target_pixels',0)),default=None)
    summary=json.loads((d/'summary.json').read_text());result=json.loads((d/'preview_result.json').read_text())
    row={'case':name,'initial':initial,'range_m':json.loads((d/'initial_view_receipt.json').read_text()).get('horizontal_distance_m'),
      'first_positive':first,'first_32px':robust,'max_visible':mx,'trace_rows':len(trace),'owner_counts':owners,'phases':phases,
      'owner_transitions':transitions,'fault_rows':len(fault),'fault_first_last':([fault[0],fault[-1]] if fault else None),
      'outcome':summary.get('outcome'),'result':{k:result.get(k) for k in ['outcome','physical_flight_completed','fault_triggered','fault_frames','observed_progress']}}
    print(json.dumps(row,separators=(',',':')))

if __name__=='__main__':main()
