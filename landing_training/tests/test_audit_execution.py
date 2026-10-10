"""Real HDF5 process-pool checks; no renderer, model training or image reads."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import h5py
import numpy as np

from .. import audit_execution as execution
from ..dataset_audit import audit_dataset,inspect_episode
from .test_dataset_audit import write_episode,manifest


def sequence(root,name='flight',world=1,count=513):
    item,entry=write_episode(root,name=name,world=world)
    path=root/entry['path']
    with h5py.File(path,'r+') as data:
        first=json.loads(data['steps'][0]);last=json.loads(data['steps'][1]);records=[];previous=[0.]*6
        for index in range(count):
            row=copy.deepcopy(last if index==count-1 else first)
            row.update(frame_index=index,time_s=10+index*.04,task_time_s=index*.04)
            observation=row['observation'];observation['mission']['elapsed_s']=index*.04
            observation.update(image_delivery_time_s=10+index*.04,image_capture_time_s=10+index*.04,
                               previous_executed_action=previous)
            action=[.1*np.sin(index),.2,0,0,0,0] if index<count-1 else [0.]*6
            row['output'].update(executed_action=action,expert_bounded_action=action)
            previous=action;records.append(json.dumps(row,separators=(',',':')))
        data['rgb'].resize(count,axis=0);data['steps'].resize(count,axis=0);data['steps'][:]=records
    (path.parent/'steps.jsonl').write_text(''.join(row+'\n' for row in records))
    summary=json.loads((path.parent/'summary.json').read_text());summary['records']=count
    (path.parent/'summary.json').write_text(json.dumps(summary))
    return item,entry


class ParallelAuditChecks(unittest.TestCase):
    def test_cli_saves_parallel_report_and_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);items=[];entries=[]
            for index in range(3):
                item,entry=sequence(root,name=f'flight_{index}',world=index)
                items.append(item);entries.append(entry)
            manifest(root,entries);(root/'plan.json').write_text(json.dumps(items))
            driver=root/'driver.py'
            driver.write_text('''if __name__ == '__main__':
    import json, sys
    from pathlib import Path
    from landing_training import dataset_audit as audit
    root=Path(sys.argv[1])
    audit.planned_scenarios=lambda: {'episodes':json.loads((root/'plan.json').read_text())}
    sys.argv=['audit','--manifest',str(root/'manifest.json'),'--output',str(root/'report.json'),'--workers','2']
    audit.main()
''')
            environment={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2]),
                         'PYTHONDONTWRITEBYTECODE':'1'}
            result=subprocess.run([sys.executable,str(driver),str(root)],env=environment,
                                  text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads((root/'report.json').read_text())
            progress=json.loads((root/'report.progress.json').read_text())
            self.assertTrue(report['passed'])
            self.assertEqual(report['performance']['workers_used'],2)
            self.assertEqual(progress['status'],'completed')
            self.assertEqual(progress['recordings_completed'],3)
            self.assertEqual(progress['frames_checked'],3*513)
            self.assertIn('3/3 recordings (100.0%)',result.stdout)

    def test_process_pool_matches_serial_report_and_bounds_queued_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);items=[];entries=[]
            for index in range(6):
                item,entry=sequence(root,name=f'flight_{index}',world=index)
                items.append(item);entries.append(entry)
            path=manifest(root,entries);serial=audit_dataset(path,items,workers=1)
            parallel=audit_dataset(path,items,workers=2)
            self.assertEqual({k:v for k,v in serial.items() if k!='performance'},
                             {k:v for k,v in parallel.items() if k!='performance'})
            performance=parallel['performance']
            self.assertEqual(performance['workers_used'],2)
            self.assertLessEqual(performance['peak_pending_jobs'],4)
            self.assertEqual(performance['frames_checked'],6*513)
            self.assertFalse(performance['indexed_rgb_decoded'])
            self.assertFalse(performance['gpu_used'])

    def test_batch_edges_equivalent_json_and_no_rgb_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);item,entry=sequence(root);path=root/entry['path']
            original=h5py.Dataset.__getitem__
            def read(dataset,key):
                if dataset.name=='/rgb':raise AssertionError('Audit must never decode RGB')
                return original(dataset,key)
            expected=inspect_episode(path,entry,item)
            # Recorder normally uses identical bytes, but semantic equivalence
            # must remain valid for differently formatted JSON copies.
            lines=(path.parent/'steps.jsonl').read_text().splitlines()
            (path.parent/'steps.jsonl').write_text('\n'.join(json.dumps(json.loads(row),sort_keys=True) for row in lines)+'\n')
            with patch.object(h5py.Dataset,'__getitem__',read):
                self.assertEqual(inspect_episode(path,entry,item),expected)
            with h5py.File(path,'r+') as data:
                row=json.loads(data['steps'][256]);row['observation']['previous_executed_action'][0]+=1
                encoded=json.dumps(row);data['steps'][256]=encoded
            lines[256]=encoded;(path.parent/'steps.jsonl').write_text('\n'.join(lines)+'\n')
            with self.assertRaisesRegex(ValueError,'Previous-action alignment'):
                audit_dataset(manifest(root,[entry]),[item],workers=2)

    def test_worker_failure_stops_pool_and_no_pass_report_is_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);items=[];entries=[];notifications=[]
            for index in range(4):
                item,entry=sequence(root,name=f'flight_{index}',world=index)
                items.append(item);entries.append(entry)
            bad=root/entries[0]['path']
            with h5py.File(bad,'r+') as data:data['steps'][0]='{}'
            with self.assertRaises(ValueError):
                audit_dataset(manifest(root,entries),items,workers=2,
                              progress=lambda state,**kw:notifications.append(state))
            self.assertEqual(notifications[-1]['status'],'failed')
            self.assertLess(notifications[-1]['recordings_completed'],4)

    def test_worker_selection_respects_vm_quota_and_ram(self):
        with patch.object(execution.os,'sched_getaffinity',return_value=set(range(32)),create=True), \
             patch.object(execution.Path,'read_text',return_value='max 100000'), \
             patch.object(execution,'available_memory',return_value=128*1024**3):
            self.assertEqual(execution.worker_count(0,1230),32)
            with patch.object(execution.Path,'read_text',return_value='200000 100000'):
                self.assertEqual(execution.worker_count(0,1230),2)
                self.assertEqual(execution.worker_count(32,1230),2)
            with patch.object(execution,'available_memory',return_value=1024**3):
                self.assertEqual(execution.worker_count(0,1230),1)
            with self.assertRaises(ValueError):execution.worker_count(-1,10)

    def test_cancelled_hash_never_reads_file(self):
        class Cancel:
            def is_set(self):return True
        with patch.object(execution,'_cancel',Cancel()),patch('builtins.open') as opened:
            with self.assertRaises(InterruptedError):execution.checked_hash('/must-not-open')
            opened.assert_not_called()


if __name__=='__main__':unittest.main()
