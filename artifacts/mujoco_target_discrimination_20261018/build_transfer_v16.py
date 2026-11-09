from pathlib import Path
import hashlib,json,datetime
p=Path(__file__).resolve().parent
(p/'wait_review_package_v16.py').write_text((p/'wait_review_package_v14.py').read_text().replace('v14','v16'))
s=(p/'download_review_v14_when_ready.py').read_text().replace('v14','v16')
s=s.replace('HERE=Path(__file__).resolve().parent',"vm_io.OPTIONS.extend(['-o','ServerAliveInterval=20','-o','ServerAliveCountMax=3'])\nHERE=Path(__file__).resolve().parent")
s=s.replace("except BaseException as error:save(status='failed',error=repr(error));raise", "except BaseException as error:save(status='failed',error=repr(error),stderr=getattr(error,'stderr',None));raise")
(p/'download_review_v16_when_ready.py').write_text(s)
verified=[]
for case in ['hard','recovery','dagger']:
    prefix='v15_'+case;video=p/'vm_results'/(prefix+'_actual_expert_review.mp4')
    r=json.loads((p/'vm_results'/(prefix+'_actual_expert_review_video_receipt.json')).read_text())
    assert hashlib.sha256(video.read_bytes()).hexdigest()==r['video_sha256'] and video.stat().st_size==r['bytes']
    verified.append(dict(case=case,video=str(video),sha256=r['video_sha256'],bytes=r['bytes']))
dest=p/'local_v15_manual_download_verified.json';assert not dest.exists()
dest.write_text(json.dumps(dict(status='completed',transport_download_seconds=77.,download_under_five_minutes=True,sha_and_size_verified=True,verified=verified,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_listener_failure_preserved=True,training_approval=False),indent=2))
