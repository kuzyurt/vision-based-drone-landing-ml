"""Audit completed flight evidence without rerunning or rendering simulations."""
from pathlib import Path
import argparse,collections,hashlib,json,math
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wilson(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;a=1+z*z/n
    mid=(p+z*z/(2*n))/a;d=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/a
    return [mid-d,mid+d]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('cohort');args=parser.parse_args();cohort=ROOT/args.cohort
    report=json.loads((cohort/'report.json').read_text());assert report['status']=='completed'
    plan=json.loads((cohort/'plan.json').read_text());jobs={x['source_case']:x for x in plan['cases']}
    assert len(report['results'])==report['planned']==len(jobs)
    frozen=json.loads((ROOT/'bundle_spatial_r7_qualification_sources.json').read_text())
    for f,h in frozen.items():assert sha(cohort/'mission_sources'/f)==h
    details=[];problems=[];by_map=collections.defaultdict(collections.Counter);by_distance=collections.defaultdict(collections.Counter)
    for result in report['results']:
        name=result['name'];job=jobs[name];p=Path(result['directory']);summary=json.loads((p/'summary.json').read_text())
        controller=json.loads((p/'controller.json').read_text());assert controller['mission_source_sha256']==frozen
        assert controller['pose_checkpoint_sha256']=='c2990e69e254cbeddde8dd57d4cf481a2c7daa37735cd96083c7f3095512f5f7'
        assert summary['outcome']==result['outcome'] and summary['physics_timestep_s']==.001 and summary['training_eligible'] is False
        assert result.get('infrastructure_error') is None
        rows=[]
        with (p/'steps.jsonl').open() as f:
            for line in f:
                row=json.loads(line)
                if not row.get('terminal'):rows.append(row)
        assert len(rows)==result['frames']
        radio_bad=[];expert_nonzero=[]
        for row in rows:
            d=row['output']['learner_diagnostics'];b=row['observation']['beacon']
            if not d.get('entire_radio_input_removed') or d.get('sx_position_supplied') or d.get('radio_position_available') or d.get('radio_controller_trusted') or b.get('valid') or 'relative_heading_m' in b or 'velocity_heading_m_s' in b:radio_bad.append(row['frame_index'])
            if any(abs(float(x))>1e-12 for x in row['output']['expert_raw_action']):expert_nonzero.append(row['frame_index'])
        assert not radio_bad,(name,radio_bad[:3]);assert not expert_nonzero,(name,expert_nonzero[:3])
        outcome=result['outcome'];events=[e['kind'] for e in summary['events']];last=rows[-1]['observation']['px4']
        if outcome=='landed':
            assert all(k in events for k in ['touchdown','stable_contact','landed'])
            assert not last['armed'] and last['landed']
            assert any('Disarmed by landing' in m for m in summary['px4_messages'])
        if outcome=='home_landed':
            e=next(e for e in summary['events'] if e['kind']=='home_landed')
            assert e['supporting_feet']>=3 and e['stable_disarmed_s']>=2.
            assert not last['armed'] and last['landed']
        by_map[job['scenario']['kind']][outcome]+=1
        by_distance[str(job['scenario']['distance'])][outcome]+=1
        details.append(dict(name=name,outcome=outcome,map=job['scenario']['kind'],distance=job['scenario']['distance'],
            task_seconds=result['task_seconds'],inland=job.get('inland',False),initial_camera_target=job['scenario']['initial_camera_target'],
            radio_input_frames=0,expert_task_action_frames=0,physics_timestep_s=summary['physics_timestep_s'],
            summary_sha256=sha(p/'summary.json'),trace_sha256=sha(p/'steps.jsonl'),controller_sha256=sha(p/'controller.json')))
    counts=collections.Counter(d['outcome'] for d in details);k=counts['landed'];n=len(details)
    value=dict(status='evidence_audited',cohort=args.cohort,planned=n,outcomes=dict(counts),boat_landing_fraction=k/n,
        by_map={k:dict(v) for k,v in by_map.items()},by_distance={k:dict(v) for k,v in by_distance.items()},
        nominal_wilson_95_interval=wilson(k,n),interval_caveat='Descriptive binomial interval; shared worlds/directions are correlated. No universal or hardware reliability claim.',
        inland_cases=sum(d['inland'] for d in details),initial_camera_target_cases=sum(d['initial_camera_target'] for d in details),
        radio_input_frames=0,expert_task_action_frames=0,details=details,
        unchanged_criteria='Original physical >=3 supporting feet, COM in support polygon, all feet inside .28m, relative XY<.1m/s, vertical<.05m/s, tilt/angular<5deg, stable disarmed contact >=2s.')
    (cohort/'evidence_audit.json').write_text(json.dumps(value,indent=2));print(json.dumps({k:v for k,v in value.items() if k!='details'},indent=2))
if __name__=='__main__':main()
