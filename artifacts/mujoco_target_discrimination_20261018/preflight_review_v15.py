from pathlib import Path
import hashlib,json,os
root=Path(__file__).resolve().parent
p=json.loads((root/'perception_hard_dataset_v5/plan.json').read_text())
job=p['jobs'][0]
model=root/'hard_scene_probe_v3/hard_scene.mjb'
assert hashlib.sha256(model.read_bytes()).hexdigest()==job['model_sha256']
assert json.loads((root/'expert_visible_native_v14/preview_result.json').read_text())['outcome']=='landed'
print(json.dumps(dict(hard_model_verified=True,hard_job_keys=list(job),available_memory_kib=next(line.strip()for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:')),bulk_approved=False)))
