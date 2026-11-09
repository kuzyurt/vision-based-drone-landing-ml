"""Supply Dawn's required C++ runtime locally; never change VM system libraries."""
from pathlib import Path
import ctypes,hashlib,io,json,os,tarfile,urllib.request,zipfile
ROOT=Path(__file__).resolve().parent;stage=ROOT/'tidewater_runtime/cpp_runtime';stage.mkdir(exist_ok=False)
zstd=ctypes.CDLL('libzstd.so.1');zstd.ZSTD_getFrameContentSize.argtypes=[ctypes.c_void_p,ctypes.c_size_t];zstd.ZSTD_getFrameContentSize.restype=ctypes.c_ulonglong
zstd.ZSTD_decompress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t];zstd.ZSTD_decompress.restype=ctypes.c_size_t
zstd.ZSTD_isError.argtypes=[ctypes.c_size_t];zstd.ZSTD_isError.restype=ctypes.c_uint
receipts=[]
for name in ['libgcc','libstdcxx']:
 metadata=json.load(urllib.request.urlopen('https://api.anaconda.org/package/conda-forge/'+name,timeout=60))
 files=[f for f in metadata['files'] if f['basename'].startswith('linux-64/') and f['basename'].endswith('.conda') and f['version'].startswith('14.')]
 item=max(files,key=lambda f:f['upload_time']);url='https:'+item['download_url'];data=urllib.request.urlopen(url,timeout=90).read()
 actual=hashlib.sha256(data).hexdigest();expected=item.get('sha256') or item.get('attrs',{}).get('sha256');assert expected and actual==expected
 archive=zipfile.ZipFile(io.BytesIO(data));pkg=next(x for x in archive.namelist() if x.startswith('pkg-') and x.endswith('.tar.zst'));compressed=archive.read(pkg)
 size=zstd.ZSTD_getFrameContentSize(compressed,len(compressed));assert 0<size<200_000_000,size
 target=ctypes.create_string_buffer(size);written=zstd.ZSTD_decompress(target,size,compressed,len(compressed));assert not zstd.ZSTD_isError(written)
 with tarfile.open(fileobj=io.BytesIO(target.raw[:written])) as tar:
  for member in tar.getmembers():assert (stage/member.name).resolve().is_relative_to(stage.resolve())
  tar.extractall(stage,filter='data')
 receipts.append(dict(package=name,version=item['version'],source=url,sha256=actual))
(stage/'receipt.json').write_text(json.dumps(dict(scope='Headless Node process LD_LIBRARY_PATH only; system unchanged',packages=receipts),indent=2)+'\n')
print((stage/'receipt.json').read_text())
