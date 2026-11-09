"""Private Node loader for Ubuntu22 VM; no system libc replacement."""
from pathlib import Path
import ctypes,gzip,hashlib,io,json,subprocess,tarfile,urllib.request
ROOT=Path(__file__).resolve().parent;stage=ROOT/'tidewater_runtime/glibc';stage.mkdir(exist_ok=False)
base='https://archive.ubuntu.com/ubuntu/'
index=gzip.decompress(urllib.request.urlopen(base+'dists/noble/main/binary-amd64/Packages.gz',timeout=60).read()).decode()
entry=next(part for part in index.split('\n\n') if part.startswith('Package: libc6\n'))
fields=dict(line.split(': ',1) for line in entry.splitlines() if ': ' in line and not line.startswith(' '))
data=urllib.request.urlopen(base+fields['Filename'],timeout=90).read();actual=hashlib.sha256(data).hexdigest();assert actual==fields['SHA256']
archive=stage/'libc6.deb';archive.write_bytes(data)
subprocess.run(['ar','x',str(archive)],cwd=stage,check=True)
payload=next(stage.glob('data.tar.*'))
if payload.suffix=='.zst':
 lib=ctypes.CDLL('libzstd.so.1');lib.ZSTD_getFrameContentSize.argtypes=[ctypes.c_void_p,ctypes.c_size_t];lib.ZSTD_getFrameContentSize.restype=ctypes.c_ulonglong
 lib.ZSTD_decompress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t];lib.ZSTD_decompress.restype=ctypes.c_size_t
 compressed=payload.read_bytes();size=lib.ZSTD_getFrameContentSize(compressed,len(compressed));assert 0<size<200_000_000
 out=ctypes.create_string_buffer(size);written=lib.ZSTD_decompress(out,size,compressed,len(compressed));assert written<=size
 tar=tarfile.open(fileobj=io.BytesIO(out.raw[:written]))
else:tar=tarfile.open(payload)
with tar:
 for member in tar.getmembers():assert (stage/member.name).resolve().is_relative_to(stage.resolve())
 tar.extractall(stage,filter='data')
(stage/'receipt.json').write_text(json.dumps(dict(version=fields['Version'],source=base+fields['Filename'],sha256=actual,scope='Explicit private Node dynamic loader only; VM system libc unchanged'),indent=2)+'\n')
print((stage/'receipt.json').read_text())
