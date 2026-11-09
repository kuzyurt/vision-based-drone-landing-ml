"""Package a completed, audited candidate separately; never overwrite evaluation."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tarfile
ROOT=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    state=json.loads((ROOT/'qualification_r7_state.json').read_text())
    assert state['status']=='qualified_pending_evidence_audit',state
    before=json.loads((ROOT/'provenance_audit_r7.json').read_text())
    subprocess.run([sys.executable,str(ROOT/'audit_provenance_r7.py')],check=True,cwd=ROOT)
    cohorts=['extended_development_spatial_r7','target_unavailable_spatial_r7','fresh_holdout_spatial_r7']
    for c in cohorts:subprocess.run([sys.executable,str(ROOT/'audit_flight_results_r7.py'),c],check=True,cwd=ROOT)
    audits={c:json.loads((ROOT/c/'evidence_audit.json').read_text()) for c in cohorts}
    assert audits[cohorts[0]]['outcomes']=={'landed':8}
    assert audits[cohorts[1]]['outcomes']=={'home_landed':6}
    final=audits[cohorts[2]];assert final['planned']==60 and final['outcomes'].get('landed',0)>=57
    assert not any(final['outcomes'].get(k,0) for k in ['collision_failure','water_strike','infrastructure_error','worker_error'])
    provenance=json.loads((ROOT/'provenance_audit_r7.json').read_text())
    assert before['physics_sources']==provenance['physics_sources'],'Physics source changed during qualification'
    assert before['operational_sources']==provenance['operational_sources']
    for name,h in provenance['physics_sources'].items():assert sha(Path(name))==h
    output=ROOT/'qualified_delivery_r7';output.mkdir(exist_ok=False)
    shutil.copytree(ROOT/'bundle_spatial_r7',output/'candidate',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(ROOT/cohorts[2]/'mission_sources',output/'evaluated_operational_sources')
    reports=output/'reports';reports.mkdir()
    for c in cohorts:
        dst=reports/c;dst.mkdir()
        for f in ['report.json','evidence_audit.json','plan.json']:shutil.copy2(ROOT/c/f,dst/f)
        for x in audits[c]['details']:
            if x['outcome']!='landed' and c!=cohorts[1]:
                src=ROOT/c/x['name'];case=dst/x['name'];case.mkdir()
                for f in ['summary.json','result.json','controller.json','scenario.json']:shutil.copy2(src/f,case/f)
    for name in ['provenance_audit_r7.json','fresh_holdout_B60.json','fresh_holdout_B60.sha256','qualification_r7_state.json','bundle_spatial_r7_qualification_sources.json']:
        shutil.copy2(ROOT/name,reports/name)
    history=reports/'previous_candidate_r5_first_fresh_suite';history.mkdir()
    for f in ['report.json','evidence_audit.json']:
        shutil.copy2(ROOT/'fresh_holdout_spatial_r5'/f,history/f)
    shutil.copy2(ROOT/'holdout_A_retirement_decision.json',history/'retirement.json')
    training=output/'training_provenance';training.mkdir()
    for name in ['result.json','history.json','consumed_sources.json','plan.json']:shutil.copy2(ROOT/'spatial_acquisition_training'/name,training/name)
    k=final['outcomes']['landed'];lo,hi=final['nominal_wilson_95_interval']
    text=f'''# Qualified simulation candidate R7

Fresh frozen no-radio suite: **{k}/60 boat landings ({100*k/60:.1f}%)**.
Outcomes: {json.dumps(final['outcomes'])}. Zero collision/water-strike outcomes.
Earlier inspected development:8/8 landings. The preceding R5 candidate achieved
56/60 on its first fresh suite (2 home landings,1 abort,1 timeout). That suite was
explicitly retired to development before fixes; this R7 rate uses a separately
frozen set of30 new worlds. The short stopped R6 diagnostic is not a success claim. Separate visually absent target
checks:6/6 physical home landings; these are not counted as boat landings.

This is learned RGB localization/pose plus visual marker registration, explicit
acquisition/tracking/landing control and native PX4. It is not end-to-end neural
actions or RL. The locator was trained from existing approved training/validation
recordings only. The main pose checkpoint and original data/checkpoints remain
preserved. Task expert commands were zero and the entire radio packet was removed
before the runtime, on every audited task frame.

The final suite spans five MuJoCo maps,30 new worlds/two route directions, moving
boats, varied water/sky/light/wind/waves<=5cm,3–60m starts, including
{final['inland_cases']} over-land starts. {final['initial_camera_target_cases']}/60
initial cameras were aimed toward the boat during setup; the rest were not.
The same boat/painted marker geometry is used throughout. All final flights are
180s-budget cases; no outcome was used to train or tune this candidate.

Boat landing still requires physical support from>=3 feet, COM inside support
polygon, all feet within.28m of pad centre, relative horizontal speed<.1m/s,
vertical<.05m/s, tilt<5deg/angular rate<5deg/s, and>=2s stable disarmed contact. PX4
disarmed normally; no forced-disarm shortcut. Home scoring is separate.

The nominal descriptive Wilson95% interval is {100*lo:.1f}–{100*hi:.1f}%; route
directions share worlds, so observations are correlated. This measured simulation
result does not establish universal or real-hardware reliability. GNSS HIL and
camera encoders are simulation references pending hardware calibration. Radio-free
home fallback uses a declared home sampled from own PX4 while disarmed, and a time
budget; it is not a calibrated battery-SOC reserve guarantee.

## Using the evaluated system

Use `candidate` inside the existing VM Python/repository environment. Its Linux
native marker library is built for that environment. Instantiate
`RadioRobustRuntime(pose.pt,calibration,slew_limits,'cuda',allow_visual_landing=True)`
and wrap it with `MissionSafety` from the byte-identical evaluated operational
sources. Provide actual own-home/preparation telemetry through `HomeReference`;
the mission wrapper requires an explicitly authorized home. Remove boat radio
input before each act call. Loading pose.pt alone does not reproduce the complete
evaluated system. The exact evaluation loader/setup is preserved in
`evaluated_operational_sources/evaluate_development.py`; simulator truth used by
setup/scoring must never be passed to the task runtime.

All original experiments/failed revisions and full RGB/trace evidence remain in
the VM experiment directory. This compact package includes candidate weights,
source, frozen plans, reports, trace hashes and training provenance; raw episodes
are intentionally retained in place on the VM.
'''
    (output/'RESULTS.md').write_text(text)
    manifest={str(p.relative_to(output)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    archive=ROOT/'qualified_delivery_r7.tar.gz'
    with tarfile.open(archive,'x:gz') as tf:tf.add(output,arcname=output.name)
    receipt=dict(status='qualified_evidence_audited',archive=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),outcomes=final['outcomes'],boat_landing_rate=k/60,
        original_recordings_preserved=True,raw_rgb_on_vm=True,qualified_output=str(output))
    (ROOT/'qualified_delivery_r7_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
