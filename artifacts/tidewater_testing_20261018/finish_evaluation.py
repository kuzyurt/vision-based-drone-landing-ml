from pathlib import Path
import datetime,hashlib,json
r=Path(__file__).resolve().parent;repo=r.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
policy=repo/'tidewater-game/app/public/policy'
assert sha(policy/'manifest.json')=='b6e3a4562cb908dcdeb3a2b099513ab26d197807d90d05cd985be138edb2fe98'
manifest=json.loads((policy/'manifest.json').read_text())
for name,h in manifest['reference_adapter_sha256'].items():assert sha(policy/'reference'/name)==h,name
assert sha(policy/'pose.onnx')==manifest['model_sha256']
assert sha(policy/'marker_kernel.wasm')==manifest['marker_kernel_sha256']
report=repo/'landing_training/docs/reports/TIDEWATER_TEST_RESULTS_2026-10-18.md'
text=report.read_text(encoding='utf-8').replace('../../../artifacts/tidewater_testing_20261018/verified/audited_results.json','verified/audited_results.json')
(r/'RESULTS_DE.md').write_text(text,encoding='utf-8')
receipt=json.loads((r/'completion_receipt.json').read_text())
receipt.update(report_sha256=sha(report),finalized_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),windows_deployed_policy_hashes_unchanged=True)
(r/'completion_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
