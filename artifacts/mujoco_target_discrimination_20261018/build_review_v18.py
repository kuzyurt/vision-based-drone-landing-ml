from pathlib import Path
root=Path(__file__).resolve().parent
p=root/'target_learning/protocol.py';s=p.read_text()
old="""        if chosen is not None:
            if chosen.age_s>.25:
                return self._intent('reorient_candidate','remembered_candidate_needs_fresh_visual_confirmation')
            if self.inspection_id!=chosen.track_id:"""
new="""        if chosen is not None:
            # Reorientation is part of inspection, not an escape from its
            # existing no-progress watchdog. Old measurements stay old.
            if self.inspection_id!=chosen.track_id:"""
assert old in s;s=s.replace(old,new)
s=s.replace("            if chosen.range_interval_m is not None:\n                distance=chosen.range_interval_m[1]", "            if chosen.age_s<=.25 and chosen.range_interval_m is not None:\n                distance=chosen.range_interval_m[1]")
old="""                self.rejected[chosen.track_id]=s.time_s;self.selected=None;self.inspection_id=None
                self.scan_seen.clear();self.scan_coverage=0.;self.scan_yaw=None
                return self._intent('scan','unresolved_candidate_no_observable_progress_cooldown',yaw=-.35)
            return self._intent('inspect_candidate'"""
new="""                self.rejected[chosen.track_id]=s.time_s
                self.cooldown_reasons[chosen.track_id]='unresolved_no_fresh_visual_progress'
                self.selected=None;self.inspection_id=None
                self.scan_seen.clear();self.scan_coverage=0.;self.scan_yaw=None
                return self._intent('scan','unresolved_candidate_no_observable_progress_cooldown',yaw=-.35)
            if chosen.age_s>.25:
                return self._intent('reorient_candidate','remembered_candidate_needs_fresh_visual_confirmation')
            return self._intent('inspect_candidate'"""
assert old in s;s=s.replace(old,new);p.write_text(s)
(root/'probe_expert_review_v18.py').write_text((root/'probe_expert_review_v14.py').read_text())
(root/'run_expert_review_v18.py').write_text((root/'run_expert_review_v15.py').read_text())
s=(root/'queue_v14.py').read_text().replace('v14','v18')
s=s.replace("'--instance','100'","'--instance','101'")
s=s.replace("        save(stage='expert_preview'", "        subprocess.run([sys.executable,str(ROOT/'package_review_v18.py')],cwd=ROOT,check=True,timeout=160)\n        save(stage='expert_preview'")
(root/'queue_v18.py').write_text(s)
(root/'launch_v18.py').write_text((root/'launch_v14.py').read_text().replace('v14','v18'))
(root/'package_review_v18.py').write_text((root/'package_review_v16.py').read_text().replace('v16','v18'))
(root/'wait_review_package_v18.py').write_text((root/'wait_review_package_v16.py').read_text().replace('v16','v18'))
(root/'download_review_v18_when_ready.py').write_text((root/'download_review_v16_when_ready.py').read_text().replace('v16','v18'))
