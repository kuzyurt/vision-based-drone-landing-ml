"""Combine only audited causal improvements; fresh full qualification remains gated."""
from pathlib import Path
import datetime,hashlib,json,os,select,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent;STATE=ROOT/'combined_r14_builder_v2_state.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(value):
    value['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=STATE.with_suffix('.tmp');p.write_text(json.dumps(value,indent=2)+'\n');p.replace(STATE)
try:
    assert not STATE.exists()
    save(dict(status='waiting_for_owned_paired_audit',review_pid=439323))
    try:fd=os.pidfd_open(439323)
    except ProcessLookupError:fd=None
    if fd is not None:
        ready,_,_=select.select([fd],[],[],3600);os.close(fd);assert ready,'Paired diagnostic review exceeded bounded wait'
    review=json.loads((ROOT/'paired_prototype_review_state.json').read_text())
    assert review['status']=='paired_prototypes_audited_requires_causal_review',review
    assert review['outcomes']=={'approach_r2_cases2':{'landed':2},'near_motion_r2_gravel':{'landed':1}},review['outcomes']
    exercised={}
    for cohort,key,minimum in [('approach_r2_cases2','approach_stopping_limited',12),('near_motion_r2_gravel','nearfield_persistent_velocity_used',100)]:
        report=json.loads((ROOT/cohort/'report.json').read_text());audit=json.loads((ROOT/cohort/'hardening_audit.json').read_text())
        assert audit['status']=='audited'and json.loads((ROOT/cohort/'nearfield_veto_audit.json').read_text())['status']=='passed'
        count=0
        for case in report['results']:
            for line in (Path(case['directory'])/'steps.jsonl').open():
                q=json.loads(line)
                if not q.get('terminal'):count+=bool(q['output']['learner_diagnostics'].get(key))
        assert count>=minimum,(cohort,key,count);exercised[key]=count
    assert sha(ROOT/'candidate_approach_r2/policy.json')=='95caee5b76059fbac2d026eab8640c8858be16d5c07ca10a6580cb049415f6a6'
    assert sha(ROOT/'candidate_near_motion_r2/policy.json')=='77af6dc5032ccd04d52b923f44c6c7466a5d421d26aeafd49dbdd536ce44602d'
    assert not (ROOT/'r12_fresh_E60/report.json').exists()
    dest=ROOT/'candidate_r14';assert not dest.exists()
    shutil.copytree(ROOT/'candidate_approach_r2',dest,ignore=shutil.ignore_patterns('__pycache__'))
    relative='code/landing_training/radio_robust_20261015/controller/marker_policy.py'
    source=(ROOT/'candidate_near_motion_r2'/relative).read_text();p=dest/relative;text=p.read_text()
    start=source.index('        # At the shrinking near-deck footprint')
    end=source.index("        current['_fresh_metric_fit']",start)
    block=source[start:end]
    a='        current = visual_motion(self, current, observation, now, fit, capture=capture)'
    assert text.count(a)==1;text=text.replace(a,a+'\n'+block)
    extra=[line for line in source.splitlines()if line.startswith('        diag.update(nearfield_persistent_velocity_used=')];assert len(extra)==1
    a="        diag.update(visual_motion_ready=current.get('motion_ready', False), visual_motion_window_s=current.get('visual_motion_window_s', 0.))"
    assert text.count(a)==1;text=text.replace(a,a+'\n'+extra[0]);compile(text,str(p),'exec');p.write_text(text)
    config=json.loads((dest/'policy.json').read_text());config.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
    config['combined_r14']=dict(scope='Combination of two separately audited causal development improvements; not qualified until new full gates.',source_approach_policy_sha256=sha(ROOT/'candidate_approach_r2/policy.json'),source_near_policy_sha256=sha(ROOT/'candidate_near_motion_r2/policy.json'),actual_development_branch_frames=exercised,neural_weights_unchanged=True,strict_original_touchdown_and_physics_unchanged=True,new_training=False)
    config['file_hashes']={f.relative_to(dest).as_posix():sha(f)for f in dest.rglob('*')if f.is_file()and f.name!='policy.json'}
    (dest/'policy.json').write_text(json.dumps(config,indent=2)+'\n');digest=sha(dest/'policy.json')
    (ROOT/'r14_pilot5_plan.json').write_bytes((ROOT/'r12_pilot5_plan.json').read_bytes())
    save(dict(status='built_combined_unpromoted_running_full_runtime_branch_probes',candidate_sha256=digest,exercised=exercised))
    for old,old_bundle,old_out,new_name,new_out in [
        ('probe_approach_r2_runtime.py','candidate_approach_r2','approach_r2_runtime_branch_probe.json','probe_r14_approach_runtime.py','r14_approach_runtime_probe.json'),
        ('probe_near_motion_r2_runtime.py','candidate_near_motion_r2','near_motion_r2_runtime_branch_probe.json','probe_r14_near_runtime.py','r14_near_runtime_probe.json')]:
        source=(ROOT/old).read_text().replace(old_bundle,'candidate_r14').replace(old_out,new_out)
        script=ROOT/new_name;assert not script.exists();compile(source,str(script),'exec');script.write_text(source)
        with (ROOT/(new_name+'.log')).open('x')as log:
            subprocess.run([sys.executable,str(script)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
        assert json.loads((ROOT/new_out).read_text())['status']=='passed'
    assert not(ROOT/'r14_pilot5').exists()
    with(ROOT/'r14_pilot5.log').open('x')as log:
        pilot=subprocess.Popen([sys.executable,str(ROOT/'evaluate_hardening_v7.py'),'--bundle','candidate_r14','--cohort','r14_pilot5','--workers','5','--full-budget','--mission-safety','--instance-base','190','--plan',str(ROOT/'r14_pilot5_plan.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    template=(ROOT/'continue_resumed_r12.py').read_text()
    template=template.replace('cfae2590824b63296a370e199b7e832a7eee3c34ae0bdd3dc4c5f5d2515deea4',digest).replace('430933',str(pilot.pid)).replace('r12','r14').replace('coarse_angular_rate_limited','approach_stopping_limited')
    a="    assert exercised>=12,'Angular-rate feedback was not meaningfully exercised'";assert a in template
    b="""    assert exercised>=12,'Stopping feedback was not meaningfully exercised'
    close_exercised=0
    for case in report['results']:
        for line in (Path(case['directory'])/'steps.jsonl').open():
            row=json.loads(line)
            if not row.get('terminal'):close_exercised+=bool(row['output']['learner_diagnostics'].get('nearfield_persistent_velocity_used'))
    assert close_exercised>=100,'Persistent near velocity not exercised'
    assert not (ROOT/'r12_fresh_E60/report.json').exists()
"""
    template=template.replace(a,b)
    flag="'--full-budget','--mission-safety','--qualification'"
    assert flag in template
    template=template.replace(flag,"'--full-budget','--mission-safety','--qualification','--record-all-rgb'")
    coordinator=ROOT/'continue_r14_native.py';assert not coordinator.exists();compile(template,str(coordinator),'exec');coordinator.write_text(template)
    with(ROOT/'continue_r14_native.log').open('x')as log:
        child=subprocess.Popen([sys.executable,str(coordinator)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    receipt=dict(status='combined_five_case_pilot_and_full_gated_coordinator_started',candidate_sha256=digest,pilot_pid=pilot.pid,coordinator_pid=child.pid,native_state='resumed_r14_state.json',qualification_unestablished=True,browser_stage_still_required=True)
    (ROOT/'r14_pipeline_v2_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');save(receipt)
except BaseException as error:
    save(dict(status='needs_specific_issue_review',error=repr(error),broad_evaluation_started=False));raise
