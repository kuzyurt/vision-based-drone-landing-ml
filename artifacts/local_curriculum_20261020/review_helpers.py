"""Recording/scene helpers. No simulator truth is passed through to a task actor."""
import local_paths
from pathlib import Path
import hashlib,json,math,subprocess
import mujoco,numpy as np
from PIL import Image,ImageDraw,ImageFont

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def nominal_structure_bound(model):
    d=mujoco.MjData(model)
    for name,value in [('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)]:d.qpos[model.jnt_qposadr[model.joint(name).id]]=value
    mujoco.mj_forward(model,d);bound=0.
    for gid in range(model.ngeom):
        body=int(model.geom_bodyid[gid]);root=None
        while body:
            name=model.body(body).name
            if name=='boat' or name.startswith('decoy_'):root=body;break
            body=int(model.body_parentid[body])
        if root is not None:bound=max(bound,float(np.linalg.norm(d.geom_xpos[gid]-d.xpos[root])+model.geom_rbound[gid]))
    return bound+.05+.4

def place_distractors(env,out,foreground=False):
    from target_learning.scenes import annotation_groups
    groups=annotation_groups(env.model);nominal=mujoco.MjData(env.model)
    for name,value in [('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)]:nominal.qpos[env.model.jnt_qposadr[env.model.joint(name).id]]=value
    mujoco.mj_forward(env.model,nominal);radii={}
    for name,gids in groups.items():
        bid=env.model.body('boat'if name=='target'else name).id
        radii[name]=max(float(np.linalg.norm(nominal.geom_xpos[g]-nominal.xpos[bid])+env.model.geom_rbound[g])for g in gids)
    route=np.asarray(env.boat.navigation.world.route.points);segments=np.roll(route,-1,axis=0)-route;lengths=(segments*segments).sum(1);rng=np.random.default_rng(env.scenario.seed+54);placed=[]
    def route_distance(xy):
        fraction=np.clip(((xy-route)*segments).sum(1)/np.maximum(lengths,1e-12),0,1)
        return float(np.linalg.norm(xy-(route+fraction[:,None]*segments),axis=1).min())
    for name in sorted(groups,key=lambda n:-radii[n]):
        if name=='target':continue
        radius=radii[name];mid=int(env.model.body_mocapid[env.model.body(name).id])
        for trial in range(3000):
            theta=rng.uniform(-math.pi,math.pi);distance=rng.uniform(6+radius,24+radius);xy=env.pad_position[:2]+distance*np.array([math.cos(theta),math.sin(theta)])
            rd=route_distance(xy)
            if env.boat.navigation.world.distance(xy)[0]<5+radius or rd<radius+radii['target']+.5:continue
            if any(np.linalg.norm(xy-p['xy'])<radius+p['radius']+.5 for p in placed):continue
            env.data.mocap_pos[mid,:2]=xy;placed.append(dict(name=name,xy=xy.tolist(),radius=radius,route_clearance_m=rd-radius-radii['target']));break
        else:raise RuntimeError('No non-overlapping distractor placement')
    if foreground:
        name='decoy_false_cross_board';radius=radii[name];direction=env.pad_position[:2]-env.task_start_xy;direction/=np.linalg.norm(direction);side=np.array([-direction[1],direction[0]]);found=False
        for offset in [0.,-1.,1.]:
            xy=env.task_start_xy+6*direction+offset*side;rd=route_distance(xy)
            if env.boat.navigation.world.distance(xy)[0]<5+radius or rd<radius+radii['target']+.5:continue
            if any(p['name']!=name and np.linalg.norm(xy-p['xy'])<radius+p['radius']+.5 for p in placed):continue
            if np.linalg.norm(xy-env.task_start_xy)<radius+2:continue
            env.data.mocap_pos[int(env.model.body_mocapid[env.model.body(name).id]),:2]=xy
            next(p for p in placed if p['name']==name).update(xy=xy.tolist(),route_clearance_m=rd-radius-radii['target'],foreground_scene_only=True);found=True;break
        assert found,'Foreground board scenario cannot safely satisfy its purpose'
    mujoco.mj_forward(env.model,env.data)
    (out/'scene_spawn_receipt.json').write_text(json.dumps(dict(nominal_radii_m=radii,placements=placed,actor_input=False),indent=2));return groups

class ReviewVideo:
    def __init__(self,out,name):
        self.path=out/'review.mp4';self.log=(out/'video_encode.log').open('x');self.name=name;self.frames=0
        self.font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
        self.process=subprocess.Popen(['ffmpeg','-n','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size','960x420','-framerate','25','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-threads','2','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(self.path)],stdin=subprocess.PIPE,stderr=self.log,creationflags=subprocess.CREATE_NO_WINDOW)
    def write(self,rgb,row):
        canvas=Image.new('RGB',(960,420),(18,24,31));canvas.paste(Image.fromarray(rgb),(0,0));d=ImageDraw.Draw(canvas);o=row['observation'];diag=row['output']['learner_diagnostics'];owner=diag['actual_command_owner'];t=row['task_time_s'];a=row['output']['executed_action']
        lines=[self.name,'ACTUAL ONBOARD RGB','EXPERIMENTAL REVIEW',f'Task {t:6.2f} s',f'Owner: {owner}',f'Phase: {diag.get("control_phase","unknown")}',f'ID: {diag.get("expert_observable_target_confirmed",False)}',f'Metric: {diag.get("metric_confirmed",False)}',f'Fault: {diag.get("evaluation_fault_active",False)}',f'PX4 armed: {o["px4"]["armed"]}',f'PX4 landed: {o["px4"]["landed"]}',f'Outcome: {row["outcome"]}']
        for i,line in enumerate(lines):d.text((650,10+i*26),line,font=self.font,fill=(255,203,102)if i in[0,2,4]else(220,231,240))
        d.text((8,370),f'Actual command fwd/right/down: {a[0]:+.2f} {a[1]:+.2f} {a[2]:+.2f} m/s',font=self.font,fill='white')
        d.text((8,393),'25 fps / normal task speed. Fault/safety/learner commands are not teacher labels.',font=self.font,fill=(255,203,102))
        self.process.stdin.write(np.asarray(canvas).tobytes());self.frames+=1
    def close(self):
        self.process.stdin.close();code=self.process.wait(timeout=60);self.log.close()
        assert code==0,'Video encoding failed'
        self.path.with_suffix('.receipt.json').write_text(json.dumps(dict(frames=self.frames,fps=25,normal_task_speed=True,source='Actual Windows MuJoCo onboard RGB and executed ownership trace',sha256=sha(self.path),bytes=self.path.stat().st_size),indent=2))

