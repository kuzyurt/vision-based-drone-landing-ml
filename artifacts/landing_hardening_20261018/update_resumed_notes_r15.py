from pathlib import Path
from datetime import datetime,timezone
r=Path(__file__).resolve().parent;p=r/'STATUS.md'
text=f'''# Latest R15 terminal-visibility work — {datetime.now(timezone.utc).isoformat()}

R14 five-case pilot COMPLETE4/5boat:front41.76s,city05incoming54.56s,city08 87.84s,
beach60m108.56s;gravelphysicalhome108.44s. All audited, no collision;5/5gateFAILED.
Nativecoordinator439795 andbrowsergate443168 EXITED. NO E60/safety/actualgameflights
run. E60 remains entirely untouched. Do not promote R14. Browser stage is only
isolated computation evidence; production parent unchanged. R14 browser1810fixed
NN/fit controller frames all phases/flags match; translationmax6.7e-13, cameratiltsolver
roundoffmax1.014e-9rad/s. Original1e-10testfailure preserved, acceptance independently
documented1e-8camera/1e-10other channels,2.24e-8pixelperdecision; physicalgatesunchanged.

ActualR14gravel: near persistentvelocity hook229frames active. Veto begins53.84s
at4.6cm footclearance while relativeXYspeed.041m/s (belowold.08limit); retained
verticalmomentum carriesclearance below3cm. Finalpixelforecast291->476, current
camera at90limit,crossleavesbottom; localrecovery54.4s thenhome58.36s. Successful
isolatednearR2alsohadmovingboat,but differentapproach/wavephase; not robust enough.
ActualRGB contact sheet r14_gravel_final_loss_actual_rgb.jpg onVM. OriginalR14all
recordings/frozen sources retained. Do not treat4/5asqualification.

New candidate_r15 BUILT/frozen SHA
5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35.
BranchesR14; ONLYextra terminal-motion veto in nearfield_visibility.py: maps planar
relativevelocity to final-view pixels using calibrated projectionJacobian at SAME
3cmgeometry. Reserve54pixels(halfexisting108inner-radius) over actualimageage +
existing.4shorizon. Speedlimit never exceedsold.08; expected~.02for160msdelay.
All old normal/position/freshfit/visibility/touchdown/disarm/physics gates unchanged.
This is stricter descent permission, not extra blind descent or a timer extension.
FullRadioRobustRuntime recordedRGB probe probe_r15_runtime.py currently RUNNING;
output r15_runtime_terminal_motion_probe.json must show>=12actualveto +>=150near
velocity frames before any R15flight. No R15flightyet. Inspectprocesses/output to
avoidduplicate replay. Then one pairedgravelpilot, actualoutcome/audits, thenfive
combineddevelopmentcases beforefullE60>=57/60zero +safety10/10 andactualbrowserflight.

Current user resumedauthorization remains active; oldcutoffs historical. No training
or newteacherdata. RenderVM only. Keep quiet routine progress, handle recoverable
failures autonomously. Existing heartbeat finish-resumed-drone-landing-hardening
stillACTIVE; update when next pipeline is actually started. Do not rerun oldstages.

'''
p.write_text(text+p.read_text(encoding='utf-8'),encoding='utf-8')
with(r/'DECISIONS.md').open('a',encoding='utf-8')as f:f.write(text)
