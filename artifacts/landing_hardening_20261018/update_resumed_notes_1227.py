from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parent;p=r/'STATUS.md'
text=f'''# Latest live corrected prototypes — {datetime.now(timezone.utc).isoformat()}

APPROACH corrected pilot437468: approach_r2_cases2,2workers, candidate_approach_r2
SHA95caee5b76059fbac2d026eab8640c8858be16d5c07ca10a6580cb049415f6a6.
NEAR corrected pilot438797 launched12:25:49UTC: near_motion_r2_gravel,1worker,
candidate_near_motion_r2 SHA77af6dc5032ccd04d52b923f44c6c7466a5d421d26aeafd49dbdd536ce44602d.
Both are separate causal development prototypes, not promoted/qualified.
Owned event reviewer439323 review_paired_prototypes.py waits both PID events and
runs source/input/physical/near-veto audits. State paired_prototype_review_state.json;
log review_paired_prototypes.log. No automatic merge/broad evaluation/promotion.
Do not duplicate any active work; inspect current states/processes first.

Corrected near FULL RadioRobustRuntime RGB replay PASSED1363frames,235activevelocity
frames, maximum commandchange.129 vsrecorded;1357/1363phase matches (commands changed).
This proves hook runs, NOT a physical improvement. near_motion_r2_runtime_branch_probe.json.
R1near was invalid inactive(.12 freshness < actual.16delay),0/243nearframesactive;
R13approach likewise invalid inactive duplicate finish. Preserve both mistakes and
audits; do not treat them as causal disproof. R2approach fullruntimeprobe114active/
29limited/7metric-handoffframes, before actual repeat. Original R12 valid failed2/5.

At next meaningful boundary inspect both corrected results/actualRGB/causaltraces.
If approach2/2boat and near1/1boat with source/physical/veto audits, merge into new
separate candidate, require5targetedcases before full untouched E60. If not, inspect
actual cause; do not blindly change thresholds or start broad suites. E60 is still
entirely untouched, production Windows game parent unchanged, no newtraining/data.
New browser stage must include approach_envelope.py and new velocity selection;
old R12 stage/parity cannot certify new sources. Full native57/60zero +safety10/10
and actual VM production ONNX/WASM/Pyodide flight remain mandatory before promotion.

Windows briefly failed spawning PowerShell (pagefile/memory OS1455); recovered by
using cmd.exe login=false for plain SSH/scriptpath commands. No user apps killed.
cmd shell quoted inline Python/rgpatterns do not parse as expected; use small saved
Python scripts via apply_patch +plain python scriptpath, and await SCP session exit
before dependent remote commands. Never render/start heavy browser on Windows.
Original ten-hour cutoff is historical; human resumed11:42UTC, ongoing authorization.

'''
p.write_text(text+p.read_text(encoding='utf-8'),encoding='utf-8')
with(r/'DECISIONS.md').open('a',encoding='utf-8')as f:f.write(text)
