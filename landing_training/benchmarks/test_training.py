"""Check real training steps, episode boundaries and durable failure reports."""
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

import h5py
import numpy as np

from . import training
from ..gate import file_hash


def fixture(root):
    bundle = root / 'review'; episode = bundle / 'one'
    episode.mkdir(parents=True)
    (bundle / 'manifest.json').write_text(json.dumps({'role': 'review', 'episodes': [{'name': 'one'}]}))
    row = {'observation': {
        'px4': {'valid': True, 'attitude_ned_rad': [0, 0, 0]},
        'beacon': {'age_s': 0, 'valid': True, 'dock_ready': True},
        'gimbal_rad': [0, 0], 'image_age_s': 0, 'previous_executed_action': [0]*6,
        'decision_dt_s': .04, 'image_valid': True},
        'output': {'expert_bounded_action': [0]*6, 'executed_action': [0]*6},
        'outcome': 'flying', 'privileged': {'pad_visible': True,
        'pad_keypoints_px': [[320, 180]], 'pad_position_enu_m': [0, 0, 0],
        'drone_position_enu_m': [0, 0, 2], 'pad_velocity_enu_m_s': [0, 0, 0],
        'drone_velocity_enu_m_s': [0, 0, 0]}}
    with h5py.File(episode / 'observations.h5', 'w') as data:
        data.attrs.update(role='review', training_eligible=False)
        data.create_dataset('rgb', data=np.zeros((4, 360, 640, 3), dtype='u1'),
                            chunks=(1, 360, 640, 3), compression='lzf')
        data.create_dataset('steps', data=[json.dumps(row)]*4, dtype=h5py.string_dtype())
    return bundle


def arguments(bundle, output):
    return Namespace(review=str(bundle), output=str(output), device='cpu', cpu_threads=1,
                     no_pretrained=True, sequence_steps=3, lanes=2, warmup_updates=1,
                     updates=3, validation_chunks=3, epochs=10, max_minutes=1)


class TrainingBenchmarkChecks(unittest.TestCase):
    def test_real_updates_cross_episode_boundaries_without_modifying_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = fixture(root); output = root / 'benchmark'
            recording = bundle / 'one/observations.h5'; before = file_hash(recording)
            with contextlib.redirect_stdout(io.StringIO()):
                code = training.benchmark(arguments(bundle, output))
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(code, 0)
            self.assertTrue(report['finite_loss_gradients_parameters'])
            self.assertEqual([s['frames'] for s in report['samples']['training']], [2, 6, 2])
            self.assertEqual([s['frames'] for s in report['samples']['validation']], [1, 3, 1])
            self.assertEqual(report['training']['frames'], 10)
            self.assertGreater(report['training']['frames_per_second'], 0)
            self.assertLess(report['parameters']['trainable'], report['parameters']['total'])
            self.assertEqual(file_hash(recording), before)
            self.assertFalse(list(output.rglob('*.pt')))

    def test_no_cuda_fails_with_saved_report_and_no_cpu_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); args = arguments(fixture(root), root / 'output'); args.device = 'cuda'
            with patch.object(training.torch.cuda, 'is_available', return_value=False), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = training.benchmark(args)
            report = json.loads((root / 'output/report.json').read_text())
            self.assertEqual(code, 2)
            self.assertEqual(report['status'], 'failed')
            self.assertIn('CUDA is unavailable', report['error'])
            self.assertFalse(report['projections'])

    def test_rejects_production_recordings_and_paths_outside_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = fixture(root)
            with h5py.File(bundle / 'one/observations.h5', 'r+') as data:
                data.attrs['training_eligible'] = True
            with self.assertRaisesRegex(ValueError, 'review-only'):
                training.recordings(bundle)
            (bundle / 'manifest.json').write_text(json.dumps({'role': 'review',
                                                    'episodes': [{'name': '../outside'}]}))
            with self.assertRaisesRegex(ValueError, 'escapes'):
                training.recordings(bundle)

    def test_sigterm_saves_partial_measurements_and_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = fixture(root); output = root / 'benchmark'
            with (root / 'console.log').open('w') as log:
                child = subprocess.Popen([sys.executable, '-m', 'landing_training.benchmarks.training',
                    '--review', str(bundle), '--output', str(output), '--device', 'cpu',
                    '--no-pretrained', '--cpu-threads', '1', '--sequence-steps', '3', '--lanes', '2',
                    '--updates', '1000', '--max-minutes', '2'], stdout=log, stderr=subprocess.STDOUT)
                try:
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        path = output / 'report.json'
                        if path.exists() and json.loads(path.read_text())['samples']['training']:
                            break
                        if child.poll() is not None:
                            self.fail((root / 'console.log').read_text())
                        time.sleep(.05)
                    else:
                        self.fail('Benchmark did not start measured updates')
                    child.send_signal(signal.SIGTERM)
                    self.assertEqual(child.wait(timeout=20), 2)
                finally:
                    if child.poll() is None:
                        child.kill(); child.wait()
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['status'], 'partial')
            self.assertEqual(report['signal'], signal.SIGTERM)
            self.assertGreater(report['training']['frames'], 0)
            self.assertTrue((output / 'summary.md').is_file())


if __name__ == '__main__':
    unittest.main()
