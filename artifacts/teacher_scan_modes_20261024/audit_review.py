"""Inspect the completed recording and export a few actual RGB stills."""
import argparse
import json
from pathlib import Path
import subprocess
import h5py
import numpy as np
from PIL import Image, ImageDraw, ImageFont

p=argparse.ArgumentParser();p.add_argument('episode',type=Path);a=p.parse_args();out=a.episode
rows=[json.loads(line) for line in (out/'steps.jsonl').read_text().splitlines()]
summary=json.loads((out/'summary.json').read_text())
video=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
    '-show_entries','stream=width,height,nb_frames,duration,avg_frame_rate','-of','json',str(out/'review.mp4')],text=True))['streams'][0]
assert int(video['nb_frames'])==len(rows)==summary['frames']
assert video['width']==960 and video['height']==420 and video['avg_frame_rate']=='25/1'
assert summary['initial']['range_m']>=80
assert all(not row['observation']['beacon']['valid'] for row in rows)
assert all(np.isfinite(row['output']['executed_action']).all() for row in rows)
mode_transitions=[];phase_transitions=[];previous_mode=previous_phase=None
for row in rows:
    d=row['output']['learner_diagnostics'];mode=d.get('expert_scan_mode')
    phase=d.get('control_phase')
    if mode!=previous_mode:
        mode_transitions.append(dict(task_s=round(row['task_time_s'],2),mode=mode,
            coverage_deg=round(d.get('expert_scan_coverage_rad',0)*180/np.pi,1)))
        previous_mode=mode
    if phase!=previous_phase:
        phase_transitions.append(dict(task_s=round(row['task_time_s'],2),phase=phase,
            selected=d.get('expert_intent',{}).get('selected_track')))
        previous_phase=phase
audit=dict(outcome=summary['outcome'],stop_reason=summary['stop_reason'],frames=len(rows),video=video,
    mode_transitions=mode_transitions,phase_transitions=phase_transitions,
    frames_with_target_identity=sum(bool(r['output']['learner_diagnostics'].get('expert_observable_target_confirmed')) for r in rows),
    frames_with_metric_pad=sum(bool(r['output']['learner_diagnostics'].get('metric_confirmed')) for r in rows),
    all_radio_absent=True,all_commands_finite=True,initial_range_m=summary['initial']['range_m'],
    final_range_m=rows[-1]['privileged']['range_m'])
decoys=json.loads((out/'decoy_scene.json').read_text())['decoys']
own=rows[-1]['privileged']['drone_position_enu_m']
nearest=min(decoys,key=lambda d:np.linalg.norm(np.asarray(d['position_enu_m'][:2])-own[:2]))
audit['nearest_decoy_at_end_eval']=dict(name=nearest['name'],label=nearest['label'],
    horizontal_distance_m=float(np.linalg.norm(np.asarray(nearest['position_enu_m'][:2])-own[:2])))
(out/'audit.json').write_text(json.dumps(audit,indent=2))
indices={0,len(rows)-1}
first_id=next((i for i,r in enumerate(rows) if r['output']['learner_diagnostics'].get('expert_observable_target_confirmed')),None)
if first_id is not None:indices.add(first_id)
for transitions in (mode_transitions,phase_transitions):
    for t in transitions:
        if t.get('mode')=='scan_2' or t.get('phase') in ('inspect_candidate','target_inspect','target_align'):
            indices.add(min(range(len(rows)),key=lambda i:abs(rows[i]['task_time_s']-t['task_s'])))
indices=sorted(indices)
if len(indices)>8:indices=[indices[i] for i in np.linspace(0,len(indices)-1,8).round().astype(int)]
stills=out/'stills';stills.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
canvas=Image.new('RGB',(1280,400*((len(indices)+1)//2)),(20,25,33))
with h5py.File(out/'observations.h5') as f:
    assert len(f['rgb'])==len(rows) and not f.attrs['training_eligible']
    for k,i in enumerate(indices):
        row=rows[i];im=Image.fromarray(f['rgb'][i]);im.save(stills/f"{row['task_time_s']:06.2f}s.png")
        x=(k%2)*640;y=(k//2)*400;canvas.paste(im,(x,y))
        d=ImageDraw.Draw(canvas);diag=row['output']['learner_diagnostics']
        d.text((x+8,y+367),f"{row['task_time_s']:.2f}s | {diag.get('expert_scan_mode')} | {row['phase']}",font=font,fill='white')
canvas.save(out/'contact_sheet.jpg',quality=90)
print(json.dumps(audit,indent=2))
