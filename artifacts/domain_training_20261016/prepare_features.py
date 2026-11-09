"""Cache new frozen-encoder features as completed episodes arrive."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import hashlib
import json
from pathlib import Path
import sys
import time
import h5py
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE));import landing_training
landing_training.__path__.append(str(ROOT/'policy_bundle/code/landing_training'))
from landing_training.radio_robust_20261015.model import RadioRobustPoseModel
from landing_training.recording import numeric_observation
from landing_training.train import auxiliary_target
from landing_training.gate import file_hash
from collect_domain import save

def main():
    torch.set_num_threads(1);source=ROOT/'policy_bundle/pose.pt'
    state=torch.load(source,map_location='cpu',weights_only=False)
    model=RadioRobustPoseModel().cuda();model.load_state_dict(state['model']);model.eval()
    legacy=torch.load(BASE/'landing_training/outputs/control_iteration_20261010T220632Z/pose_training/best.pt',map_location='cpu',weights_only=False)
    assert all(torch.equal(v,legacy['model'][k]) for k,v in state['model'].items() if k.startswith('backbone.encoder.'))
    out=ROOT/'features';out.mkdir(exist_ok=True);entries={};began=time.monotonic()
    while True:
        manifest=ROOT/'dataset/manifest.json'
        if manifest.exists():
            episodes=json.loads(manifest.read_text())['episodes']
            for e in episodes:
                if e['role']=='test' or e['name'] in entries:continue
                raw=ROOT/'dataset'/e['path'];cache=out/(e['name']+'.h5');target_file=out/(e['name']+'.npy')
                if file_hash(raw)!=e['sha256']:raise ValueError('New recording checksum mismatch')
                with h5py.File(raw) as data,h5py.File(cache,'w') as dst:
                    assert data.attrs['training_eligible'] and data.attrs['role']==e['role']
                    n=len(data['rgb']);targets=np.empty((n,15),dtype='f4');numeric=np.empty((n,32),dtype='f4');auxiliary=np.empty((n,10),dtype='f4')
                    features=dst.create_dataset('features',(n,1728),dtype='f4',chunks=(min(64,n),1728),compression='lzf')
                    for start in range(0,n,32):
                        stop=min(n,start+32);rows=[json.loads(r) for r in data['steps'][start:stop]]
                        images=torch.from_numpy(np.array(data['rgb'][start:stop])).permute(0,3,1,2)[None].cuda()
                        with torch.inference_mode():features[start:stop]=model.backbone.encode_images(images)[0].cpu().numpy()
                        for i,row in enumerate(rows,start):
                            numeric[i]=numeric_observation(row);auxiliary[i]=auxiliary_target(row)
                            p=row['privileged'];yaw=np.pi/2-row['observation']['px4']['attitude_ned_rad'][2]
                            c,s=np.cos(yaw),np.sin(yaw);R=np.array([[c,s,0],[-s,c,0],[0,0,1.]])
                            pad=np.asarray(p['pad_rotation']);angle=np.arctan2(pad[1,0],pad[0,0])-yaw
                            targets[i]=np.r_[auxiliary[i,0],auxiliary[i,3:6]*10,auxiliary[i,6:9]*2,np.sin(2*angle),np.cos(2*angle),(R@pad[:,2])*[1,-1,-1],auxiliary[i,1:3],auxiliary[i,9]]
                    dst.create_dataset('numeric',data=numeric);dst.create_dataset('auxiliary',data=auxiliary)
                    dst.attrs.update(source_path=str(raw),source_sha256=e['sha256'],role=e['role'],encoder_checkpoint_sha256=file_hash(source))
                np.save(target_file,targets)
                entries[e['name']]=dict(cache=str(cache),target=str(target_file),role=e['role'],source_path=str(raw),
                                         cache_sha256=file_hash(cache),target_sha256=file_hash(target_file),records=n)
                save(out/'manifest.json',dict(entries=list(entries.values()),source_checkpoint_sha256=file_hash(source),test_images_used=False))
                save(ROOT/'feature_progress.json',dict(status='running',completed=len(entries),frames=sum(x['records'] for x in entries.values()),elapsed_s=time.monotonic()-began))
                print('FEATURED',e['name'],n,flush=True)
            if (ROOT/'collection_result.json').exists():
                expected=[e for e in episodes if e['role']!='test']
                if len(expected)==len(entries):break
        time.sleep(10)
    save(ROOT/'feature_result.json',dict(status='completed',episodes=len(entries),frames=sum(x['records'] for x in entries.values()),elapsed_s=time.monotonic()-began))

if __name__=='__main__':main()
