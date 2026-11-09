"""Evaluation/setup/scoring adapter; none of its simulator state enters actions."""
import inspect,json,math,textwrap
from pathlib import Path
import numpy as np
import mujoco
from scipy.spatial import ConvexHull,QhullError
from landing_training.environment import object_velocity


def install(episode,*,remove_boat_visuals=False,base_environment=None):
    if not hasattr(episode,'_mission_original_environment'):
        episode._mission_original_environment=episode.Environment
        episode._mission_original_run_episode=episode.run_episode
    original=base_environment or episode._mission_original_environment
    class ScoredEnvironment(original):
        def __init__(self,scenario):
            super().__init__(scenario);self.home_stable_disarmed_s=0.;self.home_contact_s=0.
            self.visual_boat_removed=bool(remove_boat_visuals)
            if remove_boat_visuals:
                bodies=[]
                for body in range(self.model.nbody):
                    parent=body
                    while parent and parent!=self.boat.boat:parent=int(self.model.body_parentid[parent])
                    if parent==self.boat.boat:bodies.append(body)
                ids=np.flatnonzero(np.isin(self.model.geom_bodyid,bodies))
                self.model.geom_group[ids]=5
                self.removed_visual_geom_count=len(ids)
        def check_outcomes(self,armed):
            super().check_outcomes(armed)
            if self.outcome in ['landed','water_strike','collision_failure','home_landed']:return
            support=set();launch_gid=self.model.geom('launch_contact').id
            for contact in self.data.contact[:self.data.ncon]:
                pair={int(contact.geom1),int(contact.geom2)}
                if launch_gid in pair:
                    other=next(iter(pair-{launch_gid}),None)
                    if other in self.drone.foot_geoms:support.add(self.drone.foot_geoms[other])
            feet=self.data.site_xpos[self.drone.feet]-self.data.mocap_pos[self.launch_mid]
            supported=False
            if len(support)>=3:
                points=feet[sorted(support),:2]
                try:polygon=points[ConvexHull(points).vertices]
                except QhullError:polygon=None
                if polygon is not None:
                    com=self.data.subtree_com[self.drone.base]-self.data.mocap_pos[self.launch_mid]
                    edges=np.roll(polygon,-1,axis=0)-polygon;offsets=com[:2]-polygon
                    supported=bool(np.all(edges[:,0]*offsets[:,1]-edges[:,1]*offsets[:,0]>=-1e-6))
            rotation=self.data.xmat[self.drone.base].reshape(3,3)
            tilt=math.acos(float(np.clip(rotation[2,2],-1,1)))
            angular=object_velocity(self.model,self.data,mujoco.mjtObj.mjOBJ_BODY,self.drone.base)[:3]
            velocity=self.drone.velocity
            stable=(supported and np.max(abs(feet[:,:2]))<=.65 and np.linalg.norm(velocity[:2])<.1
                and abs(velocity[2])<.05 and tilt<math.radians(5) and np.linalg.norm(angular)<math.radians(5))
            self.home_stable_disarmed_s=self.home_stable_disarmed_s+self.model.opt.timestep if stable and not armed else 0.
            if self.home_stable_disarmed_s>=2.:
                self.outcome='home_landed';self.event('home_landed',supporting_feet=len(support),
                    stable_disarmed_s=self.home_stable_disarmed_s,score_only=True)
    episode.Environment=ScoredEnvironment
    original_run=episode._mission_original_run_episode
    source=textwrap.dedent(inspect.getsource(original_run))
    needle="terminal=env.outcome in ('landed','water_strike','collision_failure')"
    assert source.count(needle)==1
    source=source.replace(needle,"terminal=env.outcome in ('landed','water_strike','collision_failure','home_landed')")
    namespace=dict(original_run.__globals__);namespace['Environment']=ScoredEnvironment
    exec(compile(source,__file__,'exec'),namespace)
    episode.run_episode=namespace['run_episode']
