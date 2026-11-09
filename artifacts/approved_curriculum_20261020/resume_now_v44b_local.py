import transport
print(transport.vm.ssh('whoami',capture_output=True,text=True,timeout=30).stdout)
print(transport.vm.ssh('hostname',capture_output=True,text=True,timeout=30).stdout)
print(transport.run('close_failed_cohort_v42.py'))
print(transport.run('launch_static_repair_v44b.py'))
