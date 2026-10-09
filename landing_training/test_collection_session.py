"""Check admission, cancellation, resume accounting, and durable run reports."""
import json
import multiprocessing
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from .collection_session import CollectionSession, GB, episode_reservation
from .execution import iter_jobs


def scheduler_fixture(job, queue, cancel):
    directory = Path(job['directory'])
    directory.mkdir()
    (directory/'started').write_text('fixture')
    if job.get('crash_with_owned_child'):
        import os,subprocess,sys,psutil
        from .collection_session import atomic_json
        runtime=directory/'px4';runtime.mkdir()
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)',str(runtime.resolve())],start_new_session=True)
        atomic_json(runtime/'owned_process.json',{'pid':child.pid,'create_time':psutil.Process(child.pid).create_time(),'runtime':str(runtime.resolve())})
        os._exit(23)
    if job.get('wait_for_cancel'):
        cancel.wait(5)
        queue.put({'ok': False, 'name': job['name'], 'directory': job['directory'],
                   'error': 'cancelled', 'traceback': ''})
    else:
        time.sleep(.02)
        queue.put({'ok': True, 'name': job['name'], 'directory': job['directory']})


class SessionChecks(unittest.TestCase):
    def event(self):
        return multiprocessing.get_context('spawn').Event()

    def test_admission_reserves_active_flights_and_preserves_free_floor(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            session = CollectionSession(destination,self.event(),workers=64,max_episodes=1200,min_free_gb=32,max_dataset_gb=1500)
            job = {'scenario': {'duration': 180}, 'directory': str(destination/'episode')}
            reservation = episode_reservation(job)
            disk = type('Disk', (), {'free': 32*GB + session.shutdown_reserve + 2*reservation})()
            with patch('landing_training.collection_session.shutil.disk_usage',return_value=disk):
                self.assertTrue(session.can_launch(job, [job]))
                disk.free -= 1
                self.assertFalse(session.can_launch(job, [job]))
                self.assertFalse(session.cancel.is_set())  # Drain complete active flights.
                disk.free = 32*GB + session.shutdown_reserve - 1
                session.sample()
                self.assertTrue(session.cancel.is_set())  # Unexpected low space: stop active writes.

    def test_maximum_counts_existing_partial_data_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            destination=Path(folder)
            (destination/'partial').write_bytes(b'x'*4096)
            job={'scenario':{'duration':1},'directory':str(destination/'episode')}
            reserve=episode_reservation(job)
            # 1 worker gets a 1 GiB shutdown reserve.
            maximum=(4096+reserve+1024**3-1)/GB
            for _ in range(2):
                session=CollectionSession(destination,self.event(),workers=1,max_episodes=1,min_free_gb=0,max_dataset_gb=maximum)
                self.assertFalse(session.can_launch(job,[]))
                self.assertIn('dataset limit',session.admission_reason)
                self.assertGreaterEqual(session.initial_bytes,4096)

    def test_success_failure_and_cancel_all_persist_reports(self):
        for exception,expected in ((None,'completed'),(RuntimeError('fixture failure'),'failed'),(KeyboardInterrupt(),'cancelled')):
            with self.subTest(expected=expected),tempfile.TemporaryDirectory() as folder:
                session=CollectionSession(Path(folder),self.event(),workers=1,max_episodes=2,min_free_gb=0)
                try:
                    with session:
                        episode=Path(folder)/'episode';episode.mkdir();artifact=episode/'observations.h5';artifact.write_bytes(b'1234')
                        session.add_episode({'name':'episode','path':'episode/observations.h5','role':'training','outcome':'landed'},
                                            {'records':101,'wall_seconds':2})
                        if exception:raise exception
                except BaseException as exc:
                    self.assertIs(exc,exception)
                report=json.loads(session.latest_path.read_text())
                self.assertEqual(report['status'],expected)
                self.assertEqual(report['episodes_total'],1)
                self.assertEqual(report['outcomes'],{'landed':1})
                self.assertEqual(report['indexed_hdf5_bytes'],4)
                self.assertEqual(report['frames_total'],101)
                self.assertGreater(report['elapsed_seconds'],0)
                self.assertIn('finished_utc',report)
                self.assertEqual(json.loads(session.report_path.read_text()),report)

    def test_live_monitor_cancels_without_completing_a_flight(self):
        with tempfile.TemporaryDirectory() as folder:
            session=CollectionSession(Path(folder),self.event(),workers=1,max_episodes=1,min_free_gb=0)
            disk=type('Disk',(),{'free':10*GB})()
            with patch('landing_training.collection_session.shutil.disk_usage',return_value=disk):
                with session:
                    disk.free=session.shutdown_reserve-1
                    self.assertTrue(session.cancel.wait(2))
                report=json.loads(session.latest_path.read_text())
                self.assertEqual(report['status'],'stopped')
                self.assertIn('free disk',report['stop_reason'])
                self.assertEqual(report['episodes_total'],0)

    def test_scheduler_drains_admitted_jobs_without_launching_blocked_job(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs=[{'name':name,'directory':str(Path(folder)/name)} for name in ('allowed','blocked')]
            cancel=self.event()
            with patch('landing_training.execution.collection_worker',scheduler_fixture):
                rows=list(iter_jobs(jobs,2,cancel_event=cancel,can_launch=lambda job,active:job['name']=='allowed'))
            self.assertEqual([row['name'] for row in rows],['allowed'])
            self.assertFalse((Path(folder)/'blocked').exists())
            self.assertFalse(cancel.is_set())

    def test_scheduler_never_launches_after_cancel_and_closes_workers(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs=[{'name':name,'directory':str(Path(folder)/name),'wait_for_cancel':True} for name in ('active','pending')]
            cancel=self.event()
            def set_cancel():
                for _ in range(100):
                    if (Path(folder)/'active/started').exists():break
                    time.sleep(.02)
                cancel.set()
            thread=threading.Thread(target=set_cancel);thread.start()
            with patch('landing_training.execution.collection_worker',scheduler_fixture):
                rows=list(iter_jobs(jobs,1,cancel_event=cancel))
            thread.join()
            self.assertEqual(rows,[])
            self.assertFalse((Path(folder)/'pending').exists())

    def test_crashed_attempt_is_retained_and_retried_without_overwriting(self):
        from dataclasses import asdict
        from .config import Scenario
        from .collect import _collect_locked
        scenario=asdict(Scenario(name='crashed_fixture'))
        item={'scenario':scenario,'role':'training'}
        for summary_text in (None,'{unfinished',json.dumps({'failure':'KeyboardInterrupt'})):
            with self.subTest(summary=summary_text),tempfile.TemporaryDirectory() as folder:
                destination=Path(folder);bundle=destination/'review';bundle.mkdir()
                (bundle/'manifest.json').write_text('{}')
                episode=destination/scenario['name'];episode.mkdir()
                (episode/'observations.h5').write_bytes(b'partial-preserved')
                if summary_text is not None:(episode/'summary.json').write_text(summary_text)
                with patch('landing_training.collect.planned_scenarios',return_value={'episodes':[item]}):
                    with self.assertRaisesRegex(FileExistsError,'Partial episode'):
                        _collect_locked(bundle,destination,1,None,1,20,{},'fixture')
                    self.assertTrue(episode.exists())
                    with patch('landing_training.execution.iter_jobs',return_value=iter(())) as schedule:
                        _collect_locked(bundle,destination,1,None,1,20,{},'fixture',quarantine_partial=True)
                self.assertFalse(episode.exists())
                saved=list((destination/'partial_attempts').glob('*/observations.h5'))
                self.assertEqual(len(saved),1)
                self.assertEqual(saved[0].read_bytes(),b'partial-preserved')
                jobs=schedule.call_args.args[0]
                self.assertEqual(len(jobs),1)
                self.assertEqual(jobs[0]['name'],scenario['name'])

    def test_abrupt_worker_death_stops_only_its_journalled_native_child(self):
        import os,psutil
        if os.name=='nt':self.skipTest('Linux native ownership journal')
        with tempfile.TemporaryDirectory() as folder:
            job={'name':'crash','directory':str(Path(folder)/'crash'),'crash_with_owned_child':True}
            with patch('landing_training.execution.collection_worker',scheduler_fixture):
                with self.assertRaisesRegex(RuntimeError,'without a result'):list(iter_jobs([job],1))
            record=json.loads((Path(job['directory'])/'px4/owned_process.json').read_text())
            self.assertFalse(psutil.pid_exists(record['pid']) and psutil.Process(record['pid']).status()!=psutil.STATUS_ZOMBIE)


if __name__=='__main__':unittest.main()
