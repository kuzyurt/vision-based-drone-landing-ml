"""Durable review rows and RGB inputs, separate from authorized datasets."""
import json
import math
from pathlib import Path
import h5py
import numpy as np

def json_value(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)

class Recorder:
    def __init__(self,directory,scenario,role='review'):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.rows=(self.directory/'steps.jsonl').open('w')
        self.file=h5py.File(self.directory/'observations.h5','w')
        self.file.attrs.update(schema='aerodock.landing.v1',role=role,training_eligible=role!='review',scenario=json.dumps(scenario))
        self.images=self.file.create_dataset('rgb',(0,360,640,3),maxshape=(None,360,640,3),chunks=(1,360,640,3),dtype='u1',compression='lzf')
        self.records=self.file.create_dataset('steps',(0,),maxshape=(None,),dtype=h5py.string_dtype('utf-8'))
        self.count=0
    def append(self,rgb,row):
        index=self.count;serialized=json.dumps(row,default=json_value,separators=(',',':'),allow_nan=False)
        self.rows.write(serialized+'\n');self.images.resize(index+1,axis=0);self.records.resize(index+1,axis=0)
        self.images[index]=rgb;self.records[index]=serialized;self.count+=1
        if self.count%100==0:self.rows.flush();self.file.flush()
    def close(self):self.rows.close();self.file.close()

def numeric_observation(row):
    """Fixed 32-value deployable contract. Privileged fields are inaccessible."""
    observation=row['observation'];p=observation['px4'];b=observation['beacon']
    yaw=p.get('attitude_ned_rad',[0,0,0])[2];east,north,up=p.get('velocity_enu_m_s',[0,0,0])
    velocity=[math.cos(yaw)*north+math.sin(yaw)*east,-math.sin(yaw)*north+math.cos(yaw)*east,-up]
    values=[*velocity,*p.get('attitude_ned_rad',[0,0,0]),*p.get('angular_rate_frd_rad_s',[0,0,0]),*observation['gimbal_rad'],*b.get('relative_heading_m',[0,0,0]),*b.get('velocity_heading_m_s',[0,0,0]),p.get('position_age_s',10),p.get('attitude_age_s',10),b['age_s'],float(p['valid']),float(b['valid']),float(b['dock_ready']),observation['image_age_s'],*observation['previous_executed_action'],observation['decision_dt_s'],float(observation['image_valid'])]
    if len(values)!=32:raise AssertionError('Observation schema changed')
    return np.array(values,dtype=np.float32)
