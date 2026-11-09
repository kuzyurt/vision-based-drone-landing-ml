"""Immediate independent checkpoint copy; does not race snapshot archive writes."""
from pathlib import Path
import datetime,hashlib,json,sys,time
import transport
ROOT=Path(__file__).resolve().parent;DEST=ROOT/'trained_policy_recovery';DEST.mkdir(exist_ok=True);start=time.monotonic()
code="""
from pathlib import Path
import hashlib,json
p=Path(__ROOT__);records=[]
for root in ['perception_training_v47']:
 for name in ['best.pt','latest.pt','result.json','provenance.json']:
  q=p/root/name;data=q.read_bytes();records.append(dict(relative=q.relative_to(p).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
print(json.dumps(records))
""".replace('__ROOT__',repr(transport.REMOTE))
entries=json.loads(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
for r in entries:
    target=DEST/r['relative'];target.parent.mkdir(exist_ok=True);tmp=target.with_suffix(target.suffix+'.part');transport.pull(r['relative'],tmp);assert tmp.stat().st_size==r['bytes']and hashlib.sha256(tmp.read_bytes()).hexdigest()==r['sha256']
    if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest()==r['sha256'];tmp.unlink()
    else:tmp.replace(target)
receipt=dict(status='actual_trained_models_verified_on_laptop',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-start,files=entries,production_qualified=False,source_bundle_also_preserved_in_periodic_archives=True);(DEST/'VERIFIED_V47.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
