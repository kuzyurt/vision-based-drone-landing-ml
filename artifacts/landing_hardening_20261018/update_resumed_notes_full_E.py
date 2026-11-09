from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parent;p=r/'STATUS.md'
text=f'''# AUTHORITATIVE live full-E qualification — {datetime.now(timezone.utc).isoformat()}

R15 passed5/5targetedboatlandings +source/input/physical/nearveto audits:
front44.08s,incomingcity05 83.52s,city08 122.12s,gravel113.40s,60mbeach116.84s.
Development results are NOT independent reliability evidence. Frozen policySHA
5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35.
Native coordinator443764 now runs FIRST untouched fullE60 on8workers, evalPID446633,
began13:06:07UTC. Latest VERIFIEDsnapshot13:20UTC8/60complete,all8boatlanded;
833GiBfree. This is partial, NOTqualification. Read resumed_r15_state.json and
r15_fresh_E60/report.json/log +ownedprocesses at nextmeaningfulboundary. DoNOT
duplicate or edit frozen evaluatedsources. EworldSHA5b7840f3...5c33a unchanged;
--record-all-rgb preserves actualcamera frames. Existing eventcoordinator stops
on collision/acceptanceunreachable and requires>=57/60boat,zero collisions +all
audits/faultcoverage, then safetyE10=10/10physicalhome/5actualfaults. Originalpose
2a1cf3/spatialb432 preserved; no newneuraltraining/teachercollection.

R15 browser native/Pyodide COMPLETE controller parity PASSED1810fixedNN/fitframes,
64stopping/389memoryvelocity/201terminal-budgetframes; translationerror6.7e-13,
cameratiltoptimizerroundoff1.014e-9rad/s, documented1e-8cameratolerance vs1e-10other
channels. No fitter/neural/physicalflight claim from this computation probe.
Stage archive01f17b16...56d6ff8a /31files, manifestb6e3a456...b2fe98. ParentONNX
andmarkerWASM unchanged. R14original1e-10camera failure anddiagnostic preserved.

IMPORTANT newest actual-game gate is V2 PID452159, queue_r15_browser_gate_v2.py,
STATE r15_browser_gate_v2_state.json, LOG queue_r15_browser_gate_v2.log, waits on
native443764. Oldgate446427 was retired WHILE IDLE beforeanygameflight; do not
resume it. r15_browser_gate_v1_retirement.json proves this. V2 requires fullnative
gates/portparity/stagehashes before two bounded actual ONNX-WebGPU/WASM/Pyodide VM
Tidewater flights (unpoweredboat, independent.6m/scoast-route boat). Each max5min
runtime/360sparent cap; no longvideos. No actualgameflightyet at13:20UTC.

Additional deterministic game-handoff bug found from source: policy recovery can
reach10m, but manualHold AND next manualpilot tick forcedtarget to8m. Stagedfix
retains ownmeasuredheight, keepsnormal8mmanualceiling and gradualdescentkeys. VM
actual JS-method/PX4-setpoint boundary test PASSED:old10m->8m,new10m->10m across12
empty ticks,Rkeycannotclimbhigher,Fkey9.976m. No physicalflightclaim forcomponent
probe. SourcefileoriginalSHA0a4c8625fa188af4d2e2807f75686f595dd6910cac624ff576f9059103034d14.
Only stagedgame files changed; VM/Windowsproduction sources still untouched.
Local r15_safe_handoff_patch/; VM updated receipt vm_r15_browser_stage_v2_receipt.json;
boundary r15_safe_handoff_boundary.json. Originalstage retainedarchive+backup
r15_game_before_safe_handoff/. Newactualdrivers use stagedr15_game/BrowserPX4.js.
At futurepromotion, apply minimal2method edits to CURRENTWindowsBrowserPX4.js,
not wholeVMfile (VMstagingimports differ). Preserve unrelateddirtyedits/shipcontrols.

Useful verified local dev archive r15_pilot_verified_compact/ (646466bytes,
SHAf91abb85...958410), includes dated13:06snapshot BEFOREgame-gateV2 upgrade.
Do not mistake its oldPID446427 for currentgate452159. All fullrecordings remainVM.
Latest read-only helper inspect_r15_current.py prints identity/currentstates/
counts/processes; no tests/renders. No routine every-few-minutes polling.

NEXT: quiet healthyprogress. If native fails from policy, preserve/retireE BEFORE
tuning; never reuse it andcallfresh. If true infrastructurefailure, inspectactual
error andresumeunchangedcompletedartifacts honestly. If native+twoactualgame
checks pass, auditphysicaloutcomes/provenance/hashes, exportseparatequalification
certificate andmeasuredreport, downloadcompactverifiedartifactsunder5min, integrate
supportedpolicy andminimalJSchanges into WindowsTidewater with backups, buildonce.
Production remainsparent until evidence supportsintegration. Report finite-sample
simulationlimits, actualrates/times/failures; neverclaimcrashproof/end-to-endRL.
Then deleteheartbeat finish-resumed-drone-landing-hardening andmarkgoalonly if
actuallyachieved. User resumed11:42UTC; old11:16cutoff historical,3–5hestimate not
harddeadline. Continue autonomously; onlyfinish or genuinehumanjudgment notification.

'''
p.write_text(text+p.read_text(encoding='utf-8'),encoding='utf-8')
with(r/'DECISIONS.md').open('a',encoding='utf-8')as f:f.write(text)
