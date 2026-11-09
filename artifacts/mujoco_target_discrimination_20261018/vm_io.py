"""Strict SSH transport for this experiment; no credential content is read."""
from pathlib import Path
import argparse, hashlib, json, shlex, subprocess, time,zipfile,tempfile

HERE = Path(__file__).resolve().parent
REMOTE = '/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z'
HOST = 'hxhshsh7gyg@34.87.180.165'
OPTIONS = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-i', 'C:/Users/gamee/.ssh/id_ed25519']
PYTHON = '/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/.venv/bin/python'

def ssh(*args, **kwargs):
    return subprocess.run(['ssh', '-T', *OPTIONS, HOST, ' '.join(shlex.quote(str(a)) for a in args)], check=True, **kwargs)

def main():
    p = argparse.ArgumentParser(); p.add_argument('mode', choices=['push', 'run', 'pull']); p.add_argument('names', nargs=argparse.REMAINDER); a = p.parse_args()
    if not a.names:p.error('At least one file or script is required')
    if a.mode == 'push':
        members=[]
        for name in a.names:
            source = (HERE / name).resolve(); assert source.is_relative_to(HERE) and source.is_file()
            members.append((name.replace('\\','/'),source))
        with tempfile.TemporaryDirectory(prefix='mujoco_sources_')as td:
            archive=Path(td)/'sources.zip'
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
                for name,source in members:z.write(source,name)
            digest=hashlib.sha256(archive.read_bytes()).hexdigest();remote_archive=REMOTE+'/sources_'+digest[:16]+'.zip'
            ssh('mkdir','-p',REMOTE)
            subprocess.run(['scp',*OPTIONS,str(archive),HOST+':'+remote_archive],check=True,timeout=120)
            loader="""from pathlib import Path
import hashlib,json,sys,zipfile
root=Path(sys.argv[1]).resolve();archive=Path(sys.argv[2]);expected=sys.argv[3]
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
rows=[]
with zipfile.ZipFile(archive)as z:
 for name in z.namelist():
  dst=(root/name).resolve();assert dst.is_relative_to(root) and not name.startswith('/')
  data=z.read(name)
  if dst.exists() and dst.read_bytes()!=data:
   old=dst.read_bytes();backup=root/'source_history'/(hashlib.sha256(old).hexdigest()+'_'+dst.name)
   backup.parent.mkdir(exist_ok=True)
   if not backup.exists():backup.write_bytes(old)
  dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
  rows.append(dict(file=name,sha256=hashlib.sha256(data).hexdigest()))
print(json.dumps(dict(uploaded=rows,archive_sha256=expected)))
"""
            ssh(PYTHON,'-c',loader,REMOTE,remote_archive,digest)
    elif a.mode == 'run':
        ssh(PYTHON, REMOTE + '/' + a.names[0], *a.names[1:])
    else:
        out=HERE/'vm_results';out.mkdir(exist_ok=True)
        began=time.monotonic()
        assert len({Path(n).name for n in a.names})==len(a.names)
        for name in a.names:
            assert not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name
        # Stage first and preserve any earlier different local artifact. Remote
        # paths can share generic basenames such as result.json/receipt.json.
        preserved=[]
        with tempfile.TemporaryDirectory(prefix='mujoco_download_')as td:
            subprocess.run(['scp', *OPTIONS, *[HOST + ':' + REMOTE + '/' + n for n in a.names], td], check=True, timeout=290)
            for name in a.names:
                received=Path(td)/Path(name).name;destination=out/received.name
                data=received.read_bytes()
                if destination.exists()and destination.read_bytes()!=data:
                    previous=destination.read_bytes();digest=hashlib.sha256(previous).hexdigest()
                    archive=out/'source_history'/(digest+'_'+destination.name)
                    archive.parent.mkdir(exist_ok=True)
                    if not archive.exists():archive.write_bytes(previous)
                    preserved.append(str(archive))
                destination.write_bytes(data)
        print(json.dumps(dict(download_seconds=time.monotonic()-began,files=a.names,preserved_local_versions=preserved)),flush=True)

if __name__ == '__main__': main()
