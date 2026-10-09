"""Equivalence and integrity checks for faster production training."""
import copy
import json
import multiprocessing
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import h5py
import numpy as np
import torch

from .benchmarks.test_training import fixture
from .gate import file_hash
from .policy import LandingPolicy
from .train import Lane, loss_function
from .training_pipeline import (build_feature_cache, ChunkLoader, frame_counts,
                                chunk_plan, run_update, encoder_fingerprint,ValidationMetrics,teacher_supervision)


class PipelineChecks(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1); torch.manual_seed(714)

    def recording(self, root):
        bundle = fixture(root); path = bundle / 'one/observations.h5'
        with h5py.File(path, 'r+') as data:
            data['rgb'][:] = np.random.default_rng(714).integers(0, 256, data['rgb'].shape, dtype='u1')
            for index in range(4):
                row = json.loads(data['steps'][index]); row['terminal'] = index == 3
                row['privileged']['pad_visible'] = index % 2 == 0
                row['output']['expert_bounded_action'][0] = index * .1
                data['steps'][index] = json.dumps(row)
        return path

    def test_cached_outputs_losses_gradients_and_hidden_states_match_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.recording(root)
            second = source.with_name('second.h5')
            with h5py.File(source,'r') as original,h5py.File(second,'w') as data:
                data.attrs.update(role='review',training_eligible=False)
                images=np.concatenate((original['rgb'][:],original['rgb'][:1]),axis=0)
                data.create_dataset('rgb',data=255-images,chunks=(1,360,640,3),compression='lzf')
                records=[]
                for i in range(5):
                    row=json.loads(original['steps'][min(i,3)]);row['terminal']=i==4
                    row['observation']['px4']['attitude_ned_rad'][2]=.5
                    row['output']['expert_bounded_action'][0]=-.2
                    records.append(json.dumps(row))
                data.create_dataset('steps',data=records,dtype=h5py.string_dtype())
            reference = LandingPolicy(freeze_encoder=True).eval(); fast = copy.deepcopy(reference)
            mapping, _ = build_feature_cache(fast, [source,second], root / 'cache', 'cpu',
                                             workers=0, steps=3, min_free_gb=0)
            cache = Path(mapping[str(source)])
            with h5py.File(cache) as data:
                self.assertEqual(data.attrs['role'], 'review')
                self.assertFalse(data.attrs['training_eligible'])
            other=Path(mapping[str(second)])
            plan = chunk_plan([cache,other], frame_counts([cache,other]), lanes=2, steps=3)
            hidden = {}; lanes = [Lane(source), Lane(second)]
            optimizer = torch.optim.Adam(fast.parameters(), lr=1e-4)
            try:
                with ChunkLoader(plan, cached=True, workers=0) as loader:
                    for update in loader.updates():
                        reference.zero_grad(); reference_loss = 0
                        for lane in lanes:
                            image, observation, target, valid, aux_target = lane.chunk(3, 'cpu')
                            prediction, aux, lane.hidden = reference(image, observation, lane.hidden)
                            loss = loss_function(prediction, aux, target, valid, aux_target)
                            (loss / len(lanes)).backward(); reference_loss += float(loss.detach())
                            lane.hidden = lane.hidden.detach()
                        torch.nn.utils.clip_grad_norm_(reference.parameters(), 1.)
                        # Use a zero LR so both implementations see unchanged weights on chunk two.
                        optimizer.param_groups[0]['lr'] = 0
                        _, loss = run_update(fast, optimizer, update, hidden, 'cpu', cached=True)
                        self.assertAlmostEqual(loss, reference_loss, places=6)
                        for (name, left), (_, right) in zip(reference.named_parameters(), fast.named_parameters()):
                            if left.grad is not None:
                                torch.testing.assert_close(left.grad, right.grad, atol=2e-6, rtol=2e-4, msg=name)
                        if not update[0]['spec']['end']:
                            torch.testing.assert_close(hidden[1], lanes[0].hidden, atol=2e-6, rtol=2e-5)
                            torch.testing.assert_close(hidden[2], lanes[1].hidden, atol=2e-6, rtol=2e-5)
                        else:
                            self.assertFalse(hidden)
            finally:
                for lane in lanes:lane.close()

    def test_cache_reuse_corruption_and_changed_encoder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.recording(root); before = file_hash(source)
            model = LandingPolicy(freeze_encoder=True).eval()
            args = (model, [source], root / 'cache', 'cpu')
            mapping, first = build_feature_cache(*args, workers=0, min_free_gb=0)
            _, reused = build_feature_cache(*args, workers=0, min_free_gb=0)
            self.assertEqual(reused['built_frames'], 0); self.assertEqual(reused['reused_episodes'], 1)
            cache = Path(mapping[str(source)])
            with h5py.File(cache, 'r+') as data:data['features'][0, 0] += 1
            _, rebuilt = build_feature_cache(*args, workers=0, min_free_gb=0)
            self.assertEqual(rebuilt['built_frames'], 4)
            with torch.no_grad():next(model.encoder.parameters()).add_(.01)
            other, changed = build_feature_cache(*args, workers=0, min_free_gb=0)
            self.assertNotEqual(other[str(source)], str(cache))
            self.assertEqual(file_hash(source), before)
            self.assertFalse(list((root / 'cache').glob('*.partial-*')))

    def test_parallel_reader_order_labels_and_early_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.recording(Path(directory)); plan = chunk_plan([source], frame_counts([source]), steps=1)
            before = {p.pid for p in multiprocessing.active_children()}
            lane = Lane(source)
            try:
                with ChunkLoader(plan, workers=2) as loader:
                    item = next(loader)
                    expected = lane.chunk(1, 'cpu')
                    for value, reference in zip(item['values'], expected):
                        torch.testing.assert_close(value, reference[0], rtol=0, atol=0)
            finally:lane.close()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and any(p.pid not in before for p in multiprocessing.active_children()):
                time.sleep(.05)
            self.assertFalse([p for p in multiprocessing.active_children() if p.pid not in before])

    def test_shorter_lanes_keep_equal_loss_weighting_and_reset_on_refill(self):
        counts = {'a': 4, 'b': 7, 'c': 2}
        plan = chunk_plan(['a', 'b', 'c'], counts, lanes=2, steps=3)
        self.assertEqual([(p['path'], p['start'], p['stop'], p['lane_count']) for p in plan],
                         [('a', 0, 3, 2), ('b', 0, 3, 2), ('a', 3, 4, 2), ('b', 3, 6, 2),
                          ('c', 0, 2, 2), ('b', 6, 7, 2)])
        self.assertNotEqual(plan[0]['token'], plan[-2]['token'])

    def test_early_exit_drains_only_prefetched_window_and_reaps_four_readers(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=self.recording(root);before=file_hash(source)
            plan=chunk_plan([source],frame_counts([source]),lanes=1,steps=1,repeat=True,max_updates=10000)
            # Beyond the current prefetch window, data is deliberately unavailable.
            # Cleanup must not start these unrequested records or drain the full plan.
            for spec in plan[10:]:spec['path']=str(root/'unrequested.h5')
            with ChunkLoader(plan,workers=4) as loader:
                first=next(loader);readers=list(loader.iterator._workers)
                self.assertEqual(first['spec']['start'],0)
            self.assertTrue(all(not process.is_alive() for process in readers))
            self.assertTrue(all(process.exitcode==0 for process in readers))
            self.assertEqual(file_hash(source),before)

    def test_feature_steady_timing_excludes_reader_join_but_total_includes_it(self):
        from . import training_pipeline as pipeline
        from types import SimpleNamespace
        real_loader=pipeline.ChunkLoader;real_clock=time.monotonic;offset=[0.]
        class DelayedJoin(real_loader):
            def __exit__(self,*args):
                super().__exit__(*args)
                offset[0]+=1000. # Simulate a slow join without blocking the test.
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=self.recording(root)
            with patch.object(pipeline,'ChunkLoader',DelayedJoin), \
                    patch.object(pipeline,'time',SimpleNamespace(monotonic=lambda:real_clock()+offset[0])):
                _,stats=build_feature_cache(LandingPolicy(freeze_encoder=True),[source],root/'cache','cpu',
                                            workers=0,steps=1,min_free_gb=0)
            self.assertGreaterEqual(stats['seconds'],1000)
            self.assertLess(stats['steady_seconds'],10)
            self.assertEqual(stats['steady_frames'],2)

    def test_cache_refuses_trainable_encoder_and_cooperative_cancel(self):
        with self.assertRaisesRegex(ValueError, 'frozen'):
            encoder_fingerprint(LandingPolicy())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.recording(root); cancel = threading.Event(); cancel.set()
            with self.assertRaises(InterruptedError):
                build_feature_cache(LandingPolicy(freeze_encoder=True), [source], root/'cache', 'cpu',
                                    workers=0, cancel=cancel, min_free_gb=0)
            self.assertFalse(list((root/'cache').glob('*.h5')))

    def test_actual_trainer_exports_compatible_checkpoints_and_training_only_normalization(self):
        from . import train as trainer
        from . import training_pipeline as pipeline
        from .policy import PolicyRuntime
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = self.recording(root)
            validation = source.with_name('validation.h5')
            import shutil
            shutil.copyfile(source, validation)
            for artifact, role in [(source, 'training'), (validation, 'validation')]:
                with h5py.File(artifact, 'r+') as data:
                    data.attrs.update(role=role, training_eligible=True)
                    if role=='validation':
                        for i in range(len(data['steps'])):
                            row=json.loads(data['steps'][i]);row['observation']['beacon']['age_s']=99
                            data['steps'][i]=json.dumps(row)
            review = source.parent.parent; manifest = root/'dataset.json'
            manifest.write_text(json.dumps({'schema':'aerodock.landing.dataset.v1','role':'dataset',
                'review_manifest_sha256':file_hash(review/'manifest.json'), 'episodes':[
                    {'path':str(artifact.relative_to(root)),'role':role,'world_seed':i,'sha256':file_hash(artifact)}
                    for i,(artifact,role) in enumerate([(source,'training'),(validation,'validation')])]}))
            real_build=pipeline.build_feature_cache
            def small_test_cache(*args,**kwargs):
                return real_build(*args,**kwargs,min_free_gb=0)
            # Approval is mocked only for this disposable unit fixture, never real recordings.
            with patch.object(trainer,'require_approval'),patch.object(pipeline,'build_feature_cache',side_effect=small_test_cache):
                history=trainer.train(manifest,review,root/'checkpoints',epochs=1,device='cpu',
                                      pretrained=False,loader_workers=0,cpu_threads=1,patience=0)
                with self.assertRaisesRegex(FileExistsError,'use --resume'):
                    trainer.train(manifest,review,root/'checkpoints',epochs=1,pretrained=False)
                resumed=trainer.train(manifest,review,root/'checkpoints',epochs=2,device='cpu',
                                      pretrained=False,loader_workers=0,cpu_threads=1,resume=True,patience=0)
                control=trainer.train(manifest,review,root/'uninterrupted',epochs=2,device='cpu',
                                      pretrained=False,loader_workers=0,cpu_threads=1,patience=0)
                stopped=trainer.train(manifest,review,root/'early_stop',epochs=10,device='cpu',
                                      pretrained=False,loader_workers=0,cpu_threads=1,patience=1,min_delta=1.)
            self.assertEqual(len(stopped),2)
            self.assertEqual(json.loads((root/'early_stop/training_result.json').read_text())['stop_reason'],
                             'validation_early_stopping')
            self.assertEqual(history[0]['optimizer_steps'],1)
            saved=torch.load(root/'checkpoints/latest.pt',weights_only=False)
            uninterrupted=torch.load(root/'uninterrupted/latest.pt',weights_only=False)
            self.assertEqual(resumed,control)
            for name,value in saved['model'].items():
                torch.testing.assert_close(value,uninterrupted['model'][name],rtol=0,atol=0)
            self.assertEqual(saved['epoch'],2)
            self.assertIn('persistence_action_huber',saved['history'][-1]['validation_metrics'])
            expected=np.mean([trainer.numeric_observation(row) for row in trainer.rows(source)],axis=0)
            torch.testing.assert_close(saved['model']['observation_mean'],torch.from_numpy(expected))
            self.assertTrue(saved['training']['feature_cache'])
            self.assertFalse(list((root/'checkpoints').glob('*.tmp')))
            self.assertTrue((root/'checkpoints/best.pt').exists())
            policy=PolicyRuntime(root/'checkpoints/best.pt')
            with h5py.File(validation) as data:
                action,_=policy.act(data['rgb'][0],json.loads(data['steps'][0])['observation'])
            self.assertTrue(np.isfinite(action).all())

    def test_evaluation_rejects_mismatched_checkpoint_before_creating_output(self):
        from . import evaluate as evaluator
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);dataset=root/'dataset.json';dataset.write_text('{}')
            review=root/'review';review.mkdir();(review/'manifest.json').write_text('{}')
            runtime=SimpleNamespace(metadata={'dataset_sha256':'wrong','review_manifest_sha256':'wrong'})
            manifest={'episodes':[{'role':'validation'}]}
            with patch.object(evaluator,'approved_dataset',return_value=(dataset,manifest,[],[])), \
                    patch.object(evaluator,'PolicyRuntime',return_value=runtime),patch.object(evaluator,'run_episode') as flight:
                with self.assertRaisesRegex(PermissionError,'does not match'):
                    evaluator.evaluate(dataset,review,root/'checkpoint.pt','validation',root/'evaluation',1,device='cpu')
            flight.assert_not_called();self.assertFalse((root/'evaluation').exists())

    def test_dataset_weighted_metrics_are_invariant_to_short_terminal_chunks(self):
        torch.manual_seed(714)
        prediction=torch.rand(1,3,6);aux=torch.randn(1,3,10)
        target=torch.rand(1,3,6)*.1;valid=torch.tensor([[1.,0.,1.]])
        aux_target=torch.randn(1,3,10);aux_target[...,0]=torch.tensor([[1.,0.,1.]])
        aux_target[...,9]=torch.tensor([[0.,1.,1.]]);obs=torch.rand(1,3,32)*.1
        whole=ValidationMetrics();whole.add(prediction,aux,target,valid,aux_target,obs)
        split=ValidationMetrics()
        for start,stop in [(0,2),(2,3)]:
            split.add(prediction[:,start:stop],aux[:,start:stop],target[:,start:stop],valid[:,start:stop],
                      aux_target[:,start:stop],obs[:,start:stop])
        for key,value in whole.report().items():self.assertAlmostEqual(value,split.report()[key],places=6)

    def test_failed_expert_targets_are_masked_but_dagger_corrections_remain(self):
        manifest={'episodes':[{'path':'a.h5','name':'bad_expert','outcome':'water_strike','collection':'expert'},
                              {'path':'b.h5','name':'bad_student','outcome':'water_strike','collection':'dagger'}]}
        allowed,excluded=teacher_supervision(manifest,Path('/tmp'))
        self.assertFalse(allowed['/tmp/a.h5']);self.assertTrue(allowed['/tmp/b.h5']);self.assertEqual(excluded,['bad_expert'])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=self.recording(root);model=LandingPolicy(freeze_encoder=True).eval()
            mappings,_=build_feature_cache(model,[source],root/'cache','cpu',workers=0,min_free_gb=0,
                                           supervision={str(source):False})
            with h5py.File(mappings[str(source)]) as data:
                self.assertEqual(float(np.asarray(data['valid']).sum()),0.)
                self.assertFalse(data.attrs['imitation_allowed'])

    def test_planned_camera_aim_balance_in_every_split(self):
        from collections import Counter,defaultdict
        from .collect import planned_scenarios
        counts=defaultdict(Counter)
        for item in planned_scenarios()['episodes']:
            counts[item['role']][item['scenario']['initial_camera_target']]+=1
        self.assertEqual(counts['training'],{True:480,False:480})
        self.assertEqual(counts['validation'],{True:60,False:60})
        self.assertEqual(counts['test'],{True:60,False:60})


if __name__ == '__main__':unittest.main()
