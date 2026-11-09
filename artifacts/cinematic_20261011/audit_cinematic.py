"""Verify frozen source, originals, edit provenance and native flight outcomes."""
import json,datetime,subprocess
from pathlib import Path
import psutil,h5py
from landing_training.gate import file_hash,source_fingerprint
from landing_training.marker_bundle import read_bundle

root=Path('landing_training/outputs/cinematic_20261011_v2')
plan=json.loads((root/'plan.json').read_text());report=json.loads((root/'report.json').read_text())
assert report['status']=='completed'
configuration,checkpoint=read_bundle('landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json')
original=json.loads(Path('landing_training/outputs/control_iteration_20261010T220632Z/preservation.json').read_text())
preserved={p:dict(expected=h,actual=file_hash(p)) for p,h in original.items()}
assert all(v['expected']==v['actual'] for v in preserved.values())
assert source_fingerprint(runtime_only=True)==plan['base_runtime_sha256']=='5ef2dd6e6b1853286fd2bbda52167100eb16e69cd3594969023e684f0333f403'
assert file_hash('landing_training/cinematic_montage.py')==plan['extension_sha256']==file_hash(root/'cinematic_montage.py')
active=[dict(pid=p.pid,name=p.name()) for p in psutil.process_iter() if p.name()=='px4' or ('python' in p.name() and '-m landing_training.cinematic_montage run' in ' '.join(p.cmdline()))]
assert not active,active
flights=[]
for job in plan['jobs']:
 d=Path(job['directory']);summary=json.loads((d/'summary.json').read_text());result=json.loads((d/'result.json').read_text())
 assert json.loads((d/'scenario.json').read_text())==job['scenario']==summary['scenario']
 assert summary['outcome']=='landed' and summary['training_eligible'] is False and summary['role']=='review'
 assert summary['runtime_source_sha256']==plan['base_runtime_sha256']
 assert file_hash(d/'review.mp4')==result['video_sha256']
 rows=[json.loads(x) for x in (d/'steps.jsonl').read_text().splitlines()]
 assert rows[-1]['terminal'] and rows[-1]['outcome']=='landed'
 assert all(r['output']['learner_action'] is not None for r in rows[:-1])
 recordings=list(d.glob('*.h5'))+list(d.glob('*.hdf5'))
 for f in recordings:
  with h5py.File(f) as h:assert not bool(h.attrs['training_eligible'])
 flights.append(dict(id=job['id'],map=job['scenario']['kind'],profile=job['profile'],outcome=summary['outcome'],records=len(rows),camera=summary['camera'],video_sha256=result['video_sha256']))
edit=json.loads((root/'edit_v1/edit_decisions.json').read_text())
assert len(edit['cuts'])==40 and all(c['duration_s']==.8 and c['source_end_frame_exclusive']-c['source_start_frame']==20 for c in edit['cuts'])
assert set(c['map'] for c in edit['cuts'])=={'island','beach','city','gravel','rock'}
video=root/'policy_five_maps_cinematic.mp4';probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(video)]))
s=probe['streams'][0];assert s['codec_name']=='h264' and (s['width'],s['height'])==(1280,720) and s['r_frame_rate']=='25/1' and int(s['nb_read_frames'])==800 and float(probe['format']['duration'])==32
subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
audit=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),policy_frozen=True,policy_bundle_sha256=plan['policy_bundle_sha256'],pose_checkpoint_sha256=file_hash(checkpoint),base_runtime_sha256=plan['base_runtime_sha256'],originals=preserved,active_flight_processes=active,flights=flights,video=dict(path=str(video.resolve()),sha256=file_hash(video),bytes=video.stat().st_size,duration_s=32,fps=25,cuts=40,cut_duration_s=.8,width=1280,height=720),decoder_check='passed')
(root/'completion_audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps(audit['video']))
