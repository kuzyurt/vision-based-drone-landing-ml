from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'target_learning/expert_adapter_v21.py').read_text()
s=s.replace('from .tracks import TrackBank','from .tracks import TrackBank\nfrom .local_downlook_v22 import camera_only_downlook')
needle="            action[2]=min(action[2],0.)\n        elif intent.phase=='ground_hold':"
assert needle in s
s=s.replace(needle,"""            action[2]=min(action[2],0.)
            # Apply in BOTH active-native-recovery and camera-only paths. V21
            # incorrectly placed this correction only in the inactive path.
            aim_memory=self.runtime.controller.visual_memory.estimate(o)
            action,downlook_applied=camera_only_downlook(action,o,aim_memory,intent.look_down)
            if downlook_applied:diag['expert_expired_memory_downlook']=True
        elif intent.phase=='ground_hold':""")
(root/'target_learning/expert_adapter_v22.py').write_text(s)
s=(root/'run_annotated_development_v21.py').read_text().replace('from target_learning.expert_adapter_v21 import','from target_learning.expert_adapter_v22 import')
s=s.replace("            elapsed=float(m['elapsed_s'])", "            elapsed=float(m['elapsed_s'])\n            if a.tilt_fault and diag.get('mission_fallback_active'):\n                progress['diagnostic_stop_reason']='development_boat_recovery_failed_mission_fallback';cancel.set()")
(root/'run_annotated_development_v22.py').write_text(s)
s=(root/'probe_expert_v21.py').read_text().replace('from target_learning.expert_adapter_v21 import','from target_learning.expert_adapter_v22 import')
(root/'probe_expert_v22.py').write_text(s)
s=(root/'queue_v21.py').read_text().replace('v21','v22')
s=s.replace("jobs=[dict(case='terminal',fault=False,instance=100),dict(case='tilt',fault=True,instance=101)]", "jobs=[dict(case='tilt',fault=True,instance=100)]")
s=s.replace("[ROOT/'check_struggle_v22.py',", "[ROOT/'check_struggle_v22.py',")
(root/'queue_v22.py').write_text(s)
(root/'check_struggle_v22.py').write_text((root/'check_struggle_v21.py').read_text()+'''
import numpy as np,math
from target_learning.local_downlook_v22 import camera_only_downlook
for memory in [None,dict(local_aim_valid=False,measurement_age_s=8.)]:
    for native_active in [True,False]:
        command=np.array([.3,-.1,-.4 if native_active else 0.,-.25,.1,-.01])
        corrected,applied=camera_only_downlook(command,dict(gimbal_rad=[-2.5,.2]),memory,True)
        assert applied and np.array_equal(corrected[:3],command[:3]) and corrected[5]>0
        assert abs(corrected[4])<=math.radians(50) and abs(corrected[5])<=math.radians(40)
command=np.arange(6,dtype=float)/10
assert np.array_equal(camera_only_downlook(command,dict(gimbal_rad=[0,.2]),dict(local_aim_valid=True),True)[0],command)
assert np.array_equal(camera_only_downlook(command,dict(gimbal_rad=[0,.2]),None,False)[0],command)
print('PASSED: expired-memory downlook covers active/inactive native recovery, preserves XY/Z and valid metric aim')
''')
(root/'launch_v22.py').write_text((root/'launch_v21.py').read_text().replace('v21','v22'))
for name in ['inspect_v21.py','audit_v21_when_closed.py','launch_v21_audit.py']:
    s=(root/name).read_text().replace('v21','v22').replace("['terminal','tilt']","['tilt']")
    (root/name.replace('v21','v22')).write_text(s)
