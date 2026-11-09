"""Audit the actual teacher recording, sensor/annotation split and video."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import h5py
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def main():
    p=argparse.ArgumentParser(); p.add_argument('episode',type=Path); args=p.parse_args()
    out=args.episode
    summary=json.loads((out/'summary.json').read_text())
    receipt=json.loads((out/'source_receipt.json').read_text())
    for name,expected in receipt['sources'].items():
        snapshot=out/'sources'/Path(name).name
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest()==expected
    rows=[json.loads(line) for line in (out/'steps.jsonl').read_text().splitlines()]
    video=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames',
        '-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames,duration',
        '-of','json',str(out/'review.mp4')],text=True))['streams'][0]
    assert len(rows)==summary['frames']==int(video['nb_read_frames'])
    if summary['initial']['random_sample'].get('landing_only'):
        assert 8 <= summary['initial']['range_m'] <= 15
    else:
        assert summary['initial']['range_m']>=80
    assert summary['neural_network_used'] is False and summary['torch_loaded'] is False
    assert all(not r['observation']['beacon']['valid'] for r in rows)
    assert all(not any(k in r['observation'] for k in ('boats','segmentation','target_position','pad_position_enu_m')) for r in rows)
    actions=np.array([r['output']['executed_action'] for r in rows])
    assert np.isfinite(actions).all() and np.max(np.linalg.norm(actions[:,:2],axis=1))<=2.000001
    assert np.max(np.abs(actions[:,3]))<=.500001
    assert np.min(actions[:,2])>=-1.000001 and np.max(actions[:,2])<=.700001
    assert np.max(np.abs(actions[:,4]))<=np.radians(50)+1e-6
    assert np.max(np.abs(actions[:,5]))<=np.radians(40)+1e-6
    assert all(r['privileged']['student_input'] is False for r in rows)
    assert all(not b['identity_supervision_valid'] for r in rows for b in r['privileged']['boats'] if b['range_m']>35)
    # Check the most important control boundary on every issued action.
    lost_translation=[]; landing_without_marker=[]
    first_contact=next((e['time_s'] for e in summary['events'] if e['kind']=='touchdown'),None)
    for r in rows:
        d=r['output']['teacher_diagnostics']; selected=d['selected']
        live=next((v for v in r['privileged']['boats'] if v['key']==selected and v['boat_detection_valid']),None)
        if selected and live is None and np.linalg.norm(r['output']['executed_action'][:2])>1e-6:
            if first_contact is None or r['time_s']<first_contact: lost_translation.append(r['frame_index'])
        if r['phase'] in ('approach','match','descend','recover') and not d['metric_confirmed']:
            landing_without_marker.append(r['frame_index'])
    assert not lost_translation, lost_translation[:10]
    assert not landing_without_marker, landing_without_marker[:10]
    with h5py.File(out/'observations.h5','r') as f:
        assert len(f['rgb'])==len(f['steps'])==len(rows)
        # A compact visual timeline with true raw RGB, no synthetic scene images.
        indices=[0]
        for event in summary['search_events']:
            if event['event'] in ('visual_selection','inspection_rejected_restart_scan_1','scan_2_first_boat','full_scan_1_enter_scan_2'):
                indices.append(min(range(len(rows)),key=lambda i:abs(rows[i]['task_time_s']-event['time_s'])))
        for phase in ('approach','descend','touchdown','confirm'):
            idx=next((i for i,r in enumerate(rows) if r['phase']==phase),None)
            if idx is not None: indices.append(idx)
        indices=sorted(set(indices+[len(rows)-1]))
        if len(indices)>15: indices=[indices[i] for i in np.linspace(0,len(indices)-1,15).astype(int)]
        font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',14)
        sheet=Image.new('RGB',(960,210*((len(indices)+2)//3)),(19,24,32)); draw=ImageDraw.Draw(sheet)
        for n,i in enumerate(indices):
            x=(n%3)*320; y=(n//3)*210
            sheet.paste(Image.fromarray(f['rgb'][i]).resize((320,180)),(x,y))
            r=rows[i]; draw.text((x+4,y+185),f"{r['task_time_s']:.1f}s {r['phase']}",font=font,fill='white')
        sheet.save(out/'contact_sheet.jpg',quality=92)
    result=dict(status='passed',frames=len(rows),video=video,initial_range_m=summary['initial']['range_m'],
        outcome=summary['outcome'],no_radio=True,no_neural_network=True,student_observation_has_no_boat_truth=True,
        no_hidden_selected_translation=True,no_markerless_landing_commands=True,
        search_events=summary['search_events'],physical_events=summary['events'],scan_modes=summary['scan_modes'],
        milestones={name:next((r['task_time_s'] for r in rows if predicate(r)),None) for name,predicate in {
            'target_selected_s':lambda r:r['output']['teacher_diagnostics']['selected']=='target',
            'target_confirmed_s':lambda r:r['output']['teacher_diagnostics']['confirmed'],
            'descent_started_s':lambda r:r['phase']=='descend',
            'landed_s':lambda r:r['outcome']=='landed'}.items()})
    (out/'audit.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
