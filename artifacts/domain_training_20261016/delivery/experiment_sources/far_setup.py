"""Initial conditions only: a matched pair of 60 m beach-map starts.

No simulator quantities from this setup are exposed to evaluated policy control.
Flight dynamics, camera rendering, shoreline contacts and landing rules are intact.
"""
import json
import math
from pathlib import Path
import numpy as np
import mujoco
from landing_training.environment import Environment
from usv.world_render import WorldRenderer


class FarStartEnvironment(Environment):
    audit_directory = None

    def __init__(self, scenario):
        super().__init__(scenario)
        world=self.boat.navigation.world
        route=world.route
        coast_s=float(np.interp(self.boat_start_progress_m,route.arc,route.coast_s))
        _,normal,_=world.sample(coast_s)
        land='inland' in scenario.name
        point=self.pad_position[:2]+(-1. if land else 1.)*60.*normal
        signed=float(world.distance(point)[0])
        if land and signed>=-5.:raise ValueError('Requested inland start is not inland')
        if not land and signed<=5.:raise ValueError('Requested water start is not over water')
        canonical=point@world.rotation
        coast=world.original.coast
        starts=coast[:-1];segments=np.diff(coast,axis=0)
        fraction=np.clip(np.sum((canonical-starts)*segments,axis=1)/np.sum(segments*segments,axis=1),0.,1.)
        projected=starts+fraction[:,None]*segments
        nearest=int(np.argmin(np.linalg.norm(projected-canonical,axis=1)))
        nearest_s=float(world.original.arc[nearest]+fraction[nearest]*np.linalg.norm(segments[nearest]))
        ground=float(WorldRenderer.ground_z(None,world.original,-signed,nearest_s)) if land else 0.
        self.task_start_xy=point.copy();self.launch_xy=point.copy()
        self.data.mocap_pos[self.launch_mid]=[*point,ground+.15]
        q=self.drone.free_qadr
        self.data.qpos[q:q+3]=[*point,ground+.2-self.drone.bottom+.004]
        self.data.qvel[self.drone.free_vadr:self.drone.free_vadr+6]=0.
        self.preparation_budget_s=45.+2*scenario.height
        self.preparation_water_clearance_m=signed
        self.achieved_bearing_deg=math.degrees(math.atan2(*(point-self.pad_position[:2])[::-1])-self.boat_yaw)%360
        mujoco.mj_forward(self.model,self.data)
        audit=dict(start_type='airborne_over_land' if land else 'airborne_over_water',
                   planned_horizontal_distance_m=float(np.linalg.norm(point-self.pad_position[:2])),
                   signed_shore_distance_m=signed, terrain_height_m=ground,
                   planned_foot_height_m=float(self.pad_position[2]+scenario.height),
                   planned_terrain_clearance_m=float(self.pad_position[2]+scenario.height-ground),
                   camera_initially_aimed_at_boat=False,
                   note='PX4 performs the standard preparation before the evaluated airborne start; setup state is not a policy input')
        if audit['planned_terrain_clearance_m']<2.:raise ValueError('Insufficient airborne terrain clearance')
        Path(self.audit_directory,'spawn.json').write_text(json.dumps(audit,indent=2))
