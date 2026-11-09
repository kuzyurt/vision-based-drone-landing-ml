"""Static setup repair, before any replacement flight or controller change.

Some boat route phases are>60m offshore, so no60m in-air over-land start exists.
Retain the ORIGINAL world/path/sensor seeds, radius60m, height8m, wind, waves,
camera and speed. For invalid zero-frame setups ONLY, sort eligible route
vertices by static distance to shore, then vertex index; choose the first phase
passing the UNCHANGED original inland placement and reserve rules. No policy
is evaluated. All executed original flights must remain in qualification.
"""
import os
os.environ.update(MUJOCO_GL='egl',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
from pathlib import Path
import copy,gc,hashlib,json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
sys.path[:0]=[str(BASE),str(ROOT/'mission_helpers')]
from landing_training.environment import Environment
from landing_training.config import Scenario
from mission_setup import InlandStartEnvironment
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=ROOT/'fresh_edge_C60.json'
assert sha(plan)=='4ab63a761b5bef38c2469d1261a7070ccfcd002dca988cb4dd97b346a8f8d725'
out=ROOT/'inland_phase_preflight_v2';out.mkdir(exist_ok=False)
records=[];replacements=[]
for original in json.loads(plan.read_text())['cases']:
    if not original.get('inland'):continue
    case=out/original['source_case'];case.mkdir()
    record=dict(original_case=original['source_case'],attempts=[])
    def check(job,label):
        dest=case/label;dest.mkdir();InlandStartEnvironment.audit_directory=dest
        try:
            env=InlandStartEnvironment(Scenario(**job['scenario']))
            spawn=json.loads((dest/'spawn.json').read_text());del env;gc.collect()
            assert spawn['signed_shore_distance_m']<-5 and spawn['planned_terrain_clearance_m']>=2
            assert abs(spawn['planned_horizontal_distance_m']-60)<1e-6
            value=dict(label=label,valid=True,spawn=spawn,boat_start_fraction=job['scenario']['boat_start_fraction'])
        except ValueError as e:
            if str(e)!='No physically valid inland start at the prescribed radius and height':raise
            value=dict(label=label,valid=False,error=str(e),boat_start_fraction=job['scenario']['boat_start_fraction'])
        record['attempts'].append(value);(case/'attempts.json').write_text(json.dumps(record,indent=2));gc.collect()
        return value['valid']
    if not check(original,'original_phase'):
        env=Environment(Scenario(**original['scenario']));w=env.boat.navigation.world;route=w.route
        reserve=original['scenario']['boat_speed']*original['scenario']['duration']+20
        indices=np.where((route.arc>reserve)&(route.arc<route.length-reserve))[0]
        distances=w.distance(route.points[indices]);order=sorted(range(len(indices)),key=lambda k:(float(distances[k]),int(indices[k])))
        candidates=[(int(indices[k]),float(distances[k]),float((route.arc[indices[k]]-reserve)/(route.length-2*reserve))) for k in order[:256]]
        del env;gc.collect();record['ranked_static_phase_candidates']=candidates
        for n,(vertex,distance,fraction) in enumerate(candidates):
            job=copy.deepcopy(original);job['scenario']['boat_start_fraction']=fraction
            job['source_case']=job['name']=job['scenario']['name']=original['source_case']+'_geometry_replacement'
            if check(job,f'ranked_phase_{n:03d}'):
                replacements.append(dict(original_case=original['source_case'],job=job,route_vertex=vertex,static_boat_shore_distance_m=distance,
                    reason='Original phase places boat too far offshore for a60m over-land start; deterministic static phase repair only'))
                break
        else:raise RuntimeError('No physically valid phase within frozen static256vertex rule: '+original['source_case'])
    records.append(record)
result=dict(status='static_setup_preflight_completed',rule=__doc__,original_plan_sha256=sha(plan),candidate_policy_sha256=sha(ROOT/'candidate_r7/policy.json'),
    no_policy_evaluated=True,seeds_and_conditions_unchanged=True,records=records,replacements=replacements,updated=time.time())
(out/'receipt.json').write_text(json.dumps(result,indent=2))
p=ROOT/'C_infrastructure_phase_replacement_plan.json';assert not p.exists()
p.write_text(json.dumps(dict(role='final_holdout',cases=[x['job'] for x in replacements],note=__doc__),indent=2))
print(json.dumps(dict(status=result['status'],replacements=[x['original_case'] for x in replacements])))
