"""Narrow staged perception production contract; does not grant training rights.

Legacy review/approval gates remain unchanged. This is a separate dataset schema,
with simulator labels isolated from actors and explicit later admission required.
"""
from pathlib import Path
import hashlib,json
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_production_contract(root,script,contract_path,scenario_path,output_name,mode,prefix,tilt):
    root=Path(root).resolve();script=Path(script).resolve();contract_path=Path(contract_path).resolve();scenario_path=Path(scenario_path).resolve()
    assert contract_path.is_relative_to(root)and scenario_path.is_relative_to(contract_path.parent)
    c=json.loads(contract_path.read_text());assert c['schema']=='mujoco.perception_curriculum.contract.v1'
    assert c['grants_training_eligibility']is False and c['old_review_recordings_admissible']is False and c['action_targets_admissible']is False
    authority=root/'human_review_response_20261019.json';assert sha(authority)==c['authority_response_sha256']
    assert json.loads(authority.read_text())['future_visual_wait_required']is False
    plan_path=contract_path.parent/'plan.json';assert sha(plan_path)==c['plan_sha256'];plan=json.loads(plan_path.read_text())
    matches=[j for j in plan['jobs']if Path(j['scenario_path']).resolve()==scenario_path];assert len(matches)==1
    job=matches[0];assert job['scenario_sha256']==sha(scenario_path)
    assert mode==job['mode']and bool(prefix)==job['prefix']and bool(tilt)==job['tilt_fault']
    assert (root/output_name).resolve()==(contract_path.parent/'episodes'/job['name']).resolve()
    receipt_path=script.parent/'producer_source_hashes.json';receipt=json.loads(receipt_path.read_text())
    assert receipt['contract_sha256']==sha(contract_path)and receipt['scope']=='staged_perception_only'
    for relative,digest in receipt['files'].items():
        path=(script.parent/relative).resolve();assert path.is_relative_to(script.parent)
        assert sha(path)==digest,'Frozen producer source changed: '+relative
    from landing_training.gate import source_fingerprint
    assert source_fingerprint(runtime_only=True)==c['baseline_runtime_source_sha256'],'Inherited native runtime changed'
    model=root/'hard_scene_probe_v3/hard_scene.mjb';assert sha(model)==c['hard_model_sha256']
    return c,job,sha(contract_path)
