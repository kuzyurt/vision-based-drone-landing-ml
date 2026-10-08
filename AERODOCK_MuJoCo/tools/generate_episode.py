"""Reproducible headless episodes for future ML datasets (no rendering).

python generate_episode.py --kind gravel --world-seed 42 --path-seed 43 --seconds 60
Writes world.json + timestamped telemetry.csv into the requested output folder.
"""
import argparse
import csv
import json
from pathlib import Path
import time
from boat_sim import BoatSim
from usv.procedural_world import KINDS


def run(kind='island',world_seed=None,path_seed=None,seconds=60,hz=10,output='episodes/latest'):
    if not 0<seconds<=86400 or not 0<hz<=200:raise ValueError('seconds must be 0–86400 and hz 0–200.')
    sim=BoatSim();sim.new_world(kind,world_seed,path_seed)
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    meta=sim.export_world();meta['simulation_config']=sim.config
    meta['physics_timestep_s']=sim.model.opt.timestep;meta['requested_sample_hz']=hz
    (dest/'world.json').write_text(json.dumps(meta,indent=2))
    fields=['time_s','x_m','y_m','heading_deg','speed_mps','port_power','starboard_power',
            'route_progress_m','route_error_m','target_speed_mps','coast_distance_m','segment']
    started=time.perf_counter();next_sample=0.;rows=0
    end_time=round(seconds/sim.model.opt.timestep)*sim.model.opt.timestep
    with (dest/'telemetry.csv').open('w',newline='') as file:
        writer=csv.writer(file);writer.writerow(fields)
        while sim.data.time+1e-8<end_time:
            if sim.data.time+1e-8>=next_sample:
                state=sim.status();writer.writerow([state['time'],*state['position'][:2],state['heading_deg'],
                    state['speed_kmh']/3.6,state['port_power'],state['starboard_power'],state['route_progress_m'],
                    state['route_error_m'],state['route_target_speed_mps'],state['coast_distance_m'],state['route_segment']])
                rows+=1;next_sample+=1/hz
            sim.step(max(1,min(round((next_sample-sim.data.time)/sim.model.opt.timestep),
                               round((end_time-sim.data.time)/sim.model.opt.timestep),200)))
    report={'world_seed':sim.navigation.world.seed,'path_seed':sim.navigation.world.route.seed,
            'simulated_seconds':sim.data.time,'wall_seconds':time.perf_counter()-started,'rows':rows,
            'rendering':False,'note':'Estimated boat hydrodynamics, simplified shore contacts; not real sensor data.'}
    (dest/'report.json').write_text(json.dumps(report,indent=2));return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=KINDS,default='island')
    p.add_argument('--world-seed',type=int);p.add_argument('--path-seed',type=int)
    p.add_argument('--seconds',type=float,default=60);p.add_argument('--hz',type=float,default=10)
    p.add_argument('--output',default='episodes/latest');args=p.parse_args()
    print(json.dumps(run(**vars(args)),indent=2))


if __name__=='__main__':main()
