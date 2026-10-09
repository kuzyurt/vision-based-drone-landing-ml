"""Exercise real child exits/signals without requiring a GPU or approving data."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch
from argparse import Namespace

from . import cloud_collection as cloud

REAL_POPEN = subprocess.Popen


class LauncherChecks(unittest.TestCase):
    def launch(self, directory, *, qualification='pass', approved=False,termination_signal=signal.SIGTERM):
        root=Path(directory)/'landing_training';root.mkdir()
        args=Namespace(review='auto',output=str(root/'datasets/expert'))
        seen=[]
        child_pids=[]
        def start(command, **kwargs):
            stage=command[3] if command[2]=='-m' else 'approval' if 'approved_bundle' in command[3] else 'gpu'
            seen.append(stage)
            if stage=='gpu':code='print("Fixture GPU only",flush=True)'
            elif stage=='approval':code='print("/fixture/approved-review");raise SystemExit(0)' if approved else 'print("Fixture review pending");raise SystemExit(2)'
            elif stage=='landing_training.qualify':
                if qualification=='terminate_parent':
                    code='import os,signal,time; print("Qualification fixture OK",flush=True); time.sleep(.1); os.kill(os.getppid(),'+str(int(termination_signal))+'); time.sleep(10)'
                elif qualification=='fail':code='print("Qualification fixture failed");raise SystemExit(7)'
                else:code='print("Qualification fixture OK")'
            elif stage=='landing_training.review':
                output=command[command.index('--output')+1]
                code='import json;from pathlib import Path;root=Path('+repr(output)+');root.mkdir();(root/"manifest.json").write_text(json.dumps({"qualification_passed":True}));(root/"index.html").write_text("Invalid test fixture; not approved");print("Review fixture complete")'
            elif stage=='landing_training.collect':
                self.assertEqual(command[command.index('--workers')+1],'64')
                self.assertEqual(command[command.index('--min-free-gb')+1],'32')
                self.assertEqual(command[command.index('--max-dataset-gb')+1],'1500')
                output=command[command.index('--report-dir')+1]
                code='import json;from pathlib import Path;root=Path('+repr(output)+');root.mkdir();(root/"latest.json").write_text(json.dumps({"status":"completed","dataset_GB":12.5,"episodes_total":12,"stop_reason":None}))'
            else:raise AssertionError(stage)
            child=REAL_POPEN([sys.executable,'-u','-c',code],**kwargs);child_pids.append(child.pid);return child
        with patch.object(cloud,'ROOT',root),patch.object(cloud.subprocess,'Popen',side_effect=start),contextlib.redirect_stdout(io.StringIO()):
            runner=cloud.CloudCollection(args);code=runner.run()
        report=json.loads((runner.folder/'launch_status.json').read_text())
        log=(runner.folder/'console.log').read_text()
        return code,report,log,seen,child_pids

    def test_successful_qualification_continues_to_review_export(self):
        with tempfile.TemporaryDirectory() as folder:
            code,report,log,seen,_=self.launch(folder)
        self.assertEqual(code,2)
        self.assertEqual(report['status'],'user_review_required')
        self.assertEqual(report['active_stage'],'awaiting_user_review')
        self.assertTrue(report['review_page'])
        self.assertEqual(seen,['gpu','approval','landing_training.qualify','landing_training.review'])
        self.assertIn('STAGE START: review_export',log)
        self.assertEqual(report['stages'][-1]['exit_code'],0)
        self.assertIsNone(report['collection_report'])

    def test_termination_reports_real_signal_and_waits_for_owned_child(self):
        for signum in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):
            with self.subTest(signal=signum),tempfile.TemporaryDirectory() as folder:
                code,report,log,seen,pids=self.launch(folder,qualification='terminate_parent',termination_signal=signum)
                self.assertEqual(code,128+signum)
                self.assertEqual(report['status'],'cancelled')
                self.assertEqual(report['signal_received'],signum.name)
                self.assertEqual(report['active_stage'],'qualification')
                self.assertEqual(report['stages'][-1]['status'],'cancelled')
                self.assertEqual(report['stages'][-1]['exit_code'],-15)
                self.assertNotIn('landing_training.review',seen)
                self.assertIsNone(report['child_pid'])
                self.assertIn(signum.name+' received',report['stop_reason'])
                self.assertIn('exit=-15',log)
                import os
                with self.assertRaises(ProcessLookupError):os.kill(pids[-1],0)

    def test_qualification_failure_keeps_its_exit_code_and_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            code,report,log,seen,_=self.launch(folder,qualification='fail')
        self.assertEqual(code,7)
        self.assertEqual(report['exit_code'],7)
        self.assertEqual(report['status'],'failed')
        self.assertEqual(report['active_stage'],'qualification')
        self.assertNotIn('landing_training.review',seen)
        self.assertIn('qualification exited with code 7',report['stop_reason'])

    def test_approved_collection_retains_completion_metrics(self):
        with tempfile.TemporaryDirectory() as folder:
            code,report,log,seen,_=self.launch(folder,approved=True)
        self.assertEqual(code,0)
        self.assertEqual(report['status'],'completed')
        self.assertEqual(report['dataset_GB'],12.5)
        self.assertEqual(report['episodes_total'],12)
        self.assertEqual(seen,['gpu','approval','landing_training.collect'])
        self.assertIsNotNone(report['collection_report'])


if __name__=='__main__':unittest.main()
