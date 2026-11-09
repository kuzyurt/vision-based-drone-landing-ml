from pathlib import Path
import datetime,hashlib,json,shutil
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
QUAL=BASE/'landing_training/outputs/observable_policy_20261016T203932Z'
SWEEP=BASE/'landing_training/outputs/radio_accuracy_sweep_20261017T143452Z'
ROOT=BASE/'landing_training/outputs'/('vision_first_fusion_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
ROOT.mkdir();shutil.copytree(QUAL/'bundle_spatial_r8',ROOT/'candidate')
for name in ['mission_safety_r8.py','mission_integration.py','mission_setup.py']:shutil.copy2(QUAL/name,ROOT/name)
shutil.copy2(SWEEP/'evaluate_radio_sweep.py',ROOT/'evaluate_radio_sweep.py')
source=json.loads((SWEEP/'sweep_plan.json').read_text())
names=['wrong_bias_5m_east','wrong_bias_20m_east','gaussian_sigma_0p25','no_radio']
jobs=[next(j for j in source['cases'] if j['source_case']==name) for name in names]
for j in jobs:j['record_rgb']=j['source_case'].startswith('wrong_bias_');j['role']='radio_fusion_development'
(ROOT/'repeat_plan.json').write_text(json.dumps(dict(cases=jobs,comparison_to=str(SWEEP),note='Exactly the prior scenario, injection distributions, fixed offsets and seeds; no new qualification claim.'),indent=2))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline={str(p.relative_to(QUAL/'bundle_spatial_r8')):sha(p) for p in (QUAL/'bundle_spatial_r8').rglob('*') if p.is_file()}
(ROOT/'parent_files_sha256.json').write_text(json.dumps(baseline,indent=2))
(ROOT/'experiment_plan.json').write_text(json.dumps(dict(goal='Both previous falsely-confident 5m/20m-offset flights physically land on boat, preserving nominal/no-radio checks and strict physical touchdown/disarm.',
    parent=str(QUAL/'bundle_spatial_r8'),source_checkpoint_sha256=sha(QUAL/'bundle_spatial_r8/pose.pt'),training='Only new fusion head; all inherited vision/telemetry/recurrent weights frozen.',
    dataset='Same 1080 training +140 validation episodes; unchanged images/features/labels, causal synthetic packet streams from recorded motion; no evaluation images.',
    controller='No direct radio steering, motion feedforward, camera aiming or visual acquisition veto. Gated radio may influence neural pose only.',
    evaluation=['wrong_bias_5m_east','wrong_bias_20m_east','gaussian_sigma_0p25','no_radio'],workers=4,originals_preserved=True),indent=2))
print(str(ROOT))
