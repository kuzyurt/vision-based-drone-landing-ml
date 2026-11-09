"""Freeze new worlds and narrow perception-data production evidence, no flights."""
from pathlib import Path
import datetime,hashlib,json,os,sys
import h5py,numpy as np
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
sys.path.insert(0,str(BASE))
from landing_training import paths
from landing_training.config import Scenario
from landing_training.gate import source_fingerprint
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seeds(value,result):
    if isinstance(value,dict):
        for k,v in value.items():
            if k in ['seed','world_seed','path_seed']and isinstance(v,int)and not isinstance(v,bool):result.add(v)
            else:seeds(v,result)
    elif isinstance(value,list):
        for v in value:seeds(v,result)

out=ROOT/'curriculum_v23';out.mkdir(exist_ok=True)
assert not(out/'plan.json').exists()and not(out/'contract.json').exists(),'Never overwrite a frozen curriculum'
authority=ROOT/'human_review_response_20261019.json';human=json.loads(authority.read_text())
assert human['future_visual_wait_required']is False and human['previous_preview_approved']is False
bench=json.loads((ROOT/'native_throughput_v22.json').read_text());assert bench['status']=='completed'
assert bench['selected_workers']==8
physics=json.loads((ROOT/'environment_cached_dynamics_comparison_v1.json').read_text())
assert physics['status']=='cached_core_physics_identical'and not physics['differences']and not physics['option_mismatches']
ep=ROOT/'expert_visible_native_v22_tilt';summary=json.loads((ep/'summary.json').read_text())
assert summary['outcome']=='landed'and not summary.get('failure')
assert source_fingerprint(runtime_only=True)==summary['runtime_source_sha256'],'Native runtime files changed since measured evidence'
audit=json.loads((ROOT/'v22_tilt_actual_ownership_audit.json').read_text())
assert not audit['actual_history_mismatches']and not audit['teacher_unsupported_descent_frames']
index=load_capture_index(ep/'capture_annotations.jsonl');joins=0
with h5py.File(ep/'observations.h5','r')as h:
    assert not h.attrs['training_eligible']
    for line in(ep/'steps.jsonl').open():
        row=json.loads(line)
        if join_delivered_frame(row['observation'],np.asarray(h['rgb'][row['frame_index']]),index):joins+=1
assert joins>=2000
# Inventory metadata only, including previous worlds and future held-out plans.
known=set();inventory={};errors=[]
for current,dirs,files in os.walk(BASE/'landing_training'):
    dirs[:]=[d for d in dirs if d not in ['.venv','.vendor','node_modules','__pycache__','build','.git']]
    for name in files:
        if name not in ['scenario.json','plan.json']:continue
        p=Path(current)/name
        if p.is_relative_to(out):continue
        try:
            payload=json.loads(p.read_text());seeds(payload,known);inventory[str(p)]=sha(p)
        except(ValueError,UnicodeDecodeError)as error:errors.append(dict(path=str(p),error=str(error)))
