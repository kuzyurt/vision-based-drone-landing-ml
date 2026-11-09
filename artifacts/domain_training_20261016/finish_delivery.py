"""Consolidate the bounded iteration after its final flights; preserve all evidence."""
import json,shutil,sys,time,tarfile,hashlib,psutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
from collect_domain import save

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def report(name):
    p=ROOT/name
    return json.loads(p.read_text()) if p.exists() else None

def main():
    pid=report('advance_v4_launch.json')['pid']
    while True:
        state=report('v4_state.json') or {}
        if state.get('status') in ('evaluation_complete','needs_attention'):break
        try:alive=psutil.Process(pid).status() not in ('zombie','dead')
        except psutil.NoSuchProcess:alive=False
        if not alive:break
        time.sleep(20)
    original=report('evaluation_heldout/report.json');regression=report('evaluation_regression/report.json')
    final=report('evaluation_v4_final/report.json')
    v3=report('evaluation_v3_development/report.json');v2=report('evaluation_v2_development/report.json')
    final_cases=[] if final is None else final['scenarios']
    repeated=[r for r in final_cases if r['name'].startswith('development_')]
    fresh=[r for r in final_cases if r['name'].startswith('fresh_')]
    result=dict(status='bounded_iteration_finished',reliable_no_radio_goal_met=False,
        completed_unix=time.time(),main_pose_checkpoint_sha256=regression['checkpoint_sha256'],
        reference_bundle='baseline_bundle',experimental_bundle='experimental_boat_acquisition_bundle',
        original_plus_supplemental_training=True,new_demonstrations=160,training_epochs=16,selected_pose_epoch=14,
        no_radio_regression=dict(landed=regression['landed'],total=regression['planned'],outcomes=regression['outcomes']),
        no_radio_fresh_varied=dict(landed=original['landed'],total=original['planned'],percent=original['landing_percent'],outcomes=original['outcomes']),
        v2_hard_development=None if v2 is None else v2['outcomes'],v3_hard_development=None if v3 is None else v3['outcomes'],
        v4_final=dict(outcomes=final.get('outcomes') if final else None,
            previous_city_failures=dict(landed=sum(r['outcome']=='landed' for r in repeated),total=len(repeated)),
            independently_seeded_city_scenes=dict(landed=sum(r['outcome']=='landed' for r in fresh),total=len(fresh))),
        limitations=['Reference candidate achieved 75% on 20 fresh varied scenes; robust reliability target remains unmet',
            'Acquisition-head revisions have only small targeted development samples, not broad no-radio reliability qualification',
            'No test images entered neural training or checkpoint selection; repeated failure cases are explicitly regressions',
            'Hybrid learned perception, metric visual registration, explicit control and native PX4; not end-to-end neural actions or RL',
            'Infinite tilted-deck-plane clearance at long range must not be mistaken for actual altitude above water'],
        original_recordings_approvals_checkpoints_preserved=True,physics_and_touchdown_criteria_unchanged=True,
        automatic_deployment=False,followup_needed='Improve boat-visible versus marker-visible acquisition and false positives during search, then rerun broader independent scenes')
    save(ROOT/'final_results.json',result)
    out=ROOT/'delivery';out.mkdir(exist_ok=False)
    shutil.copytree(ROOT/'candidate_bundle',out/'baseline_bundle',ignore=shutil.ignore_patterns('__pycache__'))
    if (ROOT/'candidate_bundle_v4').exists():
        bundle=out/'experimental_boat_acquisition_bundle'
        shutil.copytree(ROOT/'candidate_bundle_v4',bundle,ignore=shutil.ignore_patterns('__pycache__'))
        manifest=json.loads((bundle/'policy.json').read_text());manifest.update(closed_loop_evaluated=bool(final),
            closed_loop_results=result['v4_final'],reliability_qualified=False,automatic_deployment=False,
            usage_status='experimental; targeted city flights only, broad verification still required')
        save(bundle/'policy.json',manifest)
    evidence=out/'reports';evidence.mkdir()
    groups=['evaluation_regression','evaluation_heldout','evaluation_v2_development','evaluation_v3_development','evaluation_v4_final',
            'benchmark','acquisition_training','boat_acquisition_training','training']
    for group in groups:
        directory=ROOT/group
        if directory.exists():
            target=evidence/group;target.mkdir()
            for p in directory.glob('*.json'):shutil.copy2(p,target/p.name)
    for p in ROOT.glob('*.json'):shutil.copy2(p,evidence/p.name)
    sources=out/'experiment_sources';sources.mkdir()
    for p in ROOT.iterdir():
        if p.is_file() and (p.suffix in ('.py','.cpp','.h') or p.name in ('SCIPY-LICENSE.txt','STATUS.md')):shutil.copy2(p,sources/p.name)
    last='No final V4 flight report was produced.' if final is None else f"V4 final targeted flights: {sum(r['outcome']=='landed' for r in final_cases)}/{len(final_cases)} landings. Previous city failures: {result['v4_final']['previous_city_failures']}; fresh city worlds: {result['v4_final']['independently_seeded_city_scenes']}."
    text=f'''# No-radio robustness iteration — 16 October 2026

The training iteration finished. **The requested broad reliability goal is still unmet.**

## Measured flight results

| Candidate / cohort | Landed | Outcome |
|---|---:|---|
| Reference, existing regressions including 60 m water/inland starts | 10/10 | All landed |
| Reference, 20 fresh varied scenes | 15/20 (75%) | Five aborts |
| V2, four hard validation-seed development flights | 0/4 | Four aborts |
| V3 image-only acquisition, same four hard flights | 2/4 | Gravel cases landed, city cases aborted |

{last}

Do not combine different revisions or development/fresh cohorts into one accuracy number.
Small targeted samples do not establish an almost-never-fail policy. The 75% fresh-scene
rate describes the broadly tested reference candidate only.

## Completed work

Collected 160 additional varied demonstrations using eight workers in 2 h 11 min.
Split: 120 training, 20 validation, 20 test, with independent world/path seeds by role.
Mixed them with the original 1,200-episode dataset; continued the current checkpoint for
16 epochs, selecting epoch 14 without using test images for training or selection.
Frozen image features were prepared alongside collection. All original data, approvals,
and checkpoints remain intact on the VM.

Twenty-second throughput measurements: 4 workers 32.3 aggregate frames/s; 8 workers
47.3; 12 workers 46.7; 16 workers 46.2. Eight workers gave the best measured throughput.
Equivalent FP64 physics math accelerated the physics hot path approximately 1.406× in
the short equivalence check. Native visual registration matched four recorded-frame
reference positions within 2.86e-9 m and ran about 6–9× faster. Physics, collision rules,
image resolution and final stable disarmed-contact criteria were retained.

## Remaining cause and experimental work

The main unresolved issue is visual acquisition and reacquisition under harder views,
including confident false positives and biased pixel estimates. Close landing succeeds
once continuous valid visual tracking is established. The separate image-only head
removes recurrent/telemetry shortcuts and learns balanced negative/off-centre frames.
The last revision additionally distinguishes visible boat structure from a landing
marker occluded by the boat/aircraft: teacher labels require actual cyan paint and white
hull pixels near the teacher-projected boat. These are training labels only. Runtime
receives RGB and own telemetry, with no boat radio positional/velocity signal or hidden
simulator pose. No additional demonstration collection was needed for those heads.

The system remains learned perception + calibrated geometric marker registration +
explicit velocity/yaw/camera control + native PX4. It is not an end-to-end neural action
policy and no RL was performed.

Earlier negative `clearance_m` readings far from the boat were checked against true
altitude and vertical clearance. They arose from distance to the boat's infinite tilted
deck plane; they do not demonstrate that the drone descended into the water.

## Delivered artifacts

- `baseline_bundle/`: broadly evaluated reference with documented 75% fresh-scene result.
- `experimental_boat_acquisition_bundle/`: last acquisition revision, with its limited
  targeted results clearly marked; do not treat it as broadly qualified.
- `reports/`: manifests, scores, plans, checksums, source authorization, and flight results.
- `experiment_sources/`: collection, optimization, training, runtime revision and evaluation code.

Main pose SHA256: `{result['main_pose_checkpoint_sha256']}`.
The `.so` kernels are Linux/VM builds. Rendering and physical evaluation ran on the VM.
Raw RGB recordings, every epoch checkpoint, full traces, and all failed candidates remain
at `{ROOT}`. This archive deliberately contains compact delivery artifacts rather than
hundreds of gigabytes of source recordings.
'''
    (ROOT/'RESULTS.md').write_text(text);(out/'RESULTS.md').write_text(text)
    save(out/'results.json',result)
    hashes={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}
    save(out/'SHA256SUMS.json',hashes)
    archive=ROOT/'delivery.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=3) as tar:tar.add(out,arcname='delivery')
    save(ROOT/'delivery_result.json',dict(status='completed',path=str(archive),bytes=archive.stat().st_size,sha256=digest(archive),
        goal_met=False,completed_unix=time.time()))
    print('DELIVERY_READY',archive,archive.stat().st_size,flush=True)

if __name__=='__main__':main()
