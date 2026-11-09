"""Independent recovery package with active source/weights, not an installation."""
from pathlib import Path
import datetime,hashlib,io,json,zipfile
import h5py,numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'candidate_exports/experimental_v39';BUNDLE=ROOT.parents[1]/'landing_hardening_20261018T011610Z/candidate_r15'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=False);binding=json.loads((ROOT/'search_v39/candidate_binding.json').read_text());assert sha(Path(binding['checkpoint']).read_bytes())==binding['recognizer_sha256'];members={}
    for prefix,directory in [('base_r15',BUNDLE),('sources',ROOT/'search_v39/sources')]:
        for p in directory.rglob('*'):
            if p.is_file()and '__pycache__'not in p.parts and p.suffix not in ['.h5','.mp4','.log','.mjb']:members[prefix+'/'+p.relative_to(directory).as_posix()]=p.read_bytes()
    for n,source in [('recognizer_best.pt',ROOT/'perception_training_v38/best.pt'),('recognizer_latest_resume.pt',ROOT/'perception_training_v38/latest.pt')]:members['checkpoints/'+n]=source.read_bytes()
    for n in ['result.json','provenance.json','history.json','baseline_validation.json']:members['training/'+n]=(ROOT/'perception_training_v38'/n).read_bytes()
    for n in ['candidate_binding.json','source_test_receipt.json','runtime_probe.json']:members['evidence/'+n]=(ROOT/'search_v39'/n).read_bytes()
    probe=json.loads((ROOT/'search_v39/runtime_probe.json').read_text());assert probe['status']=='runtime_hook_probe_passed'and probe['recognizer_sha256']==binding['recognizer_sha256'];source=Path(probe['source']);indices=[r['frame']for r in probe['rows'][:16]]
    with h5py.File(source/'observations.h5','r')as h:
        images=np.asarray(h['rgb'][indices]);rows=[json.loads(h['steps'][i])['observation']for i in indices]
    payload=io.BytesIO();np.savez_compressed(payload,rgb=images);members['restore_fixture/rgb.npz']=payload.getvalue();members['restore_fixture/observations.json']=json.dumps(rows).encode();members['restore_fixture/provenance.json']=json.dumps(dict(source=str(source),indices=indices,scope='Existing known MuJoCo development RGB for offline restore only; never training or final heldout',images_sha256=[sha(x.tobytes())for x in images])).encode()
    members['restore_check.py']=(ROOT/'restore_candidate_v39.py').read_bytes()
    members['README.md']=b'''# Experimental V39 recovery package\n\nNot qualified for production and not installed into Tidewater.\nActive runtime: sources/target_learning/expert_adapter_v39.py; original R15\npose and b432 spatial head; new RGB verifier recognizer_best.pt.\nThe latest resume checkpoint is separate and is not necessarily selected.\nUse Python with torch, numpy, OpenCV and scipy. Run python restore_check.py\nfor an offline CPU loading/input/finite-action check. No rendering or aircraft\ncommands occur. Fixtures are known MuJoCo development data, not a fresh test.\nAll files are hash-bound by MANIFEST.json. Native purpose flight outcomes are\nstill pending at export time. Preserve the final report before any use.\n'''
    manifest=dict(schema='approved.experimental.recovery.v39',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),qualification='EXPERIMENTAL_NOT_QUALIFIED',active_recognizer_sha256=binding['recognizer_sha256'],files={n:dict(sha256=sha(v),bytes=len(v))for n,v in members.items()});members['MANIFEST.json']=json.dumps(manifest,indent=2).encode();assert sum(map(len,members.values()))<128*1024**2
    archive=OUT/'experimental_v39.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=3)as z:
        for n,v in members.items():z.writestr(n,v)
    receipt=dict(status='experimental_recovery_package_closed',archive_relative=str(archive.relative_to(ROOT)),sha256=sha(archive.read_bytes()),bytes=archive.stat().st_size,manifest_sha256=sha(members['MANIFEST.json']),active_recognizer_sha256=binding['recognizer_sha256'],qualification='EXPERIMENTAL_NOT_QUALIFIED');(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
