"""Define development and target-unavailable checks without using final outcomes."""
from pathlib import Path
import copy,json

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'domain_training_20261016T134939Z'


def main():
    old=json.loads((OLD/'evaluation_heldout/plan.json').read_text())['cases']
    names=['test_beach_14_1','test_city_14_0','test_city_14_1','test_gravel_14_1','test_gravel_15_0',
           'test_beach_15_1','test_island_14_0','test_rock_14_0','test_city_15_0','test_gravel_14_0']
    jobs=[]
    for name in names:
        j=copy.deepcopy(next(j for j in old if j['source_case']==name))
        j.update(role='development',vertical_launch=True,record_rgb=True)
        jobs.append(j)
    regression=json.loads((OLD/'evaluation_regression/plan.json').read_text())['cases']
    for inland in [False,True]:
        j=copy.deepcopy(next(j for j in regression if j.get('far_start') and ('inland' in j['scenario']['name'])==inland))
        name='dev_far60_inland' if inland else 'dev_far60_water'
        j.update(name=name,source_case=name,role='development',vertical_launch=True,inland=inland,record_rgb=True)
        j['scenario']['name']=name;j['scenario']['distance']=60.
        jobs.append(j)
    plan=dict(cases=jobs,role='development',planned=12,
        note='Previously inspected worlds; actual RGB retained; physical home below initial airborne start; mission fallback enabled. Not a fresh-generalization claim.')
    (ROOT/'extended_development_plan.json').write_text(json.dumps(plan,indent=2))
    absent=[]
    for index,name in enumerate(['test_island_14_0','test_beach_15_1','test_city_15_0','test_gravel_15_1','test_rock_15_0','test_beach_14_0']):
        j=copy.deepcopy(next(j for j in old if j['source_case']==name));label=f'no_visual_boat_{index:02d}_{j["scenario"]["kind"]}'
        j.update(name=label,source_case=label,role='target_unavailable',vertical_launch=True,remove_boat_visuals=True,
            record_rgb=True,search_timeout_s=60.)
        j['scenario']['name']=label;absent.append(j)
    (ROOT/'target_unavailable_plan.json').write_text(json.dumps(dict(cases=absent,planned=6,
        note='Boat visual geometry removed while physics remains intact. Same public mission/policy; target-removal flag is NOT supplied to the controller. Score physical home landings separately.'),indent=2))
    print(json.dumps(dict(development=12,target_unavailable=6,fresh_holdout_not_executed=True)),flush=True)


if __name__=='__main__':main()
