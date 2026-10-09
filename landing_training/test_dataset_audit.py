"""Validate real recording arrays and trace alignment, not synthetic loss values."""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
import torch
from unittest.mock import patch
import h5py
import numpy as np

from .config import Scenario
from .collection_session import atomic_json
from .recording import Recorder,TraceRecorder
from .dataset_audit import audit_dataset
from .collect import planned_scenarios
from .evaluate import select_episodes
from .gate import file_hash


def write_episode(root,name='flight',role='training',outcome='landed',fault=False,world=1):
    scenario=asdict(Scenario(name=name,world_seed=world,path_seed=world+100,boat_start_fraction=.5,
                           camera_blind_seconds=1. if fault else 0.))
    directory=root/name;directory.mkdir();recorder=Recorder(directory,scenario,role)
    row={'role':role,'frame_index':0,'time_s':10.,'task_time_s':0.,'outcome':'flying',
         'observation':{'px4':{'valid':True,'armed':True,'landed':False,'attitude_ned_rad':[0,0,0]},
             'beacon':{'age_s':0.,'valid':True,'dock_ready':True},'gimbal_rad':[0,0],
             'image_age_s':0.,'image_delivery_time_s':10.,'image_capture_time_s':10.,
             'image_valid':True,'previous_executed_action':[0.]*6,'decision_dt_s':.04,
             'mission':{'elapsed_s':0.,'budget_s':scenario['duration'],'supervisor':None}},
         'output':{'executed_action':[0.]*6,'expert_bounded_action':[0.]*6,'action_supervision_valid':True},
         'privileged':{'dock_joint_m':[.4,.46,.46],'vertical_clearance_m':2.,'pad_visible':False,
             'pad_position_enu_m':[0,0,0],'drone_position_enu_m':[2,0,2]}}
    image=np.zeros((360,640,3),dtype='u1');recorder.append(image,row)
    row=copy.deepcopy(row);row.update(frame_index=1,time_s=10.04,task_time_s=.04,terminal=True,outcome=outcome)
    row['observation']['mission']['elapsed_s']=.04
    row['observation'].update(image_delivery_time_s=10.04,image_capture_time_s=10.04)
    row['observation']['px4'].update(armed=outcome!='landed',landed=outcome=='landed')
    row['output']['action_supervision_valid']=False;recorder.append(image,row);recorder.close()
    atomic_json(directory/'summary.json',{'scenario':scenario,'records':2,'role':role,'training_eligible':True,
        'failure':None,'outcome':outcome,'max_dock_error_m':0.,'preparation_water_clearance_m':6.,'boat_start_progress_m':200.})
    item={'role':role,'distance_band':0,'weather_group':0,'scenario':scenario}
    entry={'name':name,'role':role,'world_seed':world,'path_seed':world+100,'outcome':outcome,'path':name+'/observations.h5'}
    return item,entry


def manifest(root,entries):
    path=root/'manifest.json';atomic_json(path,{'schema':'aerodock.landing.dataset.v1','role':'dataset',
        'review_manifest_sha256':'disposable-test-only','episodes':entries});return path


