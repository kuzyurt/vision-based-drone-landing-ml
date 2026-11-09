"""CPU-only exact-capture RGB admission for corrected original visual labels."""
from pathlib import Path
import collections,datetime as dt,hashlib,json,os,select,time
import h5py,numpy as np
from visual_consumer_v1 import SCHEMA,sha,validate_record,self_test
ROOT=Path(__file__).resolve().parent;DATA=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/datasets/expert');OUT=ROOT/'original_rgb_admission/v1'
def wait_pid(pid):
    try:fd=os.pidfd_open(pid)
    except ProcessLookupError:return
    try:p=select.poll();p.register(fd,select.POLLIN);p.poll()
    finally:os.close(fd)
def paint(rgb):
    v=rgb.astype(np.int16);return(np.minimum(v[...,1],v[...,2])-v[...,0]>45)&(v[...,1]>=v[...,2]-12)&(v[...,1]>85)
def main():
    wait_pid(635368);m=json.loads((ROOT/'original_masks/v1/manifest.json').read_text());assert m['status']=='metadata_masks_completed_rgb_admission_pending'
    OUT.mkdir(parents=True,exist_ok=False);start=time.monotonic();test=self_test(ROOT,DATA);(OUT/'consumer_self_test.json').write_text(json.dumps(test,indent=2));chosen=[]
    for role,step in [('training',10),('validation',5)]:chosen.extend([e for e in m['episodes']if e['role']==role][::step])
    rng=np.random.default_rng(20261020);sources=[];counts=collections.Counter();records=[]
    tmp=OUT/'data.h5.tmp'
    with h5py.File(tmp,'x')as dest:
        images=dest.create_dataset('rgb',(0,360,640,3),maxshape=(None,360,640,3),chunks=(1,360,640,3),dtype='u1',compression='lzf');labels=[]
        for ei,e in enumerate(chosen):
            path=DATA/e['path'];assert sha(path)==e['source_sha256'];maskfile=ROOT/e['mask_path'];assert sha(maskfile)==e['mask_sha256'];masks=np.load(maskfile)
            candidate=masks['center_candidate'];point=masks['center_px'];radius=np.linalg.norm(point-[320,180],axis=1);valid=masks['valid_capture'];capture=masks['capture_row'];groups=[np.flatnonzero(valid&~candidate),np.flatnonzero(candidate&(radius>80)),np.flatnonzero(candidate&(radius>30)&(radius<=80)),np.flatnonzero(candidate&(radius<=30))]
            indices=[]
            for g in groups:
                if len(g):indices.extend(np.sort(rng.choice(g,min(6,len(g)),replace=False)).tolist())
            with h5py.File(path,'r')as h:
                assert str(h.attrs['role'])==e['role']and str(h.attrs['training_eligible'])in ['True','true','1'];rows=[json.loads(x)for x in h['steps']]
                scenario=json.loads(h.attrs['scenario']);before=len(records)
                for i in sorted(set(indices)):
                    row=rows[i];o=row['observation'];j=int(capture[i]);assert j>=0 and abs(rows[j]['time_s']-o['image_capture_time_s'])<=1e-6
                    rgb=h['rgb'][i];support=paint(rgb);positive=bool(candidate[i]);xy=point[i]
                    if positive:
                        x,y=xy;near=support[max(0,int(y)-12):min(360,int(y)+13),max(0,int(x)-12):min(640,int(x)+13)]
                        if near.sum()<4:counts['unverified_marker_positive_excluded']+=1;continue
                    elif support.sum()>=4:counts['ambiguous_negative_excluded']+=1;continue
                    rec=dict(schema=SCHEMA,source=str(path),source_sha256=e['source_sha256'],role=e['role'],phase=row['phase'],action_loss=False,boat_identity_loss=False,exact_capture_join=True,frame_index=i,capture_row=j,capture_s=o['image_capture_time_s'],rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),world_seed=e['world_seed'],path_seed=e['path_seed'],kind=scenario['kind'],center_loss=positive,marker_presence_loss=True,marker_present=positive,center_px=xy.tolist()if positive else[0.,0.],actual_cyan_pixels=int(support.sum()))
                    validate_record(rec,experiment_root=ROOT,original_root=DATA)
                    k=len(records);images.resize(k+1,axis=0);images[k]=rgb;records.append(rec);labels.append([int(positive),*rec['center_px'],int(e['role']=='validation')]);counts[e['role']+':'+('positive'if positive else'negative')]+=1
                sources.append(dict(path=str(path),sha256=e['source_sha256'],role=e['role'],world_seed=e['world_seed'],frames=len(records)-before,mask_sha256=e['mask_sha256']))
            if ei%10==0:
                p=OUT/'state.json.tmp';p.write_text(json.dumps(dict(status='preparing',episodes=ei+1,total=len(chosen),frames=len(records),counts=dict(counts),elapsed_s=time.monotonic()-start)));p.replace(OUT/'state.json')
        dest.create_dataset('labels',data=np.asarray(labels,np.float32));dest.attrs.update(schema='approved.curriculum.original-visual-cache.v1',actions_used=False,old_test_images_used=False)
    tmp.replace(OUT/'data.h5');roles={role:{e['world_seed']for e in sources if e['role']==role}for role in ['training','validation']};assert not roles['training']&roles['validation'];assert all(counts[role+':'+cls]>0 for role in roles for cls in ['positive','negative'])
    (OUT/'records.json').write_text(json.dumps(records));receipt=dict(status='passed_original_visual_derivatives',schema='approved.curriculum.original-visual-admission.v1',sources=sources,frames=len(records),counts=dict(counts),data_sha256=sha(OUT/'data.h5'),records_sha256=sha(OUT/'records.json'),masks_manifest_sha256=sha(ROOT/'original_masks/v1/manifest.json'),consumer_sha256=sha(ROOT/'visual_consumer_v1.py'),source_sha256=sha(__file__),split_world_disjoint=True,original_test_images_used=False,oracle_actions_used=False,whole_boat_identity_invented=False,elapsed_s=time.monotonic()-start,created_utc=dt.datetime.now(dt.timezone.utc).isoformat());(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2));(OUT/'state.json').write_text(json.dumps({k:v for k,v in receipt.items()if k!='sources'},indent=2));print(json.dumps({k:v for k,v in receipt.items()if k!='sources'}),flush=True)
if __name__=='__main__':main()
