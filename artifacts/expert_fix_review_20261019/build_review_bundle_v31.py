"""Export only the closed replacement review evidence, never training data."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z');BASE=ROOT/'expert_fix_review_20261019';DEST=BASE/'delivery_v31'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not DEST.exists();DEST.mkdir()
    cases=[];files={}
    for i in range(1,13):
        case=f'E{i:02d}';revision='v31'if case in ['E01','E03']else'v31_full';out=BASE/revision;ep=out/case
        state=json.loads((out/'packaging_v2_state.json').read_text());assert state['status']=='completed_needs_visual_review'
        result=json.loads((ep/'preview_result.json').read_text());audit=json.loads((out/(case+'_audit.json')).read_text())
        assert result['teacher_only'] and result['mode']=='expert' and not result['training_eligible']
        assert result['outcome']==('home_landed'if case=='E12'else'landed')
        assert not audit['command_history_mismatches']and not audit['unsupported_descent']and not audit['metric_wrong']
        assert audit['valid_images']==audit['exact_valid_rgb_joins']
        assert set(audit['owners']).issubset({'expert','evaluation_fault'})
        if case in ['E03','E04','E05','E10','E11']:assert audit['actual_fault_rows']
        clips=[]
        for receipt in state['deliveries']:
            if Path(receipt['source_episode']).resolve()!=ep.resolve():continue
            path=Path(receipt['video']);assert path.is_relative_to(BASE)and sha(path)==receipt['video_sha256']and path.stat().st_size==receipt['bytes']
            rel=path.relative_to(BASE).as_posix();clips.append(dict(path=rel,receipt=receipt))
            for item in [path,path.with_name(path.stem+'_video_receipt.json')]:files[item.relative_to(BASE).as_posix()]=item
        assert clips
        for item in [ep/'preview_result.json',ep/'summary.json',ep/'scenario.json',ep/'native_hook_bindings.json',out/(case+'_audit.json'),out/(case+'_actual_rgb.jpg')]:
            assert item.exists();files[item.relative_to(BASE).as_posix()]=item
        cases.append(dict(case=case,revision=revision,clips=clips,outcome=result['outcome'],teacher_only=True,
            counterfactual_expert_only_vs_old_mixed_case=case in ['E09','E10','E11'],actual_fault_frames=len(audit['actual_fault_rows']),training_eligible=False))
    for revision in ['v31','v31_full']:
        for name in ['state.json','pilot_visual_review.json','alignment_comparison_v2.json','source_hashes.json','plan.json','runtime_probe.json']:
            item=BASE/revision/name
            if item.exists():files[item.relative_to(BASE).as_posix()]=item
    sources=BASE/'v31/sources'
    for item in sources.rglob('*.py'):files[item.relative_to(BASE).as_posix()]=item
    item=sources/'source_hashes.json';files[item.relative_to(BASE).as_posix()]=item
    manifest=dict(schema='expert.replacement.review.v31',training_eligible=False,human_approval=False,
        all_original_quarantines_retained=True,training_or_production_modified=False,
        actor_only_inputs='RGB, own telemetry/encoders, declared static priors; no radio or hidden task truth',
        interpretation='Matched developmental teacher demonstrations, not independent policy reliability or proof of generalization. E09-E11 are explicitly expert-only counterfactuals, not learner rescues. E04a is detail from the same E04 recording.',
        cases=cases,files={name:dict(sha256=sha(path),bytes=path.stat().st_size)for name,path in files.items()})
    meta=DEST/'corrected_expert_review_v31_manifest.json';meta.write_text(json.dumps(manifest,indent=2));files['corrected_expert_review_v31_manifest.json']=meta
    archive=DEST/'corrected_expert_review_v31.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=3)as z:
        for name,path in files.items():z.write(path,name)
    receipt=dict(archive=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,files=len(files),training_eligible=False)
    (DEST/'corrected_expert_review_v31_bundle_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
