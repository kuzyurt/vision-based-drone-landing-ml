"""Admit NEW staged perception images after exact source/label/split checks.

Never edits source H5 eligibility; no review recordings or action targets accepted.
Filesystem events wake this consumer when a producer closes an episode.
"""
from pathlib import Path
import ctypes,hashlib,json,os,select,struct,time
import h5py,numpy as np
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'curriculum_v23';CACHE=OUT/'perception_admission_v1'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(**v):
    v.update(pid=os.getpid(),scope='new supervised perception images only',teacher_actions=False)
    p=OUT/'harvest_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)
def actual_paint_evidence(rgb,instance):
    point=instance.get('pad_pixel')
    if point is None or instance['annotation_instance']!='target':return None
    x,y=np.round(point).astype(int)
    patch=rgb[max(0,y-2):min(360,y+3),max(0,x-2):min(640,x+3)].astype(float)
    if not patch.size:return 0
    cyan=(patch[...,1]>90)&(patch[...,1]>1.4*(patch[...,0]+1))&(patch[...,2]>1.4*(patch[...,0]+1))
    return int(instance['marker_visible_pixels'])if cyan.any()else 0
def harvest(job,contract,plan):
    ep=OUT/'episodes'/job['name'];dest=CACHE/job['name'];dest.mkdir(exist_ok=False)
    source_receipt=json.loads((ep/'staged_production_receipt.json').read_text())
    assert source_receipt['schema']=='mujoco.curriculum_candidate.v1'and source_receipt['split']==job['role']
    assert source_receipt['contract_sha256']==sha(OUT/'contract.json')
    assert sha(job['scenario_path'])==job['scenario_sha256']
    scenario=json.loads(Path(job['scenario_path']).read_text());summary=json.loads((ep/'summary.json').read_text())
    assert summary['runtime_source_sha256']==contract['baseline_runtime_source_sha256']
    assert summary['outcome']not in ['water_strike','collision_failure']
    world=next(w for w in plan['worlds']if w['index']==job['world_index'])
    assert world['role']==job['role']and world['world_seed']==scenario['world_seed']and world['role']!='heldout'
    assert not json.loads((ep/'capture_annotation_receipt.json').read_text())['unbound_capture']
    index=load_capture_index(ep/'capture_annotations.jsonl')
    total=0;joined=0;selected=0;seen=set();last_sample=-float('inf');previous=None
    owners={};last_owner=None;all_history_matches=True;labels=[]
    with h5py.File(ep/'observations.h5','r')as h,h5py.File(dest/'images.h5','x')as target:
        assert h.attrs['schema']=='mujoco.curriculum_candidate.v1'and h.attrs['role']=='curriculum_candidate'
        assert not bool(h.attrs['training_eligible'])and h.attrs['split']==job['role']
        assert h.attrs['production_contract_sha256']==source_receipt['contract_sha256']
        images=target.create_dataset('rgb',(0,360,640,3),maxshape=(None,360,640,3),dtype='u1',chunks=(1,360,640,3),compression='lzf')
        text=target.create_dataset('labels',(0,),maxshape=(None,),dtype=h5py.string_dtype('utf-8'))
        for line in(ep/'steps.jsonl').open():
            row=json.loads(line);assert row['role']=='curriculum_candidate'and row['split']==job['role'];total+=1
            o=row['observation'];d=row['output'].get('learner_diagnostics')or{};dd=d.get('dagger')or{}
            owner=d.get('actual_command_owner',dd.get('ownership',{}).get('owner','observable_expert'));owners[owner]=owners.get(owner,0)+1
            if previous is not None:
                assert np.allclose(previous,o['previous_executed_action'],rtol=0,atol=1e-8),'Actual command history discontinuity'
            previous=row['output']['executed_action']
            rgb=np.asarray(h['rgb'][row['frame_index']]);label=join_delivered_frame(o,rgb,index)
            if label is None:continue
            joined+=1;uid=label['capture_uid']
            assert label['actor_input']is False and label['annotations_grant_training_eligibility']is False
            interval=.25 if job['role']=='training'and(d.get('recovery_active')or owner!=last_owner)else .5
            last_owner=owner
            capture=float(label['capture_s'])
            if uid in seen or capture-last_sample<interval-1e-6:continue
            seen.add(uid);last_sample=capture
            frame=dict(label,world_seed=scenario['world_seed'],path_seed=scenario['path_seed'],role=job['role'],index=selected,
                original_frame_index=row['frame_index'],source_episode=str(ep),source_capture_uid=uid,
                split_unit='world',actual_command_owner=owner,labels_drive_actions=False,
                marker_evidence_scope='Visible paint geometry count, confirmed by actual cyan contrast near projected center; not metric landing authorization')
            for inst in frame['instances']:
                evidence=actual_paint_evidence(rgb,inst)
                inst['marker_head_loss_available']=evidence is not None
                if evidence is not None:inst['visible_marker_evidence_pixels_annotation_only']=evidence
            images.resize(selected+1,axis=0);text.resize(selected+1,axis=0)
            images[selected]=rgb;text[selected]=json.dumps(frame,separators=(',',':'),allow_nan=False)
            labels.append(frame);selected+=1
        assert selected>=8 and joined>0
        target.attrs.update(schema='mujoco.perception_admitted.v1',role=job['role'],teacher_actions=False,
            action_targets_admissible=False,source_episode=str(ep),production_contract_sha256=sha(OUT/'contract.json'),
            admission_scope='supervised image labels only; no teacher/deployment qualification')
    receipt=dict(schema='mujoco.perception_admission.v1',status='admitted_for_perception_only',role=job['role'],
        world_seed=scenario['world_seed'],source_episode=str(ep),source_recording_role='curriculum_candidate',
        source_H5_eligibility_unchanged=True,source_training_eligible=False,
        contract_sha256=sha(OUT/'contract.json'),plan_sha256=sha(OUT/'plan.json'),
        capture_annotations_sha256=sha(ep/'capture_annotations.jsonl'),source_trace_sha256=sha(ep/'steps.jsonl'),
        total_rows=total,exact_image_joins=joined,frames=selected,path=str(dest/'images.h5'),sha256=sha(dest/'images.h5'),
        command_owners=owners,actual_command_history_matches=all_history_matches,
        outcome=summary['outcome'],learner_success_claimed=False,teacher_demonstration_qualified=False,
        old_review_data_admitted=False,action_targets_admissible=False,heldout_used=False,tidewater_used=False,
        consumer_source_sha256=sha(__file__))
    # False source_training_eligible is preserved, not a claim it was changed.
    receipt['source_H5_eligibility_unchanged']=True
    (dest/'admission.json').write_text(json.dumps(receipt,indent=2));return receipt
