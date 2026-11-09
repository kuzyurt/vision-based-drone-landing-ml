"""Export selected spatial perception onto the preserved R2 controller."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    training=ROOT/'spatial_acquisition_training';result=json.loads((training/'result.json').read_text())
    assert result['status']=='completed' and not result['test_images_used']
    bundle=ROOT/'bundle_spatial_r3';shutil.copytree(ROOT/'bundle_view_r2b',bundle)
    package=bundle/'code/landing_training/radio_robust_20261015'
    shutil.copy2(ROOT/'spatial_acquisition.py',package/'spatial_acquisition.py')
    shutil.copy2(training/'best.pt',bundle/'spatial_acquisition.pt')
    path=package/'runtime.py';s=path.read_text()
    start=s.index('        from .acquisition import AcquisitionHead');end=s.index('        self.controller =',start)
    s=s[:start]+'''        from .spatial_acquisition import SpatialAcquisition,decode_spatial
        from pathlib import Path
        spatial=torch.load(Path(checkpoint).with_name('spatial_acquisition.pt'),map_location=device,weights_only=False)
        self.acquisition=SpatialAcquisition().to(device)
        self.acquisition.load_state_dict(spatial['model']);self.acquisition.eval()
        self.decode_spatial=decode_spatial;self._spatial_maps={}
        self._fine_hook=self.model.backbone.encoder[3].register_forward_hook(lambda module,args,value:self._spatial_maps.__setitem__('fine',value))
        self._context_hook=self.model.backbone.encoder[8].register_forward_hook(lambda module,args,value:self._spatial_maps.__setitem__('context',value))
'''+s[end:]
    needle='        acquisition_prediction=self.acquisition(features)[0,0]\n        image_center=acquisition_prediction[1:3]';assert needle in s
    s=s.replace(needle,'''        spatial_output=self.acquisition(self._spatial_maps['fine'],self._spatial_maps['context'])
        spatial_presence,spatial_pixel=self.decode_spatial(spatial_output)
        image_center=spatial_pixel[0]/spatial_pixel.new_tensor([320.,180.])-1.
        acquisition_prediction=torch.cat((spatial_presence[:1],image_center))''')
    path.write_text(s)
    config=json.loads((bundle/'policy.json').read_text())
    config.update(runtime_revision='spatial_acquisition_r3_20261016',closed_loop_evaluated=False,closed_loop_results={},
        spatial_checkpoint='spatial_acquisition.pt',spatial_checkpoint_sha256=sha(bundle/'spatial_acquisition.pt'),
        spatial_training=result,automatic_deployment=False,reliability_qualified=False)
    config['controller_changes']+=['spatial image-only heatmap/offset/presence head reuses frozen encoder intermediate maps; existing RGB training/validation only']
    config['file_hashes']={str(p.relative_to(bundle)):sha(p) for p in (bundle/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    config['file_hashes']['spatial_acquisition.pt']=sha(bundle/'spatial_acquisition.pt')
    assert sha(bundle/'pose.pt')==config['checkpoint_sha256']
    (bundle/'policy.json').write_text(json.dumps(config,indent=2))
    print(json.dumps(dict(bundle=str(bundle),spatial_validation=result['validation'],pose_weights_unchanged=True)),flush=True)


if __name__=='__main__':main()
