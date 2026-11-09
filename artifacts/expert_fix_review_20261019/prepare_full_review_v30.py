from pathlib import Path
import subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018'
s=(HERE/'queue_full_review_v28.py').read_text().replace("PILOT=ROOT/'expert_fix_review_20261019/v28'","PILOT=ROOT/'expert_fix_review_20261019/v30'").replace("OUT=ROOT/'expert_fix_review_20261019/v28_full'","OUT=ROOT/'expert_fix_review_20261019/v30_full'")
s=s.replace("{'E06':'landed','E12':'home_landed'}","{'E01':'landed','E03':'landed','E10':'landed','E12':'home_landed'}")
s=s.replace('expert_adapter_v28.py','expert_adapter_v30.py').replace('expert_fix_review_20261019/v28/runtime_probe.json','expert_fix_review_20261019/v30/runtime_probe.json').replace('run_matched_expert_review_v28.py','run_matched_expert_review_v30.py').replace('expert_fix_review_20261019/v28_full/','expert_fix_review_20261019/v30_full/')
s=s.replace("order=['E10','E11','E03','E04','E01','E02','E05','E07','E08','E09']","order=['E11','E04','E02','E05','E06','E07','E08','E09']")
s=s.replace("    (OUT/'plan.json').write_text", "    pending.append(dict(inventory['E09'],case='E09_teacher',source_case='E09',prior_mode='expert',prefix=False,instance=170))\n    (OUT/'plan.json').write_text")
s=s.replace("E06_E12_reused_from='v28'","E01_E03_E10_E12_reused_from='v30'")
s=s.replace("active.append(dict(p=child,name=name,start=time.monotonic(),log=log))","active.append(dict(p=child,name=name,start=time.monotonic(),log=log))")
compile(s,'queue_full_review_v30.py','exec');p=ROOT/'queue_full_review_v30.py';assert not p.exists();p.write_text(s)
s=(HERE/'launch_full_review_v28.py').read_text().replace('expert_fix_review_20261019/v28_full','expert_fix_review_20261019/v30_full').replace('queue_full_review_v28.py','queue_full_review_v30.py')
p=ROOT/'launch_full_review_v30.py';assert not p.exists();p.write_text(s)
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push','queue_full_review_v30.py','launch_full_review_v30.py'],check=True)
