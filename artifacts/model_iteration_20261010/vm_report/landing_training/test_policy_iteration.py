"""Regression checks for the versioned policy iteration."""
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import h5py
import numpy as np
import torch

from .gate import file_hash
from .iterate_policy import verified_caches
from .policy import LandingPolicy, PolicyRuntime, policy_observation


class IterationChecks(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        torch.manual_seed(714)

    def test_periodic_inputs_ignore_previous_actions_and_full_turns(self):
        raw = torch.randn(2, 7, 32)
        changed = raw.clone()
        changed[..., 24:30] = 1000
        for index in (5, 9, 10):
            changed[..., index] += 20 * math.pi
        torch.testing.assert_close(policy_observation(raw, 'periodic_no_action_v1'),
                                   policy_observation(changed, 'periodic_no_action_v1'),
                                   atol=1e-5, rtol=1e-5)
        torch.testing.assert_close(raw, policy_observation(raw), atol=0, rtol=0)
        with self.assertRaises(ValueError):
            policy_observation(raw, 'unknown')

    def test_runtime_reads_mode_and_legacy_checkpoints_remain_compatible(self):
        for mode in ('legacy', 'periodic_no_action_v1'):
            model = LandingPolicy(observation_mode=mode).eval()
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'model.pt'
                training = {} if mode == 'legacy' else {'observation_mode': mode}
                torch.save({'schema': 'aerodock.landing.checkpoint.v1', 'model': model.state_dict(),
                            'training': training}, path)
                runtime = PolicyRuntime(path)
                self.assertEqual(runtime.model.observation_mode, mode)
                obs = torch.randn(1, 5, 32)
                features = torch.randn(1, 5, 1728)
                with torch.inference_mode():
                    expected, _, _ = model.forward_features(features, obs)
                    actual, _, _ = runtime.model.forward_features(features, obs)
                torch.testing.assert_close(actual, expected)
                runtime.hidden = torch.ones(1, 1, 128)
                runtime.reset()
                self.assertIsNone(runtime.hidden)

    def test_frozen_feature_integrity_split_and_mask_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'review'
            bundle.mkdir()
            (bundle / 'manifest.json').write_text('{}')
            cache_dir = root / 'features'
            cache_dir.mkdir()
            items = []
            for index, role in enumerate(('training', 'validation', 'test')):
                source = root / (role + '.h5')
                allowed = role != 'validation'
                item = {'path': source.name, 'name': role, 'sha256': role + '-source',
                        'role': role, 'world_seed': index, 'imitation_allowed': allowed}
                items.append(item)
                if role == 'test':
                    continue
                cache = cache_dir / (role + '.h5')
                with h5py.File(cache, 'w') as data:
                    data.attrs.update(source_path=str(source), source_sha256=item['sha256'],
                                      encoder_sha256='encoder', complete=True,
                                      schema='aerodock.landing.features.v1', role=role,
                                      training_eligible=True, imitation_allowed=allowed)
                    for name, shape in [('features', (1728,)), ('numeric', (32,)), ('actions', (6,)),
                                        ('valid', ()), ('auxiliary', (10,))]:
                        data.create_dataset(name, data=np.zeros((2, *shape), dtype=np.float32))
                cache.with_suffix('.json').write_text(json.dumps({'sha256': file_hash(cache)}))
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'schema': 'aerodock.landing.dataset.v1', 'role': 'dataset',
                                          'review_manifest_sha256': file_hash(bundle / 'manifest.json'),
                                          'episodes': items}))
            checkpoint = root / 'source.pt'
            torch.save({'schema': 'aerodock.landing.checkpoint.v1',
                        'dataset_sha256': file_hash(manifest),
                        'review_manifest_sha256': file_hash(bundle / 'manifest.json'),
                        'feature_preparation': {'encoder_sha256': 'encoder'}}, checkpoint)
            args = (manifest, bundle, checkpoint, cache_dir, Path(__file__).resolve().parent.parent)
            with patch('landing_training.iterate_policy.require_approval'):
                _, _, splits, evidence = verified_caches(*args)
                self.assertEqual([len(splits[r]) for r in ('training', 'validation')], [1, 1])
                self.assertEqual(len(evidence), 2)
                with h5py.File(cache_dir / 'training.h5', 'r+') as data:
                    data['features'][0, 0] = 99
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    verified_caches(*args)