assert not errors,repr(errors)
rng=np.random.default_rng(1941026);jobs=[];worlds=[];reserved=set(known)
for i in range(45):
    kind=['island','beach','city','gravel','rock'][i%5]
    anchor=1400000+i*100
    while any(anchor+j in reserved for j in range(4)):anchor+=50000
    reserved.update(anchor+j for j in range(4));role='training'if i<10 else'validation'if i<15 else'heldout'
    worlds.append(dict(index=i,kind=kind,role=role,world_seed=anchor+1,path_seed=anchor+2))
    if role=='heldout':continue # Reserve untouched worlds; no images or flights yet.
    for rep in range(2):
        name=f'{role}_world_{i:02d}_{rep}';seed=anchor+20000+rep
        while seed in reserved:seed+=100000
        reserved.add(seed)
        distance=float([8.,20.,40.][i%3]if rep==0 else[8.,15.,25.][i%3])
        if i in [9,14]and rep==0:distance=60.
        scenario=Scenario(name=name,kind=kind,world_seed=anchor+1,path_seed=anchor+2,seed=seed,
            distance=distance,height=8. if distance>=40 else 6.,bearing_deg=float([-120.,60.,180.,-60.,120.][i%5]),
            boat_speed=float([.25,.4,.6][(i+rep)%3]),wave_height=float([.01,.03,.05][i%3]),
            wave_period=float(rng.uniform(2.5,4.5)),wave_direction_deg=float(rng.uniform(-180,180)),
            wind_profile='gusty'if i%3==2 else'breeze',wind_mean_m_s=float(rng.uniform(1.,3.)),
            initial_camera_target=False,initial_pan_deg=float([0.,90.,-120.,140.,-60.][(i+rep)%5]),
            initial_tilt_deg=float([15.,35.,65.][(i+rep)%3]),yaw_offset_deg=float([0.,30.,-45.][i%3]),
            image_brightness=float(rng.uniform(.85,1.15)),image_contrast=float(rng.uniform(.9,1.15)),
            image_blur_px=float([0.,.15,.3][i%3]),camera_delay_steps=int((i+rep)%3),duration=180.)
        scenario.validate();payload=vars(scenario)
        scene_file=out/(name+'.json');scene_file.write_text(json.dumps(payload,indent=2))
        jobs.append(dict(name=name,role=role,world_index=i,scenario_path=str(scene_file),scenario_sha256=sha(scene_file),
            mode='expert'if rep==0 and i%3==0 else'dagger',prefix=bool(rep==1),tilt_fault=bool(rep==1 and i%2==0)))
assert not({w['world_seed']for w in worlds}&known)
plan=dict(schema='mujoco.perception_curriculum.plan.v1',jobs=jobs,worlds=worlds,
    split_unit='whole world/trajectory; paired episodes share split',heldout_flights_generated=False,
    family_limit='Authored hard-scene distractor families shared; do not claim unseen boat-design families',
    inventory_files=inventory,metadata_inventory_sha256=hashlib.sha256(json.dumps(inventory,sort_keys=True).encode()).hexdigest(),
    inventory_scope='All scenario.json/plan.json under landing_training excluding vendor/cache/build; seeds checked before generation',
    workers=8,perception_only=True,action_imitation_authorized_by_this_manifest=False)
(out/'plan.json').write_text(json.dumps(plan,indent=2))
contract=dict(schema='mujoco.perception_curriculum.contract.v1',scope='New staged perception observations only; not teacher/deployment qualification',
    authority_response_sha256=sha(authority),plan_sha256=sha(out/'plan.json'),
    baseline_runtime_source_sha256=summary['runtime_source_sha256'],reference_summary_sha256=sha(ep/'summary.json'),
    hard_model_sha256=physics['hard_model_sha256'],physics_evidence_sha256=sha(ROOT/'environment_cached_dynamics_comparison_v1.json'),
    actual_annotation_joined_images=joins,actual_command_audit_sha256=sha(ROOT/'v22_tilt_actual_ownership_audit.json'),
    actual_camera_review='V22 actual ownership sheet inspected in this chat; learner recovered after prefix, no expert rescue claim',
    original_static_recognition_gate_passed=False,teacher_demonstration_qualified=False,
    grants_training_eligibility=False,old_review_recordings_admissible=False,
    action_targets_admissible=False,perception_admission_requires_exact_capture_labels_and_split_receipt=True,
    created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(out/'contract.json').write_text(json.dumps(contract,indent=2))
print(json.dumps(dict(status='staged_perception_plan_prepared',jobs=len(jobs),worlds=15,
    heldout_worlds_reserved=30,existing_seed_count=len(known),joined_reference_images=joins,
    contract_sha256=sha(out/'contract.json'),plan_sha256=sha(out/'plan.json')),indent=2))
