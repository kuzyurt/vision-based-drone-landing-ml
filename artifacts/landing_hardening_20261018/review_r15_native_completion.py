"""Verify downloaded native evidence and summarize outcomes without re-running flights."""
from pathlib import Path
import hashlib,json,statistics,tarfile
r=Path(__file__).resolve().parent
archive=r/'r15_native_completion_compact.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='cd6ac60abdac2b77cb263bda4146a81484dd663772c5e17e4f8ff57ec69a773e'
out=r/'r15_native_completion_verified'
assert not out.exists();out.mkdir()
with tarfile.open(archive)as t:
    for item in t.getmembers():assert(out/item.name).resolve().is_relative_to(out.resolve())
    t.extractall(out,filter='data')
manifest=json.loads((out/'r15_native_completion_manifest.json').read_text())
for rel,expected in manifest['files'].items():
    assert hashlib.sha256((out/rel).read_bytes()).hexdigest()==expected,rel
review=dict(status='native_evidence_download_hashes_verified_actual_game_pending',files_verified=len(manifest['files']),cohorts={})
for name in ['r15_pilot5','r15_fresh_E60','r15_safety_E10']:
    report=json.loads((out/name/'report.json').read_text())
    audit=json.loads((out/name/'hardening_audit.json').read_text())
    veto=json.loads((out/name/'nearfield_veto_audit.json').read_text())
    assert audit['status']=='audited' and veto['status']=='passed'
    assert report['completed']==report['planned']==len(report['results'])
    assert report['outcomes']==audit['outcomes']
    assert not any(c.get('infrastructure_error')or c['radio_frames'] for c in report['results'])
    review['cohorts'][name]=dict(outcomes=report['outcomes'],maps=audit['maps'],
        faults_triggered=audit['faults_triggered'],
        median_boat_flight_s=audit.get('median_boat_flight_s'),
        range_boat_flight_s=audit.get('range_boat_flight_s'),
        fallback_cases=[dict(name=c['name'],outcome=c['outcome'],seconds=c['task_seconds'],events=c.get('events'))for c in report['results']if c['outcome']!='landed'],
        visibility_audit={k:v for k,v in veto.items()if k!='details'})
(r/'r15_native_completion_review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps(review,indent=2))
