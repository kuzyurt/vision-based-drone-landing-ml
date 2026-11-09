"""Persist latest human rejection ahead of historical autonomous instructions."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parent
NOTE='''# CURRENT HUMAN REJECTION — BUGGY EXPERT DATA QUARANTINED

2026-10-19: Human rejected the expert demonstrations as buggy and requested all
available expert situations for bug review before replacement demonstrations.
TRAINING_QUARANTINE_20261019.json rejects all 59 new recordings and experimental
derivatives/checkpoints for action AND perception reuse. Keep all originals.
Do not reinterpret earlier autonomous continuation or perception-only admission
as permission to reuse these rejected episodes. Existing fits cannot be undone;
their outputs are rejected, not silently relabeled as approved. No policy fix,
new simulation/training or promotion was performed in this review turn.

Six current admission/cache/training entry points now fail closed on the marker;
original sources backed up under quarantine_original_sources_20261019. Frozen
evaluated snapshots remain unchanged and must not be used to bypass quarantine.
EXPERT_BUG_REVIEW_20261019.md contains 13 verified clips, including four newly
exported expert-only segments (zero learner frames), plus explicit coverage gaps.
All desired curriculum situations are NOT yet demonstrated. Candidate evaluation
owner strings saying expert do not make those flights separate teacher rescues.
Next: receive concrete bug observations by review ID/time, repair separately,
show replacement demonstrations, and admit only new reviewed/qualified data.

---

'''
for name in ['STATUS.md','THINKING_RULES.md','CURRICULUM_REVIEW_CONTRACT.md']:
    path=ROOT/name
    if not path.exists():continue
    old=path.read_bytes()
    if old.startswith(b'# CURRENT HUMAN REJECTION'):continue
    backup=ROOT/'quarantine_original_sources_20261019'/(hashlib.sha256(old).hexdigest()+'_'+name);backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(old)
    path.write_bytes(NOTE.encode('utf-8')+old)
print('Latest human rejection recorded; historical instructions preserved.')
