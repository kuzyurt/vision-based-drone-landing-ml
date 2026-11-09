"""Preserved R5 plus measured horizon and close-plane registration corrections."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    b=ROOT/'bundle_spatial_r6';shutil.copytree(ROOT/'bundle_spatial_r5',b);package=b/'code/landing_training/radio_robust_20261015'
    shutil.copy2(ROOT/'normal_refinement.py',package/'normal_refinement.py')
    p=package/'native_marker.py';s=p.read_text();needle='        return fast(rgb,observation,calibration,estimate,kernel)';assert s.count(needle)==1
    s=s.replace(needle,"        from .normal_refinement import fit_with_normal_refinement\n        return fit_with_normal_refinement(rgb,observation,calibration,estimate,kernel,fast)");p.write_text(s)
    p=package/'controller/observable_acquisition.py';s=p.read_text()
    needle="    history=False;rejected=False;world=None";assert s.count(needle)==1
    s=s.replace(needle,"""    horizon_ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.])
    horizon_ray/=max(np.linalg.norm(horizon_ray),1e-9)
    horizon_rejected=bool(valid and horizon_ray[2]<=.02)
    if horizon_rejected:valid=False
"""+needle)
    s=s.replace('tentative_camera_attention=tentative)','tentative_camera_attention=tentative,horizon_target_rejected=horizon_rejected)');p.write_text(s)
    p=package/'controller/marker_policy.py';s=p.read_text()
    needle='        self.metric_heading_world = None';assert s.count(needle)==2
    s=s.replace(needle,needle+'\n        self.refined_normal_world = None')
    needle="        pose_at_capture['_tracked'] = metric_recent";assert s.count(needle)==1
    s=s.replace(needle,needle+"\n        if metric_recent and self.refined_normal_world is not None:\n            pose_at_capture['normal']=D@Rc.T@self.refined_normal_world")
    needle='                self.metric_time = now';assert s.count(needle)==1
    s=s.replace(needle,needle+"\n                if 'refined_normal_heading' in fit:\n                    self.refined_normal_world=Rc@D@np.asarray(fit['refined_normal_heading'])\n                if self.refined_normal_world is not None:\n                    current['normal']=D@R.T@self.refined_normal_world")
    needle="        if fit is not None:\n            diag.update(marker_orientation_correction_deg=";assert s.count(needle)==1
    s=s.replace(needle,"        if fit is not None and 'refined_normal_heading' in fit:\n            diag.update(normal_refinement_source=fit['normal_refinement_source'])\n"+needle)
    compile(s,str(p),'exec');p.write_text(s)
    c=json.loads((b/'policy.json').read_text());c.update(runtime_revision='rgb_plane_horizon_r6_20261017',closed_loop_evaluated=False,closed_loop_results={})
    c['controller_changes']+=['reject above-horizon coarse targets before locking camera or authorizing movement',
        'refine close plane normal from RGB only after original fixed-normal fit fails; all original registration and physical landing gates retained']
    c['file_hashes']={str(p.relative_to(b)):sha(p) for p in (b/'code').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for f in ['pose.pt','acquisition.pt','spatial_acquisition.pt']:c['file_hashes'][f]=sha(b/f)
    (b/'policy.json').write_text(json.dumps(c,indent=2));print(json.dumps(dict(bundle=str(b),pose_weights_unchanged=sha(b/'pose.pt')==sha(ROOT/'bundle_spatial_r3/pose.pt'))))
if __name__=='__main__':main()
