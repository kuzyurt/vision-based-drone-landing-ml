"""Verify counted progress, interrupted timings and loss exports without a VM."""
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from .collection_session import atomic_json
from .progress import export_loss_history, TrainingProgress
from .status import snapshot, stage_times, display


class StatusChecks(unittest.TestCase):
    def test_live_collection_training_and_evaluation_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=root/'dataset';data.mkdir();weights=root/'weights';weights.mkdir()
            evaluation=root/'evaluation';evaluation.mkdir()
            atomic_json(data/'manifest.json',{'episodes':[{'role':'training'}]*60+[{'role':'validation'}]*10})
            atomic_json(weights/'training_progress.json',{'phase':'training','current_epoch':3,
                'completed_epochs':2,'phase_completed_frames':250,'phase_total_frames':1000})
            atomic_json(evaluation/'report.json',{'episodes':[{}]*4})
            state={'configuration':{'output':str(data),'checkpoints':str(weights),'epochs':10},
                   'status':'running','active_stage':'policy_pilot','planned_episodes':100,
                   'stages':[{'name':'pilot_collection','elapsed_seconds':3600,'status':'completed'},
                             {'name':'initial_training','elapsed_seconds':1800,'status':'completed'},
                             {'name':'policy_pilot','elapsed_seconds':10,'status':'running',
                              'command':['python','--output',str(evaluation),'--max-episodes','12']}],
                   'updated_utc':datetime.now(timezone.utc).isoformat()}
            report=snapshot(state)
            self.assertEqual(report['progress']['collection']['percent'],70)
            self.assertEqual(report['progress']['training_epoch_budget']['percent'],20)
            self.assertEqual(report['progress']['current_epoch_training']['percent'],25)
            self.assertEqual(report['progress']['policy_pilot']['percent'],33.33)
            self.assertEqual(report['timing']['collection_hours'],1)
            self.assertEqual(report['timing']['training_hours_including_preparation'],.5)
            self.assertEqual(report['dataset_splits'],{'training':60,'validation':10})
            self.assertIn('70.0%',display(report))

    def test_stale_heartbeat_does_not_turn_offline_time_into_work(self):
        now=datetime.now(timezone.utc);start=now-timedelta(hours=4)
        state={'updated_utc':(start+timedelta(seconds=60)).isoformat(),
               'stages':[{'name':'main_collection','status':'running','started_utc':start.isoformat()}]}
        seconds,hours=stage_times(state,now)
        self.assertEqual(seconds['main_collection'],60)
        self.assertAlmostEqual(hours['collection_hours'],1/60)

    def test_loss_csv_repaired_from_committed_history_and_attempts_labelled(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            row={'epoch':1,'finished_utc':'2026-10-10T00:00:00+00:00',
                 'training_elapsed_hours':.5,'train_lane_loss_mean':.2,'validation_loss':.3,
                 'validation_metrics':{'action_huber':.12,'persistence_action_huber':.15}}
            export_loss_history(output,[row,{**row,'epoch':2}])
            export_loss_history(output,[row])
            with (output/'loss_history.csv').open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['validation_action_huber'],'0.12')
            first=TrainingProgress(output,10);first.loss_sample(2,20,4,.8)
            first.save(force=True,phase='training',completed_epochs=1)
            second=TrainingProgress(output,10);second.loss_sample(2,20,4,.8)
            with (output/'loss_updates.csv').open() as stream:samples=list(csv.DictReader(stream))
            self.assertEqual(len(samples),2);self.assertNotEqual(samples[0]['attempt'],samples[1]['attempt'])
            self.assertEqual(float(samples[0]['train_lane_loss_mean']),.2)
            self.assertGreaterEqual(float(samples[1]['training_elapsed_hours']),float(samples[0]['training_elapsed_hours']))


if __name__=='__main__':unittest.main()
