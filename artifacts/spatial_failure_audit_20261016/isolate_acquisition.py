"""Isolate the existing image-only centre head; fixed-observation replay only."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import copy,hashlib,json,math,shutil,sys,time
from pathlib import Path
import h5py,numpy as np,torch

BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
OLD=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
OUT=Path(__file__).resolve().parent
BUNDLE=OUT/'candidate_center_only'
sys.path.insert(0,str(BASE))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False))


def create():
    shutil.copytree(OLD/'candidate_bundle',BUNDLE)
    package=BUNDLE/'code/landing_training/radio_robust_20261015'
    shutil.copy2(OLD/'candidate_bundle_v4/acquisition.pt',BUNDLE/'acquisition.pt')
    shutil.copy2(OLD/'candidate_bundle_v4/code/landing_training/radio_robust_20261015/acquisition.py',package/'acquisition.py')
    path=package/'runtime.py';s=path.read_text()
    needle='        self.model.eval()';assert s.count(needle)==1
    s=s.replace(needle,needle+"\n        from .acquisition import AcquisitionHead\n        from pathlib import Path\n        saved_acquisition=torch.load(Path(checkpoint).with_name('acquisition.pt'),map_location=device,weights_only=False)\n        self.acquisition=AcquisitionHead().to(device)\n        self.acquisition.load_state_dict(saved_acquisition['model']);self.acquisition.eval()")
    needle='        prediction, _, self.hidden = self.model(image, numeric, self.hidden, uncertainty)';assert needle in s
    s=s.replace(needle,"        features=self.model.backbone.encode_images(image)\n        prediction,_,self.hidden=self.model.forward_features(features,numeric,self.hidden,uncertainty)\n        original_center=prediction[0,0,12:14].cpu().numpy().copy()\n        image_center=self.acquisition(features)[0,0,1:3]\n        metric_time=self.controller.metric_time\n        centre_override=metric_time is None or float(observation['image_delivery_time_s'])-metric_time>.5\n        if centre_override:\n            prediction=prediction.clone()\n            prediction[0,0,12:14]=image_center")
    needle='        return action, diagnostics';assert s.count(needle)==1
    s=s.replace(needle,"        diagnostics.update(center_only_override=centre_override,original_center_px=((original_center+1)*[320.,180.]).tolist(),image_only_center_px=((image_center.cpu().numpy()+1)*[320.,180.]).tolist())\n"+needle)
    path.write_text(s)
    config=json.loads((BUNDLE/'policy.json').read_text())
    config.update(runtime_revision='isolated_image_center_only_20261016',closed_loop_evaluated=False,
        closed_loop_results={},automatic_deployment=False,target_met_on_this_sample=False,reliability_qualified=False,
        acquisition_checkpoint='acquisition.pt',acquisition_checkpoint_sha256=sha(BUNDLE/'acquisition.pt'),
        experiment_notes='Only pre-lock image-centre predictions replaced by an existing v4 image-only head. Original visibility, pose/velocity predictions, propagation, gates, search and touchdown logic retained. No new training.',
        controller_changes=['Existing baseline controller retained; isolated image-centre substitution during acquisition only.'])
    config['file_hashes']={str(p.relative_to(BUNDLE)):sha(p) for p in (BUNDLE/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    config['file_hashes']['acquisition.pt']=sha(BUNDLE/'acquisition.pt')
    assert sha(BUNDLE/'pose.pt')==config['checkpoint_sha256']
    save(BUNDLE/'policy.json',config)
    save(OUT/'center_only_candidate.json',dict(bundle=str(BUNDLE),pose_weights_unchanged=True,new_training=False,
         baseline_checkpoint_sha256=sha(BUNDLE/'pose.pt'),existing_acquisition_sha256=sha(BUNDLE/'acquisition.pt'),
         closed_loop_evaluated=False,development_only=True,automatic_promotion=False))


def main():
    create();torch.set_num_threads(1)
    import landing_training
    landing_training.__path__.append(str(BUNDLE/'code/landing_training'))
    from landing_training import paths
    from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
    config=json.loads((BUNDLE/'policy.json').read_text())
    policy=RadioRobustRuntime(BUNDLE/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
    results=[]
    for source in sorted(OUT.glob('probe_*/observations.h5')):
        policy.reset();accepted=[];errors=[];rows=[];started=time.monotonic()
        with h5py.File(source,'r') as f:
            for i in range(len(f['steps'])):
                row=json.loads(f['steps'][i]);obs=copy.deepcopy(row['observation']);obs.pop('beacon',None)
                action,diag=policy.act(f['rgb'][i],obs)
                if diag['metric_valid']:
                    accepted.append(row['task_time_s'])
                    if 'estimated_relative_position' in diag:
                        yaw=math.pi/2-obs['px4']['attitude_ned_rad'][2];c,s=math.cos(yaw),math.sin(yaw)
                        R=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
                        p=row['privileged'];truth=np.diag([1.,-1.,-1.])@R.T@(np.array(p['pad_position_enu_m'])-p['drone_position_enu_m'])
                        errors.append(float(np.linalg.norm(truth-diag['estimated_relative_position'])))
                rows.append(dict(t=row['task_time_s'],diagnostics=diag,unexecuted_action=np.asarray(action).tolist()))
        baseline=json.loads((source.parent/'probe_result.json').read_text())
        result=dict(case=source.parent.name,frames=len(rows),first_metric_s=accepted[0] if accepted else None,
             metric_frames=len(accepted),position_error_median_m=float(np.median(errors)) if errors else None,
             position_error_p90_m=float(np.percentile(errors,90)) if errors else None,
             baseline_metric_frames=sum(r['output']['learner_diagnostics']['metric_valid'] for r in map(json.loads,(source.parent/'steps.jsonl').read_text().splitlines())),
             seconds=time.monotonic()-started,
             scope='Fixed original RGB/sensor sequence. Candidate actions are NOT executed; this is not closed-loop landing validation.')
        save(OUT/(source.parent.name+'_center_only_replay.json'),dict(summary=result,rows=rows))
        results.append(result);save(OUT/'center_only_replay_summary.json',dict(results=results,closed_loop_validated=False,new_training=False))
        print('ISOLATED_REPLAY',json.dumps(result),flush=True)


if __name__=='__main__':main()
