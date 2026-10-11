"""Derive orientation/normal targets while verifying every consumed metadata row."""
import argparse,hashlib,json,pathlib,concurrent.futures,multiprocessing
import h5py,numpy as np
from .train import auxiliary_target
from .recording import numeric_observation
from .iterate_policy import verified_caches
from .gate import file_hash
from .collection_session import atomic_json


def prepare_one(job):
    cache,target_path=map(pathlib.Path,job)
    digest=hashlib.sha256()
    with h5py.File(cache,'r') as source:
        raw_path=pathlib.Path(source.attrs['source_path'])
        n=len(source['features']);targets=np.zeros((n,15),dtype='f4')
        with h5py.File(raw_path,'r') as raw:
            if len(raw['steps'])!=n or raw.attrs['role']!=source.attrs['role']:
                raise ValueError('Raw/cache row provenance mismatch')
            for start in range(0,n,256):
                encoded=raw['steps'][start:start+256];rows=[json.loads(r) for r in encoded]
                for r in encoded:digest.update(r if isinstance(r,bytes) else r.encode())
                numeric=np.array([numeric_observation(r) for r in rows])
                auxiliary=np.array([auxiliary_target(r) for r in rows])
                if not np.array_equal(numeric,source['numeric'][start:start+256]) or not np.array_equal(auxiliary,source['auxiliary'][start:start+256]):
                    raise ValueError('Recorded metadata changed from verified feature inputs: '+str(raw_path))
                for i,row in enumerate(rows,start):
                    p=row['privileged'];yaw=np.pi/2-row['observation']['px4']['attitude_ned_rad'][2]
                    c,s=np.cos(yaw),np.sin(yaw);R=np.array([[c,s,0],[-s,c,0],[0,0,1.]])
                    pad_R=np.asarray(p['pad_rotation'])
                    if not np.allclose(pad_R.T@pad_R,np.eye(3),atol=1e-6) or np.linalg.det(pad_R)<.99999:
                        raise ValueError('Invalid recorded pad orientation')
                    heading=np.arctan2(pad_R[1,0],pad_R[0,0])-yaw
                    normal=(R@pad_R[:,2])*[1,-1,-1]
                    aux=auxiliary[i-start]
                    targets[i]=np.r_[aux[0],aux[3:6]*10,aux[6:9]*2,np.sin(2*heading),np.cos(2*heading),normal,aux[1:3],aux[9]]
    target_path.parent.mkdir(parents=True,exist_ok=True)
    np.save(target_path,targets)
    return {'cache':str(cache),'target':str(target_path),'target_sha256':file_hash(target_path),'cache_sha256':file_hash(cache),'metadata_sha256':digest.hexdigest(),'source_path':str(raw_path),'role':str(source.attrs['role']) if False else None}


def main(args):
    out=pathlib.Path(args.output)
    if out.exists() and any(out.iterdir()):raise FileExistsError('New pose target directory required')
    out.mkdir(parents=True,exist_ok=True)
    _,checkpoint,splits,provenance=verified_caches(args.manifest,args.review,args.source_checkpoint,args.feature_cache,args.source_repo)
    jobs=[]
    roles={}
    for role,files in splits.items():
        for f in files:
            jobs.append((str(f),str(out/'targets'/(f.stem+'.npy'))));roles[str(f)]=role
    atomic_json(out/'progress.json',{'status':'running','completed':0,'total':len(jobs)})
    results=[]
    context=multiprocessing.get_context('spawn')
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=context) as pool:
        for result in pool.map(prepare_one,jobs,chunksize=1):
            result['role']=roles[result['cache']];results.append(result)
            if len(results)%20==0:
                atomic_json(out/'progress.json',{'status':'running','completed':len(results),'total':len(jobs)})
                print('POSE_TARGETS',len(results),len(jobs),flush=True)
    atomic_json(out/'manifest.json',{'schema':'aerodock.landing.pose_targets.v1','source_checkpoint_sha256':file_hash(args.source_checkpoint),'dataset_sha256':checkpoint['dataset_sha256'],'review_manifest_sha256':checkpoint['review_manifest_sha256'],'source_checkpoint':args.source_checkpoint,'entries':results,'consumption_note':'Every feature file checksum verified; each consumed raw numeric/auxiliary metadata row exactly matches the verified feature cache. Raw RGB is not consumed or rehashed.'})
    atomic_json(out/'progress.json',{'status':'completed','completed':len(results),'total':len(jobs)})
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ['manifest','review','source-checkpoint','feature-cache','source-repo','output']:parser.add_argument('--'+name,required=True)
    main(parser.parse_args())
