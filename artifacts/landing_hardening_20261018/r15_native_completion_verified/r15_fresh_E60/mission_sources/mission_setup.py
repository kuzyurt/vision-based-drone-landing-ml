"""Initial spawn geometry only. No setup truth is exposed to policy actions."""
import json,math
from pathlib import Path
import numpy as np
import mujoco
from landing_training.environment import Environment
from usv.world_render import WorldRenderer


class VerticalLaunchEnvironment(Environment):
    """Take off below the prescribed airborne start, with a declared physical home."""
    audit_directory=None
    def __init__(self,scenario):
        super().__init__(scenario)
        point=self.task_start_xy.copy();self.launch_xy=point.copy()
        self.data.mocap_pos[self.launch_mid]=[*point,.15]
        q=self.drone.free_qadr;self.data.qpos[q:q+3]=[*point,.2-self.drone.bottom+.004]
        self.data.qvel[self.drone.free_vadr:self.drone.free_vadr+6]=0.
        self.preparation_budget_s=45.+2*scenario.height
        self.preparation_water_clearance_m=float(self.boat.navigation.world.distance(point)[0])
        mujoco.mj_forward(self.model,self.data)
        if self.audit_directory is not None:
            value=dict(start_type='airborne_over_water',home_at_airborne_start_xy=True,
                planned_horizontal_distance_m=float(np.linalg.norm(point-self.pad_position[:2])),
                signed_shore_distance_m=self.preparation_water_clearance_m,
                note='Only initial launch-pad position/takeoff preparation differs; task starts, physics and touchdown criteria preserved')
            Path(self.audit_directory,'spawn.json').write_text(json.dumps(value,indent=2))


class InlandStartEnvironment(Environment):
    audit_directory=None
    def __init__(self,scenario):
        super().__init__(scenario)
        world=self.boat.navigation.world;route=world.route
        coast_s=float(np.interp(self.boat_start_progress_m,route.arc,route.coast_s))
        _,normal,_=world.sample(coast_s)
        direction=math.atan2(-normal[1],-normal[0]);chosen=None
        angles=[0.]+[sign*angle for angle in range(5,181,5) for sign in [1,-1]]
        for offset in angles:
            angle=direction+math.radians(offset)
            point=self.pad_position[:2]+scenario.distance*np.array([math.cos(angle),math.sin(angle)])
            signed=float(world.distance(point)[0])
            if signed>=-5.:continue
            canonical=point@world.rotation;coast=world.original.coast;starts=coast[:-1];segments=np.diff(coast,axis=0)
            fraction=np.clip(np.sum((canonical-starts)*segments,axis=1)/np.sum(segments*segments,axis=1),0.,1.)
            nearest=int(np.argmin(np.linalg.norm(starts+fraction[:,None]*segments-canonical,axis=1)))
            nearest_s=float(world.original.arc[nearest]+fraction[nearest]*np.linalg.norm(segments[nearest]))
            ground=float(WorldRenderer.ground_z(None,world.original,-signed,nearest_s))
            clearance=float(self.pad_position[2]+scenario.height-ground)
            if clearance<2.:continue
            chosen=(point,signed,ground,clearance,offset);break
        if chosen is None:raise ValueError('No physically valid inland start at the prescribed radius and height')
        point,signed,ground,clearance,offset=chosen
        self.task_start_xy=point.copy();self.launch_xy=point.copy()
        self.data.mocap_pos[self.launch_mid]=[*point,ground+.15]
        q=self.drone.free_qadr;self.data.qpos[q:q+3]=[*point,ground+.2-self.drone.bottom+.004]
        self.data.qvel[self.drone.free_vadr:self.drone.free_vadr+6]=0.
        self.preparation_budget_s=45.+2*scenario.height;self.preparation_water_clearance_m=signed
        self.achieved_bearing_deg=math.degrees(math.atan2(*(point-self.pad_position[:2])[::-1])-self.boat_yaw)%360
        mujoco.mj_forward(self.model,self.data)
        value=dict(start_type='airborne_over_land',planned_horizontal_distance_m=float(np.linalg.norm(point-self.pad_position[:2])),
            signed_shore_distance_m=signed,terrain_height_m=ground,planned_terrain_clearance_m=clearance,
            placement_offset_deg=offset,placement_rule='first physically valid inland bearing at exact prescribed radius; no policy evaluated',
            task_inputs='no boat geometry from setup is supplied to policy')
        Path(self.audit_directory,'spawn.json').write_text(json.dumps(value,indent=2))
