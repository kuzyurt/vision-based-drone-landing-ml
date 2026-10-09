"""The optimized benchmark must retain reports and reap its spawned readers."""
from argparse import Namespace
import contextlib
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import psutil

from .test_training import fixture
from . import compare_training
from ..gate import file_hash


class ComparisonChecks(unittest.TestCase):
    def test_cuda_requirement_keeps_failure_report(self):
        with tempfile.TemporaryDirectory() as directory:
            args=Namespace(output=directory,device='cuda')
            with patch.object(compare_training.torch.cuda,'is_available',return_value=False),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(compare_training.compare(args),2)
            report=json.loads((Path(directory)/'report.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertIn('CUDA unavailable',report['error'])

    def test_signal_during_parallel_cache_preparation_preserves_review_and_reaps_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bundle=fixture(root);output=root/'benchmark'
            source=bundle/'one/observations.h5';before=file_hash(source);children=[]
            with (root/'console.log').open('w') as log:
                child=subprocess.Popen([sys.executable,'-m','landing_training.benchmarks.compare_training',
                    '--review',str(bundle),'--output',str(output),'--device','cpu','--no-pretrained',
                    '--cpu-threads','1','--sequence-steps','1','--lanes','1','--warmup-updates','0',
                    '--updates','1','--validation-chunks','1','--reader-workers','2','--min-phase-seconds','10',
                    '--max-minutes','2'],stdout=log,stderr=subprocess.STDOUT)
                try:
                    deadline=time.monotonic()+30
                    while time.monotonic()<deadline:
                        if child.poll() is not None:self.fail((root/'console.log').read_text())
                        children=psutil.Process(child.pid).children(recursive=True)
                        if len(children)>=3 and 'STAGE: feature preparation' in (root/'console.log').read_text():break
                        time.sleep(.05)
                    else:self.fail('Parallel cache readers did not start')
                    child.send_signal(signal.SIGTERM)
                    self.assertEqual(child.wait(timeout=20),2)
                finally:
                    if child.poll() is None:child.kill();child.wait()
            report=json.loads((output/'report.json').read_text())
            self.assertEqual(report['status'],'cancelled')
            self.assertEqual(report['signal'],signal.SIGTERM)
            self.assertEqual(file_hash(source),before)
            self.assertFalse(list(output.rglob('*.partial-*')))
            self.assertFalse(list(output.rglob('*.pt')))
            deadline=time.monotonic()+5
            while time.monotonic()<deadline and any(p.is_running() and p.status()!=psutil.STATUS_ZOMBIE for p in children):
                time.sleep(.05)
            self.assertFalse([p.pid for p in children if p.is_running() and p.status()!=psutil.STATUS_ZOMBIE])


if __name__=='__main__':unittest.main()
