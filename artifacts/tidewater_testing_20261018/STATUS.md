# COMPLETE — Tidewater-only evaluation, 18 October 2026

All26newflights completed and audited:18difficultcases0landed;8initiallyvisible
diagnosticflights5landed. ZERO registeredcollisions/GPUerrors. No training,policy
changes,physics/scoringchanges,Windowsrendering ornewbuild. Sources/hashes intact.
Withradio measured1.003/1.004m/s LANDED43.34/51.588s across2starts;1.350m/sfailed175.072s.
Without measured.349m/s landed35.86s thenFAILED175.064s fromchangedstart;.644failed175.052s.
Unpowered no-radio landed37.148s. Radio.643landed41.14s. No universal maximum
established. Priorcloser-start no-radio.63mean/47.7s remainsvalidseparatehistory:
do notclaimabsolute no-radio limit.35 basedonthisnewprotocol.

Maincauseevidence:17/18hardcases ZERO acceptedmetricposes,oneonly1;all3failed
visible-startcases ZERO. Eachsuccess690–943 acceptedmetricframes. Allfailedbody
height>=1.673m; no hidden boat truth/teacher taskactions. Actualradio inputs audited.
Postprocessinitialassertstrict2m/snorm disproved:existingperaxis slewafterclip
mixescomponents, observedmax2.043744m/s, allfinite. Originalfailedexportpreserved;
export_results_v2.py recordsit honestly withoutpolicy/scoringchanges.

21,019,690bytecompactarchive SHA f8f2032c449388a363561902e8464babacc8781befcfc3c5ea66423c4a68523d
downloaded;all144fileshashverified under verified/. Fulltraces/images remainVM.
German finalreport landing_training/docs/reports/TIDEWATER_TEST_RESULTS_2026-10-18.md;
completion_receipt.json, audited_results.json, sourceplans/snapshots preserved.
Current-policy docs/READMEs updatedwithbackups underdocs_before_test_report/.
No recurringautomationcreated; oldhardeninggoal stayshistoricallycomplete.
No additionaltesting/training/fixes authorized orpending for thiscompletedrequest.

## Historical progress notes below

# Active Tidewater-only evaluation — 18 October 2026

User explicitly requested more difficult Tidewater game tests and a measured boat
speed limit, both with and without radio. Testing only: no policy changes,
training, new teacher collection, physics/scoring changes or Windows rendering.
Current immutable R15 policy SHA5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35.

Verified SSH hxhshsh7gyg@34.87.180.165; hostdrone-test2-20261015-183521.
Use C:/Users/gamee/.ssh/id_ed25519 with BatchMode=yes,StrictHostKeyChecking=yes,
IdentitiesOnly=yes; never display keys. Remote root:
/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/landing_hardening_20261018T011610Z.

FIRST run tidewater_speed_20261018T152500Z COMPLETED18/18 at16:07UTC:
ZERO boat landings, ZERO registered game contact/rotor collisions, noGPUerrors.
Six requested speeds.6/1/1.4/1.8/2.2/2.8 eachwith/without radio, low~2mtruebody
height/~9mbehind/35degtilt start. InitialactualRGB containsonlywater (verified).
Also6harder starts: close/oblique/wind,~21mcloudy4.5mheight/lookaway,~41mlate
6.5mheight/lookaway/wind, eachwith/without radio. Missiondeadline or bounded
recovery restores manualhold; not boat success or native home landing.
All18complete and preserved; do not repeat them. Local measured_state.json under
artifacts/landing_hardening_20261018/tidewater_speed_20261018T152500Z/.

SECOND CURRENT run tidewater_limits_20261018T153300Z, coordinator485019,
run_suite_v2.py,state.json,coordinator.log. It imports ALL18completed priorcases;
do not confuse totalcompleted with newcompleted. No predecessor work remains.
Installer's first old-PID lookup failed because original alreadycompleted;
corrected installer receipt honestly records completed predecessor/no interrupted
flights, no duplicate collection. Driver frozenSHA0238d2db...de51a sameasfirst;
onlydeclared caseparameters differ. Same actual Tidewater geometry/graphics,
production ONNX-WebGPU/WASM/Pyodide/MuJoCo/PX4 stack; headlessNode scheduling.

Dedicated speed starts:4mmanualtarget/~4.5mactualbody,8mback,pan0/tilt20.
ActualfirstRGB checked: boat clearly visible. Adaptive per radio mode:
.6 ->1.4 ->2.2 ->2.8 onlyafter demonstratedsuccess; stopfirstfailedhigherpoint,
one boundarymidpoint then changed-start confirmation (10mback/4.5mtargetheight).
If.6fails, unpoweredboat diagnostic; onlyifthatlands try.3, thenconfirmation.
Max6flightspermode. Existing18hardcases NOT repeated. Speed success requires
originalphysicalstable/disarmedboatlanding AND final2.1smeanspeed>=.85requested,
minimum>=.75requested; alwaysreportactualspeed,notonlymotorrequest. Defaultsboat
2.8cruise/policy2m/snorm cap unchanged. Newcriteria only classify speed evidence,
never weaken existing physical landing scoring.

Latest verified newresults:
- visible_0p6_radio:LANDED41.14simulatedseconds; finalmeanspeed.643456m/s,
  min.642136/max.644721. Radio condition exercised.
- visible_0p6_visual:FAILED175.052s,missiondeadline/manualhold; finalspeed.643624.
Other tests stillrunning; do not assume results. User informed18stressfailed and
the mixed .6result. No training/fixing authorized by this task.

Local sources under artifacts/landing_hardening_20261018/tidewater_limits_20261018T153300Z/.
An SSH event watcher (session63655) waits oninotify/pidfd,not periodicpolling;
on completed newflights prints shortsummary. Wait<=55s pertoolcall with
functions.exec firstline yield_time_ms60000 toavoid extra yieldcells.
If watcherexits, read actualstate/logs and ownedprocesses, do not duplicate work.

After newrun completed, execute its export_results.py onVM (alreadyuploaded).
It audits everyactualinput/action/radio/phase/collision sample and hashes, writes
audited_results.json andcompact_results.tar.gz +download_receipt.json. FullRGB
snapshots/traces remainVM. Downloadcompactarchiveunder5min, verifySHA/safeextract,
read phase/metric/bodyheight diagnostics beforeexplaining failures. Originalgame
collision scorer does not explicitlyscoreoceanwater; report registeredcollisions
accurately and examine minimum truebodyheight separately, no fabricatedwaterproof.
Then write new dated German report/table incl failedcases and highesttested
actual contact speeds, note sample/geometrylimits, no broadreliability claim.
Update currentpolicy docs with newTidewaterstresslimits without overwriting old
reports or pretending native58/60haschanged. No newbuild needed; production is
unchanged. No recurringautomation wascreated; previoushardeningheartbeat deleted.
