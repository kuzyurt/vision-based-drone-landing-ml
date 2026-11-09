"""One verified transfer; never replace differing existing code or frozen data."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
import transport
ROOT=Path(__file__).resolve().parent;names=sys.argv[1:];assert names and len(names)==len(set(names));assert all(Path(n).name==n and(ROOT/n).is_file()and Path(n).suffix in ['.py','.md','.json']for n in names)
folder=ROOT/'_transfers';folder.mkdir(exist_ok=True);digest=hashlib.sha256(b''.join(n.encode()+b'\0'+(ROOT/n).read_bytes()for n in names)).hexdigest();archive=folder/(digest+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
    for n in names:z.writestr(n,(ROOT/n).read_bytes())
transport.vm.ssh('mkdir','-p',transport.REMOTE+'/_uploads',timeout=30);remote=transport.REMOTE+'/_uploads/'+archive.name;subprocess.run(['scp',*transport.vm.OPTIONS,str(archive),transport.vm.HOST+':'+remote],check=True,timeout=90,capture_output=True,text=True)
code="""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__ROOT__);archive=Path(__ARCHIVE__);expected=__NAMES__;mutable={'STATUS.md','EXECUTION_STATE.json'}
with zipfile.ZipFile(archive)as z:
 assert set(z.namelist())==set(expected)
 for n in expected:
  assert Path(n).name==n
  p=root/n;assert p.resolve().parent==root.resolve();value=z.read(n)
  if p.exists()and n not in mutable:assert p.read_bytes()==value,'Refuse replacement of existing different code: '+n
 for n in expected:
  p=root/n;value=z.read(n)
  if p.exists()and p.read_bytes()==value:continue
  t=p.with_suffix(p.suffix+'.uploadtmp');t.write_bytes(value);t.replace(p)
 print(json.dumps(dict(status='verified_batch_received',files={n:hashlib.sha256(z.read(n)).hexdigest()for n in expected})))
""".replace('__ROOT__',repr(transport.REMOTE)).replace('__ARCHIVE__',repr(remote)).replace('__NAMES__',repr(names))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True,timeout=40).stdout)
