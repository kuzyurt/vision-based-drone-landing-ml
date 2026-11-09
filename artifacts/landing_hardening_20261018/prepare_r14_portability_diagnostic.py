from pathlib import Path
r=Path(__file__).resolve().parent
s=(r/'probe_r14_vm_controller.mjs').read_text()
s=s.replace("browser_r14_controller_portability.json","browser_r14_controller_portability_diagnostic.json")
s=s.replace('_maximum=0.;_frames=0;', '_maximum=0.;_channels=np.zeros(6);_worst=None;_frames=0;')
a="  np.testing.assert_allclose(_a,_f['expected_action'],atol=1e-10,rtol=1e-10)"
b="  _channels=np.maximum(_channels,np.abs(_a-np.asarray(_f['expected_action'])))\n  if _error>=_maximum:_worst=(_sequence['name'],_frames,_f['task_s'],_d['control_phase'])"
assert a in s;s=s.replace(a,b)
s=s.replace("status:'passed',native_policy_sha256:","status:'diagnostic_all_frames_completed',maximum_error_per_channel:p.python.runPython('_channels.tolist()').toJs(),worst_frame:p.python.runPython('list(_worst)').toJs(),native_policy_sha256:")
(r/'probe_r14_vm_controller_diagnostic.mjs').write_text(s)
