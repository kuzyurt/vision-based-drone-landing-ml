"""Export the complete review bundle without authorizing training collection."""
from . import paths
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw
from .config import review_scenarios
from .run_episode import run_episode
from .gate import file_hash,source_fingerprint
from .scene import ROOT

def export_reviews(destination,limit=None):
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    scenarios=review_scenarios()
    if limit is not None:scenarios=scenarios[:limit]
    summaries=[]
    for scenario in scenarios:
        directory=destination/scenario.name
        if (directory/'summary.json').exists():
            summary=json.loads((directory/'summary.json').read_text())
            if summary.get('failure') or not (directory/'review.mp4').exists():raise RuntimeError('Incomplete previous export: '+str(directory))
            if summary.get('runtime_source_sha256')!=source_fingerprint(runtime_only=True):raise RuntimeError('Runtime changed: choose a new review output directory instead of reusing stale videos')
        else:summary=run_episode(scenario,directory)
        summaries.append(summary)
        print('EXPORTED',scenario.name,summary['outcome'],flush=True)
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
    (destination/'planned_collection.json').write_text(json.dumps(planned_scenarios(),indent=2))
    audit={'passed':False,'reason':'At least ten complete reviews required'}
    if len(summaries)>=10:
        from .audit import audit_bundle
        audit=audit_bundle(destination)
    links='\n'.join(f'<li><h2>{s["scenario"]["name"]}: {s["outcome"]}</h2><video controls preload="metadata" width="100%" src="{s["scenario"]["name"]}/review.mp4"></video><p><a href="{s["scenario"]["name"]}/review.mp4">Download video</a> | <a href="{s["scenario"]["name"]}/steps.jsonl">Recorded input/output rows</a> | <a href="{s["scenario"]["name"]}/observations.h5">Onboard RGB and rows (HDF5)</a> | <a href="{s["scenario"]["name"]}/scenario.json">Scenario</a> | <a href="{s["scenario"]["name"]}/summary.json">Summary</a></p></li>' for s in summaries)
    (destination/'index.html').write_text('<!doctype html><html><head><meta charset="utf-8"><title>AERODOCK review</title></head><body style="max-width:1400px;margin:24px auto;font:18px system-ui;background:#101722;color:#e5edf7"><h1>Landing environment review</h1><p>Review only. Training collection is blocked pending user verification. Inspect all ten videos and their data before approving.</p><img src="contact_sheet.jpg" width="100%"><ol>'+links+'</ol><p><a href="manifest.json">Manifest</a> | <a href="qualification.json">Physics/software qualification</a> | <a href="recording_audit.json">Recording audit</a> | <a href="planned_collection.json">All planned scenarios</a></p></body></html>')
    artifacts={str(p.relative_to(destination)):file_hash(p) for p in destination.rglob('*') if p.is_file() and p.name not in ('manifest.json','approval.json','approval.template.json') and '.ulg' not in p.name and '/px4/' not in str(p) and p.suffix not in ('.log',)}
    manifest={'schema':'aerodock.landing.review.v1','role':'review','training_eligible':False,'source_sha256':source_fingerprint(),'qualification_passed':qualification['passed'] and audit['passed'] and len(summaries)>=10 and all(s['outcome']=='landed' for s in summaries),'episodes':[{'name':s['scenario']['name'],'outcome':s['outcome'],'records':s['records'],'video':s['scenario']['name']+'/review.mp4'} for s in summaries],'artifacts':artifacts,'collection_plan':json.loads((ROOT/'dataset_plan.json').read_text())}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2))
    template={'status':'pending','reviewer':'','manifest_sha256':file_hash(destination/'manifest.json'),'reviewed_episodes':sorted(s['scenario']['name'] for s in summaries),'note':'The user must inspect every video, observation/action record and qualification report before explicitly approving. The agent must not approve its own output.'}
    (destination/'approval.template.json').write_text(json.dumps(template,indent=2))
    return manifest

if __name__=='__main__':
    import signal
    def cancel(signum,frame):raise KeyboardInterrupt('Review export cancelled')
    signal.signal(signal.SIGTERM,cancel)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default=str(ROOT/'outputs/review'));parser.add_argument('--limit',type=int)
    args=parser.parse_args();export_reviews(args.output,args.limit)
