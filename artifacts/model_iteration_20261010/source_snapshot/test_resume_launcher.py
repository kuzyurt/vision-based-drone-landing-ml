"""Exercise detached-launch shell handoff with fixture commands, without a VM."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class ResumeLauncherChecks(unittest.TestCase):
    def fixture(self,root):
        training=root/'landing_training';training.mkdir()
        shutil.copyfile(Path(__file__).with_name('resume_cloud_pipeline.sh'),training/'resume_cloud_pipeline.sh')
        scripts=root/'fixture_commands';scripts.mkdir()
        python=training/'.venv/bin/python';python.parent.mkdir(parents=True)
        bundle=training/'outputs/review';bundle.mkdir(parents=True)
        python.write_text('#!/usr/bin/env bash\ncat >/dev/null\nprintf "%s\\n" "$HARNESS_REVIEW"\n');python.chmod(0o755)
        wrapper=training/'start_cloud_pipeline.sh'
        wrapper.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$HARNESS_ARGUMENTS"\nprintf "%s\\n" "fixture pipeline launched"\n')
        tmux=scripts/'tmux'
        tmux.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$HARNESS_TMUX"\nbash -c "${@: -1}"\n');tmux.chmod(0o755)
        environment={**os.environ,'PATH':str(scripts)+os.pathsep+os.environ['PATH'],
            'HARNESS_REVIEW':str(bundle),'HARNESS_ARGUMENTS':str(root/'arguments.txt'),
            'HARNESS_TMUX':str(root/'tmux.txt')}
        return training,environment

    def test_detached_launch_preserves_review_and_configuration_with_paths_containing_spaces(self):
        with tempfile.TemporaryDirectory(prefix='landing restart ') as directory:
            root=Path(directory);training,environment=self.fixture(root)
            result=subprocess.run(['bash',str(training/'resume_cloud_pipeline.sh')],env=environment,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            arguments=(root/'arguments.txt').read_text().splitlines()
            self.assertEqual(arguments,['--review',environment['HARNESS_REVIEW'],'--no-review-export','--reuse-approved-runtime'])
            self.assertIn('-d',(root/'tmux.txt').read_text().splitlines())
            log=Path((training/'outputs/latest_resume_launcher.txt').read_text().strip())
            self.assertIn('fixture pipeline launched',log.read_text())
            self.assertTrue((training/'outputs/latest_pipeline_session.txt').read_text().startswith('landing-pipeline-'))

    def test_existing_workflow_lock_prevents_duplicate_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);training,environment=self.fixture(root)
            (training/'build').mkdir()
            with (training/'build/cloud_collection_launch.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                result=subprocess.run(['bash',str(training/'resume_cloud_pipeline.sh')],env=environment,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('no duplicate',result.stdout)
            self.assertFalse((root/'tmux.txt').exists())


if __name__=='__main__':unittest.main()
