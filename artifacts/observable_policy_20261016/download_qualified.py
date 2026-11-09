"""Download compact qualified output with a bounded transfer and verify every file."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tarfile,time,os
ROOT=Path(__file__).resolve().parent
REMOTE='/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/observable_policy_20261016T203932Z'
HOST='hxhshsh7gyg@34.87.180.165'
OPTIONS=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/Users/gamee/.ssh/id_ed25519']
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',choices=['r8'],default='r8');args=parser.parse_args();rev=args.revision
    destination=ROOT/('delivery_'+rev);destination.mkdir(exist_ok=False)
    started=time.monotonic();deadline=started+280.
    receipt_name=f'qualified_delivery_{rev}_receipt.json';archive_name=f'qualified_delivery_{rev}.tar.gz'
    for name in [receipt_name,archive_name]:
        subprocess.run(['scp',*OPTIONS,HOST+':'+REMOTE+'/'+name,str(destination/name)],check=True,
            timeout=max(1.,deadline-time.monotonic()),capture_output=True,text=True)
    transfer_seconds=time.monotonic()-started
    receipt=json.loads((destination/receipt_name).read_text());archive=destination/archive_name
    assert receipt['archive']==REMOTE+'/'+archive_name
    assert archive.stat().st_size==receipt['bytes'] and sha(archive)==receipt['sha256']
    with tarfile.open(archive,'r:gz') as tf:
        for member in tf.getmembers():
            target=(destination/member.name).resolve()
            assert os.path.commonpath([str(destination.resolve()),str(target)])==str(destination.resolve())
            assert not member.issym() and not member.islnk() and '\\' not in member.name
            assert member.isfile() or member.isdir()
        tf.extractall(destination)
    package=destination/f'qualified_delivery_{rev}';manifest=json.loads((package/'MANIFEST.json').read_text())
    for name,metadata in manifest.items():
        p=(package/name).resolve();assert os.path.commonpath([str(package.resolve()),str(p)])==str(package.resolve())
        assert p.stat().st_size==metadata['bytes'] and sha(p)==metadata['sha256'],name
    result=dict(status='downloaded_and_hash_verified',transfer_seconds=transfer_seconds,total_seconds=time.monotonic()-started,
        bytes=archive.stat().st_size,sha256=receipt['sha256'],verified_package_files=len(manifest),archive=str(archive),package=str(package),results=str(package/'RESULTS.md'))
    (destination/'download_receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
