"""Short rendering of an existing flight trace; no new flight or policy test."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import sys,json,time,math,hashlib
from pathlib import Path
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
ROOT=Path(__file__).resolve().parent
OLD=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
sys.path[:0]=[str(BASE),str(OLD),str(ROOT)]
from landing_training import paths
import numpy as np,mujoco
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial.transform import Rotation
import fast_physics;fast_physics.install()
import domain_visuals;domain_visuals.install()
from mission_setup import VerticalLaunchEnvironment
from landing_training.config import Scenario
from landing_training.rendering import ReviewRenderer,VideoWriter
from landing_training.run_episode import camera_image
from sim.server import C,D

started=time.monotonic();source=ROOT/'flights/wrong_bias_5m_east'
rows=[json.loads(l) for l in (source/'steps.jsonl').read_text().splitlines()]
scenario=Scenario(**json.loads((source/'scenario.json').read_text()))
env=VerticalLaunchEnvironment(scenario);renderer=ReviewRenderer(env,overview=True)
out=ROOT/'wrong_radio_5m_trace_replay';out.mkdir(exist_ok=False)
video_path=out/'wrong_radio_5m.mp4';video=VideoWriter(video_path,fps=12)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',16)
small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
large=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',23)
qb=env.boat.free_qadr;qd=env.drone.free_qadr
env.data.qpos[qb:qb+3]=0;env.data.qpos[qb+3:qb+7]=[1,0,0,0]
mujoco.mj_forward(env.model,env.data);local_rotation=env.pad_rotation.copy()
def quat(matrix):
    q=np.empty(4);mujoco.mju_mat2Quat(q,np.ascontiguousarray(matrix).ravel());return q
def pose(row):
    truth=row['privileged'];obs=row['observation']
    for name,value in zip(('platform_slide','aft_lid_slide','fore_lid_slide'),truth['dock_joint_m']):env.data.qpos[env.boat.qadr[name]]=value
    for eq in range(env.model.neq):
        if env.model.eq_type[eq]==mujoco.mjtEq.mjEQ_JOINT and env.model.eq_obj2id[eq]>=0:
            j1,j2=int(env.model.eq_obj1id[eq]),int(env.model.eq_obj2id[eq])
            env.data.qpos[env.model.jnt_qposadr[j1]]=np.polynomial.polynomial.polyval(env.data.qpos[env.model.jnt_qposadr[j2]],env.model.eq_data[eq,:5])
    env.data.qpos[qb:qb+3]=0;env.data.qpos[qb+3:qb+7]=[1,0,0,0]
    mujoco.mj_kinematics(env.model,env.data);local_position=env.pad_position.copy()
    rotation=np.asarray(truth['pad_rotation'])@local_rotation.T
    env.data.qpos[qb:qb+3]=np.asarray(truth['pad_position_enu_m'])-rotation@local_position
    env.data.qpos[qb+3:qb+7]=quat(rotation)
    env.data.qpos[qd:qd+3]=truth['drone_position_enu_m']
    attitude=Rotation.from_euler('xyz',obs['px4']['attitude_ned_rad']).as_matrix()
    env.data.qpos[qd+3:qd+7]=quat(C.T@attitude@D)
    env.data.qpos[env.drone.camera_qpos]=obs['gimbal_rad']
    env.data.qvel[:]=0;env.data.time=row['time_s']
    mujoco.mj_kinematics(env.model,env.data);mujoco.mj_camlight(env.model,env.data)
    cid=env.model.camera('drone_onboard').id
    assert np.linalg.norm(env.data.cam_xpos[cid]-env.drone.position)<.5
    return float(np.max(np.abs(env.pad_position-truth['pad_position_enu_m'])))
times=np.array([r['task_time_s'] for r in rows]);end=float(times[-1])
# Full original flight at 8x, then four seconds at normal speed during acquisition.
timeline=[(min(end,n*8/12),'FULL FLIGHT / 8x') for n in range(math.ceil(end/8*12))]
timeline += [(end,'FINISHED / SAFE HOME LANDING') for _ in range(12)]
timeline += [(8+n/12,'ACQUISITION DETAIL / NORMAL SPEED') for n in range(48)]
drone=np.array([r['privileged']['drone_position_enu_m'][:2] for r in rows])
boat=np.array([r['privileged']['pad_position_enu_m'][:2] for r in rows])
ghost=[]
for row in rows:
    obs=row['observation'];yaw=math.pi/2-obs['px4']['attitude_ned_rad'][2];c,s=math.cos(yaw),math.sin(yaw)
    v=np.asarray(obs['beacon']['relative_heading_m'])*[1,-1,-1]
    ghost.append(np.asarray(obs['px4']['position_enu_m'])[:2]+np.array([[c,-s],[s,c]])@v[:2])
ghost=np.asarray(ghost);allpoints=np.concatenate((boat,drone,ghost));lo=allpoints.min(0);hi=allpoints.max(0);center=(hi+lo)/2;span=max(15.,float(np.max(hi-lo))*1.2)
def point(p):
    p=(p-center)/span;return tuple(np.rint([1085+p[0]*280,535-p[1]*280]).astype(int))
max_error=0.;camera_positions=[]
try:
    for n,(t,chapter) in enumerate(timeline):
        index=int(np.argmin(abs(times-t)));row=rows[index];obs=row['observation'];diag=row['output']['learner_diagnostics']
        max_error=max(max_error,pose(row));external=renderer.overview()
        capture_index=int(np.argmin(abs(np.array([r['time_s'] for r in rows[max(0,index-8):index+1]])-obs['image_capture_time_s'])))+max(0,index-8)
        pose(rows[capture_index]);camera_positions.append(env.data.cam_xpos[env.model.camera('drone_onboard').id].copy())
        onboard=camera_image(renderer.onboard_image(),scenario)
        if not obs['image_valid']:onboard=np.zeros_like(onboard)
        image=Image.new('RGB',(1280,720),(15,21,30));image.paste(Image.fromarray(external).resize((640,360)),(0,50));image.paste(Image.fromarray(onboard),(640,50))
        draw=ImageDraw.Draw(image)
        draw.text((15,10),'WRONG RADIO POSITION: +5 m EAST / CLAIMS 0.25 m ACCURACY',font=large,fill='#ffffff')
        for x,label in [(0,'EXTERNAL VIEW / RECORDED TRAJECTORY'),(640,'RECONSTRUCTED DRONE CAMERA / RGB NOT SAVED')]:
            draw.rectangle((x,50,x+640,78),fill='#172332');draw.text((x+10,55),label,font=small,fill='#b6dfff')
        draw.text((20,426),chapter,font=large,fill='#ffcd7a')
        draw.text((20,470),f"Flight {row['task_time_s']:6.1f} / {end:.1f} s | {diag['control_phase']}",font=font,fill='#ffffff')
        lines=[f"Accepted visual track: {bool(diag.get('metric_valid'))}",
               '0-60 s: acquisition fails; then search-timeout return home',
               'Final result: SAFE HOME LANDING / NO BOAT LANDING',
               f"Camera pan/tilt: {np.degrees(obs['gimbal_rad'][0]):.0f} / {np.degrees(obs['gimbal_rad'][1]):.0f} deg",
               'Map: yellow drone | teal boat | red radio position']
        for k,line in enumerate(lines):draw.text((20,510+k*29),line,font=small,fill='#dce5ef')
        draw.rectangle((920,424,1264,668),outline='#3b526c',width=2)
        draw.line([point(p) for p in boat],fill='#376b75',width=2)
        if index>3:draw.line([point(p) for p in drone[:index+1:3]],fill='#6686c9',width=2)
        bp=point(boat[index]);gp=point(ghost[index]);draw.line([bp,gp],fill='#ef7377',width=2)
        for p,color in [(bp,'#55e4ca'),(point(drone[index]),'#ffe082'),(gp,'#ef7377')]:draw.ellipse((p[0]-5,p[1]-5,p[0]+5,p[1]+5),fill=color)
        draw.text((20,689),'TRACE RECONSTRUCTION: recorded motion + estimated attitude/gimbal; not original RGB or a new flight.',font=small,fill='#91a3b7')
        video.write(np.asarray(image))
        if n==0:image.save(out/'preview.jpg',quality=90)
        if n and n%72==0:print('RENDER',n,len(timeline),round(time.monotonic()-started,1),flush=True)
finally:video.close();renderer.close()
result=dict(file=str(video_path),bytes=video_path.stat().st_size,sha256=hashlib.sha256(video_path.read_bytes()).hexdigest(),
    trace_sha256=hashlib.sha256((source/'steps.jsonl').read_bytes()).hexdigest(),source='original flight trace reconstruction; RGB was not archived',
    outcome='home_landed',flight_seconds=end,video_seconds=len(timeline)/12,frames=len(timeline),wall_seconds=time.monotonic()-started,
    pad_reconstruction_max_error_m=max_error,camera_position_span_m=np.ptp(camera_positions,axis=0).tolist(),physics_rerun=False)
(out/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
