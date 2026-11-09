"""Repair zero-frame impossible setup geometry, never an executed policy failure.

Rule is declared before replacement flights: retain map kind, exact60m radius,
8m height and every condition except fresh world/path/sensor seeds. First seed
offset10,000,000*(attempt+1) satisfying the ORIGINAL inland placement rule wins.
No policy, image, action, score or outcome is evaluated in this preflight.
"""
import os
os.environ.update(MUJOCO_GL='egl', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
from pathlib import Path
import copy, gc, hashlib, json, sys, time
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[2]
sys.path[:0]=[str(BASE),str(ROOT/'mission_helpers')]
from landing_training.config import Scenario
from mission_setup import InlandStartEnvironment

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

plan=ROOT/'fresh_edge_C60.json'
assert sha(plan)=='4ab63a761b5bef38c2469d1261a7070ccfcd002dca988cb4dd97b346a8f8d725'
out=ROOT/'inland_fixture_preflight';out.mkdir(exist_ok=False)
source=json.loads(plan.read_text())
manifest=json.loads((BASE/'landing_training/outputs/vision_first_fusion_20261017T184307Z/motion_manifest.json').read_text())
used=set()
for e in manifest['entries']:
    s=json.loads((Path(e['source_path']).parent/'scenario.json').read_text());s=s.get('scenario',s)
    used.add((s['kind'],s['world_seed']))
used.update((j['scenario']['kind'],j['scenario']['world_seed']) for j in source['cases'])
records=[];replacements=[]
for j in source['cases']:
    if not j.get('inland'):continue
    record=dict(original_case=j['source_case'],attempts=[])
    for index in range(11):
        job=copy.deepcopy(j)
        if index:
            delta=10_000_000*index
            for key in ['world_seed','path_seed','seed']:job['scenario'][key]+=delta
            job['source_case']=job['name']=job['scenario']['name']=j['source_case']+'_geometry_replacement'
            assert (job['scenario']['kind'],job['scenario']['world_seed']) not in used
        dest=out/(j['source_case']+f'_attempt{index}')
        dest.mkdir();InlandStartEnvironment.audit_directory=dest
        try:
            env=InlandStartEnvironment(Scenario(**job['scenario']))
            spawn=json.loads((dest/'spawn.json').read_text())
            assert spawn['signed_shore_distance_m']<-5 and spawn['planned_terrain_clearance_m']>=2
            assert abs(spawn['planned_horizontal_distance_m']-60)<1e-6
            del env;gc.collect()
            record['attempts'].append(dict(index=index,valid=True,spawn=spawn))
            if index:
                replacements.append(dict(original_case=j['source_case'],job=job,reason='No physically valid inland start at prescribed radius and height; original placement rule unchanged',first_valid_seed_offset=10_000_000*index))
            break
        except ValueError as e:
            if str(e)!='No physically valid inland start at the prescribed radius and height':raise
            record['attempts'].append(dict(index=index,valid=False,error=str(e)))
        gc.collect()
    else:raise RuntimeError('No replacement fixture within declared11attempt rule: '+j['source_case'])
    records.append(record)
result=dict(status='static_setup_preflight_completed',original_plan_sha256=sha(plan),candidate_policy_sha256=sha(ROOT/'candidate_r7/policy.json'),
    rule=__doc__,no_policy_evaluated=True,records=records,replacements=replacements,updated=time.time())
(out/'receipt.json').write_text(json.dumps(result,indent=2))
if replacements:
    p=ROOT/'C_infrastructure_replacement_plan.json';assert not p.exists()
    p.write_text(json.dumps(dict(role='final_holdout',cases=[x['job'] for x in replacements],note='Zero-frame impossible geometry replacements only. Original executed flights and failed setup artifacts remain. Candidate and original operational sources unchanged.'),indent=2))
print(json.dumps(dict(status=result['status'],replacements=[x['original_case'] for x in replacements])))
