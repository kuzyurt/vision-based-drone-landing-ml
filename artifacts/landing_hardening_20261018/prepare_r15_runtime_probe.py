from pathlib import Path
r=Path(__file__).resolve().parent
s=(r/'probe_near_motion_r2_runtime.py').read_text().replace("bundle=ROOT/'candidate_near_motion_r2'","bundle=ROOT/'candidate_r15'").replace("out=ROOT/'near_motion_r2_runtime_branch_probe.json'","out=ROOT/'r15_runtime_terminal_motion_probe.json'")
s=s.replace("source=ROOT/'r12_pilot5/freshD_gravel_05'","source=ROOT/'r14_pilot5/freshD_gravel_05'")
s=s.replace('active=0;maximum_action_change=0.','active=0;motion_veto=0;minimum_limit=1.;maximum_action_change=0.')
a="        active+=bool(diag.get('nearfield_persistent_velocity_used'))";assert a in s
s=s.replace(a,a+"\n        plan=diag.get('nearfield_visibility_plan',{})\n        if 'visibility_speed_limit_m_s'in plan:\n            minimum_limit=min(minimum_limit,plan['visibility_speed_limit_m_s'])\n            motion_veto+=bool(plan['relative_speed_m_s']>plan['visibility_speed_limit_m_s'])")
s=s.replace('assert active>=150,(active,frames)','assert active>=150 and motion_veto>=12 and minimum_limit<.04,(active,motion_veto,minimum_limit,frames)')
s=s.replace('active_near_velocity_frames=active,','active_near_velocity_frames=active,actual_terminal_motion_veto_frames=motion_veto,minimum_speed_limit_m_s=minimum_limit,')
s=s.replace('Corrected near velocity branch exercised.','Calibrated terminal-motion veto and persistent velocity branches exercised.')
p=r/'probe_r15_runtime.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
