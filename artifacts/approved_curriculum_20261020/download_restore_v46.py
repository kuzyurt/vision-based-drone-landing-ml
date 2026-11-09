from pathlib import Path
import hashlib,json,time,zipfile
import transport
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'candidate_exports/experimental_v46';OUT.mkdir(parents=True,exist_ok=True);start=time.monotonic()
transport.pull('candidate_exports/experimental_v46/receipt.json',OUT/'remote_receipt.json');r=json.loads((OUT/'remote_receipt.json').read_text());tmp=OUT/'experimental_v46.zip.part';transport.pull(r['archive_relative'],tmp);assert tmp.stat().st_size==r['bytes']and hashlib.sha256(tmp.read_bytes()).hexdigest()==r['sha256']
unpack=OUT/'package';unpack.mkdir(exist_ok=False)
with zipfile.ZipFile(tmp)as z:
    m=json.loads(z.read('MANIFEST.json'));assert hashlib.sha256(z.read('MANIFEST.json')).hexdigest()==r['manifest_sha256']
    for n,item in m['files'].items():
        p=(unpack/n).resolve();assert p.is_relative_to(unpack.resolve());data=z.read(n);assert len(data)==item['bytes']and hashlib.sha256(data).hexdigest()==item['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    (unpack/'MANIFEST.json').write_bytes(z.read('MANIFEST.json'))
tmp.replace(OUT/'experimental_v46.zip');r.update(status='download_and_all_members_verified_on_laptop',files_verified=len(m['files']),elapsed_s=time.monotonic()-start,package=str(unpack));(OUT/'LOCAL_VERIFIED.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
