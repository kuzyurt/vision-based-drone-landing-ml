"""New staged schema and explicit source contract, no prior recording modified."""
from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'run_annotated_development_v22.py').read_text()
s=s.replace("p.add_argument('--annotation-probe-seconds'", "p.add_argument('--scenario-file',required=True);p.add_argument('--staging-contract',required=True);p.add_argument('--omit-overview',action='store_true');p.add_argument('--annotation-probe-seconds'")
needle="    out=ROOT/a.name;out.mkdir(exist_ok=False);check_ports(a.instance,1)"
assert needle in s
s=s.replace(needle,'''    from collection_pipeline.curriculum_contract_v23 import validate_production_contract
    contract,job,contract_sha=validate_production_contract(ROOT,__file__,a.staging_contract,
        a.scenario_file,a.name,a.mode,a.prefix,a.tilt_fault)
    out=ROOT/a.name;out.mkdir(exist_ok=False);check_ports(a.instance,1)
    (out/'staged_production_receipt.json').write_text(json.dumps(dict(
        schema='mujoco.curriculum_candidate.v1',split=job['role'],contract_sha256=contract_sha,
        scope='new supervised perception observations only; not approved action demonstrations',
        original_static_recognition_gate_passed=False,training_eligible=False),indent=2))
    original_recorder=episode.Recorder
    class StagedRecorder(original_recorder):
        def __init__(self,directory,scenario,role='review',**kw):
            super().__init__(directory,scenario,role='review',**kw)
            self.file.attrs.update(schema='mujoco.curriculum_candidate.v1',role='curriculum_candidate',
                split=job['role'],native_engine_role='review',training_eligible=False,
                production_contract_sha256=contract_sha,action_targets_admissible=False)
        def append(self,rgb,row):
            record=dict(row,role='curriculum_candidate',native_engine_role='review',split=job['role'])
            super().append(rgb,record)
    episode.Recorder=StagedRecorder''')
s=s.replace('if self.env.recording and now-self.last_external>=.2:',
            'if self.env.recording and not a.omit_overview and now-self.last_external>=.2:')
s=s.replace("if a.tilt_fault and diag.get('mission_fallback_active'):","if diag.get('mission_fallback_active'):")
s=s.replace("'development_boat_recovery_failed_mission_fallback'","'staged_boat_failure_fallback_started_not_physical_fallback_result'")
s=s.replace("if a.pan==0. and a.distance<=12. and a.mode=='expert':", "if not a.scenario_file and a.pan==0. and a.distance<=12. and a.mode=='expert':")
s=s.replace("    assert bound['ReviewRenderer']is ActualReviewRenderer", "    assert bound['ReviewRenderer']is ActualReviewRenderer\n    assert bound['Recorder']is StagedRecorder")
start=s.index('    scenario=Scenario(name=a.name,')
end=s.index('    before=time.monotonic()',start)
s=s[:start]+"    scenario=Scenario(**json.loads(Path(a.scenario_file).read_text()));scenario.validate()\n"+s[end:]
assert 'episode.Recorder=StagedRecorder'in s and "schema='mujoco.curriculum_candidate.v1'"in s
(root/'run_staged_curriculum_v23.py').write_text(s);compile(s,'run_staged_curriculum_v23.py','exec')
print('Prepared explicit staged perception producer; no training eligibility or legacy gate changes')
