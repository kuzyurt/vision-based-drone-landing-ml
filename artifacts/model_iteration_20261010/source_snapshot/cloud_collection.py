"""Own cloud collection stages and persist their actual exit/signal status."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from .collection_session import atomic_json

ROOT = Path(__file__).resolve().parent


class LaunchCancelled(Exception):
    pass


class StageFailed(Exception):
    def __init__(self, stage, code):
        self.stage = stage
        self.code = code if code > 0 else 128 - code
        super().__init__(f'{stage} exited with code {self.code}')


class CloudCollection:
    def __init__(self, args):
        self.args = args
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8]
        self.folder = ROOT / 'outputs' / ('collection_launch_' + stamp)
        self.folder.mkdir(parents=True)
        (ROOT / 'outputs/latest_collection_launch.txt').write_text(str(self.folder) + '\n')
        self.started = time.monotonic()
        self.child = None
        self.signal_received = None
        self.stage = 'initializing'
        self.stages = []
        self.code = None
        self.status = 'running'
        self.reason = None
        self.log = None
        self.dataset = Path(args.output).resolve()

    def save(self):
        result_path = self.folder / 'results/latest.json'
        result = json.loads(result_path.read_text()) if result_path.is_file() else None
        review = self.folder / 'current_review/index.html'
        atomic_json(self.folder / 'launch_status.json', {
            'status': self.status, 'exit_code': self.code,
            'updated_utc': datetime.now(timezone.utc).isoformat(),
            'elapsed_seconds': time.monotonic() - self.started,
            'active_stage': self.stage, 'stages': self.stages,
            'signal_received': signal.Signals(self.signal_received).name if self.signal_received else None,
            'child_pid': self.child.pid if self.child and self.child.poll() is None else None,
            'dataset_directory': str(self.dataset),
            'console_log': str(self.folder / 'console.log'),
            'collection_report': str(result_path) if result else None,
            'review_page': str(review) if review.is_file() else None,
            'dataset_GB': result['dataset_GB'] if result else None,
            'episodes_total': result['episodes_total'] if result else None,
            'stop_reason': self.reason or (result.get('stop_reason') if result else None),
        })

    def emit(self, line):
        self.log.write(line)
        self.log.flush()
        print(line, end='', flush=True)

    def cancel(self, signum, frame):
        if self.signal_received is not None:
            return
        self.signal_received = signum
        # Collect/review handle SIGTERM as a cleanup request. Qualification and
        # probes can terminate normally without owning flight processes.
        if self.child and self.child.poll() is None:
            self.child.send_signal(signal.SIGTERM)
        raise LaunchCancelled(signal.Signals(signum).name)

    def run_stage(self, name, command, *, capture=False):
        self.stage = name
        entry = {'name': name, 'started_utc': datetime.now(timezone.utc).isoformat(),
                 'status': 'running', 'exit_code': None}
        self.stages.append(entry)
        self.emit(f'\nSTAGE START: {name}\n')
        self.save()
        started = time.monotonic()
        output = []
        actual_code = None
        try:
            import psutil
            self.child = subprocess.Popen(command, cwd=ROOT.parent, stdin=subprocess.DEVNULL,
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          text=True, start_new_session=True)
            try:created=psutil.Process(self.child.pid).create_time()
            except psutil.NoSuchProcess:created=None  # Already-exited short probes need no recovery.
            entry.update(child_pid=self.child.pid,child_create_time=created,command=[str(value) for value in command])
            self.save()
            for line in self.child.stdout:
                self.emit(line)
                if capture:
                    output.append(line)
            actual_code = self.child.wait()
        finally:
            if self.child:
                if self.child.poll() is None:
                    self.child.send_signal(signal.SIGTERM)
                # Keep draining output while the child closes PX4 and HDF5;
                # a full pipe must not prevent its cleanup from finishing.
                for line in self.child.stdout:
                    self.emit(line)
                actual_code = self.child.wait()
                self.child.stdout.close()
                self.child = None
            entry.update(elapsed_seconds=time.monotonic()-started,
                         finished_utc=datetime.now(timezone.utc).isoformat(),
                         exit_code=actual_code,
                         status='cancelled' if self.signal_received else 'completed' if actual_code == 0 else 'failed')
            self.emit(f'STAGE END: {name}; exit={actual_code}\n')
            self.save()
        if actual_code:
            raise StageFailed(name, actual_code)
        return ''.join(output)

    def execute(self):
        python = sys.executable
        self.run_stage('gpu_probe', [python, '-u', '-c',
            'import json; from landing_training.collection_benchmark import renderer_info; '
            'info=renderer_info(); print(json.dumps(info,indent=2),flush=True)\n'
            'if info["software_rendering"]:\n'
            ' raise RuntimeError("GPU rendering required; repair NVIDIA EGL")'])
        bundle = self.args.review
        if bundle == 'auto':
            try:
                output = self.run_stage('approval_check', [python, '-u', '-c',
                    'from landing_training.collect import approved_bundle\n'
                    'try: print(approved_bundle("auto"))\n'
                    'except PermissionError as exc:\n'
                    ' print(str(exc),flush=True)\n'
                    ' raise SystemExit(2)'], capture=True)
                bundle = output.strip().splitlines()[-1]
            except StageFailed as exc:
                if exc.code != 2:
                    raise
                self.emit('No current approved review exists. Preparing ten review videos; production remains blocked.\n')
                self.run_stage('qualification', [python, '-u', '-m', 'landing_training.qualify'])
                review = self.folder / 'current_review'
                self.run_stage('review_export', [python, '-u', '-m', 'landing_training.review', '--output', str(review)])
                manifest = json.loads((review / 'manifest.json').read_text())
                if not manifest.get('qualification_passed'):
                    raise StageFailed('review_qualification', 1)
                self.status = 'user_review_required'
                self.reason = 'Verify the ten current review videos and recorded data before approving this bundle.'
                self.stage = 'awaiting_user_review'
                self.code = 2
                self.emit('Review page: ' + str(review / 'index.html') + '\n')
                return
        self.run_stage('collection', [python, '-u', '-m', 'landing_training.collect',
            '--review', bundle, '--output', str(self.dataset), '--max-episodes', '1200',
            '--workers', '64', '--instance-base', '20', '--gl', 'egl', '--require-gpu',
            '--min-free-gb', '32', '--max-dataset-gb', '1500', '--quarantine-partial',
            '--report-dir', str(self.folder / 'results')])
        report = json.loads((self.folder / 'results/latest.json').read_text())
        self.status = report['status']
        self.reason = report.get('stop_reason')
        self.stage = 'finished'
        self.code = 0

    def run(self):
        handlers = {}
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            handlers[signum] = signal.signal(signum, self.cancel)
        try:
            with (self.folder / 'console.log').open('a', buffering=1) as self.log:
                try:
                    self.save()
                    self.emit('Dataset: ' + str(self.dataset) + '\nReports: ' + str(self.folder) + '\n')
                    self.execute()
                except LaunchCancelled:
                    self.status = 'cancelled'
                    self.code = 128 + self.signal_received
                    self.reason = f'{signal.Signals(self.signal_received).name} received during {self.stage}'
                except StageFailed as exc:
                    self.status = 'failed'
                    self.code = exc.code
                    self.reason = str(exc)
                except Exception as exc:
                    self.status = 'failed'
                    self.code = 1
                    self.reason = f'{type(exc).__name__}: {exc}'
                finally:
                    self.save()
                    self.emit(f'Launch finished: {self.status}; exit={self.code}; stage={self.stage}\n')
                    self.emit('Reports and log: ' + str(self.folder) + '\n')
        finally:
            for signum, handler in handlers.items():
                signal.signal(signum, handler)
        return self.code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', default='auto')
    parser.add_argument('--output', default=str(ROOT / 'datasets/expert'))
    args = parser.parse_args()
    return CloudCollection(args).run()


if __name__ == '__main__':
    raise SystemExit(main())
