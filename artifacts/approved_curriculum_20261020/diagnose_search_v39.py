from pathlib import Path
import collections,json,math
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'search_v39/closed_diagnosis';OUT.mkdir(exist_ok=True)
def run(name):
    case=ROOT/'search_v39/pilots'/name
    assert(case/'preview_result.json').exists(),'Closed cases only'
    ann={round(json.loads(l)['capture_s']*1e6):json.loads(l)for l in(case/'capture_annotations.jsonl').open()}
    rows=[json.loads(l)for l in(case/'steps.jsonl').open()];targetviews=[];phases=collections.Counter();bands=collections.Counter();bestp=0.;matched=0;selectedtarget=0;examples=[];corridor=0;approach=0;xycommands=0;selection=collections.Counter();positions=[];transitions=[];previous=None
    for i,r in enumerate(rows):
        d=r.get('output',{}).get('learner_diagnostics')or{};o=r['observation'];phases[d.get('control_phase')]+=1;bands[str(d.get('expert_scan_band'))]+=1
        intent=d.get('expert_intent')or{};corridor+=bool((o.get('mission',{}).get('target_discrimination')or{}).get('search_corridor_valid'));approach+=bool(intent.get('allow_approach'));xycommands+=np.linalg.norm(r['output']['executed_action'][:2])>.01;selection[str(intent.get('selected_track'))]+=1;positions.append(o['px4']['position_enu_m']);key=(intent.get('phase'),intent.get('selected_track'))
        if key!=previous:transitions.append(dict(task_s=r.get('task_time_s'),intent=intent,own_xy=o['px4']['position_enu_m'][:2],tracks=d.get('expert_visual_tracks')));previous=key
        a=ann.get(round(o['image_capture_time_s']*1e6));inst=next((x for x in(a or{}).get('instances',[])if x['annotation_instance']=='target'),None)
        if inst:
            a1,b1,a2,b2=inst['bbox'];tracks=[t for t in d.get('expert_visual_tracks',[])if abs(t['capture_s']-o['image_capture_time_s'])<1e-6 and a1<=t['pixel'][0]<=a2 and b1<=t['pixel'][1]<=b2]
            best=max([t['target_probability']for t in tracks]or[0.]);bestp=max(bestp,best);matched+=bool(tracks)
            sel=(d.get('expert_intent')or{}).get('selected_track');selectedtarget+=any(t['track_id']==sel for t in tracks)
            targetviews.append(dict(frame=i,task_s=r.get('task_time_s'),pixels=inst['pixels'],identity=inst['identity'],bbox=inst['bbox'],best_actual_target_probability=best,matched_tracks=len(tracks),phase=d.get('control_phase')))
            if best>.9 and len(examples)<4:examples.append(targetviews[-1])
    select=[]
    if targetviews:
        select=[targetviews[0]['frame'],max(targetviews,key=lambda x:x['pixels'])['frame'],max(targetviews,key=lambda x:x['best_actual_target_probability'])['frame']]
    select=list(dict.fromkeys([0,*select,*np.linspace(0,len(rows)-1,6).astype(int).tolist()]))[:10]
    sheet=Image.new('RGB',(960,210*math.ceil(len(select)/3)),(15,15,15))
    with h5py.File(case/'observations.h5','r')as h:
        for k,i in enumerate(select):
            image=Image.fromarray(h['rgb'][i]).resize((320,180));sheet.paste(image,((k%3)*320,(k//3)*210));r=rows[i];d=r['output'].get('learner_diagnostics')or{};v=next((v for v in targetviews if v['frame']==i),{})
            ImageDraw.Draw(sheet).text(((k%3)*320+3,(k//3)*210+182),f"{name} task {r.get('task_time_s',0):.2f} {d.get('control_phase')}\nactual target px {v.get('pixels',0)} p {v.get('best_actual_target_probability',0):.3f}",fill='white')
    sheet.save(OUT/(name+'_actual_rgb.jpg'),quality=87)
    result=dict(case=name,frames=len(rows),actual_target_visible_frames=len(targetviews),known_design_views=sum(v['identity']==1 for v in targetviews),first_target=targetviews[0]if targetviews else None,max_target_pixels=max([v['pixels']for v in targetviews]or[0]),matched_target_track_frames=matched,maximum_target_probability_on_actual_target=bestp,selected_actual_target_frames=selectedtarget,phases=dict(phases),bands=dict(bands),last_diagnostics=rows[-1]['output'].get('learner_diagnostics'),examples=examples,truth_actor_input=False,certified_search_corridor_rows=corridor,allow_approach_rows=approach,nonzero_xy_command_rows=int(xycommands),selected_track_counts=dict(selection),own_max_displacement_m=float(np.max(np.linalg.norm(np.asarray(positions)[:,:2]-np.asarray(positions)[0,:2],axis=1))),selection_transitions=transitions)
    (OUT/(name+'.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['last_diagnostics','examples']}),flush=True)
for name in ['search_far','search_mid']:run(name)
