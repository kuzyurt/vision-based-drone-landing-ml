import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,time,hashlib
import h5py,numpy as np,torch
from target_learning.object_verifier_v12 import rgb_regions
from train_discriminator_v4 import save,sha
ROOT=Path(__file__).resolve().parent

def main():
 torch.set_num_threads(2);begin=time.monotonic();out=ROOT/'perception_rgb_cache_v12';out.mkdir(exist_ok=False)
 sources={};manifests={}
 for dataset in ['perception_dataset_v2','perception_paired_dataset_v9']:
  path=ROOT/dataset/'manifest.json';manifest=json.loads(path.read_text());manifests[dataset]=sha(path)
  for e in manifest['entries']:
   if e['role']in['training','validation']:
    assert e['world_seed']not in sources
    sources[e['world_seed']]=e
 receipts={};handles={};parity=None
 try:
  for role in ['training','validation']:
   parent=ROOT/'perception_training_v9';frames=json.loads((parent/(role+'_frames.json')).read_text());meta=np.load(parent/(role+'_meta.npy'),mmap_mode='r')
   dest=out/(role+'_rgb.npy');images=np.lib.format.open_memmap(dest,mode='w+',dtype=np.float16,shape=(len(meta),3,96,96));at=0;lineage=[]
   for f in frames:
    label=f['label'];e=sources[label['world_seed']];assert e['role']==role
    path=e['path']
    if path not in handles:handles[path]=h5py.File(path,'r')
    rgb=np.asarray(handles[path]['rgb'][label['index']]);n=len(f['predictions'])
    if role=='training':n+=sum(2 if i['identity']==1 else 1 for i in label['instances'])
    if n:
     metadata=torch.tensor(np.array(meta[at:at+n]),device='cuda');image=torch.tensor(rgb,device='cuda').permute(2,0,1)[None]
     cropped=rgb_regions(image,metadata);images[at:at+n]=cropped.cpu().numpy()
     if parity is None:
      cpu=rgb_regions(image.cpu(),metadata.cpu());error=float((cropped.cpu().float()-cpu.float()).abs().max())
      assert error<=.001,'CPU/GPU RGB sampling mismatch';parity=dict(max_absolute_error=error,tolerance=.001,actual_image_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),regions=n)
    lineage.append(dict(source=path,world_seed=label['world_seed'],index=label['index'],roi_start=at,roi_count=n,rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest()));at+=n
   assert at==len(meta);images.flush();save(out/(role+'_lineage.json'),lineage)
   receipts[role]=dict(regions=at,frames=len(frames),rgb_cache_sha256=sha(dest),metadata_sha256=sha(parent/(role+'_meta.npy')),lineage_sha256=sha(out/(role+'_lineage.json')))
   save(out/'state.json',dict(stage=role,wall_s=time.monotonic()-begin,receipts=receipts))
 finally:
  for h in handles.values():h.close()
 save(out/'receipt.json',dict(status='completed',wall_s=time.monotonic()-begin,roles=receipts,manifests=manifests,sampling_parity=parity,source_sha256=sha(__file__),sampling_source_sha256=sha(ROOT/'target_learning/object_verifier_v12.py'),heldout_used=False,tidewater_used=False,new_images=False))
 print(json.dumps(dict(status='completed',wall_s=time.monotonic()-begin,roles=receipts,sampling_parity=parity)),flush=True)
if __name__=='__main__':main()
