"""Predeclare untouched worlds before tuning; never run a policy here."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from dataclasses import asdict

ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
OLD=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(OLD))
from landing_training import paths
from landing_training.config import Scenario


def main():
    destination=ROOT/'fresh_holdout_60.json'
    if destination.exists():raise FileExistsError('Frozen holdout must not be replaced')
    jobs=[]
    for family,kind in enumerate(['island','beach','city','gravel','rock']):
        for world in range(6):
            for reverse in [False,True]:
                seed=9130000+family*1000+world*2+int(reverse)
                rng=np.random.default_rng(seed)
                inland=kind in ['beach','gravel'] and world==5
                name=f'fresh_{kind}_{world:02d}_{int(reverse)}'+('_inland' if inland else '')
                scenario=Scenario(name=name,kind=kind,world_seed=9230000+family*100+world,path_seed=9330000+family*100+world,
                    seed=seed,reverse=reverse,world_rotation_deg=float(rng.uniform(0,360)),
                    distance=[3.,8.,20.,40.,60.,60.][world],height=8. if inland else [3.,5.,4.,7.,6.,7.][world],
                    bearing_deg=float(rng.uniform(-180,180)),yaw_offset_deg=float(rng.uniform(-180,180)),
                    boat_speed=[.2,.4,.6,.8,.9,.65][world],boat_start_fraction=float(rng.uniform(.1,.9)),
                    wave_height=[0.,.01,.03,.05,.02,.04][world],wave_period=float(rng.uniform(2.5,4.5)),wave_direction_deg=float(rng.uniform(0,360)),
                    wind_profile=['calm','breeze','gusty','steady2','gusty','breeze'][world],
                    wind_mean_m_s=0. if world==0 else float(rng.uniform(.5,3.)),wind_direction_deg=float(rng.uniform(0,360)),
                    initial_camera_target=world==0,initial_pan_deg=float(rng.uniform(-180,180)),initial_tilt_deg=float(rng.choice([0,15,35,60,90])),
                    image_brightness=float(rng.uniform(.85,1.15)),image_contrast=float(rng.uniform(.85,1.15)),image_blur_px=float(rng.uniform(0,.45)),
                    camera_delay_steps=int(rng.integers(0,6)),duration=180.)
                scenario.validate()
                job=dict(name=name,source_case=name,scenario=asdict(scenario),varied_visuals=True,radio='none',
                    role='final_holdout',far_start=inland,record_rgb=False,inland=inland)
                jobs.append(job)
    old=json.loads((OLD/'collection_plan.json').read_text())['episodes']
    seen={j['scenario']['world_seed'] for j in old}
    assert all(j['scenario']['world_seed'] not in seen for j in jobs)
    # Check only initial-condition feasibility of the four land starts. No RGB,
    # learned policy or task outcome is inspected during this setup audit.
    from mission_setup import InlandStartEnvironment
    for job in jobs:
        if not job['inland']:continue
        attempts=[];original_fraction=job['scenario']['boat_start_fraction']
        fractions=[original_fraction]+[float(v) for v in np.linspace(.1,.9,9)]
        for index,fraction in enumerate(fractions):
            directory=ROOT/'fresh_spawn_setup_v3'/job['name']/f'attempt_{index:02d}'
            directory.mkdir(parents=True,exist_ok=False)
            InlandStartEnvironment.audit_directory=directory
            trial=dict(job['scenario'],boat_start_fraction=fraction)
            try:env=InlandStartEnvironment(Scenario(**trial))
            except ValueError as exc:
                reason=dict(fraction=fraction,feasible=False,reason=str(exc));attempts.append(reason)
                (directory/'infeasible.json').write_text(json.dumps(reason,indent=2));continue
            attempts.append(dict(fraction=fraction,feasible=True))
            job['scenario']=trial;job['spawn_audit']=json.loads((directory/'spawn.json').read_text())
            job['spawn_setup_attempts']=attempts
            del env;break
        else:raise ValueError('No valid inland initial condition at any predeclared coastal route fraction: '+job['name'])
    plan=dict(schema='observable_landing.frozen_holdout.v1',cases=jobs,planned=60,maps=5,episodes_per_map=12,
        min_landings=57,max_collisions=0,no_radio=True,physics_and_touchdown_unchanged=True,
        policy_evaluated=False,setup_only_land_spawns_checked=True,
        rule='Evaluate only after development warrants it. If tuned after inspecting these outcomes, they become development and a new untouched suite is required.',
        safe_fallback='separate target-unavailable suite; safe aborts do not count as landings in these 60 cases')
    destination.write_text(json.dumps(plan,indent=2));digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    (ROOT/'fresh_holdout_60.sha256').write_text(digest+'  fresh_holdout_60.json\n')
    print(json.dumps(dict(planned=len(jobs),sha256=digest,inland=sum(j['inland'] for j in jobs),policy_runs=0)),flush=True)


if __name__=='__main__':main()
