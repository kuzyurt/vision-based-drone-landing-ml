from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parent;p=r/'STATUS.md'
text=f'''# Latest ACTIVE R15 pipeline — {datetime.now(timezone.utc).isoformat()}

R15 five-case development pilot443763 and event coordinator443764 RUNNING, launched
12:53:22UTC. State resumed_r15_state.json; receipt r15_pipeline_receipt.json;
r15_pilot5/report.json/log, continue_r15_native.py/log. Candidate frozen SHA
5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35.
Use current states/processes; never duplicate. Five concurrent cases include the
pairedgravel case +four necessary regressions, avoiding wasteful1thenidentical5.
Coordinator requires5/5boat +source/input/physical/veto audits +actualstopping/
memory/calibratedterminalbranches before untouched fullE60>=57/60zero, then
safetyE10=10/10physicalhome. Existing --record-all-rgb preserves actualcameraevidence
in fresh/safety (841GiBfree at12:46). Sourceworldplan/physics/thresholds unchanged.
All prior old cutoffs historical; human resumed11:42UTC, ongoing authorization.

Full R15 RadioRobustRuntime recordedRGB proof PASSED1363frames:229persistentvelocity
and124newterminal-motionveto frames, minimumderivedspeedlimit.0163m/s;43.2wallsec.
No flight claim. r15_runtime_terminal_motion_probe.json. Newlimit fromfinal-camera
projectionJacobian, halfexisting108pixelradius andactualimageage+.4s; neverloosens
old.08m/s max. Same3cmgate/strictlanding/disarm/physics/learnedweights unchanged.

R14 was4/5development and NOTpromoted; R14native/gamegatesexitedwithoutE or actual
browserflights. Keep all failures. OlderR13/nearR1invalidinactiveexperimentsalso
preserved; see Rule18/19. New R15 browser staging is being prepared, not promoted:
archive candidate_r15_controller.tar.gz SHA8427a30074c5f74256230f1bc6a2e8175a9c0af0000ef7c4a95c27660806b72b
onVM, not downloaded yet. Native fixed-input controller reference script
make_r15_fixed_input_reference.py RUNNING (no neural/GPU/render; reuses preserved
R14NN/acceptedRGBfitinputs only), output r15_fixed_input_controller_fixtures.json.
Need newR15browser export nearfieldmodule, computed native/Pyodide parity, then
two bounded actual production ONNX/WebGPU/WASM/Pyodide Tidewater checks AFTERfull
nativegates (unpowered +independentboatmotors .6m/s coast-route scenario). R14moving
driver helper exists; newR15sources/receipts/gate must becreated. No Windowsrender.

Production game parent still unchanged. R15 no teachercollection/neuraltraining.
Preserve all recordings/approvals/checkpoints/frozen sources/unrelated dirty edits,
independent ship controls/2.8m/s default (exceeds policy2m/s, do not silentlyslowit).
Reports must distinguish development from fresh qualification and simulation limits.
Heartbeat finish-resumed-drone-landing-hardening ACTIVE; quiet healthy progress,
handle recoverable failures autonomously. Never poll every few minutes.

'''
p.write_text(text+p.read_text(encoding='utf-8'),encoding='utf-8')
with(r/'DECISIONS.md').open('a',encoding='utf-8')as f:f.write(text)
