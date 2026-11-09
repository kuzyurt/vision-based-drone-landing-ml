"""Fast visual replays of the five original failures; no new physics or policy run."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import json,sys,time,math,hashlib,concurrent.futures,multiprocessing,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE))
from landing_training import paths
from collect_domain import save

def matrix_quaternion(mujoco,matrix):
    import numpy as np
    q=np.empty(4);mujoco.mju_mat2Quat(q,np.ascontiguousarray(matrix).ravel());return q

def render(job):
    import numpy as np,mujoco
    from PIL import Image,ImageDraw,ImageFont
    from scipy.spatial.transform import Rotation
    import fast_physics;fast_physics.install()
    import domain_visuals;domain_visuals.install()
    from landing_training.environment import Environment
    from landing_training.config import Scenario
    from landing_training.rendering import ReviewRenderer,VideoWriter
    from landing_training.run_episode import camera_image
    from sim.server import C,D
    source=ROOT/'evaluation_heldout'/job['name']
    rows=[json.loads(line) for line in (source/'steps.jsonl').read_text().splitlines()]
    rows=[r for r in rows if not r.get('terminal',False)]
    scenario=Scenario(**json.loads((source/'scenario.json').read_text()))
    env=Environment(scenario);renderer=ReviewRenderer(env,overview=True)
    out=ROOT/'failure_videos';out.mkdir(exist_ok=True)
    filename=f"{job['number']:02d}_{job['source_case']}.mp4";video=VideoWriter(out/filename,fps=12)
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    font=ImageFont.truetype(font_path,17);small=ImageFont.truetype(font_path,14);large=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
    # Recover the articulated boat root from recorded platform pose, with the
    # exact static CAD/site relationship. No boat position is given to a policy.
    qb=env.boat.free_qadr;qd=env.drone.free_qadr
    env.data.qpos[qb:qb+3]=0.;env.data.qpos[qb+3:qb+7]=[1,0,0,0]
    mujoco.mj_forward(env.model,env.data)
    local_rotation=env.pad_rotation.copy()
    def articulated(values):
        for name,value in zip(('platform_slide','aft_lid_slide','fore_lid_slide'),values):env.data.qpos[env.boat.qadr[name]]=value
        for eq in range(env.model.neq):
            if env.model.eq_type[eq]==mujoco.mjtEq.mjEQ_JOINT and env.model.eq_obj2id[eq]>=0:
                j1,j2=int(env.model.eq_obj1id[eq]),int(env.model.eq_obj2id[eq])
                q2=env.data.qpos[env.model.jnt_qposadr[j2]]
                env.data.qpos[env.model.jnt_qposadr[j1]]=np.polynomial.polynomial.polyval(q2,env.model.eq_data[eq,:5])
    def pose(row):
        truth=row['privileged'];obs=row['observation'];articulated(truth['dock_joint_m'])
        # Platform slides retain orientation. Offset is recomputed for its
        # recorded joint displacement, avoiding a fixed-height approximation.
        env.data.qpos[qb:qb+3]=0.;env.data.qpos[qb+3:qb+7]=[1,0,0,0]
        mujoco.mj_kinematics(env.model,env.data)
        local_position=env.pad_position.copy()
        boat_rotation=np.asarray(truth['pad_rotation'])@local_rotation.T
        env.data.qpos[qb:qb+3]=np.asarray(truth['pad_position_enu_m'])-boat_rotation@local_position
        env.data.qpos[qb+3:qb+7]=matrix_quaternion(mujoco,boat_rotation)
        env.data.qpos[qd:qd+3]=truth['drone_position_enu_m']
        attitude=Rotation.from_euler('xyz',obs['px4']['attitude_ned_rad']).as_matrix()
        env.data.qpos[qd+3:qd+7]=matrix_quaternion(mujoco,C.T@attitude@D)
        env.data.qpos[env.drone.camera_qpos]=obs['gimbal_rad']
        env.data.qvel[:]=0.;env.data.time=row['time_s']
        mujoco.mj_kinematics(env.model,env.data)
        mujoco.mj_camlight(env.model,env.data)
        camera_id=env.model.camera('drone_onboard').id
        assert np.linalg.norm(env.data.cam_xpos[camera_id]-env.drone.position)<.5,'Replay camera is detached from the drone'
        return float(np.max(np.abs(env.pad_position-truth['pad_position_enu_m'])))
    times=np.array([r['task_time_s'] for r in rows]);end=float(times[-1])
    # Realtime detail starts shortly before first accepted pose; otherwise it
    # shows initial search or the first confident false acquisition.
    fits=[r['task_time_s'] for r in rows if r['output']['learner_diagnostics'].get('metric_valid')]
    if fits and fits[0]<60:focus=max(0.,fits[0]-5.)
    elif job['source_case']=='test_beach_14_1':focus=22.
    else:focus=0.
    focus=min(focus,max(0,end-15.))
    timeline=[(min(end,n*10/12),'FULL FLIGHT - 10x') for n in range(math.ceil(end/10*12))]
    timeline += [(min(end,focus+n/12),'DETAIL - NORMAL SPEED') for n in range(15*12)]
    drone_path=np.array([r['privileged']['drone_position_enu_m'][:2] for r in rows])
    boat_path=np.array([r['privileged']['pad_position_enu_m'][:2] for r in rows])
    lo=np.minimum(drone_path.min(0),boat_path.min(0));hi=np.maximum(drone_path.max(0),boat_path.max(0));center=(hi+lo)/2;span=max(12.,float(np.max(hi-lo))*1.15)
    def map_point(point):
        p=(np.asarray(point)-center)/span
        return tuple(np.rint([1080+p[0]*300,545-p[1]*300]).astype(int))
    max_error=0.;started=time.monotonic()
    try:
        for n,(t,chapter) in enumerate(timeline):
            index=int(np.argmin(abs(times-t)));row=rows[index];obs=row['observation'];diag=row['output']['learner_diagnostics']
            max_error=max(max_error,pose(row));external=renderer.overview()
            capture_time=float(obs['image_capture_time_s']);capture_index=int(np.argmin([abs(r['time_s']-capture_time) for r in rows[max(0,index-8):index+1]]))+max(0,index-8)
            pose(rows[capture_index]);onboard=camera_image(renderer.onboard_image(),scenario)
            if not obs['image_valid']:onboard=np.zeros_like(onboard)
            image=Image.new('RGB',(1280,720),(15,21,30));image.paste(Image.fromarray(external).resize((640,360)),(0,50));image.paste(Image.fromarray(onboard),(640,50))
            draw=ImageDraw.Draw(image)
            draw.text((16,10),f"{job['number']}/5  {scenario.kind.upper()}  |  {job['source_case']}  |  NO RADIO",font=large,fill='#ffffff')
            draw.rectangle((0,50,640,80),fill='#172332');draw.text((12,55),'OVERVIEW - RECORDED TRAJECTORY',font=small,fill='#b6dfff')
            draw.rectangle((640,50,1280,80),fill='#172332');draw.text((652,55),'RECONSTRUCTED DRONE CAMERA',font=small,fill='#b6dfff')
            draw.text((20,430),chapter,font=large,fill='#ffcd7a')
            distance=float(np.linalg.norm(np.asarray(row['privileged']['drone_position_enu_m'])[:2]-np.asarray(row['privileged']['pad_position_enu_m'])[:2]))
            action=row['output']['executed_action'];pan,tilt=np.degrees(obs['gimbal_rad']);wind=np.linalg.norm(row['privileged']['wind_enu_m_s'])
            lines=[f"Flight time {row['task_time_s']:6.1f} / {end:.1f} s   |   recorded result: ABORT",
                   f"Phase: {diag['control_phase']}   |   visual confidence {diag.get('pad_visibility_probability',0):.3f}",
                   f"Accepted visual pose: {bool(diag.get('metric_valid'))}   |   boat distance {distance:.1f} m (scoring only)",
                   f"Camera pan {pan%360:6.1f} deg  tilt {tilt:5.1f} deg  |  wind {wind:.1f} m/s",
                   f"Executed forward/right/down: {action[0]:+.2f}  {action[1]:+.2f}  {action[2]:+.2f} m/s",
                   f"Boat {scenario.boat_speed:.2f} m/s  |  waves {scenario.wave_height*100:.1f} cm  |  image delay {obs['image_age_s']:.2f} s"]
            for k,line in enumerate(lines):draw.text((20,477+k*27),line,font=font,fill='#dce5ef')
            draw.text((20,677),'Trace replay; attitude/gimbal estimated from recorded sensors. No new flight or policy run.',font=small,fill='#91a3b7')
            draw.rectangle((914,430,1250,671),outline='#3b526c',width=2)
            draw.line([map_point(p) for p in boat_path],fill='#376b75',width=2);draw.line([map_point(p) for p in drone_path[:index+1:4]],fill='#6686c9',width=2)
            bp=map_point(boat_path[index]);dp=map_point(drone_path[index]);draw.ellipse((bp[0]-5,bp[1]-5,bp[0]+5,bp[1]+5),fill='#55e4ca');draw.ellipse((dp[0]-5,dp[1]-5,dp[0]+5,dp[1]+5),fill='#ffe082')
            draw.text((925,441),'MAP: drone / boat',font=small,fill='#dce5ef')
            video.write(np.asarray(image))
            if n==0:image.save(out/(filename.replace('.mp4','.jpg')))
            if n and n%72==0:
                elapsed=time.monotonic()-started
                print('RENDER',job['source_case'],n,len(timeline),round(elapsed,1),'s',flush=True)
    finally:video.close();renderer.close()
    result=dict(file=filename,source_case=job['source_case'],outcome=job['outcome'],checkpoint_sha256=job['checkpoint_sha256'],
         trace_sha256=hashlib.sha256((source/'steps.jsonl').read_bytes()).hexdigest(),source='original failed policy flight trace, not a new run',
         onboard='reconstruction from recorded position and PX4 attitude/gimbal; original RGB frames were not recorded',
         full_flight_speed=10,detail_speed=1,detail_start_s=focus,detail_duration_s=15,video_seconds=len(timeline)/12,
         rendered_frames=len(timeline),wall_seconds=time.monotonic()-started,pad_reconstruction_max_error_m=max_error)
    save(out/(filename.replace('.mp4','.json')),result);return result

def main():
    out=ROOT/'failure_videos';out.mkdir(exist_ok=False)
    report=json.loads((ROOT/'evaluation_heldout/report.json').read_text());failed=[r for r in report['scenarios'] if r['outcome']!='landed'];assert len(failed)==5
    jobs=[dict(r,number=i+1,checkpoint_sha256=report['checkpoint_sha256']) for i,r in enumerate(failed)]
    save(out/'plan.json',dict(cases=jobs,workers=3,render_only=True,physics_rerun=False))
    results=[];started=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('spawn')) as pool:
        for f in concurrent.futures.as_completed([pool.submit(render,j) for j in jobs]):
            results.append(f.result());save(out/'progress.json',dict(completed=len(results),planned=5,elapsed_s=time.monotonic()-started))
    results.sort(key=lambda r:r['file']);save(out/'manifest.json',dict(videos=results,elapsed_s=time.monotonic()-started,source='trace reconstruction'))
    with tarfile.open(ROOT/'failure_videos.tar','w') as archive:
        for p in out.iterdir():archive.add(p,arcname='failure_videos/'+p.name)
    save(ROOT/'failure_videos_result.json',dict(status='completed',videos=results,archive=str(ROOT/'failure_videos.tar'),
         bytes=(ROOT/'failure_videos.tar').stat().st_size,sha256=hashlib.sha256((ROOT/'failure_videos.tar').read_bytes()).hexdigest(),elapsed_s=time.monotonic()-started))
    print('FIVE_FAILURE_VIDEOS_READY',json.dumps(results),flush=True)

if __name__=='__main__':main()
