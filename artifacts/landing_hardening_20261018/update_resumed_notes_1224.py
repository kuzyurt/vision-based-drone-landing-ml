from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parent;p=r/'STATUS.md'
text=f'''# Latest active work — {datetime.now(timezone.utc).isoformat()}

Corrected approach_r2_cases2 pilot437468 runs2workers, launched12:21:10UTC.
Actual full-runtime recorded-RGB probe verified114active/29limited/7metric-handoff
constrainedframes. Candidate95caee5b...415f6a6. R13 was invalid inactive duplicate
method, not evidence disproving stopping constraint.

Near_motion_r1 pilot also inactive:0activeframes because .12s measurement-age
threshold shorter than actual .16s image delay. Preserve invalid test and audit;
do not call this a tested velocity hypothesis. Corrected candidate_near_motion_r2
SHA77af6dc5032ccd04d52b923f44c6c7466a5d421d26aeafd49dbdd536ce44602d requires CURRENT
accepted fit and measurement age within image_age+.021s original history tolerance,
existing established covariance gate. Full RadioRobustRuntime RGB replay
probe_near_motion_r2_runtime.py RUNNING; output near_motion_r2_runtime_branch_probe.json
must pass with>=150activeframes before any new nearflight. No nearR2flight yet.
Inspect active processes to avoid duplicate replay. User continuation remains active.

E60 untouched, no broad suites/browserflight/productionchanges. Continue after actual
corrected pilots and source/input/physical audits. Full acceptance unchanged.

'''
p.write_text(text+p.read_text(encoding='utf-8'),encoding='utf-8')
with (r/'DECISIONS.md').open('a',encoding='utf-8')as f:f.write(text)