class AuditChecks(unittest.TestCase):
    def test_airborne_terminal_clock_and_storage_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);item,entry=write_episode(root);report=audit_dataset(manifest(root,[entry]),[item])
            self.assertTrue(report['passed']);self.assertEqual(report['frames_total'],2)
            self.assertEqual(report['feature_cache_bytes'],2*7108);self.assertEqual(report['episodes'][0]['supervised_steps'],1)
            self.assertAlmostEqual(report['mean_episode_seconds'],.04)

    def test_nominal_failure_is_rejected_but_fault_abort_is_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);item,entry=write_episode(root,outcome='abort')
            report=audit_dataset(manifest(root,[entry]),[item]);self.assertFalse(report['passed'])
            self.assertEqual(report['nominal_expert_failures'],['flight'])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);item,entry=write_episode(root,outcome='abort',fault=True)
            self.assertTrue(audit_dataset(manifest(root,[entry]),[item])['passed'])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);item,entry=write_episode(root,outcome='water_strike',fault=True)
            report=audit_dataset(manifest(root,[entry]),[item]);self.assertFalse(report['passed']);self.assertEqual(report['unsafe_expert_flights'],['flight'])

    def test_changed_rows_and_unconfirmed_landing_are_rejected(self):
        for problem in ('previous','landing','dock','supervision','mission'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);item,entry=write_episode(root)
                with h5py.File(root/entry['path'],'r+') as data:
                    rows=[json.loads(row) for row in data['steps'][:]]
                    if problem=='previous':rows[1]['observation']['previous_executed_action'][0]=1.
                    elif problem=='landing':rows[1]['observation']['px4']['armed']=True
                    elif problem=='dock':rows[0]['privileged']['dock_joint_m'][0]=0.
                    elif problem=='supervision':rows[0]['observation']['mission']['supervisor']='mission_deadline'
                    elif problem=='mission':rows[0]['observation']['mission']['elapsed_s']=1.
                    data['steps'][:]=[json.dumps(row) for row in rows]
                (root/'flight/steps.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
                with self.assertRaises(ValueError):audit_dataset(manifest(root,[entry]),[item])

    def test_pilot_resume_ignores_only_known_later_plan_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);pilot,entry=write_episode(root);later,other=write_episode(root,name='later',role='test',world=2)
            path=manifest(root,[entry,other])
            with patch('landing_training.dataset_audit.planned_scenarios',return_value={'episodes':[pilot,later]}):
                self.assertTrue(audit_dataset(path,[pilot],allow_other_planned=True)['passed'])
                other['name']='unplanned';manifest(root,[entry,other])
                with self.assertRaisesRegex(ValueError,'Unplanned'):audit_dataset(path,[pilot],allow_other_planned=True)

    def test_trace_recorder_does_not_archive_rgb_or_make_training_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);recorder=TraceRecorder(root);recorder.append(np.zeros((1,1,3)),{'decision':np.array([1,2])});recorder.close()
            self.assertEqual([p.name for p in root.iterdir()],['steps.jsonl'])
            self.assertEqual(json.loads((root/'steps.jsonl').read_text()),{'decision':[1,2]})

    def test_balanced_pilot_and_stratified_policy_selection(self):
        plan=planned_scenarios();pilot=plan['episodes'][:plan['pilot_first_episodes']]
        for role in ('training','validation'):
            subset=[e for e in pilot if e['role']==role];self.assertEqual(len(subset),120)
            self.assertEqual(len({(e['scenario']['kind'],e['distance_band'],e['weather_group'],e['scenario']['reverse']) for e in subset}),120)
        entries=[{'name':e['scenario']['name'],'role':e['role'],'world_seed':e['scenario']['world_seed']} for e in plan['episodes']]
        selected=select_episodes(entries,'validation',12,stratified=True);by_name={e['scenario']['name']:e for e in plan['episodes']}
        self.assertEqual({by_name[e['name']]['scenario']['kind'] for e in selected},{'island','beach','city','gravel','rock'})
        self.assertEqual({by_name[e['name']]['distance_band'] for e in selected},{0,1,2})
        self.assertEqual({by_name[e['name']]['weather_group'] for e in selected},{0,1,2,3})
        self.assertEqual(len({e['world_seed'] for e in selected}),12)
        self.assertTrue(all(e['role']=='validation' for e in selected))

    def test_parallel_evaluation_jobs_use_trace_only_and_preserve_split(self):
        from . import evaluate as evaluator,train as trainer,execution
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);entries=[]
            for world,role in enumerate(('training','validation','test'),1):
                _,entry=write_episode(root,name=role,role=role,world=world)
                entry['sha256']=file_hash(root/entry['path']);entries.append(entry)
            review=root/'review';review.mkdir();(review/'manifest.json').write_text('{}')
            path=manifest(root,entries);index=json.loads(path.read_text());index['review_manifest_sha256']=file_hash(review/'manifest.json');atomic_json(path,index)
            checkpoint=root/'weights.pt';torch.save({'schema':'aerodock.landing.checkpoint.v1',
                'dataset_sha256':file_hash(path),'review_manifest_sha256':file_hash(review/'manifest.json')},checkpoint)
            seen=[]
            def jobs(items,*args,**kwargs):
                for job in items:
                    seen.append(job);directory=Path(job['directory']);directory.mkdir()
                    recorder=TraceRecorder(directory);recorder.append(None,{'time_s':0.});recorder.close()
                    atomic_json(directory/'summary.json',{'scenario':job['scenario'],'failure':None,
                        'events':[],'phase_counts':{'confirm':1},'outcome':'landed','max_dock_error_m':0.})
                    yield {'directory':str(directory)}
            # Authorization is replaced only for this disposable fixture.
            with patch.object(trainer,'require_approval'),patch.object(execution,'iter_jobs',jobs),patch('landing_training.collection_benchmark.check_ports') as ports:
                report=evaluator.evaluate(path,review,checkpoint,'validation',root/'evaluation',1,device='cpu',workers=2,cpu_threads=1)
            ports.assert_called_once_with(160,1)
            self.assertEqual(report['status'],'completed');self.assertEqual(report['split'],'validation')
            self.assertEqual(report['outcomes'],{'landed':1});self.assertEqual(len(seen),1)
            self.assertFalse(seen[0]['record_images']);self.assertFalse(seen[0]['video']);self.assertEqual(seen[0]['role'],'validation')
            self.assertFalse(list((root/'evaluation').rglob('*.h5')))

if __name__=='__main__':unittest.main()
