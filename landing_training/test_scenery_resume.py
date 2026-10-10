"""Geometry and real recording recovery checks; no camera/video rendering."""
from collections import OrderedDict
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from . import paths, gate
from .collect import _collect_locked, planned_scenarios
from .collection_session import atomic_json
from .test_dataset_audit import write_episode, manifest
from . import test_gate as approval_fixtures
from .workflow import verify_runtime_resume
from usv.procedural_world import World
from usv.world_render import WorldRenderer


RENDERER = gate.REPO / gate.SCENERY_RENDERER_PATH
FIXED_SOURCE = RENDERER.read_text()
CORRECTION = '''            # The final coastline tile may be shorter than both 2 m margins.
            # Keep every previously valid tile identical, including its RNG
            # stream; shorten margins only where the old interval was invalid.
            margin=2. if end-start>=4. else (end-start)*.25
'''
LEGACY_SOURCE = FIXED_SOURCE.replace(CORRECTION, '').replace(
    'rng.uniform(start+margin,end-margin)', 'rng.uniform(start+2,end-2)')


def renderer(cls=WorldRenderer):
    # Only CPU geometry construction is exercised, without an OpenGL context.
    result = cls.__new__(cls)
    result.cache = OrderedDict()
    names = ('sand', 'wet_sand', 'grass', 'grass_macro', 'gravel', 'rock',
             'concrete', 'facade', 'asphalt', 'foliage', 'roof', 'pavers', 'quay',
             'facade_brick', 'facade_modern', 'rock_cliff', 'rock_wet', 'rock_boulder')
    result.material = {name: index for index, name in enumerate(names)}
    return result


class SceneryChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        namespace = {}
        exec(compile(LEGACY_SOURCE, 'original_world_render.py', 'exec'), namespace)
        cls.legacy = namespace['WorldRenderer']

    def test_short_rock_tail_reproduces_error_and_now_has_finite_repeatable_geometry(self):
        for width in (1e-6, .01, .5, 1., 3., 3.999999):
            for lod in (False, True):
                with self.subTest(width=width, lod=lod):
                    world = World('rock', 90001)
                    world.coast_length = 200 + width
                    with self.assertRaisesRegex(ValueError, 'high - low'):
                        renderer(self.legacy).chunk(world, 5, lod)
                    fixed = renderer(); geoms = fixed.chunk(world, 5, lod)
                    self.assertGreater(len(geoms), 0)
                    self.assertIs(fixed.chunk(world, 5, lod), geoms)
                    repeated = renderer().chunk(world, 5, lod)
                    self.assertEqual(len(geoms), len(repeated))
                    for left, right in zip(geoms, repeated):
                        for value in left[1:]:
                            self.assertTrue(np.isfinite(value).all())
                        for value, expected in zip(left, right):
                            np.testing.assert_array_equal(value, expected)

    def test_every_previously_valid_map_chunk_matches_original_geometry_exactly(self):
        for kind in ('island', 'beach', 'city', 'gravel', 'rock'):
            for width in (4., 4.5, 8., 39.9, 40.):
                for lod in (False, True):
                    with self.subTest(kind=kind, width=width, lod=lod):
                        world = World(kind, 90011); world.coast_length = 200 + width
                        before = renderer(self.legacy).chunk(world, 5, lod)
                        after = renderer().chunk(world, 5, lod)
                        self.assertEqual(len(before), len(after))
                        for left, right in zip(before, after):
                            for value, expected in zip(left, right):
                                np.testing.assert_array_equal(value, expected)

    def test_all_planned_rock_world_end_chunks_build(self):
        seeds = {item['scenario']['world_seed'] for item in planned_scenarios()['episodes']
                 if item['scenario']['kind'] == 'rock'}
        self.assertEqual(len(seeds), 120)
        short_tails = 0
        for seed in sorted(seeds):
            world = World('rock', seed)
            index = math.ceil(world.coast_length / 40) - 1
            short_tails += world.coast_length - index * 40 < 4
            for lod in (False, True):
                self.assertGreater(len(renderer().chunk(world, index, lod)), 0)
        self.assertGreater(short_tails, 0)


