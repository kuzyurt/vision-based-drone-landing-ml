from pathlib import Path
import dataclasses,importlib.util,json,sys,types
R=Path(__file__).parent
spec=importlib.util.spec_from_file_location('guard',R/'unverified_descent_v43.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sample(t,z,id=False,frame=None,v=-.3,a=.3):
 e=types.SimpleNamespace(time_s=t,image_valid=True,image_age_s=.04,own_state_valid=True,target_confirmed=id,frame_id=round(t*1e6)if frame is None else frame)
 return e,dict(observation={'px4':{'armed':True,'landed':False}},learner={'metric_confirmed':True,'metric_age_s':.04},action=[0,0,a,0,0,0],own_height=z,own_vertical_speed=v)
for name,kwargs in [('confirmed',{'id':True}),('hover',{'v':0}),('ascending',{'v':.2}),('repeat',{'frame':1})]:
 g=m.UnverifiedDescent();assert not any(g.step(*sample(t,6-.3*t,**kwargs))for t in [k*.04 for k in range(300)]),name
g=m.UnverifiedDescent();hits=[t for t in [k*.04 for k in range(300)]if g.step(*sample(t,6-.3*t))];assert hits and hits[0]>=5.3
print(json.dumps(dict(passed=True,first_sustained_trigger_s=hits[0],negative_cases=['confirmed','hover','ascending','repeat'])))
