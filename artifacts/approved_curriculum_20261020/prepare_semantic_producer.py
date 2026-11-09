"""Derive a new capture producer; never edits the reviewed V31 source package."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'expert_fix_review_20261019/delivery_v31/v31/sources/run_matched_expert_review_v31.py'

def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)

def main():
    text = SOURCE.read_text()
    text = replace_once(text, "    a=p.parse_args();torch.set_num_threads(1)",
        "    p.add_argument('--semantic-contract',required=True)\n"
        "    a=p.parse_args();torch.set_num_threads(1)\n"
        "    semantic=json.loads(Path(a.semantic_contract).read_text())\n"
        "    assert semantic['target_present'] and not a.target_absent, 'Search target must physically remain in the world'\n"
        "    assert semantic['exclude_return_home_and_land_home']\n"
        "    initial_checked=False;semantic_stream=None\n")
    text = replace_once(text, "        bridge.bind_final_rgb(final,current_capture_s=float(env.data.time))",
        "        nonlocal initial_checked,semantic_stream\n"
        "        pending=bridge.pending;seg=pending['seg'];retained=pending['retained_pixels']\n"
        "        ids=next(s.geom_ids for s in bridge.specs if s.name=='target')\n"
        "        target_pixels=int((np.isin(seg[...,0],ids)&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))&retained).sum())\n"
        "        matrix=env.data.cam_xmat[env.model.camera('drone_onboard').id].reshape(3,3);ray=-matrix[:,2]\n"
        "        if env.recording:\n"
        "            if semantic_stream is None:semantic_stream=(out/'semantic_camera_trace.jsonl').open('x')\n"
        "            semantic_stream.write(json.dumps(dict(capture_s=float(env.data.time),target_pixels=target_pixels,view_bearing_rad=math.atan2(float(ray[1]),float(ray[0])),horizontal_ray_norm=float(np.linalg.norm(ray[:2]))))+'\\n')\n"
        "            if not initial_checked:\n"
        "                initial_checked=True\n"
        "                horizontal_distance=float(np.linalg.norm(env.pad_position[:2]-env.drone.position[:2]))\n"
        "                receipt=dict(target_present=True,target_removed=False,target_pixels=target_pixels,initial_camera_target=env.scenario.initial_camera_target,horizontal_distance_m=horizontal_distance,scenario_sha256=sha(a.scenario_file),contract_sha256=sha(a.semantic_contract),actor_input=False)\n"
        "                (out/'initial_view_receipt.json').write_text(json.dumps(receipt,indent=2))\n"
        "                assert env.scenario.camera_blind_seconds==0., 'Initial invisibility must be geometric, not sensor masking'\n"
        "                assert (target_pixels==0) if semantic['initial_target']=='outside_camera' else (target_pixels>0), 'Scenario skipped its declared initial-view task'\n"
        "                lo,hi=semantic['actual_initial_distance_band_m'];assert lo<=horizontal_distance<=hi, receipt\n"
        "        bridge.bind_final_rgb(final,current_capture_s=float(env.data.time))")
    text = replace_once(text, "            self.observer.close();self.external_file.close();super().close()",
        "            if semantic_stream is not None:semantic_stream.close()\n"
        "            self.observer.close();self.external_file.close();super().close()")
    text = replace_once(text,
        "            if diag.get('mission_fallback_active'):\n                progress['mission_fallback_observed']=True",
        "            if diag.get('mission_fallback_active'):\n"
        "                progress['mission_fallback_observed']=True\n"
        "                progress['diagnostic_stop_reason']='boat_task_failed_before_return_home'\n"
        "                action=np.zeros(6);diag['actual_command_owner']='collection_stop_hold'\n"
        "                diag['excluded_home_action']=True;cancel.set()")
    text = replace_once(text,
        "    scenario=Scenario(**json.loads(Path(a.scenario_file).read_text()));scenario.validate()",
        "    scenario=Scenario(**json.loads(Path(a.scenario_file).read_text()));scenario.validate()\n"
        "    assert scenario.camera_blind_seconds==0. and not a.target_absent\n"
        "    assert not scenario.initial_camera_target if semantic['initial_target']=='outside_camera' else True")
    text = text.replace("role='review_not_training'", "role='new_approved_collection_raw_requires_derivative_admission'")
    text = text.replace("pending human review and never training eligible", "raw capture ineligible; approved derivative requires exact source/semantic/label admission")
    text = replace_once(text,
        "    install_home_score(episode,base_environment=SceneEnvironment,remove_boat_visuals=a.target_absent)",
        "    install_home_score(episode,base_environment=SceneEnvironment,remove_boat_visuals=False)")
    compile(text, 'run_semantic_collection_v32.py', 'exec')
    destination = HERE / 'run_semantic_collection_v32.py'
    assert not destination.exists(), 'Do not rewrite a potentially running producer'
    destination.write_text(text)
    (HERE/'producer_derivation.json').write_text(json.dumps({
        'parent_source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'producer_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'actor_weights_changed': False, 'actor_source_changed': False,
        'target_geometry_hidden_or_removed': False,
        'semantic_annotations_actor_input': False,
        'cancel_before_home_commands': True,
        'raw_review_attributes_flipped': False},indent=2))
    print(destination)

if __name__ == '__main__':
    main()
