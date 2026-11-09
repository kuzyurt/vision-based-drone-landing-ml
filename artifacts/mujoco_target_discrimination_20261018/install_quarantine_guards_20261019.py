"""Guard mutable experiment entry points; never change frozen evaluated snapshots."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
def main():
    assert(ROOT/'TRAINING_QUARANTINE_20261019.json').exists()
    files=['prepare_salvage_admission_v24.py','harvest_curriculum_v23.py','cache_curriculum_verifier_v23.py','cache_curriculum_verifier_v24.py','train_curriculum_verifier_v23.py','train_curriculum_verifier_v24.py']
    history=ROOT/'quarantine_original_sources_20261019';history.mkdir(exist_ok=True);changed=[]
    for name in files:
        path=ROOT/name
        if not path.exists():continue
        old=path.read_bytes();source=path.read_text();needle='def main():\n'
        assert needle in source,name
        if 'assert_training_not_quarantined(ROOT)'in source:continue
        backup=history/(hashlib.sha256(old).hexdigest()+'_'+name)
        if not backup.exists():backup.write_bytes(old)
        source=source.replace(needle,needle+'    from training_quarantine_guard import assert_training_not_quarantined\n    assert_training_not_quarantined(ROOT)\n',1)
        compile(source,str(path),'exec');path.write_text(source);changed.append(name)
    from training_quarantine_guard import assert_training_not_quarantined
    try:assert_training_not_quarantined(ROOT)
    except RuntimeError as e:blocked=str(e)
    else:raise AssertionError('Quarantine failed open')
    result=dict(changed=changed,guard_test=blocked,frozen_snapshots_changed=False)
    (ROOT/'quarantine_guard_receipt_20261019.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