def main():
    from training_quarantine_guard import assert_training_not_quarantined
    assert_training_not_quarantined(ROOT)
    assert not(OUT/'harvest_state.json').exists();CACHE.mkdir(exist_ok=False)
    contract=json.loads((OUT/'contract.json').read_text());plan=json.loads((OUT/'plan.json').read_text())
    assert sha(OUT/'plan.json')==contract['plan_sha256']and contract['action_targets_admissible']is False
    frozen=OUT/'producer_snapshot';receipt=json.loads((frozen/'producer_source_hashes.json').read_text())
    assert receipt['scope']=='staged_perception_only' and receipt['contract_sha256']==sha(OUT/'contract.json')
    for relative,digest in receipt['files'].items():
        path=(frozen/relative).resolve();assert path.is_relative_to(frozen.resolve())
        assert sha(path)==digest,'Frozen producer source changed: '+relative
    jobs={j['name']:j for j in plan['jobs']};done={};start=time.monotonic()
    save(status='waiting_on_closed_episode_events',completed=0,producer_sources_verified=len(receipt['files']))
    libc=ctypes.CDLL(None,use_errno=True);fd=libc.inotify_init1(os.O_NONBLOCK)
    if fd<0:raise OSError(ctypes.get_errno(),'inotify_init1')
    watch=libc.inotify_add_watch(fd,str(OUT).encode(),0x80|0x8) # moved-to and close-write
    if watch<0:raise OSError(ctypes.get_errno(),'inotify_add_watch')
    try:
        while True:
            state=json.loads((OUT/'collection_state.json').read_text())
            for item in state.get('completed',[]):
                name=item['name']
                if name in done:continue
                save(status='admitting_closed_episode',episode=name,completed=len(done))
                done[name]=harvest(jobs[name],contract,plan)
                save(status='waiting_on_closed_episode_events',completed=len(done),frames=sum(r['frames']for r in done.values()),wall_s=time.monotonic()-start)
            final=state['status']in ['collection_closed_needs_perception_admission','failed']
            if final:
                manifest=dict(status='completed'if state['status']!='failed'else'partial_upstream_failed',entries=list(done.values()),
                    contract_sha256=sha(OUT/'contract.json'),plan_sha256=sha(OUT/'plan.json'),
                    frames=sum(r['frames']for r in done.values()),heldout_used=False,tidewater_used=False,teacher_actions_used=False)
                (CACHE/'manifest.json').write_text(json.dumps(manifest,indent=2));save(status=manifest['status'],frames=manifest['frames'],completed=len(done));return
            # Only relevant atomic collection-state writes wake the scan; ignore
            # our own harvest receipts so this cannot become a busy self-loop.
            while True:
                if not select.select([fd],[],[],60)[0]:break
                data=os.read(fd,65536);offset=0;relevant=False
                while offset+16<=len(data):
                    wd,mask,cookie,length=struct.unpack_from('iIII',data,offset);name=data[offset+16:offset+16+length].split(b'\0',1)[0]
                    relevant|=name in[b'collection_state.json',b'staged_manifest.json'];offset+=16+length
                if relevant:break
    finally:os.close(fd)
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
