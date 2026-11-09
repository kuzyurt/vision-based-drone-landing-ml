"""Event-driven bounded packaging, no simulation or teacher collection."""
from pathlib import Path
import collections,datetime,json,os,subprocess,sys,time
import h5py,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent

def save(**value):
 value.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),training_eligible=False)
 path=ROOT/'v15_dagger_packaging_state.json';temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));temp.replace(path)

def main():
 assert not(ROOT/'v15_dagger_packaging_state.json').exists();begin=time.monotonic();episode=ROOT/'expert_visible_native_v15_dagger'
 save(stage='waiting_for_closed_recording',status='running')
 while not(episode/'preview_result.json').exists():
  state=json.loads((ROOT/'expert_v15_dagger_pipeline_state.json').read_text())
  if state['status']in['failed','runtime_evidence_needs_diagnosis','recognizer_gate_failed']:
   save(stage='not_packaged',status='upstream_stopped',upstream=state);return
  if time.monotonic()-begin>1000:raise TimeoutError('Review wait cap reached')
  time.sleep(10)
 result=json.loads((episode/'preview_result.json').read_text());rows=[json.loads(line)for line in(episode/'steps.jsonl').open()]
 rows=[row for row in rows if'observation'in row];assert rows
 interventions=collections.Counter();phases=collections.Counter();owners=collections.Counter();takeovers=[];fault_rows=[];valid_shadow_labels=0;identities=metrics=0;unsupported=[];chosen=[0];seen=set();phase_events=[]
 for index,row in enumerate(rows):
  interventions[str(row['output'].get('intervention'))]+=1
  diag=row['output'].get('learner_diagnostics',{});intent=diag.get('expert_intent',diag.get('expert_shadow_intent',{}));
  ownership=diag.get('dagger',{}).get('ownership',{});owner=diag.get('actual_command_owner',ownership.get('owner','expert'));owners[owner]+=1
  valid_shadow_labels+=int(diag.get('dagger',{}).get('expert_label_valid',False))
  if ownership.get('owner')=='expert' and (not takeovers or takeovers[-1]['handover_index']!=ownership['handover_index']):takeovers.append(dict(time_s=row['task_time_s'],**ownership))
  if diag.get('evaluation_fault_active'):fault_rows.append(row['frame_index'])
  phase=intent.get('phase',diag.get('control_phase','unknown'));phases[phase]+=1
  identified=bool(diag.get('expert_observable_target_confirmed'));metric=bool(diag.get('metric_valid'));identities+=identified;metrics+=metric
  for event,active in[('first_identity',identified),('first_metric',metric),('first_recovery','recovery'in phase),('first_target_alignment',phase=='target_align')]:
   if active and event not in seen:chosen.append(index);seen.add(event);phase_events.append(dict(event=event,time_s=row['task_time_s'],frame=row['frame_index']))
  if index+1<len(rows):
   executed=np.asarray(rows[index+1]['observation']['previous_executed_action']);own=row['observation']['px4']
   if len(executed)==6 and executed[2]>.02 and own.get('armed')and not own.get('landed')and not intent.get('allow_descent',False)and not diag.get('mission_fallback_active',False):
    unsupported.append(dict(time_s=row['task_time_s'],frame=row['frame_index'],phase=phase,actual_next_observation_previous_command=executed.tolist()))
 chosen=sorted(set(chosen+[len(rows)//2,len(rows)-1]))[:8];font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
 sheet=Image.new('RGB',(1280,390*((len(chosen)+1)//2)),(15,20,26))
 with h5py.File(episode/'observations.h5','r')as h:
  for n,i in enumerate(chosen):
   row=rows[i];diag=row['output'].get('learner_diagnostics',{});phase=diag.get('expert_intent',{}).get('phase',diag.get('control_phase','unknown'))
   im=Image.fromarray(h['rgb'][row['frame_index']]);x=n%2*640;y=n//2*390;sheet.paste(im,(x,y))
   ImageDraw.Draw(sheet).text((x+3,y+364),f"t={row['task_time_s']:.2f}s {phase} metric={bool(diag.get('metric_valid'))}",font=font,fill='white')
 sheet.save(ROOT/'v15_dagger_actual_camera_contact_sheet.jpg',quality=94)
 summary=dict(preview=result,rows=len(rows),identity_confirmed_rows=identities,metric_valid_rows=metrics,phase_counts=dict(phases),outer_supervisor_interventions=dict(interventions),phase_events=phase_events,
  unpermitted_boat_descent_rows=unsupported,actual_command_owners=dict(owners),takeovers=takeovers,actual_fault_rows=fault_rows,valid_shadow_label_rows=valid_shadow_labels,executed_action_audit_source='Next actual observation.previous_executed_action; last row excluded; authorized home fallback and own-landed excluded',
  physical_summary=json.loads((episode/'summary.json').read_text()),training_eligible=False,learner_success=False,qualification_gate_passed=False)
 (ROOT/'v15_dagger_actual_preview_audit.json').write_text(json.dumps(summary,indent=2));save(stage='encoding_actual_cameras',status='running',preview=result)
 with(ROOT/'v15_dagger_preview_encode.log').open('x')as log:
  subprocess.run([sys.executable,str(ROOT/'export_actual_review_v13.py'),'--episode',episode.name,'--name','v15_dagger_actual_expert_review','--max-seconds','30'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
 save(stage='ready_for_trace_and_visual_review',status='completed',preview=result,audit='v15_dagger_actual_preview_audit.json',video='v15_dagger_actual_expert_review.mp4',wall_s=time.monotonic()-begin)
if __name__=='__main__':
 try:main()
 except BaseException as error:save(stage='failed',status='failed',error=repr(error));raise
