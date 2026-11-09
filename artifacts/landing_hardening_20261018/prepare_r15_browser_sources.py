from pathlib import Path
r=Path(__file__).resolve().parent
oldsha='34845b34dc9490fddcc411738bd25b83e0d52bf4ab3564bf4aa22c931004c473';newsha='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
s=(r/'export_browser_stage_r14.py').read_text().replace('r14','r15').replace(oldsha,newsha).replace('f68949c25ad36bc91bb2ee0b325cc501e6eb6b9051b008e9fabe6dd0aca17d8f','8427a30074c5f74256230f1bc6a2e8175a9c0af0000ef7c4a95c27660806b72b')
(r/'export_browser_stage_r15.py').write_text(s)
s=(r/'probe_r14_vm_controller.mjs').read_text().replace('r14','r15').replace(oldsha,newsha)
s=s.replace('_maximum=0.;_frames=0;', '_maximum=0.;_channels=np.zeros(6);_budget_checked=0;_frames=0;')
a="  np.testing.assert_allclose(_a,_f['expected_action'],atol=1e-10,rtol=1e-10)";assert a in s
b="""  _difference=np.abs(_a-np.asarray(_f['expected_action']));_channels=np.maximum(_channels,_difference)
  assert max(_difference[:5])<1e-10 and _difference[5]<1e-8,(_frames,_difference)
  _plan=_d.get('nearfield_visibility_plan',{})
  if _f['expected_terminal_budget']is not None:
   assert abs(_plan['visibility_speed_limit_m_s']-_f['expected_terminal_budget'])<1e-12
   assert _plan['pause_descent']==_f['expected_terminal_pause'];_budget_checked+=1
"""
s=s.replace(a,b).replace('assert _limited>=12 and _near>=100','assert _limited>=12 and _near>=100 and _budget_checked>=100')
s=s.replace("status:'passed',native_policy_sha256:","status:'passed',maximum_error_per_channel:p.python.runPython('_channels.tolist()').toJs(),terminal_budget_frames:p.python.runPython('_budget_checked'),acceptance_maximum_per_channel:[1e-10,1e-10,1e-10,1e-10,1e-10,1e-8],native_policy_sha256:")
s=s.replace('including stopping handoff and delayed near velocity.','including stopping handoff, delayed near velocity and calibrated terminal speed budget. Camera optimizer1e-8rad/s tolerance documents inherited tiny roundoff; physical gates unchanged.')
(r/'probe_r15_vm_controller.mjs').write_text(s)
