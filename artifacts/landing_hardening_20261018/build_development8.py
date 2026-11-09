"""Additional causal development cases, distinct from frozen final C60."""
from pathlib import Path
import copy,hashlib,json
ROOT=Path(__file__).resolve().parent
source=json.loads((ROOT/'baseline_plan.json').read_text())['cases'][0]
definitions=[
 ('near_rear_low',dict(distance=3.,height=1.2,bearing_deg=180.,yaw_offset_deg=180.,initial_camera_target=True),{},True,False),
 ('near_low_camera_handoff',dict(distance=3.,height=1.2,bearing_deg=0.,yaw_offset_deg=0.,initial_camera_target=False,initial_pan_deg=0.,initial_tilt_deg=75.),{},True,False),
 ('near_side_delayed',dict(distance=3.,height=1.2,bearing_deg=90.,yaw_offset_deg=90.,initial_camera_target=True,camera_delay_steps=4),{},True,False),
 ('close_occlusion3s',dict(distance=20.,height=4.),dict(kind='central_occluder',trigger_clearance_m=.8,duration_s=3.),True,False),
 ('very_close_occlusion3s',dict(distance=20.,height=4.),dict(kind='central_occluder',trigger_clearance_m=.4,duration_s=3.),True,False),
 ('gravel_moving40m',dict(kind='gravel',distance=40.,height=6.,bearing_deg=-75.,yaw_offset_deg=125.,boat_speed=.9,initial_camera_target=False),{},False,False),
 ('city_moving20m',dict(kind='city',distance=20.,height=4.,bearing_deg=45.,yaw_offset_deg=-110.,boat_speed=.6,initial_camera_target=False),{},False,False),
 ('beach_inland60m',dict(kind='beach',distance=60.,height=8.,bearing_deg=120.,yaw_offset_deg=150.,boat_speed=.35,initial_camera_target=False),{},False,True),
]
jobs=[]
for index,(name,changes,fault,rgb,inland) in enumerate(definitions):
 job=copy.deepcopy(source);job.update(name=name,source_case=name,role='development',record_rgb=rgb,inland=inland,vertical_launch=True,fault=fault)
 job['scenario'].update(name=name,world_seed=18481000+index,path_seed=18482000+index,seed=18483000+index,**changes)
 jobs.append(job)
path=ROOT/'development8_plan.json';assert not path.exists()
path.write_text(json.dumps(dict(role='development',cases=jobs,note='Development only. Final C60 remains untouched. Triggered3s optical blockage must be scored separately from clean nominal views.'),indent=2)+'\n')
print(hashlib.sha256(path.read_bytes()).hexdigest())
