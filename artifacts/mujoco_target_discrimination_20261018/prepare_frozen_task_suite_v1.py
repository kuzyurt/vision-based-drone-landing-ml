"""Freeze independent scenarios before any held-out images/policy flights."""
from pathlib import Path
import collections,hashlib,json,os,sys
import numpy as np
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2];sys.path.insert(0,str(BASE))
from landing_training.config import Scenario
from landing_training.gate import source_fingerprint
OUT=ROOT/'frozen_task_suite_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def all_seeds(v,dest):
    if isinstance(v,dict):
        for k,x in v.items():
            if k in ['seed','world_seed','path_seed']and isinstance(x,int)and not isinstance(x,bool):dest.add(x)
            else:all_seeds(x,dest)
    elif isinstance(v,list):
        for x in v:all_seeds(x,dest)
def main():
    OUT.mkdir(exist_ok=False);prior_path=ROOT/'curriculum_v23/plan.json';prior=json.loads(prior_path.read_text())
    worlds=[w for w in prior['worlds']if w['role']=='heldout'];assert len(worlds)==30
    known=set();exposed=set();inventory={}
    for current,dirs,files in os.walk(BASE/'landing_training'):
        dirs[:]=[d for d in dirs if d not in ['.venv','.vendor','node_modules','__pycache__','build','.git']]
        for name in files:
            if name not in ['scenario.json','plan.json']:continue
            path=Path(current)/name;value=json.loads(path.read_text());all_seeds(value,known)
            if name=='scenario.json':all_seeds(value,exposed)
            inventory[str(path)]=sha(path)
    assert not({w['world_seed']for w in worlds}&exposed),'Reserved held-out world already exposed'
    rng=np.random.default_rng(2026101903);jobs=[];counters=collections.Counter()
    def add(name,scenario,*,inland=False,target_absent=False,fault=None,category='nominal',group='boat'):
        scenario.validate();scenario_file=OUT/(name+'_scenario.json');scenario_file.write_text(json.dumps(vars(scenario),indent=2))
        job=dict(name=name,scenario_file=str(scenario_file),scenario_sha256=sha(scenario_file),inland=inland,
            target_absent=target_absent,fault=fault or{},category=category,group=group,
            expected_success='home_landed'if target_absent else'landed',teacher_actions_allowed=False)
        job_file=OUT/(name+'_job.json');job_file.write_text(json.dumps(job,indent=2))
        jobs.append(dict(name=name,job_file=str(job_file),job_sha256=sha(job_file),group=group,category=category,
            map=scenario.kind,world_seed=scenario.world_seed,scenario_file=str(scenario_file),scenario_sha256=sha(scenario_file)))
        counters[group+':'+scenario.kind]+=1
    for i,w in enumerate(worlds):
        for rep in range(2):
            seed=w['world_seed']+50000+rep
            while seed in known:seed+=100000
            known.add(seed);inland=rep==1 and i%3==0
            distance=60. if inland else float(([8.,20.,40.,60.][i%4])if rep==0 else[12.,30.,50.][i%3])
            category='tilt_loss'if rep==1 and i%3==1 else'yaw_resync'if rep==1 and i%3==2 else'inland'if inland else'nominal'
            fault=dict(kind='gimbal_tilt'if category=='tilt_loss'else'gimbal_pan',trigger_clearance_m=.65,
                duration_s=1.6 if category=='tilt_loss'else 1.2,pan_rate_rad_s=.6981317008)if category in ['tilt_loss','yaw_resync']else{}
            s=Scenario(name=f'fresh_boat_{i:02d}_{rep}',kind=w['kind'],world_seed=w['world_seed'],path_seed=w['path_seed'],seed=seed,
                distance=distance,height=8. if distance>=40 or inland else 6.,bearing_deg=float([-120.,60.,180.,-60.,120.][i%5]),
                boat_speed=float([.2,.4,.6][(i+rep)%3]),wave_height=float([.01,.03,.05][i%3]),wave_period=float(rng.uniform(2.5,4.5)),
                wave_direction_deg=float(rng.uniform(-180,180)),wind_profile='gusty'if i%3==2 else'breeze',wind_mean_m_s=float(rng.uniform(1,3)),
                initial_camera_target=False,initial_pan_deg=float([0.,90.,-120.,140.,-60.][(i+rep)%5]),initial_tilt_deg=float([15.,35.,65.][(i+rep)%3]),
                yaw_offset_deg=float([0.,30.,-45.][i%3]),image_brightness=float(rng.uniform(.85,1.15)),image_contrast=float(rng.uniform(.9,1.15)),
                image_blur_px=float([0.,.15,.3][i%3]),camera_delay_steps=(i+rep)%3,duration=180.)
            add(s.name,s,inland=inland,fault=fault,category=category)
    for i in range(10):
        anchor=3100000+i*100
        while any(anchor+n in known for n in [0,1,2]):anchor+=50000
        known.update(anchor+n for n in [0,1,2]);kind=['island','beach','city','gravel','rock'][i%5]
        s=Scenario(name=f'fresh_home_{i:02d}',kind=kind,seed=anchor,world_seed=anchor+1,path_seed=anchor+2,distance=20.,height=6.,
            boat_speed=.4,wave_height=.03,wind_profile='breeze',wind_mean_m_s=1.5,initial_camera_target=False,
            initial_pan_deg=90.,initial_tilt_deg=35.,camera_blind_seconds=180. if i>=5 else 0.,duration=180.)
        add(s.name,s,target_absent=True,category='no_target_camera_unavailable'if i>=5 else'no_target',group='home')
    assert len(jobs)==70 and all(counters['boat:'+k]==12 for k in ['island','beach','city','gravel','rock'])
    contract=json.loads((ROOT/'curriculum_v23/contract.json').read_text())
    assert source_fingerprint(runtime_only=True)==contract['baseline_runtime_source_sha256']
    plan=dict(schema='mujoco.frozen_physical_task_suite.v1',jobs=jobs,heldout_worlds=worlds,
        source_reserved_plan_sha256=sha(prior_path),native_runtime_sha256=source_fingerprint(runtime_only=True),
        metadata_inventory_sha256=hashlib.sha256(json.dumps(inventory,sort_keys=True).encode()).hexdigest(),
        generated_images=False,policy_flown=False,actor_binding_pending=True,source_sha256=sha(__file__),
        qualification=dict(boat_minimum=57,boat_total=60,maximum_collision=0,maximum_wrong_boat_touchdown=0,maximum_water_strike=0,
            physical_home_minimum=10,physical_home_total=10,minimum_observed_camera_fault_missions=5),
        physical_criteria_unchanged=True,cold_static_gate_separate_and_still_failed=True,
        authored_distractor_families_shared_with_training=True,unseen_distractor_family_claim=False,
        categories=dict(collections.Counter(j['category']for j in jobs)),map_counts=dict(counters),
        note='Independent scenarios frozen before candidate flight. Own-home must physically disarm; diagnostic stops never qualify.')
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(dict(status='frozen_scenarios_only',jobs=len(jobs),plan_sha256=sha(OUT/'plan.json'),categories=plan['categories'])))
if __name__=='__main__':main()
