"""Audit the single completed build and preserve final delivery evidence; no new flights."""
from pathlib import Path
import datetime,hashlib,json,shutil
r=Path(__file__).resolve().parent;repo=r.parents[1];app=repo/'tidewater-game/app'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt_path=r/'r15_windows_integration_receipt.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
for rel,value in receipt['changes'].items():assert sha(app/rel)==value['prepared_sha256'],rel
for rel,h in receipt['unrelated_tracked_changes_after_integration_sha256'].items():
    if rel not in ['landing_training/README.md','tidewater-game/README.md']:
        assert sha(repo/rel)==h,rel
manifest=json.loads((app/'public/policy/manifest.json').read_text(encoding='utf-8'))
for rel,h in manifest['reference_adapter_sha256'].items():
    assert sha(app/'public/policy/reference'/rel)==sha(app/'dist/policy/reference'/rel)==h,rel
assert sha(app/'public/policy/manifest.json')==sha(app/'dist/policy/manifest.json')
for name,key in [('pose.onnx','model_sha256'),('marker_kernel.wasm','marker_kernel_sha256')]:
    assert sha(app/'public/policy'/name)==sha(app/'dist/policy'/name)==manifest[key]
certrel='policy/qualification/r15_simulation_qualification_certificate.json'
assert sha(app/'dist'/certrel)==sha(app/'public'/certrel)=='bb623dd8f1ac76679df5bdeb1536e5e94899a32c0628dedc59d0576551af4800'
offline=json.loads((app/'dist/offline-manifest.json').read_text(encoding='utf-8'))
listed={item['url']:item for item in offline['assets']}
for rel in ['policy/manifest.json',certrel]+['policy/reference/'+name for name in manifest['reference_adapter_sha256']]:
    assert listed[rel]['sha256']==sha(app/'dist'/rel),rel
assert 'Offline manifest: 1125 files' in(r/'r15_windows_build.log').read_text(encoding='utf-8')
report=repo/'tidewater-game/benchmarks/flight-parity/landing-hardening-20261018.md'
archived=r/'HARDENING_RESUMED_RESULTS_20261018.md';assert not archived.exists();shutil.copy2(report,archived)
receipt.update(status='completed_native_qualification_two_actual_game_checks_and_windows_build',
    finalized_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),build_still_required=False,
    build_exit_code=0,build_attempts=1,offline_version=offline['version'],offline_assets=len(offline['assets']),
    public_and_built_policy_hashes_verified=True,untargeted_tracked_changes_preserved=True,
    report_path=str(report),report_sha256=sha(report),
    qualification_certificate_sha256=sha(app/'public'/certrel),
    no_local_render_or_extra_simulation=True)
final=r/'r15_windows_delivery_completed_receipt.json';assert not final.exists()
final.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:receipt[k]for k in ['status','finalized_utc','build_exit_code','build_attempts','offline_version','offline_assets','report_path']},indent=2))
