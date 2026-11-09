from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'run_expert_review_v16.py').read_text()
s=s.replace("choices=['none','gimbal_pan']","choices=['none','gimbal_pan','gimbal_tilt']")
old="    fault=CameraFault(dict(kind='gimbal_pan',trigger_clearance_m=.65,duration_s=1.2,pan_rate_rad_s=.6981317008) if a.fault!='none' else {})"
new='''    class PhysicalTiltFault(CameraFault):
        def after(self,action,diag,observation):
            action,diag=super().after(action,diag,observation)
            if self.active and self.setting.get('kind')=='gimbal_tilt':
                action=np.asarray(action,dtype=float).copy();diag['fault_original_action']=action.tolist()
                action[4]=0.;action[5]=-.6981317008
            return action,diag
    fault=PhysicalTiltFault(dict(kind=a.fault,trigger_clearance_m=.65,duration_s=1.6 if a.fault=='gimbal_tilt' else 1.2,pan_rate_rad_s=.6981317008) if a.fault!='none' else {})'''
assert old in s;s=s.replace(old,new)
(root/'run_expert_review_v17.py').write_text(s)
s=(root/'queue_v16.py').read_text().replace('v16','v17')
s=s.replace("'--fault','gimbal_pan'],900,","'--fault','gimbal_tilt'],1100,")
(root/'queue_v17.py').write_text(s)
(root/'launch_v17.py').write_text((root/'launch_v16.py').read_text().replace('v16','v17'))
(root/'package_review_v17.py').write_text((root/'package_review_v16.py').read_text().replace('v16','v17'))
(root/'wait_review_package_v17.py').write_text((root/'wait_review_package_v16.py').read_text().replace('v16','v17').replace('>1000','>1250'))
s=(root/'download_review_v16_when_ready.py').read_text().replace('v16','v17').replace('timeout=1050','timeout=1300')
(root/'download_review_v17_when_ready.py').write_text(s)
