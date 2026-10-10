"""Export the complete review bundle without authorizing training collection."""
from . import paths
import argparse
from dataclasses import asdict
import json
import uuid
from pathlib import Path
from PIL import Image,ImageDraw
from .config import Scenario,review_scenarios
from .run_episode import run_episode
from .gate import file_hash,source_fingerprint,safe_review_outcome
from .scene import ROOT

def export_reviews(destination,limit=None,workers=1,diverse=False):
    from .runtime import cache_lock
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    with cache_lock(path=destination/'.review.lock'):
        return _export_reviews_locked(destination,limit,workers,diverse)

def _export_reviews_locked(destination,limit=None,workers=1,diverse=False):
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    scenarios=review_scenarios()
    if diverse:
        from .review_cases import diverse_review_scenarios
        scenarios=diverse_review_scenarios()
    if limit is not None:scenarios=scenarios[:limit]
    if not 1<=workers<=8:raise ValueError('Review workers must be 1..8')
    summaries=[];pending=[]
    for scenario in scenarios:
        directory=destination/scenario.name
        summary=None
        if (directory/'summary.json').exists():
            try:summary=json.loads((directory/'summary.json').read_text())
            except json.JSONDecodeError:pass
            if summary and not summary.get('failure') and summary.get('runtime_source_sha256')!=source_fingerprint(runtime_only=True):raise RuntimeError('Runtime changed: choose a new review output directory instead of reusing stale videos')
            if summary and summary.get('scenario')!=asdict(scenario):raise RuntimeError('Review scenarios changed: choose a new review output directory')
        if not summary or summary.get('failure') or not (directory/'review.mp4').exists():
            pending.append({'name':scenario.name,'scenario':asdict(scenario),
                            'directory':str(directory),'role':'review','video':True})
            continue
        summaries.append(summary)
    if pending:
        # Check before touching partial recordings: a still-shutting-down job
        # must never have its live output directory moved by a second exporter.
        from .collection_benchmark import check_ports
        check_ports(0 if workers==1 else 160,1 if workers==1 else min(workers,len(pending)))
        for job in pending:
            directory=Path(job['directory'])
            if directory.exists():
                saved=destination/'partial_attempts'/(job['name']+'_'+uuid.uuid4().hex[:8])
                saved.parent.mkdir(exist_ok=True);directory.rename(saved)
    if workers==1:
        for job in pending:
            summary=run_episode(Scenario(**job['scenario']),job['directory'])
            summaries.append(summary);print('EXPORTED',job['name'],summary['outcome'],flush=True)
    elif pending:
        from .execution import iter_jobs
        for result in iter_jobs(pending,min(workers,len(pending)),160):
            summary=json.loads((Path(result['directory'])/'summary.json').read_text())
            summaries.append(summary);print('EXPORTED',result['name'],summary['outcome'],flush=True)
    summaries.sort(key=lambda summary:summary['scenario']['name'])
    sheet=Image.new('RGB',(640*2,380*((len(summaries)+1)//2)),(15,21,30));draw=ImageDraw.Draw(sheet)
    for i,summary in enumerate(summaries):
        directory=destination/summary['scenario']['name'];preview=directory/'frame_0100.jpg'
        if not preview.exists():preview=directory/'frame_0000.jpg'
        x=(i%2)*640;y=(i//2)*380
        with Image.open(preview) as frame:sheet.paste(frame.resize((640,360)),(x,y))
        draw.text((x+8,y+362),summary['scenario']['name']+' | '+summary['outcome'],fill='white')
    sheet.save(destination/'contact_sheet.jpg',quality=92)
    qualification_path=ROOT/'build/qualification.json'
    qualification=json.loads(qualification_path.read_text()) if qualification_path.exists() else {'passed':False,'reason':'qualification not executed'}
    qualification['sibling_checks']={}
    for name in ('original_boat_validation','original_drone_validation'):
        evidence=ROOT/'build'/f'{name}.json'
        if evidence.exists():qualification['sibling_checks'][name]=json.loads(evidence.read_text())
    (destination/'qualification.json').write_text(json.dumps(qualification,indent=2))
    from .collect import planned_scenarios
    plan=planned_scenarios()
    (destination/'planned_collection.json').write_text(json.dumps(plan,indent=2))
    audit={'passed':False,'reason':'At least ten complete reviews required'}
    if len(summaries)>=10:
        from .audit import audit_bundle
        audit=audit_bundle(destination,allow_fault_outcomes=diverse)
    links='\n'.join(f'<li><h2>{s["scenario"]["name"]}: {s["outcome"]}</h2><video controls preload="metadata" width="100%" src="{s["scenario"]["name"]}/review.mp4"></video><p><a href="{s["scenario"]["name"]}/review.mp4">Download video</a> | <a href="{s["scenario"]["name"]}/steps.jsonl">Recorded input/output rows</a> | <a href="{s["scenario"]["name"]}/observations.h5">Onboard RGB and rows (HDF5)</a> | <a href="{s["scenario"]["name"]}/scenario.json">Scenario</a> | <a href="{s["scenario"]["name"]}/summary.json">Summary</a></p></li>' for s in summaries)
    (destination/'index.html').write_text('<!doctype html><html><head><meta charset="utf-8"><title>AERODOCK review</title></head><body style="max-width:1400px;margin:24px auto;font:18px system-ui;background:#101722;color:#e5edf7"><h1>Landing environment review</h1><p>Review only. Training collection is blocked pending user verification. Inspect all ten videos and their data before approving.</p><img src="contact_sheet.jpg" width="100%"><ol>'+links+'</ol><p><a href="manifest.json">Manifest</a> | <a href="qualification.json">Physics/software qualification</a> | <a href="recording_audit.json">Recording audit</a> | <a href="planned_collection.json">All planned scenarios</a></p></body></html>')
    artifacts={str(p.relative_to(destination)):file_hash(p) for p in destination.rglob('*') if p.is_file() and 'partial_attempts' not in p.relative_to(destination).parts and p.name not in ('manifest.json','approval.json','approval.template.json','.review.lock') and '.ulg' not in p.name and '/px4/' not in str(p) and p.suffix not in ('.log',)}
    manifest={'schema':'aerodock.landing.review.v1','role':'review','training_eligible':False,'source_sha256':source_fingerprint(),'review_mode':'diverse' if diverse else 'standard','qualification_passed':qualification['passed'] and qualification.get('runtime_source_sha256')==source_fingerprint(runtime_only=True) and audit['passed'] and len(summaries)>=10 and all(safe_review_outcome(s) if diverse else s['outcome']=='landed' for s in summaries),'episodes':[{'name':s['scenario']['name'],'outcome':s['outcome'],'records':s['records'],'video':s['scenario']['name']+'/review.mp4'} for s in summaries],'artifacts':artifacts,'collection_plan':plan}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2))
    template={'status':'pending','reviewer':'','manifest_sha256':file_hash(destination/'manifest.json'),'reviewed_episodes':sorted(s['scenario']['name'] for s in summaries),'note':'The user must inspect every video, observation/action record and qualification report before explicitly approving. The agent must not approve its own output.'}
    (destination/'approval.template.json').write_text(json.dumps(template,indent=2))
    return manifest

if __name__=='__main__':
    import signal
    def cancel(signum,frame):raise KeyboardInterrupt('Review export cancelled')
    signal.signal(signal.SIGTERM,cancel)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default=str(ROOT/'outputs/review'));parser.add_argument('--limit',type=int);parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--diverse',action='store_true',help='Use ten broader production-envelope scenarios with seven nominal and three fault configurations')
    args=parser.parse_args();export_reviews(args.output,args.limit,args.workers,args.diverse)
