"""Read-only RGB and command diagnosis for the closed failed search pilots."""
from pathlib import Path
import hashlib
import json
import math
import h5py
import numpy as np
from PIL import Image, ImageDraw

BASE = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020/semantic_pilots')
OUT = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020/search_diagnosis')
NAMES = ('search_near', 'search_mid', 'search_far', 'search_distractors')


def angle(a, b):
    return math.degrees(abs(math.atan2(math.sin(a-b), math.cos(a-b))))


def main():
    OUT.mkdir(exist_ok=True)
    report = {'schema':'approved.curriculum.search.diagnosis.v1','cases':[]}
    panels = []
    for name in NAMES:
        root = BASE / name
        trace = [json.loads(x) for x in (root/'semantic_camera_trace.jsonl').open()]
        annotations = {round(json.loads(x)['capture_s']*1e6): json.loads(x)
                       for x in (root/'capture_annotations.jsonl').open()}
        rows = []
        with h5py.File(root/'observations.h5','r') as h5:
            n = h5['steps'].shape[0]
            for i in range(n):
                raw = h5['steps'][i]
                row = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
                obs=row['observation'];diag=(row.get('output') or {}).get('learner_diagnostics') or {}
                rows.append({'i':i,'task_s':float(row.get('task_time_s',0)),
                    'capture_s':float(obs['image_capture_time_s']), 'valid':bool(obs['image_valid']),
                    'metric_valid':bool(diag.get('metric_valid')),
                    'identity':bool(diag.get('expert_observable_target_confirmed')),
                    'phase':diag.get('control_phase'), 'range_source':diag.get('range_source'),
                    'coarse_range':diag.get('coarse_plane_prior_range_m'),
                    'action':(row.get('output') or {}).get('executed_action'),
                    'owner':diag.get('actual_command_owner'),
                    'diag':diag})
            detections = [(int(t['target_pixels']),j,t) for j,t in enumerate(trace)]
            maxpx,maxi,maxt = max(detections, default=(0,None,None))
            first = next(((j,t) for j,t in enumerate(trace) if int(t['target_pixels'])>0),None)
            times = [r['task_s'] for r in rows]
            view_rows=[]
            if first:
                # camera trace and delivered observations share capture timestamps
                bycap={round(r['capture_s']*1e6):r for r in rows}
                for j,t in (('first',first[1]),('max',maxt)):
                    r=bycap.get(round(t['capture_s']*1e6))
                    ann=annotations.get(round(t['capture_s']*1e6),{})
                    target=next((x for x in ann.get('instances',[]) if x.get('annotation_instance')=='target'),{})
                    view_rows.append({'kind':j,'capture_s':t['capture_s'],'trace_target_pixels':t['target_pixels'],
                        'annotation_identity':target.get('identity'),'annotation_bbox':target.get('bbox'),
                        'annotation_pixels':target.get('pixels'),'frame':r['i'] if r else None,
                        'task_s':r['task_s'] if r else None,'metric_valid':r['metric_valid'] if r else None,
                        'identity':r['identity'] if r else None,'phase':r['phase'] if r else None,
                        'range_source':r['range_source'] if r else None,'coarse_range':r['coarse_range'] if r else None,
                        'diag_keys':sorted(r['diag']) if r else None,
                        'diag_identity_keys':{k:v for k,v in (r['diag'].items() if r else []) if any(s in k.lower() for s in ('identity','object','candidate','track','class','design','metric','reason'))}})
            first_t=trace[0] if trace else {}
            bearing_delta=angle(float(first_t.get('view_bearing_rad',0)),float(first[1]['view_bearing_rad'])) if first else None
            case={'name':name,'frames':len(rows),'initial_trace_pixels':first_t.get('target_pixels'),
                'actual_range_m':json.loads((root/'initial_view_receipt.json').read_text()).get('horizontal_distance_m'),
                'first_detection':view_rows[0] if view_rows else None,'max_detection':view_rows[-1] if view_rows else None,
                'max_target_pixels':maxpx,'max_pixels_task_s':maxt.get('capture_s')-first_t.get('capture_s') if maxt else None,
                'bearing_change_to_first_detection_deg':bearing_delta,
                'trace_pixel_counts':{'zero':sum(int(t['target_pixels'])==0 for t in trace),'1_31':sum(1<=int(t['target_pixels'])<32 for t in trace),'32_plus':sum(int(t['target_pixels'])>=32 for t in trace)},
                'owner_changes':[], 'summary':json.loads((root/'summary.json').read_text()),
                'preview':json.loads((root/'preview_result.json').read_text())}
            prev=None
            for r in rows:
                if r['owner']!=prev:
                    case['owner_changes'].append({'frame':r['i'],'task_s':r['task_s'],'owner':r['owner']})
                    prev=r['owner']
            report['cases'].append(case)
            with h5py.File(root/'observations.h5','r') as h5:
                n=h5['rgb'].shape[0]
                if first:
                    key=lambda t: round(float(t['capture_s'])*1e6)
                    trace_by={key(t):t for t in trace}
                    chosen=[]
                    for label,idx in [('initial',0)]: chosen.append((label,idx))
                    for tlabel,t in [('first_target', first[1]) if first else ('none',None),('max_target',maxt)]:
                        if t:
                            rr=next((i for i,r in enumerate(rows) if round(r['capture_s']*1e6)==key(t)),None)
                            if rr is not None: chosen.append((tlabel,rr))
                    if not first:
                        chosen += [(f't{int(s)}',min(n-1,max(0,int((s/ max(1.,rows[-1]['task_s']))*(n-1))))) for s in (10,25,45,65)]
                    seen=set()
                    for label,idx in chosen:
                        if idx in seen:continue
                        seen.add(idx)
                        row=rows[idx]
                        im=Image.fromarray(h5['rgb'][idx]).resize((320,180))
                        tile=Image.new('RGB',(320,206),(20,20,20));tile.paste(im,(0,26))
                        draw=ImageDraw.Draw(tile);draw.text((5,5),f"{name} {label} frame={idx} t={row['task_s']:.1f}s pixels={next((x['target_pixels'] for x in trace if round(x['capture_s']*1e6)==round(row['capture_s']*1e6)),0)}",fill='white')
                        panels.append(tile)
    cols=3;w=320;h=206;rows=(len(panels)+cols-1)//cols
    sheet=Image.new('RGB',(cols*w,rows*h),(32,32,32))
    for i,panel in enumerate(panels):sheet.paste(panel,((i%cols)*w,(i//cols)*h))
    sheet.save(OUT/'failed_search_actual_rgb.jpg',quality=90)
    report['contact_sheet']='failed_search_actual_rgb.jpg'
    (OUT/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'out':str(OUT),'cases':[{k:c[k] for k in ('name','actual_range_m','initial_trace_pixels','max_target_pixels','bearing_change_to_first_detection_deg','trace_pixel_counts','first_detection','max_detection','owner_changes')} for c in report['cases']]},indent=2))


if __name__=='__main__':main()
