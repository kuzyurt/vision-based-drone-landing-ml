"""Exact captured visual labels from NEW admitted closed collection_v2 only."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys,time
import h5py,numpy as np
ROOT=Path(__file__).resolve().parent;COL=ROOT/'collection_v2';ADMISSION=ROOT/'admission_new_v2';OUT=ROOT/'perception_admission_motion_v3'
sys.path.insert(0,str(ROOT/'search_v39/sources'))
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
FORBIDDEN={'return_home','land_home','home_land','home_landed','return_to_home','collection_stop_hold'}
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,x):t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2,allow_nan=False));t.replace(p)
def main():
    begin=time.monotonic();assert json.loads((ADMISSION/'state.json').read_text())['status']=='closed';m=json.loads((ADMISSION/'manifest.json').read_text());assert m['raw_eligibility_never_changed']and not m['teacher_action_targets']and not m['old_quarantined_or_retired_data_used'];assert sha(COL/'plan.json')==m['source_plan_sha256'];assert sha(COL/'data_contract.json')==m['data_contract_sha256'];plan=json.loads((COL/'plan.json').read_text());jobs={j['name']:j for j in plan['jobs']};roles={r:{e['world_seed']for e in m['entries']if e['role']==r}for r in ['training','validation']};assert not roles['training']&roles['validation'];OUT.mkdir(exist_ok=False);entries=[]
    for e in m['entries']:
        name=e['name'];role=e['role'];source=Path(e['source']);case=source.parent;assert source.resolve().parent.parent==(COL/'episodes').resolve()and source.name=='observations.h5';assert sha(source)==e['source_sha256']and sha(e['annotations'])==e['annotations_sha256']and sha(e['audit'])==e['audit_sha256'];audit=json.loads(Path(e['audit']).read_text());assert audit['status']=='passed';assert role in ['training','validation']and not e['raw_training_eligible']and not e['teacher_action_labels'];job=jobs[name];scenario=json.loads((case/'scenario.json').read_text());assert scenario==job['scenario'];assert scenario['world_seed']==e['world_seed'];index=load_capture_index(e['annotations']);seen=set();selected=[];last=-float('inf');last_owner=None;dst=OUT/name;dst.mkdir()
        with h5py.File(source,'r')as h,h5py.File(dst/'data.h5','x')as out:
            assert str(h.attrs.get('training_eligible'))in ['False','false','0'];images=out.create_dataset('rgb',(0,360,640,3),maxshape=(None,360,640,3),dtype='u1',chunks=(1,360,640,3),compression='lzf');labels=out.create_dataset('labels',(0,),maxshape=(None,),dtype=h5py.string_dtype());out.attrs.update(schema='approved.motion.visual-derivative.v3',role=role,teacher_actions=False,action_targets_admissible=False)
            for i in range(len(h['steps'])):
                row=json.loads(h['steps'][i]);o=row['observation'];d=row['output'].get('learner_diagnostics')or{};owner=d.get('actual_command_owner');phase=d.get('control_phase');transition=owner!=last_owner;last_owner=owner
                if not o['image_valid']or owner in FORBIDDEN or phase in FORBIDDEN or row.get('phase')in FORBIDDEN:continue
                stamp=float(o['image_capture_time_s']);recover=bool(d.get('recovery_active')or phase in ['local_downlook','recovery_climb','recovery_downlook']);stride=.25 if role=='training'and recover else .5
                if stamp-last<stride-1e-7 and not(role=='training'and transition):continue
                rgb=np.asarray(h['rgb'][i]);label=join_delivered_frame(o,rgb,index);uid=label['capture_uid']
                if uid in seen:continue
                seen.add(uid);last=stamp;label=json.loads(json.dumps(label));label.update(role=role,world_seed=e['world_seed'],path_seed=e['path_seed'],kind=e['kind'],index=len(selected),delivered_row_index=i,source_capture_uid=uid,teacher_actions=False,action_loss_mask=False,source_owner_diagnostic_only=owner)
                signed=rgb.astype(np.int16);cyan=(np.minimum(signed[...,1],signed[...,2])-signed[...,0]>45)&(signed[...,1]>=signed[...,2]-12)&(signed[...,1]>85)
                for inst in label['instances']:
                    x0,y0,x1,y1=inst['bbox'];contrast=int(cyan[y0:y1,x0:x1].sum());inst['marker_contrast_pixels_annotation_only']=contrast;ready=contrast>=32 and inst.get('marker_visible_pixels',0)>=32
                    inst['marker_head_loss_available']=bool(inst.get('marker_label_available',False));inst['marker_readiness_label']=int(ready)
                    if not ready:inst['pad_pixel']=None;inst['pad_label_available']=False
                n=len(selected);images.resize(n+1,axis=0);labels.resize(n+1,axis=0);images[n]=rgb;labels[n]=json.dumps(label);selected.append(dict(source_row=i,capture_uid=uid,rgb_sha256=label['rgb_sha256'],capture_s=stamp,action_loss_mask=False,source_owner=owner))
        assert selected;save(dst/'lineage.json',selected);record=dict(name=name,role=role,family=e['family'],path=str(dst/'data.h5'),sha256=sha(dst/'data.h5'),frames=len(selected),world_seed=e['world_seed'],path_seed=e['path_seed'],source_h5_sha256=e['source_sha256'],source_annotation_sha256=e['annotations_sha256'],source_audit_sha256=e['audit_sha256'],lineage_sha256=sha(dst/'lineage.json'),raw_eligibility_unchanged=True,action_targets_admissible=False,validation_fixed_2hz=role=='validation',training_recovery_4hz=role=='training');save(dst/'receipt.json',record);entries.append(record);save(OUT/'state.json',dict(status='deriving',closed_sources=len(entries),frames=sum(x['frames']for x in entries)))
    report=dict(status='completed',schema='approved.motion.visual-manifest.v3',entries=entries,admission_manifest_sha256=sha(ADMISSION/'manifest.json'),source_sha256=sha(__file__),teacher_actions_used=False,tidewater_used=False,heldout_used=False,raw_eligibility_never_changed=True,frames=sum(x['frames']for x in entries),wall_s=time.monotonic()-begin);save(OUT/'manifest.json',report);save(OUT/'state.json',report);print(json.dumps({k:v for k,v in report.items()if k!='entries'}),flush=True)
if __name__=='__main__':main()
