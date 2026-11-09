"""Separate acquisition-head bundle, preserving every earlier candidate."""
from pathlib import Path
import json,sys,shutil
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE));from landing_training.gate import file_hash
from collect_domain import save

def main():
    import torch
    bundle=ROOT/'candidate_bundle_v4';shutil.copytree(ROOT/'candidate_bundle_v2',bundle)
    shutil.copy2(ROOT/'boat_acquisition_training/best.pt',bundle/'acquisition.pt')
    package=bundle/'code/landing_training/radio_robust_20261015'
    source=(ROOT/'train_acquisition.py').read_text();start=source.index('class AcquisitionHead');stop=source.index('\ndef load(',start)
    (package/'acquisition.py').write_text('import torch\nfrom torch import nn\n'+source[start:stop])
    path=package/'runtime.py';source=path.read_text()
    needle='        self.model.eval()';assert needle in source
    source=source.replace(needle,needle+"\n        from .acquisition import AcquisitionHead\n        from pathlib import Path\n        acquisition=torch.load(Path(checkpoint).with_name('acquisition.pt'),map_location=device,weights_only=False)\n        self.acquisition=AcquisitionHead().to(device)\n        self.acquisition.load_state_dict(acquisition['model'],strict=True);self.acquisition.eval()")
    needle='        prediction, _, self.hidden = self.model(image, numeric, self.hidden, uncertainty)';assert needle in source
    source=source.replace(needle,"        features=self.model.backbone.encode_images(image)\n        prediction, _, self.hidden = self.model.forward_features(features,numeric,self.hidden,uncertainty)\n        image_prediction=self.acquisition(features)\n        metric_time=self.controller.metric_time\n        acquisition_active=metric_time is None or float(observation['image_delivery_time_s'])-metric_time>.5\n        if acquisition_active:\n            prediction=prediction.clone()\n            prediction[...,0]=image_prediction[...,0]\n            prediction[...,12:14]=image_prediction[...,1:3]")
    needle='        return action, diagnostics';assert needle in source
    source=source.replace(needle,"        diagnostics.update(acquisition_head_active=acquisition_active,acquisition_head_visibility=float(image_prediction[0,0,0].sigmoid().cpu()),acquisition_head_center_px=((image_prediction[0,0,1:3].cpu().numpy()+1)*[320.,180.]).tolist())\n"+needle)
    path.write_text(source)
    config=json.loads((bundle/'policy.json').read_text())
    config.update(runtime_revision='boat_visibility_acquisition_v4_20261016',closed_loop_evaluated=False,closed_loop_results={},
         target_met_on_this_sample=False,reliability_qualified=False,acquisition_checkpoint='acquisition.pt',
         acquisition_checkpoint_sha256=file_hash(bundle/'acquisition.pt'),
         acquisition_training=json.loads((ROOT/'boat_acquisition_training_result.json').read_text()),
         interface_notes='Acquisition head takes only shared frozen RGB spatial features, without telemetry or recurrent state. Main pose/controller unchanged after continuous metric lock.')
    config['acquisition_visibility_target']='Boat visible even if marker occluded; positives require actual RGB cyan paint and white hull around teacher-projected boat in training data. No runtime truth or segmentation.'
    config['controller_changes']+=['Separate image-only acquisition visibility/pixel head trained on balanced existing off-centre and negative training frames, selected only on validation']
    config['file_hashes']={str(p.relative_to(bundle)):file_hash(p) for p in (bundle/'code').rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    config['file_hashes']['acquisition.pt']=file_hash(bundle/'acquisition.pt');save(bundle/'policy.json',config)
    assert file_hash(bundle/'pose.pt')==file_hash(ROOT/'candidate_bundle/pose.pt')
    print('V4_EXPORTED',config['acquisition_checkpoint_sha256'],flush=True)

if __name__=='__main__':main()
