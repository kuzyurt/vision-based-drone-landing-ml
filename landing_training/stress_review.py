"""Five supplementary review videos; never release training collection."""
from . import paths
from dataclasses import replace
from pathlib import Path
import argparse
import html
import json
import shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from .config import Scenario
from .run_episode import run_episode
from .scene import ROOT
from .gate import file_hash,source_fingerprint
from .audit import audit_episode

def scenarios(report):
    speed=report['selected_calm_target_m_s'];combined=report['selected_combined_target_m_s']
    wave=report['weather']['wave_height'];period=report['weather']['wave_period'];wind=report['weather']['wind_mean_m_s']
    cases=[]
    for i,(name,kind,h,w,v,reverse) in enumerate((
        ('01_high_waves','island',wave,0,.35,False),
        ('02_strong_wind','beach',.02,wind,.35,True),
        ('03_wind_and_waves','city',wave,wind,.35,False),
        ('04_maximum_tested_speed','gravel',0,0,speed,True),
        ('05_fast_wind_and_waves','rock',wave,wind,combined,False))):
        cases.append(Scenario(name=name,kind=kind,world_seed=401+i,path_seed=501+i,seed=2701+i,
                              reverse=reverse,world_rotation_deg=i*43.,distance=20.,height=4.,
                              bearing_deg=(-120,60,180,-60,120)[i],yaw_offset_deg=55. if reverse else 0.,
                              initial_camera_target=not reverse,boat_speed=v,wave_height=h,wave_period=period,
                              wave_direction_deg=(70+i*31)%360,wind_profile='gusty' if w else 'calm',
                              wind_mean_m_s=w,wind_direction_deg=(250+i*43)%360,duration=180.,stress_test=True))
    return cases

def camera_comparison(destination):
    """Static diagnostic, not a flight record: rotate only the actual gimbal."""
    import mujoco
    from .environment import Environment
    from .rendering import ReviewRenderer
    env=Environment(Scenario());q=env.drone.free_qadr
    env.data.qpos[q:q+3]=env.pad_position+[5,0,4];env.data.qpos[q+3:q+7]=[1,0,0,0]
    renderer=ReviewRenderer(env);canvas=Image.new('RGB',(1280,410),(15,21,30));draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    try:
        for i,pan in enumerate((0,90)):
            env.data.qpos[env.drone.camera_qpos]=np.radians([pan,45]);mujoco.mj_forward(env.model,env.data)
            rgb=renderer.view(renderer.onboard,'drone_onboard');canvas.paste(Image.fromarray(rgb),(i*640,50))
            draw.text((i*640+12,14),f'Camera {"forward" if pan==0 else "sideways"} — pan {pan}°, tilt 45°',font=font,fill='white')
        canvas.save(Path(destination)/'camera_corridors.jpg',quality=95)
    finally:renderer.close()

def assemble(destination,report_path):
    destination=Path(destination).resolve();report_path=Path(report_path).resolve()
    report=json.loads(report_path.read_text())
    if report['runtime_source_sha256']!=source_fingerprint(runtime_only=True):raise RuntimeError('Stale speed qualification')
    cases=scenarios(report);summaries=[];audits=[]
    for scenario in cases:
        directory=destination/scenario.name
        summary=json.loads((directory/'summary.json').read_text())
        if summary['scenario']!=scenario.__dict__:raise RuntimeError('Recorded scenario differs from stress plan')
        summaries.append(summary);audits.append(audit_episode(directory,require_landing=False))
    shutil.copyfile(report_path,destination/'speed_report.json')
    shutil.copyfile(ROOT/'build/qualification.json',destination/'qualification.json')
    camera_comparison(destination)
    sheet=Image.new('RGB',(1280,380*3),(15,21,30));draw=ImageDraw.Draw(sheet)
    for i,summary in enumerate(summaries):
        x=i%2*640;y=i//2*380
        with Image.open(destination/summary['scenario']['name']/'frame_0100.jpg') as im:sheet.paste(im.resize((640,360)),(x,y))
        draw.text((x+8,y+362),summary['scenario']['name']+' | '+summary['outcome'],fill='white')
    sheet.save(destination/'contact_sheet.jpg',quality=92)
    audit={'passed':all(a['passed'] for a in audits),'all_landed':all(s['outcome']=='landed' for s in summaries),'episodes':audits}
    (destination/'recording_audit.json').write_text(json.dumps(audit,indent=2))
    links=[]
    for s in summaries:
        name=s['scenario']['name'];sc=s['scenario']
        links.append(f'<section><h2>{html.escape(name)} — {html.escape(s["outcome"])}</h2><p>Boat target {sc["boat_speed"]:.3f} m/s; wave setting {sc["wave_height"]:.2f} m / {sc["wave_period"]:.2f} s; mean wind {sc["wind_mean_m_s"]:.1f} m/s.</p><video controls preload="metadata" width="100%" src="{name}/review.mp4"></video><p><a href="{name}/review.mp4">Download MP4</a> | <a href="{name}/steps.jsonl">Inputs/outputs JSONL</a> | <a href="{name}/observations.h5">Onboard RGB and rows HDF5</a> | <a href="{name}/scenario.json">Scenario</a> | <a href="{name}/summary.json">Summary</a></p></section>')
    (destination/'index.html').write_text('<!doctype html><html><head><meta charset="utf-8"><title>AERODOCK stress review</title></head><body style="max-width:1400px;margin:24px auto;font:18px system-ui;background:#101722;color:#e5edf7"><h1>Five new stress-case videos</h1><p>Original boat CAD visuals; aircraft legs remain visible and collidable. Forward-facing approach, then front/back deck alignment. The grey launch pad is unchanged.</p><p><a href="camera_corridors.jpg">Static camera comparison: the same legs are visible in the side view</a></p><p>Review only. These experiments do not authorize dataset collection or training. Speed results apply to this simulation and controller configuration; inspect the detailed report, failed attempts and hardware limitations.</p><p><a href="speed_report.json">Speed/weather report</a> | <a href="qualification.json">Software/physics checks</a> | <a href="recording_audit.json">Recording audit</a></p><img src="contact_sheet.jpg" width="100%">'+''.join(links)+'</body></html>')
    artifacts={str(p.relative_to(destination)):file_hash(p) for p in destination.rglob('*') if p.is_file() and '/px4/' not in str(p) and p.name!='manifest.json' and p.suffix not in ('.log','.ulg')}
    manifest={'schema':'aerodock.landing.supplementary-review.v1','role':'review','training_eligible':False,
              'training_authorization':False,'source_sha256':source_fingerprint(),'runtime_source_sha256':source_fingerprint(runtime_only=True),
              'episodes':[{'name':s['scenario']['name'],'outcome':s['outcome'],'records':s['records']} for s in summaries],
              'audit_passed':audit['passed'],'all_landed':audit['all_landed'],'artifacts':artifacts}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2));return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/stress_review');parser.add_argument('--instance',type=int,default=0)
    args=parser.parse_args();report=json.loads(args.report.read_text())
    if report['runtime_source_sha256']!=source_fingerprint(runtime_only=True):raise RuntimeError('Stale speed qualification')
    for s in scenarios(report):
        directory=args.output/s.name
        if not (directory/'summary.json').exists():run_episode(s,directory,instance=args.instance)
    assemble(args.output,args.report)
