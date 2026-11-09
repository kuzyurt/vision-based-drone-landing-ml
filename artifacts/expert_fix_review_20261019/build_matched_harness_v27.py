"""Matched review harness: unchanged V26 actor, explicit original faults/ownership."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';OLD=ROOT/'expert_fix_review_20261019/v26/sources';NEW=ROOT/'expert_fix_review_20261019/v27/sources';NEW.mkdir(parents=True,exist_ok=False)
def change(s,old,new):
    assert old in s,old[:120]
    return s.replace(old,new)
s=(OLD/'run_expert_repair_v26.py').read_text()
s=change(s,"p.add_argument('--fault',choices=['none','gimbal_pan'],default='none')","p.add_argument('--fault',choices=['none','gimbal_pan'],default='none');p.add_argument('--fault-duration',type=float,default=1.2)")
s=change(s,"    assert a.mode=='expert' and not a.prefix,'Expert review only; no learner controls task actions'","    assert (a.mode=='expert' and not a.prefix)or(a.mode=='dagger' and a.prefix),'Explicit teacher-only or physically flown learner roll-in required'\n    assert 0.<a.fault_duration<=2.,'Bounded declared camera disturbance'")
s=change(s,"fault=PhysicalTiltFault(dict(kind='gimbal_tilt',trigger_clearance_m=.65,duration_s=1.6,pan_rate_rad_s=.6981317008) if a.tilt_fault else {})", "fault=PhysicalTiltFault(dict(kind='gimbal_tilt' if a.tilt_fault else 'gimbal_pan',trigger_clearance_m=.65,duration_s=1.6 if a.tilt_fault else a.fault_duration,pan_rate_rad_s=.6981317008) if a.tilt_fault or a.fault=='gimbal_pan' else {})")
s=change(s,"            if own.get('armed') and not own.get('landed'):\n                action,diag=fault.after(action,diag,observation)","            if own.get('armed') and not own.get('landed') and (a.mode=='expert' or diag.get('dagger',{}).get('ownership',{}).get('owner')=='policy'):\n                action,diag=fault.after(action,diag,observation)")
s=change(s,"candidate_actor_alone=True,no_teacher_handover=True,","candidate_actor_alone=False,teacher_only=a.mode=='expert',no_teacher_handover=a.mode=='expert',")
s=change(s,"note='Full hybrid candidate acts alone; bounded development, not fresh qualification or action-imitation training. No oracle or external expert task commands.'","note='Replacement EXPERT REVIEW, pending human review and never training eligible. Explicit teacher/fault/learner ownership preserved. Same scenario/native physics and strict physical scoring; no oracle task commands.'")
compile(s,'run_matched_expert_review_v27.py','exec');path=NEW/'run_matched_expert_review_v27.py';path.write_text(s)
(NEW/'harness_binding.json').write_text(json.dumps(dict(harness_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),actor_sources='expert_fix_review_20261019/v26/sources/target_learning',actor_changed=False,
    original_quarantine_preserved=True,training_eligible=False,changes=['bounded original pan/tilt fault declarations','explicit mixed prefix mode','fault commands only with declared actual authority','honest review ownership metadata']),indent=2))
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*[str(p.relative_to(ROOT))for p in NEW.iterdir()]],check=True)
