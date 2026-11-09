"""Use an independently built Windows DLL from the EXACT frozen C++ source."""
from pathlib import Path
import ctypes,hashlib,json,runpy,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'candidate_exports/experimental_v39/package';LIB=ROOT/'candidate_exports/native_windows/marker_kernel.dll';SRC=PKG/'base_r15/code/landing_training/radio_robust_20261015';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert LIB.is_file();manifest=json.loads((PKG/'MANIFEST.json').read_text())
for n in ['marker_kernel.cpp','marker_trf.h']:assert sha(SRC/n)==manifest['files']['base_r15/code/landing_training/radio_robust_20261015/'+n]['sha256']
receipt=dict(status='separate_windows_build_exact_frozen_kernel',compiler=str(Path('C:/msys64/ucrt64/bin/g++.exe')),compiler_version=subprocess.check_output(['C:/msys64/ucrt64/bin/g++.exe','--version'],text=True).splitlines()[0],compiler_sha256=sha('C:/msys64/ucrt64/bin/g++.exe'),flags=['-std=c++17','-D_USE_MATH_DEFINES','-O3','-shared','-static','-static-libgcc','-static-libstdc++','-Wl,--export-all-symbols'],cpp_sha256=sha(SRC/'marker_kernel.cpp'),header_sha256=sha(SRC/'marker_trf.h'),dll_sha256=sha(LIB),original_linux_binary_unchanged=True,production_installed=False)
(LIB.parent/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2));old=ctypes.CDLL
def platform_library(name,*args,**kwargs):
    try:match=Path(str(name)).resolve()==(SRC/'marker_kernel.so').resolve()
    except Exception:match=False
    return old(str(LIB)if match else name,*args,**kwargs)
ctypes.CDLL=platform_library
sys.path.insert(0,str(ROOT/'candidate_exports/restore_dependencies'))
runpy.run_path(str(PKG/'restore_check.py'),run_name='__main__')
result=json.loads((PKG/'LOCAL_RESTORE_CHECK.json').read_text());probe=json.loads((PKG/'evidence/runtime_probe.json').read_text());expected=np.asarray([r['action']for r in probe['rows'][:result['frames']]]);delta=float(np.max(np.abs(expected-np.asarray(result['actions']))));assert delta<=1e-4,delta
result.update(windows_exact_source_build_receipt_sha256=sha(LIB.parent/'BUILD_RECEIPT.json'),maximum_fixed_input_action_difference_vs_vm=delta,fixed_input_action_tolerance=1e-4,scope='16 actual development RGB frames only; no physical/local simulator or browser qualification');(LIB.parent/'LOCAL_WINDOWS_RESTORE_VERIFIED.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='actions'}),flush=True)