class SceneryResumeChecks(unittest.TestCase):
    def runtime_fixture(self, root):
        training = root / 'landing_training'; training.mkdir()
        for source in (*gate.ROOT.glob('*.py'), *gate.ROOT.glob('*.sh')):
            (training / source.name).write_bytes(source.read_bytes())
        boat = root / 'AERODOCK_MuJoCo'; (boat / 'usv').mkdir(parents=True)
        (boat / 'config.json').write_text('{}')
        scenery = root / gate.SCENERY_RENDERER_PATH
        scenery.write_text(LEGACY_SOURCE)
        self.assertEqual(gate.file_hash(scenery), gate.SCENERY_RENDERER_BEFORE)
        return training, scenery

    def test_exact_predecessor_accepted_but_other_source_assets_and_dependencies_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); training, scenery = self.runtime_fixture(root)
            with patch.object(gate, 'REPO', root), patch.object(gate, 'ROOT', training):
                old = gate.source_fingerprint(runtime_only=True)
                scenery.write_text(FIXED_SOURCE)
                current = gate.source_fingerprint(runtime_only=True)
                self.assertNotEqual(current, old)
                self.assertEqual(gate.compatible_runtime_fingerprints(current), {current, old})
                expert = training / 'expert.py'; original = expert.read_bytes()
                expert.write_bytes(original + b'\n# unrelated teacher change\n')
                self.assertNotIn(old, gate.compatible_runtime_fingerprints())
                expert.write_bytes(original)
                asset = root / 'AERODOCK_MuJoCo/assets/changed.png'
                asset.parent.mkdir(); asset.write_bytes(b'changed asset')
                self.assertNotIn(old, gate.compatible_runtime_fingerprints())
                asset.unlink()
                from importlib.metadata import version
                with patch('importlib.metadata.version', side_effect=lambda name:
                           'different-numpy' if name == 'numpy' else version(name)):
                    self.assertNotIn(old, gate.compatible_runtime_fingerprints())
                scenery.write_text(FIXED_SOURCE + '\n# another renderer change\n')
                self.assertNotIn(old, gate.compatible_runtime_fingerprints())

    def test_original_approval_reused_without_modifying_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); training, scenery = self.runtime_fixture(root)
            with patch.object(gate, 'REPO', root), patch.object(gate, 'ROOT', training):
                old = gate.source_fingerprint(runtime_only=True)
                scenery.write_text(FIXED_SOURCE)
                review = root / 'review'; review.mkdir()
                data = approval_fixtures.ApprovalReuseChecks().fixture(review)
                for relative in data['artifacts']:
                    path = review / relative; evidence = json.loads(path.read_text())
                    evidence['runtime_source_sha256'] = old
                    atomic_json(path, evidence); data['artifacts'][relative] = gate.file_hash(path)
                atomic_json(review / 'manifest.json', data)
                decision = json.loads((review / 'approval.json').read_text())
                decision['manifest_sha256'] = gate.file_hash(review / 'manifest.json')
                atomic_json(review / 'approval.json', decision)
                before = {str(p): gate.file_hash(p) for p in review.rglob('*.json')}
                with patch('landing_training.collect.planned_scenarios', return_value=data['collection_plan']):
                    with patch.dict(os.environ, {'LANDING_REUSE_APPROVED_RUNTIME': '0'}):
                        with self.assertRaises(PermissionError): gate.require_approval(review)
                    with patch.dict(os.environ, {'LANDING_REUSE_APPROVED_RUNTIME': '1'}):
                        self.assertEqual(gate.require_approval(review), data)
                        self.assertEqual(before, {str(p): gate.file_hash(p) for p in review.rglob('*.json')})
                        (training / 'environment.py').write_text('changed physics')
                        with self.assertRaisesRegex(PermissionError, 'runtime changed'):
                            gate.require_approval(review)

    def test_mixed_runtime_resume_and_complete_unindexed_recording_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            indexed_item, indexed_entry = write_episode(root, name='indexed')
            pending_item, pending_entry = write_episode(root, name='pending', world=2)
            for entry, runtime in ((indexed_entry, 'previous-runtime'), (pending_entry, 'current-runtime')):
                summary = root / entry['name'] / 'summary.json'
                data = json.loads(summary.read_text())
                data.update(source_sha256='old-source', runtime_source_sha256=runtime)
                atomic_json(summary, data)
            bundle = root / 'review'; bundle.mkdir(); (bundle / 'manifest.json').write_text('{}')
            path = manifest(root, [indexed_entry]); data = json.loads(path.read_text())
            data['review_manifest_sha256'] = gate.file_hash(bundle / 'manifest.json'); atomic_json(path, data)
            before = {str(p): gate.file_hash(p) for name in ('indexed', 'pending')
                      for p in (root / name).iterdir() if p.is_file()}
            accepted = {'previous-runtime', 'current-runtime'}
            state = {'review_authorization': {'runtime_sha256': 'previous-runtime'}}
            with patch('landing_training.workflow.compatible_runtime_fingerprints', return_value=accepted):
                verify_runtime_resume(state, 'current-runtime', path)
                state['review_authorization']['runtime_sha256'] = 'unrelated-runtime'
                with self.assertRaises(ValueError): verify_runtime_resume(state, 'current-runtime', path)
            with patch.dict(os.environ, {'LANDING_REUSE_APPROVED_RUNTIME': '1'}), \
                 patch.object(gate, 'compatible_runtime_fingerprints', return_value=accepted), \
                 patch('landing_training.collect.planned_scenarios', return_value={'episodes': [indexed_item, pending_item]}), \
                 patch('landing_training.execution.iter_jobs', return_value=iter(())) as workers:
                result = _collect_locked(bundle, root, 1, None, 64, 20, {}, 'new-source')
                self.assertEqual(workers.call_args.args[0], [])
            self.assertEqual(result['episodes'][0], indexed_entry)
            self.assertEqual([e['name'] for e in result['episodes']], ['indexed', 'pending'])
            self.assertEqual(before, {str(p): gate.file_hash(Path(p)) for p in before})


if __name__ == '__main__':
    unittest.main()
