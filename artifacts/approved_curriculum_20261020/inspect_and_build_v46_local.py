import transport
print(transport.run('build_search_v46.py'))
print(transport.run('inspect_static_close_v45.py'))
from pathlib import Path
for name in ['static_repair_v44b/near_and_background_actual_labels.jpg','roi_cache/static_v44b/actual_static_labels.jpg']:
 destination=Path(__file__).parent/'vm_results'/Path(name).name;destination.parent.mkdir(exist_ok=True);transport.pull(name,destination);print(destination)
code="from pathlib import Path;R=Path("+repr(transport.REMOTE)+");p=R/'roi_cache/static_v44b/manifest.json';print('CACHE_MANIFEST',p.exists());print((R/'static_cache_v45_queue.log').read_text()[-2000:]);print((R/'static_cache_v45.log').read_text()[-2000:])"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
