"""Frozen deployed proposals and RGB crops from admitted perception data only."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib,importlib,json,time
import h5py,numpy as np,torch
from target_learning.expert_adapter_v22 import load_parent
from target_learning.discriminator_v5 import Discriminator,decode
from target_learning.object_verifier import regions
from target_learning.object_verifier_v12 import rgb_regions
from train_design_and_marker_v12 import design_labels,class_label,marker_label
from train_object_verifier_v8 import matched
ROOT=Path(__file__).resolve().parent
BUNDLE=ROOT.parent/'landing_hardening_20261018T011610Z/candidate_r15'
OUT=ROOT/'curriculum_v23/verifier_cache_v1'
PARENT=ROOT/'perception_training_v12_rgb_only/best.pt'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def save(p,value):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False));tmp.replace(p)

@torch.inference_mode()
def main():
    torch.set_num_threads(2);start=time.monotonic()
    manifest_path=ROOT/'curriculum_v23/perception_admission_v1/manifest.json'
    manifest=json.loads(manifest_path.read_text());assert manifest['status']=='completed'
    assert not manifest['heldout_used']and not manifest['tidewater_used']and not manifest['teacher_actions_used']
    assert sha(PARENT)=='c87dca7541d361b183ce45da5f7756bdc5a358aaf544fb2bc5c3fc08bad1e0e3'
    OUT.mkdir(exist_ok=False);rng=np.random.default_rng(2026101901)
    parent=load_parent(BUNDLE,'curriculum_verifier_features');config=json.loads((BUNDLE/'policy.json').read_text())
    runtime=parent.RadioRobustRuntime(BUNDLE/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
    spatial=importlib.import_module(parent.__package__+'.spatial_acquisition')
    saved=torch.load(PARENT,map_location='cuda',weights_only=False)
    detector=Discriminator().cuda();detector.load_state_dict(saved['model'],strict=True);detector.eval()
    receipts=[];parity=None
    for source in manifest['entries']:
        path=Path(source['path']);assert sha(path)==source['sha256']
        admission=json.loads((path.parent/'admission.json').read_text())
        assert admission==source and source['status']=='admitted_for_perception_only'
        assert not source['old_review_data_admitted']and not source['action_targets_admissible']
        role=source['role'];assert role in ['training','validation']
        dst=OUT/path.parent.name;dst.mkdir(exist_ok=False)
        chunks=[];metas=[];classes=[];markers=[];masks=[];frames=[]
        with h5py.File(path,'r')as h:
            assert h.attrs['schema']=='mujoco.perception_admitted.v1'and h.attrs['role']==role
            assert not h.attrs['teacher_actions']and not h.attrs['action_targets_admissible']
            for start_index in range(0,len(h['rgb']),8):
                raw=np.asarray(h['rgb'][start_index:start_index+8]);image=torch.from_numpy(raw).permute(0,3,1,2).cuda()
                fine,context=spatial.encode_spatial(runtime.model.backbone,image)
                predictions=decode({k:v.cpu()for k,v in detector(fine,context).items()},minimum_presence=.2,topk=24)
                for b,pred in enumerate(predictions):
                    frame=design_labels(json.loads(h['labels'][start_index+b]));assert frame['role']==role
                    assert frame['world_seed']==source['world_seed']
                    assert hashlib.sha256(raw[b].tobytes()).hexdigest()==frame['rgb_sha256']
                    proposals=list(pred)
                    if role=='training':
                        for inst in frame['instances']:
                            if inst['identity']==-2:continue
                            box=np.asarray(inst['bbox'],float);center=(box[:2]+box[2:])/2;size=box[2:]-box[:2]
                            for _ in range(2 if inst['identity']==1 else 1):
                                proposals.append(dict(pixel=(center+rng.uniform(-.08,.08,2)*size).tolist(),size_px=(size*rng.uniform(.9,1.15,2)).tolist()))
                    frames.append(dict(label=frame,predictions=pred))
                    if not proposals:continue
                    boxes=[[*p['pixel'],*p['size_px']]for p in proposals]
                    _,meta=regions(fine[b:b+1],context[b:b+1],boxes,[0]*len(boxes))
                    crops=rgb_regions(image[b:b+1],meta);chunks.append(crops.cpu().numpy());metas.append(meta.cpu().numpy())
                    if parity is None:
                        cpu=rgb_regions(image[b:b+1].cpu(),meta.cpu());error=float((cpu.float()-crops.cpu().float()).abs().max())
                        assert error<=.001;parity=dict(max_absolute_error=error,tolerance=.001,source_rgb_sha256=frame['rgb_sha256'])
                    for p in proposals:
                        j=matched(p,frame['instances']);inst=frame['instances'][j]if j is not None else None
                        classes.append(class_label(p,inst));markers.append(marker_label(p,inst,frame))
                        masks.append(inst is None or bool(inst.get('marker_head_loss_available',False)))
        assert chunks
        for name,array in [('rgb',np.concatenate(chunks)),('meta',np.concatenate(metas)),('classes',np.asarray(classes,np.int64)),
                           ('marker_labels',np.asarray(markers,np.float32)),('marker_mask',np.asarray(masks,bool))]:
            np.save(dst/(name+'.npy'),array)
        save(dst/'frames.json',frames)
        receipt=dict(path=str(dst),role=role,world_seed=source['world_seed'],regions=len(classes),frames=len(frames),
            source_admission_sha256=sha(path.parent/'admission.json'),source_image_sha256=source['sha256'],
            files={p.name:sha(p)for p in dst.iterdir()if p.is_file()},
            gt_augmented_crops=role=='training',validation_proposals_deployed_only=role=='validation',teacher_actions_used=False)
        save(dst/'receipt.json',receipt);receipts.append(receipt)
        save(OUT/'state.json',dict(stage='caching',closed_sources=len(receipts),wall_s=time.monotonic()-start))
    save(OUT/'manifest.json',dict(status='completed',entries=receipts,parent_sha256=sha(PARENT),
        admission_manifest_sha256=sha(manifest_path),source_sha256=sha(__file__),rgb_sampling_parity=parity,
        pose_sha256=sha(BUNDLE/'pose.pt'),spatial_sha256=sha(BUNDLE/'spatial_acquisition.pt'),
        heldout_used=False,tidewater_used=False,action_targets_used=False,wall_s=time.monotonic()-start))
    save(OUT/'state.json',dict(stage='completed',closed_sources=len(receipts),wall_s=time.monotonic()-start))
if __name__=='__main__':main()
