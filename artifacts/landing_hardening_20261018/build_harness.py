"""Derive a separate evaluator; never modify frozen evaluation sources."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).parent
source=ROOT.parent/'vision_first_fusion_20261017/vision_first_fusion_delivery/experiment_sources/evaluate_radio_sweep.py'
text=source.read_text()
def replace(old,new):
    global text
    assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
replace("    cancel=threading.Event();last_fit=None", "    from faults import CameraFault\n    fault=CameraFault(job.get('fault',{}))\n    cancel=threading.Event();last_fit=None")
replace("            obs=copy.deepcopy(observation)","            fault.before(rgb,observation)\n            obs=copy.deepcopy(observation)")
replace("            action,diag=policy.act(rgb,obs)","            action,diag=policy.act(rgb,obs)\n            action,diag=fault.after(action,diag,observation)")
replace("    result.update(radio_setting=job['radio_setting'],mission_safety=job.get('mission_safety',False),boat_visuals_removed_for_test=job.get('remove_boat_visuals',False))", "    result.update(radio_setting=job['radio_setting'],mission_safety=job.get('mission_safety',False),boat_visuals_removed_for_test=job.get('remove_boat_visuals',False),camera_fault=job.get('fault',{}),camera_fault_triggered=fault.start is not None,camera_fault_frames=fault.frames,camera_fault_trigger_clearance_m=fault.trigger_clearance)")
replace("    source_files={'evaluate_development.py':Path(__file__).resolve(),'mission_safety.py':ROOT/'mission_safety_r8.py','mission_integration.py':ROOT/'mission_integration.py','mission_setup.py':ROOT/'mission_setup.py'}", "    source_files={'evaluate_development.py':Path(__file__).resolve(),'faults.py':ROOT/'faults.py','mission_safety.py':ROOT/'mission_helpers/mission_safety.py','mission_integration.py':ROOT/'mission_helpers/mission_integration.py','mission_setup.py':ROOT/'mission_helpers/mission_setup.py'}")
replace("    bundle=ROOT/args.bundle;out=ROOT/args.cohort;out.mkdir(exist_ok=False)","    bundle=ROOT/args.bundle;out=ROOT/args.cohort;out.mkdir(exist_ok=False)\n    if args.workers>8:raise ValueError('This experiment uses at most8 workers on the verified8vCPU VM')")
replace("         no_fresh_holdout_used=True, characterization_only=True, same_scene_all_conditions=True))", "         no_fresh_holdout_used=all(j.get('role')!='final_holdout' for j in jobs),characterization_only=all(j.get('role')!='final_holdout' for j in jobs),same_scene_all_conditions=False))")
(ROOT/'evaluate_hardening.py').write_text(text)
print('Wrote separate evaluator with causal input/action disturbance and explicit provenance.')
