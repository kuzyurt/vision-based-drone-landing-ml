from pathlib import Path
import hashlib,json
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
cases={'E01':'expert_visible_native_v18','E02':'expert_visible_native_v15_hard','E03':'expert_visible_native_v16','E04':'expert_visible_native_v17',
 'E05':'expert_visible_native_v15_recovery','E06':'expert_visible_native_v13c','E07':'expert_visible_native_v13b','E08':'expert_visible_native_v14',
 'E09':'expert_visible_native_v19_near_deck','E10':'expert_visible_native_v19_near_deck_tilt','E11':'expert_visible_native_v21_tilt','E12':'task_harness_development_v1/full_home'}
rows=[]
for case,name in cases.items():
    ep=ROOT/name;scenario=ep/'scenario.json';r=json.loads((ep/'preview_result.json').read_text())
    rows.append(dict(case=case,source_episode=name,scenario_path=str(scenario),scenario_sha256=hashlib.sha256(scenario.read_bytes()).hexdigest(),scene=r.get('scene'),
        prior_mode=r.get('mode'),prefix=r.get('prefix'),fault=r.get('fault_setting'),prior_outcome=r.get('outcome')))
out=ROOT/'expert_fix_review_20261019/matched_case_inventory.json';assert not out.exists();out.write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
