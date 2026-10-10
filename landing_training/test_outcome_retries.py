"""Real HDF5/index replay checks; no simulator flights or rendering."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import h5py

from .collect import _collect_locked
from .collection_session import atomic_json
from .dataset_audit import audit_dataset
from .gate import file_hash
from .outcome_retries import quality, prepare_attempt, RETRY_LIMIT
from .test_dataset_audit import write_episode, manifest
from .training_pipeline import teacher_supervision
from .workflow import verify_runtime_resume


class ReplayChecks(unittest.TestCase):
    def fixture(self, root, count=2):
        items=[];entries=[]
        for index in range(count):
            item,entry=write_episode(root,name=f'flight_{index}',outcome='abort' if index==0 else 'landed',world=index)
            summary=root/entry['name']/'summary.json'
            data=json.loads(summary.read_text());data.update(source_sha256='source',runtime_source_sha256='runtime')
            atomic_json(summary,data);entries.append(entry);items.append(item)
        bundle=root/'review';bundle.mkdir();(bundle/'manifest.json').write_text('{}')
        path=manifest(root,entries);data=json.loads(path.read_text());data['review_manifest_sha256']=file_hash(bundle/'manifest.json');atomic_json(path,data)
        return items,bundle,path

    def worker(self,root,outcome='landed',interrupt=False):
        def jobs(items,*args,**kwargs):
            for job in items:
                self.assertEqual(job['name'],'flight_0')
                directory=Path(job['directory']);directory.parent.mkdir(parents=True,exist_ok=True)
                shutil.copytree(root/job['name'],directory)
                summary=directory/'summary.json';data=json.loads(summary.read_text())
                self.assertEqual(data['scenario'],job['scenario'])
                data['outcome']=outcome;atomic_json(summary,data)
                with h5py.File(directory/'observations.h5','r+') as recording:
                    rows=[json.loads(row) for row in recording['steps'][:]]
                    rows[-1]['outcome']=outcome
                    rows[-1]['observation']['px4'].update(armed=outcome!='landed',landed=outcome=='landed')
                    recording['steps'][:]=[json.dumps(row) for row in rows]
                (directory/'steps.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
                if interrupt:raise RuntimeError('fixture interrupted before commit')
                yield {'name':job['name'],'directory':str(directory)}
        return jobs

    def replay(self,root,items,bundle,worker):
        with patch('landing_training.collect.planned_scenarios',return_value={'episodes':items}), \
             patch('landing_training.execution.iter_jobs',side_effect=worker), \
             patch('landing_training.collect.shutil.disk_usage',return_value=type('Disk',(),{'free':30*10**9})()):
            return _collect_locked(bundle,root,2,None,2,20,{},'source',retry_names=['flight_0','flight_1'],quarantine_partial=True)

    def test_only_failed_flight_replayed_success_swaps_index_originals_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);items,bundle,path=self.fixture(root)
            originals={str(p):file_hash(p) for p in root.glob('flight_*/*')}
            result=self.replay(root,items,bundle,self.worker(root))
            self.assertEqual(len(result['episodes']),2)
            entry=result['episodes'][0];self.assertEqual(entry['outcome'],'landed')
            self.assertEqual(entry['path'],'retry_attempts/flight_0/attempt_001/observations.h5')
            self.assertEqual(entry['sha256'],file_hash(root/entry['path']))
            self.assertEqual(originals,{p:file_hash(p) for p in originals})
            self.assertTrue(audit_dataset(path,items)['passed'])
            def no_jobs(jobs,*args,**kwargs):
                self.assertEqual(jobs,[]);return iter(())
            self.replay(root,items,bundle,no_jobs)
            self.assertEqual(len(json.loads(path.read_text())['outcome_retries']['flight_0']),1)

    def test_interrupted_completed_recording_recovers_same_attempt_without_reflight(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);items,bundle,path=self.fixture(root)
            with self.assertRaisesRegex(RuntimeError,'before commit'):
                self.replay(root,items,bundle,self.worker(root,interrupt=True))
            pending=json.loads(path.read_text());self.assertEqual(pending['outcome_retries']['flight_0'][0]['status'],'pending')
            self.assertEqual(pending['episodes'][0]['outcome'],'abort')
            def no_jobs(jobs,*args,**kwargs):
                self.assertEqual(jobs,[]);return iter(())
            result=self.replay(root,items,bundle,no_jobs)
            self.assertEqual(result['episodes'][0]['outcome'],'landed')
            self.assertEqual(len(result['outcome_retries']['flight_0']),1)

    def test_three_failed_replays_retained_masked_and_accepted_only_with_verified_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);items,bundle,path=self.fixture(root,count=50)
            for _ in range(RETRY_LIMIT):self.replay(root,items,bundle,self.worker(root,outcome='abort'))
            result=json.loads(path.read_text());self.assertFalse(result['episodes'][0]['imitation_allowed'])
            def no_jobs(jobs,*args,**kwargs):
                self.assertEqual(jobs,[]);return iter(())
            self.replay(root,items,bundle,no_jobs)
            self.assertFalse(audit_dataset(path,items)['passed'])
            report=audit_dataset(path,items,allow_retried_aborts=True)
            self.assertTrue(report['passed']);self.assertEqual(report['nominal_landing_rates']['training'],.98)
            self.assertEqual(report['retry_exhausted'],['flight_0']);self.assertTrue(report['quality_warnings'])
            allowed,excluded=teacher_supervision(result,root)
            self.assertFalse(allowed[str(root/'flight_0/observations.h5')]);self.assertEqual(excluded,['flight_0'])
            evidence=root/'retry_attempts/flight_0/attempt_001/observations.h5'
            with evidence.open('ab') as stream:stream.write(b'changed')
            with self.assertRaisesRegex(ValueError,'evidence missing or changed'):
                audit_dataset(path,items,allow_retried_aborts=True)

    def test_unsafe_retry_stops_and_never_replaces_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);items,bundle,path=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'Unsafe expert retry'):
                self.replay(root,items,bundle,self.worker(root,outcome='water_strike'))
            result=json.loads(path.read_text());self.assertEqual(result['episodes'][0]['outcome'],'abort')
            self.assertEqual(result['outcome_retries']['flight_0'][0]['status'],'pending')

    def test_quality_floor_applies_to_each_split_not_only_aggregate(self):
        history=[{'status':'completed','outcome':'abort'}]*3
        data={'outcome_retries':{'bad':[dict(item) for item in history]}}
        rows=[{'name':str(i),'role':'training','outcome':'landed','fault_case':False} for i in range(100)]
        rows += [{'name':'bad','role':'validation','outcome':'abort','fault_case':False}]
        result=quality(rows,data,True)
        self.assertFalse(result['nominal_quality_passed']);self.assertEqual(result['nominal_landing_rates']['validation'],0.)

    def test_pending_attempt_slot_survives_restart_and_rejects_escaped_path(self):
        data={};item={'scenario':{'name':'flight'}}
        first=prepare_attempt(data,Path('/tmp'),item)
        self.assertEqual(first,prepare_attempt(data,Path('/tmp'),item))
        data['outcome_retries']['flight'][0]['directory']='../escape'
        with self.assertRaisesRegex(ValueError,'escapes'):prepare_attempt(data,Path('/tmp'),item)

    def test_source_resume_requires_prior_and_every_recorded_runtime_to_match(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,_,path=self.fixture(root)
            state={'review_authorization':{'runtime_sha256':'runtime'}}
            verify_runtime_resume(state,'runtime',path)
            with self.assertRaisesRegex(ValueError,'proof is required'):verify_runtime_resume({},'runtime',path)
            summary=root/'flight_0/summary.json';data=json.loads(summary.read_text())
            data['runtime_source_sha256']='changed';atomic_json(summary,data)
            with self.assertRaisesRegex(ValueError,'episode runtime changed'):verify_runtime_resume(state,'runtime',path)


if __name__=='__main__':unittest.main()
