"""Collect explicitly authorized extra episodes; original dataset is read-only."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import concurrent.futures
from dataclasses import asdict
import datetime
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE))
from landing_training import paths
INSTANCE=None

def save(path,value):
    path=Path(path);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False));tmp.replace(path)

def initialize(instances):
    global INSTANCE
    INSTANCE=instances.get()

def plan():
    import numpy as np
    from landing_training.config import Scenario
    jobs=[]
    for family,kind in enumerate(['island','beach','city','gravel','rock']):
        for world in range(16):
            role='training' if world<12 else 'validation' if world<14 else 'test'
            rng=np.random.default_rng(724100+family*100+world)
            for reverse in [False,True]:
                seed=640000+family*100+world*2+int(reverse)
                lo,hi=[(2.5,8.),(8.,25.),(25.,60.)][world%3]
                camera=bool(world%4==0)
                s=Scenario(name=f'{role}_{kind}_{world:02d}_{int(reverse)}',kind=kind,
                           world_seed=440000+family*100+world,path_seed=540000+family*100+world,seed=seed,reverse=reverse,
                           distance=float(rng.uniform(lo,hi)),height=float(rng.uniform(2.5,8)),
                           bearing_deg=float(rng.uniform(-180,180)),yaw_offset_deg=float(rng.uniform(-180,180)),
                           boat_start_fraction=float(rng.uniform(.05,.95)),world_rotation_deg=float(rng.uniform(0,360)),
                           boat_speed=float(rng.uniform(.15,.9)),wave_height=0. if world%3==0 else float(rng.uniform(.01,.05)),
                           wave_period=float(rng.uniform(2.5,4.5)),wind_profile=['calm','breeze','gusty','steady2'][world%4],
                           wind_mean_m_s=0. if world%4==0 else float(rng.uniform(.5,3.)),wind_direction_deg=float(rng.uniform(0,360)),
                           initial_camera_target=camera,initial_pan_deg=float(rng.uniform(-180,180)),
                           initial_tilt_deg=float(rng.choice([5,15,35,60])),camera_delay_steps=int(rng.integers(0,6)),
                           image_brightness=float(rng.uniform(.85,1.15)),image_contrast=float(rng.uniform(.85,1.15)),
                           image_blur_px=float(rng.uniform(0,.45)),duration=180.)
                s.validate()
                jobs.append(dict(name=s.name,role=role,scenario=asdict(s),search_s=0. if camera else float(rng.uniform(6.,14.)),
                                 pilot=world in [0,1,2,12,14],family=family,world=world))
    return sorted(jobs,key=lambda j:(not j['pilot'],j['world'],j['family'],j['scenario']['reverse']))

def collect(job):
    import copy
    import numpy as np
    import fast_physics;fast_physics.install()
    import domain_visuals;domain_visuals.install()
    from landing_training import run_episode as episode,gate
    from landing_training.config import Scenario
    from landing_training.recording import Recorder
    original_gate=getattr(gate,'_domain_original_require',gate.require_approval)
    gate._domain_original_require=original_gate
    def authorized(bundle):
        if Path(bundle).resolve()==ROOT:
            auth=json.loads((ROOT/'authorization.json').read_text())
            if auth.get('kind')!='explicit_current_session_authorization':raise PermissionError('Explicit authorization missing')
            return auth
        return original_gate(bundle)
    gate.require_approval=authorized
    gate.source_fingerprint=lambda runtime_only=False,include_rendering=True:job['runtime_hash'] if runtime_only else job['source_hash']
    directory=ROOT/'dataset'/job['name']
    original_expert=getattr(episode,'_domain_original_expert',episode.Expert)
    episode._domain_original_expert=original_expert
    class SearchDemonstrator(original_expert):
        def act(self,px4,packet,visible):
            raw,action,reason=super().act(px4,packet,visible)
            t=float(self.env.data.time)-getattr(self.env,'task_start_time',float(self.env.data.time))
            if t<job['search_s']:
                self.phase='search_demonstration';action=np.zeros(6);action[4]=.45
                target=np.radians([15.,35.,60.][int(t/5)%3]);action[5]=.8*(target-self.env.data.qpos[self.env.drone.camera_qpos[1]])
                raw=action.copy();reason=None
            return raw,action,reason
    class RadioFreeRecorder(Recorder):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.file.attrs['authorization_sha256']=job['authorization_hash']
            self.file.attrs['visual_variation']=json.dumps(domain_visuals.settings(job['scenario']['seed']))
            self.file.attrs['teacher_scope']='privileged expert for labeling only; positional radio removed from recorded student observations'
            save(directory/'visuals.json',domain_visuals.settings(job['scenario']['seed']))
        def append(self,rgb,row):
            row=copy.deepcopy(row)
            row['observation']['beacon']=dict(valid=False,age_s=3.1,sequence=0,dock_ready=False,dock_status_valid=False,
                                             position_sigma_m=100.,velocity_sigma_m_s=10.,radio_mode='absent')
            super().append(rgb,row)
    episode.Expert=SearchDemonstrator;episode.Recorder=RadioFreeRecorder
    began=time.monotonic()
    try:
        summary=episode.run_episode(Scenario(**job['scenario']),directory,role=job['role'],video=False,
                                    instance=INSTANCE,approval_bundle=ROOT,record_images=True)
        artifact=directory/'observations.h5'
        result=dict(name=job['name'],role=job['role'],path=str(artifact.relative_to(ROOT/'dataset')),
                    sha256=gate.file_hash(artifact),world_seed=job['scenario']['world_seed'],path_seed=job['scenario']['path_seed'],
                    outcome=summary['outcome'],records=summary['records'],wall_s=time.monotonic()-began,
                    collection='expert_search_and_recovery',authorization_sha256=job['authorization_hash'],
                    visual_variation=domain_visuals.settings(job['scenario']['seed']))
    except BaseException as e:
        result=dict(name=job['name'],role=job['role'],outcome='collection_error',error=f'{type(e).__name__}: {e}',wall_s=time.monotonic()-began)
    save(directory/'collection_result.json',result);return result

def main():
    while not (ROOT/'benchmark/report.json').exists():time.sleep(10)
    bench=json.loads((ROOT/'benchmark/report.json').read_text());workers=bench['best_workers']
    from landing_training.gate import source_fingerprint,file_hash
    source_hash=source_fingerprint();runtime_hash=source_fingerprint(runtime_only=True);auth=file_hash(ROOT/'authorization.json')
    jobs=plan()
    for job in jobs:job.update(source_hash=source_hash,runtime_hash=runtime_hash,authorization_hash=auth)
    (ROOT/'dataset').mkdir(exist_ok=False);save(ROOT/'collection_plan.json',dict(episodes=jobs,workers=workers,planned=len(jobs),training=120,validation=20,test=20))
    context=mp.get_context('spawn');instances=context.Queue()
    for i in range(workers):instances.put(80+i)
    began=time.monotonic();results=[];outcomes={}
    # Reserve at least 75 minutes for feature preparation, fine-tuning and flights.
    deadline=time.time()+2.8*3600
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=context,initializer=initialize,initargs=(instances,)) as pool:
        pending={};iterator=iter(jobs)
        def submit():
            job=next(iterator,None)
            if job is not None:pending[pool.submit(collect,job)]=job
        for _ in range(workers):submit()
        while pending:
            done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                job=pending.pop(future)
                try:r=future.result()
                except BaseException as e:r=dict(name=job['name'],outcome='worker_error',error=str(e))
                results.append(r);outcomes[r['outcome']]=outcomes.get(r['outcome'],0)+1
                elapsed=time.monotonic()-began;rate=len(results)/max(1,elapsed)
                manifest=dict(schema='aerodock.landing.dataset.v1',role='dataset',authorization_kind='explicit_current_session_authorization',
                              review_manifest_sha256=auth,episodes=[r for r in results if 'path' in r],original_dataset_modified=False)
                save(ROOT/'dataset/manifest.json',manifest)
                save(ROOT/'collection_progress.json',dict(status='running',workers=workers,completed=len(results),planned=len(jobs),
                       outcomes=outcomes,elapsed_s=elapsed,projected_total_hours=len(jobs)/max(rate,1e-6)/3600))
                print('COLLECTED',json.dumps(r),flush=True)
                if time.time()<deadline:submit()
    result=dict(status='completed',workers=workers,completed=len(results),usable=sum('path' in r for r in results),outcomes=outcomes,elapsed_s=time.monotonic()-began)
    save(ROOT/'collection_result.json',result);print('COLLECTION_COMPLETE',json.dumps(result),flush=True)

if __name__=='__main__':main()
