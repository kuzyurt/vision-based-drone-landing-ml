import transport
code="from pathlib import Path;R=Path("+repr(transport.REMOTE)+");print((R/'terminal_handoff_v46/state.json').read_text());print((R/'terminal_v46_queue.log').read_text()[-2500:]);print((R/'search_v46/pilots/state.json').read_text()[-5000:])"
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
print(transport.run('build_search_v48.py'))
