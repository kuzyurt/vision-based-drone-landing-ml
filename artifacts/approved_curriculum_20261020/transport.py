"""Strict existing VM transport, scoped to the newly authorized experiment."""
from pathlib import Path
import importlib.util
import subprocess

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'mujoco_target_discrimination_20261018' / 'vm_io.py'
spec = importlib.util.spec_from_file_location('existing_vm_transport', OLD)
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)
REMOTE = vm.REMOTE + '/approved_curriculum_20261020'

def run(script, *args, timeout=240):
    return vm.ssh(vm.PYTHON, REMOTE + '/' + script, *args,
                  capture_output=True, text=True, timeout=timeout).stdout

def push(name):
    source = (HERE / name).resolve()
    assert source.is_relative_to(HERE) and source.is_file()
    vm.ssh('mkdir', '-p', REMOTE, timeout=60)
    subprocess.run(['scp', *vm.OPTIONS, str(source), vm.HOST + ':' + REMOTE + '/' + name],
                   check=True, timeout=120, capture_output=True, text=True)

def pull(remote_relative, destination):
    assert not Path(remote_relative).is_absolute() and '..' not in Path(remote_relative).parts
    subprocess.run(['scp', *vm.OPTIONS, vm.HOST + ':' + REMOTE + '/' + remote_relative,
                    str(destination)], check=True, timeout=240, capture_output=True, text=True)
