"""Wait quietly for VM packaging, then download and verify compact artifacts."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
import vm_io
HERE=Path(__file__).resolve().parent
state=HERE/'local_v13b_download_state.json'
def save(**value):
 value['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();temp=state.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));temp.replace(state)
def main():
 assert not state.exists();save(status='waiting_for_vm_packaging')
 vm_io.ssh(vm_io.PYTHON,vm_io.REMOTE+'/wait_review_package_v13b.py',capture_output=True,text=True,timeout=1050)
 save(status='downloading_verified_compact_artifacts');start=time.monotonic()
 names=['v13b_actual_preview_audit.json','v13b_actual_camera_contact_sheet.jpg','v13b_actual_expert_review.mp4','v13b_actual_expert_review_video_receipt.json']
 process=subprocess.run([sys.executable,str(HERE/'vm_io.py'),'pull',*names],capture_output=True,text=True,check=True,timeout=295)
 elapsed=time.monotonic()-start;assert elapsed<300,'Download exceeded five-minute limit'
 print(process.stdout,flush=True);out=HERE/'vm_results';receipt=json.loads((out/names[-1]).read_text());video=out/names[-2]
 digest=hashlib.sha256(video.read_bytes()).hexdigest();assert digest==receipt['video_sha256']and video.stat().st_size==receipt['bytes']
 value=dict(status='completed',download_and_verification_seconds=elapsed,video=str(video.resolve()),video_sha256=digest,files=names,rendered_on_vm_only=True,review_needed_before_bulk=True)
 save(**value);print(json.dumps(value),flush=True)
if __name__=='__main__':
 try:main()
 except BaseException as error:save(status='failed',error=repr(error));raise
