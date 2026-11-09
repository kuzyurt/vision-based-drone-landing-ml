"""Compact provenance/input-boundary audit; no rendering or new flights."""
from pathlib import Path
import collections,hashlib,json
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    bundle=ROOT/'bundle_spatial_r7';c=json.loads((bundle/'policy.json').read_text())
    bad=[name for name,value in c['file_hashes'].items() if sha(bundle/name)!=value]
    assert not bad,bad
    assert sha(bundle/'pose.pt')=='c2990e69e254cbeddde8dd57d4cf481a2c7daa37735cd96083c7f3095512f5f7'
    assert sha(bundle/'spatial_acquisition.pt')=='b432c1584b778d1959e950e855fcdf78c468d7f5ec7e86b71641f5052a6ce14b'
    t=ROOT/'spatial_acquisition_training';plan=json.loads((t/'plan.json').read_text());consumed=json.loads((t/'consumed_sources.json').read_text())
    assert not plan['test_or_development_frames_used'] and not consumed['development_or_test_rgb_used']
    for f,h in plan['source_manifests'].items():assert sha(Path(f))==h,f
    for j in plan['jobs']:
        assert j['role'] in ['training','validation'] and j['entry']['role']==j['role']
        assert sha(Path(j['entry']['target']))==j['entry']['target_sha256']
    for e in consumed['entries']:assert e['role'] in ['training','validation'] and e['selected_rgb_sha256']
    frozen=ROOT/'fresh_holdout_B60.json';expected=(ROOT/'fresh_holdout_B60.sha256').read_text().split()[0]
    assert sha(frozen)==expected
    final=json.loads(frozen.read_text())['cases'];final_worlds={j['scenario']['world_seed'] for j in final}
    training_worlds=set();scenario_sources=[]
    for e in consumed['entries']:
        p=Path(e['source']).parent/'scenario.json'
        assert p.exists(),str(p)
        d=json.loads(p.read_text());training_worlds.add(d['world_seed']);scenario_sources.append(dict(path=str(p),sha256=sha(p)))
    assert not (final_worlds&training_worlds),final_worlds&training_worlds
    source_hashes=json.loads((ROOT/'bundle_spatial_r7_qualification_sources.json').read_text())
    source_actual={'evaluate_development.py':'evaluate_r7.py','mission_safety.py':'mission_safety_r7.py'}
    for f,h in source_hashes.items():assert sha(ROOT/source_actual.get(f,f))==h,f
    physics_sources=[BASE/'landing_training/environment.py',BASE/'landing_training/run_episode.py',
        ROOT.parent/'domain_training_20261016T134939Z/fast_physics.py',
        ROOT.parent/'domain_training_20261016T134939Z/physics_math.so']
    result=dict(status='provenance_checked_not_flight_qualification',bundle=str(bundle),
        pose_sha256=sha(bundle/'pose.pt'),spatial_sha256=sha(bundle/'spatial_acquisition.pt'),
        training_selected_frames=consumed['totals'],training_episodes=len(consumed['entries']),
        training_manifest_hashes=plan['source_manifests'],training_world_seed_count=len(training_worlds),
        final_world_seed_count=len(final_worlds),world_seed_overlap=[],frozen_final_plan_sha256=expected,
        candidate_files_checked=len(c['file_hashes']),operational_sources=source_hashes,
        physics_sources={str(p):sha(p) for p in physics_sources},
        input_boundary_manual_review=dict(
          runtime='PublicPolicy deep-copies observation and removes the entire beacon before calling actual runtime.',
          missingness='Absent radio fields are neutral after normalization; availability bit is false and uncertainty is explicit.',
          spatial_head='Image features only; no telemetry or simulator state enters spatial heatmap/presence.',
          own_home='Median own PX4 telemetry while disarmed on declared physical launch pad before takeoff.',
          mission_priors='Own home/path, static camera geometry, sea datum and nominal boat deck height; no dynamic boat coordinates.',
          teacher='Expert prepare only before task; task expert act is zero and learner commands drive PX4.',
          simulator_truth='Scenario/spawn setup, labels, offline diagnostics and independent scoring only.',
          scoring='Original boat check_outcomes called unchanged. Home_landed is separate physical support/stability/disarm outcome.',
          identity='Hybrid learned vision / visual registration / explicit controller / native PX4, not end-to-end neural actions or RL.'),
        caveats=['Source/data provenance audit is not proof of universal reliability.','Flight outcomes/radio flags/physical events still require final trace audit.'])
    out=ROOT/'provenance_audit_r7.json';out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
