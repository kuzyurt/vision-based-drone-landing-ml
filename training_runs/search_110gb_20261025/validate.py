"""Bind reproducible preparation checks. Never starts a collection mission."""
from pathlib import Path
import json
import subprocess
import sys
from common import HERE,sha,utc,write_json,source_receipt


def run(arguments):
    completed=subprocess.run([sys.executable,'-B',*arguments],cwd=HERE,
        capture_output=True,text=True,encoding='utf-8',errors='replace')
    if completed.returncode:
        raise RuntimeError('Validation failed: '+str(arguments)+'\n'+completed.stdout+'\n'+completed.stderr)
    return completed


def main():
    files=[p for p in HERE.iterdir() if p.suffix=='.py' or p.name in ('config.json','README.md')]
    before={p.name:sha(p) for p in sorted(files)}
    sources_before=source_receipt()
    tests=run(['test_pipeline.py'])
    model_renderer=json.loads(run(['preflight.py','--model','--renderer']).stdout)
    backend=json.loads(run(['preflight.py','--backend']).stdout)
    run(['collect.py','--preflight']);run(['train.py','--help'])
    after={p.name:sha(p) for p in sorted(files)}
    if after!=before or source_receipt()!=sources_before:
        raise RuntimeError('Sources changed during validation; rerun against a stable snapshot')
    receipt=dict(status='passed',validated_utc=utc(),unit_test_output=tests.stderr,
        model_renderer=model_renderer,backend=backend,
        source_receipt=sources_before,
        run_file_hashes=after,
        collection_mission_started=False,training_data_created=False,production_weights_changed=False)
    write_json(HERE/'validation.json',receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
