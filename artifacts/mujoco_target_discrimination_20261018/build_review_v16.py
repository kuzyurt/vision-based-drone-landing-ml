from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'run_expert_review_v15.py').read_text()
assert "trigger_clearance_m=.65,duration_s=.75" in s
s=s.replace("trigger_clearance_m=.65,duration_s=.75","trigger_clearance_m=.65,duration_s=1.2")
(root/'run_expert_review_v16.py').write_text(s)
s=(root/'queue_v14.py').read_text().replace('v14','v16')
begin=s.index("        run('expert_runtime_probe_v16_r15'")
end=s.index("        run('expert_visible_native_v16'",begin)
s=s[:begin]+'''        # No new actor or weights: exact passed V14 dependency hashes required.
        gate=json.loads((ROOT/'expert_runtime_probe_v14_r15.json').read_text())
        for name,digest in gate['actor_package_source_hashes'].items():
            assert hashlib.sha256((snapshot/'target_learning'/name).read_bytes()).hexdigest()==digest
'''+s[end:]
s=s.replace("ROOT/'probe_expert_review_v16.py',",'')
s=s.replace("'--duration','120'],900,","'--duration','120','--scene','hard','--pan','140','--fault','gimbal_pan'],900,")
s=s.replace("EXPERT_RUNTIME_GATE='expert_runtime_probe_v16_r15.json'","EXPERT_RUNTIME_GATE='expert_runtime_probe_v14_r15.json'")
s=s.replace("        save(stage='expert_preview'", "        subprocess.run([sys.executable,str(ROOT/'package_review_v16.py')],cwd=ROOT,check=True,timeout=160)\n        save(stage='expert_preview'")
(root/'queue_v16.py').write_text(s)
(root/'launch_v16.py').write_text((root/'launch_v14.py').read_text().replace('v14','v16'))
(root/'package_review_v16.py').write_text((root/'package_review_v15_hard.py').read_text().replace('v15_hard','v16'))
