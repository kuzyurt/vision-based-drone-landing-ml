"""Event-driven audit of all eight closed real flights, not launch success."""
from pathlib import Path
import datetime as dt,hashlib,importlib.util,json,os,select,sys,time
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'search_v39/audit'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def wait(pid):
    try:fd=os.pidfd_open(int(pid))
    except ProcessLookupError:return
    try:p=select.poll();p.register(fd,select.POLLIN);p.poll()
    finally:os.close(fd)
def main():
    OUT.mkdir(exist_ok=False);(OUT/'state.json').write_text(json.dumps(dict(status='waiting_native_closure')))
    wait(json.loads((ROOT/'search_v39/launch.json').read_text())['pid'])
    binding=json.loads((ROOT/'search_v39/candidate_binding.json').read_text());assert sha(binding['checkpoint'])==binding['recognizer_sha256']
    spec=importlib.util.spec_from_file_location('closed_readonly_auditor',ROOT/'audit_semantic_pilots_v4.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    src=ROOT/'search_v39/sources';a.EXPECTED_ACTOR=binding['actor_sha256'];a.EXPECTED_HARNESS=binding['harness_sha256'];a.EXPECTED_RECOGNIZER=binding['recognizer_sha256'];results=[];sheets=[]
    for name in ['visible_start','search_near','search_mid','search_far','search_distractors','yaw_resync','tilt_loss','learner_struggle']:
        a.PILOTS=ROOT/'search_v39/pilots'
        case=a.PILOTS/name
        try:result=a.run_case(name)
        except Exception as e:result=dict(name=name,status='failed',error=repr(e))
        results.append(result);(OUT/(name+'_audit.json')).write_text(json.dumps(result,indent=2,allow_nan=False))
        if not(case/'observations.h5').exists():continue
        with h5py.File(case/'observations.h5','r')as h:
            n=len(h['steps']);indices=np.linspace(0,n-1,6).astype(int).tolist()if n else[]
            fault=result.get('fault_rows',[])
            if fault:indices=sorted(set([0,max(0,fault[0]-5),fault[0]+len(fault)//2,min(n-1,fault[-1]+30),min(n-1,fault[-1]+200),n-1]))
            sheet=Image.new('RGB',(960,420),(16,16,16));draw=ImageDraw.Draw(sheet)
            for k,i in enumerate(indices[:6]):
                row=json.loads(h['steps'][i]);d=row['output'].get('learner_diagnostics')or{};im=Image.fromarray(h['rgb'][i]).resize((320,180));sheet.paste(im,((k%3)*320,(k//3)*210));draw.text(((k%3)*320+3,(k//3)*210+181),f"{name} {row.get('task_time_s',0):.2f}s {d.get('control_phase')}\nowner {d.get('actual_command_owner')} ID {d.get('expert_observable_target_confirmed')} metric {d.get('metric_valid')}",fill='white')
            p=OUT/(name+'_actual_rgb.jpg');sheet.save(p,quality=87);sheets.append(dict(name=name,path=str(p.relative_to(ROOT)),sha256=sha(p)))
    passed=sum(x['status']=='passed'for x in results);receipt=dict(schema='approved.curriculum.gate.v1',gate_id='P02_v39_actual_purpose',status='passed'if passed==8 else'failed',finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),cases_passed=passed,cases_total=8,results=[dict(name=r['name'],status=r['status'],failed_checks=[c for c in r.get('checks',[])if not c['passed']],error=r.get('error'),outcome=r.get('outcome'))for r in results],actual_rgb_sheets=sheets,actor_sha256=a.EXPECTED_ACTOR,harness_sha256=a.EXPECTED_HARNESS,recognizer_static80_gate_still_false=True,bulk_collection_allowed=False,awaiting_agent_actual_rgb_review=True,raw_training_eligibility_granted=False,recognizer_sha256=binding['recognizer_sha256'])
    (OUT/'pilot_gate_receipt.json').write_text(json.dumps(receipt,indent=2));(OUT/'state.json').write_text(json.dumps(dict(status='closed_needs_actual_rgb_review',passed=passed,total=8)));print(json.dumps({k:v for k,v in receipt.items()if k not in ['actual_rgb_sheets']}),flush=True)
if __name__=='__main__':main()
