"""Render-only ocean diagnostic and paired capture benchmark; no flight/data collection."""
from . import paths
import argparse
import importlib.util
import json
import time
from pathlib import Path
import mujoco
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from .config import Scenario
from .environment import Environment
from .gate import file_hash,source_fingerprint
from .rendering import ReviewRenderer,VideoWriter

def preview(destination,baseline_path):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('landing_training._ocean_baseline',baseline_path)
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    cases=(('Calm water',0.,'calm',0.),('High waves',.5,'calm',0.),('Wind and high waves',.5,'gusty',8.))
    report={'role':'render-only diagnostic; poses held fixed, not a flight or training recording',
            'baseline_renderer_sha256':file_hash(baseline_path),'current_renderer_sha256':file_hash(Path(__file__).with_name('rendering.py')),
            'runtime_source_sha256':source_fingerprint(runtime_only=True),
            'controller_physics_sha256':source_fingerprint(runtime_only=True,include_rendering=False),
            'texture_size':[256,256],'texture_refresh_hz':5,'texture_world_tile_m':12,
            'water_vertices':10201,'water_triangles':20000,'shadows':False,'reflections':False,'cases':[]}
    writer=VideoWriter(destination/'comparison.mp4')
    try:
        for case_index,(name,height,wind,speed) in enumerate(cases):
            env=Environment(Scenario(wave_height=height,wave_period=4.5,wind_profile=wind,wind_mean_m_s=speed,stress_test=True))
            q=env.drone.free_qadr;env.data.qpos[q:q+3]=env.pad_position+[-5,0,4]
            env.data.qpos[q+3:q+7]=[1,0,0,0];env.data.qpos[env.drone.camera_qpos]=np.radians([0,45])
            mujoco.mj_forward(env.model,env.data)
            before=baseline.ReviewRenderer(env);after=ReviewRenderer(env)
            tid=env.model.texture('tex_water').id;adr=int(env.model.tex_adr[tid]);size=int(env.model.tex_width[tid]*env.model.tex_height[tid]*env.model.tex_nchannel[tid])
            original=env.model.tex_data[adr:adr+size].copy()
            physics_arrays={key:getattr(env.model,key).copy() for key in ('body_mass','body_inertia','geom_contype','geom_conaffinity','geom_friction')}
            state_arrays={key:getattr(env.data,key).copy() for key in ('qpos','qvel','ctrl')}
            timings={'before':[],'after':[]};generation_checks=[]
            try:
                for renderer in (before,after):
                    for _ in range(3):renderer.capture()
                candidate_pixels=env.model.tex_data[adr:adr+size].copy()
                for frame in range(100):
                    env.data.time=frame/25
                    # Alternate timing order to avoid systematic warm-cache bias.
                    captures={}
                    for label,renderer in ((('before',before),('after',after)) if frame%2==0 else (('after',after),('before',before))):
                        if label=='before':env.model.tex_data[adr:adr+size]=original
                        else:
                            # Baseline uses the same model but a different GL
                            # context. Restore candidate pixels without forcing
                            # regeneration/upload between its two cameras.
                            if after.water_texture_tick is not None:
                                env.model.tex_data[adr:adr+size]=candidate_pixels
                        start=time.perf_counter();captures[label]=renderer.capture();timings[label].append(time.perf_counter()-start)
                        if label=='after':candidate_pixels=env.model.tex_data[adr:adr+size].copy()
                    generation_checks.append(after.water_texture_generation)
                    canvas=Image.new('RGB',(1280,720),(15,21,30))
                    for column,label in enumerate(('before','after')):
                        external,onboard=captures[label]
                        canvas.paste(Image.fromarray(external).resize((640,360)),(column*640,0))
                        canvas.paste(Image.fromarray(onboard),(column*640,360))
                    draw=ImageDraw.Draw(canvas)
                    draw.rectangle((0,0,1280,32),fill=(15,21,30))
                    draw.text((12,5),'BEFORE: untextured wave mesh',font=font,fill='white')
                    draw.text((652,5),'AFTER: textured waves, 5 Hz ripple tile',font=font,fill='white')
                    draw.rectangle((0,684,1280,720),fill=(15,21,30))
                    draw.text((12,691),f'{name} | H={height:.2f} m / T=4.5 s | render diagnostic, fixed vehicle poses; no flight labels',font=font,fill='#f5cf79')
                    writer.write(np.asarray(canvas))
                    if frame==50:canvas.save(destination/f'{case_index+1:02d}_comparison.jpg',quality=95)
                    if frame%25==0:print(name,frame,'/100',flush=True)
                for key,value in physics_arrays.items():np.testing.assert_array_equal(getattr(env.model,key),value)
                for key,value in state_arrays.items():np.testing.assert_array_equal(getattr(env.data,key),value)
                np.testing.assert_allclose(env.boat._positions(),[.4,.46,.46],atol=.001)
                self_stats={label:{'median_ms':float(np.median(values)*1000),'p95_ms':float(np.percentile(values,95)*1000),'samples':len(values)} for label,values in timings.items()}
                self_stats['median_change_percent']=(self_stats['after']['median_ms']/self_stats['before']['median_ms']-1)*100
                self_stats['animation_refreshes_in_4s']=generation_checks[-1]-generation_checks[0]+1
                report['cases'].append({'name':name,'wave_height_m':height,'timing':self_stats,'physics_and_pose_unchanged':True,'dock_open_raised':True})
            finally:before.close();after.close()
    finally:writer.close()
    report['artifacts']={p.name:file_hash(p) for p in destination.glob('*comparison*') if p.suffix in ('.mp4','.jpg')}
    (destination/'report.json').write_text(json.dumps(report,indent=2))
    (destination/'index.html').write_text('<!doctype html><html><meta charset="utf-8"><title>Ocean texture comparison</title><body style="background:#101722;color:#e5edf7;max-width:1280px;margin:24px auto;font:18px system-ui"><h1>Ocean texture comparison</h1><p>Left: previous renderer. Right: explicit world-anchored ocean texture with cached 5 Hz ripple animation. Three fixed-pose render diagnostics: calm water, high waves, and wind with high waves. These are not flights or training data. Dock open and raised; drone legs remain visible.</p><video controls width="100%" src="comparison.mp4"></video><p><a href="comparison.mp4">MP4</a> | <a href="report.json">Measured performance and provenance</a></p></body></html>')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('landing_training/outputs/ocean_texture_preview'))
    parser.add_argument('--baseline',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(preview(args.output,args.baseline),indent=2))
