"""Redirect only the known frozen marker kernel to its exact-source Windows DLL."""
import local_paths
import ctypes,hashlib,json
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def install():
    marker=local_paths.PREVIOUS/'candidate_exports/native_windows/marker_kernel.dll'
    assert sha(marker)=='694cca43edd30994900bf5d577d3802d9a3d40796fd7441e22f6e69daba72fdb'
    original=ctypes.CDLL
    def load(name,*args,**kwargs):
        path=Path(str(name))
        if path.name=='marker_kernel.so':
            assert sha(path.with_name('marker_kernel.cpp'))=='0b70a9263dfc75ddba3b3771fba17391692d43bc0dbffaafe92aa33de2e58c66'
            name=str(marker)
        return original(name,*args,**kwargs)
    ctypes.CDLL=load

