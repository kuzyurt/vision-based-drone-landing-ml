"""New perception-only admission of exact recorded images after policy failure.

No old review inputs, action targets, H5 modifications or guessed image joins.
"""
from pathlib import Path
import hashlib,json
import h5py,numpy as np
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
from harvest_curriculum_v23 import actual_paint_evidence
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'curriculum_v23';DEST=OUT/'perception_admission_v2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    DEST.mkdir(exist_ok=True);assert not(DEST/'manifest.json').exists(),'Never overwrite closed admission manifest'
    plan=json.loads((OUT/'plan.json').read_text());contract=json.loads((OUT/'contract.json').read_text())
    assert sha(OUT/'plan.json')==contract['plan_sha256']
    frozen=OUT/'producer_snapshot';sources=json.loads((frozen/'producer_source_hashes.json').read_text())
    assert sources['contract_sha256']==sha(OUT/'contract.json')
    for relative,digest in sources['files'].items():assert sha(frozen/relative)==digest
    admitted=[];skipped=[]
    for job in plan['jobs']:
        ep=OUT/'episodes'/job['name']
        if not ep.exists():continue
        if not(ep/'summary.json').exists():
            skipped.append(dict(episode=job['name'],reason='no closed native summary'));continue
        required=['capture_annotations.jsonl','observations.h5','steps.jsonl']
        missing=[name for name in required if not(ep/name).exists()]
        if missing:
            skipped.append(dict(episode=job['name'],reason='interrupted before complete image/annotation recording existed',missing=missing));continue
        summary=json.loads((ep/'summary.json').read_text());assert summary['runtime_source_sha256']==contract['baseline_runtime_source_sha256']
        producer=json.loads((ep/'staged_production_receipt.json').read_text());assert producer['schema']=='mujoco.curriculum_candidate.v1'
        assert producer['contract_sha256']==sha(OUT/'contract.json')and producer['split']==job['role']
        assert sha(job['scenario_path'])==job['scenario_sha256'];scenario=json.loads(Path(job['scenario_path']).read_text())
        world=next(w for w in plan['worlds']if w['index']==job['world_index'])
        assert world['role']==job['role']and world['role']!='heldout'and world['world_seed']==scenario['world_seed']
        dst=DEST/job['name']
        if dst.exists():
            receipt=json.loads((dst/'admission.json').read_text())
            assert receipt['role']==job['role']and receipt['contract_sha256']==sha(OUT/'contract.json')
            assert receipt['source_trace_sha256']==sha(ep/'steps.jsonl')and receipt['capture_annotations_sha256']==sha(ep/'capture_annotations.jsonl')
            assert receipt['sha256']==sha(dst/'images.h5')and receipt['all_recorded_valid_images_exactly_joined']
            admitted.append(receipt);continue
        index=load_capture_index(ep/'capture_annotations.jsonl');seen=set();frames=[];images=[];previous=None;joined=0;owners={};last=-float('inf');last_owner=None
        with h5py.File(ep/'observations.h5','r')as h:
            assert h.attrs['schema']=='mujoco.curriculum_candidate.v1'and h.attrs['role']=='curriculum_candidate'
            assert not h.attrs['training_eligible']and h.attrs['split']==job['role']and h.attrs['production_contract_sha256']==producer['contract_sha256']
            rows=[json.loads(l)for l in(ep/'steps.jsonl').open()]
            assert len(h['rgb'])==len(rows),'Incomplete row/image writes cannot be admitted'
            for row in rows:
                assert row['role']=='curriculum_candidate'and row['split']==job['role']
                o=row['observation'];d=row['output'].get('learner_diagnostics')or{};owner=d.get('actual_command_owner','unknown');owners[owner]=owners.get(owner,0)+1
                if previous is not None:assert np.allclose(previous,o['previous_executed_action'],rtol=0,atol=1e-8)
                previous=row['output']['executed_action'];rgb=np.asarray(h['rgb'][row['frame_index']]);label=join_delivered_frame(o,rgb,index)
                if label is None:continue
                joined+=1;uid=label['capture_uid'];capture=label['capture_s']
                interval=.25 if job['role']=='training'and(d.get('recovery_active')or owner!=last_owner)else .5;last_owner=owner
                if uid in seen or capture-last<interval-1e-6:continue
                seen.add(uid);last=capture
                frame=dict(label,world_seed=scenario['world_seed'],path_seed=scenario['path_seed'],role=job['role'],index=len(frames),
                    original_frame_index=row['frame_index'],source_episode=str(ep),source_capture_uid=uid,split_unit='world',actual_command_owner=owner,
                    labels_drive_actions=False,source_physical_outcome=summary['outcome'],action_targets_admissible=False)
                for inst in frame['instances']:
                    evidence=actual_paint_evidence(rgb,inst);inst['marker_head_loss_available']=evidence is not None
                    if evidence is not None:inst['visible_marker_evidence_pixels_annotation_only']=evidence
                frames.append(frame);images.append(rgb)
        if len(frames)<8:
            skipped.append(dict(episode=job['name'],reason='fewer than8 unique sparse images',frames=len(frames),exact_joins=joined,outcome=summary['outcome']));continue
        dst=DEST/job['name'];dst.mkdir(exist_ok=False)
        with h5py.File(dst/'images.h5','x')as h:
            h.create_dataset('rgb',data=np.stack(images),chunks=(1,360,640,3),compression='lzf')
            h.create_dataset('labels',data=[json.dumps(f,separators=(',',':'),allow_nan=False)for f in frames],dtype=h5py.string_dtype('utf-8'))
            h.attrs.update(schema='mujoco.perception_admitted.v1',role=job['role'],teacher_actions=False,action_targets_admissible=False,
                source_episode=str(ep),production_contract_sha256=sha(OUT/'contract.json'))
        receipt=dict(schema='mujoco.perception_admission.v2',status='admitted_for_perception_only',role=job['role'],world_seed=scenario['world_seed'],
            source_episode=str(ep),source_recording_role='curriculum_candidate',source_training_eligible=False,source_H5_eligibility_unchanged=True,
            source_trace_sha256=sha(ep/'steps.jsonl'),capture_annotations_sha256=sha(ep/'capture_annotations.jsonl'),
            contract_sha256=sha(OUT/'contract.json'),plan_sha256=sha(OUT/'plan.json'),total_rows=len(rows),exact_image_joins=joined,
            frames=len(frames),path=str(dst/'images.h5'),sha256=sha(dst/'images.h5'),command_owners=owners,
            actual_command_history_matches=True,outcome=summary['outcome'],failed_or_interrupted_recording=summary['outcome']!='landed',
            all_recorded_valid_images_exactly_joined=True,teacher_demonstration_qualified=False,old_review_data_admitted=False,
            action_targets_admissible=False,heldout_used=False,tidewater_used=False,consumer_source_sha256=sha(__file__))
        (dst/'admission.json').write_text(json.dumps(receipt,indent=2));admitted.append(receipt)
    assert any(e['role']=='training'for e in admitted)and any(e['role']=='validation'for e in admitted)
    manifest=dict(status='completed',entries=admitted,skipped=skipped,frames=sum(e['frames']for e in admitted),
        contract_sha256=sha(OUT/'contract.json'),plan_sha256=sha(OUT/'plan.json'),heldout_used=False,tidewater_used=False,
        teacher_actions_used=False,scope='Isolated visual labels, including disclosed policy failure/interruption; not teacher actions or deployment proof')
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(dict(status='completed',episodes=len(admitted),frames=manifest['frames'],skipped=skipped)))
if __name__=='__main__':main()
