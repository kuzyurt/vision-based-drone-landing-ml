"""Versioned original-data masks. No writes to H5 and no original test read."""
from pathlib import Path
import collections,concurrent.futures,datetime as dt,hashlib,json,os,time
import h5py,numpy as np
ROOT=Path(__file__).resolve().parent;DATA=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/datasets/expert');OUT=ROOT/'original_masks/v1'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb')as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def process(e):
    path=DATA/e['path'];before=(path.stat().st_size,path.stat().st_mtime_ns)
    digest=sha(path);assert digest==e['sha256'],'Original source differs from approved manifest: '+e['path']
    with h5py.File(path,'r')as h:
        assert str(h.attrs['training_eligible'])in ['True','true','1'] and str(h.attrs['role'])==e['role']
        rows=[json.loads(x)for x in h['steps']];assert len(rows)==len(h['rgb'])
        bytime={round(float(r['time_s'])*1e6):i for i,r in enumerate(rows)}
        captures=np.full(len(rows),-1,np.int32);center=np.zeros((len(rows),2),np.float32);corners=np.zeros((len(rows),5,2),np.float32)
        cm=np.zeros(len(rows),bool);pm=np.zeros(len(rows),bool);valid=np.zeros(len(rows),bool);reason=collections.Counter();unique=set()
        phases=collections.Counter()
        for i,r in enumerate(rows):
            phase=str(r.get('phase',''));phases[phase]+=1;o=r['observation']
            if any(x in phase.lower()for x in ['return_home','land_home','home_land'])or r.get('terminal'):
                reason['home_or_terminal']+=1;continue
            if not o.get('image_valid'):
                reason['invalid_image']+=1;continue
            t=float(o['image_capture_time_s']);j=bytime.get(round(t*1e6))
            if j is None or abs(float(rows[j]['time_s'])-t)>1e-6:
                reason['capture_label_unmatched']+=1;continue
            captures[i]=j;valid[i]=True
            if j in unique:reason['repeated_capture']+=1;continue
            unique.add(j);p=rows[j].get('privileged',{});kp=np.asarray(p.get('pad_keypoints_px',[]),float)
            if kp.shape!=(5,2)or not np.isfinite(kp).all()or not p.get('pad_visible'):
                reason['marker_unobservable_or_invalid']+=1;continue
            inside=(kp[:,0]>=0)&(kp[:,0]<640)&(kp[:,1]>=0)&(kp[:,1]<360)
            if inside[0]:cm[i]=True;center[i]=kp[0];corners[i]=kp;pm[i]=bool(inside.all())
            else:reason['marker_center_outside']+=1
        out=OUT/(e['name']+'.npz')
        np.savez_compressed(out,capture_row=captures,center_px=center,keypoints_px=corners,center_candidate=cm,full_pose_candidate=pm,valid_capture=valid,action_loss=np.zeros(len(rows),bool),boat_identity_loss=np.zeros(len(rows),bool))
    assert before==(path.stat().st_size,path.stat().st_mtime_ns),'Source changed during derivative'
    return dict(name=e['name'],path=e['path'],role=e['role'],world_seed=e['world_seed'],path_seed=e['path_seed'],source_sha256=digest,mask_path=str(out.relative_to(ROOT)),mask_sha256=sha(out),rows=len(rows),center_candidates=int(cm.sum()),full_pose_candidates=int(pm.sum()),valid_captures=int(valid.sum()),action_supervision_rows=0,boat_design_rows=0,reasons=dict(reason),phases=dict(phases),final_admission=False,rgb_marker_support_verification_required=True)
def main():
    OUT.mkdir(parents=True,exist_ok=False);start=time.monotonic();manifest=json.loads((DATA/'manifest.json').read_text());entries=manifest['episodes'];allowed=[e for e in entries if e['role']in ['training','validation']]
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=2)as pool:
        for row in pool.map(process,allowed,chunksize=1):
            results.append(row)
            if len(results)%40==0:
                p=OUT/'state.json.tmp';p.write_text(json.dumps(dict(status='running',done=len(results),total=len(allowed),elapsed_s=time.monotonic()-start)));p.replace(OUT/'state.json')
    report=dict(schema='approved.curriculum.original-masks.v1',status='metadata_masks_completed_rgb_admission_pending',created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),original_manifest_sha256=sha(DATA/'manifest.json'),original_episodes=len(entries),processed=len(results),original_test_episodes_untouched=sum(e['role']=='test'for e in entries),elapsed_s=time.monotonic()-start,episodes=results,action_targets_used=False,identity_targets_used=False,reason_action_mask='Original oracle/beacon expert actions are not observation-only teacher targets; current hybrid trains perception only.',note='Exact delayed capture labels are rejoined. Mask candidate is not final RGB admission. Valid disturbed perception images remain eligible if actual RGB support checks pass.')
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2));(OUT/'state.json').write_text(json.dumps({k:v for k,v in report.items()if k!='episodes'},indent=2));print(json.dumps({k:v for k,v in report.items()if k!='episodes'}),flush=True)
if __name__=='__main__':main()
