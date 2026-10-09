"""Exercise durable handoff gates and restarts without approving real recordings."""
from argparse import Namespace
import contextlib
from dataclasses import asdict
import io
import json
from pathlib import Path
import tempfile
import time
import subprocess
import sys
import unittest
from unittest.mock import patch
import torch

from . import workflow as flow,cloud_collection as cloud
from .collection_session import atomic_json
from .config import Scenario
from .gate import file_hash


def plan_fixture():
    entries=[]
    for i,role in enumerate(('training','validation','test','training')):
        entries.append({'role':role,'distance_band':0,'weather_group':0,'pair':i,
                        'scenario':asdict(Scenario(name=f'{role}_{i}',world_seed=i,path_seed=i+10,boat_start_fraction=.5))})
    return {'episodes':entries,'pilot_first_episodes':2}


def args_fixture(root):
    return Namespace(state=str(root/'outputs/state.json'),output=str(root/'dataset'),checkpoints=str(root/'checkpoints'),
                     review='auto',epochs=10,pilot_epochs=3,patience=3,workers=64,evaluation_workers=8,
                     reader_workers=4,min_free_gb=32.,max_dataset_gb=1500.,device='cuda')


class WorkflowChecks(unittest.TestCase):
    def fixtures(self,root,*,pending=False,stop_collection=False,unsafe_policy=False,failed_audit=False):
        plan=plan_fixture();bundle=root/'fixture_review';bundle.mkdir()
        (bundle/'manifest.json').write_text(json.dumps({'collection_plan':plan,'qualification_passed':True}))
        calls=[]
        def stage(runner,name,command,**kwargs):
            calls.append(name);runner.stage=name
            runner.stages.append({'name':name,'elapsed_seconds':.01,'exit_code':0,'status':'completed'})
            if name.endswith('collection'):
                runner.dataset.mkdir(exist_ok=True);report_dir=runner.folder/'results';report_dir.mkdir(exist_ok=True)
                entries=json.loads(runner.manifest.read_text())['episodes'] if runner.manifest.exists() else []
                have={e['name'] for e in entries};remaining=[e for e in plan['episodes'] if e['scenario']['name'] not in have]
                count=int(command[command.index('--max-episodes')+1]);remaining=remaining[:count]
                if stop_collection:remaining=remaining[:1]
                for item in remaining:
                    s=item['scenario'];entries.append({'name':s['name'],'role':item['role'],'world_seed':s['world_seed']})
                atomic_json(runner.manifest,{'episodes':entries})
                atomic_json(report_dir/'latest.json',{'status':'stopped' if stop_collection else 'completed',
                       'dataset_GB':.01,'episodes_total':len(entries),'stop_reason':'fixture disk stop' if stop_collection else None})
            elif name.endswith('audit'):
                output=Path(command[command.index('--output')+1]);atomic_json(output,{
                    'passed':not failed_audit,'episodes_total':2 if name=='pilot_audit' else 4,
                    'indexed_hdf5_bytes':100,'mean_episode_seconds':20,'feature_cache_bytes':100})
                if failed_audit:raise cloud.StageFailed(name,2)
            elif name.endswith('training'):
                runner.checkpoints.mkdir(exist_ok=True)
                checkpoint={'epoch':int(command[command.index('--epochs')+1]),'bad_epochs':0,
                    'dataset_sha256':file_hash(runner.manifest),'review_manifest_sha256':file_hash(bundle/'manifest.json')}
                torch.save(checkpoint,runner.checkpoints/'latest.pt');torch.save(checkpoint,runner.checkpoints/'best.pt')
                atomic_json(runner.checkpoints/'training_result.json',{'status':'completed'})
            elif name in ('policy_pilot','final_validation','final_test'):
                output=Path(command[command.index('--output')+1]);output.mkdir()
                atomic_json(output/'report.json',{'status':'completed','outcomes':{'water_strike':1} if unsafe_policy else {'landed':12},
                     'success_rate':0. if unsafe_policy else 1.,'dataset_sha256':file_hash(runner.manifest)})
            elif name in ('gpu_probe','qualification','review_export'):pass
            else:raise AssertionError(name)
            runner.save()
        disk=Namespace(free=2000*10**9)
        patches=[patch.object(flow,'ROOT',root),patch.object(cloud,'ROOT',root),
                 patch.object(flow,'planned_scenarios',return_value=plan),patch.object(flow,'source_fingerprint',return_value='fixture-source'),
                 patch.object(flow,'approved_bundle',side_effect=PermissionError('fixture pending') if pending else None,return_value=str(bundle)),
                 patch.object(flow.Pipeline,'run_stage',stage),patch.object(flow.shutil,'disk_usage',return_value=disk)]
        return plan,bundle,calls,patches,disk

    def start(self,args,patches):
        with contextlib.ExitStack() as stack:
            for replacement in patches:stack.enter_context(replacement)
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            runner=flow.Pipeline(args);code=runner.run()
        return runner,code

    def test_pending_review_never_creates_dataset_or_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);plan,bundle,calls,patches,_=self.fixtures(root,pending=True)
            # Pending export fixture occupies the deterministic bundle, not an approval.
            pending=root/'outputs/pipeline_review_fixture-source';pending.mkdir(parents=True)
            (pending/'manifest.json').write_text(json.dumps({'qualification_passed':True}));(pending/'index.html').write_text('fixture')
            runner,code=self.start(args_fixture(root),patches)
            self.assertEqual(code,2);self.assertEqual(runner.status,'user_review_required')
            self.assertFalse(runner.dataset.exists());self.assertFalse(runner.checkpoints.exists())
            self.assertEqual(calls,['gpu_probe','qualification','review_export'])
            self.assertTrue(json.loads((runner.folder/'launch_status.json').read_text())['review_page'])

    def test_storage_stop_prevents_training_and_saves_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,_,calls,patches,_=self.fixtures(root,stop_collection=True)
            runner,code=self.start(args_fixture(root),patches)
            self.assertEqual(code,3);self.assertEqual(runner.status,'stopped')
            self.assertNotIn('initial_training',calls)
            report=json.loads(runner.state_path.read_text())
            self.assertEqual(report['episodes_total'],1);self.assertGreater(report['elapsed_total_seconds'],0)
            self.assertEqual(json.loads((runner.folder/'pipeline_report.json').read_text()),report)

    def test_failed_expert_audit_prevents_full_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,_,calls,patches,_=self.fixtures(root,failed_audit=True)
            runner,code=self.start(args_fixture(root),patches)
            self.assertEqual(code,2);self.assertEqual(runner.status,'failed')
            self.assertNotIn('main_collection',calls);self.assertNotIn('initial_training',calls)
            self.assertTrue(Path(runner.state['milestones']['pilot_audit']['report']).is_file())

    def test_unsafe_policy_pilot_prevents_remaining_budget_and_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,_,calls,patches,_=self.fixtures(root,unsafe_policy=True)
            runner,code=self.start(args_fixture(root),patches)
            self.assertEqual(code,4);self.assertEqual(runner.status,'needs_model_iteration')
            self.assertIn('initial_training',calls);self.assertNotIn('remaining_training',calls);self.assertNotIn('final_test',calls)

    def test_completed_restart_reuses_weights_and_test_assessment(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,_,calls,patches,_=self.fixtures(root)
            args=args_fixture(root);first,code=self.start(args,patches);self.assertEqual(code,0)
            self.assertLess(calls.index('main_collection'),calls.index('initial_training'))
            before=file_hash(first.checkpoints/'best.pt');elapsed=first.state['elapsed_total_seconds'];calls.clear()
            second,code=self.start(args,patches);self.assertEqual(code,0)
            self.assertEqual(calls,['gpu_probe','dataset_audit'])
            self.assertEqual(before,file_hash(second.checkpoints/'best.pt'))
            self.assertEqual(second.state['episodes_total'],4)
            self.assertGreater(second.state['elapsed_total_seconds'],elapsed)
            args.patience=1
            with self.assertRaisesRegex(ValueError,'settings changed'):self.start(args,patches)

    def test_source_change_rejects_resume_before_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,_,calls,patches,_=self.fixtures(root)
            first,_=self.start(args_fixture(root),patches);state=json.loads(first.state_path.read_text());state['source_sha256']='old'
            atomic_json(first.state_path,state);calls.clear()
            second,code=self.start(args_fixture(root),patches)
            self.assertEqual(code,1);self.assertEqual(calls,['gpu_probe']);self.assertIn('Source changed',second.reason)

    def test_completion_requires_unique_exact_plan_and_reserves_training_space(self):
        plan=plan_fixture()
        self.assertGreater(flow.storage_reserve(plan,32),32)
        with tempfile.TemporaryDirectory() as directory:
            manifest=Path(directory)/'manifest.json'
            self.assertFalse(flow.completion(manifest,plan['episodes']))
            entries=[{'name':item['scenario']['name']} for item in plan['episodes']]
            atomic_json(manifest,{'episodes':entries[:-1]});self.assertFalse(flow.completion(manifest,plan['episodes']))
            atomic_json(manifest,{'episodes':entries});self.assertTrue(flow.completion(manifest,plan['episodes']))
            atomic_json(manifest,{'episodes':entries+[entries[0]]})
            with self.assertRaisesRegex(ValueError,'Duplicate'):flow.completion(manifest,plan['episodes'])

    def test_interrupted_launcher_recovers_owned_child_and_refuses_changed_identity(self):
        import psutil
        for changed in (False,True):
            with self.subTest(changed_identity=changed),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);_,_,calls,patches,_=self.fixtures(root)
                command=[sys.executable,'-c','import time;time.sleep(120)']
                child=subprocess.Popen(command,start_new_session=True)
                try:
                    args=args_fixture(root)
                    with contextlib.ExitStack() as stack:
                        for replacement in patches:stack.enter_context(replacement)
                        runner=flow.Pipeline(args)
                        runner.state['stages'].append({'name':'interrupted_fixture','status':'running','child_pid':child.pid,
                            'child_create_time':psutil.Process(child.pid).create_time()+(1 if changed else 0),'command':command})
                        atomic_json(runner.state_path,runner.state)
                    runner,code=self.start(args,patches)
                    if changed:
                        self.assertEqual(code,1);self.assertIsNone(child.poll());self.assertEqual(calls,[])
                        self.assertIn('ownership changed',runner.reason)
                    else:
                        self.assertEqual(code,0);child.wait(timeout=5);self.assertNotEqual(child.returncode,0)
                        self.assertEqual(runner.state['stages'][0]['status'],'interrupted_recovered')
                finally:
                    if child.poll() is None:child.terminate()
                    child.wait(timeout=5)

if __name__=='__main__':unittest.main()
