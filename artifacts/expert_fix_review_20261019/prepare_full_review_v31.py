from pathlib import Path
import subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018'
s=(HERE/'queue_full_review_v28.py').read_text().replace('v28','v31')
s=s.replace("{'E06':'landed','E12':'home_landed'}","{'E01':'landed','E03':'landed'}")
s=s.replace("    hashes=json.loads", "    visual=json.loads((PILOT/'pilot_visual_review.json').read_text());assert visual['actual_camera_inspected'] and visual['accepted_for_expanded_review_only'] and not visual['training_eligible']\n    hashes=json.loads")
s=s.replace("order=['E10','E11','E03','E04','E01','E02','E05','E07','E08','E09']", "order=['E10','E11','E04','E05','E02','E06','E07','E08','E09','E12']")
s=s.replace("job=dict(inventory[name],instance=160+i)", "job=dict(inventory[name],instance=210+i,target_absent=name=='E12',original_mode=inventory[name]['prior_mode'])\n        # Primary requested videos are the EXPERT driving these situations.\n        # E09-E11 are explicit expert-only counterfactuals to old mixed flights,\n        # never represented as an observed learner rescue.\n        job['prior_mode']='expert'")
s=s.replace("E06_E12_reused_from='v31'", "E01_E03_reused_from='v31',E09_E10_E11_expert_only_counterfactuals=True")
s=s.replace("if job['prior_mode']=='dagger':args+=['--mode','dagger','--prefix']", "if job['prior_mode']=='dagger':args+=['--mode','dagger','--prefix']\n                if job.get('target_absent'):args+=['--target-absent']")
s=s.replace("if result['outcome']!='landed':", "if result['outcome']!=('home_landed' if task['name']=='E12' else 'landed'):")
compile(s,'queue_full_review_v31.py','exec');p=ROOT/'queue_full_review_v31.py';assert not p.exists();p.write_text(s)
s=(HERE/'launch_full_review_v28.py').read_text().replace('v28','v31');p=ROOT/'launch_full_review_v31.py';assert not p.exists();p.write_text(s)
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push','queue_full_review_v31.py','launch_full_review_v31.py'],check=True)
