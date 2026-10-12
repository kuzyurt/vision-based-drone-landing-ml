"""Consolidate the four declared attempts, preserving the parent report."""
import json,datetime,subprocess,collections
from pathlib import Path
import psutil,h5py,numpy as np
from landing_training.gate import file_hash,source_fingerprint
from landing_training.marker_bundle import read_bundle

root=Path('landing_training/outputs/tidewater_20261011');out=root/'pilot_v1'
plan=json.loads((out/'plan.json').read_text());results=[];metrics=[]
for case in plan['cases']:
 directory=out/case['scenario']['name'];result=json.loads((directory/'result.json').read_text());summary=json.loads((directory/'summary.json').read_text())
 assert json.loads((directory/'scenario.json').read_text())==case['scenario']==summary['scenario']
 assert summary['time_of_day']==case['time_of_day'] and not summary['training_eligible']
 assert file_hash(directory/'review.mp4')==result['video_sha256']
 assert result['frozen_policy_metadata']['bundle_sha256']==plan['policy_bundle_sha256']
 rows=[json.loads(line) for line in (directory/'steps.jsonl').read_text().splitlines()]
 assert rows[-1]['terminal'] and rows[-1]['outcome']==result['outcome']
 active=[r for r in rows if not r.get('terminal')]
 assert all(r['output']['learner_action'] is not None for r in active)
 for file in list(directory.glob('*.h5'))+list(directory.glob('*.hdf5')):
  with h5py.File(file) as h:assert not bool(h.attrs['training_eligible'])
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(directory/'review.mp4')]))
 video=next(s for s in info['streams'] if s['codec_type']=='video');assert int(video['nb_read_frames'])==len(rows) and video['r_frame_rate']=='25/1'
 subprocess.run(['ffmpeg','-v','error','-i',str(directory/'review.mp4'),'-f','null','-'],check=True)
 v=[r['output']['learner_diagnostics'] for r in active];speed=np.array([r['privileged']['boat_speed_m_s'] for r in active]);wind=np.array([np.linalg.norm(r['privileged']['wind_enu_m_s']) for r in active])
 metrics.append(dict(name=case['scenario']['name'],outcome=result['outcome'],task_seconds=rows[-1]['task_time_s'],
  metric_fraction=sum(bool(d.get('metric_valid')) for d in v)/len(v),mean_learned_visibility=float(np.mean([d['raw_model_visibility_probability'] for d in v])),
  median_actual_boat_speed_m_s=float(np.median(speed)),max_actual_boat_speed_m_s=float(speed.max()),median_actual_wind_m_s=float(np.median(wind)),
  video_seconds=float(info['format']['duration']),video_sha256=result['video_sha256'],video_bytes=result['video_bytes']))
 results.append(result)
config,checkpoint=read_bundle('landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json')
originals=json.loads(Path('landing_training/outputs/control_iteration_20261010T220632Z/preservation.json').read_text())
assert all(file_hash(p)==h for p,h in originals.items())
assert all(file_hash(p)==h for p,h in plan['extension_source_sha256'].items())
assert source_fingerprint(runtime_only=True)==plan['base_runtime_sha256']=='5ef2dd6e6b1853286fd2bbda52167100eb16e69cd3594969023e684f0333f403'
processes=[]
for p in psutil.process_iter(['pid','name','cmdline']):
 command=' '.join(p.info['cmdline'] or [])
 if p.info['name']=='px4' or ('python' in (p.info['name'] or '') and ('evaluate_tidewater' in command or 'run_tidewater_case' in command)):processes.append(p.info)
assert not processes,processes
counts=collections.Counter(r['outcome'] for r in results)
report=dict(status='completed',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),upstream_sha=plan['upstream_sha'],requested=4,completed=4,workers=3,
 outcomes=dict(counts),unsafe_count=counts['water_strike']+counts['collision_failure'],policy_frozen=True,policy_bundle_sha256=plan['policy_bundle_sha256'],episodes=results,metrics=metrics,
 scheduling_note='Cases 0–1 ran sequentially on instance 240. Cases 2–3 used isolated browser/physics workers on instances 241–242 and collector ports 5191–5192. Reserved case directories caused the original sequential driver to stop at its non-overwrite guard after case 1; the original partial report and log remain preserved.',
 scope='Zero-shot Tidewater visual/terrain transfer using original vehicle physics and the shared Airy wave model; not independent validation of Tidewater boat dynamics.')
(root/'pilot_final_report.json').write_text(json.dumps(report,indent=2))
audit=dict(originals_preserved=True,frozen_actor_and_checkpoint_verified=True,pose_checkpoint_sha256=file_hash(checkpoint),source_extensions_verified=True,active_flight_processes=processes,
 camera=json.loads((root/'camera_alignment.json').read_text()),waves=json.loads((root/'wave_alignment.json').read_text()),vehicle_contacts=json.loads((root/'vehicle_contact_alignment.json').read_text()),
 vehicle_dynamics=json.loads((root/'physics_mapping.json').read_text()),media_decode_check='passed',metrics=metrics)
(root/'completion_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps({'outcomes':dict(counts),'unsafe_count':report['unsafe_count'],'metrics':metrics},indent=2))
