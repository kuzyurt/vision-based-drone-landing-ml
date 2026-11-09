"""Explicit seeded scenarios. Reviews are never a training dataset."""
from dataclasses import asdict,dataclass,replace
import json
from pathlib import Path

@dataclass(frozen=True)
class Scenario:
    name:str='review_island_forward'
    kind:str='island'
    world_seed:int=401
    path_seed:int=501
    seed:int=701
    reverse:bool=False
    world_rotation_deg:float=0.
    distance:float=4.
    bearing_deg:float=180.
    height:float=2.5
    boat_speed:float=.35
    boat_start_fraction:float|None=None
    wave_height:float=.02
    wave_period:float=3.
    wave_direction_deg:float=35.
    wind_profile:str='calm'
    wind_mean_m_s:float|None=None
    wind_direction_deg:float=0.
    current_x:float=0.
    current_y:float=0.
    yaw_offset_deg:float=0.
    initial_camera_target:bool=True
    initial_pan_deg:float=0.
    initial_tilt_deg:float=0.
    image_brightness:float=1.
    image_contrast:float=1.
    image_blur_px:float=0.
    camera_delay_steps:int=0
    camera_blind_seconds:float=0.
    beacon_dropout_start_s:float=-1.
    beacon_dropout_duration_s:float=0.
    dock_unavailable_seconds:float=0.
    duration:float=90.
    stress_test:bool=False

    def validate(self):
        import math
        from usv.procedural_world import KINDS
        from sim.environment import PROFILES
        if self.kind not in KINDS or self.wind_profile not in PROFILES:raise ValueError('Unknown map/wind')
        for key,value in asdict(self).items():
            if isinstance(value,(int,float)) and not math.isfinite(value):raise ValueError(key+' must be finite')
        # Explicit review experiments can explore the existing boat model's
        # 0.5 m wave setting and the unchanged 2 m/s flight action envelope.
        # The approved production collection ranges remain unchanged.
        if not isinstance(self.stress_test,bool):raise ValueError('stress_test must be boolean')
        if not 0<=self.wave_height<=(.5 if self.stress_test else .15) or not 2<=self.wave_period<=5:raise ValueError('Wave qualification envelope exceeded')
        if not 0<=self.boat_speed<=(2 if self.stress_test else 1) or not 0<=self.distance<=60 or not 1.2<=self.height<=8:raise ValueError('Flight qualification envelope exceeded')
        if not 1<=self.duration<=180:raise ValueError('Duration must be 1..180 seconds')
        if self.boat_start_fraction is not None and not 0<=self.boat_start_fraction<=1:raise ValueError('Boat start fraction must be 0..1')
        if self.wind_mean_m_s is not None and not 0<=self.wind_mean_m_s<=(10 if self.stress_test else 4):raise ValueError('Mean wind outside scenario envelope')
        if not 0<=self.camera_delay_steps<=5 or int(self.camera_delay_steps)!=self.camera_delay_steps:raise ValueError('Camera delay must be 0..5 decision steps')
        if not .7<=self.image_brightness<=1.3 or not .7<=self.image_contrast<=1.3 or not 0<=self.image_blur_px<=1:raise ValueError('Image variation outside envelope')
        if any(not isinstance(value,int) or not 0<=value<2**32 for value in (self.seed,self.world_seed,self.path_seed)):raise ValueError('Seeds must be uint32 integers')
        if math.hypot(self.current_x,self.current_y)>.3:raise ValueError('Current outside initial 0.3 m/s envelope')
        if min(self.camera_blind_seconds,self.beacon_dropout_duration_s,self.dock_unavailable_seconds)<0:raise ValueError('Fault durations must be nonnegative')

def review_scenarios():
    cases=[]
    for i,kind in enumerate(('island','beach','city','gravel','rock')):
        for reverse in (False,True):
            scenario=Scenario(name=f'{i*2+int(reverse)+1:02d}_{kind}_{"reverse" if reverse else "forward"}',kind=kind,world_seed=401+i,path_seed=501+i,seed=701+i*2+int(reverse),reverse=reverse,world_rotation_deg=i*43.,distance=3.+i*.8,bearing_deg=(-120.,60.,180.,-60.,120.)[i],height=2.+i*.25,boat_speed=.2+i*.08,wave_height=.0 if i==0 else .015+i*.01,wave_period=2.5+i*.45,wave_direction_deg=(i*71+int(reverse)*180)%360,wind_profile='calm' if i<2 else 'breeze',wind_direction_deg=(i*83+int(reverse)*180)%360,yaw_offset_deg=55. if reverse else 0.,initial_camera_target=not reverse,camera_blind_seconds=1.5 if reverse and i==2 else 0.,duration=90.)
            if i==4:scenario=replace(scenario,distance=60. if reverse else 40.,height=8. if reverse else 6.,duration=180.,camera_delay_steps=4 if reverse else 2,image_brightness=1.1 if reverse else .9,image_contrast=1.1,image_blur_px=.35)
            scenario=replace(scenario,boat_start_fraction=(.10,.30,.50,.70,.90)[i])
            cases.append(scenario)
    return cases

def load_scenario(path):return Scenario(**json.loads(Path(path).read_text()))
