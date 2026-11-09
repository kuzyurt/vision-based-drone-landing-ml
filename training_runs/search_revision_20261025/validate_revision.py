"""Validate preparation without starting a collection or model-training run."""
import json
import subprocess
import sys
from common import HERE, source_receipt, write_json, utc, sha, verify_sources


def main():
    before=source_receipt()
    original=HERE.parent/'search_110gb_20261025/data/collection.json'
    verify_sources(json.loads(original.read_text())['sources'])
    results={}
    for name,args in [('tests',['test_revision.py']),('delivery',['check_delivery.py']),
                      ('model_renderer',['preflight.py','--model','--renderer']),
                      ('backend',['preflight.py','--backend']),('audit',['curate.py','audit'])]:
        p=subprocess.run([sys.executable,'-B',*args],cwd=HERE,capture_output=True,text=True,encoding='utf-8',errors='replace')
        results[name]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
        print(name, 'passed' if p.returncode==0 else 'FAILED',flush=True)
        if p.returncode:raise RuntimeError(p.stdout+'\n'+p.stderr)
    if before!=source_receipt():raise RuntimeError('Sources changed during validation')
    write_json(HERE/'validation.json',dict(status='passed',validated_utc=utc(),source_receipt=before,
        checks=results,audit_sha256=sha(HERE/'audit.json'),delivery_checks_sha256=sha(HERE/'delivery_checks.json'),
        original_recordings_modified=False,training_started=False))


if __name__=='__main__':main()
