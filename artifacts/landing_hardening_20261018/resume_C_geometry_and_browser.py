"""Finish unchanged candidate qualification after zero-frame fixture repair.

Never exclude an executed policy flight. Preserve original C plan/report/error
directories; explicitly label its static-geometry amendment and replacement
flights. Operational sources and candidate remain frozen and identical.
"""
from pathlib import Path
import collections,copy,datetime,hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'r7_geometry_resume_state.json'
def save(v):
    v['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=STATE.with_suffix('.tmp');p.write_text(json.dumps(v,indent=2));p.replace(STATE)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def evaluate(cohort,plan,base,workers=8):
    cmd=[sys.executable,str(ROOT/'evaluate_hardening_v5.py'),'--bundle','candidate_r7','--cohort',cohort,'--workers',str(workers),'--full-budget','--mission-safety','--qualification','--instance-base',str(base),'--plan',str(ROOT/plan)]
    with (ROOT/(cohort+'.log')).open('x') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    return json.loads((ROOT/cohort/'report.json').read_text())
def audit(cohort):
    path=ROOT/cohort/'hardening_audit.json'
    if not path.exists():subprocess.run([sys.executable,str(ROOT/'audit_hardening_v2.py'),cohort],check=True)
    return json.loads(path.read_text())
try:
    while True:
        s=json.loads((ROOT/'r7_qualification_state.json').read_text())
        if s['status']=='needs_specific_issue_review':break
        if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime(2026,10,18,10,40,tzinfo=datetime.timezone.utc):
            raise RuntimeError('Insufficient remaining authorized work window; no new run launched')
        save(dict(status='waiting_for_original_C_completion',original_state=s))
        time.sleep(1200)
    report=json.loads((ROOT/'r7_fresh_C60/report.json').read_text())
    assert report['status']=='completed' and report['completed']==report['planned']==60
    assert sha(ROOT/'candidate_r7/policy.json')=='c32bb34d0f22d7334dda67ea7cca911025c75e56244e95287fefeaed1a450d31'
    bad=[x for x in report['results'] if x.get('infrastructure_error')]
    assert bad and all(x['frames']==0 and x['infrastructure_error']=='ValueError: No physically valid inland start at the prescribed radius and height' for x in bad),bad
    receipt=json.loads((ROOT/'inland_phase_preflight_v2/receipt.json').read_text())
    assert receipt['status']=='static_setup_preflight_completed' and receipt['no_policy_evaluated'] and receipt['seeds_and_conditions_unchanged']
    assert {x['name'] for x in bad}=={x['original_case'] for x in receipt['replacements']}
    original_plan=json.loads((ROOT/'r7_fresh_C60/plan.json').read_text())
    for x in receipt['replacements']:
        before=copy.deepcopy(next(j['scenario'] for j in original_plan['cases'] if j['source_case']==x['original_case']))
        after=copy.deepcopy(x['job']['scenario'])
        before.pop('name');after.pop('name');before.pop('boat_start_fraction');after.pop('boat_start_fraction')
        assert before==after, 'Replacement changed more than static starting phase'
    save(dict(status='running_zero_frame_geometry_replacements',original_invalid_setups=[x['name'] for x in bad],replacement_plan_sha256=sha(ROOT/'C_infrastructure_phase_replacement_plan.json')))
    replacement=evaluate('r7_C_geometry_replacements','C_infrastructure_phase_replacement_plan.json',150,min(4,len(bad)))
    assert replacement['completed']==len(bad)
    assert all(not x.get('infrastructure_error') for x in replacement['results'])
    replacement_plan=json.loads((ROOT/'r7_C_geometry_replacements/plan.json').read_text())
    original_sources=ROOT/'r7_fresh_C60/mission_sources'
    for p in original_sources.iterdir():
        if p.is_file():assert sha(p)==sha(ROOT/'r7_C_geometry_replacements/mission_sources'/p.name)
    combined=ROOT/'r7_fresh_C60_geometry_amended';combined.mkdir(exist_ok=False)
    shutil.copytree(original_sources,combined/'mission_sources')
    invalid_names={x['name'] for x in bad}
    results=[x for x in report['results'] if x['name'] not in invalid_names]+replacement['results']
    cases=[x for x in original_plan['cases'] if x['source_case'] not in invalid_names]+replacement_plan['cases']
    assert len(results)==len(cases)==60
    assert len({(x['scenario']['kind'],x['scenario']['world_seed']) for x in cases})==60
    amendment=dict(original_plan_sha256=sha(ROOT/'fresh_edge_C60.json'),geometry_replacement_plan_sha256=sha(ROOT/'C_infrastructure_phase_replacement_plan.json'),
        static_preflight_receipt_sha256=sha(ROOT/'inland_phase_preflight_v2/receipt.json'),excluded_only_zero_frame_infrastructure_errors=bad,
        all_original_executed_flights_retained=True,candidate_unchanged=True,original_frozen_suite_unmodified=True,
        note='Explicit static boat-start phase amendment of impossible over-land fixtures. This is not the unchanged original C60 plan. No policy tuning or executed-flight replacement.')
    (combined/'amendment.json').write_text(json.dumps(amendment,indent=2))
    (combined/'plan.json').write_text(json.dumps(dict(cases=cases,role='final_holdout',geometry_amendment=amendment),indent=2))
    (combined/'report.json').write_text(json.dumps(dict(status='completed',phase=combined.name,bundle=str(ROOT/'candidate_r7'),completed=60,planned=60,
        outcomes=dict(collections.Counter(x['outcome'] for x in results)),results=results,geometry_amendment=amendment),indent=2))
    fresh=audit(combined.name)
    assert fresh['outcomes'].get('landed',0)>=57, fresh['outcomes']
    assert fresh['faults_triggered']>=12, fresh['faults_triggered']
    save(dict(status='running_safety10',fresh_outcomes=fresh['outcomes']))
    evaluate('r7_safety10','safety_holdout10.json',130)
    safety=audit('r7_safety10')
    assert safety['outcomes']=={'home_landed':10}, safety['outcomes']
    assert safety['faults_triggered']==5, safety['faults_triggered']
    save(dict(status='running_one_production_browser_stack_flight',fresh_outcomes=fresh['outcomes'],safety_outcomes=safety['outcomes']))
    runtime=ROOT/'tidewater_runtime';config=json.loads((runtime/'adapter_verified.json').read_text())
    cmd=[config['loader'],'--library-path',config['library_path'],str(runtime/'node-v22.23.2-linux-x64/bin/node'),str(runtime/'app/test/tidewater_landing_r7_browser.mjs')]
    env=os.environ.copy();env.update(TIDEWATER_GPU_BACKEND='vulkan',XDG_RUNTIME_DIR='/tmp',POLICY_PYTHON=str(ROOT.parents[1]/'.venv/bin/python'))
    with (ROOT/'tidewater_stationary_r7_browser.log').open('x') as log:
        subprocess.run(cmd,cwd=runtime/'app',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=360,check=True)
    game=json.loads((ROOT/'tidewater_stationary_r7_browser/report.json').read_text())
    assert game['physical_assessment']['landed'] and not game['gpu_errors'] and not game['physical_assessment']['collision_failure'], game
    save(dict(status='all_gates_passed_requires_final_export',fresh_cohort=combined.name,fresh_outcomes=fresh['outcomes'],safety_outcomes=safety['outcomes'],game_flight_s=game['flight_seconds']))
except BaseException as e:
    save(dict(status='needs_specific_issue_review',error=repr(e)));raise
