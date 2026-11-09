"""Bounded 2s native capture-path proof; no collection or training eligibility."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys,time
import h5py,numpy as np
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(**v):
    v.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),training_eligible=False,bulk_collection=False)
    p=ROOT/'v20_annotation_probe_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)
def main():
    assert not(ROOT/'v20_annotation_probe_state.json').exists()
    snapshot=ROOT/'annotation_source_snapshot_v20';snapshot.mkdir(exist_ok=False);hashes={}
    for f in [ROOT/'run_annotated_development_v20.py',*(ROOT/'target_learning').glob('*.py'),*(ROOT/'collection_pipeline').glob('*.py')]:
        d=snapshot/f.relative_to(ROOT);d.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(f,d);hashes[str(f.relative_to(ROOT))]=sha(f)
    (snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2));save(status='running_2s_native_capture_contract_probe')
    begin=time.monotonic()
    with(ROOT/'v20_annotation_native_probe.log').open('x')as log:
        subprocess.run([sys.executable,str(snapshot/'run_annotated_development_v20.py'),
            '--name','v20_actual_annotation_probe','--mode','dagger','--scene','hard','--instance','103',
            '--distance','8','--duration','120','--annotation-probe-seconds','2'],cwd=ROOT,
            stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300,
            env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only',
                 'EXPERT_RUNTIME_GATE':'expert_runtime_probe_v18_r15.json','PYTHONDONTWRITEBYTECODE':'1'})
    from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
    ep=ROOT/'v20_actual_annotation_probe';index=load_capture_index(ep/'capture_annotations.jsonl')
    rows=[json.loads(line)for line in(ep/'steps.jsonl').open()];joins=[];ages=[]
    with h5py.File(ep/'observations.h5','r')as h:
        assert not h.attrs['training_eligible']
        for row in rows:
            o=row['observation'];label=join_delivered_frame(o,np.asarray(h['rgb'][row['frame_index']]),index)
            if label:joins.append(label['capture_uid']);ages.append(o['image_age_s'])
    assert len(joins)>=45 and max(ages)>=.079,'Probe failed to exercise real delayed-frame delivery'
    assert len(set(joins))<len(joins),'Initial delayed frames must join repeated actual capture'
    receipt=json.loads((ep/'capture_annotation_receipt.json').read_text());assert not receipt['unbound_capture']
    result=dict(status='actual_native_capture_annotation_join_passed',rows=len(rows),joined_images=len(joins),
        distinct_delivered_captures=len(set(joins)),saved_captures=len(index),maximum_image_age_s=max(ages),
        receipt=receipt,wall_s=time.monotonic()-begin,teacher_qualification=False,training_eligible=False,
        native_camera_effect_binding_asserted=True,physics_and_touchdown_criteria_unchanged=True)
    (ROOT/'v20_actual_annotation_join_audit.json').write_text(json.dumps(result,indent=2));save(**result)
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
