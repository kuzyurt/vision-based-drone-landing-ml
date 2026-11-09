"""Event-driven compact experimental evidence export. NEVER qualifies/promotes."""
from pathlib import Path
import datetime,hashlib,json,os,select,zipfile
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'experimental_delivery_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    p=OUT/'state.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**v),indent=2));t.replace(p)
def main():
    OUT.mkdir(exist_ok=False);baseline_root=ROOT/'retired_matched_baseline_v1'
    pid=json.loads((ROOT/'retired_matched_baseline_v1_launch.json').read_text())['pid'];save(status='waiting_for_closed_retrospective_baseline',coordinator=pid)
    try:fd=os.pidfd_open(pid)
    except ProcessLookupError:fd=None
    if fd is not None:
        try:select.select([fd],[],[],6500)
        finally:os.close(fd)
    candidate=json.loads((ROOT/'frozen_task_evaluation_v3/state.json').read_text());baseline=json.loads((baseline_root/'state.json').read_text())
    assert candidate['status']=='retired_57_of_60_unreachable'and baseline['status']!='running'
    results=candidate['results'];pairs=baseline.get('results',[])
    table=['| Scenario | Condition | Candidate | Time | Original baseline | Time |','|---|---|---|---:|---|---:|']
    for r in results:
        a=r['audit'];b=next((p['baseline']for p in pairs if p['job']['name']==r['job']['name']),None)
        table.append(f"| {r['job']['name']} | {r['job']['map']}, {r['job']['category']} | {a['outcome']} | {a['final_task_s']:.2f}s | {b['outcome']if b else'not completed'} | {format(b['final_task_s'],'.2f')+'s'if b else'—'} |")
    report='''# MuJoCo target discrimination and recovery — experimental results

**The new candidate did not meet the reliability goal and is not approved for deployment.**

We added artificial water glare, different boats, copied-cross boards and other
objects in MuJoCo, then separated whole-boat identity, unknown objects, visible
marker and permission to descend. Tidewater images were not used for training
or model selection.

We implemented observable search/tracking, bounded visual memory and guarded
close-range recovery. After a real camera tilt disturbance, the complete new
candidate lost the pad, stopped descending, climbed from about1.39m to3.12m,
reacquired it and physically landed/disarmed. Three selected development flights
landed in64.60s,79.44s and95.60s. These are development examples, not reliability
statistics. The latest stale-hypothesis helper never fired in those three
successes, so it cannot be credited with causing them.

The DAgger recording/takeover system distinguishes learner, shadow teacher,
executed safety/fault commands and assisted outcomes. Bulk collection stopped
after the preserved original learner actually descended onto a copied-cross
board. A qualified large rescue/action-imitation dataset was not delivered.
Instead, exact capture-bound correct visual labels from nine staged recordings
were admitted for perception only:1,544 new images,846train/698validation across
five island/beach worlds, mixed with original MuJoCo data. Six fine-tuning epochs
took40.79s; epoch2 was retained. The boat verifier changed; the original pose/
spatial models stayed intact. Explicit controller changes are not learned actions.

The independent physical qualification was stopped after **one boat landing and
four physical safe-home landings in five completed boat missions**. Four missed
boat landings make57/60 unreachable. This early-stopped sample is not a general
20% accuracy estimate. Started but interrupted and never-started missions are
not scored as completed trials. No collision was observed in the five completed
candidate missions. The separate10-flight no-target qualification was not run;
one earlier no-target development flight did physically return home/disarm.

## Completed trials and retrospective comparison

'''+ '\n'.join(table)+'''

Flight times are simulation task time. Native PX4 preparation/camera histories
can vary between runs; same scenarios do not mean identical RGB. The original
baseline comparison is retrospective on the retired set, not a fresh benchmark
or model-selection set. Incomplete baseline pairs are explicitly unscored.

## Why the broader candidate failed

Both60m inland failures had no allowed horizontal approach throughout all2,500
search frames: the existing inspection guard requires the drone to already be
over a water corridor. There is no certified land-to-water search transition.
Removing that guard blindly would be unsafe: the actual static terrain includes
cliffs that can exceed the permitted altitude. A terrain/obstacle-certified
transition planner is required.

Water-start failures repeatedly scanned/reoriented weak nearby hypotheses while
the real boat was only briefly visible at low input resolution. One beach case
moved only3.46m; another0.45m. The new negative-view helper did execute, but did
not produce successful search. All selected hypotheses were already from the
original boat-like proposal channel; simply filtering distractor-channel peaks
does not explain these failures. The next work should join calibrated objectness,
unknown/identity evidence and deliberate spatial search coverage, then collect
genuine approach/inspection examples under that corrected planner. Longer timers
or more blind epochs are not an established fix.

The original80% cold-frame recognition gate remains FAILED. At the selected
zero-observed-false validation point, the new verifier's cold recall was54.2%
on original validation images and34.6% on new ones. These are image metrics,
not landing rates or proof of universal boat recognition. The positive
development examples did not justify overriding the failed broader test.

## Remaining work and limits

The57/60 fresh boat goal,10/10 separate fallback suite, fresh Tidewater transfer
comparison and game integration remain unfinished. No reliable replacement is
being installed. This export preserves an experimental checkpoint, exact sources,
failed evidence and reports for continuation. Failed/retired evaluation images
remain excluded from training and must never be called fresh after tuning.

The system is learned vision plus geometric registration/tracking, explicit
control and native PX4. Task actions use RGB, own telemetry/encoders and declared
static priors. Simulator annotations and physical scoring stay separate. This
is not end-to-end neural motor control, RL, real-hardware qualification or a
crash-proof claim. Original recordings, checkpoints and approvals are preserved.
'''
    (OUT/'RESULTS.md').write_text(report,encoding='utf-8')
    decision=dict(status='EXPERIMENTAL_NOT_QUALIFIED',goal_achieved=False,production_promotion=False,
        candidate_state=candidate['status'],candidate_completed=len(results),candidate_boat_landings=sum(r['audit']['physical_success']for r in results),
        candidate_home_instead_of_boat=sum(r['audit']['outcome']=='home_landed'for r in results),
        baseline_status=baseline['status'],baseline_completed=len(pairs),
        remaining_separate_home_suite=10,tidewater_external_benchmark_completed=False,new_tidewater_training_images=0,
        recognizer_sha256=sha(ROOT/'perception_training_v24/best.pt'),
        original_cold_gate_passed=False,all_originals_preserved=True)
    (OUT/'DECISION.json').write_text(json.dumps(decision,indent=2))
    files=[OUT/'RESULTS.md',OUT/'DECISION.json',ROOT/'perception_training_v24/best.pt',ROOT/'perception_training_v24/result.json',
        ROOT/'frozen_task_evaluation_v3/state.json',ROOT/'frozen_task_evaluation_v3/candidate_binding.json',ROOT/'frozen_task_evaluation_v3/development_home_audit.json',
        ROOT/'frozen_task_suite_v2/plan.json',baseline_root/'state.json',baseline_root/'plan.json',ROOT/'frozen_task_postmortem_v1/report.json',ROOT/'frozen_task_postmortem_v1/public_search_diagnosis.json']
    files += list((ROOT/'frozen_task_postmortem_v1').glob('*_actual_rgb.jpg'))
    files += list((ROOT/'candidate_development_v25').glob('*_actual_rgb.jpg'))
    files += [ROOT/'candidate_recovery_v25/actual_fault_window_v2.jpg',ROOT/'candidate_recovery_v25/actual_fault_window_v2.json']
    files += list((ROOT/'frozen_task_evaluation_v3/source_snapshot').rglob('*.py'))
    files += list((baseline_root/'source_snapshot').rglob('*.py'))
    files += list((ROOT/'frozen_task_suite_v2').glob('*_scenario.json'))+list((ROOT/'frozen_task_suite_v2').glob('*_job.json'))
    for r in results:files.append(ROOT/'frozen_task_evaluation_v3'/r['job']['name']/'physical_audit.json')
    for p in pairs:files.append(baseline_root/p['job']['name']/'physical_audit.json')
    files=list(dict.fromkeys(p for p in files if p.exists()))
    manifest={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in files}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    archive=OUT/'experimental_evidence.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=4)as z:
        for p in files:z.write(p,p.relative_to(ROOT))
        z.write(OUT/'manifest.json','experimental_delivery_v1/manifest.json')
    receipt=dict(archive=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),files=len(files),decision=decision)
    (OUT/'archive_receipt.json').write_text(json.dumps(receipt,indent=2));save(status='experimental_export_ready_not_qualified',receipt=receipt)
if __name__=='__main__':
    try:main()
    except BaseException as e:
        if OUT.exists():save(status='failed',error=repr(e))
        raise
