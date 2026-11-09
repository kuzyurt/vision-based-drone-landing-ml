"""Re-render the complete recorded trajectory without physics or policy inference.

Vehicle and pad positions are recorded truth. Drone orientation/gimbal use logged
onboard sensors; unrecorded boat heading/trim are approximations. Never claim RGB
equivalence or use these images as training data or benchmark input.
"""
from pathlib import Path
import json
import math
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=Path(r'D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing')
sys.path[:0]=[str(REPO),str(REPO/'artifacts/local_curriculum_20261020')]
import local_paths
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw,ImageFont
from benchmark import runner
from benchmark.common import read,write,sha
from landing_training import environment
from usv.boat_sim import quaternion
from usv.world_render import WorldRenderer
from sim.server import C,D


def main():
    source=Path(r'D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\benchmark\runs\comparison_20261024_qualified\r15-archived-export-67a80a63\waves-waves-moderate-gravel-r0');media=HERE/'video';media.mkdir(exist_ok=True)
    rows=[json.loads(line) for line in (source/'steps.jsonl').read_text().splitlines()]
    result=read(source/'result.json');case=read(source/'case.json')
    assert sha(source/'steps.jsonl')==result['trace_sha256']
    receipt=dict(schema='drone.benchmark.telemetry_video.v1',status='rendering',
        source_trace_sha256=sha(source/'steps.jsonl'),source_result_sha256=sha(source/'result.json'),
        policy_inference_executed=False,physics_rerun=False,training_eligible=False,scored_trial=False,
        reconstructed=True,original_rgb_recording=False,
        exact_fields=['recorded drone position','recorded pad position','recorded task timeline','recorded diagnostics and actions'],
        approximate_fields=['drone orientation from PX4 estimate','gimbal pose from own encoder including noise','boat heading from recorded motion','boat roll/pitch use initial static trim; articulated joints use prepared nominal geometry'],
        frames=0)
    write(media/'reconstruction_validation.json',receipt)
    runtime=read(REPO/'benchmark/environments/runtime.json')
    environment.compile_scene=lambda *a,**kw:mujoco.MjModel.from_binary_path(str(REPO/runtime['scene']))
    env=environment.Environment(runner.make_scenario(case))
    runner.setup_scene(env,case,media)
    renderer=runner.make_renderer(env)
    external=mujoco.Renderer(env.model,height=450,width=800,max_geom=20000)
    renderer.worlds[id(external)]=WorldRenderer(env.model,radius=250)
    for flag in (mujoco.mjtRndFlag.mjRND_SHADOW,mujoco.mjtRndFlag.mjRND_REFLECTION):external.scene.flags[flag]=False
    cam=mujoco.MjvCamera();cam.type=mujoco.mjtCamera.mjCAMERA_FREE
    boat_q=env.boat.free_qadr;drone_q=env.drone.free_qadr
    boat_rotation=env.data.xmat[env.boat.boat].reshape(3,3)
    pad_local=boat_rotation.T@(env.pad_position-env.data.xpos[env.boat.boat])
    initial_euler=Rotation.from_matrix(boat_rotation).as_euler('xyz')
    pads=np.array([r['scoring_only']['pad_position_enu_m'] for r in rows])
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',22)
    small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',20)
    title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',29)
    final=media/'r15_waves_gravel_reconstruction.mp4'
    if final.exists():raise FileExistsError(final)
    partial=media/'r15_waves_gravel_reconstruction.partial.mp4'
    log=(media/'reconstruction_ffmpeg.log').open('x')
    writer=subprocess.Popen(['ffmpeg','-nostdin','-y','-loglevel','error','-f','rawvideo',
        '-pixel_format','rgb24','-video_size','1440x810','-framerate','2.5','-i','pipe:0',
        '-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
        '-movflags','+faststart',str(partial)],stdin=subprocess.PIPE,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    max_drone_error=max_pad_error=0.;began=time.perf_counter()
    try:
        for i in range(0,len(rows),10):
            row=rows[i];s=row['scoring_only'];obs=row['observation'];d=row['diagnostics']
            env.data.time=obs['image_capture_time_s']
            env.data.qpos[drone_q:drone_q+3]=s['drone_position_enu_m']
            r=C.T@Rotation.from_euler('xyz',obs['px4']['attitude_ned_rad']).as_matrix()@D
            q=Rotation.from_matrix(r).as_quat()
            env.data.qpos[drone_q+3:drone_q+7]=q[[3,0,1,2]]
            env.data.qpos[env.drone.camera_qpos]=obs['gimbal_rad']
            low=max(0,i-10);high=min(len(rows)-1,i+10)
            velocity=pads[high,:2]-pads[low,:2]
            yaw=initial_euler[2] if np.linalg.norm(velocity)<.02 else math.atan2(velocity[1],velocity[0])
            boat_r=Rotation.from_euler('xyz',[initial_euler[0],initial_euler[1],yaw]).as_matrix()
            env.data.qpos[boat_q:boat_q+3]=pads[i]-boat_r@pad_local
            env.data.qpos[boat_q+3:boat_q+7]=quaternion(initial_euler[0],initial_euler[1],yaw)
            # Forward kinematics only: do not advance physics or generate new actions.
            mujoco.mj_kinematics(env.model,env.data)
            mujoco.mj_comPos(env.model,env.data)
            mujoco.mj_camlight(env.model,env.data)
            max_drone_error=max(max_drone_error,float(np.linalg.norm(env.drone.position-s['drone_position_enu_m'])))
            max_pad_error=max(max_pad_error,float(np.linalg.norm(env.pad_position-pads[i])))
            onboard=renderer.onboard_image()
            cam.lookat[:]=(env.pad_position+env.drone.position)/2
            cam.distance=max(6.,float(np.linalg.norm(env.pad_position-env.drone.position))*1.15+3.)
            cam.azimuth=math.degrees(env.boat_yaw)+135.;cam.elevation=-23.
            outside=renderer.view(external,cam)
            canvas=Image.new('RGB',(1440,810),'#0d1620')
            canvas.paste(Image.fromarray(outside),(0,50));canvas.paste(Image.fromarray(onboard),(800,50))
            draw=ImageDraw.Draw(canvas)
            draw.text((18,9),'R15 | WAVES 0.15 m / GRAVEL | TELEMETRY RECONSTRUCTION',font=title,fill='#eef4fa')
            draw.text((18,513),'OUTSIDE VIEW',font=title,fill='#8bd0f5')
            draw.text((818,426),'ONBOARD VIEW (reconstructed)',font=title,fill='#8bd0f5')
            distance=math.dist(s['drone_position_enu_m'][:2],s['pad_position_enu_m'][:2])
            left=['Case: 30 m start / 0.6 m/s boat / 0.15 m waves',
                  f"Time: {row['task_s']:.2f} / {result['mission_time_s']:.2f} s",
                  f"Phase: {d.get('control_phase')}",
                  f"Track: {d.get('selected') or 'none'} | Identity confirmed: {bool(d.get('search_identity_confirmed'))}",
                  f'Horizontal distance to boat: {distance:.2f} m',
                  'Final result: MISSION FALLBACK / NO LANDING']
            for j,line in enumerate(left):draw.text((18,559+j*34),line,font=font,fill='#dce7ee')
            right=['Boat radio: ON | Decoys: OFF',
                   f"Metric landing pose: {'valid' if d.get('metric_valid') else 'not established'}",
                   'Positions and timeline: original recorded flight',
                   'Drone attitude/gimbal: logged sensor estimates',
                   'Boat heading/trim: approximate reconstruction',
                   'Not original RGB; no new policy decisions.']
            for j,line in enumerate(right):draw.text((818,483+j*43),line,font=small,fill='#dce7ee' if j<4 else '#f1ce85')
            draw.rectangle((18,797,1422,802),fill='#33434f')
            draw.rectangle((18,797,18+int(1404*row['task_s']/result['mission_time_s']),802),fill='#7ac9f3')
            writer.stdin.write(np.asarray(canvas).tobytes());receipt['frames']+=1
            if i in (0,1000,1900):canvas.save(media/f'r15_wave_reconstruction_{i}.png')
            if i%250==0:
                write(media/'reconstruction_validation.json',dict(receipt,last_task_s=row['task_s']))
                print(json.dumps(dict(task_s=row['task_s'],frames=receipt['frames'])),flush=True)
        writer.stdin.close()
        if writer.wait()!=0:raise RuntimeError('FFmpeg failed')
        assert max_drone_error<1e-8 and max_pad_error<1e-8
        partial.rename(final)
        receipt.update(status='completed',last_task_s=rows[-1]['task_s'],video=final.name,
            video_sha256=sha(final),max_drone_position_error_m=max_drone_error,max_pad_position_error_m=max_pad_error,
            duration_s=receipt['frames']/2.5,wall_seconds=time.perf_counter()-began)
        write(media/'reconstruction_validation.json',receipt)
        print(json.dumps(receipt),flush=True)
    finally:
        if writer.poll() is None:
            try:writer.stdin.close()
            except OSError:pass
            writer.wait()
        log.close();external.close();renderer.close()


if __name__=='__main__':main()
