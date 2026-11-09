"""One quiet event wait, then one compact verified transfer under five minutes."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
import vm_io
HERE=Path(__file__).resolve().parent;state=HERE/'local_v15_download_state.json'
def save(**v):
    v['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(state)
try:
    assert not state.exists();save(status='waiting_for_vm_review_group')
    vm_io.ssh(vm_io.PYTHON,vm_io.REMOTE+'/wait_review_package_v15.py',capture_output=True,text=True,timeout=1600)
    start=time.monotonic();save(status='downloading_compact_previews')
    names=[]
    for case in ['hard','recovery','dagger']:
        prefix='v15_'+case
        names.extend([prefix+'_actual_preview_audit.json',prefix+'_actual_camera_contact_sheet.jpg',prefix+'_actual_expert_review.mp4',prefix+'_actual_expert_review_video_receipt.json'])
    p=subprocess.run([sys.executable,str(HERE/'vm_io.py'),'pull',*names],capture_output=True,text=True,check=True,timeout=295)
    assert time.monotonic()-start<300;out=HERE/'vm_results';verified=[]
    for case in ['hard','recovery','dagger']:
        prefix='v15_'+case;video=out/(prefix+'_actual_expert_review.mp4');receipt=json.loads((out/(prefix+'_actual_expert_review_video_receipt.json')).read_text())
        assert hashlib.sha256(video.read_bytes()).hexdigest()==receipt['video_sha256'] and video.stat().st_size==receipt['bytes']
        verified.append(dict(case=case,video=str(video.resolve()),sha256=receipt['video_sha256']))
    save(status='completed',download_and_verification_s=time.monotonic()-start,verified=verified,training_approved=False,rendered_on_vm_only=True)
except BaseException as e:save(status='failed',error=repr(e));raise
